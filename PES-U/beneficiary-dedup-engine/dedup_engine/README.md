# dedup_engine

Offline, schema-agnostic record deduplication. Pure Dart — no Flutter dependency, no network calls, no database library required.

Warns a field worker when the record they are registering looks like one that
already exists. Runs entirely **on-device** — the package makes no network
calls and opens no database of its own.

## Design

The package hardcodes **nothing** about your schema. Table names, column names,
comparison strategies, weights, rules and thresholds are all supplied by you in
a `DedupConfig`. The engine never assumes a column called `name` or `dob`
exists.

It also does not depend on a database library. You supply a small function that
runs a query; the package builds the SQL. That means it works with `sqflite`,
`sqlite3`, `drift`, or your own repository layer.

## Quick start

```dart
import 'package:dedup_engine/dedup_engine.dart';

// 1. Describe your schema and matching rules.
final config = DedupConfig(
  tableName: 'individual',
  idColumn: 'client_reference_id',

  // Pull extra columns in from other tables.
  joins: [
    JoinSpec(table: 'individual_name',
             on: 'individual_client_reference_id'),
    JoinSpec(table: 'individual_address',
             on: 'related_client_reference_id'),
  ],

  // Single-column comparisons. Weights should total ~1.0.
  matchFields: [
    MatchField(column: 'given_name',    strategy: Strategy.nameBest,     weight: 0.16),
    MatchField(column: 'given_name',    strategy: Strategy.damerau,      weight: 0.10),
    MatchField(column: 'given_name',    strategy: Strategy.phonetic,     weight: 0.08),
    MatchField(column: 'father_name',   strategy: Strategy.jaroWinkler,  weight: 0.16),
    MatchField(column: 'father_name',   strategy: Strategy.damerau,      weight: 0.06),
    MatchField(column: 'father_name',   strategy: Strategy.phonetic,     weight: 0.04),
    MatchField(column: 'family_name',   strategy: Strategy.jaroWinkler,  weight: 0.08),
    MatchField(column: 'date_of_birth', strategy: Strategy.dateTolerant, weight: 0.18),
  ],

  // GPS is a lat/lon pair, so it has its own spec.
  proximityFields: [
    ProximityField(
      latColumn: 'latitude',
      lonColumn: 'longitude',
      accuracyColumn: 'location_accuracy',
      weight: 0.14,
    ),
  ],

  // Identical mobile number -> certain duplicate, skip scoring.
  shortCircuits: [
    ShortCircuitRule(column: 'mobile_number'),
  ],

  // Different gender -> cannot be the same person.
  mismatchRules: [
    MismatchRule(column: 'gender'),
  ],

  // Same house + same father + different first name -> probably a sibling,
  // so demote a DUPLICATE verdict to REVIEW.
  siblingGuard: SiblingGuard(
    familyColumn: 'father_name',
    distinguishingColumn: 'given_name',
  ),

  // Which records are even worth comparing. A record is a candidate if it
  // matches ANY key. Keep these narrow — they are what makes it fast.
  blockingKeys: [
    BlockingKey(columns: ['boundary_code'], yearColumn: 'date_of_birth'),
    BlockingKey(columns: ['boundary_code'], phoneticColumn: 'given_name'),
  ],

  duplicateThreshold: 0.82,
  reviewThreshold: 0.62,
);

// 2. Tell the package how to run a query. (sqflite shown; any stack works.)
final source = SqlCandidateSource(
  (sql, params) => database.rawQuery(sql, params),
);

// 3. Build the engine.
final engine = DedupEngine(config: config, source: source);

// Check the config once at startup — it catches common mistakes.
final problems = engine.validateConfig();
if (problems.isNotEmpty) print(problems.join('\n'));
```

## Using it

Call this before saving a new registration:

```dart
final newRecord = {
  'client_reference_id': uuid,
  'given_name': 'Ibrahim',
  'family_name': 'Saleh',
  'father_name': 'Ali',
  'gender': 'MALE',
  'date_of_birth': '2021-02-16',
  'boundary_code': 'POLIO_CHAD_CH_01_06_02',
  'latitude': 12.193385,
  'longitude': 15.071581,
  'location_accuracy': 8.0,
};

final matches = await engine.checkForDuplicates(newRecord);

if (matches.isNotEmpty) {
  // Show the warning. matches are sorted, highest score first.
  final top = matches.first;

  showWarning(
    title: 'Warning: could be a duplicate',
    score: top.score,                 // 0.0 - 1.0
    verdict: top.verdict,             // duplicate | review
    existing: top.matchedRecord,      // the full row, ready to display
    reasons: top.topSignals(3),       // e.g. [given_name:nameBest -> 1.00, ...]
  );
} else {
  await save(newRecord);
}
```

Or, for a simple yes/no:

```dart
if (await engine.hasDuplicate(newRecord)) {
  // block the save until the worker confirms
}
```

## Strategies

| Strategy                    | What it catches                                    |
|-----------------------------|----------------------------------------------------|
| `Strategy.exact`            | identical values                                    |
| `Strategy.jaroWinkler`      | close strings; good for short personal names        |
| `Strategy.damerau`          | typos, including swapped adjacent letters           |
| `Strategy.phonetic`         | transliteration variants (Mahamat / Muhammad)       |
| `Strategy.containment`      | abbreviations (Ibrahim -> Ibra)                     |
| `Strategy.nameBest`         | best of jaroWinkler + containment; use for names    |
| `Strategy.dateTolerant`     | DOB typos: day/month swap, off-by-one, +/- one year |
| `Strategy.numericProximity` | close numbers (set `maxDelta`)                      |

Cross-field strategies compare two *different* columns across the two records:

| CrossStrategy             | What it catches                                     |
|---------------------------|-----------------------------------------------------|
| `CrossStrategy.swap`      | given/family name recorded in the wrong order       |
| `CrossStrategy.tokenSorted` | the same, order-independent                       |

## Notes

**Blocking is what keeps it fast.** Without blocking keys, every record is
compared against every other. Pair a phonetic key with an exact column (such as
a boundary or village code) so the query stays narrow — SQLite has no phonetic
function, so a phonetic-only key cannot be pushed into SQL.

**Weights should sum to ~1.0**, otherwise the composite score is not on a 0–1
scale and the thresholds lose their meaning. `validateConfig()` checks this.

**Records are plain `Map<String, dynamic>`** — exactly what SQLite returns, so
no conversion layer is needed.

## Testing without a database

`InMemoryCandidateSource` takes a plain list, so the whole engine can be tested
with no database at all:

```dart
final engine = DedupEngine(
  config: config,
  source: InMemoryCandidateSource(myRecords),
);
```
