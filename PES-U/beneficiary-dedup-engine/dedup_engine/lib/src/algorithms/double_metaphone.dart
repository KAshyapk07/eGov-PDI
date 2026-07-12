/// A compact, deterministic Double Metaphone implementation.
///
/// Double Metaphone returns up to TWO phonetic codes (primary + alternate), so
/// a name with more than one plausible pronunciation can match either. This is
/// the strongest phonetic signal for Arabic/French transliteration variants:
///   doubleMetaphone("mahamat")  -> ("MHMT", "MHMT")
///   doubleMetaphone("muhammad") -> ("MHMT", "MHMT")
///
/// This is a pragmatic subset of Lawrence Philips' algorithm, covering the
/// consonant rules that matter for these names.

/// The two phonetic codes for a name.
library; 
class MetaphoneCodes {
  final String primary;
  final String alternate;

  const MetaphoneCodes(this.primary, this.alternate);

  @override
  String toString() => '($primary, $alternate)';

  @override
  bool operator ==(Object other) =>
      other is MetaphoneCodes &&
      other.primary == primary &&
      other.alternate == alternate;

  @override
  int get hashCode => Object.hash(primary, alternate);
}

const _vowels = 'aeiouy';

bool _isVowel(String s, int i) {
  if (i < 0 || i >= s.length) return false;
  return _vowels.contains(s[i]);
}

/// Compute the (primary, alternate) Double Metaphone codes. Codes are capped
/// at 4 characters.
MetaphoneCodes doubleMetaphone(String name) {
  if (name.isEmpty) return const MetaphoneCodes('', '');

  // First token, letters only, lowercased.
  final token = name.trim().split(' ').first.toLowerCase();
  final buf = StringBuffer();
  for (var i = 0; i < token.length; i++) {
    final c = token[i];
    if (c.compareTo('a') >= 0 && c.compareTo('z') <= 0) buf.write(c);
  }
  final s = buf.toString();
  if (s.isEmpty) return const MetaphoneCodes('', '');

  final primary = StringBuffer();
  final alternate = StringBuffer();
  final length = s.length;
  var i = 0;
  const maxLen = 4;

  void add(String p, [String? a]) {
    primary.write(p);
    alternate.write(a ?? p);
  }

  // Skip silent leading pairs.
  if (length >= 2) {
    final first2 = s.substring(0, 2);
    if (first2 == 'gn' ||
        first2 == 'kn' ||
        first2 == 'pn' ||
        first2 == 'wr' ||
        first2 == 'ps') {
      i = 1;
    }
  }

  // Initial 'x' sounds like 's'.
  if (s[0] == 'x') {
    add('s');
    i = 1;
  }

  while (i < length &&
      (primary.length < maxLen || alternate.length < maxLen)) {
    final c = s[i];

    if (_vowels.contains(c)) {
      // Only a leading vowel contributes.
      if (i == 0) add('a');
      i++;
      continue;
    }

    switch (c) {
      case 'b':
        add('p');
        i += (i + 1 < length && s[i + 1] == 'b') ? 2 : 1;
        break;

      case 'c':
        if (i + 1 < length && s[i + 1] == 'h') {
          add('x');
          i += 2;
        } else if (i + 1 < length &&
            (s[i + 1] == 'i' || s[i + 1] == 'e' || s[i + 1] == 'y')) {
          add('s');
          i += 2;
        } else {
          add('k');
          i += (i + 1 < length && s[i + 1] == 'c') ? 2 : 1;
        }
        break;

      case 'd':
        if (i + 2 < length &&
            s[i + 1] == 'g' &&
            (s[i + 2] == 'i' || s[i + 2] == 'e' || s[i + 2] == 'y')) {
          add('j');
          i += 3;
        } else {
          add('t');
          i += (i + 1 < length && s[i + 1] == 'd') ? 2 : 1;
        }
        break;

      case 'g':
        if (i + 1 < length && s[i + 1] == 'h') {
          add('k');
          i += 2;
        } else if (i + 1 < length &&
            (s[i + 1] == 'i' || s[i + 1] == 'e' || s[i + 1] == 'y')) {
          add('j', 'k'); // soft/hard ambiguity
          i += 2;
        } else {
          add('k');
          i += (i + 1 < length && s[i + 1] == 'g') ? 2 : 1;
        }
        break;

      case 'h':
        // Pronounced only between vowels, or at the start before a vowel.
        if ((i == 0 || _isVowel(s, i - 1)) && _isVowel(s, i + 1)) {
          add('h');
        }
        i++;
        break;

      case 'j':
        add('j');
        i += (i + 1 < length && s[i + 1] == 'j') ? 2 : 1;
        break;

      case 'k':
        add('k');
        i += (i + 1 < length && s[i + 1] == 'k') ? 2 : 1;
        break;

      case 'l':
        add('l');
        i += (i + 1 < length && s[i + 1] == 'l') ? 2 : 1;
        break;

      case 'm':
        add('m');
        i += (i + 1 < length && s[i + 1] == 'm') ? 2 : 1;
        break;

      case 'n':
        add('n');
        i += (i + 1 < length && s[i + 1] == 'n') ? 2 : 1;
        break;

      case 'p':
        if (i + 1 < length && s[i + 1] == 'h') {
          add('f');
          i += 2;
        } else {
          add('p');
          i += (i + 1 < length && s[i + 1] == 'p') ? 2 : 1;
        }
        break;

      case 'q':
        add('k');
        i++;
        break;

      case 'r':
        add('r');
        i += (i + 1 < length && s[i + 1] == 'r') ? 2 : 1;
        break;

      case 's':
        if (i + 1 < length && s[i + 1] == 'h') {
          add('x');
          i += 2;
        } else {
          add('s');
          i += (i + 1 < length && s[i + 1] == 's') ? 2 : 1;
        }
        break;

      case 't':
        if (i + 1 < length && s[i + 1] == 'h') {
          add('0'); // theta
          i += 2;
        } else {
          add('t');
          i += (i + 1 < length && s[i + 1] == 't') ? 2 : 1;
        }
        break;

      case 'v':
        add('f');
        i += (i + 1 < length && s[i + 1] == 'v') ? 2 : 1;
        break;

      case 'w':
        if (_isVowel(s, i + 1)) add('a');
        i++;
        break;

      case 'x':
        add('k');
        i++;
        break;

      case 'z':
        add('s');
        i += (i + 1 < length && s[i + 1] == 'z') ? 2 : 1;
        break;

      default:
        i++;
        break;
    }
  }

  String cap(String v) =>
      (v.length > maxLen ? v.substring(0, maxLen) : v).toUpperCase();

  return MetaphoneCodes(cap(primary.toString()), cap(alternate.toString()));
}

/// Primary Double Metaphone code only (used as a blocking key).
String metaphoneCode(String name) => doubleMetaphone(name).primary;

/// Soft phonetic agreement: 1.0 if either code of one name matches either code
/// of the other, else 0.0.
double metaphoneMatch(String a, String b) {
  if (a.isEmpty || b.isEmpty) return 0.0;
  final ca = doubleMetaphone(a);
  final cb = doubleMetaphone(b);
  if (ca.primary.isEmpty || cb.primary.isEmpty) return 0.0;

  final setA = {ca.primary, ca.alternate};
  final setB = {cb.primary, cb.alternate};
  return setA.intersection(setB).isNotEmpty ? 1.0 : 0.0;
}
