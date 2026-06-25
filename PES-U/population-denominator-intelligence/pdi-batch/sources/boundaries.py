"""Settlement boundary reader: loads the campaign boundary polygons from GeoJSON."""

import geopandas as gpd

import config


def load_boundaries():
    boundaries = gpd.read_file(config.BOUNDARY_GEOJSON)
    boundaries = boundaries[boundaries.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
    boundaries = boundaries.to_crs(config.STORAGE_CRS)
    return boundaries.reset_index(drop=True)
