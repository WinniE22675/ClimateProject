import os
import geopandas as gpd
import json
import shapely

def overlay_with_shapefile(input_path: str, shapefile: gpd.GeoDataFrame):
    """
    Overlay output GeoJSON/GeoDataFrame with country boundary.
    Works for the map output from preview export.
    """
    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        return input_path

    # try:
    with open(input_path, "r") as f:
        original = json.load(f)

    metadata = original.get("metadata", {})
    features_list = original.get("features", [])

    if not features_list:
            print(f"No features to overlay in {input_path}")
            return input_path

    gdf = gpd.GeoDataFrame.from_features(original["features"], crs="EPSG:4326")

    clipped = gpd.overlay(gdf, shapefile, how="intersection")

    clipped['geometry'] = shapely.set_precision(clipped['geometry'].values, grid_size=0.001)

    for col in clipped.select_dtypes(include=['datetime', 'datetimetz']).columns:
        clipped[col] = clipped[col].astype(str)

    features = json.loads(clipped.to_json())["features"]

    out = {
    "type": "FeatureCollection",
    "metadata": metadata,
    "features": features,
    }

    print(f"Overlay applied to {input_path}")

    with open(input_path, "w") as f:
        json.dump(out, f, separators=(',', ':'))

    print(f"Overlay applied (metadata preserved) to {input_path}")
    return input_path

