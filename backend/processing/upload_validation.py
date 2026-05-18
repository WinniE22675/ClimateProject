# backend/processing/upload_validation.py
from processing.preprocessing import normalize_var_name
import os
import re
import xarray as xr
import numpy as np
from typing import List, Dict, Tuple, Any, Optional

COORD_ALIASES = {
    "latitude": ["lat", "latitude", "nav_lat", "y", "rlat"],
    "longitude": ["lon", "longitude", "nav_lon", "x", "rlon"],
    "time": ["time", "Times", "datetime", "date", "valid_time"],
}

SKIP_VARS = {"time_bnds", "lat_bnds", "lon_bnds", "height", "crs"}

ALLOWED_VARS = {"pr", "tmax", "tmin"}

VAR_ALIASES = {
    "pr": ["pr", "tp", "precip", "precipitation", "rainfall", "rr"],
    "tas": ["tas", "t2m", "temp", "temperature", "air_temperature"],
    "tmax": ["tasmax", "tmax", "tas_max", "t2m_max", "mx2t"],
    "tmin": ["tasmin", "tmin", "tas_min", "t2m_min", "mn2t"],
}

def filter_dataset_vars(ds: xr.Dataset) -> xr.Dataset:
    """
    Helper function: Keep only allowed variables, drop others.
    Does not touch coordinates (lat, lon, time).
    """
    vars_to_drop = [v for v in ds.data_vars if v not in ALLOWED_VARS]
    
    if vars_to_drop:
        print(f"Dropping unallowed variables: {vars_to_drop}") # Optional log
        ds = ds.drop_vars(vars_to_drop)
        
    return ds

def map_and_rename_coord(ds, canonical_name, aliases):
    """
    - find alias in ds.coords
    - if not equal canonical_name → rename to canonical
    - return canonical_name if found
    - return None if not found
    """
    for name in aliases:
        if name in ds.coords:
            if name != canonical_name:
                ds = ds.rename({name: canonical_name})
            return ds, canonical_name
    
    raise KeyError(
        f"Required coordinate '{canonical_name}' not found. "
        f"Checked aliases: {aliases}"
    )

