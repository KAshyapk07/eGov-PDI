import '../models/dedup_config.dart';
import '../models/dedup_result.dart';
import '../utils/gps_utils.dart';
import 'strategies.dart';

/// Scores a pair of records against a [DedupConfig].
///
/// Records are plain `Map<String, dynamic>` — column name to value — which is
/// exactly what SQLite hands back. The scorer never assumes a column exists;
/// a missing column simply scores 0 for that feature.
class PairScorer {
  final DedupConfig config;

  const PairScorer(this.config);

  /// Score [a] (the incoming record) against [b] (an existing record).
  DedupResult score(Map<String, dynamic> a, Map<String, dynamic> b) {
    final idA = a[config.idColumn]?.toString() ?? '';
    final idB = b[config.idColumn]?.toString() ?? '';

    // ── Rule: hard mismatch (e.g. different gender) ─────────────────────
    for (final rule in config.mismatchRules) {
      final va = a[rule.column]?.toString().trim().toLowerCase() ?? '';
      final vb = b[rule.column]?.toString().trim().toLowerCase() ?? '';
      if (va.isNotEmpty && vb.isNotEmpty && va != vb) {
        return DedupResult(
          idA: idA,
          idB: idB,
          score: 0.0,
          verdict: Verdict.clear,
          flags: ['${rule.column.toUpperCase()}_MISMATCH'],
          matchedRecord: b,
        );
      }
    }

    // ── Rule: short circuit (e.g. identical mobile number) ──────────────
    for (final rule in config.shortCircuits) {
      final va = a[rule.column]?.toString().trim() ?? '';
      final vb = b[rule.column]?.toString().trim() ?? '';
      if (va.isNotEmpty && vb.isNotEmpty && va == vb) {
        return DedupResult(
          idA: idA,
          idB: idB,
          score: 1.0,
          verdict: rule.verdict,
          featureScores: {'${rule.column}:exact': 1.0},
          flags: ['${rule.column.toUpperCase()}_MATCH'],
          matchedRecord: b,
        );
      }
    }

    final features = <String, double>{};
    var composite = 0.0;

    // ── Single-column match fields ──────────────────────────────────────
    for (final f in config.matchFields) {
      final s = applyStrategy(
        f.strategy,
        a[f.column],
        b[f.column],
        maxDelta: f.maxDelta,
      );
      features['${f.column}:${f.strategy.name}'] = s;
      composite += s * f.weight;
    }

    // ── Cross-field comparisons (name-order swap etc.) ───────────────────
    for (final f in config.crossFields) {
      final s = applyCrossStrategy(
        f.strategy,
        a[f.columnA],
        a[f.columnB],
        b[f.columnA],
        b[f.columnB],
      );
      features['${f.columnA}x${f.columnB}:${f.strategy.name}'] = s;
      composite += s * f.weight;
    }

    // ── Proximity (lat/lon pairs) ───────────────────────────────────────
    var householdScore = 0.0;
    for (final f in config.proximityFields) {
      final latA = _toDouble(a[f.latColumn]);
      final lonA = _toDouble(a[f.lonColumn]);
      final latB = _toDouble(b[f.latColumn]);
      final lonB = _toDouble(b[f.lonColumn]);

      double? accA;
      double? accB;
      if (f.accuracyColumn != null) {
        accA = _toDouble(a[f.accuracyColumn!]);
        accB = _toDouble(b[f.accuracyColumn!]);
      }

      final s = proximityScore(
        latA,
        lonA,
        latB,
        lonB,
        acc1: accA,
        acc2: accB,
        maxRadiusKm: f.maxRadiusKm,
      );
      features['${f.latColumn}:proximity'] = s;
      composite += s * f.weight;

      // Tight same-dwelling score, used by the sibling guard.
      final h = sameHouseholdScore(latA, lonA, latB, lonB,
          acc1: accA, acc2: accB);
      if (h > householdScore) householdScore = h;
    }

    composite = _round4(composite);

    // ── Verdict ─────────────────────────────────────────────────────────
    var verdict = Verdict.clear;
    if (composite >= config.duplicateThreshold) {
      verdict = Verdict.duplicate;
    } else if (composite >= config.reviewThreshold) {
      verdict = Verdict.review;
    }

    // ── Guard: possible sibling ─────────────────────────────────────────
    final flags = <String>[];
    final guard = config.siblingGuard;
    if (guard != null) {
      final familySim = jaroWinklerScore(
        a[guard.familyColumn],
        b[guard.familyColumn],
      );
      final distinguishSim = nameBestScore(
        a[guard.distinguishingColumn],
        b[guard.distinguishingColumn],
      );

      if (householdScore >= guard.householdMin &&
          familySim >= guard.familyMin &&
          distinguishSim < guard.distinguishingMax) {
        flags.add('POSSIBLE_SIBLING');
        if (verdict == Verdict.duplicate) verdict = Verdict.review;
      }
    }

    return DedupResult(
      idA: idA,
      idB: idB,
      score: composite,
      verdict: verdict,
      featureScores: features,
      flags: flags,
      matchedRecord: b,
    );
  }

  static double? _toDouble(dynamic v) {
    if (v == null) return null;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString().trim());
  }

  static double _round4(double v) => (v * 10000).round() / 10000;
}
