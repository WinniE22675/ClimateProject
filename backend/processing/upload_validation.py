# backend/processing/upload_validation.py
from processing.preprocessing import normalize_var_name
import os
import re
import xarray as xr
import numpy as np
from typing import List, Dict, Tuple, Any, Optional

"""
Utilities to inspect NetCDF/GRIB/CSV (xarray-readable) files,
detect upload mode (attribute / time / mixed), and validate compatibility.

Functions:
- inspect_file(path) -> dict (variables, dims, coords, time_range, resolution, units)
- detect_mode(metadata_list) -> ("attribute"|"time"|"mixed", grouping_info, diagnostics)
- validate_attribute_mode(meta_list) -> (ok, errors)
- validate_time_mode(meta_list) -> (ok, errors)
- validate_mixed_mode(meta_list) -> (ok, errors, groups)
"""

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

# def normalize_var_name(name: str) -> str:
#     """
#     Map variable names to standardized aliases.
#     Example: tp → pr, t2m → tas
#     """
#     for std, aliases in VAR_ALIASES.items():
#         if name.lower() in aliases:
#             return std
#     return name

def filter_dataset_vars(ds: xr.Dataset) -> xr.Dataset:
    """
    Helper function: Keep only allowed variables, drop others.
    Does not touch coordinates (lat, lon, time).
    """
    # หาตัวแปรที่ "ไม่ได้" อยู่ใน ALLOWED_VARS
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

# ------------------------------------------------------------------------------
# Helper Function: Extract Resolution
# ------------------------------------------------------------------------------

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
        # filename = os.path.basename(path)
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
            # print("delta_days :",delta_days)
            # print("np.datetime64(time_end)", np.datetime64(time_end))
            # print("np.datetime64(time_start)", np.datetime64(time_start))
            # print("np.timedelta64(1, D)", np.timedelta64(1, "D"))
            # print("np.datetime64(time_end) - np.datetime64(time_start)", np.datetime64(time_end) - np.datetime64(time_start))
            time_years = round(delta_days / 365.25, 2)
        except Exception:
            time_years = None

        # spatial resolution: compute if lat/lon present and 1D
        spatial_resolution = None
        lat_res = lon_res = None
        # lat_name = None
        # lon_name = None
        # for n in ["lat", "latitude", "y", "nav_lat"]:
        #     if n in ds.coords:
        #         lat_name = n
        #         break
        # for n in ["lon", "longitude", "x", "nav_lon"]:
        #     if n in ds.coords:
        #         lon_name = n
        #         break

        if lat_name and lon_name:
            try:
                # lat = ds[lat_name].values
                # lon = ds[lon_name].values

                # lat_min = float(lat.min())
                # lat_max = float(lat.max())
                # lon_min = float(lon.min())
                # lon_max = float(lon.max())
                lat_min = float(ds[lat_name].min())
                lat_max = float(ds[lat_name].max())
                lon_min = float(ds[lon_name].min())
                lon_max = float(ds[lon_name].max())


                # if lat.ndim == 1 and lon.ndim == 1 and len(lat) > 1 and len(lon) > 1:
                #     lat_res = float(abs(lat[1] - lat[0]))
                #     lon_res = float(abs(lon[1] - lon[0]))
                lat_res, lon_res = get_spatial_resolution(ds)
                # spatial_resolution = (round(lat_res, 6), round(lon_res, 6))
                if lat_res is not None and lon_res is not None:
                    spatial_resolution = f"{lat_res:.3f}° x {lon_res:.3f}°"
            except Exception:
                spatial_resolution = None

        # units per variable
        variable_units = {}
        standard_names = {}

        # vars_filtered = [v for v in vars_ if v not in SKIP_VARS]

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

        # normalized_vars = {v: normalize_var_name(v) for v in vars_filtered}

        # for v in normalized_vars:
        #     attrs = ds[v].attrs
        #     variable_units[v] = attrs.get("units", None)
        #     standard_names[v] = attrs.get("standard_name", attrs.get("long_name", None))
        for original, normalized in normalized_vars.items():
            attrs = ds[original].attrs

            variable_units[normalized] = attrs.get("units", None)
            standard_names[normalized] = attrs.get(
                "standard_name",
                attrs.get("long_name", None)
            )

        try:
            ds = xr.open_dataset(path, decode_times=False) # decode_times=False เพื่ออ่านค่าดิบ
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

# def inspect_file(path: str) -> Dict[str, Any]:
#     """
#     Open file and extract metadata efficiently.
#     """
#     try:
#         # decode_times=False เพื่ออ่านค่า raw calendar และ units
#         ds = xr.open_dataset(path, decode_times=False, chunks={})
        
#         # 1. Identify Time Variable
#         time_var = None
#         for t in ["time", "t", "date"]:
#             if t in ds.coords:
#                 time_var = t
#                 break
        
#         calendar = "unknown"
#         if time_var:
#             if "calendar" in ds[time_var].attrs:
#                 calendar = ds[time_var].attrs["calendar"]
#             elif "calendar" in ds[time_var].encoding:
#                 calendar = ds[time_var].encoding["calendar"]
        
