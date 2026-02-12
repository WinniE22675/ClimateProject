from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List, Optional
from pydantic import BaseModel
import os
import shutil
import traceback
from services.dataset_service import (
    save_raw_files, 
    get_file_list, 
    delete_raw_file, 
    run_async_calculation,
    run_async_processing,
    check_processing_status )

# from services.dataset_clip import process_and_clip
from services.dataset_metadata import get_dataset_metadata_merged
# from services.dataset_preview import generate_preview_for_processed
# from services.dataset_merge import prepare_merged_file_for_calculation


router = APIRouter()

class SelectionScope(BaseModel):
    startYear: int
    endYear: int
    minLat: float
    maxLat: float
    minLon: float
    maxLon: float

# BASE_DIR = r"D:\Students\YearFour\Project\ClimateRiskMap\ClimReact\my-app\backend" 

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
    # คืนค่า List ของชื่อไฟล์ และปี (ถ้า extract จากชื่อได้)
    return get_file_list(slot_id)

# # 3. Process/Clip Route: crop follow Scope
# @router.post("/datasets/{slot_id}/process_selection")
# def process_selection(slot_id: int, scope: SelectionScope, background_tasks: BackgroundTasks):
#     try:
#         print(f"DEBUG: Processing Slot {slot_id} with scope {scope}")
#         process_and_clip(slot_id, scope)
#         return {"status": "success", "message": "Files clipped and saved."}

#     except Exception as e:
#         print("---------------- ERROR OCCURRED ----------------")
#         traceback.print_exc() 
#         print("------------------------------------------------")
#         raise HTTPException(status_code=500, detail=str(e))
    
# Route Process Selection: crop follow Scope
# @router.post("/datasets/{slot_id}/process_selection")
# def process_selection(slot_id: int, dataset_name: str, scope: SelectionScope, background_tasks: BackgroundTasks):
#     try:
#         # Trigger Background Task
#         background_tasks.add_task(run_async_processing, slot_id, dataset_name, scope)
#         return {"status": "success", "message": "Processing started in background."}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

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

# Get List of Processed Files (Top Panel)
# @router.get("/datasets/{slot_id}/processed_files")
# def list_processed_files(slot_id: int):
#     files = get_processed_files(slot_id)
#     return {"files": files}

# Get Merged Metadata (Left Panel)
@router.get("/datasets/{dataset_name}/metadata")
def get_dataset_metadata(dataset_name: str): # slot_id: int
    meta = get_dataset_metadata_merged(dataset_name)
    if not meta:
        raise HTTPException(status_code=404, detail="Dataset not found or empty")
    return meta

# Generate Preview (Bottom Panel Visualization)
# class PreviewRequest(BaseModel):
#     variable: str

# @router.post("/datasets/{slot_id}/preview")
# def generate_dataset_preview(slot_id: int, req: PreviewRequest):
#     try:
#         paths = generate_preview_for_processed(slot_id, req.variable)
#         # Frontend expects paths relative to public or accessible URL
#         # Assuming frontend fetches static files from /output/...
#         return paths
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# Route Calculate to Process
class BaselinePeriod(BaseModel):
    start_year: Optional[int] = None
    end_year: Optional[int] = None

class CalculateRequest(BaseModel):
    selected_indices: List[str]
    baseline: Optional[BaselinePeriod] = None

# class CalculateRequest(BaseModel):
#     selected_indices: List[str]

# @router.post("/datasets/{slot_id}/calculate_indices")
# async def calculate_indices_from_slot(slot_id: int, req: CalculateRequest):
#     try:
#         # Merge Processed file to Dataset
#         merged_filename = prepare_merged_file_for_calculation(slot_id)
        
#         # prepare Path
#         merged_path = os.path.join(BASE_DIR, "uploads", "merged", merged_filename)

#         if not os.path.exists(merged_path) or os.path.getsize(merged_path) == 0:
#              raise Exception("Merged file creation failed or file is empty.")
        
#         shapefile_path = "data/tha_admbnda_adm1_rtsd_20190221.shp" 
        
#         # Pipeline (generate_all)
#         print(f"Starting pipeline for {merged_filename} with {req.selected_indices}")
#         generate_all(
#             file_input=merged_path, 
#             shapefile_path=shapefile_path,
#             selected_indices=req.selected_indices      
#         )
        
#         return {"status": "success", "message": "Calculation complete", "dataset": merged_filename}

#     except Exception as e:
#         print(f"Calculation failed: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

# @router.post("/datasets/{slot_id}/calculate_indices")
# async def calculate_indices_from_slot(slot_id: int, req: CalculateRequest):
#     try:
#         result = run_async_calculation(
#             slot_id=slot_id,
#             selected_indices=req.selected_indices
#         )
#         return result
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

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
    
# # Route Download
# @router.get("/datasets/{slot_id}/download_merged")
# async def download_merged_dataset(slot_id: int):
#     try:
#         # ใช้ Logic เดียวกับตอนคำนวณเลย คือ Merge ใหม่ทับของเดิม (รับประกันความสดใหม่)
#         merged_filename = prepare_merged_file_for_calculation(slot_id)
#         merged_path = os.path.join(BASE_DIR, "uploads", "merged", merged_filename)
        
#         if not os.path.exists(merged_path):
#              raise HTTPException(status_code=404, detail="Merged file generation failed")

#         return FileResponse(
#             path=merged_path, 
#             filename=merged_filename, 
#             media_type='application/x-netcdf'
#         )
#     except Exception as e:
#         print(f"Download failed: {e}")
#         raise HTTPException(status_code=500, detail=str(e))
    
# Route Download pull from output/{dataset_name}/merged.nc
@router.get("/datasets/{dataset_name}/download_merged")
async def download_merged(dataset_name: str):
    # file_path = os.path.join("output", f"dataset_{slot_id}", f"dataset_{slot_id}_merged.nc")
    file_path = os.path.join(
        "output",
        dataset_name,
        "merged.nc" # f"{dataset_name}_merged.nc"
    )
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=f"{dataset_name}_merged.nc") # f"dataset_{slot_id}_merged.nc"
    raise HTTPException(status_code=404, detail="File not ready")
    
# @router.post("/datasets/{slot_id}/download_custom")
# async def download_custom_dataset(slot_id: int, scope: SelectionScope, background_tasks: BackgroundTasks):
#     try:
#         # Clip -> Merge -> Save
#         merged_filename = prepare_download_with_clip(slot_id, scope)
#         merged_path = os.path.join(BASE_DIR, "uploads", "merged", merged_filename)
        
#         if not os.path.exists(merged_path):
#              raise HTTPException(status_code=404, detail="File generation failed")

#         # send file to User
#         # use BackgroundTasks delete merged data after User download finish 
#         background_tasks.add_task(os.remove, merged_path)

#         return FileResponse(
#             path=merged_path, 
#             filename=f"climate_data_slot{slot_id}_custom.nc", 
#             media_type='application/x-netcdf'
#         )

#     except Exception as e:
#         print(f"Custom download failed: {e}")
#         raise HTTPException(status_code=500, detail=str(e))
    
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

# @router.delete("/datasets/{dataset_name}")
# def delete_dataset(dataset_name: str):

#     dataset_path = os.path.join("output", dataset_name)

#     if not os.path.isdir(dataset_path):
#         raise HTTPException(status_code=404, detail="Dataset not found")

#     try:
#         shutil.rmtree(dataset_path)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

#     return {
#         "status": "success",
#         "message": f"Dataset '{dataset_name}' deleted"
#     }

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
