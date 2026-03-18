import os
import shutil
import xarray as xr
import gc  
import time

from processing.preprocessing import normalize_var_name, ensure_pr_unit, ensure_temperature_unit
from processing.upload_validation import inspect_file, validate_compatibility, SKIP_VARS
from services.dataset_paths import get_raw_path, get_processed_path

COORD_ALIASES = {
    "latitude": ["lat", "latitude", "nav_lat", "y", "rlat"],
    "longitude": ["lon", "longitude", "nav_lon", "x", "rlon"],
    "time": ["time", "Times", "datetime", "date", "valid_time"],
}

def standardize_coords(ds):
    rename_dict = {}
    for standard_name, aliases in COORD_ALIASES.items():
        # if dataset already have standard_name, it will not do anything 
        if standard_name in ds.coords or standard_name in ds.dims:
            continue
            
        # if don't have, will find in alias 
        for alias in aliases:
            if alias in ds.coords or alias in ds.dims:
                rename_dict[alias] = standard_name
                break
    
    if rename_dict:
        print(f"Renaming coords: {rename_dict}")
        ds = ds.rename(rename_dict)
    
    return ds

def get_smart_slice(ds, coord_name, min_val, max_val):
    """
    ตรวจสอบว่า data เรียงจาก น้อย->มาก หรือ มาก->น้อย
    แล้ว return slice object ที่ถูกต้อง
    """
    if coord_name not in ds:
        return slice(None) 

    data = ds[coord_name]
    
    # Check direction : Look at the first and last values.
    # if first < last = Ascending -> slice(min, max)
    # if first > last = Descending -> slice(max, min)
    
    if data[0] < data[-1]:
        return slice(min_val, max_val)
    else:
        return slice(max_val, min_val)

def core_process_file(raw_path, save_path, scope):
    try:
        # use chunks={} for open only Metadata (fast and less eat RAM)
        # ds = xr.open_dataset(raw_path, chunks={})
        with xr.open_dataset(raw_path, chunks={}) as ds:
            # Standardize Coords (solve latitude/longitude name)
            ds = standardize_coords(ds)

            # Check Time & Scope Intersection
            if 'time' not in ds.dims:
                ds.close()
                return False

            file_years = ds.time.dt.year
            min_year = int(file_years.min())
            max_year = int(file_years.max())

            if not (min_year <= scope.endYear and max_year >= scope.startYear):
                ds.close()
                return False

            # Rename
            rename_dict = {}
            for var_name in ds.data_vars:
                std_name = normalize_var_name(var_name)
                if std_name != var_name:
                    rename_dict[var_name] = std_name
                    if "long_name" not in ds[var_name].attrs:
                        ds[var_name].attrs["long_name"] = var_name 
            
            if rename_dict:
                ds = ds.rename(rename_dict)

            # Clip
            lat_slice = get_smart_slice(ds, 'latitude', scope.minLat, scope.maxLat)
            lon_slice = get_smart_slice(ds, 'longitude', scope.minLon, scope.maxLon)

            ds_subset = ds.sel(
                time=slice(str(scope.startYear), str(scope.endYear)),
                latitude=lat_slice,
                longitude=lon_slice
            )
            
            if ds_subset.time.size == 0 or ds_subset.latitude.size == 0 or ds_subset.longitude.size == 0:
                ds.close()
                return False

            # 4. Load & Unit Conversion
            ds_subset = ds_subset.load() 
        
        for var in ds_subset.data_vars:
            if var == "pr":
                ds_subset[var] = ensure_pr_unit(ds_subset[var])
            elif var in ["tmax", "tmin", "tas"]:
                ds_subset[var] = ensure_temperature_unit(ds_subset[var])

        # 5. Cleanup & Save
        vars_to_drop = [v for v in ds_subset.variables if v in SKIP_VARS or 'bnds' in v or 'bounds' in v]
        if vars_to_drop:
            ds_subset = ds_subset.drop_vars(vars_to_drop)

        ds_subset.encoding = {} 
        for var in ds_subset.variables:
            ds_subset[var].encoding = {}
            if "_FillValue" in ds_subset[var].attrs:
                del ds_subset[var].attrs["_FillValue"]

        ds_subset.to_netcdf(save_path, format='NETCDF4')
        ds.close()
        ds_subset.close()
        return True

    except Exception as e:
        print(f"Error processing {raw_path}: {e}")
        return False

def process_and_clip(user_id: str, slot_id: int, dataset_name: str, scope):
    raw_dir = get_raw_path(user_id, slot_id)
    proc_dir = get_processed_path(user_id, dataset_name)

    if os.path.exists(proc_dir):
        # force close all files in Python Memory
        gc.collect() 
        
        # delete folder each file (soft delete)
        for filename in os.listdir(proc_dir):
            file_path = os.path.join(proc_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path) 
            except Exception as e:
                print(f"Warning: Could not remove {filename}: {e}")
        
        # try delete folder (if can't will skip and Overwrite )
        try:
            shutil.rmtree(proc_dir)
        except PermissionError:
            print("Warning: Could not delete folder (locked), will try to overwrite files.")
            # wait Windows slow
            time.sleep(0.5)
    os.makedirs(proc_dir, exist_ok=True)

    files = sorted([f for f in os.listdir(raw_dir) if f.endswith('.nc')])
    
    # Validation 
    # check all file in folder raw before Clip
    metas = [inspect_file(os.path.join(raw_dir, f)) for f in files]
    is_valid, errors = validate_compatibility(metas)
    if not is_valid:
         # send Error back for User know and delete error file
        raise Exception(f"Validation Failed: {'; '.join(errors)}")
    
    processed_count = 0
    for filename in files:
        raw_path = os.path.join(raw_dir, filename)
        save_path = os.path.join(proc_dir, filename)

        if os.path.exists(save_path):
            try:
                os.remove(save_path)
            except OSError:
                pass
        
        # Core Function
        success = core_process_file(raw_path, save_path, scope)
        if success:
            processed_count += 1
            print(f"Processed: {filename}")

    return processed_count