import argparse
from datetime import datetime, timezone

import geopandas as gpd
import pandas as pd

import config
from sources import register

CODE = config.BOUNDARY_CODE_FIELD

IDENTITY_COLUMNS = [CODE, "campaign_id", "msp_district", "msp_province", "microplan_district"]
REPORT_COLUMNS = [
    "estimated_population", "registered_population", "population_gap",
    "estimated_households", "registered_households", "household_gap",
    "coverage_ratio", "gap_classification",
    "registered_under5", "estimated_under5", "coverage_ratio_under5",
    "computed_at", "tenant_id",
]


def classify(coverage_ratio, registered_population, building_count):
    """GREEN/YELLOW/RED by coverage, BLACK when a built-up district has no registrations."""
    if registered_population == 0:
        return "BLACK" if building_count > 0 else "RED"
    if coverage_ratio is None or pd.isna(coverage_ratio):
        return "RED"
    if coverage_ratio >= config.GAP_GREEN_THRESHOLD:
        return "GREEN"
    if coverage_ratio >= config.GAP_YELLOW_THRESHOLD:
        return "YELLOW"
    return "RED"


def _coverage(registered, estimated):
    return (registered / estimated).where(estimated > 0).round(4)


def build(scope="national"):
    """Return (table, gdf): the per-district gap report as a DataFrame and a GeoDataFrame."""
    if not config.DISTRICT_POPULATION_GEOJSON.exists():
        raise FileNotFoundError(
            f"{config.DISTRICT_POPULATION_GEOJSON} not found - run features.estimation first")
    est = gpd.read_file(config.DISTRICT_POPULATION_GEOJSON)

    counts = register.registered_counts(est[[CODE, "geometry"]])
    df = est.merge(counts, on=CODE, how="left")
    for column in ["registered_population", "registered_under5", "registered_households"]:
        df[column] = df[column].fillna(0).astype(int)

    df["campaign_id"] = config.CAMPAIGN_ID
    df["tenant_id"] = config.TENANT_ID
    df["estimated_population"] = df["population_estimate"].astype(int)
    df["estimated_under5"] = df["under5"].round().astype(int)

    df["population_gap"] = df["estimated_population"] - df["registered_population"]
    df["household_gap"] = df["estimated_households"] - df["registered_households"]
    df["coverage_ratio"] = _coverage(df["registered_population"], df["estimated_population"])
    df["coverage_ratio_under5"] = _coverage(df["registered_under5"], df["estimated_under5"])
    df["gap_classification"] = df.apply(
        lambda row: classify(row["coverage_ratio"], row["registered_population"],
                             row["building_count"]), axis=1)
    df["computed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if scope == "ndjamena":
        df = df[df["registered_population"] > 0]

    columns = [c for c in IDENTITY_COLUMNS if c in df.columns] + REPORT_COLUMNS
    table = df[columns].reset_index(drop=True)
    gdf = gpd.GeoDataFrame(
        table.merge(est[[CODE, "geometry"]], on=CODE), geometry="geometry",
        crs=config.STORAGE_CRS)
    return table, gdf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=["national", "ndjamena"], default="national",
                        help="national: every district (uncovered ones fall to BLACK); "
                             "ndjamena: only districts the register actually covers")
    args = parser.parse_args()

    table, gdf = build(scope=args.scope)
    config.GAP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    table.to_csv(config.GAP_REPORT_CSV, index=False, encoding="utf-8-sig")
    gdf.to_file(config.GAP_REPORT_GEOJSON, driver="GeoJSON")

    counts = table["gap_classification"].value_counts()
    print(f"scope:                    {args.scope}")
    print(f"districts in report:      {len(table):>12,}")
    print(f"registered (assigned):    {table['registered_population'].sum():>12,}")
    print(f"estimated (in report):    {table['estimated_population'].sum():>12,}")
    print("classification:")
    for label in ["GREEN", "YELLOW", "RED", "BLACK"]:
        print(f"  {label:<8} {int(counts.get(label, 0)):>6}")
    covered = table[table["registered_population"] > 0]
    if not covered.empty:
        print("\ncovered districts (registered vs estimated, coverage):")
        for _, row in covered.sort_values("registered_population", ascending=False).iterrows():
            name = row.get("msp_district") or row[CODE]
            print(f"  {name:<20} {row['registered_population']:>7,} / "
                  f"{row['estimated_population']:>9,}  "
                  f"{(row['coverage_ratio'] or 0):>6.1%}  {row['gap_classification']}")
    print(f"\nWrote:\n  {config.GAP_REPORT_CSV}\n  {config.GAP_REPORT_GEOJSON}")


if __name__ == "__main__":
    main()
