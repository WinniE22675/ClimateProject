import os
import shutil
import json
import geopandas as gpd
import shapely

from services.dataset_paths import *
from services.dataset_merge import prepare_merged_file_for_calculation
from processing.pipeline import generate_all, generate_custom_map_pipeline
from services.dataset_clip import process_and_clip
from services.dataset_metadata import get_dataset_metadata_merged
from services.preview_service import run_preview_visualization

import os
import shutil
import zipfile
from services.shapefile_services import detect_region_columns
from typing import Optional
from services.dataset_metadata import read_metadata_json

import re # IMPORT Regex to clean strings

from fastapi import HTTPException # Ensure this is imported for raising HTTP errors

# FILE SIZE LIMITS CONFIGURATION
MAX_SLOT_SIZE_BYTES = 5 * 1024 * 1024 * 1024  # 5 GB limit per dataset slot
MAX_SHAPEFILE_SIZE_BYTES = 1 * 1024 * 1024 * 1024  # 500 MB limit for shapefiles
UPLOAD_CHUNK_SIZE = 1024 * 1024               # 1 MB chunk size for safe reading

def get_dir_size(path: str) -> int:
    """Helper function to calculate total size of a directory in bytes."""
    total_size = 0
    if os.path.exists(path):
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
    return total_size

async def save_raw_files(user_id: str, slot_id, files):
    target_dir = get_raw_path(user_id, slot_id)
    os.makedirs(target_dir, exist_ok=True)
    
    # Calculate currently used space in this slot
    current_slot_size = get_dir_size(target_dir)
    saved_list = []
    
    for file in files:
        file_path = os.path.join(target_dir, file.filename)
        
        # Read and write in chunks to prevent memory overload and monitor size
        with open(file_path, "wb") as buffer:
            while chunk := file.file.read(UPLOAD_CHUNK_SIZE):
                buffer.write(chunk)
                current_slot_size += len(chunk)
                
                # Abort immediately if the 5GB slot limit is breached
                if current_slot_size > MAX_SLOT_SIZE_BYTES:
                    buffer.close()
                    os.remove(file_path) # Clean up the partial file
                    raise HTTPException(
                        status_code=413, 
                        detail="Upload failed: Total dataset size exceeds the 5 GB limit per slot."
                    )
                    
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


