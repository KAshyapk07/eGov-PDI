/// Result of a deduplication analysis on a set of records.
class DedupResult {
  /// Index of the first record in the original list
  final int recordIndex1;

  /// Index of the second record in the original list
  final int recordIndex2;

  /// Overall similarity score (0.0 to 1.0)
  final double score;

  /// Individual attribute scores
  final Map<String, double> attributeScores;

  /// Whether this pair is classified as a duplicate
  final bool isDuplicate;

  DedupResult({
    required this.recordIndex1,
    required this.recordIndex2,
    required this.score,
    required this.attributeScores,
    required this.isDuplicate,
  });
}
