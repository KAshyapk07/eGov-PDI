import 'package:test/test.dart';
import 'package:dedup_engine/dedup_engine.dart';

/// A config mirroring the Python engine's weights, expressed generically.
/// Note that NO column name is known to the package — they are all supplied
/// here, and could be anything.
final testConfig = DedupConfig(
  tableName: 'individual',
  idColumn: 'id',
  matchFields: const [
    MatchField(column: 'given_name', strategy: Strategy.nameBest, weight: 0.16),
    MatchField(column: 'given_name', strategy: Strategy.damerau, weight: 0.10),
    MatchField(column: 'given_name', strategy: Strategy.phonetic, weight: 0.08),
    MatchField(column: 'father_name', strategy: Strategy.jaroWinkler, weight: 0.16),
    MatchField(column: 'father_name', strategy: Strategy.damerau, weight: 0.06),
    MatchField(column: 'father_name', strategy: Strategy.phonetic, weight: 0.04),
    MatchField(column: 'family_name', strategy: Strategy.jaroWinkler, weight: 0.08),
    MatchField(column: 'dob', strategy: Strategy.dateTolerant, weight: 0.18),
  ],
  crossFields: const [
    CrossMatchField(
      columnA: 'given_name',
      columnB: 'family_name',
      strategy: CrossStrategy.tokenSorted,
      weight: 0.0, // diagnostic only in this config
    ),
  ],
  proximityFields: const [
    ProximityField(
      latColumn: 'lat',
      lonColumn: 'lon',
      accuracyColumn: 'acc',
      weight: 0.14,
    ),
  ],
  shortCircuits: const [
    ShortCircuitRule(column: 'mobile', verdict: Verdict.duplicate),
  ],
  mismatchRules: const [
    MismatchRule(column: 'gender'),
  ],
  siblingGuard: const SiblingGuard(
    familyColumn: 'father_name',
    distinguishingColumn: 'given_name',
  ),
  duplicateThreshold: 0.82,
  reviewThreshold: 0.62,
);

Map<String, dynamic> person({
  String id = 'x',
  String given = 'Ibrahim',
  String family = 'Saleh',
  String father = 'Ali',
  String gender = 'MALE',
  String dob = '2021-02-16',
  String? mobile,
  double? lat = 12.193385,
  double? lon = 15.071581,
  double? acc = 8.0,
}) {
  return {
    'id': id,
    'given_name': given,
    'family_name': family,
    'father_name': father,
    'gender': gender,
    'dob': dob,
    'mobile': mobile,
    'lat': lat,
    'lon': lon,
    'acc': acc,
  };
}

void main() {
  final scorer = PairScorer(testConfig);

  group('config sanity', () {
    test('weights sum to 1.0', () {
      expect(testConfig.totalWeight, closeTo(1.0, 0.0001));
    });

    test('referencedColumns lists every column used', () {
      final cols = testConfig.referencedColumns;
      expect(cols, contains('given_name'));
      expect(cols, contains('father_name'));
      expect(cols, contains('dob'));
      expect(cols, contains('lat'));
      expect(cols, contains('mobile'));
      expect(cols, contains('gender'));
    });
  });

  group('duplicate detection', () {
    test('EXACT: identical records score ~1.0 and are DUPLICATE', () {
      final a = person(id: 'a');
      final b = person(id: 'b');
      final r = scorer.score(a, b);
      expect(r.verdict, Verdict.duplicate);
      expect(r.score, greaterThan(0.95));
    });

    test('SPELLING: a typo in the given name is still caught', () {
      final a = person(id: 'a', given: 'Ibrahim');
      final b = person(id: 'b', given: 'Ibrahmi');
      final r = scorer.score(a, b);
      expect(r.verdict, Verdict.duplicate);
    });

    test('PHONETIC: Mahamat vs Muhammad is caught', () {
      final a = person(id: 'a', given: 'Mahamat');
      final b = person(id: 'b', given: 'Muhammad');
      final r = scorer.score(a, b);
      expect(r.verdict, anyOf(Verdict.duplicate, Verdict.review));
    });

    test('ABBREVIATION: Ibrahim vs Ibra is caught by containment', () {
      final a = person(id: 'a', given: 'Ibrahim');
      final b = person(id: 'b', given: 'Ibra');
      final r = scorer.score(a, b);
      expect(r.verdict, anyOf(Verdict.duplicate, Verdict.review));
    });

    test('DOB: a day/month swap still scores high', () {
      final a = person(id: 'a', dob: '2021-03-05');
      final b = person(id: 'b', dob: '2021-05-03');
      final r = scorer.score(a, b);
      expect(r.featureScores['dob:dateTolerant'], closeTo(0.95, 0.001));
      expect(r.verdict, Verdict.duplicate);
    });

    test('GPS: a nearby reading still matches', () {
      final a = person(id: 'a', lat: 12.193385, lon: 15.071581);
      final b = person(id: 'b', lat: 12.193900, lon: 15.071900);
      final r = scorer.score(a, b);
      expect(r.verdict, Verdict.duplicate);
    });
  });

  group('rules', () {
    test('MISMATCH: different gender forces CLEAR', () {
      final a = person(id: 'a', gender: 'MALE');
      final b = person(id: 'b', gender: 'FEMALE');
      final r = scorer.score(a, b);
      expect(r.verdict, Verdict.clear);
      expect(r.score, 0.0);
      expect(r.flags, contains('GENDER_MISMATCH'));
    });

    test('SHORT CIRCUIT: identical mobile forces DUPLICATE', () {
      final a = person(id: 'a', given: 'Ibrahim', mobile: '23566703329');
      final b = person(id: 'b', given: 'Fatima', mobile: '23566703329');
      final r = scorer.score(a, b);
      expect(r.verdict, Verdict.duplicate);
      expect(r.score, 1.0);
      expect(r.flags, contains('MOBILE_MATCH'));
    });

    test('empty mobile does NOT short circuit', () {
      final a = person(id: 'a', mobile: '');
      final b = person(id: 'b', mobile: '');
      final r = scorer.score(a, b);
      expect(r.flags, isNot(contains('MOBILE_MATCH')));
    });
  });

  group('non-duplicates', () {
    test('completely different people are CLEAR', () {
      final a = person(
          id: 'a',
          given: 'Ibrahim',
          family: 'Saleh',
          father: 'Ali',
          dob: '2021-02-16');
      final b = person(
          id: 'b',
          given: 'Zubairu',
          family: 'Wamba',
          father: 'Gideon',
          dob: '1975-08-03',
          lat: 12.9,
          lon: 15.9);
      final r = scorer.score(a, b);
      expect(r.verdict, Verdict.clear);
    });
  });

  group('result explanation', () {
    test('featureScores are populated and topSignals works', () {
      final a = person(id: 'a');
      final b = person(id: 'b');
      final r = scorer.score(a, b);
      expect(r.featureScores, isNotEmpty);
      expect(r.topSignals(3).length, 3);
      expect(r.matchedRecord['id'], 'b');
    });
  });

  group('missing data is safe', () {
    test('null values do not crash and simply score 0', () {
      final a = <String, dynamic>{'id': 'a'};
      final b = <String, dynamic>{'id': 'b'};
      final r = scorer.score(a, b);
      expect(r.score, 0.0);
      expect(r.verdict, Verdict.clear);
    });
  });
}
