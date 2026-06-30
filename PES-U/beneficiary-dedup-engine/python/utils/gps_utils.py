"""
utils/gps_utils.py   <->   lib/src/utils/gps_utils.dart

Geographic distance and proximity scoring.

Duplicate registrations usually happen near each other; same household ~ same
coordinates. We score proximity and downweight readings with poor GPS accuracy.

Dart port note: `dart:math` has sin/cos/sqrt/atan2/pi. Direct port.
"""

from math import radians, sin, cos, sqrt, atan2
from typing import Optional


EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres."""
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = (sin(d_lat / 2) ** 2
         + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2)
    return EARTH_RADIUS_KM * 2 * atan2(sqrt(a), sqrt(1 - a))


def proximity_score(
    lat1: Optional[float], lon1: Optional[float],
    lat2: Optional[float], lon2: Optional[float],
    acc1: Optional[float] = None,
    acc2: Optional[float] = None,
    max_radius_km: float = 0.5,
) -> float:
    """
    1.0 at same point, decaying linearly to 0.0 at max_radius_km.
    Poor average GPS accuracy applies a penalty.

    Returns 0.0 if any coordinate is missing.
    Dart port note: use double? params; null-check before computing.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 0.0

    dist = haversine_km(lat1, lon1, lat2, lon2)
    score = 1.0 - dist / max_radius_km
    if score < 0.0:
        score = 0.0

    if acc1 is not None and acc2 is not None:
        avg = (acc1 + acc2) / 2.0
        if avg > 50:
            score *= 0.5
        elif avg > 30:
            score *= 0.75

    return round(score, 4)


def same_household_score(
    lat1: Optional[float], lon1: Optional[float],
    lat2: Optional[float], lon2: Optional[float],
    acc1: Optional[float] = None,
    acc2: Optional[float] = None,
) -> float:
    """Tight 50m-radius proximity — high value strongly implies same dwelling."""
    return proximity_score(lat1, lon1, lat2, lon2, acc1, acc2, max_radius_km=0.05)
