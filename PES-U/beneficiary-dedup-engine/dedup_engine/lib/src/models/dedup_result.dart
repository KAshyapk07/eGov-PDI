import 'dedup_config.dart' show Verdict;

/// The result of scoring one candidate pair.
///
/// [featureScores] carries every individual comparison so the host app can
/// explain the match to the user ("matched on: given_name 0.94, dob 1.00").
class DedupResult {
  /// Id of the incoming record.
  final String idA;

  /// Id of the existing record it was compared against.
  final String idB;

  /// Composite score in [0.0, 1.0].
  final double score;

  final Verdict verdict;

  /// Per-comparison scores, keyed by a readable label
  /// (e.g. "given_name:phonetic").
  final Map<String, double> featureScores;

  /// Notes such as "MOBILE_MATCH", "GENDER_MISMATCH", "POSSIBLE_SIBLING".
  final List<String> flags;

  /// The full row of the matched existing record, so the host app can display
  /// it without a second query.
  final Map<String, dynamic> matchedRecord;

  const DedupResult({
    required this.idA,
    required this.idB,
    required this.score,
    required this.verdict,
    this.featureScores = const {},
    this.flags = const [],
    this.matchedRecord = const {},
  });

  bool get isDuplicate => verdict == Verdict.duplicate;
  bool get needsReview => verdict == Verdict.review;
  bool get isClear => verdict == Verdict.clear;

  /// The highest-scoring features — useful for a "why did this match?" line.
  List<MapEntry<String, double>> topSignals([int k = 3]) {
    final entries = featureScores.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    return entries.take(k).toList();
  }

  @override
  String toString() =>
      'DedupResult($idB, score: ${score.toStringAsFixed(3)}, $verdict)';
}
