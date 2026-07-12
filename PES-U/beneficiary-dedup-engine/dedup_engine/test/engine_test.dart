import 'package:test/test.dart';
import 'package:dedup_engine/dedup_engine.dart';

/// A config using entirely made-up column names, to prove the package really
/// is schema-agnostic.
final config = DedupConfig(
  tableName: 'beneficiary',
  idColumn: 'ref',
  matchFields: const [
    MatchField(column: 'first', strategy: Strategy.nameBest, weight: 0.16),
    MatchField(column: 'first', strategy: Strategy.damerau, weight: 0.10),
    MatchField(column: 'first', strategy: Strategy.phonetic, weight: 0.08),
    MatchField(column: 'guardian', strategy: Strategy.jaroWinkler, weight: 0.16),
    MatchField(column: 'guardian', strategy: Strategy.damerau, weight: 0.06),
    MatchField(column: 'guardian', strategy: Strategy.phonetic, weight: 0.04),
    MatchField(column: 'last', strategy: Strategy.jaroWinkler, weight: 0.08),
    MatchField(column: 'birthdate', strategy: Strategy.dateTolerant, weight: 0.18),
  ],
  proximityFields: const [
    ProximityField(
      latColumn: 'y',
      lonColumn: 'x',
      accuracyColumn: 'precision_m',
      weight: 0.14,
    ),
  ],
  shortCircuits: const [
    ShortCircuitRule(column: 'phone'),
  ],
  mismatchRules: const [
    MismatchRule(column: 'sex'),
  ],
  blockingKeys: const [
    BlockingKey(columns: ['zone'], yearColumn: 'birthdate'),
    BlockingKey(columns: ['zone'], phoneticColumn: 'first'),
  ],
  duplicateThreshold: 0.82,
  reviewThreshold: 0.62,
);

Map<String, dynamic> rec({
  required String ref,
  String first = 'Ibrahim',
  String last = 'Saleh',
  String guardian = 'Ali',
  String sex = 'MALE',
  String birthdate = '2021-02-16',
  String? phone,
  String zone = 'ZONE_A',
  double? y = 12.193385,
  double? x = 15.071581,
  double? precision = 8.0,
}) =>
    {
      'ref': ref,
      'first': first,
      'last': last,
      'guardian': guardian,
      'sex': sex,
      'birthdate': birthdate,
      'phone': phone,
      'zone': zone,
      'y': y,
      'x': x,
      'precision_m': precision,
    };

