import 'models/dedup_config.dart';
import 'models/dedup_result.dart';
import 'scoring/pair_scorer.dart';
import 'source/candidate_source.dart';

/// The public entry point.
///
/// Give it a [DedupConfig] (which describes the host app's schema and the
/// matching rules) and a [CandidateSource] (which knows how to fetch records),
/// then call [checkForDuplicates] with each new record before saving it.
///
/// Everything runs on-device. The package makes no network calls.
///
/// ```dart
/// final engine = DedupEngine(
///   config: myConfig,
///   source: SqlCandidateSource((sql, params) => db.rawQuery(sql, params)),
/// );
///
/// final matches = await engine.checkForDuplicates(newRecord);
/// if (matches.isNotEmpty) {
///   // show the field worker a warning with matches.first.matchedRecord
/// }
/// ```
class DedupEngine {
  final DedupConfig config;
  final CandidateSource source;

  late final PairScorer _scorer;

  DedupEngine({
    required this.config,
    required this.source,
  }) {
    _scorer = PairScorer(config);
  }

  /// Check [newRecord] against existing records.
  ///
  /// Returns the potential duplicates, highest score first. By default only
  /// [Verdict.duplicate] and [Verdict.review] results are returned — the ones
  /// worth showing a user. Pass `includeClear: true` to get everything scored
  /// (useful for debugging or tuning).
  Future<List<DedupResult>> checkForDuplicates(
    Map<String, dynamic> newRecord, {
    bool includeClear = false,
  }) async {
    final candidates = await source.fetchCandidates(newRecord, config);

    final results = <DedupResult>[];
    for (final candidate in candidates) {
      final result = _scorer.score(newRecord, candidate);
      if (includeClear || result.verdict != Verdict.clear) {
        results.add(result);
      }
    }

    results.sort((a, b) => b.score.compareTo(a.score));
    return results;
  }

  /// Score one specific pair. Useful for testing a configuration, or when the
  /// host app already has both records in hand.
  DedupResult scorePair(
    Map<String, dynamic> a,
    Map<String, dynamic> b,
  ) {
    return _scorer.score(a, b);
  }

  /// True if [newRecord] has at least one match at or above the duplicate
  /// threshold. A convenience for the common "block the save?" question.
  Future<bool> hasDuplicate(Map<String, dynamic> newRecord) async {
    final results = await checkForDuplicates(newRecord);
    return results.any((r) => r.verdict == Verdict.duplicate);
  }

  /// Validate the configuration. Returns a list of human-readable problems;
  /// an empty list means the config looks sane.
  ///
  /// Call this once at startup — a misweighted config silently produces bad
  /// scores, and this catches the common mistakes.
  List<String> validateConfig() {
    final problems = <String>[];

    final total = config.totalWeight;
    if ((total - 1.0).abs() > 0.01) {
      problems.add(
        'Weights sum to ${total.toStringAsFixed(3)}, expected ~1.0. '
        'Scores will not be on a 0-1 scale.',
      );
    }

    if (config.matchFields.isEmpty &&
        config.crossFields.isEmpty &&
        config.proximityFields.isEmpty) {
      problems.add('No match fields configured — nothing will ever match.');
    }

    if (config.duplicateThreshold <= config.reviewThreshold) {
      problems.add(
        'duplicateThreshold (${config.duplicateThreshold}) should be greater '
        'than reviewThreshold (${config.reviewThreshold}).',
      );
    }

    if (config.blockingKeys.isEmpty) {
      problems.add(
        'No blocking keys — every record will be compared against every other, '
        'which may be slow on a large table.',
      );
    }

    for (final f in config.matchFields) {
      if (f.strategy == Strategy.numericProximity && f.maxDelta == null) {
        problems.add(
          'MatchField "${f.column}" uses numericProximity but has no maxDelta; '
          'it will always score 0.',
        );
      }
    }

    return problems;
  }
}
