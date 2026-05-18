# backend/processing/merge_datasets.py
import os
import xarray as xr
from typing import List, Dict, Any, Tuple
import tempfile
import gc
from processing.upload_validation import filter_dataset_vars, SKIP_VARS, ALLOWED_VARS

# Match the same chunk config used in dataset_clip.py
CHUNK_CONFIG = {"time": 50, "latitude": 180, "longitude": 360}

"""
Functions to merge/concat datasets depending on detected mode.
- for attribute mode: merge datasets (different variables) that share same spatial/time dims
- for time mode: concat files (same var) along time (use open_mfdataset)
- for mixed mode: for each variable group concat times then merge variables

Each function returns:
  - success flag (bool)
  - result: either xr.Dataset or path to saved merged netcdf
  - diagnostics/errors list
"""

# PREVIEW_MERGED_DIR = "uploads/merged"  # or configurable
# os.makedirs(PREVIEW_MERGED_DIR, exist_ok=True)

def save_dataset_to_netcdf(ds: xr.Dataset, merged_dir: str, prefix: str = "merged") -> str:
    """
    Save dataset to temporary netCDF and return path.
    """
    out_path = os.path.join(merged_dir, f"{prefix}_{next(tempfile._get_candidate_names())}.nc")
    # choose NETCDF4 format
    # ds.to_netcdf(out_path, format="NETCDF4")
    # compute=True streams dask chunks one at a time — constant RAM
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
    # datasets = [] 
    # merged = None 
    
    try:
        # Open with chunks so each file is a lazy Dask graph, not in RAM
        datasets = []
        for p in paths:
            try:
                ds = xr.open_dataset(p, chunks=CHUNK_CONFIG)
                # ds = xr.open_dataset(p)
                # Drop unwanted vars
                # vars_to_drop = [v for v in ds.data_vars if v in SKIP_VARS]
                # if vars_to_drop:
                #     ds = ds.drop_vars(vars_to_drop)
                ds = filter_dataset_vars(ds)
                datasets.append(ds)
            except Exception as sub_e:
                errors.append(f"Failed to open {os.path.basename(p)}: {sub_e}")
                # if don't have file pass will leave function

        if not datasets:
            raise Exception("No datasets could be opened for attribute merge.")
        
        if errors: # if some file can't open will stop
             raise Exception(f"Errors opening files: {errors}")

        # merge datasets
        merged = xr.merge(datasets, compat="override")
        merged = _infer_and_fill_gaps(merged)

        # if "time" in merged.coords:
        #     merged = merged.sortby("time")
            
        #     # ตัวแปรเก็บความถี่
        #     freq = None
            
        #     try:
        #         # try guess frequency (if < 3 days will Error)
        #         freq = xr.infer_freq(merged.time)
        #     except ValueError:

        #         freq = None
        #     except Exception:
        #         freq = None

        #     try:
        #         if freq:
        #             merged = merged.resample(time=freq).asfreq()
        #         else:
        #             print("Warning: Could not infer freq. Defaulting to '1D'.")
        #             merged = merged.resample(time='1D').asfreq()
        #     except Exception as e:
        #         print(f"Gap filling completely failed: {e}")
        #         pass

        out_path = save_dataset_to_netcdf(merged, merged_dir, prefix="attribute")
        
        # Explicit cleanup to release file locks
        merged.close()
        for ds in datasets:
            ds.close()
        gc.collect()
        
        # return path only, dataset is closed
        return True, {"dataset": None, "path": out_path}, []

    except Exception as e:
        # Safe Cleanup
        for ds in datasets:
            try:
                ds.close()
            except Exception:
                pass
        
        # if merged:
        #     try: merged.close()
        #     except: pass
            
        errors.append(f"Attribute Merge Error: {str(e)}")
        return False, None, errors

