/// Levenshtein and Damerau-Levenshtein edit distance, plus normalized
/// [0,1] similarity scores.
///
/// Damerau counts a swap of two adjacent characters as ONE edit, which is
/// what a typo like "ibrahmi" for "ibrahim" actually is.

/// Classic Levenshtein edit distance (insert / delete / substitute).
library; 
int levenshteinDistance(String a, String b) {
  if (a == b) return 0;
  if (a.isEmpty) return b.length;
  if (b.isEmpty) return a.length;

  // Two rolling rows — O(min(m,n)) memory.
  var previous = List<int>.generate(b.length + 1, (i) => i);
  var current = List<int>.filled(b.length + 1, 0);

  for (var i = 1; i <= a.length; i++) {
    current[0] = i;
    for (var j = 1; j <= b.length; j++) {
      final cost = (a[i - 1] == b[j - 1]) ? 0 : 1;
      final deletion = previous[j] + 1;
      final insertion = current[j - 1] + 1;
      final substitution = previous[j - 1] + cost;
      current[j] = [deletion, insertion, substitution]
          .reduce((x, y) => x < y ? x : y);
    }
    // swap the rows
    final tmp = previous;
    previous = current;
    current = tmp;
  }

  return previous[b.length];
}

/// Damerau-Levenshtein (optimal string alignment): like Levenshtein, but a
/// transposition of two adjacent characters costs 1 instead of 2.
int damerauDistance(String a, String b) {
  if (a == b) return 0;
  if (a.isEmpty) return b.length;
  if (b.isEmpty) return a.length;

  // Full matrix is needed here because of the transposition look-back.
  final d = List<List<int>>.generate(
    a.length + 1,
    (_) => List<int>.filled(b.length + 1, 0),
  );

  for (var i = 0; i <= a.length; i++) {
    d[i][0] = i;
  }
  for (var j = 0; j <= b.length; j++) {
    d[0][j] = j;
  }

  for (var i = 1; i <= a.length; i++) {
    for (var j = 1; j <= b.length; j++) {
      final cost = (a[i - 1] == b[j - 1]) ? 0 : 1;
      var best = [
        d[i - 1][j] + 1, // deletion
        d[i][j - 1] + 1, // insertion
        d[i - 1][j - 1] + cost, // substitution
      ].reduce((x, y) => x < y ? x : y);

      // transposition
      if (i > 1 && j > 1 && a[i - 1] == b[j - 2] && a[i - 2] == b[j - 1]) {
        final transposition = d[i - 2][j - 2] + 1;
        if (transposition < best) best = transposition;
      }

      d[i][j] = best;
    }
  }

  return d[a.length][b.length];
}

/// Normalized Levenshtein similarity in [0.0, 1.0].
double levenshteinSimilarity(String a, String b) {
  if (a.isEmpty && b.isEmpty) return 1.0;
  if (a.isEmpty || b.isEmpty) return 0.0;
  final maxLen = a.length > b.length ? a.length : b.length;
  return 1.0 - levenshteinDistance(a, b) / maxLen;
}

/// Normalized Damerau-Levenshtein similarity in [0.0, 1.0].
double damerauSimilarity(String a, String b) {
  if (a.isEmpty && b.isEmpty) return 1.0;
  if (a.isEmpty || b.isEmpty) return 0.0;
  final maxLen = a.length > b.length ? a.length : b.length;
  return 1.0 - damerauDistance(a, b) / maxLen;
}