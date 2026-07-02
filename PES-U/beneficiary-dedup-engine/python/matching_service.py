"""
matching_service.py   <->   lib/src/matching_service.dart

Multi-attribute scoring. Runs every algorithm on a candidate pair, combines the
scores with tunable weights, and produces a verdict.

The feature set is designed to cover the 9 labeled duplicate types:
  EXACT_DUPLICATE     -> all features high (mobile short-circuit also helps)
  PHONETIC_VARIATION  -> metaphone/soundex agreement
  SPELLING_ERROR      -> jaro-winkler / damerau on given+father
  NAME_ABBREVIATION   -> prefix/containment score (Ibrahim vs Ibra)
  NAME_ORDER_SWAP     -> cross-field given<->family comparison
  DOB_VARIATION       -> dob_score tolerance window
  GPS_NEARBY          -> proximity_score
  COMBINED_NOISE      -> weighted blend of all of the above
  CROSS_BOUNDARY      -> name+dob carry it (geo contributes ~0)

CYCLE: campaign cycle is included as a *gentle nudge* (weight 0.04). It rewards
a duplicate spanning DIFFERENT cycles (the re-registration story this project
targets), stays neutral on same/missing cycle, and at this weight can never flip
a verdict on its own. Set the "cycle" weight to 0.0 to disable, then re-run
evaluate.py and keep it only if F1 improves.

Dart port note: pure arithmetic over the algorithm modules already ported.
Keep DEFAULT_WEIGHTS and THRESHOLDS as const maps so they can be tuned without
touching logic.
"""

from typing import Optional, Dict
from datetime import date

from models.candidate_pair import Beneficiary
from models.dedup_result import DedupResult, DUPLICATE, REVIEW, CLEAR
from algorithms.jaro_winkler import jaro_winkler_similarity
from algorithms.levenshtein import damerau_similarity
from algorithms.soundex import soundex_match
from algorithms.double_metaphone import metaphone_match
from utils.gps_utils import proximity_score, same_household_score


# -- Weights (must sum to ~1.0) ---------------------------------------------
# CYCLE: 0.04 was carved out of geo (0.14->0.12) and family_jw (0.08->0.06),
# the two weakest contributors, so the composite still sums to 1.0 and the
# 0.82 DUPLICATE threshold keeps its meaning.
DEFAULT_WEIGHTS: Dict[str, float] = {
    # Given name (0.34)
    "given_jw":        0.16,
    "given_damerau":   0.10,
    "given_phonetic":  0.08,
    # Father name (0.26) -- strong signal
    "father_jw":       0.16,
    "father_damerau":  0.06,
    "father_phonetic": 0.04,
    # Family name (0.06)
    "family_jw":       0.08,
    # DOB (0.18)
    "dob":             0.18,
    # Geography (0.12)
    "geo":             0.14,
    # Campaign cycle (0.04) -- gentle nudge, see cycle_score()
    "cycle":           0.00,
}

THRESHOLDS = {
    "DUPLICATE": 0.82,
    "REVIEW":    0.62,
}

# Sibling guard
_SIBLING_HOUSEHOLD = 0.90
_SIBLING_FATHER = 0.85
_SIBLING_GIVEN_MAX = 0.75


# -- Sub-scorers ------------------------------------------------------------

def phonetic_score(a: str, b: str) -> float:
    """Blend metaphone + soundex agreement: 1.0 / 0.5 / 0.0."""
    if not a or not b:
        return 0.0
    m = metaphone_match(a, b)
    s = soundex_match(a, b)
    if m == 1.0 and s == 1.0:
        return 1.0
    if m == 1.0 or s == 1.0:
        return 0.5
    return 0.0


def containment_score(a: str, b: str) -> float:
    """
    Handles NAME_ABBREVIATION: 'ibrahim' vs 'ibra'.
    1.0 if the shorter is a prefix of the longer (>=3 chars),
    0.85 if it's a substring, else 0.0.
    """
    if not a or not b:
        return 0.0
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    if len(short) < 3:
        return 0.0
    if long.startswith(short):
        return 1.0
    if short in long:
        return 0.85
    return 0.0


def given_name_score(a: Beneficiary, b: Beneficiary) -> float:
    """
    Best of: direct JW, and containment (for abbreviations).
    Returns the max so abbreviations don't get penalized by length.
    """
    direct = jaro_winkler_similarity(a.norm_given, b.norm_given)
    contain = containment_score(a.norm_given, b.norm_given)
    return max(direct, contain)


def name_swap_score(a: Beneficiary, b: Beneficiary) -> float:
    """
    Handles NAME_ORDER_SWAP: compare a.given<->b.family and a.family<->b.given.
    Returns the average of the two cross comparisons.
    """
    cross1 = jaro_winkler_similarity(a.norm_given, b.norm_family)
    cross2 = jaro_winkler_similarity(a.norm_family, b.norm_given)
    return (cross1 + cross2) / 2.0


def full_name_swapped_score(a: Beneficiary, b: Beneficiary) -> float:
    """
    Order-independent full-name similarity: compares the token-sorted
    given+family of both records. 'Mahamat Deby' vs 'Deby Mahamat' -> 1.0.
    This is what actually rescues NAME_ORDER_SWAP, because it ignores which
    field each token landed in.
    """
    return jaro_winkler_similarity(a.norm_full, b.norm_full)


