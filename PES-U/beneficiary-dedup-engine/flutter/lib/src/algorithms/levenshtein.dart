/// Levenshtein edit distance algorithm.
///
/// Computes the minimum number of single-character edits
/// (insertions, deletions, substitutions) required to transform
/// one string into another.
class Levenshtein {
  /// Compute the Levenshtein edit distance between two strings.
  static int distance(String s1, String s2) {
    // TODO: Implement Levenshtein distance using dynamic programming
    throw UnimplementedError();
  }

  /// Compute normalized similarity (0.0 to 1.0) from edit distance.
  static double similarity(String s1, String s2) {
    // TODO: 1 - (distance / max(len(s1), len(s2)))
    throw UnimplementedError();
  }
}
