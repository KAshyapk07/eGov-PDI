/// dedup_engine — offline, schema-agnostic beneficiary deduplication.
///
/// Nothing about the host app's database is hardcoded. Table names, column
/// names, comparison strategies, weights, rules and thresholds are all passed
/// in via [DedupConfig].
///
/// The package makes NO network calls — everything runs on-device.
///
///     import 'package:dedup_engine/dedup_engine.dart';
library;

// The engine (public entry point)
export 'src/dedup_engine_base.dart';

// Configuration + results
export 'src/models/dedup_config.dart';
export 'src/models/dedup_result.dart';

// Candidate sources
export 'src/source/candidate_source.dart';
export 'src/source/sql_candidate_source.dart';
export 'src/source/query_builder.dart';

// Scoring
export 'src/scoring/pair_scorer.dart';
export 'src/scoring/strategies.dart';

// Algorithms (exported so callers can use them directly if they wish)
export 'src/algorithms/levenshtein.dart';
export 'src/algorithms/jaro_winkler.dart';
export 'src/algorithms/soundex.dart';
export 'src/algorithms/double_metaphone.dart';

// Utils
export 'src/utils/string_utils.dart';
export 'src/utils/gps_utils.dart';
