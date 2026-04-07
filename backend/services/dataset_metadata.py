import os
import xarray as xr
import numpy as np
import pandas as pd
import json
from services.dataset_paths import get_dataset_output_dir

INVALID_NAMES = {"unknown", "unspecified", "n/a", "na", ""}

def is_valid_name(x):
    if x is None:
        return False
    if not isinstance(x, str):
        return False
    return x.strip().lower() not in INVALID_NAMES

def read_metadata_json(dataset_name: str) -> dict:
    """Read and return metadata.json as a dictionary."""
    meta_path = os.path.join(get_dataset_output_dir(dataset_name), "metadata.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def get_dataset_metadata_merged(dataset_name):
    """
    Open all processed files as a single virtual dataset 
    to get combined metadata (Time range, Lat/Lon bounds, Variables).
    """

    merged_path = os.path.join(
        get_dataset_output_dir(dataset_name),
        "merged.nc" 
    )

    if not os.path.exists(merged_path):
        return None

    try:
        with xr.open_dataset(merged_path) as ds:

            # Extract Variables Info
            # variables = [v for v in ds.data_vars]
            variables_list = list(ds.data_vars)
            standard_names = {}
            variable_units = {}
            
            for v in variables_list:
                attrs = ds[v].attrs
                variable_units[v] = ds[v].attrs.get("units", "unknown")
                # standard_names[v] = ds[v].attrs.get("standard_name", ds[v].attrs.get("long_name", v))
                std = attrs.get("standard_name")
                long_n = attrs.get("long_name")
                # standard_names[v] = std if std else (long_n if long_n else v)
                if is_valid_name(std):
                    standard_names[v] = std
                elif is_valid_name(long_n):
                    standard_names[v] = long_n
                else:
                    standard_names[v] = v

            # Spatial Resolution
            # lat_res = abs(ds.latitude.values[1] - ds.latitude.values[0]) if len(ds.latitude) > 1 else 0
            # lon_res = abs(ds.longitude.values[1] - ds.longitude.values[0]) if len(ds.longitude) > 1 else 0
            # spatial_resolution = f"{lat_res:.3f}° x {lon_res:.3f}°"

            if len(ds.latitude) > 1 and len(ds.longitude) > 1:
                # Calculate absolute differences between all adjacent points
                lat_diffs = np.abs(np.diff(ds.latitude.values))
                lon_diffs = np.abs(np.diff(ds.longitude.values))

                # Calculate average resolution
                lat_res_avg = lat_diffs.mean()
                lon_res_avg = lon_diffs.mean()

                # Check if irregular (if max diff and min diff vary by more than 0.001 degrees)
                lat_is_irreg = (lat_diffs.max() - lat_diffs.min()) > 1e-3
                lon_is_irreg = (lon_diffs.max() - lon_diffs.min()) > 1e-3

                # Add '~' (tilde) if the grid is irregular to indicate approximation
                lat_str = f"~{lat_res_avg:.3f}°" if lat_is_irreg else f"{lat_res_avg:.3f}°"
                lon_str = f"~{lon_res_avg:.3f}°" if lon_is_irreg else f"{lon_res_avg:.3f}°"

                spatial_resolution = f"{lat_str} x {lon_str}"
            
            # Extract Time Info
            # time_min = str(ds.time.min().values)[:10]
            # time_max = str(ds.time.max().values)[:10]
            # time_min = pd.Timestamp(ds.time.min().values).isoformat()
            # time_max = pd.Timestamp(ds.time.max().values).isoformat()
            try:
                # xarray's .dt.strftime smartly handles both datetime64 and cftime automatically
                time_min = str(ds.time.min().dt.strftime("%Y-%m-%dT%H:%M:%S").item())
                time_max = str(ds.time.max().dt.strftime("%Y-%m-%dT%H:%M:%S").item())
            except Exception:
                # Fallback just in case the time variable is not a proper datetime format
                time_min_obj = ds.time.min().values.item()
                time_max_obj = ds.time.max().values.item()
                time_min = str(time_min_obj)[:10]
                time_max = str(time_max_obj)[:10]
            
            # Extract Spatial Info
            lat_min = float(ds.latitude.min())
            lat_max = float(ds.latitude.max())
            lon_min = float(ds.longitude.min())
            lon_max = float(ds.longitude.max())

            # Calculate Time Span (Years)
            # use len(unique years) 
            years = np.unique(ds.time.dt.year)
            time_years = len(years)

            calendar = None
            calendar = ds["time"].encoding.get("calendar", None)

            if calendar is None:
                calendar = ds["time"].attrs.get("calendar", None)

            if calendar is None:
                calendar = "unknown"
            
            metadata = {
                "variables": variables_list,
                "standard_names": standard_names,
                "variable_units": variable_units,
                "shape": {k: v for k, v in ds.sizes.items()},
                "lat_min": round(lat_min, 4),
                "lat_max": round(lat_max, 4),
                "lon_min": round(lon_min, 4),
                "lon_max": round(lon_max, 4),
                "time_start": time_min,
                "time_end": time_max,
                "time_years": time_years,
                "spatial_resolution": spatial_resolution,
                "calendar": calendar,
            }
        return metadata
    
    except Exception as e:
        print(f"Error reading merged metadata: {e}")
        return None