"""WorldPop zonal statistics computed directly from the GeoTIFFs """

import sys

from rasterstats import zonal_stats
from shapely.geometry import box

import config
from sources.boundaries import load_boundaries


def _band_raster(token):
    if token == "total":
        return config.WORLDPOP_TOTAL_RASTER
    matches = sorted(config.WORLDPOP_AGESEX_DIR.glob(f"{config.WORLDPOP_ISO}_{token}_*.tif"))
    if not matches:
        raise FileNotFoundError(f"no WorldPop band for token '{token}'")
    return matches[0]


def _zonal_sums(geometries, raster_path):
    stats = zonal_stats(list(geometries), str(raster_path), stats="sum")
    return [(entry["sum"] or 0.0) for entry in stats]


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
