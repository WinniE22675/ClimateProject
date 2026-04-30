# routes/dataset_routes.py
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends, Query, Form
from fastapi.responses import FileResponse
from typing import List, Optional
from pydantic import BaseModel
import os
import shutil
from services.dataset_service import (
    save_raw_files, 
    get_file_list, 
    delete_raw_file, 
    run_async_calculation,
    run_async_processing,
    check_processing_status,
    generate_on_demand_map
)

# from services.dataset_metadata import get_dataset_metadata_merged

from dependencies import get_current_user, require_analyst_role
from services.dataset_paths import *

import json
import geopandas as gpd

router = APIRouter()

class SelectionScope(BaseModel):
    startYear: Optional[int] = None
    endYear: Optional[int] = None
    minLat: Optional[float] = None
    maxLat: Optional[float] = None
    minLon: Optional[float] = None
    maxLon: Optional[float] = None

# Upload Route: get raw file into Folder follow Slot
@router.post("/datasets/{slot_id}/upload")
async def upload_dataset_files(
    slot_id: int, 
    files: List[UploadFile] = File(...), 
    current_user: dict = Depends(require_analyst_role)
):
    # Validate slot_id 1-4
    if slot_id not in [1, 2, 3, 4]:
        raise HTTPException(status_code=400, detail="Invalid slot ID")
    
    saved_files = await save_raw_files(current_user["id"], slot_id, files)
    return {"message": f"Saved {len(saved_files)} files", "files": saved_files}

# List Files Route: send list file to Frontend
@router.get("/datasets/{slot_id}/files")
def list_dataset_files(slot_id: int, current_user: dict = Depends(get_current_user)):
    # Return List of file name 
    return get_file_list(current_user["id"], slot_id)

class ProcessSelectionRequest(BaseModel):
    slot_id: int
    dataset_name: str
    scope: SelectionScope

@router.post("/datasets/process_selection")
def process_selection(
    req: ProcessSelectionRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_analyst_role)   
):
    try:
        # Check for duplicate dataset name before processing
        output_dir = os.path.join("output", req.dataset_name)
        if os.path.exists(output_dir):
            raise HTTPException(
                status_code=400, 
                detail=f"Dataset name '{req.dataset_name}' already exists. Please use a different name."
            )
        
        background_tasks.add_task(
            run_async_processing,
            current_user["id"],
            req.slot_id,
            req.dataset_name,
            req.scope,
            background_tasks
        )
        return {
            "status": "success",
            "dataset_name": req.dataset_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    
@router.delete("/datasets/{slot_id}/files/{filename}")
def delete_file(slot_id: int, filename: str, current_user: dict = Depends(require_analyst_role)):
    success = delete_raw_file(current_user["id"], slot_id, filename)
    if not success:
        raise HTTPException(status_code=404, detail="File not found")
    return {"message": f"Deleted {filename}"}

# Get Merged Metadata (Left Panel)
# @router.get("/datasets/{dataset_name}/metadata")
# def get_dataset_metadata(dataset_name: str): # slot_id: int
#     meta = get_dataset_metadata_merged(dataset_name)
#     if not meta:
#         raise HTTPException(status_code=404, detail="Dataset not found or empty")
#     return meta
# Get Metadata (Read directly from metadata.json for better performance and workspace data)
@router.get("/datasets/{dataset_name}/metadata")
def get_dataset_metadata(dataset_name: str):
    # Define path to the JSON file
    dataset_dir = os.path.join("output", dataset_name)
    metadata_path = os.path.join(dataset_dir, "metadata.json")

    # Check if file exists
    if not os.path.exists(metadata_path):
        raise HTTPException(status_code=404, detail="Metadata not found or dataset empty")

    try:
        # Read and return JSON data directly
        with open(metadata_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        return meta
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read metadata: {str(e)}")

# Route Calculate to Process
class BaselinePeriod(BaseModel):
    start_year: Optional[int] = None
    end_year: Optional[int] = None

class CalculateRequest(BaseModel):
    selected_indices: List[str]
    shapefile_name: str
    target_col: str
    country: str
    baseline: Optional[BaselinePeriod] = None
    spi_threshold: Optional[float] = 1 # Add SPI threshold with a default value

@router.post("/datasets/{dataset_name}/calculate_indices")
async def calculate_indices_from_slot(
    dataset_name: str,
    req: CalculateRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_analyst_role)
):
    try:
        # Schedule heavy calculation as background task (Level 2)
        background_tasks.add_task(
            run_async_calculation,
            current_user["id"], # Need user_id to find shapefile folder
            dataset_name,
            req.selected_indices,
            req.shapefile_name,
            req.target_col,
            req.country,
            req.baseline,
            req.spi_threshold
        )

        # Return immediately (do NOT wait for calculation)
        return {
            "status": "processing",
            "message": "Indices calculation started in background"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Route Download pull from output/{dataset_name}/merged.nc
@router.get("/datasets/{dataset_name}/download_merged")
async def download_merged(dataset_name: str):
    file_path = os.path.join(
        "output",
        dataset_name,
        "merged.nc" 
    )
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=f"{dataset_name}_merged.nc") 
    raise HTTPException(status_code=404, detail="File not ready")
    
# Route check status
@router.get("/datasets/{dataset_name}/status")
def get_status(dataset_name: str):
    return check_processing_status(dataset_name)

@router.get("/datasets")
def list_available_datasets():
    """
    Return list of dataset names that already have merged.nc
    """
    base_dir = "output"
    datasets = []

    if not os.path.exists(base_dir):
        return {"datasets": []}

    for name in os.listdir(base_dir):
        dataset_dir = os.path.join(base_dir, name)
        merged_file = os.path.join(dataset_dir, "merged.nc")

        if os.path.isdir(dataset_dir) and os.path.exists(merged_file):
            datasets.append(name)

    return {"datasets": datasets}

@router.delete("/datasets/{dataset_name}")
def delete_dataset(dataset_name: str, current_user: dict = Depends(require_analyst_role)):

    DATASET_ROOTS = {
        "output": os.path.join("output", dataset_name),
        # "processed": os.path.join("uploads","processed", dataset_name),
        # optional future
        # "uploads": os.path.join("uploads", dataset_name),
    }

    deleted = []
    missing = []

    for key, path in DATASET_ROOTS.items():
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
                deleted.append(key)
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to delete {key}: {str(e)}"
                )
        else:
            missing.append(key)

    if not deleted:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return {
        "status": "success",
        "dataset": dataset_name,
        "deleted": deleted,
        "missing": missing,
        "deleted_by": current_user["email"]
    }

