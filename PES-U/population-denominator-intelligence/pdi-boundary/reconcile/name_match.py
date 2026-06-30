# Name matching between two boundary rosters.

import difflib
import re
import unicodedata


def normalize(value):
    """Accent-stripped, lowercased, alphanumeric-only key for comparing names."""
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def match_names(left_names, right_names, fuzzy_cutoff=0.80):
    # Greedy one-to-one match of two name lists.
    left_by_key = {}
    for name in left_names:
        left_by_key.setdefault(normalize(name), name)
    right_by_key = {}
    for name in right_names:
        right_by_key.setdefault(normalize(name), name)

    pairs = []

    for key in list(left_by_key):
        if key and key in right_by_key:
            pairs.append({"left": left_by_key.pop(key), "right": right_by_key.pop(key),
                          "score": 1.0, "kind": "exact"})

    for key in list(left_by_key):
        candidates = difflib.get_close_matches(key, list(right_by_key), n=1, cutoff=fuzzy_cutoff)
        if candidates:
            best = candidates[0]
            score = difflib.SequenceMatcher(None, key, best).ratio()
            pairs.append({"left": left_by_key.pop(key), "right": right_by_key.pop(best),
                          "score": round(score, 3), "kind": "fuzzy"})

    return pairs, list(left_by_key.values()), list(right_by_key.values())
