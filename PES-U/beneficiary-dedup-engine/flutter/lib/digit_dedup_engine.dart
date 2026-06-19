library digit_dedup_engine;

// Core engine
export 'src/dedup_engine.dart';
export 'src/matching_service.dart';
export 'src/blocking_strategy.dart';

// Algorithms
export 'src/algorithms/soundex.dart';
export 'src/algorithms/double_metaphone.dart';
export 'src/algorithms/jaro_winkler.dart';
export 'src/algorithms/levenshtein.dart';

// Models
export 'models/dedup_result.dart';
export 'models/candidate_pair.dart';

// Utils
export 'utils/gps_utils.dart';
export 'utils/string_utils.dart';
