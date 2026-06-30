"""
algorithms/jaro_winkler.py   <->   lib/src/algorithms/jaro_winkler.dart

Pure Jaro and Jaro-Winkler string similarity.
No external libraries — written to port directly to Dart (dart:core only).

Jaro-Winkler is the workhorse for short personal names: it rewards a matching
prefix, which fits Chadian given/father names well.

  jaro_winkler("fatime", "fatima")  -> ~0.94
  jaro_winkler("mahamat", "mohamed") -> ~0.76

All functions return a double in [0.0, 1.0].
"""


def jaro_similarity(a: str, b: str) -> float:
    """
    Plain Jaro similarity.

    Dart port note: identical logic. Use `a.codeUnitAt(i)` for char compares,
    and List<bool> for the match flags.
    """
    if a == b:
        return 1.0
    len_a = len(a)
    len_b = len(b)
    if len_a == 0 or len_b == 0:
        return 0.0

    # Max distance a matching char can be apart.
    match_distance = (max(len_a, len_b) // 2) - 1
    if match_distance < 0:
        match_distance = 0

    a_matches = [False] * len_a
    b_matches = [False] * len_b

    matches = 0
    transpositions = 0

    # Count matches
    for i in range(len_a):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len_b)
        for j in range(start, end):
            if b_matches[j]:
                continue
            if a[i] != b[j]:
                continue
            a_matches[i] = True
            b_matches[j] = True
            matches += 1
            break

    if matches == 0:
        return 0.0

    # Count transpositions
    k = 0
    for i in range(len_a):
        if not a_matches[i]:
            continue
        while not b_matches[k]:
            k += 1
        if a[i] != b[k]:
            transpositions += 1
        k += 1

    m = float(matches)
    t = transpositions / 2.0
    return (m / len_a + m / len_b + (m - t) / m) / 3.0


def jaro_winkler_similarity(
    a: str,
    b: str,
    prefix_scale: float = 0.1,
    max_prefix: int = 4,
) -> float:
    """
    Jaro-Winkler similarity = Jaro + prefix boost.

    prefix_scale: how much a common prefix boosts the score (standard 0.1).
    max_prefix:   prefix length cap (standard 4).

    Dart port note: identical. Keep prefix_scale and max_prefix as named params
    with the same defaults.
    """
    jaro = jaro_similarity(a, b)
    if jaro == 0.0:
        return 0.0

    # Length of common prefix, capped at max_prefix
    prefix_len = 0
    limit = min(len(a), len(b), max_prefix)
    for i in range(limit):
        if a[i] == b[i]:
            prefix_len += 1
        else:
            break

    return jaro + prefix_len * prefix_scale * (1.0 - jaro)
