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
///     final result = db.select(sql, params);
///       return result.map((r) => `Map<String, dynamic>`.from(r)).toList();
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

    // SQLite has no phonetic function, so a phonetic blocking key cannot be
    // expressed in SQL. If one is configured, the SQL result is a superset:
    // a row is kept if it satisfied a SQL-expressible key OR the phonetic one.
    //
    // The SQL already filtered on the expressible keys, so every returned row
    // is valid. The phonetic key can only ADD candidates, and those would need
    // a full scan to find — which we deliberately avoid on-device. Document
    // this: pair a phonetic key with an exact column (e.g. boundary) so it is
    // still expressible.
    return rows;
  }

  /// Debug helper: see the SQL that would be run, without running it.
  SqlQuery previewQuery(Map<String, dynamic> newRecord, DedupConfig config) {
    return QueryBuilder(config).buildCandidateQuery(newRecord);
  }
}