class MapGenerateRequest(BaseModel):
    indexName: str
    datasetName: str
    country: str
    province: Optional[str] = None
    startYear: int
    endYear: int
    shapefile_name: Optional[str] = None
    target_col: Optional[str] = None
    supportsTrend: bool
    spi_threshold: Optional[float] = 1

@router.post("/maps/generate")
async def generate_map_endpoint(req: MapGenerateRequest, current_user: dict = Depends(require_analyst_role)):
    """
    Synchronous endpoint to generate specific map (Actual & Trend) on demand.
    Frontend will wait for this to finish before trying to fetch the files.
    """
    try:
        # Call the service function directly (blocks until finished)
        result = generate_on_demand_map(
            user_id=current_user["id"],
            dataset_name=req.datasetName,
            index_name=req.indexName,
            start_year=req.startYear,
            end_year=req.endYear,
            country=req.country,
            shapefile_name=req.shapefile_name,
            target_col = req.target_col,
            province=req.province,
            supports_trend=req.supportsTrend,
            spi_threshold=req.spi_threshold
        )
        
        return {
            "status": "success",
            "message": f"Maps generated for {req.startYear}-{req.endYear}",
            "details": result
        }

    except Exception as e:
        print(f"Error generating map: {e}")
        # Return 500 Internal Server Error so Frontend knows it failed
        raise HTTPException(status_code=500, detail=str(e))
    
from services.dataset_service import upload_and_validate_shapefile

