# backend/processing/merge_datasets.py
import os
import xarray as xr
from typing import List, Dict, Any, Tuple
import tempfile
from processing.upload_validation import filter_dataset_vars, SKIP_VARS, ALLOWED_VARS

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

PREVIEW_MERGED_DIR = "uploads/merged"  # or configurable
os.makedirs(PREVIEW_MERGED_DIR, exist_ok=True)

def save_dataset_to_netcdf(ds: xr.Dataset, prefix: str = "merged") -> str:
    """
    Save dataset to temporary netCDF (or in PREVIEW_MERGED_DIR) and return path.
    """
    out_path = os.path.join(PREVIEW_MERGED_DIR, f"{prefix}_{next(tempfile._get_candidate_names())}.nc")
    # choose NETCDF4 format
    ds.to_netcdf(out_path, format="NETCDF4")
    return out_path

# def merge_attribute_mode(paths: List[str]) -> Tuple[bool, Any, List[str]]:
#     """
#     Merge files that contain different variables but share same time/spatial dims.
#     We'll open each file and merge.
#     """
#     errors = []
#     datasets = []
#     merged = None
#     try:
#         for p in paths:
#             try:
#                 ds = xr.open_dataset(p)
#                 # Drop unwanted vars
#                 vars_to_drop = [v for v in ds.data_vars if v in SKIP_VARS]
#                 if vars_to_drop:
#                     ds = ds.drop_vars(vars_to_drop) 
#                 datasets.append(ds) # like this [ds_tmax, ds_tmin, ds_pr]
#             except Exception as sub_e:
#                 errors.append(f"Failed to open {os.path.basename(p)}: {sub_e}") 

#         if not datasets:
#             raise Exception("No datasets could be opened for attribute merge.")
        
#         # merge datasets (if variables do not overlap)
#         merged = xr.merge(datasets, compat="override")  # override if attrs differ
#         out_path = save_dataset_to_netcdf(merged, prefix="attribute")
#         # close original opened datasets
#         for ds in datasets:
#             ds.close()

#         # Close merged object in memory
#         merged.close()
        
#         return True, {"dataset": merged, "path": out_path}, errors
#     except Exception as e:
#         for ds in datasets:
#             try: ds.close()
#             except: pass
        
#         if merged:
#             try: merged.close()
#             except: pass
            
#         errors.append(f"Attribute Merge Error: {str(e)}")

# def merge_time_mode(paths: List[str]) -> Tuple[bool, Any, List[str]]:
#     """
#     Concat along time for files containing same variable.
#     Use xarray.open_mfdataset with combine='by_coords' where possible.
#     """
#     errors = []
#     ds = None
#     try:
#         # use combine='by_coords' so files can be concatenated along time if coords align
#         ds = xr.open_mfdataset(paths, combine="by_coords", parallel=False) # open_mfdataset can open many file in same time but open_dataset is not //, preprocess=None

#         vars_to_drop = [v for v in ds.data_vars if v in SKIP_VARS]
#         if vars_to_drop:
#             ds = ds.drop_vars(vars_to_drop)


#         # ensure time sorted
#         if "time" in ds.coords:
#             ds = ds.sortby("time")
#         # check : if Dataset >> save | if DataArray(may be result from open_mfdataset) >> change to Dataset >> save
#         # out_path = save_dataset_to_netcdf(ds.to_dataset()) if isinstance(ds, xr.DataArray) else save_dataset_to_netcdf(ds)
#         ds_to_save = ds.to_dataset() if isinstance(ds, xr.DataArray) else ds
        
#         out_path = save_dataset_to_netcdf(ds_to_save, prefix="time")
#         return True, {"dataset": ds, "path": out_path}, errors
#     except Exception as e:
#         # [FIX] Safe Close
#         if ds:
#             try: ds.close()
#             except: pass
            
#         errors.append(f"Time Merge Error: {str(e)}")
#         return False, None, errors