def run_async_calculation(
        user_id: str,
        dataset_name: str,
        selected_indices: list,
        shapefile_name: str,
        target_col: str,
        country: str,
        baseline=None,
        spi_threshold: float = 1,
        is_existing: bool = False
): 
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

    existing_meta = read_metadata_json(dataset_name)
    workspaces = existing_meta.get("workspaces", {})
    existing_workspace = workspaces.get(country, {})
    existing_indices = existing_workspace.get("available_indices", [])

    if is_existing:
        # if Workspace can load Metadata in file
        final_shapefile_name = existing_workspace.get("shapefile_name")
        final_target_col = existing_workspace.get("target_col")
        area_list = existing_workspace.get("available_areas", [])
        
        # prevent if Metadata don't have 
        if not final_shapefile_name or not final_target_col:
            raise Exception(f"Cannot find existing shapefile config for workspace '{country}'.")
            
        print(f"Using existing shapefile config: {final_shapefile_name} / {final_target_col}")
        
    else:
        # if new use value from Frontend
        final_shapefile_name = shapefile_name
        final_target_col = target_col

    shapefile_path = get_shapefile_path(user_id, final_shapefile_name)
    
    output_dir = get_dataset_output_dir(dataset_name)
    country_output_dir = os.path.join(output_dir, country)
    os.makedirs(country_output_dir, exist_ok=True) # Ensure the directory exists
    
    # 2. Set the cached GeoJSON path to be inside the public output folder
    cached_geojson_path = os.path.join(country_output_dir, "boundary.geojson")
    
    try:
        # Case 1: GeoJSON does not exist OR file is empty (0 bytes) -> Generate cache
        if not os.path.exists(cached_geojson_path) or os.path.getsize(cached_geojson_path) == 0:
            print(f"Generating public GeoJSON cache for {country}...")
            
            if not os.path.exists(shapefile_path):
                raise Exception(f"Valid .shp file not found at: {shapefile_path}")

            # Load full shapefile and convert to standard GPS projection
            gdf_full = gpd.read_file(shapefile_path)
            gdf_full = gdf_full.to_crs("EPSG:4326")

            gdf_full['geometry'] = shapely.set_precision(gdf_full['geometry'].values, grid_size=0.001)

            # Extract unique areas BEFORE dropping columns
            area_list = gdf_full[final_target_col].dropna().unique().tolist()
            
            # KEEP ONLY final_target_coll AND geometry to prevent Datetime JSON serialization errors
            gdf_minimal = gdf_full[[final_target_col, 'geometry']]
            
            # Save as GeoJSON directly to the public output directory
            geojson_string = gdf_minimal.to_json()
            
            with open(cached_geojson_path, "w", encoding="utf-8") as f:
                f.write(geojson_string)
                
            print(f"Successfully generated public GeoJSON at: {cached_geojson_path}")
                
        # Case 2: GeoJSON already exists and is not empty
        else:
            shp_areas = gpd.read_file(cached_geojson_path, rows=1000)
            area_list = shp_areas[final_target_col].dropna().unique().tolist()

    except Exception as e:
        print(f"[Error] Failed to read shapefile for available_areas: {e}")
        area_list = []

    if len(area_list) <= 1:
        print(f"Notice: '{final_target_col}' contains only 1 area. Setting available_areas to empty list.")
        area_list = []

    # Combine old indices with newly calculated ones
    combined_indices = existing_indices + extended_indices

    # Remove duplicates while preserving order
    unique_indices = list(dict.fromkeys(combined_indices))

    # Format the baseline dictionary
    baseline_dict = None
    if baseline:
        baseline_dict = baseline.dict() if hasattr(baseline, 'dict') else baseline

    # Create or update the configuration for THIS specific country
    workspaces[country] = {
        "shapefile_name": final_shapefile_name,
        "target_col": final_target_col,
        "available_areas": area_list,
        "baseline": baseline_dict,
        "available_indices": unique_indices # Store calculated indices per workspace
    }

    # Save the nested workspaces object back to metadata.json
    update_metadata_json(dataset_name, {"workspaces": workspaces})

    output_dir = get_dataset_output_dir(dataset_name)
    merged_path = os.path.join(output_dir, "merged.nc")

    if not os.path.exists(merged_path):
        raise Exception(f"Merged file creation failed, dataset: {dataset_name}")
    
    run_preview_visualization(dataset_name, user_id, country)

    generate_all(
        file_input=merged_path,
        selected_indices=selected_indices,
        dataset_name=dataset_name,
        shapefile_path=shapefile_path,
        target_col=final_target_col, 
        country=country,
        baseline=baseline,
        spi_threshold=spi_threshold
    )

    update_metadata_json(dataset_name, {"status": "ready", "step": "ready"})

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
        try :
            with open(meta_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {
            "status": "error", 
            "message": "Status file not found."
        }
    return {"status": "idle"} 

def generate_on_demand_map(
        user_id: str,
        dataset_name: str,
        index_name: str,
        start_year: int,
        end_year: int,
        country: str,
        province: str,
        supports_trend: bool,
        shapefile_name: Optional[str] = None,
        target_col: Optional[str] = None,
        spi_threshold: float = 1):
    """
    Service layer to handle on-demand map generation.
    """
    merged_path = os.path.join("output", dataset_name, "merged.nc")
    output_base_dir = os.path.join("output", dataset_name)

    if not os.path.exists(merged_path):
        raise Exception(f"Merged dataset file not found at {merged_path}")
    
    metadata = read_metadata_json(dataset_name)

    workspaces = metadata.get("workspaces", {})
    current_workspace = workspaces.get(country, {})

    # Extract baseline from the specific workspace
    saved_baseline = metadata.get("baseline")
 
    final_shapefile_name = shapefile_name or current_workspace.get("shapefile_name")
    final_target_col = target_col or current_workspace.get("target_col")

    if not final_shapefile_name or not final_target_col:
        raise Exception("Shapefile metadata is missing. Please recalculate indices.")

    # RESOLVE SHAPEFILE PATH
    shapefile_path = get_shapefile_path(user_id, final_shapefile_name)

    if shapefile_path is None or not os.path.exists(shapefile_path):
        raise Exception(
            f"The shapefile '{final_shapefile_name}' has been deleted or is missing from the server. "
            f"Please re-upload the file or go to the Process page to recalculate with a valid shapefile."
        )

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
        shapefile_path=shapefile_path,
        target_col=final_target_col,
        baseline=saved_baseline,
        spi_threshold=spi_threshold
    )

    return {"dataset": dataset_name, "index": index_name}

