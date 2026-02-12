import os
import json
import numpy as np
import xarray as xr
from shapely.geometry import Polygon
from cf_xarray import vertices_to_bounds
import pymannkendall as mk

# base output folder (configurable)
# OUT_MAPS = "output/maps_grid"
# os.makedirs(OUT_MAPS, exist_ok=True)

# ========== helper functions ==========

LON_CF_ATTRS = {"standard_name": "longitude", "units": "degrees_east"}
LAT_CF_ATTRS = {"standard_name": "latitude", "units": "degrees_north"}


def _grid_1d(start_b, end_b, step):
    bounds = np.arange(start_b, end_b + step / 2, step)
    centers = (bounds[:-1] + bounds[1:]) / 2
    return centers, bounds


def cf_grid_2d(lon0_b, lon1_b, d_lon, lat0_b, lat1_b, d_lat):
    lon_1d, lon_b_1d = _grid_1d(lon0_b, lon1_b, d_lon)
    lat_1d, lat_b_1d = _grid_1d(lat0_b, lat1_b, d_lat)

    ds = xr.Dataset(
        coords={
            "lon": ("lon", lon_1d, {"bounds": "lon_bounds", **LON_CF_ATTRS}),
            "lat": ("lat", lat_1d, {"bounds": "lat_bounds", **LAT_CF_ATTRS}),
            "latitude_longitude": xr.DataArray(),
        },
        data_vars={
            "lon_bounds": vertices_to_bounds(lon_b_1d, ("bound", "lon")),
            "lat_bounds": vertices_to_bounds(lat_b_1d, ("bound", "lat")),
        },
    )
    return ds


# ========== 1. Export Actual Map ==========
def export_actual_maps_xesmf(index_data: xr.DataArray, index_name: str, output_base_dir: str):
    """Export average map (GeoJSON grid) over a the dataset's time range."""
    # print("w")
    actual = index_data.sortby("latitude", "longitude")
    avg_map = actual.mean("time", skipna=True)

    # create grid from latitude/longitude of dataset
    lat = avg_map.latitude.values
    lon = avg_map.longitude.values
    d_lat = abs(lat[1] - lat[0])
    d_lon = abs(lon[1] - lon[0])

    grid = cf_grid_2d(
        lon.min() - d_lon / 2,
        lon.max() + d_lon / 2,
        d_lon,
        lat.min() - d_lat / 2,
        lat.max() + d_lat / 2,
        d_lat,
    )
    # print("ww")
    features = []
    for i in range(len(lat)):
        # print(i)
        for j in range(len(lon)):
            # print(j)
            val = (
                avg_map.sel(latitude=lat[i], longitude=lon[j], method="nearest")
                .values.item()
            )
            if np.isnan(val):
                continue

            # print(val)

            poly = Polygon(
                [
                    (grid["lon_bounds"][j, 0], grid["lat_bounds"][i, 0]),
                    (grid["lon_bounds"][j, 1], grid["lat_bounds"][i, 0]),
                    (grid["lon_bounds"][j, 1], grid["lat_bounds"][i, 1]),
                    (grid["lon_bounds"][j, 0], grid["lat_bounds"][i, 1]),
                ]
            )

            # print(poly)

            features.append(
                {
                    "type": "Feature",
                    "geometry": poly.__geo_interface__,
                    "properties": {"value": round(float(val),2)},
                }
            )
    # print("www")
    out = {
        "type": "FeatureCollection",
        "metadata": {
            "index": index_name,
            "unit": getattr(index_data, "units", ""),
            "start_date": str(index_data.time.min().values)[:10],
            "end_date": str(index_data.time.max().values)[:10],
            "years": [
                int(index_data.time.dt.year.min()),
                int(index_data.time.dt.year.max()),
            ],
        },
        "features": features,
    }

    out_dir = os.path.join(output_base_dir, "maps_grid", "actual") # OUT_MAPS
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{index_name}_actual_grid.geojson")

    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"  Saved actual map to {out_path}")

    return out_path


# ========== 2. Export Trend Map ==========
def export_trend_map_xesmf(index_data: xr.DataArray, index_name: str, output_base_dir: str):
    """Export trend map using Mann-Kendall test (GeoJSON grid)."""
    trend = index_data.sortby("latitude", "longitude")
    lats = trend.latitude.values
    lons = trend.longitude.values
    d_lat = abs(lats[1] - lats[0])
    d_lon = abs(lons[1] - lons[0])

    grid = cf_grid_2d(
        lons.min() - d_lon / 2,
        lons.max() + d_lon / 2,
        d_lon,
        lats.min() - d_lat / 2,
        lats.max() + d_lat / 2,
        d_lat,
    )

    slope_map = np.full((len(lats), len(lons)), np.nan)
    p_map = np.full_like(slope_map, np.nan)

    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            series = trend[:, i, j].values
            if np.sum(~np.isnan(series)) >= len(series) * 0.7:
                try:
                    result = mk.original_test(series)
                    slope_map[i, j] = result.slope * 10  # per decade
                    p_map[i, j] = result.p
                except Exception:
                    pass

    features = []
    for i in range(len(lats)):
        for j in range(len(lons)):
            slope = slope_map[i, j]
            pval = p_map[i, j]
            if not np.isnan(slope):
                poly = Polygon(
                    [
                        (grid["lon_bounds"][j, 0], grid["lat_bounds"][i, 0]),
                        (grid["lon_bounds"][j, 1], grid["lat_bounds"][i, 0]),
                        (grid["lon_bounds"][j, 1], grid["lat_bounds"][i, 1]),
                        (grid["lon_bounds"][j, 0], grid["lat_bounds"][i, 1]),
                    ]
                )

                features.append(
                    {
                        "type": "Feature",
                        "geometry": poly.__geo_interface__,
                        "properties": {"slope": round(float(slope),2), "p": round(float(pval),2)},
                    }
                )

    out = {
        "type": "FeatureCollection",
        "metadata": {
            "index": index_name,
            "method": "Mann-Kendall",
            "unit": getattr(index_data, "units", ""),
            "start_date": str(index_data.time.min().values)[:10],
            "end_date": str(index_data.time.max().values)[:10],
            "years": [
                int(index_data.time.dt.year.min()),
                int(index_data.time.dt.year.max()),
            ],
        },
        "features": features,
    }

    out_dir = os.path.join(output_base_dir, "maps_grid", "trend") # OUT_MAPS
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{index_name}_trend_grid.geojson")

    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"  Saved trend map to {out_path}")

    return out_path
