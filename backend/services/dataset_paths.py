import os

UPLOAD_BASE = "uploads"

# def get_raw_path(slot_id):
#     path = os.path.join(UPLOAD_BASE, "raw", f"dataset_{slot_id}")
#     os.makedirs(path, exist_ok=True)
#     return path

# def get_processed_path(dataset_name: str):
#     path = os.path.join(UPLOAD_BASE, "processed", dataset_name)
#     os.makedirs(path, exist_ok=True)
#     return path

def get_raw_path(user_id: str, slot_id: int):
    # Path: uploads/user_{user_id}/raw/dataset_{slot_id}
    path = os.path.join(UPLOAD_BASE, f"user_{user_id}", "raw", f"dataset_{slot_id}")
    os.makedirs(path, exist_ok=True)
    return path

def get_processed_path(user_id: str, dataset_name: str):
    # Path: uploads/user_{user_id}/processed/{dataset_name}
    path = os.path.join(UPLOAD_BASE, f"user_{user_id}", "processed", dataset_name)
    os.makedirs(path, exist_ok=True)
    return path

def get_dataset_output_dir(dataset_name: str):
    path = os.path.join("output", dataset_name)
    os.makedirs(path, exist_ok=True)
    return path