# def merge_mixed_mode(paths: List[str], groups: Dict[str, List[int]], metas: List[Dict[str, Any]], temp_paths: List[str]) -> Tuple[bool, Any, List[str]]:
#     """
#     groups: variable -> list of file indices (indices into metas/temp_paths)
#     temp_paths: list of saved file paths in same order as metas
#     Process:
#       - for each variable: gather corresponding paths -> concat (time)
#       - collect per-variable datasets then merge
#     """
#     errors = []
#     per_var_ds = {}
#     merged = None
#     print("start merge_mixed")
#     try:
#         # group
#         # {
#         #   "tmax": [0, 3, 5],   # file index 0,3,5 belongs to tmax 
#         #   "tmin": [1, 2],      # file index 1,2 belongs to tmin
#         #   "pr": [4, 6, 7]      # file index 4,6,7 belongs to pr
#         # }
#         # var = “tmax”, “tmin”, “pr”
#         # idxs = [0,3,5]  (index varibale file)

#         for var, idxs in groups.items():
#             var_paths = [temp_paths[i] for i in idxs] # change index to path
#             ok, res, errs = merge_time_mode(var_paths)
            
#             if not ok:
#                 errors.append(f"Failed to merge variable '{var}': {errs}")
#             else:
#                 # res["dataset"] might be Dataset or DataArray
#                 ds_var = res["dataset"]

#                 vars_to_drop = [v for v in ds.data_vars if v in SKIP_VARS]
#                 if vars_to_drop:
#                     ds_var = ds_var.drop_vars(vars_to_drop)

#                 per_var_ds[var] = ds_var

#         if errors:
#             raise Exception(f"Errors occurred during variable grouping: {errors}")
#         # if errors:
#         #     return False, None, errors
#         # now merge variables into single dataset
#         # convert DataArrays to Datasets if needed
#         print("start merge_mixed 2")
#         ds_list = []
#         for v, ds in per_var_ds.items():
#             if isinstance(ds, xr.DataArray):
#                 ds_list.append(ds.to_dataset(name=v))
#             else:
#                 ds_list.append(ds)

#         merged = xr.merge(ds_list, compat="override")
#         out_path = save_dataset_to_netcdf(merged, prefix="mixed")

#         print("close")
#         for ds in per_var_ds.values():
#             ds.close()
        
#         if merged:
#             merged.close()

#         return True, {"dataset": merged, "path": out_path}, errors
#     except Exception as e:
#         # [FIX] Cleanup Phase
#         # close subset of dataset, it's not close
#         for ds in per_var_ds.values():
#             try: ds.close()
#             except: pass
            
#         # close merged result (if already create)
#         if merged:
#             try: merged.close()
#             except: pass
            
#         errors.append(str(e))
#         return False, None, errors



def merge_attribute_mode(paths: List[str]) -> Tuple[bool, Any, List[str]]:
    errors = []
    datasets = [] 
    merged = None 
    
    try:
        for p in paths:
            try:
                ds = xr.open_dataset(p)
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

        if "time" in merged.coords:
            merged = merged.sortby("time")
            
            # ตัวแปรเก็บความถี่
            freq = None
            
            try:
                # พยายามเดาความถี่
                freq = xr.infer_freq(merged.time)
            except ValueError:
                # ถ้าข้อมูลน้อยเกินไป (เช่น < 3 วัน) infer_freq จะ error
                # เราจะถือว่าหาไม่เจอ (None) แล้วไปเข้า case else ด้านล่าง
                freq = None
            except Exception:
                freq = None

            try:
                if freq:
                    # ถ้าเดาได้ ให้ใช้ความถี่นั้น
                    merged = merged.resample(time=freq).asfreq()
                else:
                    # [สำคัญ] ถ้าเดาไม่ได้ (หรือ Error) ให้บังคับเป็นรายวัน '1D'
                    print("Warning: Could not infer freq. Defaulting to '1D'.")
                    merged = merged.resample(time='1D').asfreq()
            except Exception as e:
                print(f"Gap filling completely failed: {e}")
                pass

        out_path = save_dataset_to_netcdf(merged, prefix="attribute")
        
        # Cleanup
        for ds in datasets:
            ds.close()
        merged.close()
        
        return True, {"dataset": None, "path": out_path}, []

    except Exception as e:
        # Safe Cleanup
        for ds in datasets:
            try: ds.close()
            except: pass
        
        if merged:
            try: merged.close()
            except: pass
            
        errors.append(f"Attribute Merge Error: {str(e)}")
        return False, None, errors

