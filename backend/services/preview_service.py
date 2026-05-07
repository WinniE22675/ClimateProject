import xarray as xr

from services.dataset_paths import *
from processing.export_preview import export_preview_all
from services.dataset_metadata import read_metadata_json

def run_preview_visualization(dataset_name: str, user_id: str, country_name: str):
    """
    Background preview job (slow)
    """
    try:
        output_base_dir = get_dataset_output_dir(dataset_name)
        
        # CHECK: Skip if previews already exist
        # Assuming 'pr', 'tmax', or 'tmin' are the raw variables.
        # We check if a directory for one of them exists to avoid re-running.
        raw_vars = ["pr", "tmax", "tmin"] # , "tas"
        # already_generated = any(os.path.exists(os.path.join(output_base_dir, country_name, "overview", v)) for v in raw_vars for country_name in os.listdir(output_base_dir) if os.path.isdir(os.path.join(output_base_dir, country_name)))
        
        # A simpler check: Just look if ANY variable folder exists directly inside the country folder
        # For a more robust check, we can just look for the "overview" folder of raw variables.
        # metadata = read_metadata_json(dataset_name)
        # country_name = metadata.get("country", "custom_workspace")

        preview_check_path = os.path.join(output_base_dir, country_name, "overview")
        if os.path.exists(preview_check_path):
            # Check if any raw var is in the overview folder
            if any(os.path.exists(os.path.join(preview_check_path, v)) for v in raw_vars):
                print(f"[PREVIEW] Previews for {dataset_name} ({country_name}) already exist. Skipping.")
                return
        
        print(f"[PREVIEW] Start preview generation for {dataset_name} - Workspace: {country_name}")
        merged_path = os.path.join(
            get_dataset_output_dir(dataset_name),
            "merged.nc",
        )

        if not os.path.exists(merged_path):
            raise FileNotFoundError(f"Merged file not found: {merged_path}")

        metadata = read_metadata_json(dataset_name)
        workspaces = metadata.get("workspaces", {})
        current_workspace = workspaces.get(country_name, {})

        # shapefile_name = metadata.get("shapefile_name")
        # target_col = metadata.get("target_col")
        shapefile_name = current_workspace.get("shapefile_name")
        target_col = current_workspace.get("target_col")

        # Fallback for older datasets without shapefile metadata
        if not shapefile_name or not target_col:
            print(f"[PREVIEW] No shapefile metadata found for workspace '{country_name}'. Preview skipped.")
            return

        shapefile_path = get_shapefile_path(user_id, shapefile_name)

        print(f"[PREVIEW] Loading {merged_path}")

        # ds = xr.open_dataset(merged_path)
        with xr.open_dataset(merged_path) as ds:
            export_preview_all(
                ds=ds,
                dataset_name=dataset_name,
                shapefile_path=shapefile_path, 
                target_col=target_col,
                country_name=country_name
            )

        print(f"[PREVIEW] Completed preview for {dataset_name} ({country_name})")
        print(f"[PREVIEW] Variables: {list(ds.data_vars)}")
    except Exception as e:
        print(f"[PREVIEW][ERROR] {dataset_name}: {e}")