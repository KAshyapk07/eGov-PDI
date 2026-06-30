"""Reconcile the microplan district roster against MSP district polygons.
"""

import geopandas as gpd
import pandas as pd

import config
from reconcile import name_match
from sources import itn_microplan, msp_health

TABLE_COLUMNS = [
    "Boundary_code", "microplan_code", "microplan_district", "microplan_province",
    "msp_district", "msp_pcode", "msp_province", "match_status", "match_score",
]


def _boundary_code(row):
    if pd.notna(row.get("microplan_code")):
        return row["microplan_code"]
    if pd.notna(row.get("msp_pcode")):
        return f"MSP_{row['msp_pcode']}"
    return None


def _dedupe(codes):
    """Guarantee a unique join key; suffix any repeated code (the MSP layer has one shared Pcode)."""
    seen = {}
    out = []
    for code in codes:
        if code is None:
            out.append(code)
            continue
        seen[code] = seen.get(code, 0) + 1
        out.append(code if seen[code] == 1 else f"{code}_{seen[code]}")
    return out


def reconcile():
    """Return (table, common_gdf): the side-by-side district table and the geometry-bearing subset."""
    microplan = itn_microplan.district_roster()
    msp = msp_health.load_districts()
    msp_attrs = msp.drop(columns="geometry")

    pairs, microplan_only, msp_only = name_match.match_names(
        microplan["microplan_district"], msp["msp_district"], config.DISTRICT_FUZZY_CUTOFF)
    pairs = pd.DataFrame(pairs, columns=["left", "right", "score", "kind"])

    matched = (
        microplan.merge(pairs, left_on="microplan_district", right_on="left", how="inner")
        .merge(msp_attrs, left_on="right", right_on="msp_district", how="left")
    )
    matched["match_status"] = "matched_" + matched["kind"]
    matched["match_score"] = matched["score"]

    left_rows = microplan[microplan["microplan_district"].isin(microplan_only)].copy()
    left_rows["match_status"] = "unmatched_microplan"

    right_rows = msp_attrs[msp_attrs["msp_district"].isin(msp_only)].copy()
    right_rows["match_status"] = "unmatched_msp"

    table = pd.concat([matched, left_rows, right_rows], ignore_index=True)
    table["Boundary_code"] = table.apply(_boundary_code, axis=1)
    table["Boundary_code"] = _dedupe(table["Boundary_code"])
    table = table.reindex(columns=TABLE_COLUMNS)

    geometry_by_name = msp.set_index("msp_district").geometry
    has_geometry = table[table["msp_district"].notna()].copy()
    has_geometry["geometry"] = has_geometry["msp_district"].map(geometry_by_name)
    geo = gpd.GeoDataFrame(has_geometry, geometry="geometry", crs=config.STORAGE_CRS)

    return table, geo


def main():
    table, geo = reconcile()
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    common = geo[geo["match_status"].isin(["matched_exact", "matched_fuzzy"])]
    msp_only = geo[geo["match_status"] == "unmatched_msp"]
    not_in_msp = table[table["match_status"] == "unmatched_microplan"]

    common.to_file(config.COMMON_DISTRICTS_GEOJSON, driver="GeoJSON")
    msp_only.to_file(config.MSP_ONLY_GEOJSON, driver="GeoJSON")
    not_in_msp.to_csv(config.DISTRICT_MISMATCH_CSV, index=False, encoding="utf-8-sig")
    table.to_csv(config.DISTRICT_RECONCILIATION_CSV, index=False, encoding="utf-8-sig")

    counts = table["match_status"].value_counts()
    print("District reconciliation (microplan vs MSP)")
    for status in ["matched_exact", "matched_fuzzy", "unmatched_microplan", "unmatched_msp"]:
        print(f"  {status:<22} {int(counts.get(status, 0)):>4}")
    print(f"\n  common in both (GeoJSON):       {len(common):>4}")
    print(f"  MSP-only, not in microplan:     {len(msp_only):>4}")
    print(f"  microplan-only, not in MSP:     {len(not_in_msp):>4}")
    print(f"\nWrote:\n  {config.COMMON_DISTRICTS_GEOJSON}\n  {config.MSP_ONLY_GEOJSON}"
          f"\n  {config.DISTRICT_MISMATCH_CSV}\n  {config.DISTRICT_RECONCILIATION_CSV}")


if __name__ == "__main__":
    main()
