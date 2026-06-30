# HCM Beneficiary Deduplication — Python Reference Implementation

This is the **Python reference** for the on-device Flutter/Dart deduplication
package (`digit_dedup_engine`). Every file maps 1:1 to a target Dart file, and
the algorithms are written in pure, dependency-free Python so the port is
mechanical.

> The Flutter package is the graded deliverable. This Python tree is where you
> tune algorithms, weights, and thresholds against the labeled dataset before
> porting. No `rapidfuzz` / `jellyfish` / `pandas` — every algorithm is
> hand-implemented so it has a direct Dart equivalent.

## File mapping (Python -> Dart)

| Python (`py_dedup_ref/`)      | Dart (`lib/`)                          |
|-------------------------------|----------------------------------------|
| `digit_dedup_engine.py`       | `digit_dedup_engine.dart` (barrel)     |
| `dedup_engine.py`             | `src/dedup_engine.dart`                |
| `matching_service.py`         | `src/matching_service.dart`            |
| `blocking_strategy.py`        | `src/blocking_strategy.dart`           |
| `algorithms/soundex.py`       | `src/algorithms/soundex.dart`          |
| `algorithms/double_metaphone.py` | `src/algorithms/double_metaphone.dart` |
| `algorithms/jaro_winkler.py`  | `src/algorithms/jaro_winkler.dart`     |
| `algorithms/levenshtein.py`   | `src/algorithms/levenshtein.dart`      |
| `models/dedup_result.py`      | `models/dedup_result.dart`             |
| `models/candidate_pair.py`    | `models/candidate_pair.dart` (+ Beneficiary) |
| `utils/gps_utils.py`          | `utils/gps_utils.dart`                 |
| `utils/string_utils.py`       | `utils/string_utils.dart`              |
| `evaluate.py`                 | *(dev/benchmark only — not ported)*    |

## Two usage paths

**On-device (the real product):** `check_for_duplicates(new_record, local_records)`
in `dedup_engine.py`. One incoming registration vs the worker's local SQLite
records. This is `DedupEngine.checkForDuplicates()` in Dart.

**Benchmark (dev only):** `run_batch(records)` + `evaluate.py`. All-pairs over
the labeled dataset to measure precision/recall/F1 and tune weights.

## Running the benchmark

```bash
python evaluate.py \
  --records dedup_test/dedup_test_records.csv \
  --truth   dedup_test/dedup_ground_truth.csv
```

Reports precision/recall/F1 overall, per duplicate TYPE, and per DIFFICULTY,
against the targets in `dedup_test_summary.json`.

## Coverage of the 9 labeled duplicate types

| Type                | Handled by                                            |
|---------------------|-------------------------------------------------------|
| EXACT_DUPLICATE     | all features high; mobile short-circuit               |
| PHONETIC_VARIATION  | Double Metaphone + Soundex agreement                  |
| SPELLING_ERROR      | Jaro-Winkler + Damerau-Levenshtein                    |
| NAME_ABBREVIATION   | prefix/containment score (`ibrahim` vs `ibra`)        |
| NAME_ORDER_SWAP     | order-independent token-sorted full-name comparison   |
| DOB_VARIATION       | tolerant `dob_score` (swap / +-day / +-year window)   |
| GPS_NEARBY          | Haversine proximity score                             |
| COMBINED_NOISE      | weighted blend of all features                        |
| CROSS_BOUNDARY      | boundary-free blocking rule D + name/dob carry it     |

## Porting notes

- Each file's docstring has a **Dart port note** describing the equivalent
  idiom (e.g. `List<List<int>>` for the DP tables, `Map<String,String>` for the
  diacritic map, `dart:math` for haversine).
- `DEFAULT_WEIGHTS` and `THRESHOLDS` in `matching_service.py` are plain maps —
  port them as `const` and tune in Python first, then copy the final values.
- The explicit `_DIACRITIC_MAP` in `string_utils.py` exists specifically so the
  Dart side needs no Unicode normalization tables.

## Tuning before you port

Threshold and weight tuning should be done here against the real labeled data,
not in Dart. The DUPLICATE threshold drives precision/recall directly; the
REVIEW band drives how aggressive the in-app warning is.
