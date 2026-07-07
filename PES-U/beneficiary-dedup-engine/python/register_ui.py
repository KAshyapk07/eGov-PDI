"""
register_ui.py  —  Offline field-worker registration UI (cycle-aware).

NEW MODEL (vaccination drives):
Each cycle is a different drive (cycle 1 = malaria, cycle 2 = polio, ...).
The SAME person is EXPECTED to appear across cycles — that is normal repeat
participation, not an error. So:

  * SAME-CYCLE match  -> a real duplicate (double registration in THIS drive).
                         BLOCKS the save; worker must review before storing.
  * PAST-CYCLE match  -> the person's history across earlier drives.
                         Shown for information only; never blocks.

The field worker enters CYCLE 3 records. Existing population = cycles 1-3
(cycle 3 is needed so we can detect same-cycle duplicates), plus anything
saved this session.

Fully offline: pure Python standard library (tkinter). No network, no pip.

Run:
    python register_ui.py --records <path to dedup_test_records.csv>
"""

import argparse
import os
import sys
import uuid
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox

from digit_dedup_engine import load_records, check_for_duplicates
from models.candidate_pair import Beneficiary
from models.dedup_result import DUPLICATE, REVIEW
from algorithms.double_metaphone import metaphone_code

# ── Cycle model ────────────────────────────────────────────────────────────
NEW_CYCLE = "3"                 # the drive the worker is registering for now
PAST_CYCLES = {"1", "2"}        # earlier drives -> shown as history, never block
EXISTING_CYCLES = {"1", "2", "3"}  # load these as the existing population

# Optional friendly labels for the drives (edit to match reality).
CYCLE_LABELS = {
    "1": "Cycle 1",
    "2": "Cycle 2",
    "3": "Cycle 3",
}

DATE_INPUT_FORMATS = ["%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"]


def cycle_label(c):
    c = (c or "").strip()
    return CYCLE_LABELS.get(c, f"Cycle {c}" if c else "Cycle ?")


def _candidate_subset(new_rec, existing):
    """Fast pre-filter: keep existing records sharing boundary, phonetic given
    name, or birth year with the new record. Mirrors the SQLite query the real
    on-device app would run."""
    code = metaphone_code(new_rec.norm_given) if new_rec.norm_given else ""
    year = new_rec.dob_year
    subset = []
    for r in existing:
        if new_rec.boundary_code and r.boundary_code == new_rec.boundary_code:
            subset.append(r); continue
        if code and r.norm_given and metaphone_code(r.norm_given) == code:
            subset.append(r); continue
        if year and r.dob_year == year:
            subset.append(r); continue
    return subset


