import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd

import config

CODE = config.BOUNDARY_CODE_FIELD


def _targets_frame(table, groups):
    """Per-boundary target columns (``household_target`` + one per age group)."""
    targets = pd.DataFrame({CODE: table[CODE].to_numpy()})
    targets["household_target"] = table["building_count"].astype(int).to_numpy()
    for group in groups:
        targets[f"{group}_target"] = table[group].round().astype(int).to_numpy()
    return targets.reset_index(drop=True)


def compute(iso3=None, sheet_path=None, avg_household_size=None,
            groups=None, with_buildings=True, year=None):
    
    from features import estimation

    groups = groups or config.DEFAULT_TARGET_GROUPS
    table, units = estimation.estimate(
        iso3=iso3, sheet_path=None, with_buildings=with_buildings,
        avg_household_size=avg_household_size, year=year, label="country population")
    return _targets_frame(table, groups), units.reset_index(drop=True)


def compute_catchments(iso3=None, sheet_path=None, avg_household_size=None,
                       groups=None, with_buildings=True, year=None):
    if not sheet_path:
        return None, None
    from features import estimation
    from sources.catchments import build_analysis_units

    groups = groups or config.DEFAULT_TARGET_GROUPS
    cells = build_analysis_units(iso3, sheet_path)
    cells = cells[cells["is_catchment"]].reset_index(drop=True)
    if cells.empty:
        return None, None
    table, units = estimation.estimate(
        iso3=iso3, with_buildings=with_buildings,
        avg_household_size=avg_household_size, units=cells, year=year,
        label="catchment population")
    return _targets_frame(table, groups), units.reset_index(drop=True)


def catchment_buildings(catchment_units, iso3=None):
    if catchment_units is None or catchment_units.empty:
        return None
    from sources import buildings as buildings_source

    clipped = buildings_source.clip_to_boundaries(catchment_units[[CODE, "geometry"]], iso3)
    points = clipped.set_geometry("centroid")[["boundary_code", "centroid"]].rename(
        columns={"boundary_code": "boundaryCode", "centroid": "geometry"})
    return gpd.GeoDataFrame(
        points, geometry="geometry", crs=config.STORAGE_CRS).reset_index(drop=True)


def compute_targets(iso3=None, sheet_path=None, avg_household_size=None,
                    groups=None, with_buildings=True):
    """Per-boundary targets DataFrame (see :func:`compute`)."""
    targets, _ = compute(iso3, sheet_path, avg_household_size, groups, with_buildings)
    return targets


def _coverage(registered, estimated):
    """Registered / estimated, left undefined (NaN) where nothing is estimated."""
    return (registered / estimated).where(estimated > 0).round(4)


REGISTERED_COLUMNS = [
    "registered_population", "registered_under5", "registered_households",
    "coverage_ratio", "coverage_ratio_under5", "gap_classification",
]
REGISTERED_COUNT_COLUMNS = [
    "registered_population", "registered_under5", "registered_households",
]


def registered_frame(units, iso3=None):
    from features.gap import classify
    from sources import register

    if not register.has_register(iso3):
        return None

    counts = register.registered_counts(units[[CODE, "geometry"]])
    frame = units[[CODE, "population_estimate", "under5", "building_count"]].merge(
        counts, on=CODE, how="left")
    for column in REGISTERED_COUNT_COLUMNS:
        frame[column] = frame[column].fillna(0).astype(int)

    estimated_under5 = frame["under5"].round().astype(int)
    frame["coverage_ratio"] = _coverage(frame["registered_population"], frame["population_estimate"])
    frame["coverage_ratio_under5"] = _coverage(frame["registered_under5"], estimated_under5)
    frame["gap_classification"] = frame.apply(
        lambda row: classify(row["coverage_ratio"], row["registered_population"],
                             row["building_count"]), axis=1)
    return frame[[CODE, *REGISTERED_COLUMNS]].reset_index(drop=True)


def fill_sheet(sheet_path, targets, output_path, column_map=None, registered=None):
    sheet = pd.read_excel(sheet_path, sheet_name=config.SHEET_SHEET_NAME)
    lookup = targets.set_index(CODE)
    key = sheet[config.SHEET_CODE_COLUMN].astype(str)

    if column_map:
        pairs = [(sheet_col, target_key) for target_key, sheet_col in column_map.items()]
    else:
        pairs = [(col, col) for col in targets.columns if col != CODE]

    for sheet_col, target_key in pairs:
        sheet[sheet_col] = key.map(lookup[target_key])

    if registered is not None:
        reg_lookup = registered.set_index(CODE)
        for column in REGISTERED_COLUMNS:
            sheet[column] = key.map(reg_lookup[column])

    output_path = Path(output_path)
    sheet.to_excel(output_path, index=False)
    return output_path


