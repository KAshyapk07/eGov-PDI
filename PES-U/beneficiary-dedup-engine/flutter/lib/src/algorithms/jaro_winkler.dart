/// Jaro-Winkler string similarity algorithm.
///
/// Measures similarity between two strings with a bias towards
/// strings that share a common prefix. Returns a value between
/// 0.0 (no similarity) and 1.0 (identical strings).
///
/// Particularly effective for name matching where typos tend
/// to occur in the middle/end of names rather than the beginning.
class JaroWinkler {
  /// Compute Jaro similarity between two strings.
  /// Returns a value between 0.0 and 1.0.
  static double jaroSimilarity(String s1, String s2) {
    // TODO: Implement Jaro similarity
    // 1. Count matching characters (within match window)
    // 2. Count transpositions
    // 3. jaro = (matches/len1 + matches/len2 + (matches-transpositions)/matches) / 3
    throw UnimplementedError();
  }

  /// Compute Jaro-Winkler similarity (Jaro + prefix bonus).
  /// Returns a value between 0.0 and 1.0.
  static double similarity(String s1, String s2, {double prefixScale = 0.1}) {
    // TODO: Implement Jaro-Winkler
    // winkler = jaro + (prefixLength * prefixScale * (1 - jaro))
    throw UnimplementedError();
  }
}