def merge_time_mode(paths: List[str], merged_dir: str) -> Tuple[bool, Any, List[str]]:
    errors = []
    ds = None
    
    try:
        # use chunks to protect Memory full
        # ds = xr.open_mfdataset(paths, combine="by_coords", parallel=False)
        # FIX: Add chunks= so open_mfdataset stays lazy
        # parallel=True is safe with Dask and faster for many files
        ds = xr.open_mfdataset(
            paths,
            combine="by_coords",
            parallel=False,          
            chunks=CHUNK_CONFIG,    # keeps data as Dask arrays
            engine="netcdf4" 
        )

        # vars_to_drop = [v for v in ds.data_vars if v in SKIP_VARS]
        # if vars_to_drop:
        #     ds = ds.drop_vars(vars_to_drop)
        ds = filter_dataset_vars(ds)
        ds = _infer_and_fill_gaps(ds)

        # if "time" in ds.coords:
        #     ds = ds.sortby("time")

        #     freq = None

        #     try:
        #         # try guess frequency (if < 3 days will Error)
        #         freq = xr.infer_freq(ds.time)
        #     except ValueError:
        #         freq = None
        #     except Exception:
        #         freq = None

        #     try:    
        #         if freq:
        #             ds = ds.resample(time=freq).asfreq()
        #         else:
        #             print("Warning: Could not infer frequency. Defaulting to Daily ('1D') gap filling.")
        #             ds = ds.resample(time='1D').asfreq()
                    
        #     except Exception as sort_err:
        #         print(f"Warning: Gap filling failed: {sort_err}")
        #         pass
            
        ds_to_save = ds.to_dataset() if isinstance(ds, xr.DataArray) else ds
        out_path = save_dataset_to_netcdf(ds_to_save, merged_dir, prefix="time")
        
        ds.close()
        # Do not return the dataset object since it is closed. Just return the path.
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
    # per_var_ds = {} 
    # Don't hold all variable datasets in memory simultaneously.
    # Instead save each variable's intermediate file, then merge from disk.
    var_temp_paths: Dict[str, str] = {}
    open_datasets = []
    # merged = None  
    
    print("start merge_mixed")
    
    try:
        for var, idxs in groups.items():
            # pull path of group file
            var_paths = [temp_paths[i] for i in idxs]
            
            # This calls merge_time_mode which creates a time_*.nc file and returns its path
            ok, res, errs = merge_time_mode(var_paths, merged_dir)
            
            if not ok:
                errors.append(f"Failed to merge variable '{var}': {errs}")
                break 
            # else:

            # Save intermediate per-variable file, then close the dataset
            # Peak RAM per iteration = 1 variable's worth of chunks
            
            # ds_var = res["dataset"]
                
            # vars_to_drop = [v for v in ds_var.data_vars if v in SKIP_VARS]
            # if vars_to_drop:
            #     ds_var = ds_var.drop_vars(vars_to_drop)
            # ds_var = filter_dataset_vars(ds_var)
            # per_var_ds[var] = ds_var
            # var_temp_path = save_dataset_to_netcdf(
                # ds_var, merged_dir, prefix=f"var_{var}"
            # )
            # var_temp_paths[var] = var_temp_path
            # ds_var.close()  # Release memory before opening next variable
            # gc.collect()

            var_temp_paths[var] = res["path"]

        if errors:
            raise Exception(f"Errors occurred during variable grouping: {errors}")

        print("start merge_mixed 2")
        
        # Combine all variables
        # Open all saved per-variable files lazily and merge
        ds_list = []
        # for v, ds in per_var_ds.items():
        #     if isinstance(ds, xr.DataArray):
        #         ds_list.append(ds.to_dataset(name=v))
        #     else:
        #         ds_list.append(ds)
        for var, vpath in var_temp_paths.items():
            ds_v = xr.open_dataset(vpath, chunks=CHUNK_CONFIG)
            open_datasets.append(ds_v)
            ds_list.append(ds_v)
        
        merged = xr.merge(ds_list, compat="override")
        merged = _infer_and_fill_gaps(merged)

        # if "time" in merged.coords:
        #      merged = merged.sortby("time")
             
        #      freq = None
        #      try:
        #          # try guess frequency (if < 3 days will Error)
        #          freq = xr.infer_freq(merged.time)
        #      except Exception:
        #          freq = None

        #      try:
        #          if freq:
        #              merged = merged.resample(time=freq).asfreq()
        #          else:
        #              print("Warning: Mixed mode defaulting to '1D' gap filling.")
        #              merged = merged.resample(time='1D').asfreq()
        #      except Exception as e:
        #          print(f"Global gap filling completely failed: {e}")
        #          pass
             
        out_path = save_dataset_to_netcdf(merged, merged_dir, prefix="mixed")

        print("closing resources...")
        merged.close()
        
        # close dataset sebset
        # for ds in per_var_ds.values():
        #     ds.close()
        
        # if merged:
        #     merged.close()

        for ds in open_datasets:
            try:
                ds.close()
            except Exception:
                pass

        # Clean up intermediate per-variable temp files
        for vpath in var_temp_paths.values():
            try:
                os.remove(vpath)
            except OSError as e:
                print(f"Warning: Failed to delete intermediate file {vpath}: {e}")

        gc.collect()

        return True, {"dataset": None, "path": out_path}, []

    except Exception as e:
        # for ds in per_var_ds.values():
        #     try: ds.close()
        #     except: pass
            
        # if merged:
        #     try: merged.close()
        #     except: pass
            
        # # if have error in merge_time_mode it will return error list back
        # # just append it
        # if not errors: # if don't have error in list will put exception in
        #      errors.append(str(e))
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
    
