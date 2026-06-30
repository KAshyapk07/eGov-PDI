"""
dedup_engine.py   <->   lib/src/dedup_engine.dart

Main orchestrator. Ties blocking + scoring together.

Two public entry points mirror how the Dart package is used:

  check_for_duplicates(new_record, existing_records)
      -> ON-DEVICE path. One record being registered vs the local DB.
         This is what the Flutter app calls in real time. Returns the
         ranked list of likely matches for the warning UX.

  run_batch(records)
      -> SERVER/BENCHMARK path. All-pairs over a dataset for evaluation
         and weight tuning. Not used on-device.

Dart port note:
  - check_for_duplicates is the primary API surface (DedupEngine.checkForDuplicates).
  - run_batch is dev/benchmark only; you may omit it from the published package
    or guard it behind a separate dev entry point.
"""

from typing import List, Optional, Dict

from models.candidate_pair import Beneficiary
from models.dedup_result import DedupResult, CLEAR
from blocking_strategy import build_candidate_pairs
from matching_service import score_pair, DEFAULT_WEIGHTS, THRESHOLDS


def check_for_duplicates(
    new_record: Beneficiary,
    existing_records: List[Beneficiary],
    weights: Optional[Dict[str, float]] = None,
    thresholds: Optional[Dict[str, float]] = None,
    return_clear: bool = False,
) -> List[DedupResult]:
    """
    Score one incoming record against existing local records.
    Returns matches sorted by score (highest first).

    By default only DUPLICATE/REVIEW are returned (what the UX needs).
    Dart port note: this is the real-time on-device call.
    """
    new_record.normalize()
    for r in existing_records:
        if not r.norm_full and (r.given_name or r.family_name):
            r.normalize()

    results: List[DedupResult] = []
    for r in existing_records:
        if r.individual_id == new_record.individual_id:
            continue
        res = score_pair(new_record, r, weights, thresholds)
        if return_clear or res.verdict != CLEAR:
            results.append(res)

    results.sort(key=lambda x: x.score, reverse=True)
    return results


def run_batch(
    records: List[Beneficiary],
    weights: Optional[Dict[str, float]] = None,
    thresholds: Optional[Dict[str, float]] = None,
    verbose: bool = True,
) -> List[DedupResult]:
    """
    All-pairs (via blocking) over a dataset. For benchmarking/evaluation.
    """
    for r in records:
        r.normalize()

    if verbose:
        print("Blocking...")
    candidates = build_candidate_pairs(records)
    if verbose:
        n = len(records)
        total = n * (n - 1) // 2 if n > 1 else 0
        red = (1.0 - len(candidates) / total) if total else 0.0
        print("  %d candidate pairs (%.1f%% of %d eliminated)"
              % (len(candidates), red * 100, total))

    if verbose:
        print("Scoring...")
    results: List[DedupResult] = []
    for (i, j) in candidates:
        results.append(score_pair(records[i], records[j], weights, thresholds))
    return results
