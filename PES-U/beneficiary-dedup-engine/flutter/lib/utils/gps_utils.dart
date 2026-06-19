import 'dart:math';

/// GPS utility functions for proximity-based dedup scoring.
class GpsUtils {
  /// Compute Haversine distance between two GPS coordinates.
  /// Returns distance in meters.
  static double haversineDistance(
    double lat1, double lon1,
    double lat2, double lon2,
  ) {
    const earthRadiusMeters = 6371000.0;
    final dLat = _toRadians(lat2 - lat1);
    final dLon = _toRadians(lon2 - lon1);
    final a = sin(dLat / 2) * sin(dLat / 2) +
        cos(_toRadians(lat1)) * cos(_toRadians(lat2)) *
        sin(dLon / 2) * sin(dLon / 2);
    final c = 2 * atan2(sqrt(a), sqrt(1 - a));
    return earthRadiusMeters * c;
  }

  /// Convert GPS distance to a similarity score (0.0 to 1.0).
  /// Records within 50m get score 1.0, decaying to 0.0 at maxDistanceMeters.
  static double proximityScore(
    double lat1, double lon1,
    double lat2, double lon2, {
    double maxDistanceMeters = 500.0,
  }) {
    final distance = haversineDistance(lat1, lon1, lat2, lon2);
    if (distance <= 50) return 1.0;
    if (distance >= maxDistanceMeters) return 0.0;
    return 1.0 - ((distance - 50) / (maxDistanceMeters - 50));
  }

  static double _toRadians(double degrees) => degrees * pi / 180;
}
