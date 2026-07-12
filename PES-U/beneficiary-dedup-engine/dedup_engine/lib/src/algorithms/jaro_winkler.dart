/// Jaro and Jaro-Winkler string similarity.
///
/// Jaro-Winkler rewards a matching prefix, which suits short personal names.
///   jaroWinklerSimilarity("fatime", "fatima")   -> ~0.9333
///   jaroWinklerSimilarity("mahamat", "mohamed") -> ~0.6679
///
/// All functions return a double in [0.0, 1.0].

/// Plain Jaro similarity.
library; 
double jaroSimilarity(String a, String b) {
  if (a == b) return 1.0;
  final lenA = a.length;
  final lenB = b.length;
  if (lenA == 0 || lenB == 0) return 0.0;

  // Maximum distance apart two characters can be and still count as a match.
  var matchDistance = ((lenA > lenB ? lenA : lenB) ~/ 2) - 1;
  if (matchDistance < 0) matchDistance = 0;

  final aMatches = List<bool>.filled(lenA, false);
  final bMatches = List<bool>.filled(lenB, false);

  var matches = 0;
  var transpositions = 0;

  // Count matching characters.
  for (var i = 0; i < lenA; i++) {
    var start = i - matchDistance;
    if (start < 0) start = 0;
    var end = i + matchDistance + 1;
    if (end > lenB) end = lenB;

    for (var j = start; j < end; j++) {
      if (bMatches[j]) continue;
      if (a[i] != b[j]) continue;
      aMatches[i] = true;
      bMatches[j] = true;
      matches++;
      break;
    }
  }

  if (matches == 0) return 0.0;

  // Count transpositions.
  var k = 0;
  for (var i = 0; i < lenA; i++) {
    if (!aMatches[i]) continue;
    while (!bMatches[k]) {
      k++;
    }
    if (a[i] != b[k]) transpositions++;
    k++;
  }

  final m = matches.toDouble();
  final t = transpositions / 2.0;
  return (m / lenA + m / lenB + (m - t) / m) / 3.0;
}

/// Jaro-Winkler similarity = Jaro plus a common-prefix boost.
///
/// [prefixScale] controls how much a shared prefix boosts the score (0.1 is
/// standard). [maxPrefix] caps how many leading characters count (4 standard).
double jaroWinklerSimilarity(
  String a,
  String b, {
  double prefixScale = 0.1,
  int maxPrefix = 4,
}) {
  final jaro = jaroSimilarity(a, b);
  if (jaro == 0.0) return 0.0;

  // Length of the common prefix, capped at maxPrefix.
  var prefixLen = 0;
  var limit = a.length < b.length ? a.length : b.length;
  if (limit > maxPrefix) limit = maxPrefix;

  for (var i = 0; i < limit; i++) {
    if (a[i] == b[i]) {
      prefixLen++;
    } else {
      break;
    }
  }

  return jaro + prefixLen * prefixScale * (1.0 - jaro);
}