# Helper Function: Extract Resolution
def get_spatial_resolution(ds: xr.Dataset) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract spatial resolution (lat_res, lon_res).
    
    Priority:
    1. rioxarray (Affine Transform via GDAL/Rasterio) - Most Accurate
    2. Global Attributes (ACDD standard) - Metadata based
    3. Calculate from Coordinates (Fallback) - Data based
    
    Returns:
        (lat_res, lon_res) as absolute float values.
        Returns (None, None) if determination fails.
    """
    lat_res, lon_res = None, None

    # --- Method 1: Rioxarray (The "Gold Standard" for GIS) ---
    # rioxarray uses the Affine Transform matrix which is the most accurate 
    # definition of resolution in geospatial files.
    try:
        if hasattr(ds, "rio"):
            # .rio.resolution() returns (x_res, y_res) -> (lon, lat)
            # Note: y_res is usually negative for north-up images.
            x_res, y_res = ds.rio.resolution()
            
            # Ensure we don't get NaN or Zero (which implies invalid CRS/Transform)
            if x_res and y_res and not np.isnan(x_res) and not np.isnan(y_res):
                return abs(float(y_res)), abs(float(x_res))
    except Exception:
        # Pass silently if rioxarray is not installed or CRS is missing
        pass 

    # --- Method 2: ACDD Metadata Attributes ---
    # Parses strings like "0.25 degrees", "0.25", "10 km"
    def parse_resolution_attr(value) -> Optional[float]:
        if not value:
            return None
        try:
            # Use regex to extract the first floating point number found
            match = re.search(r"[-+]?\d*\.\d+|\d+", str(value))
            if match:
                return float(match.group())
        except ValueError:
            return None
        return None

    try:
        if "geospatial_lat_resolution" in ds.attrs:
            lat_res = parse_resolution_attr(ds.attrs["geospatial_lat_resolution"])
        
        if "geospatial_lon_resolution" in ds.attrs:
            lon_res = parse_resolution_attr(ds.attrs["geospatial_lon_resolution"])
            
        if lat_res is not None and lon_res is not None:
            return abs(lat_res), abs(lon_res)
    except Exception:
        pass # Continue to fallback

    # --- Method 3: Calculate from Coordinates (The "Truth" from Data) ---
    # Standard names for coordinates including x/y for projected systems
    ds, lat_name = map_and_rename_coord(ds, "latitude", COORD_ALIASES["latitude"])
    ds, lon_name = map_and_rename_coord(ds, "longitude", COORD_ALIASES["longitude"])
    ds, time_name = map_and_rename_coord(ds, "time", COORD_ALIASES["time"])
        
    # 3.2 Find Lon Resolution
    try:
        if lat_name and lon_name:
            lat = ds[lat_name].values
            lon = ds[lon_name].values

            if lat.ndim == 1 and lon.ndim == 1 and len(lat) > 1 and len(lon) > 1:
                lat_res = float(abs(lat[1] - lat[0]))
                lon_res = float(abs(lon[1] - lon[0]))
                    
    except Exception as e:
        print(f"Warning: Error calculating resolution from coordinates: {e}")

    return lat_res, lon_res

def inspect_file(path: str) -> Dict[str, Any]:
    """
    Open with xarray (defer loading) and extract light metadata.
    NOTE: keep minimal IO (no heavy computation).
    """
    try:
        ds = xr.open_dataset(path, decode_times=True, mask_and_scale=False, decode_cf=True)
        vars_ = list(ds.data_vars.keys())
        coords_ = list(ds.coords.keys())
        shape = {k: int(v) for k, v in ds.sizes.items()}

        ds, lat_name = map_and_rename_coord(ds, "latitude", COORD_ALIASES["latitude"])
        ds, lon_name = map_and_rename_coord(ds, "longitude", COORD_ALIASES["longitude"])
        ds, time_name = map_and_rename_coord(ds, "time", COORD_ALIASES["time"])

        # Basic Info
        filename = None  
        file_size = f"{os.path.getsize(path)/1024/1024:.2f} MB"

        # pick time range (if exists)
        time_start = None
        time_end = None
        calendar = None
        if time_name in ds.coords:
            try:
                tvals = ds[time_name].values
                if len(tvals) > 0:
                    time_start = np.datetime_as_string(tvals.min(), unit="s")
                    time_end = np.datetime_as_string(tvals.max(), unit="s")
            except Exception:
                # fallback to str() for weird calendars
                try:
                    time_start = str(ds[time_name].min().values)
                    time_end = str(ds[time_name].max().values)
                except Exception:
                    time_start = None
                    time_end = None

            calendar = ds[time_name].encoding.get("calendar", None)

            if calendar is None:
                calendar = ds[time_name].attrs.get("calendar", None)

            if calendar is None:
                calendar = "unknown"

        try:
            delta_days = (np.datetime64(time_end) - np.datetime64(time_start)) / np.timedelta64(1, "D")
            time_years = round(delta_days / 365.25, 2)
        except Exception:
            time_years = None

        # spatial resolution: compute if lat/lon present and 1D
        spatial_resolution = None
        lat_res = lon_res = None

        if lat_name and lon_name:
            try:
                lat_min = float(ds[lat_name].min())
                lat_max = float(ds[lat_name].max())
                lon_min = float(ds[lon_name].min())
                lon_max = float(ds[lon_name].max())
                lat_res, lon_res = get_spatial_resolution(ds)
                if lat_res is not None and lon_res is not None:
                    spatial_resolution = f"{lat_res:.3f}° x {lon_res:.3f}°"
            except Exception:
                spatial_resolution = None

        # units per variable
        variable_units = {}
        standard_names = {}

        normalized_vars_all = {
            v: normalize_var_name(v)
            for v in ds.data_vars
        }

        # filter หลัง normalize
        normalized_vars = {
            orig: norm
            for orig, norm in normalized_vars_all.items()
            if norm in ALLOWED_VARS
        }

        for original, normalized in normalized_vars.items():
            attrs = ds[original].attrs

            variable_units[normalized] = attrs.get("units", None)
            standard_names[normalized] = attrs.get(
                "standard_name",
                attrs.get("long_name", None)
            )

        try:
            ds = xr.open_dataset(path, decode_times=False) # decode_times=False for read raw values
            calendar = "unknown"
            if "time" in ds.coords:
                if "calendar" in ds.time.attrs:
                    calendar = ds.time.attrs["calendar"]
                elif "calendar" in ds.time.encoding:
                    calendar = ds.time.encoding["calendar"]
            ds.close()
        except Exception:
            calendar = "error"

        ds.close()
        return {
            "path": path,
            "filename": filename,
            "file_size": file_size,

            "variables": list(normalized_vars.values()),
            "standard_names": standard_names,
            "variable_units": variable_units,

            "spatial_resolution": spatial_resolution,
            "coords": coords_,
            "shape": shape,
            "lat_min": lat_min,
            "lat_max": lat_max,
            "lon_min": lon_min,
            "lon_max": lon_max,
            "lat_res": lat_res,
            "lon_res": lon_res,

            "time_start": time_start,
            "time_end": time_end,
            "calendar": calendar,
            "time_years": time_years,

        }
    except Exception as e:
        print(f"Error inspecting {path}: {e}")
        return {"error": str(e)}

def detect_mode(metas: List[Dict[str, Any]]) -> Tuple[str, Dict[str, Any], List[str]]:
    """
    Decide upload mode based on the inspected metadata list.
    Updated to be robust for multi-variable time merges and misaligned attribute merges.
    """
    diagnostics = []
    
    # Extract the set of variables in each file
    vars_per_file = [set(m.get("variables", [])) for m in metas]
    
    # -------------------------------------------------------------------------
    # 1. TIME MODE CHECK
    # Condition: All files must have the "exact same set of variables" (Set Equality)
    # e.g., File A: {tas, pr}, File B: {tas, pr} -> Time Mode
    # -------------------------------------------------------------------------
    first_file_vars = vars_per_file[0]
    is_same_variables = all(vs == first_file_vars for vs in vars_per_file)
    
    if is_same_variables:
        mode = "time"
        # info might store the list of all variables instead
        info = {"variables": list(first_file_vars), "files": metas}
        return mode, info, diagnostics

    # -------------------------------------------------------------------------
    # 2. ATTRIBUTE MODE CHECK
    # Condition: Variables in each file must be "completely non-overlapping" (Disjoint Sets)
    # Ignore whether time coordinates match, because our backend attribute mode can handle it
    # -------------------------------------------------------------------------
    # Check if the intersection of all pairs is empty
    all_vars_flat = [v for m in metas for v in m.get("variables", [])]
    unique_vars_count = len(set(all_vars_flat))
    total_vars_count = len(all_vars_flat)
    
    # If the number of unique variables equals the total number of variables, it means there are no duplicates
    is_disjoint = unique_vars_count == total_vars_count
    
    if is_disjoint:
        mode = "attribute"
        # Create a map indicating which variable is in which file
        var_map = {}
        for idx, m in enumerate(metas):
            for v in m.get("variables", []):
                var_map[v] = idx # map variable -> file index
                
        info = {"variables": list(var_map.keys()), "files": metas, "var_map": var_map}
        return mode, info, diagnostics

    # -------------------------------------------------------------------------
    # 3. MIXED MODE (Fallback)
    # Case: Some overlapping variables, but not all, or other complexities exist
    # -------------------------------------------------------------------------
    mode = "mixed"
    
    # Create info to map which variables are in which file indices
    var_map_mixed = {}
    for idx, m in enumerate(metas):
        for v in m.get("variables", []):
            var_map_mixed.setdefault(v, []).append(idx)
            
    info = {"groups": var_map_mixed, "files": metas}
    diagnostics.append("Mixed mode detected: Overlapping variables found across files.")
    
    return mode, info, diagnostics

# (call before Clip)
def validate_compatibility(metas: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """
    Check if a list of files can be merged.
    """
    errors = []
    if not metas:
        return False, ["No files provided."]

    # filter Error file out first or tell Error 
    valid_metas = [m for m in metas if "error" not in m]
    if len(valid_metas) < len(metas):
        errors.append(f"Some files could not be read.")
        return False, errors

    if not valid_metas:
        return False, ["No valid files to process."]

    # 1. Check Calendar Consistency
    calendars = set(m.get("calendar") for m in valid_metas)
    if len(calendars) > 1:
        errors.append(f"Inconsistent calendars found: {calendars}. All files must use the same calendar system.")

    resolutions = [
        (m.get("lat_res"), m.get("lon_res"))
        for m in valid_metas
        if m.get("lat_res") is not None and m.get("lon_res") is not None
    ]

    if resolutions:
        base_lat, base_lon = resolutions[0]
        rtol_val = 1e-05

        for lat, lon in resolutions[1:]:
            if not np.isclose(lat, base_lat, rtol=rtol_val) or \
            not np.isclose(lon, base_lon, rtol=rtol_val):
                errors.append(
                    f"Inconsistent spatial resolution: "
                    f"({lat:.6f}, {lon:.6f}) != ({base_lat:.6f}, {base_lon:.6f})"
                )
    
    return len(errors) == 0, errors