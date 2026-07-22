/// Configuration for the dedup engine.
///
/// NOTHING about the caller's schema is hardcoded in this package. Table
/// names, column names, strategies, weights and thresholds are all supplied
/// here by the integrator.

/// The comparison strategies the package can apply to a column.
library; 
enum Strategy {
  /// Exact string equality (after trim + lowercase). 1.0 or 0.0.
  exact,

  /// Jaro-Winkler string similarity. Good for short personal names.
  jaroWinkler,

  /// Damerau-Levenshtein similarity. Good for typos / transpositions.
  damerau,

  /// Phonetic agreement (Double Metaphone + Soundex). Catches
  /// transliteration variants such as Mahamat / Muhammad.
  phonetic,

  /// Prefix / substring containment. Catches abbreviations
  /// (Ibrahim -> Ibra).
  containment,

  /// Best of jaroWinkler and containment. The usual choice for a given name.
  nameBest,

  /// Date comparison with tolerance for transcription errors: day/month
  /// swaps, off-by-one days, +/- one year.
  dateTolerant,

  /// Numeric closeness, scaled by [MatchField.maxDelta].
  numericProximity,
}

/// Strategies that compare TWO DIFFERENT columns across the two records.
enum CrossStrategy {
  /// Compare columnA of record 1 against columnB of record 2, and vice versa.
  /// This is what catches a given/family name-order swap.
  swap,

  /// Order-independent comparison of the two columns combined: the tokens of
  /// (columnA + columnB) are sorted before comparing, so field order does not
  /// matter at all.
  tokenSorted,
}

/// The verdict for a scored pair.
enum Verdict { duplicate, review, clear }

/// One single-column comparison contributing to the composite score.
class MatchField {
  /// Column name in the caller's schema.
  final String column;

  /// How to compare it.
  final Strategy strategy;

  /// Contribution to the composite score. Weights across all fields
  /// (match + cross + proximity) should sum to ~1.0.
  final double weight;

  /// Only used by [Strategy.numericProximity]: the delta at which the score
  /// decays to 0.
  final double? maxDelta;

  /// Optional mapping from raw stored values to canonical forms.
  ///
  /// Keys should be **lowercase**. Before comparison the engine converts the
  /// raw value to a lowercase string and looks it up here. If found, the
  /// mapped value is used; otherwise the raw value is passed through as-is.
  ///
  /// Example — Drift stores gender as an integer enum:
  /// ```dart
  /// valueMap: {'0': 'male', '1': 'female', '2': 'other'},
  /// ```
  final Map<String, String>? valueMap;

  const MatchField({
    required this.column,
    required this.strategy,
    required this.weight,
    this.maxDelta,
    this.valueMap,
  });
}

/// A comparison between two DIFFERENT columns, crossed between the records.
class CrossMatchField {
  final String columnA;
  final String columnB;
  final CrossStrategy strategy;
  final double weight;

  const CrossMatchField({
    required this.columnA,
    required this.columnB,
    required this.strategy,
    required this.weight,
  });
}

/// A geographic proximity comparison. Latitude and longitude are inherently a
/// pair, so they get their own spec rather than being two MatchFields.
class ProximityField {
  final String latColumn;
  final String lonColumn;

  /// Optional GPS accuracy column; if given, poor accuracy reduces the score.
  final String? accuracyColumn;

  final double weight;

  /// Distance (km) at which the proximity score decays to 0.
  final double maxRadiusKm;

  const ProximityField({
    required this.latColumn,
    required this.lonColumn,
    this.accuracyColumn,
    required this.weight,
    this.maxRadiusKm = 0.5,
  });
}

/// If both records have a non-empty, EQUAL value in [column], immediately
/// return [verdict] without computing the composite score.
///
/// Typical use: an identical mobile number means a near-certain duplicate.
class ShortCircuitRule {
  final String column;
  final Verdict verdict;

  /// Optional mapping from raw stored values to canonical forms.
  /// See [MatchField.valueMap] for details.
  final Map<String, String>? valueMap;

  const ShortCircuitRule({
    required this.column,
    this.verdict = Verdict.duplicate,
    this.valueMap,
  });
}

/// If both records have a non-empty value in [column] and those values
/// DIFFER, immediately return [Verdict.clear].
///
/// Typical use: a gender mismatch means it cannot be the same person.
class MismatchRule {
  final String column;

  /// Optional mapping from raw stored values to canonical forms.
  /// See [MatchField.valueMap] for details.
  ///
  /// Example — compare gender stored as integer with gender as string:
  /// ```dart
  /// MismatchRule(
  ///   column: 'gender',
  ///   valueMap: {'0': 'male', '1': 'female', '2': 'other'},
  /// ),
  /// ```
  final Map<String, String>? valueMap;

  const MismatchRule({required this.column, this.valueMap});
}

