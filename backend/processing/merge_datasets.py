# backend/processing/merge_datasets.py
import os
import xarray as xr
from typing import List, Dict, Any, Tuple
import tempfile
import gc
from processing.upload_validation import filter_dataset_vars, SKIP_VARS, ALLOWED_VARS

CHUNK_CONFIG = {"time": 50, "latitude": 180, "longitude": 360}

def save_dataset_to_netcdf(ds: xr.Dataset, merged_dir: str, prefix: str = "merged") -> str:
    """
    Save dataset to temporary netCDF and return path.
    """
    out_path = os.path.join(merged_dir, f"{prefix}_{next(tempfile._get_candidate_names())}.nc")
    ds.to_netcdf(out_path, format="NETCDF4", compute=True)
    return out_path

def _infer_and_fill_gaps(ds: xr.Dataset) -> xr.Dataset:
    """Shared helper: sort by time, infer freq, fill gaps."""
    if "time" not in ds.coords:
        return ds
    ds = ds.sortby("time")
    freq = None
    try:
        freq = xr.infer_freq(ds.time)
    except Exception:
        freq = None
    try:
        ds = ds.resample(time=freq or "1D").asfreq()
    except Exception as e:
        print(f"Warning: Gap filling failed ({e}), skipping.")
    return ds

def merge_attribute_mode(paths: List[str], merged_dir: str) -> Tuple[bool, Any, List[str]]:
    errors = []
    
    try:
        datasets = []
        for p in paths:
            try:
                ds = xr.open_dataset(p, chunks=CHUNK_CONFIG)
                ds = filter_dataset_vars(ds)
                datasets.append(ds)
            except Exception as sub_e:
                errors.append(f"Failed to open {os.path.basename(p)}: {sub_e}")

        if not datasets:
            raise Exception("No datasets could be opened for attribute merge.")
        
        if errors:
             raise Exception(f"Errors opening files: {errors}")

        merged = xr.merge(datasets, compat="override")
        merged = _infer_and_fill_gaps(merged)

        out_path = save_dataset_to_netcdf(merged, merged_dir, prefix="attribute")
        
        # Explicit cleanup to release file locks
        merged.close()
        for ds in datasets:
            ds.close()
        gc.collect()
        
        # return path only, dataset is closed
        return True, {"dataset": None, "path": out_path}, []

    except Exception as e:
        for ds in datasets:
            try:
                ds.close()
            except Exception:
                pass
        errors.append(f"Attribute Merge Error: {str(e)}")
        return False, None, errors

def merge_time_mode(paths: List[str], merged_dir: str) -> Tuple[bool, Any, List[str]]:
    errors = []
    ds = None
    
    try:
        ds = xr.open_mfdataset(
            paths,
            combine="by_coords",
            parallel=False,          
            chunks=CHUNK_CONFIG,  
            engine="netcdf4"  
        )

        ds = filter_dataset_vars(ds)
        ds = _infer_and_fill_gaps(ds)
            
        ds_to_save = ds.to_dataset() if isinstance(ds, xr.DataArray) else ds
        out_path = save_dataset_to_netcdf(ds_to_save, merged_dir, prefix="time")
        
        ds.close()
        
        return True, {"dataset": None, "path": out_path}, []

    except Exception as e:
        if ds is not None:
            try:
                ds.close()
            except Exception:
                pass
        errors.append(f"Time Merge Error: {str(e)}")
        return False, None, errors

def merge_mixed_mode(paths: List[str], groups: Dict[str, List[int]], metas: List[Dict[str, Any]], temp_paths: List[str], merged_dir: str) -> Tuple[bool, Any, List[str]]:
    errors = []
    var_temp_paths: Dict[str, str] = {}
    open_datasets = []
    
    print("start merge_mixed")
    
    try:
        for var, idxs in groups.items():
            var_paths = [temp_paths[i] for i in idxs]
            
            # This calls merge_time_mode which creates a time_*.nc file and returns its path
            ok, res, errs = merge_time_mode(var_paths, merged_dir)
            
            if not ok:
                errors.append(f"Failed to merge variable '{var}': {errs}")
                break 
            
            var_temp_paths[var] = res["path"]

        if errors:
            raise Exception(f"Errors occurred during variable grouping: {errors}")

        print("start merge_mixed 2")
        
        # Combine all variables using the intermediate time_*.nc files
        ds_list = []
        for var, vpath in var_temp_paths.items():
            ds_v = xr.open_dataset(vpath, chunks=CHUNK_CONFIG)
            open_datasets.append(ds_v)
            ds_list.append(ds_v)
        
        merged = xr.merge(ds_list, compat="override")
        merged = _infer_and_fill_gaps(merged)
             
        out_path = save_dataset_to_netcdf(merged, merged_dir, prefix="mixed")

        print("closing resources...")
        merged.close()

        for ds in open_datasets:
            try:
                ds.close()
            except Exception:
                pass

        for vpath in var_temp_paths.values():
            try:
                os.remove(vpath)
            except OSError as e:
                print(f"Warning: Failed to delete intermediate file {vpath}: {e}")

        gc.collect()

        return True, {"dataset": None, "path": out_path}, []

    except Exception as e:
        for ds in open_datasets:
            try:
                ds.close()
            except Exception:
                pass
        for vpath in var_temp_paths.values():
            try:
                os.remove(vpath)
            except OSError:
                pass
        
        if not errors:
            errors.append(str(e))
             
        return False, None, errors