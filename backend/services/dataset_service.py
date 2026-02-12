import os
import shutil
import xarray as xr
# import numpy as np
# import pandas as pd
# import re
import json
# import gc  
# import time
# import geopandas as gpd
# import uuid # use create temp folder not same

# from processing.export_preview import export_preview_all
# from processing.preprocessing import normalize_var_name, ensure_pr_unit, ensure_temperature_unit
# from processing.overlay import overlay_with_shapefile

# from processing.upload_validation import inspect_file, validate_compatibility, detect_mode, SKIP_VARS
# from processing.merge_datasets import merge_time_mode, merge_attribute_mode, merge_mixed_mode

from services.dataset_paths import *
from services.dataset_merge import prepare_merged_file_for_calculation
from processing.pipeline import generate_all
from services.dataset_clip import process_and_clip
from services.dataset_metadata import get_dataset_metadata_merged

from services.preview_service import run_preview_visualization

from fastapi import BackgroundTasks

async def save_raw_files(slot_id, files):
    target_dir = get_raw_path(slot_id)
    saved_list = []
    
    for file in files:
        file_path = os.path.join(target_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_list.append(file.filename)
    return saved_list

def delete_raw_file(slot_id, filename):
    target_dir = get_raw_path(slot_id)
    file_path = os.path.join(target_dir, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False

def get_file_list(slot_id):
    target_dir = get_raw_path(slot_id)
    if not os.path.exists(target_dir):
        return {"files": []}
    
    files = sorted([f for f in os.listdir(target_dir) if f.endswith('.nc')])
    file_data = []
    
    for f in files:
        file_data.append({"name": f})
        
    return {"files": file_data}

# function for DatasetProcessPage
def get_processed_files(slot_id):
    """List files in the processed folder"""
    proc_dir = get_processed_path(slot_id)
    if not os.path.exists(proc_dir):
        return []
    return sorted([f for f in os.listdir(proc_dir) if f.endswith('.nc')])

def save_metadata_json(slot_id, metadata):
    out_dir = get_dataset_output_dir(slot_id)
    with open(os.path.join(out_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f)

def run_async_calculation(dataset_name: str, selected_indices: list, baseline=None): # slot_id: int
    """
    Run indices calculation using already-merged dataset.
    No merge or clip is performed here.
    """
    # Path must match process_selection output
    merged_path = os.path.join(
        "output",
        f"{dataset_name}",
        "merged.nc" # f"{dataset_name}_merged.nc"
    )

    if not os.path.exists(merged_path):
        raise Exception("Merged file creation failed, dataset: {dataset_name}")

    generate_all(
        file_input=merged_path,
        selected_indices=selected_indices,
        dataset_name=dataset_name,
        baseline=baseline
    )

    return {
        "status": "success",
        "dataset": f"{dataset_name}_merged.nc"
    }

# ---------------------------------------------------------
# Asynchronous Background Task Logic
# ---------------------------------------------------------
def run_async_processing(slot_id, dataset_name, scope, background_tasks):
    """
    1. Clip files (using core_process_file logic)
    2. Merge files
    3. Generate Metadata & Status
    """
    try:
        print(f"[Dataset {dataset_name}] Async Task Started...")
        
        # 1. Update Status -> Processing
        # save_metadata_json(slot_id, {"status": "processing", "message": "Clipping and Merging..."})
        # ---- STEP 1: Clipping ----
        save_metadata_json(
            dataset_name,
            {
                "status": "processing",
                "step": "clipping",
                "message": "Clipping input files"
            }
        )

        # 2. Process & Clip (ใช้ process_and_clip หรือ core_process_file ตามที่คุณมี)
        # แนะนำให้ process_and_clip ทำหน้าที่ Clip ลง folder processed เหมือนเดิมก่อน
        # เพื่อความปลอดภัยของไฟล์ย่อย
        process_and_clip(slot_id, dataset_name, scope)

        save_metadata_json(
            dataset_name,
            {
                "status": "processing",
                "step": "merging",
                "message": "Merging NetCDF files"
            }
        )
        
        # 3. Merge (ใช้ Logic จาก prepare_merged_file_for_calculation)
        merged_filename = prepare_merged_file_for_calculation(dataset_name)
        
        # proc_dir = get_processed_path(slot_id)
        # files = [os.path.join(proc_dir, f) for f in os.listdir(proc_dir) if f.endswith('.nc')]
        
        # if not files:
        #     raise Exception("No processed files to merge.")

        # ---- STEP 3: Finalizing ----
        save_metadata_json(
            dataset_name,
            {
                "status": "processing",
                "step": "finalizing",
                "message": "Extracting dataset metadata"
            }
        )
        
        # Merge Logic
        merged_metadata = get_dataset_metadata_merged(dataset_name)

        if merged_metadata is None:
            raise Exception("Failed to extract merged dataset metadata")
            
        # Update Status -> Ready
        final_meta = {
            "status": "ready",
            "step": "ready",
            "filename": merged_filename,
            **merged_metadata
        }

    
        save_metadata_json(dataset_name, final_meta)
            
        print(f"[Dataset {dataset_name}] Async Task Completed.")

        # background_tasks = BackgroundTasks()
        background_tasks.add_task(
            run_preview_visualization,
            dataset_name
        )

    except Exception as e:
        print(f"[{dataset_name}] Task Failed: {e}")
        save_metadata_json(
            dataset_name,
            {
                "status": "error",
                "step": "error",
                "message": str(e)
            }
        )

def check_processing_status(dataset_name: str):
    out_dir = get_dataset_output_dir(dataset_name)
    meta_path = os.path.join(out_dir, "metadata.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r") as f:
            return json.load(f)
    return {"status": "idle"} 

