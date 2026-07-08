import pytest

import config
from features import gap


@pytest.mark.parametrize(
    "coverage_ratio, registered_population, building_count, expected",
    [
        (0.90, 900, 200, "GREEN"),                 # coverage >= green threshold
        (config.GAP_GREEN_THRESHOLD, 850, 200, "GREEN"),   # exactly at the green cut
        (0.70, 700, 200, "YELLOW"),                # between yellow and green
        (config.GAP_YELLOW_THRESHOLD, 500, 200, "YELLOW"), # exactly at the yellow cut
        (0.30, 300, 200, "RED"),                   # below yellow, still registered
        (0.0, 0, 200, "BLACK"),                    # no registrations but built up -> invisible
        (0.0, 0, 0, "RED"),                        # no registrations and nothing built
        (None, 0, 5, "BLACK"),                     # undefined coverage, buildings present
    ],
)
def test_classify(coverage_ratio, registered_population, building_count, expected):
    assert gap.classify(coverage_ratio, registered_population, building_count) == expected
