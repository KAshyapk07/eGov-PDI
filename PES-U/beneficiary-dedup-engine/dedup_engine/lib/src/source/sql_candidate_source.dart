import '../models/dedup_config.dart';
import 'candidate_source.dart';
import 'query_builder.dart';

/// A function that runs a parameterised SQL query and returns the rows.
///
/// The host app supplies this, which is what lets the package work with ANY
/// SQLite stack. Examples:
///
/// sqflite:
///     final executor = (sql, params) => database.rawQuery(sql, params);
///
/// sqlite3 (synchronous):
///     final executor = (sql, params) async {
///       final result = db.select(sql, params);
///       return result.map((r) => Map<String, dynamic>.from(r)).toList();
///     };
///
/// drift / a repository layer: wrap whatever query method you already have.
typedef QueryExecutor = Future<List<Map<String, dynamic>>> Function(
  String sql,
  List<Object?> params,
);

/// A [CandidateSource] backed by a real SQL database.
///
/// The package never imports a database library. It builds the SQL from the
/// config and hands it to the [QueryExecutor] the host app provided, so the
/// host stays in full control of the connection, transactions and lifecycle.
class SqlCandidateSource implements CandidateSource {
  final QueryExecutor executor;

  const SqlCandidateSource(this.executor);

  @override
  Future<List<Map<String, dynamic>>> fetchCandidates(
    Map<String, dynamic> newRecord,
    DedupConfig config,
  ) async {
    final builder = QueryBuilder(config);
    final query = builder.buildCandidateQuery(newRecord);

    final rows = await executor(query.sql, query.params);

    // SQLite has no phonetic function, so phonetic blocking keys cannot be
    // expressed in SQL. The SQL query only filters on exact and year columns.
    // If any blocking key uses a phoneticColumn, we must post-filter in Dart
    // to ensure each returned row actually satisfies at least one blocking key
    // (either a fully SQL-expressed key or a phonetic key checked here).
    if (builder.needsPhoneticFilter) {
      return rows.where((row) {
        return matchesAnyBlockingKey(newRecord, row, config);
      }).toList();
    }

    return rows;
  }

  /// Debug helper: see the SQL that would be run, without running it.
  SqlQuery previewQuery(Map<String, dynamic> newRecord, DedupConfig config) {
    return QueryBuilder(config).buildCandidateQuery(newRecord);
  }
}
