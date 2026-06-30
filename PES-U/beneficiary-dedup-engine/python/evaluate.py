"""
evaluate.py   —  benchmark/dev tool (NOT part of the Dart package)

Runs the reference pipeline over dedup_test_records.csv and scores it against
dedup_ground_truth.csv. Reports precision / recall / F1 overall, per duplicate
TYPE, and per DIFFICULTY, against the benchmarks in dedup_test_summary.json.

Usage:
    python evaluate.py --records dedup_test/dedup_test_records.csv \
                       --truth   dedup_test/dedup_ground_truth.csv
"""

import csv
import argparse
import time
from typing import Dict, List, Set, FrozenSet

from digit_dedup_engine import load_records, run_batch
from models.dedup_result import DUPLICATE, REVIEW


def load_ground_truth(path: str):
    """Return (true_pairs set of frozenset, meta dict keyed by frozenset)."""
    true_pairs: Set[FrozenSet] = set()
    meta: Dict[FrozenSet, dict] = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            pair = frozenset([row["original_id"].strip(), row["duplicate_id"].strip()])
            true_pairs.add(pair)
            meta[pair] = {
                "type": (row.get("type") or "").strip(),
                "difficulty": (row.get("difficulty") or "").strip(),
            }
    return true_pairs, meta


def evaluate(results, true_pairs, meta, count_review_as_positive=True):
    positive = {DUPLICATE, REVIEW} if count_review_as_positive else {DUPLICATE}

    flagged: Set[FrozenSet] = set()
    flagged_score: Dict[FrozenSet, float] = {}
    for r in results:
        if r.verdict in positive:
            pair = frozenset([r.id_a, r.id_b])
            flagged.add(pair)
            flagged_score[pair] = r.score

    # Overall
    tp = len(true_pairs & flagged)
    fn = len(true_pairs - flagged)
    fp = len(flagged - true_pairs)

    def prf(tp, fp, fn):
        p = tp / (tp + fp) if (tp + fp) else 0.0
        r = tp / (tp + fn) if (tp + fn) else 0.0
        f = 2 * p * r / (p + r) if (p + r) else 0.0
        return p, r, f

    overall = prf(tp, fp, fn)

    # Per-type and per-difficulty recall (precision is global only — FPs have no type)
    by_type: Dict[str, List[int]] = {}     # [found, total]
    by_diff: Dict[str, List[int]] = {}
    for pair in true_pairs:
        m = meta.get(pair, {})
        ty = m.get("type", "?")
        di = m.get("difficulty", "?")
        found = 1 if pair in flagged else 0
        by_type.setdefault(ty, [0, 0])
        by_diff.setdefault(di, [0, 0])
        by_type[ty][0] += found; by_type[ty][1] += 1
        by_diff[di][0] += found; by_diff[di][1] += 1

    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": overall[0], "recall": overall[1], "f1": overall[2],
        "by_type": by_type, "by_diff": by_diff,
    }


def print_report(m, label):
    print("\n" + "=" * 56)
    print("  " + label)
    print("=" * 56)
    print("  Precision: %.3f   Recall: %.3f   F1: %.3f"
          % (m["precision"], m["recall"], m["f1"]))
    print("  TP=%d  FP=%d  FN=%d" % (m["tp"], m["fp"], m["fn"]))
    print("  -- Recall by difficulty --")
    for di in ("EASY", "MEDIUM", "HARD"):
        if di in m["by_diff"]:
            f, t = m["by_diff"][di]
            print("     %-7s %4d/%-4d  %.3f" % (di, f, t, f / t if t else 0))
    print("  -- Recall by type --")
    for ty in sorted(m["by_type"], key=lambda k: -m["by_type"][k][1]):
        f, t = m["by_type"][ty]
        print("     %-20s %4d/%-4d  %.3f" % (ty, f, t, f / t if t else 0))
    print("=" * 56)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", default="dedup_test/dedup_test_records.csv")
    ap.add_argument("--truth",   default="dedup_test/dedup_ground_truth.csv")
    args = ap.parse_args()

    t0 = time.perf_counter()
    records = load_records(args.records)
    print("Loaded %d records" % len(records))
    true_pairs, meta = load_ground_truth(args.truth)
    print("Loaded %d ground-truth pairs" % len(true_pairs))

    results = run_batch(records, verbose=True)
    dt = time.perf_counter() - t0

    m_dup = evaluate(results, true_pairs, meta, count_review_as_positive=False)
    print_report(m_dup, "DUPLICATE verdict only")

    m_rev = evaluate(results, true_pairs, meta, count_review_as_positive=True)
    print_report(m_rev, "DUPLICATE + REVIEW (recommended for warning UX)")

    print("\nTotal time: %.1fs" % dt)


if __name__ == "__main__":
    main()