#         # 2. Get Resolution (Lat/Lon)
#         lat_res, lon_res = None, None
#         # พยายามหา Resolution จากความต่างของ coordinates 2 จุดแรก
#         # (สมมติว่าเป็น standard names 'lat', 'lon' หรือชื่ออื่นๆที่ ds มี)
#         # เพื่อความง่ายในการ validate เราจะลองหาจาก coords ที่มี
#         for lat_name in ['lat', 'latitude']:
#             if lat_name in ds.coords and ds[lat_name].size > 1:
#                 lat_res = abs(float(ds[lat_name][1] - ds[lat_name][0]))
#                 break
        
#         for lon_name in ['lon', 'longitude']:
#             if lon_name in ds.coords and ds[lon_name].size > 1:
#                 lon_res = abs(float(ds[lon_name][1] - ds[lon_name][0]))
#                 break

#         # 3. Variables
#         vars_ = list(ds.data_vars.keys())

#         ds.close()
        
#         return {
#             "path": path,
#             "variables": vars_,
#             "calendar": calendar,
#             "lat_res": lat_res,
#             "lon_res": lon_res
#         }

#     except Exception as e:
#         print(f"Error inspecting {path}: {e}")
#         return {"error": str(e)}

'''
def detect_mode(metas: List[Dict[str, Any]]) -> Tuple[str, Dict[str, Any], List[str]]:
    """
    Decide upload mode based on the inspected metadata list.

    Returns:
      mode: "attribute" | "time" | "mixed"
      info: useful grouping info (e.g., grouped by variable)
      diagnostics: list of strings (notes/warnings)
    """
    diagnostics = []
    all_vars = []
    for m in metas:
        all_vars.extend(m.get("variables", []))
    unique_vars = sorted(set(all_vars))

    # count unique variables per file
    vars_per_file = [set(m.get("variables", [])) for m in metas]

    # If every file has exactly the same single variable -> time mode candidate
    single_var_files = all(len(vs) == 1 for vs in vars_per_file)
    if single_var_files:
        # check whether all files share the same variable
        vars_in_files = [next(iter(vs)) for vs in vars_per_file]
        if len(set(vars_in_files)) == 1:
            mode = "time"
            info = {"variable": vars_in_files[0], "files": metas}
            return mode, info, diagnostics

    # If no overlapping variables across files (each file contains different variables OR files contain differing sets)
    # but all files are not single-variable identical times -> attribute candidate
    # We'll be conservative: if union(vars per file) > 1 and there is at least one file with different variable set -> attribute or mixed
    # Mixed: some files are single-var with same variable but others have different variable -> mixed
    # Simpler logic:
    # - if each file contains different variables and times are identical -> attribute
    # - else mixed

    # Build variable -> list of file indices map
    var_map = {}
    for idx, m in enumerate(metas):
        for v in m.get("variables", []):
            var_map.setdefault(v, []).append(idx)

    # if all variables appear in only one file and files have same time extents -> attribute
    all_vars_unique_files = all(len(var_map[v]) == 1 for v in var_map)
    times = [(m.get("time_start"), m.get("time_end")) for m in metas]
    times_equal = len(set(times)) == 1

    if all_vars_unique_files and times_equal:
        mode = "attribute"
        info = {"variables": list(var_map.keys()), "files": metas}
        return mode, info, diagnostics

    # fallback: mixed
    mode = "mixed"
    # grouping by variable: list of file indices for each variable
    # groups = {}
    # for v, idxs in var_map.items():
    #     groups[v] = [metas[i] for i in idxs]
    # info = {"groups": groups}
    info = {"groups": var_map}
    diagnostics.append("Mixed mode detected: multiple variables and/or differing time ranges.")
    return mode, info, diagnostics
'''