RISK_PROPERTY_COLUMNS = ["risk_score", "risk_priority", "risk_factors"]


def write_geojson(units, targets, output_path, registered=None, risk=None):
    merged = units.merge(targets, on=CODE, how="left")
    if registered is not None:
        merged = merged.merge(registered, on=CODE, how="left")
    if risk is not None:
        cols = [CODE, *[c for c in RISK_PROPERTY_COLUMNS if c in risk.columns]]
        merged = merged.merge(risk[cols], on=CODE, how="left")
    frame = merged.rename(
        columns={CODE: "boundaryCode", config.BOUNDARY_NAME_FIELD: "name"})
    output_path = Path(output_path)
    frame.to_file(output_path, driver="GeoJSON")
    return output_path


def write_invisible_geojson(invisible, output_path, register_households=None):
    import json

    output_path = Path(output_path)
    if invisible is None or invisible.empty:
        collection = {"type": "FeatureCollection", "features": []}
    else:
        collection = json.loads(invisible.to_json())
    if register_households is not None and not register_households.empty:
        collection["registerHouseholds"] = {
            "type": "MultiPoint",
            "coordinates": [[float(point.x), float(point.y)]
                            for point in register_households.geometry],
        }
    output_path.write_text(json.dumps(collection), encoding="utf-8")
    return output_path


def write_points_geojson(points, output_path):
    output_path = Path(output_path)
    if points is None or points.empty:
        output_path.write_text(
            '{"type": "FeatureCollection", "features": []}', encoding="utf-8")
    else:
        points.to_file(output_path, driver="GeoJSON")
    return output_path


def build_stats(units, registered, invisible, risk=None):
    df = units.drop(columns="geometry") if "geometry" in units.columns else units.copy()
    est_pop = int(df["population_estimate"].sum())
    est_hh = int(df["estimated_households"].sum())

    risk_lookup = {}
    risk_distribution = {}
    if risk is not None and not risk.empty:
        risk_lookup = {
            row[CODE]: (int(row["risk_score"]), row["risk_priority"])
            for _, row in risk.iterrows()
        }
        risk_distribution = {
            str(priority): int(count)
            for priority, count in risk["risk_priority"].value_counts().items()
        }

    summary = {
        "totalEstimatedPopulation": est_pop,
        "totalEstimatedHouseholds": est_hh,
        "totalRegisteredPopulation": 0,
        "totalRegisteredHouseholds": 0,
        "totalPopulationGap": est_pop,
        "householdGap": est_hh,
        "overallCoverageRatio": None,
        "invisibleSettlementCount": 0,
        "invisibleEstimatedPopulation": 0,
    }
    gap_distribution = {}
    top_gap = []

    if registered is not None:
        merged = df.merge(registered, on=CODE, how="left")
        reg_pop = int(merged["registered_population"].fillna(0).sum())
        reg_hh = int(merged["registered_households"].fillna(0).sum())
        summary["totalRegisteredPopulation"] = reg_pop
        summary["totalRegisteredHouseholds"] = reg_hh
        summary["totalPopulationGap"] = est_pop - reg_pop
        summary["householdGap"] = est_hh - reg_hh
        summary["overallCoverageRatio"] = round(reg_pop / est_pop, 4) if est_pop else None

        for cls, group in merged.groupby("gap_classification"):
            gap_distribution[cls] = {
                "count": int(len(group)),
                "population": int(group["population_estimate"].sum()),
            }

        merged["gap"] = merged["population_estimate"] - merged["registered_population"].fillna(0)
        for _, row in merged.sort_values("gap", ascending=False).head(10).iterrows():
            coverage = row["coverage_ratio"]
            risk_score, risk_priority = risk_lookup.get(row[CODE], (None, None))
            top_gap.append({
                "name": row.get(config.BOUNDARY_NAME_FIELD) or row[CODE],
                "boundaryCode": row[CODE],
                "gap": int(row["gap"]),
                "coverageRatio": None if pd.isna(coverage) else float(coverage),
                "riskScore": risk_score,
                "riskPriority": risk_priority,
            })

    if invisible is not None and not invisible.empty:
        summary["invisibleSettlementCount"] = int(len(invisible))
        summary["invisibleEstimatedPopulation"] = int(invisible["estimated_population"].sum())

    return {
        "summary": summary,
        "gapDistribution": gap_distribution,
        "topGapSettlements": top_gap,
        "riskDistribution": risk_distribution,
    }


