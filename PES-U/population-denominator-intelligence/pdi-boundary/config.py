from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_SOURCE = REPO_ROOT / "Data_Source"

ITN_BOUNDARY_XLSX = (
    DATA_SOURCE / "Synthetic data" / "itn_microplan" / "Chad_ITN_Boundary_Data_EN.xlsx"
)
ITN_BOUNDARY_SHEET = "Boundary Data"

MSP_HEALTH_DIR = DATA_SOURCE / "Chad" / "boundaries" / "msp_health_2020"
MSP_DISTRICTS_SHP = (
    MSP_HEALTH_DIR / "tcd_a_hlt_districtssanitaires_msp_2020"
    / "tcd_a_hlt_districtsSanitaires_msp_2020.shp"
)
MSP_PROVINCES_SHP = (
    MSP_HEALTH_DIR / "tcd_a_hlt_provincessanitaires_msp_2020"
    / "tcd_a_hlt_provincesSanitaires_msp_2020.shp"
)
MSP_FACILITIES_SHP = (
    MSP_HEALTH_DIR / "tcd_p_hlt_formationssanitaires_msp_2020"
    / "tcd_p_hlt_formationsSanitaires_msp_2020.shp"
)

OUTPUT_DIR = REPO_ROOT / "pdi-boundary" / "output"

COMMON_DISTRICTS_GEOJSON = OUTPUT_DIR / "chad_districts_common.geojson"

MSP_ONLY_GEOJSON = OUTPUT_DIR / "districts_not_in_microplan.geojson"

DISTRICT_MISMATCH_CSV = OUTPUT_DIR / "district_mismatch.csv"

DISTRICT_RECONCILIATION_CSV = OUTPUT_DIR / "district_reconciliation.csv"

BOUNDARY_CODE_FIELD = "Boundary_code"

STORAGE_CRS = "EPSG:4326"

DISTRICT_FUZZY_CUTOFF = 0.82
