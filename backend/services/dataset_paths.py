import os

UPLOAD_BASE = "uploads"

def get_raw_path(slot_id):
    path = os.path.join(UPLOAD_BASE, "raw", f"dataset_{slot_id}")
    os.makedirs(path, exist_ok=True)
    return path

def get_processed_path(dataset_name: str):
    path = os.path.join(UPLOAD_BASE, "processed", dataset_name)
    os.makedirs(path, exist_ok=True)
    return path

def get_dataset_output_dir(dataset_name: str):
    path = os.path.join("output", dataset_name)
    os.makedirs(path, exist_ok=True)
    return path