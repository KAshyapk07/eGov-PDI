"""
dashboard.py  —  Offline dedup dashboard (two tabs).

TAB 1 — Register
    Enter a new Cycle 3 record; on save the engine checks it against existing
    records. Same-cycle matches BLOCK and must be reviewed; past-cycle matches
    are shown as history. Saved entries (clean saves and "register anyway"
    overrides) are appended to a SEPARATE csv, cycle3_new_registrations.csv,
    so they survive restarts and never touch the original dataset.

TAB 2 — Analyze
    Runs the full batch pipeline once (progress bar), caches the result to
    dedup_analysis_cache.json so it is instant on reopen. Shows:
      - total records
      - ground-truth duplicate count
      - duplicates the model found (DUPLICATE verdict), and how many are in GT
      - a table of the highest-confidence model finds, top 10 with a
        "Load more" button up to 40.

Fully offline: pure Python standard library (tkinter). No network, no pip.

Run:
    python dashboard.py --records <dedup_test_records.csv> --truth <dedup_ground_truth.csv>
"""

import argparse
import csv
import hashlib
import json
import os
import sys
import threading
import uuid
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox

from digit_dedup_engine import load_records, check_for_duplicates
from blocking_strategy import build_candidate_pairs
from matching_service import score_pair
from models.candidate_pair import Beneficiary
from models.dedup_result import DUPLICATE, REVIEW
from algorithms.double_metaphone import metaphone_code

# ── Cycle model ────────────────────────────────────────────────────────────
NEW_CYCLE = "3"
PAST_CYCLES = {"1", "2"}
EXISTING_CYCLES = {"1", "2", "3"}
CYCLE_LABELS = {"1": "Cycle 1", "2": "Cycle 2", "3": "Cycle 3"}

DATE_INPUT_FORMATS = ["%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"]

NEW_REG_FILE = "cycle3_new_registrations.csv"
CACHE_FILE = "dedup_analysis_cache.json"
CACHE_VERSION = "2"  # bump when the analysis computation changes (invalidates old caches)

NEW_REG_HEADER = [
    "individual_client_ref", "given_name", "family_name", "gender",
    "date_of_birth", "father_name", "husband_name", "mobile_number",
    "boundary_code", "latitude", "longitude", "location_accuracy",
    "locality_name", "tenant_id", "cycle", "is_duplicate", "saved_at", "override",
]

MAX_TABLE = 40
PAGE = 10


def cycle_label(c):
    c = (c or "").strip()
    return CYCLE_LABELS.get(c, f"Cycle {c}" if c else "Cycle ?")


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


def _candidate_subset(new_rec, existing):
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


def _file_signature(path):
    """Small stable signature (size + mtime) to invalidate the cache if data changes."""
    st = os.stat(path)
    raw = f"{path}:{st.st_size}:{int(st.st_mtime)}"
    return hashlib.md5(raw.encode()).hexdigest()


