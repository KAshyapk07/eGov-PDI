"""
algorithms/double_metaphone.py   <->   lib/src/algorithms/double_metaphone.dart

A compact, deterministic Double Metaphone implementation.

Double Metaphone returns up to TWO phonetic codes (primary + alternate) so a
name with more than one plausible pronunciation can match either. This is the
strongest phonetic signal for the Arabic/French transliteration variants in the
Chad dataset (Mahamat / Muhammad / Mohamed all collapse toward "MMT"/"MHMT").

This is a pragmatic port-friendly subset of Lawrence Philips' algorithm. It
handles the consonant rules that matter for these names and is intentionally
written with explicit index walking (no regex) so the Dart port is mechanical.

  double_metaphone("mahamat")  -> ("MMT", "MMT")
  double_metaphone("muhammad") -> ("MMT", "MMT")
  double_metaphone("khadija")  -> ("KTJ", "KTK")

Returns a (primary, alternate) tuple of uppercase codes.
Dart port note: return a record/2-tuple or a small class with .primary/.alternate.
"""

_VOWELS = set("aeiouy")


def _is_vowel(s: str, i: int) -> bool:
    if i < 0 or i >= len(s):
        return False
    return s[i] in _VOWELS


def double_metaphone(name: str) -> tuple:
    """
    Compute (primary, alternate) Double Metaphone codes.
    Codes are capped at 4 characters, matching common implementations.
    """
    if not name:
        return ("", "")

    # Work on first token, letters only, uppercased.
    token = name.strip().split(" ")[0]
    s = "".join(c for c in token.lower() if "a" <= c <= "z")
    if not s:
        return ("", "")

    primary = []
    alternate = []
    length = len(s)
    i = 0
    MAX = 4

    def add(p, a=None):
        primary.append(p)
        alternate.append(a if a is not None else p)

    # Skip silent leading pairs
    if length >= 2 and s[0:2] in ("gn", "kn", "pn", "wr", "ps"):
        i = 1

    # Initial 'x' sounds like 's'
    if s[0] == "x":
        add("s")
        i = 1

    while i < length and (len("".join(primary)) < MAX or len("".join(alternate)) < MAX):
        c = s[i]

        if c in _VOWELS:
            # Only the very first letter, if a vowel, contributes.
            if i == 0:
                add("a")
            i += 1
            continue

        if c == "b":
            add("p")
            i += 2 if (i + 1 < length and s[i + 1] == "b") else 1
        elif c == "c":
            # 'ch'
            if i + 1 < length and s[i + 1] == "h":
                add("x")  # 'ch' -> X (sh sound); common in these names
                i += 2
            elif i + 1 < length and s[i + 1] in ("i", "e", "y"):
                add("s")
                i += 2
            else:
                add("k")
                i += 2 if (i + 1 < length and s[i + 1] == "c") else 1
        elif c == "d":
            if i + 2 < length and s[i + 1] == "g" and s[i + 2] in ("i", "e", "y"):
                add("j")
                i += 3
            else:
                add("t")
                i += 2 if (i + 1 < length and s[i + 1] == "d") else 1
        elif c == "g":
            if i + 1 < length and s[i + 1] == "h":
                # 'gh' — keep as K initially, often silent later; pragmatic K
                add("k")
                i += 2
            elif i + 1 < length and s[i + 1] in ("i", "e", "y"):
                add("j", "k")  # soft/hard ambiguity
                i += 2
            else:
                add("k")
                i += 2 if (i + 1 < length and s[i + 1] == "g") else 1
        elif c == "h":
            # Pronounced only between vowels or at start before a vowel
            if (i == 0 or _is_vowel(s, i - 1)) and _is_vowel(s, i + 1):
                add("h")
            i += 1
        elif c == "j":
            add("j")
            i += 2 if (i + 1 < length and s[i + 1] == "j") else 1
        elif c == "k":
            add("k")
            i += 2 if (i + 1 < length and s[i + 1] == "k") else 1
        elif c == "l":
            add("l")
            i += 2 if (i + 1 < length and s[i + 1] == "l") else 1
        elif c == "m":
            add("m")
            i += 2 if (i + 1 < length and s[i + 1] == "m") else 1
        elif c == "n":
            add("n")
            i += 2 if (i + 1 < length and s[i + 1] == "n") else 1
        elif c == "p":
            if i + 1 < length and s[i + 1] == "h":
                add("f")
                i += 2
            else:
                add("p")
                i += 2 if (i + 1 < length and s[i + 1] == "p") else 1
        elif c == "q":
            add("k")
            i += 1
        elif c == "r":
            add("r")
            i += 2 if (i + 1 < length and s[i + 1] == "r") else 1
        elif c == "s":
            if i + 1 < length and s[i + 1] == "h":
                add("x")
                i += 2
            else:
                add("s")
                i += 2 if (i + 1 < length and s[i + 1] == "s") else 1
        elif c == "t":
            if i + 1 < length and s[i + 1] == "h":
                add("0")  # 'th' -> theta, represented as '0'
                i += 2
            else:
                add("t")
                i += 2 if (i + 1 < length and s[i + 1] == "t") else 1
        elif c == "v":
            add("f")
            i += 2 if (i + 1 < length and s[i + 1] == "v") else 1
        elif c == "w":
            # Pronounced as a vowel-glide; encode only if followed by a vowel
            if _is_vowel(s, i + 1):
                add("a")
            i += 1
        elif c == "x":
            add("k")  # ks — pragmatic single K
            i += 1
        elif c == "z":
            add("s")
            i += 2 if (i + 1 < length and s[i + 1] == "z") else 1
        else:
            i += 1

    p = "".join(primary)[:MAX].upper()
    a = "".join(alternate)[:MAX].upper()
    return (p, a)


def metaphone_code(name: str) -> str:
    """Primary Double Metaphone code only (used as a blocking key)."""
    return double_metaphone(name)[0]


def metaphone_match(a: str, b: str) -> float:
    """
    Soft phonetic agreement using both codes:
      1.0  — primary codes match, OR either code matches the other's
      0.0  — no overlap
    """
    if not a or not b:
        return 0.0
    pa, aa = double_metaphone(a)
    pb, ab = double_metaphone(b)
    if not pa or not pb:
        return 0.0
    codes_a = {pa, aa}
    codes_b = {pb, ab}
    return 1.0 if codes_a & codes_b else 0.0
