"""
register_ui.py  —  Offline field-worker registration UI with duplicate warning.

Cycles 1-3 are preloaded as the existing population. The worker enters a new
cycle-4 record; on Save, the real dedup engine checks it against the existing
population. If any potential duplicate is found, the save is BLOCKED and a
warning + the candidate matches are shown for review. The worker must explicitly
decide (Register anyway / Cancel) before anything is stored.

Fully offline: pure Python standard library (tkinter). No network, no pip.

Run:
    python register_ui.py --records <path to dedup_test_records.csv>

The engine modules (digit_dedup_engine.py etc.) must be in the same folder.
"""

import argparse
import csv
import os
import sys
import uuid
from datetime import datetime, date

import tkinter as tk
from tkinter import ttk, messagebox

# Engine imports (same folder)
from digit_dedup_engine import load_records, check_for_duplicates
from models.candidate_pair import Beneficiary
from models.dedup_result import DUPLICATE, REVIEW

# Only compare a new record against records from these cycles.
EXISTING_CYCLES = {"1", "2", "3"}
NEW_CYCLE = "4"

DATE_INPUT_FORMATS = ["%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"]


# ── Blocking for a single new record ───────────────────────────────────────
# check_for_duplicates() compares against every existing record. For tens of
# thousands that is still workable, but we pre-filter to the plausible ones so
# the UI stays instant — this mirrors how the real on-device app would issue a
# narrow SQLite query rather than scanning the whole table.
from algorithms.double_metaphone import metaphone_code


