"""Flattens the ITN microplan workbook into a (boundary_code, name, level, parent_code) table."""

import pandas as pd

import config

PATH_COLUMNS = ["country", "province", "district", "health_centre", "spp_sfd", "village"]
_RAW_COLUMNS = PATH_COLUMNS + ["boundary_code", "name"]


def _is_filled(value):
    return value is not None and not pd.isna(value) and str(value).strip() != ""


def _row_level(row):
    level = 0
    for index, column in enumerate(PATH_COLUMNS):
        if _is_filled(row[column]):
            level = index
    return level


def normalize(frame):
    """Resolve each row's level and parent_code from the column nesting, preserving file order."""
    frame = frame.iloc[:, : len(_RAW_COLUMNS)].copy()
    frame.columns = _RAW_COLUMNS
    frame = frame[frame["boundary_code"].map(_is_filled)].reset_index(drop=True)

    code_by_level = [None] * len(PATH_COLUMNS)
    records = []
    for row in frame.to_dict("records"):
        level = _row_level(row)
        parent_code = next(
            (code_by_level[depth] for depth in range(level - 1, -1, -1) if code_by_level[depth]),
            None,
        )

        code = str(row["boundary_code"]).strip()
        code_by_level[level] = code
        for deeper in range(level + 1, len(code_by_level)):
            code_by_level[deeper] = None

        label = row["name"] if _is_filled(row["name"]) else row[PATH_COLUMNS[level]]
        record = {
            "boundary_code": code,
            "name": str(label).strip(),
            "level": PATH_COLUMNS[level],
            "level_num": level,
            "parent_code": parent_code,
        }
        record.update({column: (str(row[column]).strip() if _is_filled(row[column]) else None)
                        for column in PATH_COLUMNS})
        records.append(record)

    return pd.DataFrame(records, columns=["boundary_code", "name", "level", "level_num",
                                          "parent_code", *PATH_COLUMNS])


def load_itn_boundaries(path=None, sheet=None):
    frame = pd.read_excel(path or config.ITN_BOUNDARY_XLSX,
                          sheet_name=sheet or config.ITN_BOUNDARY_SHEET)
    return normalize(frame)


def district_roster(path=None, sheet=None):
    """The microplan's districts only: (microplan_code, microplan_district, microplan_province)."""
    boundaries = load_itn_boundaries(path, sheet)
    districts = boundaries[boundaries["level"] == "district"].copy()
    districts = districts[["boundary_code", "name", "province"]].rename(
        columns={
            "boundary_code": "microplan_code",
            "name": "microplan_district",
            "province": "microplan_province",
        }
    )
    return districts.reset_index(drop=True)


def main():
    boundaries = load_itn_boundaries()
    print(f"boundary units: {len(boundaries):,}")
    for level, count in boundaries["level"].value_counts().reindex(PATH_COLUMNS).dropna().items():
        print(f"  {level:<14} {int(count):>7,}")

    codes = set(boundaries["boundary_code"])
    orphans = boundaries[boundaries["parent_code"].notna()
                         & ~boundaries["parent_code"].isin(codes)]
    if not orphans.empty:
        print(f"parent_code without a matching unit: {len(orphans):,}")

    duplicates = boundaries["boundary_code"].duplicated().sum()
    if duplicates:
        print(f"duplicate boundary codes: {duplicates:,}")


if __name__ == "__main__":
    main()
