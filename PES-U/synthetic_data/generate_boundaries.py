"""
Generate GeoJSON boundary polygons from synthetic dataset GPS coordinates.

Uses Voronoi tessellation clipped to N'Djamena bounding box to create
approximate catchment area polygons for each health center boundary.
Output format matches egovernments/egov-mdms-data map-config GeoJSON structure.
"""

import pandas as pd
import json
import os
from scipy.spatial import Voronoi
from shapely.geometry import Polygon, MultiPoint, box, mapping
from shapely.ops import unary_union
import numpy as np
from collections import defaultdict

# ── Config ──────────────────────────────────────────────────────
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "individuals_flat.csv")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "boundary_data")

# N'Djamena bounding box (used to clip Voronoi regions)
NDJAMENA_BBOX = {
    "min_lon": 14.95,
    "max_lon": 15.15,
    "min_lat": 11.98,
    "max_lat": 12.20,
}


def load_data():
    """Load CSV and compute centroids per boundary."""
    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} records with {df['boundary_code'].nunique()} boundaries")

    centroids = {}
    boundary_points = defaultdict(list)
    boundary_names = {}

    for code, group in df.groupby("boundary_code"):
        lat = group["latitude"].mean()
        lon = group["longitude"].mean()
        centroids[code] = (lon, lat)  # Shapely uses (x, y) = (lon, lat)
        boundary_names[code] = group["locality_name"].iloc[0]
        for _, row in group.iterrows():
            boundary_points[code].append((row["longitude"], row["latitude"]))

    return centroids, boundary_points, boundary_names


def voronoi_polygons(centroids, bbox):
    """Generate Voronoi polygons from centroids, clipped to bounding box."""
    codes = list(centroids.keys())
    points = np.array([centroids[c] for c in codes])

    # Add far-away mirror points to bound the Voronoi diagram
    x_range = bbox["max_lon"] - bbox["min_lon"]
    y_range = bbox["max_lat"] - bbox["min_lat"]
    mirror_points = np.array([
        [bbox["min_lon"] - x_range * 2, bbox["min_lat"] - y_range * 2],
        [bbox["max_lon"] + x_range * 2, bbox["min_lat"] - y_range * 2],
        [bbox["min_lon"] - x_range * 2, bbox["max_lat"] + y_range * 2],
        [bbox["max_lon"] + x_range * 2, bbox["max_lat"] + y_range * 2],
    ])
    all_points = np.vstack([points, mirror_points])

    vor = Voronoi(all_points)
    clip_box = box(bbox["min_lon"], bbox["min_lat"], bbox["max_lon"], bbox["max_lat"])

    polygons = {}
    for i, code in enumerate(codes):
        region_idx = vor.point_region[i]
        region = vor.regions[region_idx]

        if -1 in region or len(region) == 0:
            # Fallback: convex hull of actual points
            pts = centroids[code]
            polygons[code] = clip_box  # Will be replaced by convex hull below
            continue

        vertices = [vor.vertices[v] for v in region]
        try:
            poly = Polygon(vertices)
            if not poly.is_valid:
                poly = poly.buffer(0)
            poly = poly.intersection(clip_box)
            if poly.is_empty:
                poly = None
            polygons[code] = poly
        except Exception:
            polygons[code] = None

    return polygons


def convex_hull_polygons(boundary_points):
    """Fallback: generate convex hull polygons from actual GPS points."""
    polygons = {}
    for code, pts in boundary_points.items():
        if len(pts) < 3:
            # Not enough points for a polygon, create small buffer around centroid
            from shapely.geometry import Point
            centroid = Point(np.mean([p[0] for p in pts]), np.mean([p[1] for p in pts]))
            polygons[code] = centroid.buffer(0.002)  # ~200m radius
        else:
            mp = MultiPoint(pts)
            hull = mp.convex_hull
            if hull.geom_type == "Point" or hull.geom_type == "LineString":
                hull = hull.buffer(0.002)
            polygons[code] = hull
    return polygons


def build_geojson(polygons, boundary_names, method="voronoi"):
    """Build GeoJSON FeatureCollection matching egov-mdms-data format."""
    features = []

    for code in sorted(polygons.keys()):
        poly = polygons[code]
        if poly is None or poly.is_empty:
            continue

        name = boundary_names.get(code, code)

        feature = {
            "type": "Feature",
            "id": code,
            "properties": {
                "name": name,
                "boundaryCode": code,
                "type": "HEALTH_CENTER" if "_CS_" in code else "POLLING_AREA",
                "method": method,
            },
            "geometry": mapping(poly),
        }
        features.append(feature)

    # Compute center for map config
    all_coords = []
    for poly in polygons.values():
        if poly and not poly.is_empty:
            centroid = poly.centroid
            all_coords.append((centroid.x, centroid.y))

    center_lon = np.mean([c[0] for c in all_coords])
    center_lat = np.mean([c[1] for c in all_coords])

    geojson = {
        "type": "FeatureCollection",
        "metadata": {
            "campaign": "POLIO_CHAD_2024",
            "region": "N'Djamena",
            "center": [center_lon, center_lat],
            "zoom": 12,
            "boundaryCount": len(features),
            "source": "Generated from synthetic dataset GPS coordinates",
        },
        "features": features,
    }
    return geojson


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Loading synthetic data...")
    centroids, boundary_points, boundary_names = load_data()

    # Method 1: Voronoi tessellation (non-overlapping full coverage)
    print("\nGenerating Voronoi boundary polygons...")
    vor_polygons = voronoi_polygons(centroids, NDJAMENA_BBOX)

    # Fill any None entries with convex hull fallback
    hull_polygons = convex_hull_polygons(boundary_points)
    for code in vor_polygons:
        if vor_polygons[code] is None or vor_polygons[code].is_empty:
            vor_polygons[code] = hull_polygons.get(code)

    voronoi_geojson = build_geojson(vor_polygons, boundary_names, "voronoi")

    voronoi_path = os.path.join(OUTPUT_DIR, "ndjamena_boundaries_voronoi.json")
    with open(voronoi_path, "w", encoding="utf-8") as f:
        json.dump(voronoi_geojson, f, indent=2, ensure_ascii=False)
    print(f"Voronoi boundaries saved: {voronoi_path}")
    print(f"  Features: {len(voronoi_geojson['features'])}")

    # Method 2: Convex hull (actual spread of registered households)
    print("\nGenerating convex hull boundary polygons...")
    hull_geojson = build_geojson(hull_polygons, boundary_names, "convex_hull")

    hull_path = os.path.join(OUTPUT_DIR, "ndjamena_boundaries_convex_hull.json")
    with open(hull_path, "w", encoding="utf-8") as f:
        json.dump(hull_geojson, f, indent=2, ensure_ascii=False)
    print(f"Convex hull boundaries saved: {hull_path}")
    print(f"  Features: {len(hull_geojson['features'])}")

    # Summary
    print("\n" + "=" * 60)
    print("BOUNDARY FILES GENERATED")
    print("=" * 60)
    print(f"\n1. Voronoi tessellation: {voronoi_path}")
    print("   - Non-overlapping polygons covering entire N'Djamena bbox")
    print("   - Best for: area coverage analysis, population estimation")
    print(f"\n2. Convex hull: {hull_path}")
    print("   - Tight polygons around actual household GPS clusters")
    print("   - Best for: visualizing actual registration spread")
    print(f"\nBoth files use the same GeoJSON format as egov-mdms-data map-config.")
    print("Each feature has: properties.name, properties.boundaryCode, geometry")
    print(f"\nTotal boundaries: {len(voronoi_geojson['features'])}")


if __name__ == "__main__":
    main()
