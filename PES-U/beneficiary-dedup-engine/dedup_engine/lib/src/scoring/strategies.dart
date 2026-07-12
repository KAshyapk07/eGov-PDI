import '../algorithms/jaro_winkler.dart';
import '../algorithms/levenshtein.dart';
import '../algorithms/soundex.dart';
import '../algorithms/double_metaphone.dart';
import '../utils/string_utils.dart';
import '../models/dedup_config.dart';

/// Applies a [Strategy] to a pair of raw values. This is the only place that
/// knows how a generic strategy name maps to a concrete algorithm, which keeps
/// the scorer schema-agnostic.
///
/// All values arrive as `dynamic` because they come straight out of SQLite.

/// Normalize any raw value to a comparable string. Returns '' for null.
String _str(dynamic v) {
  if (v == null) return '';
  return v.toString().trim();
}

/// Parse a value into a DateTime, tolerating the formats SQLite may hold
/// (ISO strings, "dd-MM-yyyy", or an int epoch in millis).
DateTime? parseDate(dynamic v) {
  if (v == null) return null;
  if (v is DateTime) return v;
  if (v is int) return DateTime.fromMillisecondsSinceEpoch(v);

  final s = v.toString().trim();
  if (s.isEmpty) return null;

  // ISO first (yyyy-MM-dd or full ISO timestamp).
  final iso = DateTime.tryParse(s);
  if (iso != null) return iso;

  // dd-MM-yyyy or dd/MM/yyyy
  final parts = s.split(RegExp(r'[-/]'));
  if (parts.length == 3 && parts[0].length <= 2) {
    final d = int.tryParse(parts[0]);
    final m = int.tryParse(parts[1]);
    final y = int.tryParse(parts[2]);
    if (d != null && m != null && y != null) {
      try {
        return DateTime(y, m, d);
      } catch (_) {
        return null;
      }
    }
  }
  return null;
}

/// Exact equality after trim + lowercase.
double exactScore(dynamic a, dynamic b) {
  final sa = _str(a).toLowerCase();
  final sb = _str(b).toLowerCase();
  if (sa.isEmpty || sb.isEmpty) return 0.0;
  return sa == sb ? 1.0 : 0.0;
}

/// Phonetic agreement: Double Metaphone and Soundex combined.
/// 1.0 both agree, 0.5 one agrees, 0.0 neither.
double phoneticScore(dynamic a, dynamic b) {
  final sa = normalizeName(_str(a));
  final sb = normalizeName(_str(b));
  if (sa.isEmpty || sb.isEmpty) return 0.0;

  final m = metaphoneMatch(sa, sb);
  final s = soundexMatch(sa, sb);
  if (m == 1.0 && s == 1.0) return 1.0;
  if (m == 1.0 || s == 1.0) return 0.5;
  return 0.0;
}

/// Prefix / substring containment — catches abbreviations (Ibrahim -> Ibra).
double containmentScore(dynamic a, dynamic b) {
  final sa = normalizeName(_str(a));
  final sb = normalizeName(_str(b));
  if (sa.isEmpty || sb.isEmpty) return 0.0;

  final short = sa.length <= sb.length ? sa : sb;
  final long = sa.length <= sb.length ? sb : sa;
  if (short.length < 3) return 0.0;

  if (long.startsWith(short)) return 1.0;
  if (long.contains(short)) return 0.85;
  return 0.0;
}

/// Jaro-Winkler on normalized names.
double jaroWinklerScore(dynamic a, dynamic b) {
  final sa = normalizeName(_str(a));
  final sb = normalizeName(_str(b));
  if (sa.isEmpty || sb.isEmpty) return 0.0;
  return jaroWinklerSimilarity(sa, sb);
}

/// Damerau-Levenshtein on normalized names.
double damerauScore(dynamic a, dynamic b) {
  final sa = normalizeName(_str(a));
  final sb = normalizeName(_str(b));
  if (sa.isEmpty || sb.isEmpty) return 0.0;
  return damerauSimilarity(sa, sb);
}

