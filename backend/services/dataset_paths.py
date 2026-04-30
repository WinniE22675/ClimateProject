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

def get_user_shapefile_dir(user_id: str):
    # Path: uploads/user_{user_id}/shapefiles
    path = os.path.join(UPLOAD_BASE, f"user_{user_id}", "shapefiles")
    os.makedirs(path, exist_ok=True)
    return path

def get_global_shapefile_dir():
    # Path: data/shapefiles
    path = os.path.join("data", "shapefiles")
    os.makedirs(path, exist_ok=True)
    return path

# Helper Function for Shapefile Path
def get_shapefile_path(user_id: str, shapefile_name: str) -> str:
    """Helper function to locate the actual .shp file path."""
    user_shape_dir = get_user_shapefile_dir(user_id)
    target_dir = os.path.join(user_shape_dir, shapefile_name)
    
    # Fallback: Check global directory
    if not os.path.exists(target_dir):
        global_shape_dir = get_global_shapefile_dir()
        target_dir = os.path.join(global_shape_dir, shapefile_name)
        if not os.path.exists(target_dir):
            raise Exception(f"Shapefile '{shapefile_name}' directory not found")
            
    # shp_files = [f for f in os.listdir(target_dir) if f.lower().endswith('.shp')]
    valid_files = [f for f in os.listdir(target_dir) if f.lower().endswith(('.shp', '.geojson'))]

    if not valid_files:
        raise Exception("No .shp file found inside the directory")
        
    return os.path.join(target_dir, valid_files[0])