def detect_mode(metas: List[Dict[str, Any]]) -> Tuple[str, Dict[str, Any], List[str]]:
    """
    Decide upload mode based on the inspected metadata list.
    Updated to be robust for multi-variable time merges and misaligned attribute merges.
    """
    diagnostics = []
    
    # ดึงเซตของตัวแปรในแต่ละไฟล์
    vars_per_file = [set(m.get("variables", [])) for m in metas]
    
    # -------------------------------------------------------------------------
    # 1. TIME MODE CHECK
    # เงื่อนไข: ทุกไฟล์ต้องมี "ตัวแปรชุดเดียวกัน" (Set Equality)
    # เช่น File A: {tas, pr}, File B: {tas, pr} -> Time Mode
    # -------------------------------------------------------------------------
    first_file_vars = vars_per_file[0]
    is_same_variables = all(vs == first_file_vars for vs in vars_per_file)
    
    if is_same_variables:
        mode = "time"
        # info อาจจะเก็บ list ของตัวแปรทั้งหมดแทน
        info = {"variables": list(first_file_vars), "files": metas}
        return mode, info, diagnostics

    # -------------------------------------------------------------------------
    # 2. ATTRIBUTE MODE CHECK
    # เงื่อนไข: ตัวแปรในแต่ละไฟล์ต้อง "ไม่ซ้ำกันเลย" (Disjoint Sets)
    # ไม่สนเรื่องเวลา (Time) ว่าตรงกันไหม เพราะ backend attribute mode เราจัดการได้
    # -------------------------------------------------------------------------
    # เช็คว่า intersection ของทุกคู่เป็นว่างเปล่าไหม
    all_vars_flat = [v for m in metas for v in m.get("variables", [])]
    unique_vars_count = len(set(all_vars_flat))
    total_vars_count = len(all_vars_flat)
    
    # ถ้าจำนวนตัวแปร unique เท่ากับจำนวนตัวแปรทั้งหมดรวมกัน แปลว่าไม่มีตัวไหนซ้ำกันเลย
    is_disjoint = unique_vars_count == total_vars_count
    
    if is_disjoint:
        mode = "attribute"
        # สร้าง map ว่าตัวแปรไหนอยู่ไฟล์ไหน
        var_map = {}
        for idx, m in enumerate(metas):
            for v in m.get("variables", []):
                var_map[v] = idx # map variable -> file index
                
        info = {"variables": list(var_map.keys()), "files": metas, "var_map": var_map}
        return mode, info, diagnostics

    # -------------------------------------------------------------------------
    # 3. MIXED MODE (Fallback)
    # กรณี: มีตัวแปรซ้ำกันบ้าง แต่ไม่ทั้งหมด หรือมีความซับซ้อนอื่นๆ
    # -------------------------------------------------------------------------
    mode = "mixed"
    
    # สร้าง info เพื่อบอกว่าตัวแปรไหน อยู่ในไฟล์ index ไหนบ้าง
    var_map_mixed = {}
    for idx, m in enumerate(metas):
        for v in m.get("variables", []):
            var_map_mixed.setdefault(v, []).append(idx)
            
    info = {"groups": var_map_mixed, "files": metas}
    diagnostics.append("Mixed mode detected: Overlapping variables found across files.")
    
    return mode, info, diagnostics

def validate_attribute_mode(metas: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """
    Attribute mode validation:
      - all files must have the SAME time_start/time_end
      - spatial dims (lat/lon sizes) should match
    """
    errors = []
    # time equality
    times = [(m.get("time_start"), m.get("time_end")) for m in metas]
    if len(set(times)) != 1:
        errors.append("Time ranges across files are not identical. Attribute mode requires identical time dimension.")
    # spatial sizes
    lat_sizes = [m["shape"].get("latitude") or m["shape"].get("lat") or None for m in metas]
    lon_sizes = [m["shape"].get("longitude") or m["shape"].get("lon") or None for m in metas]
    if len(set(lat_sizes)) != 1 or len(set(lon_sizes)) != 1:
        errors.append("Spatial dimensions (latitude/longitude sizes) differ across files.")
    return (len(errors) == 0), errors

def validate_time_mode(metas: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """
    Time mode validation:
      - all files should contain exactly the same variable
      - spatial dims and resolution should match
      - units should match (warn if not)
    """
    errors = []
    # same single variable
    vars_ = [list(m.get("variables", [])) for m in metas]
    if not all(len(v) == 1 for v in vars_):
        errors.append("Not all files contain a single variable required for time mode.")
    else:
        var_names = [v[0] for v in vars_]
        if len(set(var_names)) != 1:
            errors.append("Files do not share the same variable (time mode requires same variable across files).")
    # spatial dims & resolution
    res = [m.get("spatial_resolution") for m in metas]
    if len(set(res)) != 1:
        errors.append("Spatial resolution differs across files.")
    # units
    units = [list(m.get("variable_units", {}).values())[0] if m.get("variable_units") else None for m in metas]
    if len(set(units)) != 1:
        errors.append("Variable units differ across files (warning: may need conversion).")
    return (len(errors) == 0), errors

def validate_mixed_mode(metas: List[Dict[str, Any]]) -> Tuple[bool, List[str], Dict[str, List[int]]]:
    """
    Mixed mode: group by variable then validate each group as time-mode.
    Returns groups (variable -> list of indices).
    """
    errors = []
    groups = {}
    for idx, m in enumerate(metas):
        for v in m.get("variables", []):
            groups.setdefault(v, []).append(idx)
    # validate each group
    for v, idxs in groups.items():
        group_meta = [metas[i] for i in idxs]
        ok, errs = validate_time_mode(group_meta)
        if not ok:
            errors.append({v: errs})
    return (len(errors) == 0), errors, groups

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

    # 2. Check Spatial Resolution Consistency (Allow small floating point tolerance)
    # lat_resolutions = [m.get("lat_res") for m in valid_metas if m.get("lat_res") is not None]
    # if lat_resolutions:
    #     # ใช้ numpy.isclose เพื่อเปรียบเทียบ float หรือเช็ค set
    #     # แบบง่าย: เช็คค่า unique โดยปัดเศษทศนิยม
    #     unique_lat_res = set(round(r, 5) for r in lat_resolutions)
    #     if len(unique_lat_res) > 1:
    #          errors.append(f"Inconsistent latitude resolution found: {unique_lat_res}")

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
    
    # 2. Check Mode Validity
    mode, info, diag = detect_mode(metas)
    if mode == "mixed": #
        pass 
    
    return len(errors) == 0, errors