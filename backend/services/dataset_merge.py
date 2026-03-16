import os
import shutil
import xarray as xr
import uuid # use create temp folder not same
import glob

from processing.upload_validation import inspect_file, detect_mode
from processing.merge_datasets import merge_time_mode, merge_attribute_mode, merge_mixed_mode
from services.dataset_paths import get_processed_path, get_dataset_output_dir


def prepare_merged_file_for_calculation(dataset_name):
    proc_dir = get_processed_path(dataset_name)
    files = [os.path.join(proc_dir, f) for f in os.listdir(proc_dir) if f.endswith('.nc')]
    
    if not files:
        raise Exception("No files to calculate")

    # Pre-cleanup for merged directory
    merged_dir = os.path.join("uploads", "merged") # Adjust this path to your UPLOAD_BASE
    if os.path.exists(merged_dir):
        # Delete all .nc files in the merged temporary folder
        for old_file in glob.glob(os.path.join(merged_dir, "*.nc")):
            try:
                os.remove(old_file)
            except Exception as e:
                print(f"Warning: Could not remove old merged file {old_file}: {e}")
    else:
        os.makedirs(merged_dir, exist_ok=True)
    
    # Detect Mode again from Process file (optional ? really ?)
    metas = [inspect_file(f) for f in files]
    mode, info, _ = detect_mode(metas)
    print(f"Detected Merge Mode: {mode}")

    success = False
    result = None
    err = []

    if mode == "time":
        success, result, err = merge_time_mode(files)
    elif mode == "attribute":
        success, result, err = merge_attribute_mode(files)
    elif mode == "mixed":
        # Mixed mode send temp_paths or group correct file
        success, result, err = merge_mixed_mode(files, info['groups'], metas, files)
    else:
        # Fallback or Error ???
        pass

    if not success:
        raise Exception(f"Merge Failed: {err}")
    
    # Set Path for Merged file 
    output_dir = get_dataset_output_dir(dataset_name)
    # merged_dir = os.path.join(UPLOAD_BASE, "merged")
    os.makedirs(output_dir, exist_ok=True)
    
    # target_filename = f"{dataset_name}_merged.nc" # (dataset_{slot_id}_merged.nc)
    target_filename = "merged.nc"
    target_path = os.path.join(output_dir, target_filename)
    
    if os.path.exists(target_path):
        os.remove(target_path)
    
    # Move merged result to final location
    shutil.move(result['path'], target_path)

    # Cleanup processed files 
    try:
        for f in files:
            os.remove(f)

        # Optional: remove empty processed folder
        if not os.listdir(proc_dir):
            os.rmdir(proc_dir)

        print(f"Cleanup processed files for dataset: {dataset_name}")

    except Exception as e:
        print(f"Warning: Cleanup failed: {e}")
    
    return target_filename