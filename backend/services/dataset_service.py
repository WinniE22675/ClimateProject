import os
import shutil
import json

from services.dataset_paths import *
from services.dataset_merge import prepare_merged_file_for_calculation
from processing.pipeline import generate_all, generate_custom_map_pipeline
from services.dataset_clip import process_and_clip
from services.dataset_metadata import get_dataset_metadata_merged
from services.preview_service import run_preview_visualization

async def save_raw_files(user_id: str, slot_id, files):
    target_dir = get_raw_path(user_id, slot_id)
    saved_list = []
    
    for file in files:
        file_path = os.path.join(target_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_list.append(file.filename)
    return saved_list

def delete_raw_file(user_id: str, slot_id, filename):
    target_dir = get_raw_path(user_id, slot_id)
    file_path = os.path.join(target_dir, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False

def get_file_list(user_id: str, slot_id):
    target_dir = get_raw_path(user_id, slot_id)
    if not os.path.exists(target_dir):
        return {"files": []}
    
    files = sorted([f for f in os.listdir(target_dir) if f.endswith('.nc')])
    file_data = []
    
    for f in files:
        file_data.append({"name": f})
        
    return {"files": file_data}

# function for DatasetProcessPage
def get_processed_files(user_id: str, slot_id):
    """List files in the processed folder"""
    proc_dir = get_processed_path(user_id, slot_id)
    if not os.path.exists(proc_dir):
        return []
    return sorted([f for f in os.listdir(proc_dir) if f.endswith('.nc')])

def save_metadata_json(dataset_name, metadata):
    out_dir = get_dataset_output_dir(dataset_name)
    with open(os.path.join(out_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f)

# Define the Master Order to enforce beautiful sorting
MASTER_ORDER = [
    "SPI3", "SPI9", "SPI6", "SPI12", "PRCPTOT", "Rx1day", "Rx5day", "SDII", "R10mm", "R20mm", 
    "CDD", "CWD", "R95p", "R99p", "R95pTOT", "R99pTOT", "FD", "SU", 
    "ID", "TR", "TXx", "TNx", "TXn", "TNn", "TN10p", "TX10p", "TN90p", 
    "TX90p", "WSDI", "CSDI","SPI3_Drought_Frequency",
    "SPI3_Drought_Duration",
    "SPI3_Drought_Peak",
    "SPI3_Drought_Severity",
    "SPI3_Flood_Frequency",
    "SPI3_Flood_Duration",
    "SPI3_Flood_Peak",
    "SPI3_Flood_Severity",

    "SPI6_Drought_Frequency",
    "SPI6_Drought_Duration",
    "SPI6_Drought_Peak",
    "SPI6_Drought_Severity",
    "SPI6_Flood_Frequency",
    "SPI6_Flood_Duration",
    "SPI6_Flood_Peak",
    "SPI6_Flood_Severity",

    "SPI9_Drought_Frequency",
    "SPI9_Drought_Duration",
    "SPI9_Drought_Peak",
    "SPI9_Drought_Severity",
    "SPI9_Flood_Frequency",
    "SPI9_Flood_Duration",
    "SPI9_Flood_Peak",
    "SPI9_Flood_Severity",

    "SPI12_Drought_Frequency",
    "SPI12_Drought_Duration",
    "SPI12_Drought_Peak",
    "SPI12_Drought_Severity",
    "SPI12_Flood_Frequency",
    "SPI12_Flood_Duration",
    "SPI12_Flood_Peak",
    "SPI12_Flood_Severity"
]

def update_metadata_json(dataset_name: str, new_data: dict):
    """
    Read existing metadata.json, update with new_data, and save back.
    This prevents overwriting existing keys.
    """
    out_dir = get_dataset_output_dir(dataset_name)
    os.makedirs(out_dir, exist_ok=True)
    meta_path = os.path.join(out_dir, "metadata.json")
    
    existing_data = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                pass # Proceed with empty dict if file is corrupt
                
    # Update the dictionary with new values
    # existing_data.update(new_data)
    # for key, value in new_data.items():
    #     # Check if the key already exists and BOTH values are lists
    #     if key in existing_data and isinstance(existing_data[key], list) and isinstance(value, list):
    #         # Combine the old list and the new list
    #         combined_list = existing_data[key] + value
    #         # Use set() to remove duplicates, then convert back to list
    #         # Note: set() might lose order. If order matters, use a different deduplication method.
    #         existing_data[key] = list(set(combined_list))
    #     else:
    #         # If it's not a list (e.g., string, dict, or new key), overwrite normally
    #         existing_data[key] = value
    for key, value in new_data.items():
        if key in existing_data and isinstance(existing_data[key], list) and isinstance(value, list):
            
            # 1. Combine lists without destroying the initial order
            # Using dict.fromkeys() is a Python trick to remove duplicates while preserving order
            combined_list = existing_data[key] + value
            unique_list = list(dict.fromkeys(combined_list))
            
            # 2. Sort the list if the key is 'available_indices' (or any other key you want to sort)
            if key == "available_indices":
                unique_list.sort(
                    key=lambda x: MASTER_ORDER.index(x) if x in MASTER_ORDER else 999
                )
                
            existing_data[key] = unique_list
            
        else:
            # Overwrite normally for non-list items
            existing_data[key] = value
    
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2)

def read_metadata_json(dataset_name: str) -> dict:
    """Read and return metadata.json as a dictionary."""
    meta_path = os.path.join(get_dataset_output_dir(dataset_name), "metadata.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def run_async_calculation(dataset_name: str, selected_indices: list, baseline=None, spi_threshold: float = 1): # slot_id: int
    """
    Run indices calculation using already-merged dataset.
    No merge or clip is performed here.
    """

    # Expand selected_indices to automatically include all 8 SPI events if a base SPI is selected
    extended_indices = []
    if selected_indices:
        for idx in selected_indices:
            extended_indices.append(idx)
            # Check if it is a base SPI (e.g., "SPI6" without underscores)
            if idx.startswith("SPI") and "_" not in idx:
                for event in ["Drought", "Flood"]:
                    for metric in ["Frequency", "Duration", "Peak", "Severity"]:
                        extended_indices.append(f"{idx}_{event}_{metric}")

    # Remove duplicates while preserving order
    extended_indices = list(dict.fromkeys(extended_indices))

    # Update baseline and basic info BEFORE generation starts
    metadata_updates = {}
    if baseline:
        # Convert Pydantic model (BaselinePeriod) to dict safely
        baseline_dict = baseline.dict() if hasattr(baseline, 'dict') else baseline
        metadata_updates["baseline"] = baseline_dict
    else:
        metadata_updates["baseline"] = None
        
    update_metadata_json(dataset_name, metadata_updates)

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
        baseline=baseline,
        spi_threshold=spi_threshold
    )

    update_metadata_json(dataset_name, {"available_indices": extended_indices})

    return {
        "status": "success",
        "dataset": f"{dataset_name}_merged.nc"
    }

# Asynchronous Background Task Logic
def run_async_processing(user_id: str, slot_id, dataset_name, scope, background_tasks):
    """
    1. Clip files (using core_process_file logic)
    2. Merge files
    3. Generate Metadata & Status
    """
    try:
        print(f"[Dataset {dataset_name}] Async Task Started...")
        
        # 1. Update Status
        save_metadata_json(
            dataset_name,
            {
                "status": "processing",
                "step": "clipping",
                "message": "Clipping input files"
            }
        )

        # 2. Process & Clip 
        process_and_clip(user_id, slot_id, dataset_name, scope)

        print(f"[Dataset {dataset_name}] Clipping")

        save_metadata_json(
            dataset_name,
            {
                "status": "processing",
                "step": "merging",
                "message": "Merging NetCDF files"
            }
        )
        
        # 3. Merge (use Logic from prepare_merged_file_for_calculation)
        merged_filename = prepare_merged_file_for_calculation(user_id, dataset_name)

        print(f"[Dataset {dataset_name}] Merge Dataset")

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

        print(f"[Dataset {dataset_name}] Get metadata")

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

        run_preview_visualization(dataset_name)

        print(f"[Dataset {dataset_name}] All Processes and Previews Finished.")

        # Delete the temporary 'processed' folder immediately after successful merge
        proc_dir = get_processed_path(user_id, dataset_name)
        if os.path.exists(proc_dir):
            try:
                print(f"[Dataset {dataset_name}] Cleaning up temporary processed files...")
                shutil.rmtree(proc_dir)
            except Exception as e:
                print(f"[Warning] Failed to cleanup processed folder for {dataset_name}: {e}")

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

def generate_on_demand_map(dataset_name: str, index_name: str, start_year: int, end_year: int, country: str, province: str, supports_trend: bool, spi_threshold: float = 1):
    """
    Service layer to handle on-demand map generation.
    """
    # Define dataset path 
    # if dataset_name == "default":
    #     # Adjust this to where your default raw/merged data is stored
    #     # merged_path = os.path.join("data", "merged.nc") 
    #     # output_base_dir = "data"
    #     raise Exception(f"default can't calculate indices") #############################################################
    # else:
    merged_path = os.path.join("output", dataset_name, "merged.nc")
    output_base_dir = os.path.join("output", dataset_name)

    if not os.path.exists(merged_path):
        raise Exception(f"Merged dataset file not found at {merged_path}")
    
    metadata = read_metadata_json(dataset_name)
    saved_baseline = metadata.get("baseline")
    # # saved_baseline will be something like {"start_year": 1981, "end_year": 2010} or None

    # Call the specific pipeline for map generation
    generate_custom_map_pipeline(
        file_input=merged_path,
        output_base_dir=output_base_dir,
        index_name=index_name,
        start_year=start_year,
        end_year=end_year,
        country=country,
        province=province,
        supports_trend=supports_trend,
        baseline=saved_baseline,
        spi_threshold=spi_threshold
    )

    return {"dataset": dataset_name, "index": index_name}