class Dashboard:
    def __init__(self, master, records_path, truth_path):
        self.master = master
        self.records_path = records_path
        self.truth_path = truth_path
        master.title("Beneficiary Dedup Dashboard (Offline)")
        master.geometry("900x740")

        self.existing = []
        self.new_records = []            # in-memory mirror of this session's saves
        self.records_by_id = {}          # for analyze tab display

        nb = ttk.Notebook(master)
        nb.pack(fill="both", expand=True)
        self.tab_reg = ttk.Frame(nb)
        self.tab_an = ttk.Frame(nb)
        nb.add(self.tab_reg, text="  Register  ")
        nb.add(self.tab_an, text="  Analyze  ")

        self._build_register_tab()
        self._build_analyze_tab()
        self._load_existing()

    # ═══════════════════════ shared data ═══════════════════════
    def _load_existing(self):
        self.reg_status.set("Loading existing records (cycles 1-3)...")
        self.master.update_idletasks()
        try:
            all_recs = load_records(self.records_path)
        except Exception as e:
            messagebox.showerror("Load error", f"Could not load records:\n{e}")
            return
        self.existing = [r for r in all_recs
                         if (r.cycle or "").strip() in EXISTING_CYCLES]
        self.records_by_id = {r.individual_id: r for r in all_recs}
        # Load any previously-saved new registrations back in (persistence)
        self._load_saved_registrations()
        n3 = sum(1 for r in self.existing if (r.cycle or "").strip() == NEW_CYCLE)
        self.reg_status.set(
            f"Ready. {len(self.existing):,} existing records "
            f"({n3:,} in {cycle_label(NEW_CYCLE)}). "
            f"{len(self.new_records)} saved this/previous sessions.")

    def _load_saved_registrations(self):
        if not os.path.exists(NEW_REG_FILE):
            return
        try:
            saved = load_records(NEW_REG_FILE)
            for r in saved:
                self.existing.append(r)
                self.new_records.append(r)
        except Exception:
            pass  # ignore a malformed/partial file

    # ═══════════════════════ TAB 1: REGISTER ═══════════════════════
    def _build_register_tab(self):
        pad = {"padx": 8, "pady": 4}
        frm = ttk.Frame(self.tab_reg, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text=f"New Registration - {cycle_label(NEW_CYCLE)}",
                  font=("Segoe UI", 14, "bold")).grid(
                      row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.fields = {}
        rows = [
            ("given_name", "Given name *"), ("family_name", "Family name *"),
            ("father_name", "Father's name"), ("husband_name", "Husband's name"),
            ("date_of_birth", "Date of birth (DD-MM-YYYY) *"),
            ("mobile_number", "Mobile number"), ("boundary_code", "Boundary code *"),
            ("locality_name", "Locality name"),
            ("latitude", "Latitude (optional)"), ("longitude", "Longitude (optional)"),
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

        self.reg_status = tk.StringVar(value="Starting...")
        ttk.Label(frm, textvariable=self.reg_status, foreground="#555",
                  wraplength=820, justify="left").grid(
                      row=r, column=0, columnspan=2, sticky="w", pady=(6, 0))
        r += 1
        ttk.Label(frm, text=f"Saved entries are appended to {NEW_REG_FILE}",
                  foreground="#888").grid(row=r, column=0, columnspan=2, sticky="w")

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
            ("given_name", "Given name"), ("family_name", "Family name"),
            ("date_of_birth", "Date of birth"), ("boundary_code", "Boundary code")]
            if not val(key)]
        if missing:
            messagebox.showwarning("Missing fields", "Please fill: " + ", ".join(missing))
            return None
        rec = Beneficiary(
            individual_id=str(uuid.uuid4()),
            given_name=val("given_name") or None, family_name=val("family_name") or None,
            father_name=val("father_name") or None, husband_name=val("husband_name") or None,
            gender=self.gender.get(), date_of_birth=dob,
            boundary_code=val("boundary_code") or None, locality_name=val("locality_name") or None,
            latitude=fnum("latitude"), longitude=fnum("longitude"), location_accuracy=None,
            mobile_number=val("mobile_number") or None, cycle=NEW_CYCLE)
        rec.normalize()
        return rec

    def on_save(self):
        rec = self._form_to_record()
        if rec is None:
            return
        self.reg_status.set("Checking...")
        self.master.update_idletasks()

        pool = _candidate_subset(rec, self.existing)
        by_id = {r.individual_id: r for r in pool}
        matches = check_for_duplicates(rec, pool)
        strong = [m for m in matches if m.verdict in (DUPLICATE, REVIEW)]

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
            self._show_duplicate_dialog(rec, same_cycle, past_cycle, by_id)
        else:
            self._commit(rec, override=False)
            if past_cycle:
                self._show_history_info(rec, past_cycle, by_id)
            else:
                messagebox.showinfo("Saved", "No duplicate found. Record saved.")
            self.reg_status.set(
                f"Saved to {cycle_label(NEW_CYCLE)}. "
                f"{len(self.new_records)} new record(s) total.")
            self.clear_form()

    def _commit(self, rec, override):
        self.new_records.append(rec)
        self.existing.append(rec)      # so later entries are checked against it
        self._append_to_csv(rec, override)

    def _append_to_csv(self, rec, override):
        exists = os.path.exists(NEW_REG_FILE)
        with open(NEW_REG_FILE, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=NEW_REG_HEADER)
            if not exists:
                w.writeheader()
            w.writerow({
                "individual_client_ref": rec.individual_id,
                "given_name": rec.given_name or "", "family_name": rec.family_name or "",
                "gender": rec.gender or "",
                "date_of_birth": rec.date_of_birth.strftime("%d-%m-%Y") if rec.date_of_birth else "",
                "father_name": rec.father_name or "", "husband_name": rec.husband_name or "",
                "mobile_number": rec.mobile_number or "",
                "boundary_code": rec.boundary_code or "",
                "latitude": rec.latitude if rec.latitude is not None else "",
                "longitude": rec.longitude if rec.longitude is not None else "",
                "location_accuracy": rec.location_accuracy if rec.location_accuracy is not None else "",
                "locality_name": rec.locality_name or "", "tenant_id": "mz",
                "cycle": rec.cycle or NEW_CYCLE, "is_duplicate": "FALSE",
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "override": "TRUE" if override else "FALSE",
            })

    def _show_history_info(self, rec, past, by_id):
        lines = []
        for m in sorted(past, key=lambda x: x.score, reverse=True)[:6]:
            o = by_id.get(m.id_b)
            if not o: continue
            lines.append(f"- {cycle_label(o.cycle)}: {o.given_name} {o.family_name} (match {m.score:.2f})")
        messagebox.showinfo("Saved - past-cycle history found",
            "Record saved to this drive.\n\n"
            "This person also appears in earlier cycles (expected):\n\n" + "\n".join(lines))

    def _show_duplicate_dialog(self, rec, same, past, by_id):
        dlg = tk.Toplevel(self.master)
        dlg.title("Duplicate in this cycle")
        dlg.geometry("780x560"); dlg.transient(self.master); dlg.grab_set()
        ttk.Label(dlg, text="Warning: could be a duplicate or duplicate record exists.",
                  font=("Segoe UI", 13, "bold"), foreground="#b00020",
                  wraplength=740).pack(anchor="w", padx=14, pady=(14, 4))
        ttk.Label(dlg, text=(f"A matching record already exists in {cycle_label(NEW_CYCLE)}. "
                             f"Review before saving."), wraplength=740).pack(anchor="w", padx=14)
        ttk.Label(dlg, text="Same-cycle match(es) - this blocks the save:",
                  font=("Segoe UI", 10, "bold"), foreground="#b00020").pack(anchor="w", padx=14, pady=(10, 2))
        self._matches_table(dlg, same, by_id, height=5)
        if past:
            ttk.Label(dlg, text="Past-cycle history (informational only):",
                      font=("Segoe UI", 10, "bold"), foreground="#555").pack(anchor="w", padx=14, pady=(8, 2))
            self._matches_table(dlg, past, by_id, height=4)

        bfrm = ttk.Frame(dlg); bfrm.pack(pady=14)
        def cancel():
            dlg.destroy()
            self.reg_status.set("Save cancelled - same-cycle duplicate, not stored.")
        def register_anyway():
            if messagebox.askyesno("Confirm",
                    "Save as a NEW, distinct person in this cycle?\n"
                    "Confirm it is not one of the same-cycle records shown."):
                dlg.destroy()
                self._commit(rec, override=True)
                messagebox.showinfo("Saved", "Registered as a new record (override).")
                self.reg_status.set(f"Saved with override. {len(self.new_records)} new record(s) total.")
                self.clear_form()
        ttk.Button(bfrm, text="Cancel (it's a duplicate)", command=cancel).pack(side="left", padx=8)
        ttk.Button(bfrm, text="Register anyway (not a duplicate)", command=register_anyway).pack(side="left", padx=8)

    def _matches_table(self, parent, matches, by_id, height):
        cols = ("score", "verdict", "name", "father", "dob", "cycle", "why")
        tree = ttk.Treeview(parent, columns=cols, show="headings", height=height)
        widths = {"score":55,"verdict":75,"name":150,"father":110,"dob":90,"cycle":70,"why":150}
        for c in cols:
            tree.heading(c, text=c.capitalize()); tree.column(c, width=widths[c], anchor="w")
        tree.pack(fill="x", padx=14)
        for m in sorted(matches, key=lambda x: x.score, reverse=True):
            o = by_id.get(m.id_b)
            if not o: continue
            why = ", ".join(f"{k} {v:.2f}" for k, v in m.top_signals(2))
            tree.insert("", "end", values=(f"{m.score:.2f}", m.verdict,
                f"{o.given_name or ''} {o.family_name or ''}".strip(), o.father_name or "",
                o.date_of_birth.strftime("%d-%m-%Y") if o.date_of_birth else "",
                cycle_label(o.cycle), why))

    def clear_form(self):
        for e in self.fields.values():
            e.delete(0, "end")
        self.gender.set("MALE")

    # ═══════════════════════ TAB 2: ANALYZE ═══════════════════════
    def _build_analyze_tab(self):
        frm = ttk.Frame(self.tab_an, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Dataset Analysis",
                  font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 8))

        self.an_run_btn = ttk.Button(frm, text="Run analysis", command=self._run_analysis_clicked)
        self.an_run_btn.pack(anchor="w")
        self.an_progress = ttk.Progressbar(frm, mode="indeterminate", length=300)
        self.an_status = tk.StringVar(value="Not run yet. Click 'Run analysis'. "
                                            "First run scores the whole dataset (~1-3 min); result is cached.")
        ttk.Label(frm, textvariable=self.an_status, foreground="#555",
                  wraplength=840, justify="left").pack(anchor="w", pady=(8, 4))

        # Stat cards
        self.stat_vars = {
            "total": tk.StringVar(value="-"),
            "gt": tk.StringVar(value="-"),
            "found": tk.StringVar(value="-"),
            "tp": tk.StringVar(value="-"),
        }
        cards = ttk.Frame(frm); cards.pack(fill="x", pady=8)
        self._stat_card(cards, "Total records", self.stat_vars["total"], 0)
        self._stat_card(cards, "Duplicates (ground truth)", self.stat_vars["gt"], 1)
        self._stat_card(cards, "Duplicates found (model)", self.stat_vars["found"], 2)
        self._stat_card(cards, "Found that are in GT", self.stat_vars["tp"], 3)

        ttk.Label(frm, text="Highest-confidence confirmed duplicates (found by model AND in ground truth):",
                  font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10, 4))

        cols = ("score", "name_a", "father_a", "dob_a", "cyc_a",
                "name_b", "father_b", "dob_b", "cyc_b")
        heads = {"score":"Score","name_a":"Name A","father_a":"Father A","dob_a":"DOB A","cyc_a":"Cyc A",
                 "name_b":"Name B","father_b":"Father B","dob_b":"DOB B","cyc_b":"Cyc B"}
        widths = {"score":55,"name_a":130,"father_a":95,"dob_a":85,"cyc_a":45,
                  "name_b":130,"father_b":95,"dob_b":85,"cyc_b":45}
        self.an_tree = ttk.Treeview(frm, columns=cols, show="headings", height=13)
        for c in cols:
            self.an_tree.heading(c, text=heads[c]); self.an_tree.column(c, width=widths[c], anchor="w")
        self.an_tree.pack(fill="both", expand=True, pady=4)

        self.load_more_btn = ttk.Button(frm, text="Load more", command=self._load_more, state="disabled")
        self.load_more_btn.pack(anchor="w", pady=6)

        self._top_pairs = []     # cached list of dicts
        self._shown = 0

    def _stat_card(self, parent, label, var, col):
        card = ttk.Frame(parent, relief="ridge", borderwidth=1, padding=10)
        card.grid(row=0, column=col, padx=6, sticky="ew")
        parent.columnconfigure(col, weight=1)
        ttk.Label(card, textvariable=var, font=("Segoe UI", 18, "bold")).pack()
        ttk.Label(card, text=label, foreground="#555").pack()

    def _run_analysis_clicked(self):
        self.an_run_btn.config(state="disabled")
        self.load_more_btn.config(state="disabled")
        self.an_progress.pack(anchor="w", pady=4)
        self.an_progress.start(12)
        self.an_status.set("Analyzing... (checking cache, else scoring all pairs)")
        # run in a thread so the UI stays responsive
        threading.Thread(target=self._run_analysis_worker, daemon=True).start()

    def _run_analysis_worker(self):
        try:
            result = self._compute_or_load_cache()
        except Exception as e:
            self.master.after(0, lambda: self._analysis_failed(str(e)))
            return
        self.master.after(0, lambda: self._analysis_done(result))

    def _compute_or_load_cache(self):
        sig = (CACHE_VERSION + "|" + _file_signature(self.records_path)
               + "|" + _file_signature(self.truth_path))
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, encoding="utf-8") as f:
                    cached = json.load(f)
                if cached.get("signature") == sig:
                    return cached
            except Exception:
                pass  # rebuild on any cache problem

        records = load_records(self.records_path)
        by_id = {r.individual_id: r for r in records}
        truth = set()
        with open(self.truth_path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                truth.add(frozenset([row["original_id"].strip(), row["duplicate_id"].strip()]))

        candidates = build_candidate_pairs(records)
        found = []
        for (i, j) in candidates:
            res = score_pair(records[i], records[j])
            if res.verdict == DUPLICATE:
                found.append(res)
        found.sort(key=lambda x: x.score, reverse=True)
        tp = sum(1 for r in found if frozenset([r.id_a, r.id_b]) in truth)

        # Table shows only TRUE POSITIVES: pairs the model flagged AND that are
        # in the ground truth. (found - true_positives are excluded here.)
        true_positive_pairs = [r for r in found
                               if frozenset([r.id_a, r.id_b]) in truth]

        def row_of(r):
            a, b = by_id.get(r.id_a), by_id.get(r.id_b)
            def d(x, attr, fmt=False):
                v = getattr(x, attr, None) if x else None
                if fmt and v: return v.strftime("%d-%m-%Y")
                return v or ""
            return {
                "score": round(r.score, 3),
                "name_a": f"{d(a,'given_name')} {d(a,'family_name')}".strip(),
                "father_a": d(a, "father_name"), "dob_a": d(a, "date_of_birth", True), "cyc_a": d(a, "cycle"),
                "name_b": f"{d(b,'given_name')} {d(b,'family_name')}".strip(),
                "father_b": d(b, "father_name"), "dob_b": d(b, "date_of_birth", True), "cyc_b": d(b, "cycle"),
            }
        top_pairs = [row_of(r) for r in true_positive_pairs[:MAX_TABLE]]

        result = {
            "signature": sig,
            "total": len(records),
            "gt": len(truth),
            "found": len(found),
            "tp": tp,
            "top_pairs": top_pairs,
        }
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(result, f)
        except Exception:
            pass
        return result

    def _analysis_failed(self, msg):
        self.an_progress.stop(); self.an_progress.pack_forget()
        self.an_run_btn.config(state="normal")
        self.an_status.set("Analysis failed: " + msg)

    def _analysis_done(self, result):
        self.an_progress.stop(); self.an_progress.pack_forget()
        self.an_run_btn.config(state="normal")
        self.stat_vars["total"].set(f"{result['total']:,}")
        self.stat_vars["gt"].set(f"{result['gt']:,}")
        self.stat_vars["found"].set(f"{result['found']:,}")
        self.stat_vars["tp"].set(f"{result['tp']:,}")
        self._top_pairs = result["top_pairs"]
        self._shown = 0
        for iid in self.an_tree.get_children():
            self.an_tree.delete(iid)
        self._load_more()
        self.an_status.set(
            f"Done. Model found {result['found']:,} duplicates "
            f"({result['tp']:,} confirmed in ground truth). "
            f"Table shows top {min(PAGE, len(self._top_pairs))} confirmed "
            f"(up to {MAX_TABLE}).")

    def _load_more(self):
        end = min(self._shown + PAGE, len(self._top_pairs))
        for p in self._top_pairs[self._shown:end]:
            self.an_tree.insert("", "end", values=(
                p["score"], p["name_a"], p["father_a"], p["dob_a"], p["cyc_a"],
                p["name_b"], p["father_b"], p["dob_b"], p["cyc_b"]))
        self._shown = end
        if self._shown >= len(self._top_pairs):
            self.load_more_btn.config(state="disabled")
        else:
            self.load_more_btn.config(state="normal")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", required=True)
    ap.add_argument("--truth", required=True)
    args = ap.parse_args()
    for p in (args.records, args.truth):
        if not os.path.exists(p):
            print("File not found:", p); sys.exit(1)
    root = tk.Tk()
    Dashboard(root, args.records, args.truth)
    root.mainloop()


if __name__ == "__main__":
    main()