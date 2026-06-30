"""
algorithms/soundex.py   <->   lib/src/algorithms/soundex.dart

Classic American Soundex phonetic encoding.
Encodes a name to a letter + 3 digits, so similar-sounding names collide.

  soundex("Robert") -> "R163"
  soundex("Rupert") -> "R163"

Used as a coarse phonetic signal and as a blocking key.

Dart port note: pure string/char work. The digit map is a const Map<String,String>.
"""

# Soundex digit groups
_SOUNDEX_MAP = {
    "b": "1", "f": "1", "p": "1", "v": "1",
    "c": "2", "g": "2", "j": "2", "k": "2", "q": "2", "s": "2", "x": "2", "z": "2",
    "d": "3", "t": "3",
    "l": "4",
    "m": "5", "n": "5",
    "r": "6",
}


def _code_of(ch: str) -> str:
    """Soundex digit for a single lowercase letter, or '' if none."""
    return _SOUNDEX_MAP.get(ch, "")


def soundex(name: str) -> str:
    """
    Soundex code for the FIRST token of a name string.
    Returns "" for empty input.

    Algorithm:
      1. Keep letters only, lowercase.
      2. First letter is kept as-is (uppercased).
      3. Encode remaining letters to digits; drop duplicates that share a code
         (unless separated by a vowel / h / w).
      4. Pad/truncate to length 4.
    """
    if not name:
        return ""

    # First token, letters only
    token = name.strip().split(" ")[0].lower()
    letters = [c for c in token if "a" <= c <= "z"]
    if not letters:
        return ""

    first = letters[0].upper()
    result = first
    prev_code = _code_of(letters[0])

    for i in range(1, len(letters)):
        ch = letters[i]
        code = _code_of(ch)
        if code != "":
            if code != prev_code:
                result += code
        # 'h' and 'w' do NOT reset prev_code; vowels do.
        if ch in ("h", "w"):
            pass
        else:
            prev_code = code
        if len(result) >= 4:
            break

    # Pad with zeros to 4 chars, then truncate
    result = (result + "000")[:4]
    return result


def soundex_match(a: str, b: str) -> float:
    """1.0 if first-token Soundex codes match, else 0.0."""
    if not a or not b:
        return 0.0
    return 1.0 if soundex(a) == soundex(b) else 0.0
