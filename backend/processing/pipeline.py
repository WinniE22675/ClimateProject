# import os
# import xarray as xr
# import geopandas as gpd
# from processing.preprocessing import load_dataset
# from processing.clipping import prep_for_rio, clip_to_shape
# from processing.indices import calculate_all_indices
# from processing.export_maps import export_trend_map_xesmf, export_actual_maps_xesmf
# from processing.export_timeseries import export_yearly_timeseries, export_monthly_series

# # ---- Load shapefile Thailand ----
# geojson_path = r"data/geoBoundaries-THA-ADM0.geojson"
# shp_country = gpd.read_file(geojson_path).to_crs("EPSG:4326")

# def overlay_with_shapefile(input_path: str, shapefile: gpd.GeoDataFrame):
#     """
#     overlay between GeoJSON with shapefile
#     """
#     if not os.path.exists(input_path):
#         print(f"File not found: {input_path}")
#         return

#     try:
#         gdf = gpd.read_file(input_path)
#         gdf = gdf.to_crs("EPSG:4326")
#         clipped = gpd.overlay(gdf, shapefile, how="intersection")
#         clipped.to_file(input_path, driver="GeoJSON")
#         print(f"Overlay applied to {input_path}")
#     except Exception as e:
#         print(f"Failed overlay for {input_path}: {e}")

# def generate_all(file_input, shapefile_path):
#     """
#     Main pipeline:
#     1. Load dataset
#     2. Preprocess 
#     3. Clip to Thailand
#     4. Calculate indices
#     5. Export results
#     """

#     # 1. Load
#     # already one file with multiple variables
#     ds = load_dataset(file_input)

#     print("Dataset")

#     # 2. Clip
#     clipped_vars = {}
#     for var in ds.data_vars:
#         da = prep_for_rio(ds[var])
#         clipped_vars[var] = clip_to_shape(da, shapefile_path)

#     ds_clip = xr.Dataset(clipped_vars)

#     print("Clip")

#     # 3. Indices
#     indices_annual = calculate_all_indices(ds_clip, "YS")
#     indices_monthly = calculate_all_indices(ds_clip, "MS")

#     print(indices_annual.data_vars)
#     print(indices_monthly.data_vars)

#     print("Indices")

#     for var in indices_annual.data_vars:
#         print("Exporting:", var)
#         export_yearly_timeseries(indices_annual[var], var)
#         export_actual_maps_xesmf(indices_annual[var], var)
#         export_trend_map_xesmf(indices_annual[var], var)

#         # === Overlay ===
#         actual_path = fr"output/maps_grid/actual/{var}_actual_grid.geojson"
#         trend_path = fr"output/maps_grid/trend/{var}_trend_grid.geojson"

#         overlay_with_shapefile(actual_path, shp_country)
#         overlay_with_shapefile(trend_path, shp_country)

#     for var in indices_monthly.data_vars:
#         export_monthly_series(indices_monthly[var], var)

#     return
# # {
# #   "indices": {
# #     "annual": "/output/indices/annual/",
# #     "monthly": "/output/indices/monthly/"
# #   },
# #   "maps": {
# #     "actual": "/output/maps/actual/",
# #     "trend": "/output/maps/trend/"
# #   }
# # }



# def clear_upload_folder(file_path=r"D:\Students\YearFour\Project\ClimateRiskMap\ClimReact\my-app\backend\upload"):

#     if os.path.isdir(file_path):  
#         for f in os.listdir(file_path):
#             file_to_remove = os.path.join(file_path, f)
#             if os.path.isfile(file_to_remove):  
#                 try:
#                     os.remove(file_to_remove)
#                     print(f"Removed: {file_to_remove}")
#                 except Exception as e:
#                     print(f"Error removing {file_to_remove}: {e}")


# def main_pipeline(file_path):
#     shapefile_path = "data/tha_admbnda_adm1_rtsd_20190221.shp"
#     # file_path = "upload/"
    
#     print("Start Calculate")

#     result = generate_all(file_path, shapefile_path)

#     # print(indices_annual, indices_monthly)