void main() {
  // The existing population.
  final existing = <Map<String, dynamic>>[
    rec(ref: 'e1'), // Ibrahim Saleh — the person we will re-register
    rec(ref: 'e2', first: 'Fatima', last: 'Abakar', guardian: 'Sanda', sex: 'FEMALE'),
    rec(ref: 'e3', first: 'Yacoub', last: 'Baguirmi', guardian: 'Yusuf', birthdate: '2019-09-25'),
    rec(ref: 'e4', first: 'Zubairu', last: 'Wamba', guardian: 'Gideon', birthdate: '1975-08-03', zone: 'ZONE_B'),
  ];

  final engine = DedupEngine(
    config: config,
    source: InMemoryCandidateSource(existing),
  );

  group('config validation', () {
    test('a sane config reports no problems', () {
      expect(engine.validateConfig(), isEmpty);
    });

    test('a bad config is caught', () {
      final bad = DedupConfig(
        tableName: 't',
        idColumn: 'id',
        matchFields: const [
          MatchField(column: 'a', strategy: Strategy.exact, weight: 0.5),
        ],
        duplicateThreshold: 0.5,
        reviewThreshold: 0.8, // inverted!
      );
      final problems =
          DedupEngine(config: bad, source: InMemoryCandidateSource([]))
              .validateConfig();
      expect(problems, isNotEmpty);
      expect(problems.join(' '), contains('duplicateThreshold'));
    });
  });

  group('checkForDuplicates', () {
    test('an exact re-registration is flagged', () async {
      final incoming = rec(ref: 'new1'); // same as e1
      final matches = await engine.checkForDuplicates(incoming);

      expect(matches, isNotEmpty);
      expect(matches.first.idB, 'e1');
      expect(matches.first.verdict, Verdict.duplicate);
      expect(matches.first.score, greaterThan(0.95));
    });

    test('a typo re-registration is still flagged', () async {
      final incoming = rec(ref: 'new2', first: 'Ibrahmi');
      final matches = await engine.checkForDuplicates(incoming);

      expect(matches, isNotEmpty);
      expect(matches.first.idB, 'e1');
      expect(matches.first.verdict, Verdict.duplicate);
    });

    test('a genuinely new person is NOT flagged', () async {
      final incoming = rec(
        ref: 'new3',
        first: 'Bakari',
        last: 'Zerbo',
        guardian: 'Salifou',
        birthdate: '2020-03-14',
      );
      final matches = await engine.checkForDuplicates(incoming);
      expect(matches, isEmpty);
    });

    test('results are sorted by score, highest first', () async {
      final incoming = rec(ref: 'new4');
      final matches =
          await engine.checkForDuplicates(incoming, includeClear: true);

      for (var i = 1; i < matches.length; i++) {
        expect(matches[i - 1].score,
            greaterThanOrEqualTo(matches[i].score));
      }
    });

    test('the matched record comes back for display', () async {
      final incoming = rec(ref: 'new5');
      final matches = await engine.checkForDuplicates(incoming);

      final matched = matches.first.matchedRecord;
      expect(matched['first'], 'Ibrahim');
      expect(matched['last'], 'Saleh');
      expect(matched['guardian'], 'Ali');
    });

    test('topSignals explains why it matched', () async {
      final incoming = rec(ref: 'new6');
      final matches = await engine.checkForDuplicates(incoming);

      final signals = matches.first.topSignals(3);
      expect(signals.length, 3);
      expect(signals.first.value, greaterThan(0.5));
    });
  });

  group('hasDuplicate', () {
    test('true for a re-registration', () async {
      expect(await engine.hasDuplicate(rec(ref: 'n')), isTrue);
    });

    test('false for a new person', () async {
      final fresh = rec(
        ref: 'n',
        first: 'Bakari',
        last: 'Zerbo',
        guardian: 'Salifou',
        birthdate: '2020-03-14',
      );
      expect(await engine.hasDuplicate(fresh), isFalse);
    });
  });

  group('blocking', () {
    test('a record in a different zone with a different year is not fetched',
        () async {
      final source = InMemoryCandidateSource(existing);
      // ZONE_C matches no existing record, and the year is unique.
      final incoming = rec(ref: 'n', zone: 'ZONE_C', birthdate: '1901-01-01');
      final candidates = await source.fetchCandidates(incoming, config);
      expect(candidates, isEmpty);
    });

    test('a record is never compared against itself', () async {
      final source = InMemoryCandidateSource(existing);
      final self = existing.first; // ref e1
      final candidates = await source.fetchCandidates(self, config);
      expect(candidates.any((c) => c['ref'] == 'e1'), isFalse);
    });
  });

  group('query builder', () {
    test('builds parameterised SQL with the configured column names', () {
      final builder = QueryBuilder(config);
      final q = builder.buildCandidateQuery(rec(ref: 'n'));

      expect(q.sql, contains('FROM beneficiary'));
      expect(q.sql, contains('zone = ?'));
      expect(q.sql, contains('LIMIT'));
      // Values are bound, never interpolated.
      expect(q.sql, isNot(contains('ZONE_A')));
      expect(q.params, contains('ZONE_A'));
    });

    test('includes joins when configured', () {
      final joined = DedupConfig(
        tableName: 'individual',
        idColumn: 'client_reference_id',
        joins: const [
          JoinSpec(
            table: 'individual_name',
            on: 'individual_client_reference_id',
          ),
        ],
        matchFields: const [
          MatchField(column: 'given_name', strategy: Strategy.nameBest, weight: 1.0),
        ],
        blockingKeys: const [
          BlockingKey(columns: ['boundary_code']),
        ],
      );
      final q = QueryBuilder(joined)
          .buildCandidateQuery({'boundary_code': 'B1', 'client_reference_id': 'x'});

      expect(q.sql, contains('LEFT JOIN individual_name'));
      expect(q.sql, contains('individual_client_reference_id'));
    });
  });
}
