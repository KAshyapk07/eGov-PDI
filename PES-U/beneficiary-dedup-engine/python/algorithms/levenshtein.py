"""
algorithms/levenshtein.py   <->   lib/src/algorithms/levenshtein.dart

Levenshtein edit distance and a normalized [0,1] similarity, plus the
Damerau variant (adds adjacent transposition as a single edit).

  levenshtein_distance("ibrahim", "ibrahmi") -> 2   (plain Levenshtein)
  damerau_distance   ("ibrahim", "ibrahmi") -> 1   (one transposition)

Damerau is better for name typos because swapped adjacent letters are common.

Dart port note: these are classic DP tables. Use List<List<int>> or two
rolling List<int> rows. No external packages needed.
"""


def levenshtein_distance(a: str, b: str) -> int:
    """Classic Levenshtein edit distance (insert/delete/substitute)."""
    if a == b:
        return 0
    if len(a) == 0:
        return len(b)
    if len(b) == 0:
        return len(a)

    # Two-row rolling DP for O(min(m,n)) memory — easy to port.
    previous = list(range(len(b) + 1))
    current = [0] * (len(b) + 1)

    for i in range(1, len(a) + 1):
        current[0] = i
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            current[j] = min(
                previous[j] + 1,        # deletion
                current[j - 1] + 1,     # insertion
                previous[j - 1] + cost, # substitution
            )
        previous, current = current, previous

    return previous[len(b)]


def damerau_levenshtein_distance(a: str, b: str) -> int:
    """
    Damerau-Levenshtein (optimal string alignment variant).
    Like Levenshtein but a swap of two adjacent chars costs 1, not 2.

    Dart port note: needs the full (m+1)x(n+1) matrix because of the
    transposition look-back. Use List<List<int>>.
    """
    if a == b:
        return 0
    len_a = len(a)
    len_b = len(b)
    if len_a == 0:
        return len_b
    if len_b == 0:
        return len_a

    d = [[0] * (len_b + 1) for _ in range(len_a + 1)]
    for i in range(len_a + 1):
        d[i][0] = i
    for j in range(len_b + 1):
        d[0][j] = j

    for i in range(1, len_a + 1):
        for j in range(1, len_b + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(
                d[i - 1][j] + 1,         # deletion
                d[i][j - 1] + 1,         # insertion
                d[i - 1][j - 1] + cost,  # substitution
            )
            # Transposition
            if (i > 1 and j > 1
                    and a[i - 1] == b[j - 2]
                    and a[i - 2] == b[j - 1]):
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)

    return d[len_a][len_b]


def levenshtein_similarity(a: str, b: str) -> float:
    """Normalized: 1 - distance / max_len. Returns [0,1]."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    max_len = max(len(a), len(b))
    return 1.0 - levenshtein_distance(a, b) / max_len


def damerau_similarity(a: str, b: str) -> float:
    """Normalized Damerau-Levenshtein similarity. Returns [0,1]."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    max_len = max(len(a), len(b))
    return 1.0 - damerau_levenshtein_distance(a, b) / max_len
