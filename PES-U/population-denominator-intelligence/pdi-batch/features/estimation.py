# Feature 1 - population estimation per district over the common boundary.

import argparse

import geopandas as gpd
import pandas as pd

import config
from sources import buildings, worldpop
from sources.catchments import build_analysis_units

CODE = config.BOUNDARY_CODE_FIELD
GROUP_COLUMNS = list(config.TARGET_GROUPS)
IDENTITY_COLUMNS = [
    CODE, config.BOUNDARY_NAME_FIELD, "is_catchment",
    "microplan_district", "microplan_province",
    "msp_district", "msp_province", "match_status",
]


def building_counts(boundaries, iso3=None):
    """Buildings assigned to each unit, as a count keyed by boundary code."""
    clipped = buildings.clip_to_boundaries(boundaries, iso3)
    return clipped.groupby("boundary_code").size()


def _ensemble(total, count, household_size):
    """Blend the WorldPop and building-count estimates per the Feature 1 algorithm."""
    building_estimate = count * household_size
    if total <= 0:
        return building_estimate, 0.40, "buildings_only", None

    divergence = abs(total - building_estimate) / total
    if count and divergence < 0.30:
        population = 0.6 * total + 0.4 * building_estimate
        confidence = 0.85 + 0.15 * (1 - divergence)
        method = "ensemble"
    else:
        population = total
        confidence = 0.50 + 0.2 * min(count / 10, 1) if count else 0.50
        method = "worldpop_primary"
    return population, round(confidence, 3), method, round(divergence, 3)


def estimate(iso3=None, sheet_path=None, with_buildings=True, avg_household_size=None):
    """Return (table, gdf): per-unit estimates as a DataFrame and a GeoDataFrame.

    Units are ADM2 districts, or Voronoi catchment cells where ``sheet_path`` is
    given. ``avg_household_size`` overrides the per-country config default.
    """
    household_size = avg_household_size or config.AVG_HOUSEHOLD_SIZE
    districts = build_analysis_units(iso3, sheet_path)

    groups = pd.DataFrame(worldpop.compute_zonal(districts, iso3)).set_index("boundary_code")
    table = districts.drop(columns="geometry").join(groups, on=CODE)

    counts = building_counts(districts, iso3) if with_buildings else pd.Series(dtype=int)
    table["building_count"] = table[CODE].map(counts).fillna(0).astype(int)

    ensembled = table.apply(
        lambda row: _ensemble(row["total"], row["building_count"], household_size),
        axis=1, result_type="expand")
    table[["population_estimate", "confidence", "method", "divergence"]] = ensembled
    table["population_estimate"] = table["population_estimate"].round().astype(int)
    table["estimated_households"] = table["building_count"]

    # District area and resulting population density.
    area_km2 = districts.to_crs(config.AREA_CRS).area / 1_000_000
    table["area_km2"] = table[CODE].map(dict(zip(districts[CODE], area_km2))).round(1)
    table["density_ppl_km2"] = (table["population_estimate"] / table["area_km2"]).round(1)

    ordered = [c for c in IDENTITY_COLUMNS if c in table.columns] + [
        "population_estimate", "confidence", "method", "divergence",
        "building_count", "estimated_households", "area_km2", "density_ppl_km2",
        *GROUP_COLUMNS,
    ]
    table = table[ordered]

    gdf = gpd.GeoDataFrame(
        table.merge(districts[[CODE, "geometry"]], on=CODE),
        geometry="geometry", crs=config.STORAGE_CRS,
    )
    return table, gdf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-buildings", action="store_true",
                        help="skip the VIDA building cross-check (WorldPop only, much faster)")
    parser.add_argument("--iso3", help="country ISO3 (default from PDI_ISO3 / config)")
    parser.add_argument("--sheet", help="microplan boundary sheet; enables Voronoi catchment units")
    parser.add_argument("--household-size", type=float,
                        help="average household size (default from config per country)")
    args = parser.parse_args()

    table, gdf = estimate(iso3=args.iso3, sheet_path=args.sheet,
                          with_buildings=not args.no_buildings,
                          avg_household_size=args.household_size)
    config.ESTIMATION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    table.to_csv(config.DISTRICT_POPULATION_CSV, index=False, encoding="utf-8-sig")
    gdf.to_file(config.DISTRICT_POPULATION_GEOJSON, driver="GeoJSON")

    print(f"districts estimated:        {len(table):>12,}")
    print(f"WorldPop total (sum):       {table['total'].sum():>12,.0f}")
    print(f"under-5 (sum):              {table['under5'].sum():>12,.0f}")
    if not args.no_buildings:
        print(f"buildings assigned (sum):   {table['building_count'].sum():>12,}")
        print(f"method counts:              {table['method'].value_counts().to_dict()}")
    print(f"selectable denominators:    {len(GROUP_COLUMNS)}")
    print(f"\nWrote:\n  {config.DISTRICT_POPULATION_CSV}\n  {config.DISTRICT_POPULATION_GEOJSON}")


if __name__ == "__main__":
    main()
