import '../models/dedup_config.dart';
import '../algorithms/double_metaphone.dart';
import '../utils/string_utils.dart';

/// Where candidate records come from.
///
/// The engine never talks to a database directly — it asks a [CandidateSource]
/// for the records worth comparing against. This keeps the package independent
/// of which SQLite plugin (sqflite, drift, sqlite3, a repository layer...) the
/// host app happens to use: they simply supply an implementation.
///
/// Two implementations ship with the package:
///   * [InMemoryCandidateSource]  — a plain list; used in tests.
///   * SqliteCandidateSource      — queries a real database (see sqlite_source.dart).
abstract class CandidateSource {
  /// Return the records worth scoring against [newRecord].
  ///
  /// Implementations should honour [DedupConfig.blockingKeys] to narrow the
  /// search, and [DedupConfig.maxCandidates] to cap the result size.
  Future<List<Map<String, dynamic>>> fetchCandidates(
    Map<String, dynamic> newRecord,
    DedupConfig config,
  );
}

/// Shared blocking logic: does [candidate] satisfy ANY of the blocking keys
/// when compared against [newRecord]?
///
/// A record is a candidate if it matches at least one key. Each key may
/// require exact matches on some columns, a phonetic match on another, and/or
/// the same year on a date column.
///
/// This is exposed so a custom [CandidateSource] can reuse the exact same
/// blocking semantics the SQL implementation uses.
bool matchesAnyBlockingKey(
  Map<String, dynamic> newRecord,
  Map<String, dynamic> candidate,
  DedupConfig config,
) {
  // No blocking keys configured -> everything is a candidate.
  if (config.blockingKeys.isEmpty) return true;

  for (final key in config.blockingKeys) {
    if (_matchesKey(newRecord, candidate, key)) return true;
  }
  return false;
}

bool _matchesKey(
  Map<String, dynamic> a,
  Map<String, dynamic> b,
  BlockingKey key,
) {
  // Every exact column must match (and be non-empty).
  for (final col in key.columns) {
    final va = a[col]?.toString().trim() ?? '';
    final vb = b[col]?.toString().trim() ?? '';
    if (va.isEmpty || vb.isEmpty) return false;
    if (va.toLowerCase() != vb.toLowerCase()) return false;
  }

  // Phonetic column: codes must match.
  final pc = key.phoneticColumn;
  if (pc != null) {
    final va = normalizeName(a[pc]?.toString());
    final vb = normalizeName(b[pc]?.toString());
    if (va.isEmpty || vb.isEmpty) return false;
    if (metaphoneCode(va) != metaphoneCode(vb)) return false;
  }

  // Year column: the year part must match.
  final yc = key.yearColumn;
  if (yc != null) {
    final ya = _yearOf(a[yc]);
    final yb = _yearOf(b[yc]);
    if (ya == null || yb == null) return false;
    if (ya != yb) return false;
  }

  // An empty key (no columns, no phonetic, no year) matches nothing —
  // guard against a misconfiguration silently allowing everything.
  if (key.columns.isEmpty && pc == null && yc == null) return false;

  return true;
}

int? _yearOf(dynamic v) {
  if (v == null) return null;
  if (v is DateTime) return v.year;

  final s = v.toString().trim();
  if (s.isEmpty) return null;

  final iso = DateTime.tryParse(s);
  if (iso != null) return iso.year;

  // dd-MM-yyyy / dd/MM/yyyy
  final parts = s.split(RegExp(r'[-/]'));
  if (parts.length == 3) {
    // Year is whichever part has 4 digits.
    for (final p in parts) {
      if (p.length == 4) {
        final y = int.tryParse(p);
        if (y != null) return y;
      }
    }
  }
  return null;
}

/// A [CandidateSource] backed by a plain in-memory list.
///
/// Use this in tests, or when the host app already holds the relevant records
/// in memory and does not want a database round trip.
class InMemoryCandidateSource implements CandidateSource {
  final List<Map<String, dynamic>> records;

  const InMemoryCandidateSource(this.records);

  @override
  Future<List<Map<String, dynamic>>> fetchCandidates(
    Map<String, dynamic> newRecord,
    DedupConfig config,
  ) async {
    final newId = newRecord[config.idColumn]?.toString();
    final out = <Map<String, dynamic>>[];

    for (final r in records) {
      // Never compare a record against itself.
      final rid = r[config.idColumn]?.toString();
      if (newId != null && rid != null && rid == newId) continue;

      if (matchesAnyBlockingKey(newRecord, r, config)) {
        out.add(r);
        if (out.length >= config.maxCandidates) break;
      }
    }
    return out;
  }
}
