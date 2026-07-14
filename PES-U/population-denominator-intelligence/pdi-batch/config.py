# Central configuration for the PDI batch pre-computation layer.

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_SOURCE = REPO_ROOT / "Data_Source"

# --- Country selection  --------
COUNTRY_ISO3 = os.getenv("PDI_ISO3", "TCD").upper()
TARGET_YEAR = int(os.getenv("PDI_YEAR", "2026"))

CACHE_DIR = Path(os.getenv("PDI_CACHE_DIR", str(REPO_ROOT / ".cache")))

GEOBOUNDARIES_API = "https://www.geoboundaries.org/api/current/gbOpen/{iso3}/{adm}/"
GEOBOUNDARIES_ADM_LEVELS = ("ADM2", "ADM1", "ADM0")

WORLDPOP_REST = "https://hub.worldpop.org/rest/data"
WORLDPOP_AGE_ALIAS = "age_structures/G2_CN_Age_R25A_100m"
WORLDPOP_TOTAL_ALIAS = "pop/G2_CN_POP_R25A_100m"
WORLDPOP_ISO = COUNTRY_ISO3.lower() 

VIDA_PARQUET_URL = (
    "https://data.source.coop/vida/google-microsoft-osm-open-buildings"
    "/geoparquet/by_country/country_iso={iso3}/{iso3}.parquet"
)

BOUNDARY_CODE_FIELD = "shapeID"
BOUNDARY_NAME_FIELD = "shapeName"

AVG_HOUSEHOLD_SIZE = 5.4

SHEET_SHEET_NAME = 0                       # first sheet, or a sheet name
SHEET_LAT_COLUMN = "Latitude"
SHEET_LON_COLUMN = "Longitude"
SHEET_CODE_COLUMN = "Service Boundary Code"
# A point up to this far outside every district is snapped to the nearest; dropped beyond.
CATCHMENT_SNAP_TOLERANCE_M = 2000

DEFAULT_TARGET_GROUPS = ["total", "under5", "age_00", "age_01_04"]

COUNTRY = COUNTRY_ISO3
CAMPAIGN_ID = "POLIO_CHAD_2024"
TENANT_ID = "default"
WORLDPOP_VERSION = "2026-CN-100m-R2025A"
OPEN_BUILDINGS_SOURCE = "vida-google-microsoft-osm"

SANITY_BBOX = None
WORLDPOP_REFERENCE = None

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
    "female_all": ["T_F"],
    "male_all": ["T_M"],
    "women_15_49": ["f_15", "f_20", "f_25", "f_30", "f_35", "f_40", "f_45"],
    "men_15_49": ["m_15", "m_20", "m_25", "m_30", "m_35", "m_40", "m_45"],
    "female_under5": ["f_00", "f_01"],
    "male_under5": ["m_00", "m_01"],
    "female_under15": ["f_00", "f_01", "f_05", "f_10"],
    "male_under15": ["m_00", "m_01", "m_05", "m_10"],
    "female_under30": ["f_00", "f_01", "f_05", "f_10", "f_15", "f_20", "f_25"],
    "male_under30": ["m_00", "m_01", "m_05", "m_10", "m_15", "m_20", "m_25"],
}

AGE_BANDS = [
    ("00", "00"), ("01", "01_04"), ("05", "05_09"), ("10", "10_14"), ("15", "15_19"),
    ("20", "20_24"), ("25", "25_29"), ("30", "30_34"), ("35", "35_39"), ("40", "40_44"),
    ("45", "45_49"), ("50", "50_54"), ("55", "55_59"), ("60", "60_64"), ("65", "65_69"),
    ("70", "70_74"), ("75", "75_79"), ("80", "80_84"), ("85", "85_89"), ("90", "90_plus"),
]
for _token, _label in AGE_BANDS:
    TARGET_GROUPS[f"female_age_{_label}"] = [f"f_{_token}"]
    TARGET_GROUPS[f"male_age_{_label}"] = [f"m_{_token}"]

STORAGE_CRS = "EPSG:4326"
# Equal-area CRS used for district area / population density (EPSG:6933).
AREA_CRS = "EPSG:6933"
METRIC_CRS = None  # None auto-derives the UTM zone from the data

BUILDING_CONFIDENCE_THRESHOLD = 0.70

DBSCAN_EPS_METERS = 100
DBSCAN_MIN_SAMPLES = 3
INVISIBLE_BUFFER_METERS = 200
INVISIBLE_STATUS_INITIAL = "UNVERIFIED"

CONCAVE_HULL_RATIO = 0.1

REGISTERED_SOURCE = "gps"
GAP_GREEN_THRESHOLD = 0.85
GAP_YELLOW_THRESHOLD = 0.50

REGISTER_ISO3 = "TCD"
REGISTER_DIR = DATA_SOURCE / "Synthetic data" / "synthetic_data"
REGISTER_INDIVIDUALS_CSV = REGISTER_DIR / "individuals_flat.csv"
REGISTER_HOUSEHOLD_SQL = REGISTER_DIR / "03_household_addresses.sql"
REGISTER_AGE_REFERENCE = "2024-06-01"


RISK_WEIGHTS = {
    "population_gap": 0.30,
    "past_performance": 0.25,
    "facility_distance": 0.20,
    "building_density": 0.15,
    "missed_children": 0.10,
}

RISK_FACILITY_MAX_KM = 50

RISK_MISSING_FACTOR_DEFAULT = 0.5
RISK_PROVISIONAL_FACTORS = ("past_performance", "missed_children")
# Priority bands on the 0-100 score.
RISK_CRITICAL_THRESHOLD = 75
RISK_HIGH_THRESHOLD = 50
RISK_MEDIUM_THRESHOLD = 25

SANITY_TOLERANCE = 0.02

OUTPUT_DIR = REPO_ROOT / "pdi-batch" / "output"
ESTIMATION_OUTPUT_DIR = OUTPUT_DIR / "estimation"
DISTRICT_POPULATION_CSV = ESTIMATION_OUTPUT_DIR / "district_population.csv"
DISTRICT_POPULATION_GEOJSON = ESTIMATION_OUTPUT_DIR / "district_population.geojson"

GAP_OUTPUT_DIR = OUTPUT_DIR / "gap"
GAP_REPORT_CSV = GAP_OUTPUT_DIR / "gap_report.csv"
GAP_REPORT_GEOJSON = GAP_OUTPUT_DIR / "gap_report.geojson"

INVISIBLE_OUTPUT_DIR = OUTPUT_DIR / "invisible"
INVISIBLE_SETTLEMENTS_CSV = INVISIBLE_OUTPUT_DIR / "invisible_settlements.csv"
INVISIBLE_SETTLEMENTS_GEOJSON = INVISIBLE_OUTPUT_DIR / "invisible_settlements.geojson"
