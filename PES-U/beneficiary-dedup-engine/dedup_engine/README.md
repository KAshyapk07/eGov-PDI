# dedup_engine

Offline, schema-agnostic record deduplication for Dart. Pure Dart — no Flutter
dependency, no network calls, no database library required.

Detects when a record being registered looks like one that already exists.
Runs entirely **on-device** against the local database.

## Table of Contents

- [Installation](#installation)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Configuration Reference](#configuration-reference)
  - [Match Fields](#match-fields)
  - [Cross-Field Comparisons](#cross-field-comparisons)
  - [GPS Proximity](#gps-proximity)
  - [Short-Circuit Rules](#short-circuit-rules)
  - [Mismatch Rules](#mismatch-rules)
  - [Sibling Guard](#sibling-guard)
  - [Blocking Keys](#blocking-keys)
  - [Joins](#joins)
  - [Soft Delete](#soft-delete)
  - [Thresholds](#thresholds)
- [Candidate Sources](#candidate-sources)
  - [InMemoryCandidateSource](#inmemorycandidatesource)
  - [SqlCandidateSource](#sqlcandidatesource)
- [Running a Check](#running-a-check)
- [Understanding Results](#understanding-results)
- [Strategies](#strategies)
- [Handling Campaign Cycles](#handling-campaign-cycles)
- [Integration with Flutter](#integration-with-flutter)
- [SQL Debugging](#sql-debugging)
- [Configuration Validation](#configuration-validation)
- [Performance](#performance)
- [Testing](#testing)
- [API Summary](#api-summary)

## Installation

### Git dependency

Add to your `pubspec.yaml`:

```yaml
dependencies:
  dedup_engine:
    git:
      url: https://github.com/egovernments/pes-university-projects.git
      ref: dedup-engine-sarayu
      path: PES-U/beneficiary-dedup-engine/dedup_engine
```

### Local path (for development)

```yaml
dependencies:
  dedup_engine:
    path: ../path/to/dedup_engine
```

Then run:

```bash
dart pub get       # pure Dart project
flutter pub get    # Flutter project
```

### Requirements

- Dart SDK `>=3.2.0 <4.0.0`
- No runtime dependencies (pure Dart)

## Architecture

```
┌───────────────────────────────────────────────────────┐
│                     DedupEngine                       │
│  checkForDuplicates(newRecord) -> List<DedupResult>   │
│  scorePair(a, b) -> DedupResult                       │
│  hasDuplicate(newRecord) -> bool                      │
└──────────────┬──────────────────────┬─────────────────┘
               │                      │
     ┌─────────▼──────────┐  ┌───────▼────────┐
     │   CandidateSource  │  │   PairScorer    │
     │   (fetch records)  │  │   (score pair)  │
     └─────────┬──────────┘  └───────┬────────┘
               │                      │
     ┌─────────┴──────────┐  ┌───────▼────────┐
     │ InMemory │   Sql   │  │   Strategies   │
     │  Source  │  Source  │  │  (algorithms)  │
     └─────────┴──────────┘  └────────────────┘
```

The package hardcodes **nothing** about your schema. Table names, column names,
comparison strategies, weights, rules and thresholds are all supplied by you in
a `DedupConfig`. The engine never assumes a column called `name` or `dob`
exists.

It also does not depend on a database library. You supply a small function that
runs a query; the package builds the SQL. That means it works with `sqflite`,
`sqlite3`, `drift`, or your own repository layer.

## Quick Start

```dart
import 'package:dedup_engine/dedup_engine.dart';

// 1. Describe your schema and matching rules.
final config = DedupConfig(
  tableName: 'individual',
  idColumn: 'client_reference_id',

  // Pull extra columns from joined tables.
  joins: [
    JoinSpec(table: 'name', on: 'individual_client_reference_id'),
    JoinSpec(table: 'address', on: 'individual_client_reference_id'),
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

  // GPS proximity.
  proximityFields: [
    ProximityField(
      latColumn: 'latitude',
      lonColumn: 'longitude',
      weight: 0.14,
      maxRadiusKm: 0.5,
    ),
  ],

  // Identical mobile number -> certain duplicate, skip scoring.
  shortCircuits: [ShortCircuitRule(column: 'mobile_number')],

  // Different gender -> cannot be the same person.
  // Use valueMap when the DB stores enums as integers but incoming data uses strings.
  mismatchRules: [
    MismatchRule(
      column: 'gender',
      valueMap: {'0': 'male', '1': 'female', '2': 'other'},
    ),
  ],

  // Sibling detection.
  siblingGuard: SiblingGuard(
    familyColumn: 'father_name',
    distinguishingColumn: 'given_name',
  ),

  // Candidate filtering. A record is a candidate if it matches ANY key.
  blockingKeys: [
    BlockingKey(columns: ['boundary_code'], yearColumn: 'date_of_birth'),
    BlockingKey(columns: ['boundary_code'], phoneticColumn: 'given_name'),
  ],

  // Soft-delete support (optional).
  softDeleteColumn: 'isDeleted',

  duplicateThreshold: 0.82,
  reviewThreshold: 0.62,
);

// 2. Tell the package how to run a query.
final source = SqlCandidateSource(
  (sql, params) => database.rawQuery(sql, params),
);

// 3. Build the engine.
final engine = DedupEngine(config: config, source: source);

// 4. Validate at startup.
final problems = engine.validateConfig();
if (problems.isNotEmpty) print(problems.join('\n'));

// 5. Check before saving.
final matches = await engine.checkForDuplicates(newRecord);
if (matches.isNotEmpty) {
  // Show warning to user with matches.first.matchedRecord
}
```

## Configuration Reference

### Match Fields

Each `MatchField` compares a single column between the new record and each
candidate, using a specified strategy. The same column can appear multiple times
with different strategies.

```dart
MatchField(
  column: 'given_name',        // column name in your schema
  strategy: Strategy.nameBest, // comparison algorithm
  weight: 0.16,                // contribution to composite score
)
```

Weights across all match fields, cross fields, and proximity fields should sum
to approximately 1.0.

#### Value Mapping

When a column stores values in a different format than the incoming record (e.g.
an ORM stores enums as integers while the form data uses strings), use
`valueMap` to normalize both sides to a canonical form before comparison:

```dart
MatchField(
  column: 'risk_level',
  strategy: Strategy.exact,
  weight: 0.10,
  valueMap: {'0': 'low', '1': 'medium', '2': 'high'},
)
```

Keys must be **lowercase strings**. The engine converts each raw value to a
lowercase string, looks it up in the map, and uses the mapped value if found.
Values not in the map are passed through as-is. This keeps the config
`const`-compatible (no callbacks needed).

### Cross-Field Comparisons

`CrossMatchField` compares **two different columns** across two records, useful
for detecting name-order swaps (e.g. given name and family name reversed).

```dart
CrossMatchField(
  columnA: 'given_name',
  columnB: 'family_name',
  strategy: CrossStrategy.tokenSorted,
  weight: 0.0,  // set to 0 for diagnostic-only
)
```

### GPS Proximity

`ProximityField` compares latitude/longitude pairs using the Haversine formula.

```dart
ProximityField(
  latColumn: 'latitude',
  lonColumn: 'longitude',
  accuracyColumn: 'location_accuracy',  // optional
  weight: 0.14,
  maxRadiusKm: 0.5,  // score decays to 0 at this distance
)
```

### Short-Circuit Rules

If both records share an identical non-empty value in the specified column, the
engine immediately returns a duplicate verdict **without computing the composite
score**. Useful for unique identifiers like phone numbers.

```dart
ShortCircuitRule(column: 'mobile_number')
// Optionally specify the verdict (default: Verdict.duplicate)
ShortCircuitRule(column: 'national_id', verdict: Verdict.duplicate)
// Use valueMap when stored and incoming formats differ
ShortCircuitRule(column: 'status', valueMap: {'0': 'active', '1': 'inactive'})
```

### Mismatch Rules

If both records have non-empty but **different** values for the column, the
engine immediately returns `Verdict.clear`. Useful for gender, where a mismatch
means it cannot be the same person.

```dart
MismatchRule(column: 'gender')

// When the DB stores gender as an integer enum but incoming data uses strings:
MismatchRule(
  column: 'gender',
  valueMap: {'0': 'male', '1': 'female', '2': 'other'},
)
// DB value 0 -> "male", incoming "MALE" -> "male" -> they match (no mismatch).
// DB value 0 -> "male", incoming "FEMALE" -> "female" -> mismatch -> Verdict.clear.
```

### Sibling Guard

Demotes a `duplicate` verdict to `review` when records appear to be siblings
rather than the same person: same household location + same guardian + different
first name.

```dart
SiblingGuard(
  familyColumn: 'father_name',
  distinguishingColumn: 'given_name',
  householdMin: 0.90,       // proximity must be at least this
  familyMin: 0.85,          // familyColumn similarity >= this
  distinguishingMax: 0.75,  // distinguishingColumn similarity < this
)
```

### Blocking Keys

Blocking keys determine which existing records are **worth comparing** against
the new record. Without them, every record would be compared against every
other (slow). A record is a candidate if it matches **any** blocking key.

```dart
// Exact match on boundary + same birth year
BlockingKey(columns: ['boundary_code'], yearColumn: 'date_of_birth')

// Exact match on boundary + phonetically similar given name
BlockingKey(columns: ['boundary_code'], phoneticColumn: 'given_name')
```

**Important:** SQLite has no built-in phonetic function. Phonetic blocking keys
cannot be pushed into SQL. The SQL query fetches a wider set, and Dart-side
post-filtering enforces the phonetic constraint.

### Joins

If the data you need lives across multiple tables, specify joins:

```dart
JoinSpec(
  table: 'name',                              // table to join
  on: 'individual_client_reference_id',        // FK column in joined table
  left: true,                                  // LEFT JOIN (default)
)
```

The generated SQL joins on `{joinTable}.{on} = {baseTable}.{idColumn}`.

### Soft Delete

If your schema uses a soft-delete flag, records marked as deleted are excluded
from candidate queries:

```dart
DedupConfig(
  // ...
  softDeleteColumn: 'isDeleted',
)
```

The generated SQL adds: `WHERE (isDeleted IS NULL OR isDeleted = 0 OR isDeleted = 'false')`

### Thresholds

```dart
DedupConfig(
  duplicateThreshold: 0.82,  // score >= this -> Verdict.duplicate
  reviewThreshold: 0.62,     // score >= this -> Verdict.review
  maxCandidates: 500,        // max records to fetch per check
)
```

## Candidate Sources

The engine fetches records through a `CandidateSource` abstraction, so it never
imports a database library.

### InMemoryCandidateSource

Takes a plain list. Use in tests or when records are already in memory.

```dart
final source = InMemoryCandidateSource([
  {'client_reference_id': '1', 'given_name': 'Ibrahim', ...},
  {'client_reference_id': '2', 'given_name': 'Fatima',  ...},
]);
final engine = DedupEngine(config: config, source: source);
```

### SqlCandidateSource

Wraps a function that executes parameterised SQL. Works with any SQLite library.

```dart
// sqflite
final source = SqlCandidateSource(
  (sql, params) => database.rawQuery(sql, params),
);

// drift
final source = SqlCandidateSource(
  (sql, params) async {
    final result = await db.customSelect(sql,
      variables: params.map((p) => Variable(p)).toList(),
    ).get();
    return result.map((r) => r.data).toList();
  },
);

// sqlite3 (synchronous)
final source = SqlCandidateSource(
  (sql, params) async {
    final result = db.select(sql, params);
    return result.map((r) => Map<String, dynamic>.from(r)).toList();
  },
);
```

The `QueryExecutor` typedef:

```dart
typedef QueryExecutor = Future<List<Map<String, dynamic>>> Function(
  String sql,
  List<Object?> params,
);
```

### Custom CandidateSource

Implement the interface for full control:

```dart
class MyCandidateSource implements CandidateSource {
  @override
  Future<List<Map<String, dynamic>>> fetchCandidates(
    Map<String, dynamic> newRecord,
    DedupConfig config,
  ) async {
    // Your custom candidate retrieval logic.
    // Use matchesAnyBlockingKey() to reuse the blocking logic.
  }
}
```

## Running a Check

```dart
final newRecord = {
  'client_reference_id': uuid,
  'given_name': 'Ibrahim',
  'family_name': 'Saleh',
  'father_name': 'Ali',
  'gender': 'MALE',
  'date_of_birth': '2021-02-16',
  'boundary_code': 'WARD_01',
  'latitude': 12.193385,
  'longitude': 15.071581,
};

// Check for duplicates (returns only duplicate + review verdicts).
final matches = await engine.checkForDuplicates(newRecord);

// Include all scored pairs (useful for debugging/tuning).
final all = await engine.checkForDuplicates(newRecord, includeClear: true);

// Simple boolean check.
final isDuplicate = await engine.hasDuplicate(newRecord);

// Score a specific pair without querying.
final result = engine.scorePair(recordA, recordB);
```

## Understanding Results

Each `DedupResult` contains:

| Field           | Type                        | Description                                    |
|-----------------|-----------------------------|------------------------------------------------|
| `score`         | `double`                    | Composite score, 0.0 - 1.0                    |
| `verdict`       | `Verdict`                   | `duplicate`, `review`, or `clear`              |
| `matchedRecord` | `Map<String, dynamic>`      | The full existing row, ready to display        |
| `featureScores` | `Map<String, double>`       | Per-comparison breakdown (e.g. `given_name:nameBest -> 0.94`) |
| `flags`         | `List<String>`              | Notes: `MOBILE_MATCH`, `GENDER_MISMATCH`, `POSSIBLE_SIBLING` |
| `idA`           | `String`                    | ID of the incoming record                      |
| `idB`           | `String`                    | ID of the matched existing record              |

```dart
final match = matches.first;
print('Score: ${(match.score * 100).round()}%');
print('Verdict: ${match.verdict}');
print('Matched: ${match.matchedRecord['given_name']}');

// Top reasons for the match.
final signals = match.topSignals(3);
for (final s in signals) {
  print('  ${s.key}: ${(s.value * 100).round()}%');
}
// Output:
//   given_name:nameBest: 94%
//   date_of_birth:dateTolerant: 100%
//   father_name:jaroWinkler: 88%
```

Convenience getters:

```dart
match.isDuplicate  // verdict == Verdict.duplicate
match.needsReview  // verdict == Verdict.review
match.isClear      // verdict == Verdict.clear
```

## Strategies

### Single-column strategies

| Strategy                    | What it catches                                     | Score range |
|-----------------------------|-----------------------------------------------------|-------------|
| `Strategy.exact`            | Identical values (after trim + lowercase)           | 0.0 or 1.0 |
| `Strategy.jaroWinkler`      | Close strings; good for short personal names        | 0.0 - 1.0  |
| `Strategy.damerau`          | Typos, including swapped adjacent letters           | 0.0 - 1.0  |
| `Strategy.phonetic`         | Transliteration variants (Mahamat / Muhammad)       | 0.0, 0.5, or 1.0 |
| `Strategy.containment`      | Abbreviations (Ibrahim -> Ibra)                     | 0.0, 0.85, or 1.0 |
| `Strategy.nameBest`         | Best of jaroWinkler + containment; use for names    | 0.0 - 1.0  |
| `Strategy.dateTolerant`     | DOB typos: day/month swap, off-by-one, +/- 1 year  | 0.0 - 1.0  |
| `Strategy.numericProximity` | Close numbers (requires `maxDelta`)                 | 0.0 - 1.0  |

### Cross-field strategies

| CrossStrategy               | What it catches                               |
|-----------------------------|-----------------------------------------------|
| `CrossStrategy.swap`        | Given/family name recorded in the wrong order |
| `CrossStrategy.tokenSorted` | Order-independent full-name comparison        |

### Phonetic algorithms

The package includes Double Metaphone and Soundex implementations. These handle
transliteration variants common in multilingual contexts (Chad, Sub-Saharan
Africa). Name normalization includes transliteration rules for common patterns:
`ou->u`, `dj->j`, `kh->k`, `gh->g`, `ph->f`, `ei/ai/ey->e`.

### Date tolerance levels

| Condition              | Score |
|------------------------|-------|
| Exact match            | 1.00  |
| Day/month swapped      | 0.95  |
| Same year+month, <= 7d | 0.90  |
| Same year+month, > 7d  | 0.75  |
| Same year              | 0.60  |
| One year apart         | 0.40  |
| Otherwise              | 0.00  |

## Handling Campaign Cycles

In multi-cycle deployments (e.g. polio vaccination campaigns), the same person
legitimately appears across cycles. The engine returns **every** match above the
threshold. The host app decides what a match means.

### The rule

- Match in the **same cycle** = real duplicate. **Block the save.**
- Match in a **different cycle** = expected history. **Informational only.**

### Implementation

```dart
final matches = await engine.checkForDuplicates(newRecord);
final currentCycle = newRecord['cycle'];

final sameCycle = matches
    .where((m) => m.matchedRecord['cycle'] == currentCycle)
    .toList();

final pastCycles = matches
    .where((m) => m.matchedRecord['cycle'] != currentCycle)
    .toList();

if (sameCycle.isNotEmpty) {
  // Block: show warning, let user decide.
} else {
  // Save normally. Show past-cycle history as info.
}
```

## Integration with Flutter

### Provider pattern

Wrap the engine in a `Provider` so executors and widgets can access it via
`context.read<DedupEngine>()`:

```dart
import 'package:dedup_engine/dedup_engine.dart';
import 'package:provider/provider.dart';

Provider<DedupEngine>(
  create: (_) {
    final config = DedupConfig(
      tableName: 'individual',
      idColumn: 'client_reference_id',
      // ... your full config ...
    );

    final source = SqlCandidateSource(
      (sql, params) => yourDatabase.rawQuery(sql, params),
    );

    return DedupEngine(config: config, source: source);
  },
  child: YourApp(),
)
```

### Using in a form submission

```dart
Future<void> onSubmit(BuildContext context) async {
  final engine = context.read<DedupEngine>();
  final newRecord = buildRecordFromForm();

  final matches = await engine.checkForDuplicates(newRecord);

  if (matches.isEmpty) {
    await saveRecord(newRecord);
    return;
  }

  // Show duplicate review dialog.
  final decision = await showDuplicateDialog(context, matches);

  if (decision == 'CREATE') {
    await saveRecord(newRecord);
  } else if (decision == 'LINK') {
    // Link to existing record instead of creating new.
    final existingId = matches.first.matchedRecord['client_reference_id'];
    await linkToExisting(existingId);
  }
}
```

### Flow builder integration

For apps using an action-executor pattern, create an executor:

```dart
class DedupCheckExecutor extends ActionExecutor {
  @override
  Future<Map<String, dynamic>> execute(
    ActionConfig action,
    BuildContext context,
    Map<String, dynamic> contextData,
  ) async {
    final engine = context.read<DedupEngine>();
    final entities = contextData['entities'] as List;

    // Convert your entity model to a plain map.
    final newRecord = entityToMap(entities.first);

    final matches = await engine.checkForDuplicates(newRecord);

    if (matches.isEmpty) {
      contextData['dedupDecision'] = 'CREATE';
    } else {
      // Show popup, await user decision.
      final decision = await showDedupPopup(context, matches);
      contextData['dedupDecision'] = decision;
    }

    return contextData;
  }
}
```

## SQL Debugging

Preview the generated SQL without executing it:

```dart
final source = SqlCandidateSource(myExecutor);
final query = source.previewQuery(newRecord, config);

print(query.sql);
// SELECT individual.*, name.*, address.*
// FROM individual
// LEFT JOIN name ON name.individual_client_reference_id = individual.client_reference_id
// LEFT JOIN address ON address.individual_client_reference_id = individual.client_reference_id
// WHERE ((boundary_code = ? AND CAST(strftime('%Y', date_of_birth) AS INTEGER) = ?)
//   OR (boundary_code = ?))
// AND (individual.isDeleted IS NULL OR individual.isDeleted = 0 OR individual.isDeleted = 'false')
// LIMIT 500

print(query.params);
// [WARD_01, 2021, WARD_01]
```

Check if phonetic post-filtering is needed:

```dart
final builder = QueryBuilder(config);
print(builder.needsPhoneticFilter);  // true if any key uses phoneticColumn
```

## Configuration Validation

Call `validateConfig()` once at startup to catch common mistakes:

```dart
final problems = engine.validateConfig();
for (final p in problems) {
  print('Config warning: $p');
}
```

Checks performed:
- Weights sum to ~1.0
- At least one match field is configured
- `duplicateThreshold > reviewThreshold`
- Blocking keys are present (warns about performance if missing)
- `numericProximity` fields have a `maxDelta` set

## Performance

- **Blocking keys** are critical. They reduce the candidate set from the entire
  table to a small subset (typically 2-10 records per query). Without them,
  every record is compared against every other.
- **Target latency:** < 200ms per check on low-end devices.
- **`maxCandidates`** caps the number of records fetched (default 500).
- Phonetic blocking keys add a Dart-side post-filter. If performance is
  critical, precompute metaphone codes as a stored column and block on that
  column with exact matching instead.
- All algorithms (Jaro-Winkler, Damerau-Levenshtein, Soundex, Double Metaphone)
  are pure Dart with no FFI overhead.

## Testing

The package includes 58 tests covering algorithms, scoring, blocking, and
end-to-end engine behavior. Run them with:

```bash
cd dedup_engine
dart test
```

Write your own tests using `InMemoryCandidateSource`:

```dart
import 'package:dedup_engine/dedup_engine.dart';
import 'package:test/test.dart';

void main() {
  test('detects similar names', () async {
    final config = DedupConfig(
      tableName: 't',
      idColumn: 'id',
      matchFields: [
        MatchField(column: 'name', strategy: Strategy.jaroWinkler, weight: 1.0),
      ],
      duplicateThreshold: 0.85,
      reviewThreshold: 0.70,
    );

    final engine = DedupEngine(
      config: config,
      source: InMemoryCandidateSource([
        {'id': '1', 'name': 'Ibrahim'},
        {'id': '2', 'name': 'Mohamed'},
      ]),
    );

    final results = await engine.checkForDuplicates({'id': '3', 'name': 'Ibrahima'});
    expect(results, isNotEmpty);
    expect(results.first.matchedRecord['name'], equals('Ibrahim'));
  });
}
```

## API Summary

### DedupEngine

| Method                  | Returns              | Description                                |
|-------------------------|----------------------|--------------------------------------------|
| `checkForDuplicates(record, {includeClear})` | `Future<List<DedupResult>>` | Check a record against existing data |
| `scorePair(a, b)`       | `DedupResult`        | Score one specific pair                    |
| `hasDuplicate(record)`  | `Future<bool>`       | Convenience: any match at duplicate level? |
| `validateConfig()`      | `List<String>`       | List configuration problems                |

### DedupConfig

| Property            | Type                      | Description                          |
|---------------------|---------------------------|--------------------------------------|
| `tableName`         | `String`                  | Base table name                      |
| `idColumn`          | `String`                  | Primary/unique ID column             |
| `joins`             | `List<JoinSpec>`          | Tables to join for extra columns     |
| `matchFields`       | `List<MatchField>`        | Single-column comparisons            |
| `crossFields`       | `List<CrossMatchField>`   | Cross-column comparisons             |
| `proximityFields`   | `List<ProximityField>`    | GPS proximity comparisons            |
| `shortCircuits`     | `List<ShortCircuitRule>`  | Instant-match rules                  |
| `mismatchRules`     | `List<MismatchRule>`      | Instant-reject rules                 |
| `siblingGuard`      | `SiblingGuard?`           | Sibling detection                    |
| `blockingKeys`      | `List<BlockingKey>`       | Candidate filtering                  |
| `softDeleteColumn`  | `String?`                 | Soft-delete flag column              |
| `duplicateThreshold`| `double`                  | Score for duplicate verdict (0.82)   |
| `reviewThreshold`   | `double`                  | Score for review verdict (0.62)      |
| `maxCandidates`     | `int`                     | Max records per check (500)          |
| `totalWeight`       | `double` (getter)         | Sum of all weights (should be ~1.0)  |
| `referencedColumns` | `Set<String>` (getter)    | All columns the config reads         |

### DedupResult

| Property         | Type                      | Description                          |
|------------------|---------------------------|--------------------------------------|
| `score`          | `double`                  | Composite score 0.0 - 1.0           |
| `verdict`        | `Verdict`                 | `duplicate`, `review`, `clear`       |
| `matchedRecord`  | `Map<String, dynamic>`    | Full row of the matched record       |
| `featureScores`  | `Map<String, double>`     | Per-comparison score breakdown       |
| `flags`          | `List<String>`            | Diagnostic flags                     |
| `topSignals(k)`  | `List<MapEntry>`          | Top k scoring features               |
| `isDuplicate`    | `bool`                    | Convenience getter                   |
| `needsReview`    | `bool`                    | Convenience getter                   |
| `isClear`        | `bool`                    | Convenience getter                   |

### Utility classes

| Class                     | Description                                      |
|---------------------------|--------------------------------------------------|
| `InMemoryCandidateSource` | List-backed source for tests                     |
| `SqlCandidateSource`      | SQL-backed source via `QueryExecutor`             |
| `QueryBuilder`            | Generates SQL from config (used internally)       |
| `PairScorer`              | Scores a pair against config (used internally)    |

### Algorithms (directly usable)

```dart
import 'package:dedup_engine/dedup_engine.dart';

// String similarity
jaroWinklerSimilarity('ibrahim', 'ibrahima');  // 0.975
damerauSimilarity('ibrahim', 'ibrahm');        // 0.857

// Phonetic
soundexCode('Muhammad');         // 'M530'
metaphoneCode('Muhammad');       // 'MHMT'
soundexMatch('Mahamat', 'Muhammad');   // 1.0
metaphoneMatch('Mahamat', 'Muhammad'); // 1.0

// GPS
haversineKm(12.19, 15.07, 12.20, 15.08);  // ~1.4 km

// Name normalization (handles transliteration)
normalizeName('Ousmane');  // 'usman'
```
