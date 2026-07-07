"""
analyze_fp.py  —  Diagnose WHY the pipeline produces false positives.

Runs the full batch pipeline, finds every pair flagged as DUPLICATE that is NOT
in the ground truth, and buckets those false positives by their likely cause so
we can see the dominant pattern before changing any scoring.

Buckets (a pair can land in several):
  SIBLING_LIKE     same father + same boundary + close GPS, DIFFERENT given name
  SAME_HOUSE_DIFF  very close GPS (<50m) but given-name similarity < 0.6
  COMMON_NAME_YEAR near-identical given name + same birth year, weak elsewhere
  FATHER_CARRIED   father score high but given name weak (father dragging it up)
  GEO_CARRIED      geo high but names weak (geo dragging it up)
  DOB_SWAP_ONLY    strong dob + weak names
  OTHER            none of the above

Also prints, for each bucket, the average per-feature scores, and dumps a sample
of real pairs so you can eyeball them.

Usage:
  python analyze_fp.py --records <dedup_test_records.csv> --truth <dedup_ground_truth.csv>
  optional:  --sample 8   (rows to print per bucket)   --limit 0 (score cap)
"""

import argparse
import csv
from collections import defaultdict

from digit_dedup_engine import load_records
from blocking_strategy import build_candidate_pairs
from matching_service import score_pair, DEFAULT_WEIGHTS, THRESHOLDS
from models.dedup_result import DUPLICATE


def load_truth(path):
    truth = set()
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            truth.add(frozenset([row["original_id"].strip(),
                                 row["duplicate_id"].strip()]))
    return truth


def classify(a, b, feat):
    """Return the list of buckets a false-positive pair falls into."""
    tags = []
    given = feat.get("given_jw", 0.0)
    father = feat.get("father_jw", 0.0)
    dob = feat.get("dob", 0.0)
    geo = feat.get("geo", 0.0)
    household = feat.get("household", 0.0)
    same_boundary = (a.boundary_code and a.boundary_code == b.boundary_code)

    # Near-identical on the strong fields but not in truth -> very likely a REAL
    # duplicate the ground truth simply doesn't label (accidental lookalike).
    if given >= 0.9 and father >= 0.9 and dob >= 0.9:
        tags.append("LOOKALIKE_MAYBE_REAL")

    if father >= 0.85 and same_boundary and geo >= 0.5 and given < 0.75:
        tags.append("SIBLING_LIKE")
    if household >= 0.9 and given < 0.6:
        tags.append("SAME_HOUSE_DIFF")
    if given >= 0.85 and dob >= 0.9 and father < 0.5 and geo < 0.5:
        tags.append("COMMON_NAME_YEAR")
    if father >= 0.85 and given < 0.6:
        tags.append("FATHER_CARRIED")
    if geo >= 0.85 and given < 0.6 and father < 0.6:
        tags.append("GEO_CARRIED")
    if dob >= 0.9 and given < 0.5 and father < 0.5:
        tags.append("DOB_SWAP_ONLY")
    if not tags:
        tags.append("OTHER")
    return tags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", required=True)
    ap.add_argument("--truth", required=True)
    ap.add_argument("--sample", type=int, default=6)
    args = ap.parse_args()

    print("Loading records...")
    records = load_records(args.records)
    truth = load_truth(args.truth)
    print(f"  {len(records):,} records, {len(truth):,} truth pairs")

    print("Blocking...")
    candidates = build_candidate_pairs(records)
    print(f"  {len(candidates):,} candidate pairs")

    print("Scoring + collecting false positives...")
    buckets = defaultdict(list)                 # bucket -> list of (a,b,result)
    feat_sums = defaultdict(lambda: defaultdict(float))
    feat_counts = defaultdict(int)
    n_fp = 0
    n_flagged = 0

    for (i, j) in candidates:
        a, b = records[i], records[j]
        res = score_pair(a, b)
        if res.verdict != DUPLICATE:
            continue
        n_flagged += 1
        pair = frozenset([a.individual_id, b.individual_id])
        if pair in truth:
            continue  # true positive, ignore
        n_fp += 1
        for tag in classify(a, b, res.feature_scores):
            buckets[tag].append((a, b, res))
            feat_counts[tag] += 1
            for k, v in res.feature_scores.items():
                feat_sums[tag][k] += v

    print("\n" + "=" * 64)
    print(f"  FALSE-POSITIVE BREAKDOWN  (flagged={n_flagged:,}, "
          f"false positives={n_fp:,})")
    print("=" * 64)

    order = sorted(buckets, key=lambda t: -len(buckets[t]))
    key_feats = ["given_jw", "father_jw", "family_jw", "dob", "geo", "household"]
    for tag in order:
        rows = buckets[tag]
        share = 100.0 * len(rows) / n_fp if n_fp else 0
        print(f"\n[{tag}]  {len(rows):,} pairs  ({share:.1f}% of FPs)")
        cnt = feat_counts[tag]
        avgs = "  ".join(f"{k}={feat_sums[tag][k]/cnt:.2f}" for k in key_feats)
        print("   avg:", avgs)
        for (a, b, res) in rows[:args.sample]:
            print(f"     {res.score:.2f} | "
                  f"{(a.given_name or ''):<12} {(a.family_name or ''):<10} "
                  f"f:{(a.father_name or '-'):<10} dob:{a.date_of_birth} "
                  f"cyc:{a.cycle}")
            print(f"          | "
                  f"{(b.given_name or ''):<12} {(b.family_name or ''):<10} "
                  f"f:{(b.father_name or '-'):<10} dob:{b.date_of_birth} "
                  f"cyc:{b.cycle}")

    print("\n" + "=" * 64)
    print("  READING THIS:")
    print("  The biggest bucket is where your precision is bleeding.")
    print("  SIBLING_LIKE / SAME_HOUSE_DIFF  -> need a discriminating rule,")
    print("                                     not more metrics.")
    print("  COMMON_NAME_YEAR                -> need stricter multi-signal")
    print("                                     agreement or threshold tuning.")
    print("  FATHER_CARRIED / GEO_CARRIED    -> one strong feature is dragging")
    print("                                     weak names over the line;")
    print("                                     rebalance weights.")
    print("=" * 64)


if __name__ == "__main__":
    main()