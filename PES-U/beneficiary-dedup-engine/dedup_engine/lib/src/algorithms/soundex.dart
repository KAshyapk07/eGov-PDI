/// Classic American Soundex phonetic encoding.
///
/// Encodes a name to a letter plus three digits, so similar-sounding names
/// collide:
///   soundex("Robert") -> "R163"
///   soundex("Rupert") -> "R163"
///
/// Used as a coarse phonetic signal and as a blocking key.
library; 

const Map<String, String> _soundexMap = {
  'b': '1', 'f': '1', 'p': '1', 'v': '1',
  'c': '2', 'g': '2', 'j': '2', 'k': '2',
  'q': '2', 's': '2', 'x': '2', 'z': '2',
  'd': '3', 't': '3',
  'l': '4',
  'm': '5', 'n': '5',
  'r': '6',
};

String _codeOf(String ch) => _soundexMap[ch] ?? '';

/// Soundex code for the FIRST token of [name]. Returns '' for empty input.
String soundex(String name) {
  if (name.isEmpty) return '';

  // First token, letters only, lowercased.
  final token = name.trim().split(' ').first.toLowerCase();
  final letters = <String>[];
  for (var i = 0; i < token.length; i++) {
    final c = token[i];
    if (c.compareTo('a') >= 0 && c.compareTo('z') <= 0) {
      letters.add(c);
    }
  }
  if (letters.isEmpty) return '';

  var result = letters[0].toUpperCase();
  var prevCode = _codeOf(letters[0]);

  for (var i = 1; i < letters.length; i++) {
    final ch = letters[i];
    final code = _codeOf(ch);

    if (code != '') {
      if (code != prevCode) {
        result += code;
      }
    }

    // 'h' and 'w' do NOT reset prevCode; vowels do.
    if (ch != 'h' && ch != 'w') {
      prevCode = code;
    }

    if (result.length >= 4) break;
  }

  // Pad with zeros to 4 characters, then truncate.
  result = '${result}000';
  return result.substring(0, 4);
}

/// 1.0 if the first-token Soundex codes match, else 0.0.
double soundexMatch(String a, String b) {
  if (a.isEmpty || b.isEmpty) return 0.0;
  return soundex(a) == soundex(b) ? 1.0 : 0.0;
}