/// Best of Jaro-Winkler and containment. The usual choice for a given name,
/// because an abbreviation should not be penalised for being short.
double nameBestScore(dynamic a, dynamic b) {
  final jw = jaroWinklerScore(a, b);
  final c = containmentScore(a, b);
  return jw > c ? jw : c;
}

/// Date comparison with tolerance for transcription errors.
///
///   1.00 exact
///   0.95 day and month swapped (05-03 vs 03-05)
///   0.90 same year+month, within 7 days
///   0.75 same year+month, further apart
///   0.60 same year
///   0.40 one year apart
///   0.00 otherwise / missing
double dateTolerantScore(dynamic a, dynamic b) {
  final da = parseDate(a);
  final db = parseDate(b);
  if (da == null || db == null) return 0.0;

  if (da.year == db.year && da.month == db.month && da.day == db.day) {
    return 1.0;
  }

  // Day/month transposition.
  if (da.year == db.year && da.month == db.day && da.day == db.month) {
    return 0.95;
  }

  final deltaDays = da.difference(db).inDays.abs();

  if (da.year == db.year && da.month == db.month) {
    return deltaDays <= 7 ? 0.90 : 0.75;
  }
  if (da.year == db.year) return 0.60;
  if ((da.year - db.year).abs() == 1) return 0.40;
  return 0.0;
}

/// Numeric closeness: 1.0 when equal, decaying to 0.0 at [maxDelta].
double numericProximityScore(dynamic a, dynamic b, double maxDelta) {
  final na = a is num ? a.toDouble() : double.tryParse(_str(a));
  final nb = b is num ? b.toDouble() : double.tryParse(_str(b));
  if (na == null || nb == null || maxDelta <= 0) return 0.0;

  final delta = (na - nb).abs();
  final score = 1.0 - delta / maxDelta;
  return score < 0.0 ? 0.0 : score;
}

/// Dispatch a single-column [Strategy].
double applyStrategy(Strategy strategy, dynamic a, dynamic b,
    {double? maxDelta}) {
  switch (strategy) {
    case Strategy.exact:
      return exactScore(a, b);
    case Strategy.jaroWinkler:
      return jaroWinklerScore(a, b);
    case Strategy.damerau:
      return damerauScore(a, b);
    case Strategy.phonetic:
      return phoneticScore(a, b);
    case Strategy.containment:
      return containmentScore(a, b);
    case Strategy.nameBest:
      return nameBestScore(a, b);
    case Strategy.dateTolerant:
      return dateTolerantScore(a, b);
    case Strategy.numericProximity:
      return numericProximityScore(a, b, maxDelta ?? 1.0);
  }
}

/// Dispatch a [CrossStrategy] — compares two DIFFERENT columns across the two
/// records.
///
/// [a1]/[b1] are columnA/columnB of record 1.
/// [a2]/[b2] are columnA/columnB of record 2.
double applyCrossStrategy(
  CrossStrategy strategy,
  dynamic a1,
  dynamic b1,
  dynamic a2,
  dynamic b2,
) {
  switch (strategy) {
    case CrossStrategy.swap:
      // columnA of record 1 vs columnB of record 2, and vice versa.
      final cross1 = jaroWinklerScore(a1, b2);
      final cross2 = jaroWinklerScore(b1, a2);
      return (cross1 + cross2) / 2.0;

    case CrossStrategy.tokenSorted:
      // Combine both columns, sort the tokens, compare. Order-independent.
      final full1 = tokenSort(
          '${normalizeName(_str(a1))} ${normalizeName(_str(b1))}'.trim());
      final full2 = tokenSort(
          '${normalizeName(_str(a2))} ${normalizeName(_str(b2))}'.trim());
      if (full1.isEmpty || full2.isEmpty) return 0.0;
      return jaroWinklerSimilarity(full1, full2);
  }
}
