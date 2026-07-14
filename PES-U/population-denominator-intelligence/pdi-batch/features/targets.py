import argparse
from pathlib import Path

import pandas as pd

import config

CODE = config.BOUNDARY_CODE_FIELD


def compute_targets(iso3=None, sheet_path=None, avg_household_size=None,
                    groups=None, with_buildings=True):
    """Per-boundary targets: ``household_target`` plus one column per age group.

    With a sheet the rows are its Voronoi catchment cells (keyed by Service
    Boundary Code); without one they are the country's ADM2 districts.
    """
    from features import estimation

    groups = groups or config.DEFAULT_TARGET_GROUPS
    table, _ = estimation.estimate(
        iso3=iso3, sheet_path=sheet_path,
        with_buildings=with_buildings, avg_household_size=avg_household_size)
    if sheet_path and "is_catchment" in table.columns:
        table = table[table["is_catchment"]]

    out = pd.DataFrame({CODE: table[CODE].to_numpy()})
    out["household_target"] = table["building_count"].astype(int).to_numpy()
    for group in groups:
        out[f"{group}_target"] = table[group].round().astype(int).to_numpy()
    return out.reset_index(drop=True)


def fill_sheet(sheet_path, targets, output_path, column_map=None):
    """Write ``targets`` into a downloadable copy of the sheet, matched by Service Boundary Code.

    ``column_map`` maps target keys -> existing sheet column names (fills only
    those); without it the target columns are appended. Returns ``output_path``.
    The uploaded original file is never touched.
    """
    sheet = pd.read_excel(sheet_path, sheet_name=config.SHEET_SHEET_NAME)
    lookup = targets.set_index(CODE)
    key = sheet[config.SHEET_CODE_COLUMN].astype(str)

    if column_map:
        pairs = [(sheet_col, target_key) for target_key, sheet_col in column_map.items()]
    else:
        pairs = [(col, col) for col in targets.columns if col != CODE]

    for sheet_col, target_key in pairs:
        sheet[sheet_col] = key.map(lookup[target_key])

    output_path = Path(output_path)
    sheet.to_excel(output_path, index=False)
    return output_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso3", help="country ISO3 (default from PDI_ISO3 / config)")
    parser.add_argument("--sheet", required=True, help="microplan boundary sheet")
    parser.add_argument("--out", help="output sheet path (default: <sheet>_targets.xlsx)")
    parser.add_argument("--household-size", type=float, help="average household size")
    parser.add_argument("--no-buildings", action="store_true", help="skip Open Buildings")
    args = parser.parse_args()

    targets = compute_targets(
        iso3=args.iso3, sheet_path=args.sheet,
        avg_household_size=args.household_size, with_buildings=not args.no_buildings)

    out = args.out or str(Path(args.sheet).with_suffix("")) + "_targets.xlsx"
    fill_sheet(args.sheet, targets, out)
    print(f"targets computed for {len(targets):,} boundaries")
    print(f"wrote downloadable sheet: {out}")


if __name__ == "__main__":
    main()
