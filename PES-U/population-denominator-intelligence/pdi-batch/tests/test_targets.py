import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box, Point

import config
from features import targets

CODE = config.BOUNDARY_CODE_FIELD


def _units():
    """Two boundaries: one over N'Djamena (catches the register), one far away."""
    return gpd.GeoDataFrame(
        {
            CODE: ["NDJ", "FAR"],
            "population_estimate": [100000, 5000],
            "under5": [20000, 1000],
            "building_count": [500, 0],
            "geometry": [box(14.9, 12.0, 15.2, 12.3), box(20.0, 20.0, 20.1, 20.1)],
        },
        geometry="geometry",
        crs=config.STORAGE_CRS,
    )


def test_registered_frame_none_without_register():
    # A country with no register: the overlay is omitted, other layers still render.
    assert targets.registered_frame(_units(), iso3="KEN") is None


@pytest.mark.skipif(
    not config.REGISTER_INDIVIDUALS_CSV.exists(),
    reason="synthetic register not present",
)
def test_registered_frame_follows_boundary_geometry():
    frame = targets.registered_frame(_units(), iso3=config.REGISTER_ISO3)
    assert frame is not None
    assert set(frame.columns) == {CODE, *targets.REGISTERED_COLUMNS}

    by_code = frame.set_index(CODE)
    # The N'Djamena cell picks up registrations; the far cell gets none.
    assert by_code.loc["NDJ", "registered_population"] > 0
    assert by_code.loc["FAR", "registered_population"] == 0
    # Coverage is registered / estimated where the register covers the boundary,
    # and undefined (no registrations, nothing built) elsewhere -> RED.
    assert 0 < by_code.loc["NDJ", "coverage_ratio"] <= 1
    assert by_code.loc["FAR", "gap_classification"] == "RED"


def _stats_units():
    return gpd.GeoDataFrame(
        {
            CODE: ["A", "B"],
            config.BOUNDARY_NAME_FIELD: ["Alpha", "Beta"],
            "population_estimate": [1000, 500],
            "estimated_households": [200, 100],
            "building_count": [200, 0],
            "under5": [200, 100],
            "total": [1000, 500],
            "geometry": [box(0, 0, 1, 1), box(2, 2, 3, 3)],
        },
        geometry="geometry",
        crs=config.STORAGE_CRS,
    )


def test_build_stats_without_register_is_estimation_only():
    stats = targets.build_stats(_stats_units(), None, None)
    summary = stats["summary"]
    assert summary["totalEstimatedPopulation"] == 1500
    assert summary["totalRegisteredPopulation"] == 0
    assert summary["totalPopulationGap"] == 1500
    assert summary["overallCoverageRatio"] is None
    assert stats["gapDistribution"] == {}
    assert stats["riskDistribution"] == {}


def test_build_stats_with_register_and_invisible():
    registered = pd.DataFrame({
        CODE: ["A", "B"],
        "registered_population": [850, 0],
        "registered_under5": [170, 0],
        "registered_households": [160, 0],
        "coverage_ratio": [0.85, pd.NA],
        "coverage_ratio_under5": [0.85, pd.NA],
        "gap_classification": ["GREEN", "RED"],
    })
    invisible = gpd.GeoDataFrame(
        {"cluster_id": ["A-C0001"], "building_count": [12], "estimated_population": [65],
         "geometry": [Point(0.5, 0.5)]},
        geometry="geometry", crs=config.STORAGE_CRS)

    stats = targets.build_stats(_stats_units(), registered, invisible)
    summary = stats["summary"]
    assert summary["totalRegisteredPopulation"] == 850
    assert summary["totalPopulationGap"] == 650
    assert summary["overallCoverageRatio"] == round(850 / 1500, 4)
    assert summary["invisibleSettlementCount"] == 1
    assert summary["invisibleEstimatedPopulation"] == 65
    assert stats["gapDistribution"]["GREEN"] == {"count": 1, "population": 1000}
    # Highest gap first.
    assert stats["topGapSettlements"][0]["boundaryCode"] == "B"