async def upload_and_validate_shapefile(user_id: str, file, custom_name: str = None):
    user_shape_dir = get_user_shapefile_dir(user_id)

    if custom_name:
        # Clean the user-provided string to prevent folder creation errors
        base_name = re.sub(r'[^A-Za-z0-9_ -]', '', custom_name).strip()
        # Fallback if the clean name becomes empty
        if not base_name:
            base_name = os.path.splitext(file.filename)[0]
    else:
        # Get original filename without extension (e.g., "my_map")
        base_name = os.path.splitext(file.filename)[0]
    
    # Handle duplicate names by appending a counter (like Windows)
    folder_name = base_name
    counter = 1
    
    # Check if folder already exists, if yes, increment counter
    while os.path.exists(os.path.join(user_shape_dir, folder_name)):
        folder_name = f"{base_name}_{counter}"
        counter += 1
        
    target_dir = os.path.join(user_shape_dir, folder_name)
    os.makedirs(target_dir, exist_ok=True)
    zip_path = os.path.join(target_dir, file.filename)
    
    # 1. Save the uploaded .zip file WITH size limit enforcement
    current_file_size = 0
    with open(zip_path, "wb") as buffer:
        while chunk := file.file.read(UPLOAD_CHUNK_SIZE):
            buffer.write(chunk)
            current_file_size += len(chunk)
            
            # Abort if the zip file exceeds 500MB
            if current_file_size > MAX_SHAPEFILE_SIZE_BYTES:
                buffer.close()
                os.remove(zip_path)      # Remove partial zip
                shutil.rmtree(target_dir) # Clean up generated folder
                raise HTTPException(
                    status_code=413, 
                    detail="Upload failed: Shapefile zip exceeds the 500 MB limit."
                )
            
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext == '.zip':
        # 2. Extract the .zip file
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
        except zipfile.BadZipFile:
            shutil.rmtree(target_dir)
            raise Exception("Invalid or corrupted zip file")
            
        # Remove the .zip file after successful extraction
        os.remove(zip_path)
        
        # 3. Validate required shapefile components (.shp, .shx, .dbf, .prj)
        extracted_files = os.listdir(target_dir)
        extensions = [os.path.splitext(f)[1].lower() for f in extracted_files]
        
        required_exts = ['.shp', '.shx', '.dbf', '.prj']
        missing_exts = [ext for ext in required_exts if ext not in extensions]
        
        if missing_exts:
            shutil.rmtree(target_dir)
            raise Exception(f"Missing required files: {', '.join(missing_exts)}")
        
    elif file_ext == '.geojson':
        # No extraction or multiple-file validation needed for GeoJSON. 
        # The file is already saved as a single complete file.
        pass
    
    # Return the folder_name to be used as the display name and ID in Frontend
    return {
        "status": "success",
        "message": "Shapefile uploaded and validated successfully",
        "shapefile_name": folder_name 
    }

def get_shapefile_columns(user_id: str, shapefile_name: str) -> dict:
    """
    Locates the shapefile directory (user or global), finds the .shp file,
    and extracts its text columns.
    """
    user_shape_dir = get_user_shapefile_dir(user_id)
    target_dir = os.path.join(user_shape_dir, shapefile_name)
    
    # Fallback: Check global directory if not found in user directory
    if not os.path.exists(target_dir):
        global_shape_dir = get_global_shapefile_dir()
        target_dir = os.path.join(global_shape_dir, shapefile_name)
        
        if not os.path.exists(target_dir):
            raise Exception("Shapefile directory not found")

    valid_files = [f for f in os.listdir(target_dir) if f.lower().endswith(('.shp', '.geojson'))]
    
    if not valid_files:
        raise Exception("No .shp or .geojson file found inside the directory")
        
    # Construct the full path to the .shp file
    shp_path = os.path.join(target_dir, valid_files[0])
    
    # Call the utility function to read the columns
    return detect_region_columns(shp_path)