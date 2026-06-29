# Data Sources

This directory holds the input geospatial and registration data for the Population Denominator
Intelligence (PDI) engine. It is read at batch time by `pdi-batch/`.

Large binary datasets are not stored in version control. They exceed GitHub limits or would bloat
the repository, so they are listed below with exact instructions to download them. Small reference
data, the company input workbooks, and provenance notes are committed so the repository is usable
immediately after cloning and the download steps are self-documenting.

After cloning, recreate the full dataset by following the "Download instructions" section. File and
folder names must match exactly, because `pdi-batch/config.py` resolves paths against them.

## Directory structure

```
Data_Source/
├── README.md                                       
├── Chad/
│   ├── Worldpop/                                      
│   │   ├── WorldPop_CHAD.tif                                national all-ages raster
│   │   └── Worlpop_age_and_sex/
│   │       ├── MANIFEST.md                                  band reference + sanity totals
│   │       └── tcd_{sex}_{age}_2026_CN_100m_R2025A_v1.tif   62 age/sex band rasters
│   ├── VIDA/                                            
│   │   └── TCD.parquet                                    VIDA combined building footprints
│   └── boundaries/                                    
│       ├── gadm41_TCD.gpkg                                GADM civil hierarchy ADM0-ADM3
│       └── msp_health_2020/                               Chad MoH health layers (HDX)
│           ├── tcd_a_hlt_provincessanitaires_msp_2020/    23 health provinces (shapefile)
│           ├── tcd_a_hlt_districtssanitaires_msp_2020/    126 health districts (shapefile)
│           ├── tcd_p_hlt_formationssanitaires_msp_2020/   1,985 facility points (shapefile)
│           └── *.xlsx                                     CdS / district reference lists  
└── Synthetic data/                                   

```

## Dataset summary

| Dataset | Path | Source |
|---------|------|------|
| WorldPop population rasters | `Chad/Worldpop/` | WorldPop Hub (R2025A, 2026, constrained, 100 m) |
| VIDA building footprints | `Chad/VIDA/TCD.parquet`| Source Cooperative (VIDA combined) |
| GADM civil boundaries | `Chad/boundaries/gadm41_TCD.gpkg` | GADM 4.1 |
| MSP health boundaries | `Chad/boundaries/msp_health_2020/` | HDX (Ministère de la Santé Publique, 2020) |
| N'Djamena arrondissements | `OSM-boundry/` | OpenStreetMap + manual gap-fill |

## Download instructions

### 1. WorldPop population rasters (`Chad/Worldpop/`)

Product: Chad (TCD), projection year 2026, Constrained (settlement-masked), 100 m resolution,
release R2025A. Required files:

- `WorldPop_CHAD.tif` — national all-ages total.
- `Worlpop_age_and_sex/tcd_{sex}_{age}_2026_CN_100m_R2025A_v1.tif` — 62 age/sex band rasters.
  See `Chad/Worldpop/Worlpop_age_and_sex/MANIFEST.md` for the band tokens and the zonal-stats
  sanity totals.

Obtain from the WorldPop Hub (https://hub.worldpop.org) or the WorldPop programmatic APIs
(STAC: https://stac.worldpop.org, REST: https://www.worldpop.org/rest/data). Select the Chad
constrained age/sex structures for 2026 (R2025A) and place the files under the paths shown above.

### 2. VIDA building footprints (`Chad/VIDA/TCD.parquet`)

Product: VIDA combined building footprints (Google Open Buildings v3 + Microsoft + OpenStreetMap),
country partition for Chad (ISO `TCD`).

Source: Source Cooperative, dataset `vida/google-microsoft-open-buildings`
(https://source.coop/vida/google-microsoft-open-buildings). Download the Chad country partition and
save it as `Chad/VIDA/TCD.parquet`. The engine filters to `confidence >= 0.70` at load time.


## Notes on the boundary layers

- `gadm41_TCD.gpkg` is the committed civil-administrative hierarchy (ADM0-ADM3). The official host
  (https://geodata.ucdavis.edu/gadm/gadm4.1/gpkg/gadm41_TCD.gpkg) .
- `msp_health_2020/` is the Ministry of Public Health hierarchy (health provinces, health districts,
  facility points). This is the layer the ITN microplan is built on and the primary join for the
  health view. Source: HDX, "Chad - List of health facilities and health districts".
  
## Conventions

- Storage CRS for all layers is EPSG:4326. Distance computations reproject to the local UTM zone.
- Country profile and dataset paths are configured in `pdi-batch/config.py`.
