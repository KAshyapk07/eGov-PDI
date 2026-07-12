import 'dart:math' as math;

/// Geographic distance and proximity scoring.
///
/// Duplicate registrations usually happen near each other; the same household
/// is at roughly the same coordinates. We score proximity and downweight
/// readings with poor GPS accuracy.

const double earthRadiusKm = 6371.0;

double _radians(double deg) => deg * math.pi / 180.0;

/// Great-circle distance between two points, in kilometres.
double haversineKm(double lat1, double lon1, double lat2, double lon2) {
  final dLat = _radians(lat2 - lat1);
  final dLon = _radians(lon2 - lon1);

  final a = math.sin(dLat / 2) * math.sin(dLat / 2) +
      math.cos(_radians(lat1)) *
          math.cos(_radians(lat2)) *
          math.sin(dLon / 2) *
          math.sin(dLon / 2);

  return earthRadiusKm * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a));
}

double _round4(double v) => (v * 10000).round() / 10000;

/// 1.0 at the same point, decaying linearly to 0.0 at [maxRadiusKm].
/// Poor average GPS accuracy applies a penalty.
/// Returns 0.0 if any coordinate is null.
double proximityScore(
  double? lat1,
  double? lon1,
  double? lat2,
  double? lon2, {
  double? acc1,
  double? acc2,
  double maxRadiusKm = 0.5,
}) {
  if (lat1 == null || lon1 == null || lat2 == null || lon2 == null) {
    return 0.0;
  }

  final dist = haversineKm(lat1, lon1, lat2, lon2);
  var score = 1.0 - dist / maxRadiusKm;
  if (score < 0.0) score = 0.0;

  if (acc1 != null && acc2 != null) {
    final avg = (acc1 + acc2) / 2.0;
    if (avg > 50) {
      score *= 0.5;
    } else if (avg > 30) {
      score *= 0.75;
    }
  }

  return _round4(score);
}

/// Tight 50 m radius proximity — a high value strongly implies the same
/// dwelling.
double sameHouseholdScore(
  double? lat1,
  double? lon1,
  double? lat2,
  double? lon2, {
  double? acc1,
  double? acc2,
}) {
  return proximityScore(
    lat1,
    lon1,
    lat2,
    lon2,
    acc1: acc1,
    acc2: acc2,
    maxRadiusKm: 0.05,
  );
}