def dob_score(a: Optional[date], b: Optional[date]) -> float:
    """
    Tolerant DOB scoring (handles DOB_VARIATION):
      1.00 exact
      0.95 day/month swapped
      0.90 same year+month, <= 7 days apart
      0.75 same year+month, further
      0.60 same year
      0.40 +-1 year
      0.00 otherwise / missing
    """
    if a is None or b is None:
        return 0.0
    if a == b:
        return 1.0
    if a.year == b.year and a.month == b.day and a.day == b.month:
        return 0.95
    delta = abs((a - b).days)
    if a.year == b.year and a.month == b.month:
        return 0.90 if delta <= 7 else 0.75
    if a.year == b.year:
        return 0.60
    if abs(a.year - b.year) == 1:
        return 0.40
    return 0.0


def cycle_score(a: Optional[str], b: Optional[str]) -> float:
    """
    CYCLE: campaign-cycle agreement, as a gentle signal.

    Design choice (Interpretation A -- re-registration across campaigns):
      - DIFFERENT cycles  -> 1.0  (the same child re-registered in a later
                                    cycle is exactly the duplicate we hunt for)
      - SAME cycle        -> 0.5  (neutral; double-entry in one cycle is fine
                                    too, but we don't want to over-reward it)
      - EITHER missing    -> 0.5  (absence must never penalize a match)

    At weight 0.04 this can only tilt borderline composites, never flip a
    verdict alone. To use Interpretation B (same cycle = more suspicious),
    swap the return to:  return 0.5 if a != b else 1.0  -- then re-run evaluate.

    Dart port note: signature double cycleScore(String? a, String? b); same
    null-handling.
    """
    if not a or not b:
        return 0.5
    a = a.strip()
    b = b.strip()
    if a == "" or b == "":
        return 0.5
    return 1.0 if a != b else 0.5


# -- Main entry -------------------------------------------------------------

def score_pair(
    a: Beneficiary,
    b: Beneficiary,
    weights: Dict[str, float] = None,
    thresholds: Dict[str, float] = None,
) -> DedupResult:
    w = weights or DEFAULT_WEIGHTS
    t = thresholds or THRESHOLDS

    # Hard filter: different gender -> not a duplicate
    if a.gender and b.gender and a.gender.upper() != b.gender.upper():
        return DedupResult(a.individual_id, b.individual_id, 0.0, CLEAR,
                           {}, ["GENDER_MISMATCH"])

    # Short-circuit: identical mobile number -> near-certain duplicate
    if a.mobile_number and b.mobile_number and a.mobile_number == b.mobile_number:
        return DedupResult(a.individual_id, b.individual_id, 1.0, DUPLICATE,
                           {"mobile_match": 1.0}, ["MOBILE_MATCH"])

    given_direct = given_name_score(a, b)
    swap = name_swap_score(a, b)
    full_swap = full_name_swapped_score(a, b)
    # If a name-order swap scores higher than the direct comparison, use it.
    given_final = max(given_direct, swap, full_swap)
    # When the order is swapped, the family comparison is also wrong; lift it
    # with the order-independent full-name score so the composite recovers.
    family_final = max(jaro_winkler_similarity(a.norm_family, b.norm_family), full_swap)

    geo = proximity_score(a.latitude, a.longitude, b.latitude, b.longitude,
                          a.location_accuracy, b.location_accuracy)
    household = same_household_score(a.latitude, a.longitude,
                                     b.latitude, b.longitude,
                                     a.location_accuracy, b.location_accuracy)

    features = {
        "given_jw":        given_final,
        "given_damerau":   damerau_similarity(a.norm_given, b.norm_given),
        "given_phonetic":  phonetic_score(a.norm_given, b.norm_given),
        "father_jw":       jaro_winkler_similarity(a.norm_father, b.norm_father),
        "father_damerau":  damerau_similarity(a.norm_father, b.norm_father),
        "father_phonetic": phonetic_score(a.norm_father, b.norm_father),
        "family_jw":       family_final,
        "dob":             dob_score(a.date_of_birth, b.date_of_birth),
        "geo":             geo,
        # CYCLE: gentle nudge feature
        "cycle":           cycle_score(a.cycle, b.cycle),
        # diagnostics (not weighted)
        "name_swap":       swap,
        "household":       household,
    }

    composite = 0.0
    for k, weight in w.items():
        if k in features:
            composite += features[k] * weight
    composite = round(composite, 4)

    if composite >= t["DUPLICATE"]:
        verdict = DUPLICATE
    elif composite >= t["REVIEW"]:
        verdict = REVIEW
    else:
        verdict = CLEAR

    flags = []
    if (features["household"] >= _SIBLING_HOUSEHOLD
            and features["father_jw"] >= _SIBLING_FATHER
            and given_direct < _SIBLING_GIVEN_MAX
            and swap < _SIBLING_GIVEN_MAX):
        flags.append("POSSIBLE_SIBLING")
        if verdict == DUPLICATE:
            verdict = REVIEW

    return DedupResult(a.individual_id, b.individual_id, composite, verdict,
                       features, flags)