def detect_invisible(iso3=None):
    """Feature 4 clusters, or ``None`` where the country has no register to detect against."""
    from sources import register

    if not register.has_register(iso3):
        return None
    from features import invisible as invisible_feature

    _, gdf = invisible_feature.detect(scope="ndjamena", iso3=iso3)
    return gdf


def detect_risk(units, registered, iso3=None, sheet_path=None):
    if registered is None:
        return None
    from features import risk as risk_feature

    name = config.BOUNDARY_NAME_FIELD
    base = units[[CODE, name, "population_estimate", "geometry"]].copy()
    gap_gdf = base.merge(
        registered[[CODE, "registered_population", "coverage_ratio", "gap_classification"]],
        on=CODE, how="left")
    gap_gdf["registered_population"] = gap_gdf["registered_population"].fillna(0).astype(int)
    gap_gdf = gap_gdf.rename(columns={"population_estimate": "estimated_population"})
    gap_gdf["estimated_population"] = gap_gdf["estimated_population"].astype(int)
    gap_gdf["population_gap"] = gap_gdf["estimated_population"] - gap_gdf["registered_population"]
    gap_gdf = gpd.GeoDataFrame(gap_gdf, geometry="geometry", crs=config.STORAGE_CRS)

    centers = None
    if sheet_path:
        from sources.catchments import load_catchment_points
        centers = load_catchment_points(sheet_path)

    _, risk_gdf = risk_feature.score(gap_gdf, units[[CODE, "building_count", "area_km2"]], centers)
    return risk_gdf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso3", help="country ISO3 (default from PDI_ISO3 / config)")
    parser.add_argument("--sheet", help="microplan boundary sheet; adds the catchment overlay")
    parser.add_argument("--out", help="output sheet path (default: <sheet>_targets.xlsx)")
    parser.add_argument("--json", help="write computed targets as a JSON envelope (for the API)")
    parser.add_argument("--geojson", help="write the whole-country district polygons + targets as GeoJSON")
    parser.add_argument("--catchments-geojson", help="write the Voronoi catchment cells (with a sheet) as GeoJSON")
    parser.add_argument("--buildings-geojson", help="write catchment building points tagged by facility as GeoJSON")
    parser.add_argument("--groups", help="comma-separated target-group keys (default from config)")
    parser.add_argument("--household-size", type=float, help="average household size")
    parser.add_argument("--year", type=int,
                        help="WorldPop population year (default from PDI_YEAR / config)")
    parser.add_argument("--no-buildings", action="store_true", help="skip Open Buildings")
    parser.add_argument("--invisible-geojson", help="write invisible-settlement clusters as GeoJSON")
    parser.add_argument("--no-invisible", action="store_true", help="skip invisible-settlement detection")
    parser.add_argument("--no-risk", action="store_true", help="skip Feature 5 risk scoring")
    parser.add_argument("--stats-json", help="write the dashboard summary JSON")
    parser.add_argument("--persist", action="store_true",
                        help="upsert the results into the PostGIS tables the API reads from")
    parser.add_argument("--campaign-id", help="campaign identifier for the persisted gap report")
    parser.add_argument("--tenant-id", default=config.TENANT_ID, help="tenant identifier for persisted rows")
    parser.add_argument("--persist-buildings", action="store_true",
                        help="also persist individual building footprints (large; off by default)")
    args = parser.parse_args()

    resolved_groups = [g.strip() for g in args.groups.split(",")] if args.groups else None
    with_buildings = not args.no_buildings

    # Whole-country base layer (always the country's ADM2 districts).
    targets, units = compute(
        iso3=args.iso3, sheet_path=args.sheet, groups=resolved_groups,
        avg_household_size=args.household_size, with_buildings=with_buildings,
        year=args.year)
    registered = registered_frame(units, args.iso3)
    invisible = None if args.no_invisible else detect_invisible(args.iso3)
    invisible_count = 0 if invisible is None else int(len(invisible))
    risk = None if args.no_risk else detect_risk(units, registered, args.iso3, args.sheet)

    # Catchment overlay (only when a sheet supplies service points).
    catch_targets, catch_units = compute_catchments(
        iso3=args.iso3, sheet_path=args.sheet, groups=resolved_groups,
        avg_household_size=args.household_size, with_buildings=with_buildings,
        year=args.year)
    # Carry each health centre's exact coordinates on its catchment cell so the map
    # can mark the facility point (from the uploaded sheet) inside its Voronoi cell.
    if catch_units is not None and args.sheet:
        from sources.catchments import load_catchment_points

        centers = load_catchment_points(args.sheet)
        if not centers.empty:
            centers = centers.assign(center_lon=centers.geometry.x, center_lat=centers.geometry.y)
            catch_units = catch_units.merge(
                centers[[CODE, "center_lon", "center_lat"]], on=CODE, how="left")
    catch_registered = registered_frame(catch_units, args.iso3) if catch_units is not None else None
    catchment_count = 0 if catch_units is None else int(len(catch_units))

    if args.persist:
        campaign_id = args.campaign_id or config.CAMPAIGN_ID
        try:
            from persistence import store

            summary = store.persist(campaign_id, args.tenant_id, units, registered, risk, invisible)
            print(f"persisted {summary['boundaries']:,} boundaries "
                  f"(campaign {campaign_id}, tenant {args.tenant_id})")
            if args.persist_buildings:
                written = store.persist_buildings(args.tenant_id, units.attrs.get("building_footprints"))
                print(f"persisted {written:,} building footprints")
        except Exception as exc:  # noqa: BLE001 - persistence is best-effort for the live tool
            print(f"WARNING persistence skipped: {exc}")

    out = None
    if args.sheet and catch_targets is not None:
        out = args.out or str(Path(args.sheet).with_suffix("")) + "_targets.xlsx"
        fill_sheet(args.sheet, catch_targets, out, registered=catch_registered)

    geojson_path = None
    if args.geojson:
        geojson_path = str(write_geojson(units, targets, args.geojson, registered, risk).resolve())

    catchments_path = None
    if args.catchments_geojson and catch_units is not None:
        catchments_path = str(
            write_geojson(catch_units, catch_targets, args.catchments_geojson, catch_registered).resolve())

    buildings_path = None
    if args.buildings_geojson and catch_units is not None:
        blds = catchment_buildings(catch_units, args.iso3) if with_buildings else None
        buildings_path = str(write_points_geojson(blds, args.buildings_geojson).resolve())

    invisible_path = None
    if args.invisible_geojson:
        from sources import register

        register_homes = register.load_households() if register.has_register(args.iso3) else None
        invisible_path = str(write_invisible_geojson(
            invisible, args.invisible_geojson, register_homes).resolve())

    stats_path = None
    if args.stats_json:
        import json

        Path(args.stats_json).write_text(
            json.dumps(build_stats(units, registered, invisible, risk)), encoding="utf-8")
        stats_path = str(Path(args.stats_json).resolve())

    if args.json:
        import json

        records = targets.rename(columns={CODE: "boundaryCode"}).to_dict(orient="records")
        registered_records = [] if registered is None else (
            registered[[CODE, *REGISTERED_COUNT_COLUMNS]]
            .rename(columns={CODE: "boundaryCode"}).to_dict(orient="records"))
        envelope = {
            "iso3": (args.iso3 or config.COUNTRY_ISO3).upper(),
            "count": int(len(targets)),
            "groups": resolved_groups or config.DEFAULT_TARGET_GROUPS,
            "sheet": str(Path(out).resolve()) if out else None,
            "geojson": geojson_path,
            "targets": records,
            "registeredAvailable": registered is not None,
            "registered": registered_records,
            "invisibleAvailable": invisible is not None,
            "invisibleCount": invisible_count,
            "invisibleGeojson": invisible_path,
            "catchmentsAvailable": catch_units is not None,
            "catchmentCount": catchment_count,
            "catchmentsGeojson": catchments_path,
            "buildingsGeojson": buildings_path,
            "riskAvailable": risk is not None,
            "statsJson": stats_path,
        }
        Path(args.json).write_text(json.dumps(envelope), encoding="utf-8")

    print(f"targets computed for {len(targets):,} districts (whole country)")
    if catchment_count:
        print(f"catchment overlay: {catchment_count:,} Voronoi cells from the sheet")
    if registered is not None:
        covered = int((registered["registered_population"] > 0).sum())
        print(f"register: {covered:,} of {len(registered):,} districts carry registrations")
    else:
        print("register: none for this country (registration/risk overlays omitted)")
    if risk is not None:
        print(f"risk: scored {len(risk):,} districts")
    if invisible is not None:
        print(f"invisible settlements: {invisible_count:,} clusters detected")
    if out:
        print(f"wrote downloadable sheet: {out}")


if __name__ == "__main__":
    main()