def _parse_date(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in DATE_INPUT_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return "INVALID"


class RegistrationApp:
    def __init__(self, master, records_path):
        self.master = master
        self.records_path = records_path
        master.title(f"Beneficiary Registration — {cycle_label(NEW_CYCLE)} (Offline)")
        master.geometry("660x760")

        self.existing = []      # cycles 1-3 from file
        self.new_records = []   # saved this session (all cycle 3)

        self._build_form()
        self._load_existing()

    def _load_existing(self):
        self.status.set("Loading existing records (cycles 1-3)...")
        self.master.update_idletasks()
        try:
            all_recs = load_records(self.records_path)
        except Exception as e:
            messagebox.showerror("Load error", f"Could not load records:\n{e}")
            self.status.set("Load failed.")
            return
        self.existing = [r for r in all_recs
                         if (r.cycle or "").strip() in EXISTING_CYCLES]
        n3 = sum(1 for r in self.existing if (r.cycle or "").strip() == NEW_CYCLE)
        self.status.set(
            f"Ready. {len(self.existing):,} existing records loaded "
            f"({n3:,} already in {cycle_label(NEW_CYCLE)}). "
            f"Same-cycle matches block; past-cycle matches show as history.")

    def _build_form(self):
        pad = {"padx": 8, "pady": 4}
        frm = ttk.Frame(self.master, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text=f"New Registration - {cycle_label(NEW_CYCLE)}",
                  font=("Segoe UI", 14, "bold")).grid(
                      row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.fields = {}
        rows = [
            ("given_name",   "Given name *"),
            ("family_name",  "Family name *"),
            ("father_name",  "Father's name"),
            ("husband_name", "Husband's name"),
            ("date_of_birth","Date of birth (DD-MM-YYYY) *"),
            ("mobile_number","Mobile number"),
            ("boundary_code","Boundary code *"),
            ("locality_name","Locality name"),
            ("latitude",     "Latitude (optional)"),
            ("longitude",    "Longitude (optional)"),
        ]
        r = 1
        for key, label in rows:
            ttk.Label(frm, text=label).grid(row=r, column=0, sticky="w", **pad)
            e = ttk.Entry(frm, width=42)
            e.grid(row=r, column=1, sticky="w", **pad)
            self.fields[key] = e
            r += 1

        ttk.Label(frm, text="Gender *").grid(row=r, column=0, sticky="w", **pad)
        self.gender = tk.StringVar(value="MALE")
        gfrm = ttk.Frame(frm); gfrm.grid(row=r, column=1, sticky="w", **pad)
        ttk.Radiobutton(gfrm, text="Male", variable=self.gender, value="MALE").pack(side="left")
        ttk.Radiobutton(gfrm, text="Female", variable=self.gender, value="FEMALE").pack(side="left")
        r += 1

        btns = ttk.Frame(frm); btns.grid(row=r, column=0, columnspan=2, pady=14)
        ttk.Button(btns, text="Check & Save", command=self.on_save).pack(side="left", padx=6)
        ttk.Button(btns, text="Clear", command=self.clear_form).pack(side="left", padx=6)
        r += 1

        self.status = tk.StringVar(value="Starting...")
        ttk.Label(frm, textvariable=self.status, foreground="#555",
                  wraplength=600, justify="left").grid(
                      row=r, column=0, columnspan=2, sticky="w", pady=(6, 0))

    def _form_to_record(self):
        def val(k): return self.fields[k].get().strip()
        dob = _parse_date(val("date_of_birth"))
        if dob == "INVALID":
            messagebox.showwarning("Invalid date", "Date of birth must be DD-MM-YYYY.")
            return None
        def fnum(k):
            try: return float(val(k)) if val(k) else None
            except ValueError: return None
        missing = [lbl for key, lbl in [
            ("given_name","Given name"), ("family_name","Family name"),
            ("date_of_birth","Date of birth"), ("boundary_code","Boundary code")]
            if not val(key)]
        if missing:
            messagebox.showwarning("Missing fields", "Please fill: " + ", ".join(missing))
            return None
        rec = Beneficiary(
            individual_id=str(uuid.uuid4()),
            given_name=val("given_name") or None,
            family_name=val("family_name") or None,
            father_name=val("father_name") or None,
            husband_name=val("husband_name") or None,
            gender=self.gender.get(),
            date_of_birth=dob,
            boundary_code=val("boundary_code") or None,
            locality_name=val("locality_name") or None,
            latitude=fnum("latitude"), longitude=fnum("longitude"),
            location_accuracy=None,
            mobile_number=val("mobile_number") or None,
            cycle=NEW_CYCLE,
        )
        rec.normalize()
        return rec

    def on_save(self):
        rec = self._form_to_record()
        if rec is None:
            return
        self.status.set("Checking...")
        self.master.update_idletasks()

        pool = self._candidate_pool(rec)
        by_id = {r.individual_id: r for r in pool}
        matches = check_for_duplicates(rec, pool)
        strong = [m for m in matches if m.verdict in (DUPLICATE, REVIEW)]

        # Split by the cycle of the matched record.
        same_cycle, past_cycle = [], []
        for m in strong:
            other = by_id.get(m.id_b)
            if other is None:
                continue
            oc = (other.cycle or "").strip()
            if oc == NEW_CYCLE:
                same_cycle.append(m)
            elif oc in PAST_CYCLES:
                past_cycle.append(m)

        if same_cycle:
            # BLOCK: a real duplicate within this drive.
            self._show_duplicate_dialog(rec, same_cycle, past_cycle, by_id)
        else:
            # No same-cycle duplicate -> save. Show past-cycle history as info.
            self._commit(rec)
            if past_cycle:
                self._show_history_info(rec, past_cycle, by_id)
            else:
                messagebox.showinfo("Saved", "No duplicate found. Record saved.")
            self.status.set(
                f"Saved to {cycle_label(NEW_CYCLE)}. "
                f"{len(self.new_records)} new record(s) this session.")
            self.clear_form()

    def _candidate_pool(self, rec):
        base = _candidate_subset(rec, self.existing)
        base.extend(self.new_records)  # same-cycle dupes entered this session
        return base

    def _commit(self, rec):
        self.new_records.append(rec)

    # ── history info popup (non-blocking) ──
    def _show_history_info(self, rec, past, by_id):
        lines = []
        for m in sorted(past, key=lambda x: x.score, reverse=True)[:6]:
            o = by_id.get(m.id_b)
            if not o: continue
            lines.append(f"- {cycle_label(o.cycle)}: {o.given_name} {o.family_name} "
                         f"(match {m.score:.2f})")
        messagebox.showinfo(
            "Saved - past-cycle history found",
            "Record saved to this drive.\n\n"
            "This person also appears in earlier drives (expected):\n\n"
            + "\n".join(lines))

    # ── same-cycle duplicate dialog (blocking) ──
    def _show_duplicate_dialog(self, rec, same, past, by_id):
        dlg = tk.Toplevel(self.master)
        dlg.title("Duplicate in this cycle")
        dlg.geometry("760x560")
        dlg.transient(self.master)
        dlg.grab_set()

        ttk.Label(dlg,
                  text="Warning: could be a duplicate or duplicate record exists.",
                  font=("Segoe UI", 13, "bold"), foreground="#b00020",
                  wraplength=720).pack(anchor="w", padx=14, pady=(14, 4))
        ttk.Label(dlg,
                  text=(f"A matching record already exists in "
                        f"{cycle_label(NEW_CYCLE)} (the current drive). "
                        f"Review before saving."),
                  wraplength=720).pack(anchor="w", padx=14)

        ttk.Label(dlg, text="Same-cycle match(es) - this blocks the save:",
                  font=("Segoe UI", 10, "bold"), foreground="#b00020").pack(
                      anchor="w", padx=14, pady=(10, 2))
        self._matches_table(dlg, same, by_id, height=5)

        if past:
            ttk.Label(dlg, text="Past-cycle history (informational only):",
                      font=("Segoe UI", 10, "bold"), foreground="#555").pack(
                          anchor="w", padx=14, pady=(8, 2))
            self._matches_table(dlg, past, by_id, height=4)

        ttk.Label(dlg, text=(
            f"New entry: {rec.given_name} {rec.family_name}  |  "
            f"father: {rec.father_name or '-'}  |  "
            f"DOB: {rec.date_of_birth.strftime('%d-%m-%Y') if rec.date_of_birth else '-'}  |  "
            f"{cycle_label(rec.cycle)}"),
            foreground="#333", wraplength=720).pack(anchor="w", padx=14, pady=(8, 0))

        bfrm = ttk.Frame(dlg); bfrm.pack(pady=14)

        def cancel():
            dlg.destroy()
            self.status.set("Save cancelled - same-cycle duplicate, not stored.")

        def register_anyway():
            if messagebox.askyesno("Confirm",
                    "Save as a NEW, distinct person in this cycle?\n"
                    "Confirm it is not one of the same-cycle records shown."):
                dlg.destroy()
                self._commit(rec)
                messagebox.showinfo("Saved", "Registered as a new record (override).")
                self.status.set(
                    f"Saved with override. {len(self.new_records)} new record(s) this session.")
                self.clear_form()

        ttk.Button(bfrm, text="Cancel (it's a duplicate)", command=cancel).pack(side="left", padx=8)
        ttk.Button(bfrm, text="Register anyway (not a duplicate)",
                   command=register_anyway).pack(side="left", padx=8)

    def _matches_table(self, parent, matches, by_id, height):
        cols = ("score", "verdict", "name", "father", "dob", "cycle", "why")
        tree = ttk.Treeview(parent, columns=cols, show="headings", height=height)
        widths = {"score":55,"verdict":75,"name":140,"father":110,"dob":90,"cycle":140,"why":130}
        for c in cols:
            tree.heading(c, text=c.capitalize())
            tree.column(c, width=widths[c], anchor="w")
        tree.pack(fill="x", padx=14)
        for m in sorted(matches, key=lambda x: x.score, reverse=True):
            o = by_id.get(m.id_b)
            if not o: continue
            why = ", ".join(f"{k} {v:.2f}" for k, v in m.top_signals(2))
            tree.insert("", "end", values=(
                f"{m.score:.2f}", m.verdict,
                f"{o.given_name or ''} {o.family_name or ''}".strip(),
                o.father_name or "",
                o.date_of_birth.strftime("%d-%m-%Y") if o.date_of_birth else "",
                cycle_label(o.cycle), why))

    def clear_form(self):
        for e in self.fields.values():
            e.delete(0, "end")
        self.gender.set("MALE")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", required=True,
                    help="Path to dedup_test_records.csv (has cycles 1-3).")
    args = ap.parse_args()
    if not os.path.exists(args.records):
        print("File not found:", args.records); sys.exit(1)
    root = tk.Tk()
    RegistrationApp(root, args.records)
    root.mainloop()


if __name__ == "__main__":
    main()