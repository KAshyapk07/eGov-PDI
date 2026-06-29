"""
Central configuration for the PDI batch pre-computation layer.

"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_SOURCE = REPO_ROOT / "Data_Source"

# Location profile: edit these per country / campaign.

WORLDPOP_DIR = DATA_SOURCE / "Chad" / "Worldpop"
WORLDPOP_TOTAL_RASTER = WORLDPOP_DIR / "WorldPop_CHAD.tif"
WORLDPOP_AGESEX_DIR = WORLDPOP_DIR / "Worlpop_age_and_sex"
WORLDPOP_ISO = "tcd"

BOUNDARY_GEOJSON = (
    DATA_SOURCE / "OSM-boundry" / "Final_N'Djamena Arroddissment with boundry code.geojson"
)
# VIDA combined Open Buildings (Google v3 + Microsoft + OSM), country-wide GeoParquet.
BUILDINGS_PARQUET = DATA_SOURCE / "Chad" / "VIDA" / "TCD.parquet"
BOUNDARY_CODE_FIELD = "Boundary_code"

AVG_HOUSEHOLD_SIZE = 5.4

COUNTRY = "TCD"
CAMPAIGN_ID = "POLIO_CHAD_2024"
TENANT_ID = "default"
WORLDPOP_VERSION = "2026-CN-100m-R2025A"
OPEN_BUILDINGS_SOURCE = "vida-google-microsoft-osm"

# Optional sanity check: bbox + known control totals (set either to None to skip).
SANITY_BBOX = (14.98, 12.06, 15.13, 12.21)
WORLDPOP_REFERENCE = {"total": 1_632_766, "under5": 305_893}

# "total" uses the all-ages raster; t_NN = both sexes, f_NN/m_NN = by sex, T_F/T_M = all ages by sex.
TARGET_GROUPS = {
    "total": ["total"],
    "age_00": ["t_00"],
    "age_01_04": ["t_01"],
    "age_05_09": ["t_05"],
    "age_10_14": ["t_10"],
    "age_15_19": ["t_15"],
    "age_20_24": ["t_20"],
    "age_25_29": ["t_25"],
    "age_30_34": ["t_30"],
    "age_35_39": ["t_35"],
    "age_40_44": ["t_40"],
    "age_45_49": ["t_45"],
    "age_50_54": ["t_50"],
    "age_55_59": ["t_55"],
    "age_60_64": ["t_60"],
    "age_65_69": ["t_65"],
    "age_70_74": ["t_70"],
    "age_75_79": ["t_75"],
    "age_80_84": ["t_80"],
    "age_85_89": ["t_85"],
    "age_90_plus": ["t_90"],
    "under5": ["t_00", "t_01"],
    "under15": ["t_00", "t_01", "t_05", "t_10"],
    "school_age_5_14": ["t_05", "t_10"],
    "working_age_15_64": [
        "t_15", "t_20", "t_25", "t_30", "t_35",
        "t_40", "t_45", "t_50", "t_55", "t_60",
    ],
    "elderly_65_plus": ["t_65", "t_70", "t_75", "t_80", "t_85", "t_90"],
    "women_15_49": ["f_15", "f_20", "f_25", "f_30", "f_35", "f_40", "f_45"],
    "female_all": ["T_F"],
    "male_all": ["T_M"],
}

STORAGE_CRS = "EPSG:4326"
METRIC_CRS = None  # None auto-derives the UTM zone from the data

BUILDING_CONFIDENCE_THRESHOLD = 0.70

DBSCAN_EPS_METERS = 100
DBSCAN_MIN_SAMPLES = 3
INVISIBLE_BUFFER_METERS = 200
INVISIBLE_STATUS_INITIAL = "UNVERIFIED"

REGISTERED_SOURCE = "gps"
GAP_GREEN_THRESHOLD = 0.85
GAP_YELLOW_THRESHOLD = 0.50

RISK_MISSING_FACTOR_DEFAULT = 0.5

SANITY_TOLERANCE = 0.02