# # backend/processing/merge_datasets.py
# import os
# import xarray as xr
# from typing import List, Dict, Any, Tuple
# import tempfile
# from processing.upload_validation import filter_dataset_vars, SKIP_VARS, ALLOWED_VARS

# """
# Functions to merge/concat datasets depending on detected mode.
# - for attribute mode: merge datasets (different variables) that share same spatial/time dims
# - for time mode: concat files (same var) along time (use open_mfdataset)
# - for mixed mode: for each variable group concat times then merge variables

# Each function returns:
#   - success flag (bool)
#   - result: either xr.Dataset or path to saved merged netcdf
#   - diagnostics/errors list
# """

# # PREVIEW_MERGED_DIR = "uploads/merged"  # or configurable
# # os.makedirs(PREVIEW_MERGED_DIR, exist_ok=True)

# def save_dataset_to_netcdf(ds: xr.Dataset, merged_dir: str, prefix: str = "merged") -> str:
#     """
#     Save dataset to temporary netCDF (or in PREVIEW_MERGED_DIR) and return path.
#     """
#     out_path = os.path.join(merged_dir, f"{prefix}_{next(tempfile._get_candidate_names())}.nc")
#     # choose NETCDF4 format
#     ds.to_netcdf(out_path, format="NETCDF4")
#     return out_path

# def merge_attribute_mode(paths: List[str], merged_dir: str) -> Tuple[bool, Any, List[str]]:
#     errors = []
#     datasets = [] 
#     merged = None 
    
#     try:
#         for p in paths:
#             try:
#                 ds = xr.open_dataset(p)
#                 # Drop unwanted vars
#                 # vars_to_drop = [v for v in ds.data_vars if v in SKIP_VARS]
#                 # if vars_to_drop:
#                 #     ds = ds.drop_vars(vars_to_drop)
#                 ds = filter_dataset_vars(ds)

#                 datasets.append(ds)
#             except Exception as sub_e:
#                 errors.append(f"Failed to open {os.path.basename(p)}: {sub_e}")
#                 # if don't have file pass will leave function

#         if not datasets:
#             raise Exception("No datasets could be opened for attribute merge.")
        
#         if errors: # if some file can't open will stop
#              raise Exception(f"Errors opening files: {errors}")

#         # merge datasets
#         merged = xr.merge(datasets, compat="override")

#         if "time" in merged.coords:
#             merged = merged.sortby("time")
            
#             # ตัวแปรเก็บความถี่
#             freq = None
            
#             try:
#                 # try guess frequency (if < 3 days will Error)
#                 freq = xr.infer_freq(merged.time)
#             except ValueError:

#                 freq = None
#             except Exception:
#                 freq = None

#             try:
#                 if freq:
#                     merged = merged.resample(time=freq).asfreq()
#                 else:
#                     print("Warning: Could not infer freq. Defaulting to '1D'.")
#                     merged = merged.resample(time='1D').asfreq()
#             except Exception as e:
#                 print(f"Gap filling completely failed: {e}")
#                 pass

#         out_path = save_dataset_to_netcdf(merged, merged_dir, prefix="attribute")
        
#         # Cleanup
#         for ds in datasets:
#             ds.close()
#         merged.close()
        
#         return True, {"dataset": None, "path": out_path}, []

#     except Exception as e:
#         # Safe Cleanup
#         for ds in datasets:
#             try: ds.close()
#             except: pass
        
#         if merged:
#             try: merged.close()
#             except: pass
            
#         errors.append(f"Attribute Merge Error: {str(e)}")
#         return False, None, errors