def merge_time_mode(paths: List[str]) -> Tuple[bool, Any, List[str]]:
    errors = []
    ds = None 
    
    try:
        # use chunks to protect Memory full
        ds = xr.open_mfdataset(paths, combine="by_coords", parallel=False)

        # vars_to_drop = [v for v in ds.data_vars if v in SKIP_VARS]
        # if vars_to_drop:
        #     ds = ds.drop_vars(vars_to_drop)
        ds = filter_dataset_vars(ds)

        if "time" in ds.coords:
            ds = ds.sortby("time")

            freq = None

            try:
                # พยายามเดาความถี่ของข้อมูล (เช่น 'D', 'M', 'Y')
                freq = xr.infer_freq(ds.time)
            except ValueError:
                freq = None
            except Exception:
                freq = None

            try:    
                if freq:
                    ds = ds.resample(time=freq).asfreq()
                else:
                    print("Warning: Could not infer frequency. Defaulting to Daily ('1D') gap filling.")
                    ds = ds.resample(time='1D').asfreq()
                    
            except Exception as sort_err:
                # ถ้า Resample พังจริงๆ ให้ข้ามไป (ดีกว่าโปรแกรมล่ม)
                print(f"Warning: Gap filling failed: {sort_err}")
                pass
            
        ds_to_save = ds.to_dataset() if isinstance(ds, xr.DataArray) else ds
        out_path = save_dataset_to_netcdf(ds_to_save, prefix="time")
        
        return True, {"dataset": ds, "path": out_path}, []

    except Exception as e:
        if ds:
            try: ds.close()
            except: pass
            
        errors.append(f"Time Merge Error: {str(e)}")
        return False, None, errors

def merge_mixed_mode(paths: List[str], groups: Dict[str, List[int]], metas: List[Dict[str, Any]], temp_paths: List[str]) -> Tuple[bool, Any, List[str]]:
    errors = []
    per_var_ds = {} 
    merged = None  
    
    print("start merge_mixed")
    
    try:
        for var, idxs in groups.items():
            # pull path of group file
            var_paths = [temp_paths[i] for i in idxs]
            
            # call merge_time_mode
            ok, res, errs = merge_time_mode(var_paths)
            
            if not ok:
                errors.append(f"Failed to merge variable '{var}': {errs}")
                break 
            else:
                ds_var = res["dataset"]
                
                # vars_to_drop = [v for v in ds_var.data_vars if v in SKIP_VARS]
                # if vars_to_drop:
                #     ds_var = ds_var.drop_vars(vars_to_drop)
                ds_var = filter_dataset_vars(ds_var)
                
                per_var_ds[var] = ds_var

        if errors:
            raise Exception(f"Errors occurred during variable grouping: {errors}")

        print("start merge_mixed 2")
        
        # Combine all variables
        ds_list = []
        for v, ds in per_var_ds.items():
            if isinstance(ds, xr.DataArray):
                ds_list.append(ds.to_dataset(name=v))
            else:
                ds_list.append(ds)
        
        merged = xr.merge(ds_list, compat="override")

        if "time" in merged.coords:
             merged = merged.sortby("time")
             
             # ตัวแปรเก็บความถี่
             freq = None
             try:
                 # พยายามเดาความถี่ (ถ้า < 3 วัน จะ Error)
                 freq = xr.infer_freq(merged.time)
             except Exception:
                 freq = None

             try:
                 if freq:
                     merged = merged.resample(time=freq).asfreq()
                 else:
                     # [สำคัญ] ถ้าเดาไม่ได้ หรือ Error ให้บังคับเป็นรายวัน '1D'
                     # เพื่อแก้ปัญหา Need at least 3 dates และถมช่องว่างให้ได้
                     print("Warning: Mixed mode defaulting to '1D' gap filling.")
                     merged = merged.resample(time='1D').asfreq()
             except Exception as e:
                 print(f"Global gap filling completely failed: {e}")
                 pass
             
        out_path = save_dataset_to_netcdf(merged, prefix="mixed")

        print("closing resources...")
        
        # close dataset sebset
        for ds in per_var_ds.values():
            ds.close()
        
        if merged:
            merged.close()

        return True, {"dataset": None, "path": out_path}, []

    except Exception as e:
        for ds in per_var_ds.values():
            try: ds.close()
            except: pass
            
        if merged:
            try: merged.close()
            except: pass
            
        # if have error in merge_time_mode it will return error list back
        # just append it
        if not errors: # if don't have error in list will put exception in
             errors.append(str(e))
             
        return False, None, errors