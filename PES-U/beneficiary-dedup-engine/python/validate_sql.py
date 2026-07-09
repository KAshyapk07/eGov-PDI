"""
validate_sql.py  —  Phase 1 validation.

Runs the dedup engine against the SQL-loaded records and reports the same
metrics you got from CSV, so you can confirm the relational fetch produces
equivalent results. If you also have the CSV ground truth, it computes
precision/recall/F1; if not, it just reports totals + model finds.

Usage:
    set PGPASSWORD=your_password    (Windows)
    python validate_sql.py --truth <dedup_ground_truth.csv>

    (omit --truth to just see totals and duplicates found)
"""

import argparse
import csv
import os
import time

from sql_loader import load_records_from_sql
from blocking_strategy import build_candidate_pairs
from matching_service import score_pair
from models.dedup_result import DUPLICATE


def load_truth(path):
    truth = set()
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            truth.add(frozenset([row["original_id"].strip(),
                                 row["duplicate_id"].strip()]))
    return truth


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--truth", default=None,
                    help="Optional ground-truth CSV for precision/recall.")
    ap.add_argument("--password", default=None,
                    help="Postgres password (or set PGPASSWORD env var).")
    args = ap.parse_args()

    t0 = time.perf_counter()
    print("Fetching records from SQL...")
    records = load_records_from_sql(password=args.password)
    print(f"  Loaded {len(records):,} records")

    print("Blocking...")
    candidates = build_candidate_pairs(records)
    print(f"  {len(candidates):,} candidate pairs")

    print("Scoring...")
    found = []
    for (i, j) in candidates:
        res = score_pair(records[i], records[j])
        if res.verdict == DUPLICATE:
            found.append(res)
    dt = time.perf_counter() - t0

    print("\n" + "=" * 56)
    print("  PHASE 1 — SQL VALIDATION")
    print("=" * 56)
    print(f"  Records:          {len(records):,}")
    print(f"  Candidate pairs:  {len(candidates):,}")
    print(f"  Duplicates found: {len(found):,}  (DUPLICATE verdict)")

    if args.truth and os.path.exists(args.truth):
        truth = load_truth(args.truth)
        flagged = set(frozenset([r.id_a, r.id_b]) for r in found)
        tp = len(truth & flagged)
        fp = len(flagged - truth)
        fn = len(truth - flagged)
        p = tp / (tp + fp) if (tp + fp) else 0.0
        r = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) else 0.0
        print(f"  Ground-truth pairs: {len(truth):,}")
        print(f"  TP={tp:,}  FP={fp:,}  FN={fn:,}")
        print(f"  Precision: {p:.3f}   Recall: {r:.3f}   F1: {f1:.3f}")
    else:
        print("  (no --truth given; skipping precision/recall)")

    print(f"\n  Time: {dt:.1f}s")
    print("=" * 56)
    print("  Compare these numbers to your CSV run. They should match")
    print("  (same data, same engine, different source).")
    print("=" * 56)


if __name__ == "__main__":
    main()
