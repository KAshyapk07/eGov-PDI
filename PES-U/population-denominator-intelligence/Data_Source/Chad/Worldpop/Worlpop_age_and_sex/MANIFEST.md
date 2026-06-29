# WorldPop Chad age-sex rasters

Filename pattern: `tcd_{sex}_{age}_2026_CN_100m_R2025A_v1.tif`
- `tcd` Chad · `CN` constrained (settlement-masked) · `100m` cell (~0.000833°, EPSG:4326) · `2026` projection year · `R2025A_v1` release.
- Each cell holds the estimated number of people of that sex/age band living in it. Counts come from summing cells over an area.

## Sex token
| Token | Meaning |
|-------|---------|
| `f_NN` | female, age band NN |
| `m_NN` | male, age band NN |
| `t_NN` | both sexes, age band NN (= f_NN + m_NN) |
| `T_F`  | female, all ages |
| `T_M`  | male, all ages |

## Age bands (NN = start year)
| NN | Ages | NN | Ages | NN | Ages |
|----|------|----|------|----|------|
| 00 | 0 (under 1) | 30 | 30-34 | 60 | 60-64 |
| 01 | 1-4  | 35 | 35-39 | 65 | 65-69 |
| 05 | 5-9  | 40 | 40-44 | 70 | 70-74 |
| 10 | 10-14| 45 | 45-49 | 75 | 75-79 |
| 15 | 15-19| 50 | 50-54 | 80 | 80-84 |
| 20 | 20-24| 55 | 55-59 | 85 | 85-89 |
| 25 | 25-29|    |       | 90 | 90+   |

## Filter mapping
| Filter | Files to sum |
|--------|--------------|
| Total population | `../WorldPop_CHAD.tif` |
| Under-5 (0-4) | `t_00` + `t_01` |
| Female under-5 | `f_00` + `f_01` |
| Female / male (all ages) | `T_F` / `T_M` |
| Age band (e.g. 20-24) | `t_20` |
| Women of childbearing age (15-49, F) | `f_15`+`f_20`+`f_25`+`f_30`+`f_35`+`f_40`+`f_45` |

The 40 `f_*`/`m_*` band files are the primitives; `t_*`, `T_F`, `T_M` are derivable conveniences.

## Reference numbers (N'Djamena bbox 14.98-15.13 E, 12.06-12.21 N)
- Total: 1,632,766 · Under-5: 305,893 · Female: 809,570 · Male: 823,197 (F+M = Total).
