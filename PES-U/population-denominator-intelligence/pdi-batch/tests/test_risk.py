import pandas as pd
import pytest

import config
from features import risk


@pytest.mark.parametrize(
    "score, expected",
    [
        (100, "CRITICAL"),
        (config.RISK_CRITICAL_THRESHOLD, "CRITICAL"),
        (config.RISK_CRITICAL_THRESHOLD - 1, "HIGH"),
        (config.RISK_HIGH_THRESHOLD, "HIGH"),
        (config.RISK_MEDIUM_THRESHOLD, "MEDIUM"),
        (config.RISK_MEDIUM_THRESHOLD - 1, "LOW"),
        (0, "LOW"),
    ],
)
def test_priority_for(score, expected):
    assert risk.priority_for(score) == expected


def test_normalize_scales_to_unit_range():
    scaled = risk._normalize(pd.Series([10.0, 20.0, 30.0]))
    assert list(scaled) == [0.0, 0.5, 1.0]


def test_normalize_constant_series_is_zero():
    scaled = risk._normalize(pd.Series([5.0, 5.0, 5.0]))
    assert list(scaled) == [0.0, 0.0, 0.0]


def test_weights_sum_to_one():
    assert sum(config.RISK_WEIGHTS.values()) == pytest.approx(1.0)


def test_factors_json_marks_provisional():
    scores = pd.Series({name: 0.5 for name in config.RISK_WEIGHTS})
    factors = risk._factors_json(scores, building_density=12.0, distance_km=3.0)
    assert factors["past_performance"]["provisional"] is True
    assert factors["missed_children"]["provisional"] is True
    assert factors["population_gap"]["provisional"] is False
    assert factors["building_density"]["buildings_per_km2"] == 12.0
    assert factors["facility_distance"]["distance_to_nearest_km"] == 3.0
