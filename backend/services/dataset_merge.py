import os
import shutil
import xarray as xr
import uuid # use create temp folder not same
import glob

from processing.upload_validation import inspect_file, detect_mode
from processing.merge_datasets import merge_time_mode, merge_attribute_mode, merge_mixed_mode
from services.dataset_paths import get_processed_path, get_dataset_output_dir
# from services.dataset_clip import core_process_file

# UPLOAD_BASE = "uploads"

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
    
    # output_filename = f"dataset_{slot_id}_merged.nc"
    # output_path = os.path.join(merged_dir, output_filename)
    
    # # Merge และ Save เป็นไฟล์เดียว
    # with xr.open_mfdataset(files, combine='by_coords') as ds:
    #     ds.to_netcdf(output_path)
    
    # return output_filename # ส่งชื่อไฟล์กลับไป (หรือ full path ก็ได้แล้วแต่ pipeline)

# def prepare_download_with_clip(slot_id, scope):
#     raw_dir = get_raw_path(slot_id)
#     files = sorted([os.path.join(raw_dir, f) for f in os.listdir(raw_dir) if f.endswith('.nc')])
    
#     if not files:
#         raise Exception("No raw files found")

#     # 1. สร้าง Temp Folder สำหรับเก็บไฟล์ที่ Clip แล้วเฉพาะกิจ
#     temp_id = str(uuid.uuid4())
#     temp_dir = os.path.join(UPLOAD_BASE, "temp_download", temp_id)
#     os.makedirs(temp_dir, exist_ok=True)

#     try:
#         # 2. Process & Clip ลง Temp
#         valid_files = []
#         for f in files:
#             filename = os.path.basename(f)
#             save_path = os.path.join(temp_dir, filename)
#             success = core_process_file(f, save_path, scope)
#             if success:
#                 valid_files.append(save_path)
        
#         if not valid_files:
#             raise Exception("No data found in the selected range.")

#         # 3. Merge Files ใน Temp
#         # ใช้ Logic เดียวกับ prepare_merged_file_for_calculation แต่ระบุ folder เอง
#         merged_dir = os.path.join(UPLOAD_BASE, "merged")
#         os.makedirs(merged_dir, exist_ok=True)
#         output_filename = f"download_{slot_id}_{temp_id}.nc"
#         output_path = os.path.join(merged_dir, output_filename)

#         # Detect Mode & Merge (เหมือนเดิม)
#         # เพื่อความง่าย ใช้ open_mfdataset save เลยก็ได้เพราะผ่านการ clean มาแล้ว
#         with xr.open_mfdataset(valid_files, combine='by_coords') as ds:
#             ds.to_netcdf(output_path)
            
#         return output_filename

#     finally:
#         # 4. Cleanup Temp Folder (สำคัญมาก)
#         if os.path.exists(temp_dir):
#             shutil.rmtree(temp_dir)