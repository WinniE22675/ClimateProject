from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
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

from services.dataset_metadata import get_dataset_metadata_merged

router = APIRouter()

class SelectionScope(BaseModel):
    startYear: int
    endYear: int
    minLat: float
    maxLat: float
    minLon: float
    maxLon: float

# Upload Route: get raw file into Folder follow Slot
@router.post("/datasets/{slot_id}/upload")
async def upload_dataset_files(slot_id: int, files: List[UploadFile] = File(...)):
    # Validate slot_id 1-4
    if slot_id not in [1, 2, 3, 4]:
        raise HTTPException(status_code=400, detail="Invalid slot ID")
    
    saved_files = await save_raw_files(slot_id, files)
    return {"message": f"Saved {len(saved_files)} files", "files": saved_files}

# List Files Route: send list file to Frontend
@router.get("/datasets/{slot_id}/files")
def list_dataset_files(slot_id: int):
    # Return List of file name 
    return get_file_list(slot_id)

class ProcessSelectionRequest(BaseModel):
    slot_id: int
    dataset_name: str
    scope: SelectionScope

@router.post("/datasets/process_selection")
def process_selection(
    req: ProcessSelectionRequest,
    background_tasks: BackgroundTasks
):
    try:
        background_tasks.add_task(
            run_async_processing,
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
def delete_file(slot_id: int, filename: str):
    success = delete_raw_file(slot_id, filename)
    if not success:
        raise HTTPException(status_code=404, detail="File not found")
    return {"message": f"Deleted {filename}"}

# Get Merged Metadata (Left Panel)
@router.get("/datasets/{dataset_name}/metadata")
def get_dataset_metadata(dataset_name: str): # slot_id: int
    meta = get_dataset_metadata_merged(dataset_name)
    if not meta:
        raise HTTPException(status_code=404, detail="Dataset not found or empty")
    return meta

# Route Calculate to Process
class BaselinePeriod(BaseModel):
    start_year: Optional[int] = None
    end_year: Optional[int] = None

class CalculateRequest(BaseModel):
    selected_indices: List[str]
    baseline: Optional[BaselinePeriod] = None

@router.post("/datasets/{dataset_name}/calculate_indices")
async def calculate_indices_from_slot(
    dataset_name: str,
    req: CalculateRequest,
    background_tasks: BackgroundTasks
):
    try:
        # Schedule heavy calculation as background task (Level 2)
        background_tasks.add_task(
            run_async_calculation,
            dataset_name,
            req.selected_indices,
            req.baseline
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
def delete_dataset(dataset_name: str):

    DATASET_ROOTS = {
        "output": os.path.join("output", dataset_name),
        "processed": os.path.join("uploads","processed", dataset_name),
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
    }

class MapGenerateRequest(BaseModel):
    indexName: str
    datasetName: str
    country: str
    province: Optional[str] = None
    startYear: int
    endYear: int
    supportsTrend: bool

@router.post("/maps/generate")
async def generate_map_endpoint(req: MapGenerateRequest):
    """
    Synchronous endpoint to generate specific map (Actual & Trend) on demand.
    Frontend will wait for this to finish before trying to fetch the files.
    """
    try:
        # Call the service function directly (blocks until finished)
        result = generate_on_demand_map(
            dataset_name=req.datasetName,
            index_name=req.indexName,
            start_year=req.startYear,
            end_year=req.endYear,
            country=req.country,
            province=req.province,
            supports_trend=req.supportsTrend
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