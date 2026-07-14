"""MSP health-facility reader: the 'formations sanitaires' point layer for facility-distance risk."""

import geopandas as gpd

import config


def load_facilities():
    """MSP facility points in the storage CRS, dropping any missing or non-point geometries."""
    facilities = gpd.read_file(config.MSP_FACILITY_POINTS)
    facilities = facilities[facilities.geometry.notna() & ~facilities.geometry.is_empty]
    facilities = facilities[facilities.geometry.geom_type == "Point"]
    return facilities.to_crs(config.STORAGE_CRS).reset_index(drop=True)


def main():
    facilities = load_facilities()
    print(f"facility points: {len(facilities):,}")
    print(facilities["TYPES"].value_counts().head(10).to_string())


if __name__ == "__main__":
    main()
