import '../models/dedup_config.dart';
import '../algorithms/double_metaphone.dart';
import '../utils/string_utils.dart' show normalizeName, yearOf;

/// A SQL statement plus its bound parameters.
class SqlQuery {
  final String sql;
  final List<Object?> params;

  const SqlQuery(this.sql, this.params);

  @override
  String toString() => '$sql  -- params: $params';
}

/// Builds the candidate-fetch SQL from a [DedupConfig].
///
/// This class produces SQL *text* and *parameters*; it does not execute
/// anything. That keeps it independent of which SQLite package the host app
/// uses — sqflite, sqlite3, drift, or a repository layer can all take the
/// output of [buildCandidateQuery] and run it.
///
/// All values are bound as parameters (never string-interpolated), so the
/// query is injection-safe even though the column names come from config.
class QueryBuilder {
  final DedupConfig config;

  const QueryBuilder(this.config);

  /// Qualified reference to the id column of the base table.
  String get _qualifiedId => '${config.tableName}.${config.idColumn}';

  /// The SELECT + FROM + JOIN preamble, shared by every query.
  String _selectFrom() {
    final buf = StringBuffer();
    buf.write('SELECT ${config.tableName}.*');

    // Pull in the joined tables' columns too.
    for (final j in config.joins) {
      buf.write(', ${j.table}.*');
    }

    buf.write(' FROM ${config.tableName}');

    for (final j in config.joins) {
      final kind = j.left ? 'LEFT JOIN' : 'JOIN';
      buf.write(
        ' $kind ${j.table} ON ${j.table}.${j.on} = $_qualifiedId',
      );
    }

    return buf.toString();
  }

  /// Build the query that fetches candidates worth scoring against
  /// [newRecord].
  ///
  /// Each [BlockingKey] becomes one OR'd group in the WHERE clause. A record
  /// is a candidate if it satisfies ANY key.
  ///
  /// Phonetic blocking cannot be done in plain SQLite (there is no Soundex or
  /// Metaphone function), so a phonetic key is widened here: it is dropped
  /// from the SQL and enforced afterwards in Dart. See [needsPhoneticFilter].
  SqlQuery buildCandidateQuery(Map<String, dynamic> newRecord) {
    final clauses = <String>[];
    final params = <Object?>[];

    for (final key in config.blockingKeys) {
      final parts = <String>[];

      for (final col in key.columns) {
        final v = newRecord[col];
        if (v == null || v.toString().trim().isEmpty) {
          // A key requiring a column the new record lacks cannot be used.
          parts.clear();
          break;
        }
        parts.add('$col = ?');
        params.add(v);
      }

      // Year blocking: compare the 4-digit year.
      final yc = key.yearColumn;
      if (yc != null) {
        final year = yearOf(newRecord[yc]);
        if (year == null) {
          parts.clear();
        } else {
          // Works for ISO 'yyyy-...' text dates, the common SQLite storage.
          parts.add("CAST(strftime('%Y', $yc) AS INTEGER) = ?");
          params.add(year);
        }
      }

      // NOTE: phoneticColumn is deliberately NOT added to the SQL — SQLite has
      // no phonetic function. If a key is phonetic-only, it would produce an
      // empty clause, which we skip; the Dart-side filter still applies.

      if (parts.isNotEmpty) {
        clauses.add('(${parts.join(' AND ')})');
      }
    }

    final buf = StringBuffer(_selectFrom());

    // Always exclude the record itself, if it already has an id.
    final newId = newRecord[config.idColumn];

    final conditions = <String>[];

    if (clauses.isNotEmpty) {
      conditions.add('(${clauses.join(' OR ')})');
    }

    if (newId != null) {
      conditions.add('$_qualifiedId != ?');
      params.add(newId);
    }

    // Exclude soft-deleted records.
    final delCol = config.softDeleteColumn;
    if (delCol != null) {
      conditions.add(
        '(${config.tableName}.$delCol IS NULL '
        'OR ${config.tableName}.$delCol = 0 '
        "OR ${config.tableName}.$delCol = 'false')",
      );
    }

    if (conditions.isNotEmpty) {
      buf.write(' WHERE ${conditions.join(' AND ')}');
    }

    buf.write(' LIMIT ${config.maxCandidates}');
    return SqlQuery(buf.toString(), params);
  }

  /// True if any blocking key uses a phonetic column. When true, the rows
  /// returned by [buildCandidateQuery] are a SUPERSET and should be filtered
  /// in Dart with [passesPhoneticBlocking].
  bool get needsPhoneticFilter =>
      config.blockingKeys.any((k) => k.phoneticColumn != null);

  /// Dart-side phonetic blocking, applied to rows returned by the SQL query.
  ///
  /// Returns true if the candidate satisfies at least one key that the SQL
  /// could fully express, OR satisfies a phonetic key.
  static bool passesPhoneticBlocking(
    Map<String, dynamic> newRecord,
    Map<String, dynamic> candidate,
    DedupConfig config,
  ) {
    for (final key in config.blockingKeys) {
      final pc = key.phoneticColumn;
      if (pc == null) continue;

      final a = normalizeName(newRecord[pc]?.toString());
      final b = normalizeName(candidate[pc]?.toString());
      if (a.isEmpty || b.isEmpty) continue;

      if (metaphoneCode(a) == metaphoneCode(b)) return true;
    }
    return false;
  }

}