#     clear_upload_folder(file_path)

#     print("Clear path")

#     return result

# if __name__ == "__main__":
#     main_pipeline(file_path="upload/")


import os
import xarray as xr
import geopandas as gpd
from processing.preprocessing import load_dataset
from processing.clipping import prep_for_rio, clip_to_shape, calc_weighted_mean
from processing.indices import calculate_all_indices
from processing.export_maps import export_trend_map_xesmf, export_actual_maps_xesmf
from processing.export_timeseries import export_yearly_timeseries, export_seasonal_cycle
from processing.overlay import overlay_with_shapefile

from fastapi import HTTPException

SEA_SHAPEFILE_PATH = "data/sea_boundary_dissolved/sea_boundary_dissolved.geojson"

COUNTRY_SHAPEFILE_PATH = "data/sea_boundary/southeast-asia-boundary.shp"
shp_countries = gpd.read_file(COUNTRY_SHAPEFILE_PATH).to_crs("EPSG:4326")

SEA_COUNTRIES = [
    "Thailand", 
    "Vietnam", 
    "Laos", 
    "Cambodia", 
    "Myanmar", 
    "Malaysia", 
    "Indonesia", 
    "Philippines", 
    "Brunei", 
    "Singapore", 
    "Timor-Leste"
]

# ---- Load shapefile Thailand ----
# geojson_path = r"data/geoBoundaries-THA-ADM0.geojson"
# shp_country = gpd.read_file(geojson_path).to_crs("EPSG:4326")

# def overlay_with_shapefile(input_path: str, shapefile: gpd.GeoDataFrame):
#     """
#     overlay between GeoJSON with shapefile
#     """
#     if not os.path.exists(input_path):
#         print(f"File not found: {input_path}")
#         return

#     try:
#         gdf = gpd.read_file(input_path)
#         gdf = gdf.to_crs("EPSG:4326")
#         clipped = gpd.overlay(gdf, shapefile, how="intersection")
#         clipped.to_file(input_path, driver="GeoJSON")
#         print(f"Overlay applied to {input_path}")
#     except Exception as e:
#         print(f"Failed overlay for {input_path}: {e}")
def clear_upload_folder(file_path=r"D:\Students\YearFour\Project\ClimateRiskMap\ClimReact\my-app\backend\uploads\merged"):
# def clear_upload_folder(file_path=r"D:\WinnieWork\SubProject\Project\ClimateProject\ClimReact\my-app\backend\uploads\merged"):

    if os.path.isdir(file_path):  
        for f in os.listdir(file_path):
            file_to_remove = os.path.join(file_path, f)
            if os.path.isfile(file_to_remove):  
                try:
                    os.remove(file_to_remove)
                    print(f"Removed: {file_to_remove}")
                except Exception as e:
                    print(f"Error removing {file_to_remove}: {e}")


# import pandas as pd
# def prepare_for_xclim(ds: xr.Dataset) -> xr.Dataset:
#     time = ds.time.to_index()

#     inferred = pd.infer_freq(time)
#     if inferred is None:
#         # บังคับ daily (สำหรับ CMIP6 daily)
#         ds = ds.assign_coords(
#             time=pd.date_range(
#                 start=str(time[0]),
#                 periods=len(time),
#                 freq="D",
#             )
#         )

#     return ds