# def merge_time_mode(paths: List[str], merged_dir: str) -> Tuple[bool, Any, List[str]]:
#     errors = []
#     ds = None 
    
#     try:
#         # use chunks to protect Memory full
#         ds = xr.open_mfdataset(paths, combine="by_coords", parallel=False)

#         # vars_to_drop = [v for v in ds.data_vars if v in SKIP_VARS]
#         # if vars_to_drop:
#         #     ds = ds.drop_vars(vars_to_drop)
#         ds = filter_dataset_vars(ds)

#         if "time" in ds.coords:
#             ds = ds.sortby("time")

#             freq = None

#             try:
#                 # try guess frequency (if < 3 days will Error)
#                 freq = xr.infer_freq(ds.time)
#             except ValueError:
#                 freq = None
#             except Exception:
#                 freq = None

#             try:    
#                 if freq:
#                     ds = ds.resample(time=freq).asfreq()
#                 else:
#                     print("Warning: Could not infer frequency. Defaulting to Daily ('1D') gap filling.")
#                     ds = ds.resample(time='1D').asfreq()
                    
#             except Exception as sort_err:
#                 print(f"Warning: Gap filling failed: {sort_err}")
#                 pass
            
#         ds_to_save = ds.to_dataset() if isinstance(ds, xr.DataArray) else ds
#         out_path = save_dataset_to_netcdf(ds_to_save, merged_dir, prefix="time")
        
#         return True, {"dataset": ds, "path": out_path}, []

#     except Exception as e:
#         if ds:
#             try: ds.close()
#             except: pass
            
#         errors.append(f"Time Merge Error: {str(e)}")
#         return False, None, errors

# def merge_mixed_mode(paths: List[str], groups: Dict[str, List[int]], metas: List[Dict[str, Any]], temp_paths: List[str], merged_dir: str) -> Tuple[bool, Any, List[str]]:
#     errors = []
#     per_var_ds = {} 
#     merged = None  
    
#     print("start merge_mixed")
    
#     try:
#         for var, idxs in groups.items():
#             # pull path of group file
#             var_paths = [temp_paths[i] for i in idxs]
            
#             # call merge_time_mode
#             ok, res, errs = merge_time_mode(var_paths, merged_dir)
            
#             if not ok:
#                 errors.append(f"Failed to merge variable '{var}': {errs}")
#                 break 
#             else:
#                 ds_var = res["dataset"]
                
#                 # vars_to_drop = [v for v in ds_var.data_vars if v in SKIP_VARS]
#                 # if vars_to_drop:
#                 #     ds_var = ds_var.drop_vars(vars_to_drop)
#                 ds_var = filter_dataset_vars(ds_var)
                
#                 per_var_ds[var] = ds_var

#         if errors:
#             raise Exception(f"Errors occurred during variable grouping: {errors}")

#         print("start merge_mixed 2")
        
#         # Combine all variables
#         ds_list = []
#         for v, ds in per_var_ds.items():
#             if isinstance(ds, xr.DataArray):
#                 ds_list.append(ds.to_dataset(name=v))
#             else:
#                 ds_list.append(ds)
        
#         merged = xr.merge(ds_list, compat="override")

#         if "time" in merged.coords:
#              merged = merged.sortby("time")
             
#              freq = None
#              try:
#                  # try guess frequency (if < 3 days will Error)
#                  freq = xr.infer_freq(merged.time)
#              except Exception:
#                  freq = None

#              try:
#                  if freq:
#                      merged = merged.resample(time=freq).asfreq()
#                  else:
#                      print("Warning: Mixed mode defaulting to '1D' gap filling.")
#                      merged = merged.resample(time='1D').asfreq()
#              except Exception as e:
#                  print(f"Global gap filling completely failed: {e}")
#                  pass
             
#         out_path = save_dataset_to_netcdf(merged, merged_dir, prefix="mixed")

#         print("closing resources...")
        
#         # close dataset sebset
#         for ds in per_var_ds.values():
#             ds.close()
        
#         if merged:
#             merged.close()

#         return True, {"dataset": None, "path": out_path}, []

#     except Exception as e:
#         for ds in per_var_ds.values():
#             try: ds.close()
#             except: pass
            
#         if merged:
#             try: merged.close()
#             except: pass
            
#         # if have error in merge_time_mode it will return error list back
#         # just append it
#         if not errors: # if don't have error in list will put exception in
#              errors.append(str(e))
             
#         return False, None, errors