import re

import geopandas as gpd
import pandas as pd

import config

_HOUSEHOLD_ROW = re.compile(
    r"\(\s*'[^']*',\s*'[^']*',\s*(?:'[^']*'|NULL),\s*(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)"
)


def has_register(iso3=None):
    """True when the entered country has register data available (Chad only today)."""
    iso3 = (iso3 or config.COUNTRY_ISO3).upper()
    return iso3 == config.REGISTER_ISO3 and config.REGISTER_INDIVIDUALS_CSV.exists()


def _points(frame, longitude, latitude):
    return gpd.GeoDataFrame(
        frame, geometry=gpd.points_from_xy(longitude, latitude), crs=config.STORAGE_CRS)


def load_individuals():
    """Registered individuals as points, with an ``under5`` flag (the polio target cohort)."""
    df = pd.read_csv(
        config.REGISTER_INDIVIDUALS_CSV,
        usecols=["individual_client_ref", "gender", "date_of_birth", "latitude", "longitude"],
    )
    age_days = pd.Timestamp(config.REGISTER_AGE_REFERENCE) - pd.to_datetime(
        df["date_of_birth"], errors="coerce")
    df["under5"] = (age_days.dt.days / 365.25) < 5
    return _points(df, df["longitude"], df["latitude"])


def load_households():
    """Registered households as points, parsed from the household_address INSERT statements."""
    text = config.REGISTER_HOUSEHOLD_SQL.read_text(encoding="utf-8")
    coords = _HOUSEHOLD_ROW.findall(text)
    frame = pd.DataFrame(coords, columns=["latitude", "longitude"]).astype(float)
    return _points(frame, frame["longitude"], frame["latitude"])


def _assign(points, boundaries):
    """Tag each register point with the district polygon that contains it (ST_Within)."""
    code = config.BOUNDARY_CODE_FIELD
    joined = gpd.sjoin(
        points, boundaries.to_crs(config.STORAGE_CRS)[[code, "geometry"]],
        how="inner", predicate="within")
    return joined.rename(columns={code: "boundary_code"})


def registered_counts(boundaries):
    """Registered population, under-5, and households per district (indexed by boundary_code)."""
    people = _assign(load_individuals(), boundaries)
    homes = _assign(load_households(), boundaries)
    counts = pd.DataFrame({
        "registered_population": people.groupby("boundary_code").size(),
        "registered_under5": people[people["under5"]].groupby("boundary_code").size(),
        "registered_households": homes.groupby("boundary_code").size(),
    }).fillna(0).astype(int)
    return counts.rename_axis(config.BOUNDARY_CODE_FIELD).reset_index()


def main():
    from sources.boundaries import load_boundaries

    boundaries = load_boundaries()
    counts = registered_counts(boundaries)
    print(f"districts with registrations: {len(counts):>8,}")
    print(f"registered individuals (assigned): {counts['registered_population'].sum():>8,}")
    print(f"registered under-5 (assigned):     {counts['registered_under5'].sum():>8,}")
    print(f"registered households (assigned):  {counts['registered_households'].sum():>8,}")
    print("\ntop districts by registered population:")
    top = counts.sort_values("registered_population", ascending=False).head(10)
    for _, row in top.iterrows():
        print(f"  {row[config.BOUNDARY_CODE_FIELD]:<20} {row['registered_population']:>8,}")


if __name__ == "__main__":
    main()
