import xarray as xr

from services.dataset_paths import *
from processing.export_preview import export_preview_all

def run_preview_visualization(dataset_name: str):
    """
    Background preview job (slow)
    """
    try:
        print(f"[PREVIEW] Start preview generation for {dataset_name}")
        merged_path = os.path.join(
            get_dataset_output_dir(dataset_name),
            "merged.nc",
        )
        if not os.path.exists(merged_path):
            raise FileNotFoundError(f"Merged file not found: {merged_path}")
        print(f"[PREVIEW] Loading {merged_path}")

        # ds = xr.open_dataset(merged_path)
        with xr.open_dataset(merged_path) as ds:
            export_preview_all(
                ds=ds,
                dataset_name=dataset_name,
            )

        print(f"[PREVIEW] Completed preview for {dataset_name}")
        print(f"[PREVIEW] Variables: {list(ds.data_vars)}")
    except Exception as e:
        print(f"[PREVIEW][ERROR] {dataset_name}: {e}")