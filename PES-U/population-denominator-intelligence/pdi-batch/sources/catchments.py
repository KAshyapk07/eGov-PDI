import geopandas as gpd
import pandas as pd
from shapely import voronoi_polygons
from shapely.geometry import MultiPoint

import config
from geo import resolve_metric_crs
from sources.boundaries import load_boundaries

CODE = config.BOUNDARY_CODE_FIELD
NAME = config.BOUNDARY_NAME_FIELD


def load_catchment_points(sheet_path):
    """Service points from the sheet: rows with coordinates, keyed by Service Boundary Code."""
    frame = pd.read_excel(sheet_path, sheet_name=config.SHEET_SHEET_NAME)
    lat, lon, code = config.SHEET_LAT_COLUMN, config.SHEET_LON_COLUMN, config.SHEET_CODE_COLUMN
    frame = frame.dropna(subset=[lat, lon, code])
    points = gpd.GeoDataFrame(
        {CODE: frame[code].astype(str)},
        geometry=gpd.points_from_xy(frame[lon], frame[lat]),
        crs=config.STORAGE_CRS,
    )
    return points.reset_index(drop=True)


def _assign_to_districts(points, districts):
    """Tag each point with the district that contains it, snapping strays to the nearest."""
    inside = gpd.sjoin(points, districts[[CODE, "geometry"]].rename(columns={CODE: "district_code"}),
                       how="left", predicate="within").drop(columns="index_right")
    stray = inside["district_code"].isna()
    if stray.any():
        metric = resolve_metric_crs(districts)
        near = gpd.sjoin_nearest(
            points[stray].to_crs(metric),
            districts[[CODE, "geometry"]].rename(columns={CODE: "district_code"}).to_crs(metric),
            distance_col="dist_m", max_distance=config.CATCHMENT_SNAP_TOLERANCE_M)
        near = near[~near.index.duplicated(keep="first")]
        inside.loc[near.index, "district_code"] = near["district_code"]
    dropped = int(inside["district_code"].isna().sum())
    return inside.dropna(subset=["district_code"]), dropped


def _voronoi_cells(points, district_geom):
    """Voronoi polygons of ``points`` clipped to ``district_geom``, aligned back to each point."""
    if len(points) == 1:
        return [district_geom]
    regions = voronoi_polygons(MultiPoint(list(points.geometry)), extend_to=district_geom)
    cells = gpd.GeoDataFrame(
        geometry=[cell.intersection(district_geom) for cell in regions.geoms],
        crs=config.STORAGE_CRS)
    cells = cells[~cells.geometry.is_empty].reset_index(drop=True)
    matched = gpd.sjoin(points, cells, how="left", predicate="within")
    matched = matched[~matched.index.duplicated(keep="first")]
    return [None if pd.isna(i) else cells.geometry.iloc[int(i)] for i in matched["index_right"]]


def build_analysis_units(iso3=None, sheet_path=None):
    """District polygons, or Voronoi catchment cells where the sheet provides points.

    Returns a GeoDataFrame of ``(boundary_code, name, is_catchment, geometry)``.
    Catchment cells carry the sheet's Service Boundary Code; whole districts carry
    the geoBoundaries shapeID.
    """
    districts = load_boundaries(iso3)
    if not sheet_path:
        units = districts[[CODE, "geometry"]].copy()
        units[NAME] = districts[NAME] if NAME in districts.columns else units[CODE]
        units["is_catchment"] = False
        return units[[CODE, NAME, "is_catchment", "geometry"]].reset_index(drop=True)

    points = load_catchment_points(sheet_path)
    points, _ = _assign_to_districts(points, districts)

    rows = []
    covered = set()
    districts_by_code = districts.set_index(CODE)
    for district_code, group in points.groupby("district_code"):
        covered.add(district_code)
        district_geom = districts_by_code.loc[district_code, "geometry"]
        cells = _voronoi_cells(group, district_geom)
        for (_, point), cell in zip(group.iterrows(), cells):
            rows.append({CODE: point[CODE], NAME: point[CODE],
                         "is_catchment": True, "geometry": cell or district_geom})

    for _, district in districts[~districts[CODE].isin(covered)].iterrows():
        rows.append({CODE: district[CODE], NAME: district.get(NAME, district[CODE]),
                     "is_catchment": False, "geometry": district.geometry})

    return gpd.GeoDataFrame(rows, geometry="geometry", crs=config.STORAGE_CRS).reset_index(drop=True)


def main():
    import sys

    sheet = sys.argv[1] if len(sys.argv) > 1 else None
    units = build_analysis_units(sheet_path=sheet)
    catchments = int(units["is_catchment"].sum())
    print(f"{config.COUNTRY_ISO3} analysis units: {len(units):,} "
          f"({catchments} catchment cells, {len(units) - catchments} whole districts)")


if __name__ == "__main__":
    main()
