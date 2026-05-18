import os
import shutil
import tempfile

from processing.upload_validation import inspect_file, detect_mode
from processing.merge_datasets import merge_time_mode, merge_attribute_mode, merge_mixed_mode
from services.dataset_paths import get_processed_path, get_dataset_output_dir


def prepare_merged_file_for_calculation(user_id: str,dataset_name):
    proc_dir = get_processed_path(user_id, dataset_name)
    files = [os.path.join(proc_dir, f) for f in os.listdir(proc_dir) if f.endswith('.nc')]
    
    if not files:
        raise Exception("No files to calculate")

    # Detect Mode again from Process file (optional ? really ?)
    metas = [inspect_file(f) for f in files]
    mode, info, _ = detect_mode(metas)
    print(f"Detected Merge Mode: {mode}")

    success = False
    result = None
    err = []

    with tempfile.TemporaryDirectory(prefix=f"merge_user_{user_id}_") as temp_merged_dir:

        if mode == "time":
            success, result, err = merge_time_mode(files, temp_merged_dir)
        elif mode == "attribute":
            success, result, err = merge_attribute_mode(files, temp_merged_dir)
        elif mode == "mixed":
            # Mixed mode send temp_paths or group correct file
            success, result, err = merge_mixed_mode(files, info['groups'], metas, files, temp_merged_dir)
        else:
            raise Exception(f"Unsupported merge mode: {mode}")

        if not success:
            raise Exception(f"Merge Failed: {err}")
        
        # Set Path for final Merged file (Public Output Directory)
        output_dir = get_dataset_output_dir(dataset_name)
        os.makedirs(output_dir, exist_ok=True)
        
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

        # remove empty processed folder
        if not os.listdir(proc_dir):
            os.rmdir(proc_dir)

        print(f"Cleanup processed files for dataset: {dataset_name}")

    except Exception as e:
        print(f"Warning: Cleanup failed: {e}")
    
    return target_filename