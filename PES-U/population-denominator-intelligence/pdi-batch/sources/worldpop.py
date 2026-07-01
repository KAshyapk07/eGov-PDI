"""WorldPop zonal statistics computed directly from the GeoTIFFs """

import math
import sys

import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_bounds as transform_from_bounds
from rasterio.windows import Window, bounds as window_bounds, from_bounds
from rasterstats import zonal_stats
from shapely.geometry import box

import config
from sources.boundaries import load_boundaries

# Sub-pixel supersampling factor for coverage-weighted extraction 
COVERAGE_SUBSAMPLE = 10


def _band_raster(token):
    if token == "total":
        return config.WORLDPOP_TOTAL_RASTER
    matches = sorted(config.WORLDPOP_AGESEX_DIR.glob(f"{config.WORLDPOP_ISO}_{token}_*.tif"))
    if not matches:
        raise FileNotFoundError(f"no WorldPop band for token '{token}'")
    return matches[0]


def _coverage_weighted_sum(geom, src, k):
    """"Return the sum of raster values under a geometry, weighted by the fraction of each pixel covered."""
    w0 = from_bounds(*geom.bounds, src.transform)
    col0 = max(0, math.floor(w0.col_off))
    row0 = max(0, math.floor(w0.row_off))
    col1 = min(src.width, max(math.ceil(w0.col_off + w0.width), col0 + 1))
    row1 = min(src.height, max(math.ceil(w0.row_off + w0.height), row0 + 1))
    if col1 <= col0 or row1 <= row0:
        return 0.0

    win = Window(col0, row0, col1 - col0, row1 - row0)
    data = src.read(1, window=win).astype("float64")
    if src.nodata is not None:
        data = np.where(data == src.nodata, 0.0, data)
    data = np.where(np.isnan(data), 0.0, data)

    height, width = data.shape
    kk = max(1, min(k, 1500 // max(height, width)))
    fine = transform_from_bounds(*window_bounds(win, src.transform), width * kk, height * kk)
    cover = rasterize([(geom, 1)], out_shape=(height * kk, width * kk),
                      transform=fine, fill=0, dtype="uint8")
    fraction = np.reshape(cover, (height, kk, width, kk)).mean(axis=(1, 3))
    return float((data * fraction).sum())


def _zonal_sums(geometries, raster_path, k=COVERAGE_SUBSAMPLE):
    with rasterio.open(raster_path) as src:
        return [_coverage_weighted_sum(geom, src, k) for geom in geometries]


def _bbox_sum(raster_path, bbox):
    return zonal_stats([box(*bbox)], str(raster_path), stats="sum")[0]["sum"] or 0.0


def _group_rows(codes, band_sums, groups):
    rows = []
    for index, code in enumerate(codes):
        row = {"boundary_code": code}
        for name, tokens in groups.items():
            row[name] = sum(band_sums[token][index] for token in tokens)
        rows.append(row)
    return rows


def compute_zonal(boundaries):
    """Per-boundary population for every configured target group, keyed by boundary_code."""
    codes = boundaries[config.BOUNDARY_CODE_FIELD].tolist()
    tokens = {token for tokens in config.TARGET_GROUPS.values() for token in tokens}
    band_sums = {
        token: _zonal_sums(boundaries.geometry, _band_raster(token)) for token in tokens
    }
    return _group_rows(codes, band_sums, config.TARGET_GROUPS)


def run_sanity_check():
    if not (config.SANITY_BBOX and config.WORLDPOP_REFERENCE):
        print("no bbox reference configured; skipping exact sanity check")
        return True

    bbox = config.SANITY_BBOX
    passed = True
    for label, expected in config.WORLDPOP_REFERENCE.items():
        measured = sum(_bbox_sum(_band_raster(token), bbox) for token in config.TARGET_GROUPS[label])
        deviation = abs(measured - expected) / expected
        status = "PASS" if deviation <= config.SANITY_TOLERANCE else "FAIL"
        passed = passed and status == "PASS"
        print(f"{label:<7} measured={measured:>12,.0f} expected={expected:>12,.0f} "
              f"deviation={deviation:6.2%} {status}")
    return passed


def main():
    print("WorldPop bbox sanity check")
    passed = run_sanity_check()

    print(f"\nPer-boundary population ({len(config.TARGET_GROUPS)} target groups computed)")
    boundaries = load_boundaries()
    rows = sorted(compute_zonal(boundaries), key=lambda row: row["boundary_code"])
    for row in rows:
        print(f"{row['boundary_code']:<12} total={row['total']:>10,.0f} "
              f"under5={row['under5']:>9,.0f}")

    footprint = sum(row["total"] for row in rows)
    print(f"\n{'footprint':<12} total={footprint:>10,.0f} (sum over loaded boundaries)")

    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
