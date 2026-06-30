"""
blocking_strategy.py   <->   lib/src/blocking_strategy.dart

Reduces the O(n^2) pair space to a small candidate set, without missing real
duplicates (favor recall; precision is refined later by scoring).

On-device note: in the Flutter app this runs over the LOCAL SQLite records for
the worker's area, so n is small. The same rules apply; just the data source
differs. Blocking keys here are exactly what you'd index/query in SQLite.

Four rules — a pair needs to match only ONE:
  A. boundary + dob_year + gender               (tight)
  B. boundary + metaphone(given)                (phonetic variants)
  C. boundary + first_token(father) + gender    (father is a strong signal)
  D. metaphone(given) + dob_year  (NO boundary) (catches CROSS_BOUNDARY dups)

Rule D is new vs the original Python: the labeled set includes CROSS_BOUNDARY
duplicates (same person, different settlement) where boundary-keyed rules fail.

Dart port note: each rule is a Map<String, List<int>> bucket build then pairwise
combine within buckets. combinations() -> nested i<j loop.
"""

from typing import List, Set, Tuple, Dict

from models.candidate_pair import Beneficiary
from algorithms.double_metaphone import metaphone_code


MAX_BUCKET_SIZE = 60   # skip very common-name buckets to avoid blow-up


def _combine(bucket: List[int], out: Set[Tuple[int, int]]) -> None:
    n = len(bucket)
    for x in range(n):
        for y in range(x + 1, n):
            i = bucket[x]
            j = bucket[y]
            out.add((i, j) if i < j else (j, i))


def _gender_ok(a: Beneficiary, b: Beneficiary) -> bool:
    if a.gender and b.gender:
        return a.gender.upper() == b.gender.upper()
    return True


def build_candidate_pairs(records: List[Beneficiary]) -> Set[Tuple[int, int]]:
    """Union of all blocking rules. Returns set of (i, j) with i < j."""
    out: Set[Tuple[int, int]] = set()
    _rule_boundary_year_gender(records, out)
    _rule_boundary_phonetic(records, out)
    _rule_boundary_father(records, out)
    _rule_phonetic_year_global(records, out)
    return out


def _rule_boundary_year_gender(records, out):
    buckets: Dict[str, List[int]] = {}
    for i, r in enumerate(records):
        if r.boundary_code and r.dob_year and r.gender:
            key = r.boundary_code + "|" + str(r.dob_year) + "|" + r.gender.upper()
            buckets.setdefault(key, []).append(i)
    for bucket in buckets.values():
        if 2 <= len(bucket) <= MAX_BUCKET_SIZE:
            _combine(bucket, out)


def _rule_boundary_phonetic(records, out):
    buckets: Dict[str, List[int]] = {}
    for i, r in enumerate(records):
        if r.boundary_code and r.norm_given:
            code = metaphone_code(r.norm_given)
            if code:
                buckets.setdefault(r.boundary_code + "|" + code, []).append(i)
    for bucket in buckets.values():
        if 2 <= len(bucket) <= MAX_BUCKET_SIZE:
            # gender filter inside bucket
            for x in range(len(bucket)):
                for y in range(x + 1, len(bucket)):
                    i, j = bucket[x], bucket[y]
                    if _gender_ok(records[i], records[j]):
                        out.add((i, j) if i < j else (j, i))


def _rule_boundary_father(records, out):
    buckets: Dict[str, List[int]] = {}
    for i, r in enumerate(records):
        if r.boundary_code and r.norm_father and r.gender:
            first = r.norm_father.split(" ")[0]
            key = r.boundary_code + "|" + first + "|" + r.gender.upper()
            buckets.setdefault(key, []).append(i)
    for bucket in buckets.values():
        if 2 <= len(bucket) <= MAX_BUCKET_SIZE:
            _combine(bucket, out)


def _rule_phonetic_year_global(records, out):
    """No boundary in the key — catches CROSS_BOUNDARY duplicates."""
    buckets: Dict[str, List[int]] = {}
    for i, r in enumerate(records):
        if r.norm_given and r.dob_year and r.gender:
            code = metaphone_code(r.norm_given)
            if code:
                key = code + "|" + str(r.dob_year) + "|" + r.gender.upper()
                buckets.setdefault(key, []).append(i)
    for bucket in buckets.values():
        if 2 <= len(bucket) <= MAX_BUCKET_SIZE:
            _combine(bucket, out)
