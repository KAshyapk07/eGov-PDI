# Beneficiary Deduplication Engine - Flutter Package

Offline-capable fuzzy matching package for detecting duplicate beneficiary registrations in DIGIT HCM mobile app.

## Overview

Detects duplicate beneficiary registrations on mobile devices using:
- Phonetic algorithms (Soundex, Double Metaphone)
- String similarity (Jaro-Winkler, Levenshtein)
- GPS proximity scoring (Haversine distance)
- Multi-attribute weighted matching

Designed to work entirely offline on the mobile device.

## Package Structure

```
lib/
  digit_dedup_engine.dart        - Public API (library barrel file)
  src/
    dedup_engine.dart            - Main orchestrator
    matching_service.dart        - Multi-attribute scoring
    blocking_strategy.dart       - Phonetic blocking for search space reduction
    algorithms/
      soundex.dart               - Soundex phonetic encoding
      double_metaphone.dart      - Double Metaphone encoding
      jaro_winkler.dart          - Jaro-Winkler string similarity
      levenshtein.dart           - Levenshtein edit distance
  models/
    dedup_result.dart            - Dedup result model
    candidate_pair.dart          - Candidate pair model
  utils/
    gps_utils.dart               - Haversine distance and proximity scoring
    string_utils.dart            - Name normalization utilities
```

## Pattern

This package follows the same structure as `digit_data_converter` in the Flutter packages. See `flutter/packages/digit_data_converter/` for reference.

## Usage

```dart
import 'package:digit_dedup_engine/digit_dedup_engine.dart';

final engine = DedupEngine(matchThreshold: 0.85);
final results = engine.findDuplicates(beneficiaryRecords);

for (final result in results) {
  print('Records ${result.recordIndex1} and ${result.recordIndex2}: '
        'score ${result.score}');
}
```