/// A guard that DEMOTES a duplicate verdict to review when a suspicious
/// pattern is present — e.g. same household + same father but a different
/// given name is more likely a sibling than a duplicate.
class SiblingGuard {
  /// Column whose high similarity suggests the same family (e.g. father name).
  final String familyColumn;

  /// Column whose LOW similarity suggests different people (e.g. given name).
  final String distinguishingColumn;

  /// The proximity field must score at least this high (same dwelling).
  final double householdMin;

  /// familyColumn similarity must be at least this high.
  final double familyMin;

  /// distinguishingColumn similarity must be BELOW this to trigger.
  final double distinguishingMax;

  const SiblingGuard({
    required this.familyColumn,
    required this.distinguishingColumn,
    this.householdMin = 0.90,
    this.familyMin = 0.85,
    this.distinguishingMax = 0.75,
  });
}

/// A join from the base table to another table holding more columns.
class JoinSpec {
  /// The table to join in.
  final String table;

  /// The column IN [table] that points back at the base table's id column.
  final String on;

  /// Use a LEFT JOIN (default) so a missing row never drops the record.
  final bool left;

  const JoinSpec({
    required this.table,
    required this.on,
    this.left = true,
  });
}

/// One blocking rule: a set of columns that must match exactly for a record to
/// be considered a candidate. If [phoneticColumn] is set, its phonetic code
/// must also match.
///
/// A record is a candidate if it satisfies ANY blocking key (they are OR'd).
class BlockingKey {
  /// Columns that must match exactly (may be empty if only phonetic is used).
  final List<String> columns;

  /// Optional column compared by phonetic code rather than exact value.
  final String? phoneticColumn;

  /// Optional column compared by year only (useful for dates of birth).
  final String? yearColumn;

  const BlockingKey({
    this.columns = const [],
    this.phoneticColumn,
    this.yearColumn,
  });
}

/// The full configuration.
class DedupConfig {
  // ── Where the data lives ────────────────────────────────────────────────
  final String tableName;
  final String idColumn;
  final List<JoinSpec> joins;

  // ── What to compare ─────────────────────────────────────────────────────
  final List<MatchField> matchFields;
  final List<CrossMatchField> crossFields;
  final List<ProximityField> proximityFields;

  // ── Rules ───────────────────────────────────────────────────────────────
  final List<ShortCircuitRule> shortCircuits;
  final List<MismatchRule> mismatchRules;
  final SiblingGuard? siblingGuard;

  // ── Candidate selection ─────────────────────────────────────────────────
  final List<BlockingKey> blockingKeys;

  /// Maximum candidates to fetch for one incoming record.
  final int maxCandidates;

  /// Optional column holding a soft-delete flag (e.g. "isDeleted"). When set,
  /// the SQL query excludes rows where this column is true/1/'true'.
  final String? softDeleteColumn;

  // ── Verdict thresholds ──────────────────────────────────────────────────
  final double duplicateThreshold;
  final double reviewThreshold;

  const DedupConfig({
    required this.tableName,
    required this.idColumn,
    this.joins = const [],
    this.matchFields = const [],
    this.crossFields = const [],
    this.proximityFields = const [],
    this.shortCircuits = const [],
    this.mismatchRules = const [],
    this.siblingGuard,
    this.blockingKeys = const [],
    this.maxCandidates = 500,
    this.softDeleteColumn,
    this.duplicateThreshold = 0.82,
    this.reviewThreshold = 0.62,
  });

  /// Sum of every weight in the config. Should be ~1.0; use this to check a
  /// configuration is sane before running.
  double get totalWeight {
    var sum = 0.0;
    for (final f in matchFields) {
      sum += f.weight;
    }
    for (final f in crossFields) {
      sum += f.weight;
    }
    for (final f in proximityFields) {
      sum += f.weight;
    }
    return sum;
  }

  /// Every column this config reads. Used by the query builder to know what
  /// to SELECT.
  Set<String> get referencedColumns {
    final cols = <String>{idColumn};
    for (final f in matchFields) {
      cols.add(f.column);
    }
    for (final f in crossFields) {
      cols.add(f.columnA);
      cols.add(f.columnB);
    }
    for (final f in proximityFields) {
      cols.add(f.latColumn);
      cols.add(f.lonColumn);
      if (f.accuracyColumn != null) cols.add(f.accuracyColumn!);
    }
    for (final r in shortCircuits) {
      cols.add(r.column);
    }
    for (final r in mismatchRules) {
      cols.add(r.column);
    }
    for (final k in blockingKeys) {
      cols.addAll(k.columns);
      if (k.phoneticColumn != null) cols.add(k.phoneticColumn!);
      if (k.yearColumn != null) cols.add(k.yearColumn!);
    }
    final g = siblingGuard;
    if (g != null) {
      cols.add(g.familyColumn);
      cols.add(g.distinguishingColumn);
    }
    return cols;
  }
}
