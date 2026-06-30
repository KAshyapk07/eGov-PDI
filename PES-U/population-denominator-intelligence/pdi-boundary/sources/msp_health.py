"""Readers for the MSP 2020 health GIS layers (district/province polygons, facility points)."""

import geopandas as gpd

import config


def load_districts():
    gdf = gpd.read_file(config.MSP_DISTRICTS_SHP).to_crs(config.STORAGE_CRS)
    gdf = gdf.rename(columns={
        "District": "msp_district",
        "Pcode": "msp_pcode",
        "RegName": "msp_province",
    })
    return gdf[["msp_district", "msp_pcode", "msp_province", "geometry"]].reset_index(drop=True)


def load_provinces():
    gdf = gpd.read_file(config.MSP_PROVINCES_SHP).to_crs(config.STORAGE_CRS)
    gdf = gdf.rename(columns={"NamePS": "msp_province", "HRPcode": "msp_province_code"})
    return gdf[["msp_province", "msp_province_code", "geometry"]].reset_index(drop=True)


def load_facilities():
    gdf = gpd.read_file(config.MSP_FACILITIES_SHP).to_crs(config.STORAGE_CRS)
    gdf = gdf.rename(columns={
        "Nom": "facility_name",
        "TYPES": "facility_type",
        "District": "msp_district",
        "Pcode": "msp_pcode",
    })
    return gdf[["facility_name", "facility_type", "msp_district", "msp_pcode",
                "geometry"]].reset_index(drop=True)


def main():
    districts = load_districts()
    provinces = load_provinces()
    facilities = load_facilities()
    print(f"MSP districts:   {len(districts):>5,}")
    print(f"MSP provinces:   {len(provinces):>5,}")
    print(f"MSP facilities:  {len(facilities):>5,}")
    centres = facilities[facilities["facility_type"].str.contains("Centre", case=False, na=False)]
    print(f"  of which Centres de Sante: {len(centres):,}")


if __name__ == "__main__":
    main()
