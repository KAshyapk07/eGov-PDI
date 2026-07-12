/// Name normalization. Every name passes through here before any algorithm
/// sees it, so spelling / diacritic / transliteration noise is reduced up
/// front.
///
/// Pipeline:
///   1. lowercase + trim
///   2. strip diacritics (é -> e, ç -> c, î -> i ...)
///   3. remove apostrophes (O'Umar -> oumar)
///   4. apply transliteration map (ou -> u, dj -> j, kh -> k ...)
///   5. keep [a-z space] only, collapse spaces
///
///   normalizeName("Oumar")      -> "umar"
///   normalizeName("Mahàmat")    -> "mahamat"
///   normalizeName("Khalil")     -> "kalil"
///   normalizeName("Djimadoum")  -> "jimadum"

/// Accented character -> ASCII. Explicit so no Unicode tables are needed.

library; 
const Map<String, String> _diacriticMap = {
  'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a',
  'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
  'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
  'ò': 'o', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
  'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
  'ñ': 'n', 'ç': 'c', 'ý': 'y', 'ÿ': 'y',
};

/// Transliteration variants common in Chadian names across Arabic/French
/// scripts. Applied in order, AFTER diacritics are stripped.
const List<List<String>> _translit = [
  ['ou', 'u'], // Oumar -> Umar, Moussa -> Musa
  ['dj', 'j'], // Djimet -> Jimet
  ['kh', 'k'], // Khalil -> Kalil
  ['gh', 'g'],
  ['ph', 'f'],
  ['ei', 'e'],
  ['ai', 'e'],
  ['ey', 'e'],
];

const List<String> _apostrophes = ["'", '\u2019', '\u02bc', '`'];

/// Replace accented characters using the explicit map.
String stripDiacritics(String text) {
  final out = StringBuffer();
  for (var i = 0; i < text.length; i++) {
    final ch = text[i];
    out.write(_diacriticMap[ch] ?? ch);
  }
  return out.toString();
}

/// Full normalization for one name. Returns '' for null/empty.
String normalizeName(String? raw) {
  if (raw == null) return '';
  var text = raw.toLowerCase().trim();
  if (text.isEmpty) return '';

  text = stripDiacritics(text);

  for (final ap in _apostrophes) {
    text = text.replaceAll(ap, '');
  }

  for (final pair in _translit) {
    text = text.replaceAll(pair[0], pair[1]);
  }

  // Keep only a-z and spaces; everything else becomes a space.
  final kept = StringBuffer();
  for (var i = 0; i < text.length; i++) {
    final ch = text[i];
    if ((ch.compareTo('a') >= 0 && ch.compareTo('z') <= 0) || ch == ' ') {
      kept.write(ch);
    } else {
      kept.write(' ');
    }
  }

  // Collapse multiple spaces.
  final parts =
      kept.toString().split(' ').where((p) => p.isNotEmpty).toList();
  return parts.join(' ');
}

/// Sort tokens alphabetically so name-order swaps become identical.
///   tokenSort("saleh mahamat") -> "mahamat saleh"
///   tokenSort("mahamat saleh") -> "mahamat saleh"
String tokenSort(String name) {
  final parts = name.split(' ').where((p) => p.isNotEmpty).toList();
  parts.sort();
  return parts.join(' ');
}