def _candidate_subset(new_rec, existing):
    """Return existing records worth scoring against the new one."""
    code = metaphone_code(new_rec.norm_given) if new_rec.norm_given else ""
    year = new_rec.dob_year
    subset = []
    for r in existing:
        # same boundary, OR same given-name phonetic code, OR same birth year
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
        master.title("Beneficiary Registration — Cycle 4 (Offline)")
        master.geometry("640x720")

        self.existing = []       # cycles 1-3
        self.new_records = []    # saved this session

        self._build_form()
        self._load_existing()

    # ── data ──
    def _load_existing(self):
        self.status.set("Loading existing records (cycles 1-3)…")
        self.master.update_idletasks()
        try:
            all_recs = load_records(self.records_path)
        except Exception as e:
            messagebox.showerror("Load error", f"Could not load records:\n{e}")
            self.status.set("Load failed.")
            return
        self.existing = [r for r in all_recs
                         if (r.cycle or "").strip() in EXISTING_CYCLES]
        self.status.set(
            f"Ready. {len(self.existing):,} existing records (cycles 1-3) loaded. "
            f"Entering cycle {NEW_CYCLE}."
        )

    # ── UI layout ──
    def _build_form(self):
        pad = {"padx": 8, "pady": 4}
        frm = ttk.Frame(self.master, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="New Cycle 4 Registration",
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
            e = ttk.Entry(frm, width=40)
            e.grid(row=r, column=1, sticky="w", **pad)
            self.fields[key] = e
            r += 1

        # Gender radio
        ttk.Label(frm, text="Gender *").grid(row=r, column=0, sticky="w", **pad)
        self.gender = tk.StringVar(value="MALE")
        gfrm = ttk.Frame(frm)
        gfrm.grid(row=r, column=1, sticky="w", **pad)
        ttk.Radiobutton(gfrm, text="Male", variable=self.gender,
                        value="MALE").pack(side="left")
        ttk.Radiobutton(gfrm, text="Female", variable=self.gender,
                        value="FEMALE").pack(side="left")
        r += 1

        btns = ttk.Frame(frm)
        btns.grid(row=r, column=0, columnspan=2, pady=14)
        ttk.Button(btns, text="Check & Save", command=self.on_save).pack(side="left", padx=6)
        ttk.Button(btns, text="Clear", command=self.clear_form).pack(side="left", padx=6)
        r += 1

        self.status = tk.StringVar(value="Starting…")
        ttk.Label(frm, textvariable=self.status, foreground="#555",
                  wraplength=580, justify="left").grid(
                      row=r, column=0, columnspan=2, sticky="w", pady=(6, 0))

    # ── build a Beneficiary from the form ──
    def _form_to_record(self):
        def val(k): return self.fields[k].get().strip()

        dob = _parse_date(val("date_of_birth"))
        if dob == "INVALID":
            messagebox.showwarning("Invalid date",
                                   "Date of birth must be DD-MM-YYYY.")
            return None

        def fnum(k):
            try:
                return float(val(k)) if val(k) else None
            except ValueError:
                return None

        # required-field check
        missing = [lbl for key, lbl in [
            ("given_name", "Given name"), ("family_name", "Family name"),
            ("date_of_birth", "Date of birth"), ("boundary_code", "Boundary code")]
            if not val(key)]
        if missing:
            messagebox.showwarning("Missing fields",
                                   "Please fill: " + ", ".join(missing))
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
            latitude=fnum("latitude"),
            longitude=fnum("longitude"),
            location_accuracy=None,
            mobile_number=val("mobile_number") or None,
            cycle=NEW_CYCLE,
        )
        rec.normalize()
        return rec

    # ── save flow ──
    def on_save(self):
        rec = self._form_to_record()
        if rec is None:
            return

        self.status.set("Checking for duplicates…")
        self.master.update_idletasks()

        pool = self._candidate_pool(rec)
        matches = check_for_duplicates(rec, pool)
        strong = [m for m in matches if m.verdict in (DUPLICATE, REVIEW)]

        if not strong:
            self._commit(rec)
            messagebox.showinfo("Saved",
                                "No duplicate found. Record saved.")
            self.status.set(
                f"Saved. {len(self.new_records)} new cycle-4 record(s) this session.")
            self.clear_form()
            return

        # BLOCK: show warning + candidates, require explicit decision
        self._show_duplicate_dialog(rec, strong, pool)

    def _candidate_pool(self, rec):
        # existing cycles 1-3 plus anything already saved this session
        base = _candidate_subset(rec, self.existing)
        base.extend(self.new_records)
        return base

    def _commit(self, rec):
        self.new_records.append(rec)

    # ── duplicate review dialog ──
    def _show_duplicate_dialog(self, rec, matches, pool):
        by_id = {r.individual_id: r for r in pool}

        dlg = tk.Toplevel(self.master)
        dlg.title("⚠ Possible Duplicate")
        dlg.geometry("720x520")
        dlg.transient(self.master)
        dlg.grab_set()  # modal — blocks the main window

        ttk.Label(dlg,
                  text="Warning: could be a duplicate or duplicate record exists.",
                  font=("Segoe UI", 13, "bold"),
                  foreground="#b00020", wraplength=680).pack(
                      anchor="w", padx=14, pady=(14, 6))
        ttk.Label(dlg,
                  text="Review the potential match(es) below before deciding.",
                  wraplength=680).pack(anchor="w", padx=14)

        cols = ("score", "verdict", "name", "father", "dob", "boundary", "cycle", "why")
        tree = ttk.Treeview(dlg, columns=cols, show="headings", height=8)
        widths = {"score": 60, "verdict": 80, "name": 130, "father": 100,
                  "dob": 90, "boundary": 90, "cycle": 45, "why": 120}
        for c in cols:
            tree.heading(c, text=c.capitalize())
            tree.column(c, width=widths[c], anchor="w")
        tree.pack(fill="both", expand=True, padx=14, pady=10)

        for m in matches:
            other = by_id.get(m.id_b)
            if other is None:
                continue
            top = ", ".join(f"{k} {v:.2f}" for k, v in m.top_signals(2))
            tree.insert("", "end", values=(
                f"{m.score:.2f}", m.verdict,
                f"{other.given_name or ''} {other.family_name or ''}".strip(),
                other.father_name or "",
                other.date_of_birth.strftime("%d-%m-%Y") if other.date_of_birth else "",
                (other.boundary_code or "")[-12:],
                other.cycle or "",
                top,
            ))

        # New record summary
        ttk.Label(dlg, text=(
            f"New entry: {rec.given_name} {rec.family_name}  |  "
            f"father: {rec.father_name or '-'}  |  "
            f"DOB: {rec.date_of_birth.strftime('%d-%m-%Y') if rec.date_of_birth else '-'}  |  "
            f"cycle {rec.cycle}"),
            foreground="#333", wraplength=680).pack(anchor="w", padx=14)

        btns = ttk.Frame(dlg)
        btns.pack(pady=14)

        def cancel():
            dlg.destroy()
            self.status.set("Save cancelled — treated as duplicate, not stored.")

        def register_anyway():
            if messagebox.askyesno(
                    "Confirm",
                    "You are about to save this as a NEW, distinct person.\n"
                    "Confirm it is not one of the records shown?"):
                dlg.destroy()
                self._commit(rec)
                messagebox.showinfo("Saved",
                                    "Registered as a new record (override).")
                self.status.set(
                    f"Saved with override. "
                    f"{len(self.new_records)} new record(s) this session.")
                self.clear_form()

        ttk.Button(btns, text="Cancel (it's a duplicate)",
                   command=cancel).pack(side="left", padx=8)
        ttk.Button(btns, text="Register anyway (not a duplicate)",
                   command=register_anyway).pack(side="left", padx=8)

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
        print("File not found:", args.records)
        sys.exit(1)

    root = tk.Tk()
    RegistrationApp(root, args.records)
    root.mainloop()


if __name__ == "__main__":
    main()