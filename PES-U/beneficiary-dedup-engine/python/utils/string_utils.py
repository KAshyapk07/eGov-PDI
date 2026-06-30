"""
utils/string_utils.py   <->   lib/src/utils/string_utils.dart

Name normalization. Every name passes through here before any algorithm sees
it, so spelling/diacritic/transliteration noise is reduced up front.

Pipeline:
  1. lowercase + trim
  2. strip diacritics (é->e, ç->c, î->i ...)
  3. remove apostrophes (O'Umar -> oumar)
  4. apply transliteration map (ou->u, dj->j, kh->k ...)
  5. keep [a-z space] only, collapse spaces

Dart port note:
  - Diacritic stripping: Dart has no stdlib NFD that drops combining marks as
    cleanly as Python's unicodedata. Port `_DIACRITIC_MAP` below as an explicit
    const Map<String,String> (it already lists every accented char we expect).
  - Everything else is plain String ops + a couple of simple loops.
"""

# Explicit accented-char -> ascii map (so Dart doesn't need unicode tables).
_DIACRITIC_MAP = {
    "à": "a", "á": "a", "â": "a", "ã": "a", "ä": "a", "å": "a",
    "è": "e", "é": "e", "ê": "e", "ë": "e",
    "ì": "i", "í": "i", "î": "i", "ï": "i",
    "ò": "o", "ó": "o", "ô": "o", "õ": "o", "ö": "o",
    "ù": "u", "ú": "u", "û": "u", "ü": "u",
    "ñ": "n", "ç": "c", "ý": "y", "ÿ": "y",
}

# Transliteration variants common in Chadian names across Arabic/French scripts.
# Applied left-to-right AFTER diacritics are stripped.
_TRANSLIT = [
    ("ou", "u"),   # Oumar -> Umar, Moussa -> Musa
    ("dj", "j"),   # Djimet -> Jimet
    ("kh", "k"),   # Khalil -> Kalil
    ("gh", "g"),
    ("ph", "f"),
    ("ei", "e"),
    ("ai", "e"),
    ("ey", "e"),
]

_APOSTROPHES = ("'", "\u2019", "\u02bc", "\u0060")


def strip_diacritics(text: str) -> str:
    """Replace accented chars using the explicit map."""
    out = []
    for ch in text:
        out.append(_DIACRITIC_MAP.get(ch, ch))
    return "".join(out)


def normalize_name(raw) -> str:
    """
    Full normalization for one name string.
    Returns "" for None / empty.

    Dart port note: signature String normalizeName(String? raw).
    """
    if raw is None:
        return ""
    text = str(raw).lower().strip()
    if not text:
        return ""

    text = strip_diacritics(text)

    for ap in _APOSTROPHES:
        text = text.replace(ap, "")

    for src, dst in _TRANSLIT:
        text = text.replace(src, dst)

    # Keep only a-z and spaces
    kept = []
    for ch in text:
        if ("a" <= ch <= "z") or ch == " ":
            kept.append(ch)
        else:
            kept.append(" ")
    text = "".join(kept)

    # Collapse multiple spaces
    parts = [p for p in text.split(" ") if p]
    return " ".join(parts)


def token_sort(name: str) -> str:
    """
    Sort tokens alphabetically so name-order swaps become identical.
      'saleh mahamat' -> 'mahamat saleh'
      'mahamat saleh' -> 'mahamat saleh'
    Dart port note: name.split(' ')..sort() then join(' ').
    """
    parts = [p for p in name.split(" ") if p]
    parts.sort()
    return " ".join(parts)