@router.post("/shapefiles/upload")
async def upload_shapefile(
    file: UploadFile = File(...),
    custom_name: str = Form(None),
    current_user: dict = Depends(require_analyst_role)
):
    # Validate file extension before processing
    # if not file.filename.lower().endswith('.zip'):
    #     raise HTTPException(status_code=400, detail="Only .zip files are allowed")
    file_ext = file.filename.lower()
    if not (file_ext.endswith('.zip') or file_ext.endswith('.geojson')):
        raise HTTPException(status_code=400, detail="Only .zip or .geojson files are allowed")
    
    try:
        result = await upload_and_validate_shapefile(current_user["id"], file, custom_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
from services.dataset_service import get_shapefile_columns

@router.get("/shapefiles/{shapefile_name}/columns")
def fetch_shapefile_columns(
    shapefile_name: str,
    current_user: dict = Depends(require_analyst_role)
):
    """
    API endpoint to get available text columns and a default suggested column 
    from a specific shapefile.
    """
    try:
        result = get_shapefile_columns(current_user["id"], shapefile_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/shapefiles")
def list_available_shapefiles(
    user_only: bool = Query(False),
    current_user: dict = Depends(require_analyst_role)
    ):
    user_shape_dir = get_user_shapefile_dir(current_user["id"])
    global_shape_dir = get_global_shapefile_dir()
    
    shapefiles = []
    
    # Read user's own shapefiles
    if os.path.exists(user_shape_dir):
        # shapefiles.extend([d for d in os.listdir(user_shape_dir) if os.path.isdir(os.path.join(user_shape_dir, d))])
        user_dirs = [d for d in os.listdir(user_shape_dir) if os.path.isdir(os.path.join(user_shape_dir, d))]
        for d in user_dirs:
            shapefiles.append({"name": d, "is_global": False})
        
    # Read global shapefiles ONLY if user_only is False
    if not user_only:
        if os.path.exists(global_shape_dir):
            global_files = [d for d in os.listdir(global_shape_dir) if os.path.isdir(os.path.join(global_shape_dir, d))]
            # shapefiles.extend([f for f in global_files if f not in shapefiles])

            # Avoid duplicates if user uploaded a file with the same name
            existing_names = [s["name"] for s in shapefiles]
            for f in global_files:
                if f not in existing_names:
                    shapefiles.append({"name": f, "is_global": True})
            
    return {"shapefiles": shapefiles}

@router.delete("/shapefiles/{shapefile_name}")
def delete_shapefile(shapefile_name: str, current_user: dict = Depends(require_analyst_role)):
    """
    Delete a user's uploaded shapefile directory.
    """
    user_shape_dir = get_user_shapefile_dir(current_user["id"])
    target_dir = os.path.join(user_shape_dir, shapefile_name)
    
    # Check if the directory exists
    if os.path.exists(target_dir):
        try:
            # Use shutil.rmtree to delete the entire directory and its contents
            shutil.rmtree(target_dir)
            return {"message": f"Deleted shapefile {shapefile_name} successfully"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete directory: {str(e)}")
            
    raise HTTPException(status_code=404, detail="Shapefile not found")

# # The API acts as a smart middleman
# @router.get("/shapefiles/{shapefile_name}/geojson")
# def get_shapefile_geojson(shapefile_name: str, current_user: dict = Depends(require_analyst_role)):
    
#     # 1. Secures the file (Only this user can access their directory)
#     shapefile_path = get_shapefile_path(current_user["id"], shapefile_name)
#     shapefile_dir = os.path.dirname(shapefile_path)
#     cached_geojson_path = os.path.join(shapefile_dir, "boundary.geojson")
    
#     # 2. Checks existence and handles errors gracefully
#     if os.path.exists(cached_geojson_path):
#         with open(cached_geojson_path, "r", encoding="utf-8") as f:
#             return json.load(f)
#     else:
#         # 3. Returns meaningful error instead of just a dead link
#         raise HTTPException(status_code=404, detail="Cache not found. Run Calculate first.")

@router.delete("/datasets/{dataset_name}/workspaces/{workspace_name}")
def delete_workspace(dataset_name: str, workspace_name: str, current_user: dict = Depends(require_analyst_role)):
    # Define paths
    dataset_dir = os.path.join("output", dataset_name)
    metadata_path = os.path.join(dataset_dir, "metadata.json")
    
    # 1. Check if metadata exists
    if not os.path.exists(metadata_path):
        raise HTTPException(status_code=404, detail="Metadata not found for this dataset")
        
    # 2. Read existing metadata
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
        
    # 3. Check if workspace exists in metadata
    if "workspaces" not in metadata or workspace_name not in metadata["workspaces"]:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_name}' not found in metadata")
        
    # 4. Delete workspace directory and its calculated files
    workspace_path = os.path.join(dataset_dir, workspace_name)
    deleted_files = False
    if os.path.exists(workspace_path):
        try:
            shutil.rmtree(workspace_path)
            deleted_files = True
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to delete workspace files: {str(e)}"
            )
            
    # 5. Remove workspace from metadata and save
    del metadata["workspaces"][workspace_name]
    
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
        
    return {
        "status": "success",
        "dataset": dataset_name,
        "deleted_workspace": workspace_name,
        "files_deleted": deleted_files,
        "deleted_by": current_user["email"]
    }