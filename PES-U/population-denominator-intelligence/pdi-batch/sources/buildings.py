"""VIDA combined Open Buildings reader: load, confidence-filter, and clip to the campaign area.

The source is a country-wide GeoParquet that merges Google Open Buildings v3, Microsoft, and
OSM footprints (D8 - raw stays on disk). Only the rows whose footprint bbox intersects the
campaign boundary bbox are read (predicate pushdown via the GeoParquet ``bbox`` covering
column), then footprints are clipped exactly to the boundary polygons by a representative-point
``within`` join. Only buildings inside a boundary are returned, tagged with boundary_code.

Confidence is only carried on Google-sourced rows; Microsoft and OSM footprints have a null
confidence and are kept regardless of the threshold.
"""

import geopandas as gpd

import config
from sources.boundaries import load_boundaries

_OUTPUT_COLUMNS = ["geometry", "centroid", "area_m2", "confidence", "bf_source", "boundary_code"]


def _confidence_ok(buildings):
    """Keep Google footprints above the threshold, and all null-confidence (Microsoft/OSM) ones."""
    confidence = buildings["confidence"]
    return confidence.isna() | (confidence >= config.BUILDING_CONFIDENCE_THRESHOLD)


def _read_in_bbox(bounds):
    """Footprints whose bbox intersects ``bounds`` (minx, miny, maxx, maxy)."""
    try:
        buildings = gpd.read_parquet(config.BUILDINGS_PARQUET, bbox=tuple(bounds))
    except ValueError:
        # Parquet without a covering-bbox column: read all, then filter by bounding box.
        minx, miny, maxx, maxy = bounds
        buildings = gpd.read_parquet(config.BUILDINGS_PARQUET).cx[minx:maxx, miny:maxy]
    return buildings.to_crs(config.STORAGE_CRS)


def clip_to_boundaries(boundaries):
    """Buildings whose representative point lies within a boundary, tagged with boundary_code."""
    boundaries = boundaries.to_crs(config.STORAGE_CRS)

    buildings = _read_in_bbox(boundaries.total_bounds)
    buildings = buildings[_confidence_ok(buildings)]
    buildings = buildings.rename(columns={"area_in_meters": "area_m2"})
    buildings["centroid"] = buildings.geometry.representative_point()

    code = config.BOUNDARY_CODE_FIELD
    clipped = gpd.sjoin(
        buildings.set_geometry("centroid"),
        boundaries[[code, "geometry"]],
        how="inner",
        predicate="within",
    )
    clipped = clipped.rename(columns={code: "boundary_code"})
    return clipped.set_geometry("geometry")[_OUTPUT_COLUMNS]


def main():
    boundaries = load_boundaries()
    buildings = clip_to_boundaries(boundaries)
    print(f"buildings within boundaries (confidence >= {config.BUILDING_CONFIDENCE_THRESHOLD} "
          f"or null): {len(buildings):,}")

    print("by source:")
    for source, count in buildings["bf_source"].value_counts().items():
        print(f"  {source:<12} {count:>8,}")

    counts = buildings.groupby("boundary_code").size().sort_index()
    for code, count in counts.items():
        print(f"{code:<14} {count:>8,}")

    missing = set(boundaries[config.BOUNDARY_CODE_FIELD]) - set(counts.index)
    if missing:
        print("no buildings assigned:", ", ".join(sorted(missing)))


if __name__ == "__main__":
    main()