def generate_all(file_input, selected_indices, dataset_name, baseline=None):
    """
    Main pipeline:
    1. Load dataset
    2. Preprocess 
    3. Clip to Thailand
    4. Calculate indices
    5. Export results
    """
    output_base_dir = f"output/{dataset_name}"
    os.makedirs(output_base_dir, exist_ok=True)

    # 1. Load
    # already one file with multiple variables
    ds = load_dataset(file_input)

    print("Dataset loaded.")

    try:
        # 2. Clip
        clipped_vars = {}
        for var in ds.data_vars:
            da = prep_for_rio(ds[var])
            clipped_vars[var] = clip_to_shape(da, SEA_SHAPEFILE_PATH)

        ds_clip = xr.Dataset(clipped_vars)
        print("Clipped to SEA boundary.")
        # ds_clip = prepare_for_xclim(ds_clip)

        # 3. Indices
        print("Calculate Indices.")
        try:
            indices_annual = calculate_all_indices(ds_clip, "YS", selected_indices, baseline)
            indices_monthly = calculate_all_indices(ds_clip, "MS", selected_indices, baseline)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Calculation error: {str(e)}")
        
        # print("Calculated annual:", list(indices_annual.data_vars))
        # print("Calculated monthly:", list(indices_monthly.data_vars))

        try:
            shp_sea = gpd.read_file(SEA_SHAPEFILE_PATH).to_crs("EPSG:4326")
        except Exception as e:
            print(f"Warning: Could not load SEA shapefile: {e}")
            shp_sea = None

        for var in indices_annual.data_vars:
            print(f"Exporting Annual: {var}")
            
            # Maps 
            # send output_base_dir to export_maps and will auto create folder 'actual'/'trend' 
            actual_json_path = export_actual_maps_xesmf(indices_annual[var], var, output_base_dir)
            print("finish export map")
            trend_json_path = export_trend_map_xesmf(indices_annual[var], var, output_base_dir)
            
            # Overlay Map 
            if shp_sea is not None:
                overlay_with_shapefile(actual_json_path, shp_sea)
                overlay_with_shapefile(trend_json_path, shp_sea)

            # Timeseries (each counrty)
            # 1. SEA Average 
            export_yearly_timeseries(indices_annual[var], var, output_base_dir, region_name="SEA")
            
            # 2. Country-specific Average
            for country in SEA_COUNTRIES:
                # Mask only counrty
                weighted_da = calc_weighted_mean(indices_annual[var], country, shp_countries) # COUNTRY_SHAPEFILE_PATH
                
                if weighted_da is not None and not weighted_da.isnull().all():
                    export_yearly_timeseries(weighted_da, var, output_base_dir, region_name=country)
                else:
                    print(f"Skipping {country} for {var} (No data coverage)")

        # --- Monthly Export ---
        for var in indices_monthly.data_vars:
            print(f"Exporting monthly: {var}")
            # SEA Avg
            export_seasonal_cycle(indices_monthly[var], var, output_base_dir, region_name="SEA")
            
            # Country Avg
            for country in SEA_COUNTRIES:
                weighted_da = calc_weighted_mean(indices_monthly[var], country, shp_countries) # COUNTRY_SHAPEFILE_PATH
                if weighted_da is not None and not weighted_da.isnull().all():
                    export_seasonal_cycle(weighted_da, var, output_base_dir, region_name=country)
    
    except Exception as e:
        print(f"Pipeline Error: {e}")
        raise e
        # for var in indices_annual.data_vars:
        #     print("Exporting:", var)
        #     export_yearly_timeseries(indices_annual[var], var)
        #     export_actual_maps_xesmf(indices_annual[var], var)
        #     export_trend_map_xesmf(indices_annual[var], var)

        #     # === Overlay ===
        #     actual_path = fr"output/maps_grid/actual/{var}_actual_grid.geojson"
        #     trend_path = fr"output/maps_grid/trend/{var}_trend_grid.geojson"

        #     overlay_with_shapefile(actual_path, shp_country)
        #     overlay_with_shapefile(trend_path, shp_country)

        # for var in indices_monthly.data_vars:
        #     export_monthly_series(indices_monthly[var], var)

    finally:
        ds.close() 
        print("Dataset closed.")
        # clear_upload_folder() # ย้ายมาลบตรงนี้ หลังจากปิดไฟล์แล้ว





# def main_pipeline(file_path):
#     shapefile_path = "data/tha_admbnda_adm1_rtsd_20190221.shp"
#     # file_path = "upload/"
    
#     print("Start Calculate")

#     result = generate_all(file_path, shapefile_path)

#     # print(indices_annual, indices_monthly)

#     clear_upload_folder(file_path)

#     print("Clear path")

#     return result

# if __name__ == "__main__":
#     main_pipeline(file_path="upload/")
