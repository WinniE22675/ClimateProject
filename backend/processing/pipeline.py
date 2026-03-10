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
from processing.export_maps import export_trend_map_xesmf, export_actual_maps_xesmf, export_actual_map_shapefile, export_trend_map_shapefile
from processing.export_timeseries import export_yearly_timeseries, export_seasonal_cycle
from processing.overlay import overlay_with_shapefile

from fastapi import HTTPException

SEA_SHAPEFILE_PATH = "data/sea_boundary_dissolved/sea_boundary_dissolved.geojson"

COUNTRY_SHAPEFILE_PATH = "data/sea_boundary/southeast-asia-boundary.shp"
shp_countries = gpd.read_file(COUNTRY_SHAPEFILE_PATH).to_crs("EPSG:4326")

THAILAND_SHAPEFILE_PATH = "data/tha_admbnda_adm1_rtsd_20190221.shp"
shp_thai_provinces = gpd.read_file(THAILAND_SHAPEFILE_PATH).to_crs("EPSG:4326")

THAILAND_PROVINCES_LIST = shp_thai_provinces['ADM1_EN'].dropna().unique()

THAILAND_BOUNDARY_SHAPEFILE_PATH = r"data/geoBoundaries-THA-ADM0.geojson"
shp_thai_boundary = gpd.read_file(THAILAND_BOUNDARY_SHAPEFILE_PATH).to_crs("EPSG:4326")

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
#         # force daily 
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
            clipped_vars[var] = clip_to_shape(da, THAILAND_BOUNDARY_SHAPEFILE_PATH) # SEA_SHAPEFILE_PATH

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

        # try:
        #     shp_sea = gpd.read_file(SEA_SHAPEFILE_PATH).to_crs("EPSG:4326")
        # except Exception as e:
        #     print(f"Warning: Could not load SEA shapefile: {e}")
        #     shp_sea = None
       
        for var in indices_annual.data_vars:
            print(f"Exporting Annual: {var}")
            
            # SEA
            """
            # Maps 
            # send output_base_dir to export_maps and will auto create folder 'actual'/'trend' 
            actual_json_path = export_actual_maps_xesmf(indices_annual[var], var, output_base_dir)
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
                weighted_da = calc_weighted_mean(indices_annual[var], country, shp_countries, target_col="ADMIN") # COUNTRY_SHAPEFILE_PATH
                
                if weighted_da is not None and not weighted_da.isnull().all():
                    export_yearly_timeseries(weighted_da, var, output_base_dir, region_name=country)
                else:
                    print(f"Skipping {country} for {var} (No data coverage)")
            """

            # indices_annual = indices_annual[var].rio.write_crs("EPSG:4326")
            # indices_annual[var]
            current_da = prep_for_rio(indices_annual[var]).load()

            is_spi_event = var.startswith("SPI") and any(evt in var for evt in ["_Drought_", "_Flood_"])
            
            '''
            actual_json_path_overview = export_actual_maps_xesmf(
                index_data=current_da, # indices_annual[var], 
                index_name=var, 
                output_base_dir=output_base_dir,
                region_name="Thailand",
                province_name=None 
            )
            
            
            trend_json_path_overview = export_trend_map_xesmf(
                index_data=current_da, #indices_annual[var], 
                index_name=var, 
                output_base_dir=output_base_dir,
                region_name="Thailand",
                province_name=None
            )

            if shp_thai_provinces is not None:
                overlay_with_shapefile(actual_json_path_overview, shp_thai_boundary)
                overlay_with_shapefile(trend_json_path_overview, shp_thai_boundary)
            '''

            provincial_ts_dict = {}
            '''
            # ==========================================
            # ---> NEW: Shapefile Mode Maps <---
            # Export maps where each province has a single averaged value
            # ==========================================
            if shp_thai_provinces is not None:
                # Actual Map for Shapefile Mode
                actual_shp_path = export_actual_map_shapefile(
                    index_data=current_da,
                    index_name=var,
                    output_base_dir=output_base_dir,
                    region_name="Thailand",
                    gdf_provinces=shp_thai_provinces,
                    target_col="ADM1_EN"
                )
                
                # Trend Map for Shapefile Mode
                trend_shp_path = export_trend_map_shapefile(
                    index_data=current_da,
                    index_name=var,
                    output_base_dir=output_base_dir,
                    region_name="Thailand",
                    gdf_provinces=shp_thai_provinces,
                    target_col="ADM1_EN"
                )
            # ==========================================
            '''
            '''
            if not is_spi_event:
                print(f"Start Timeseries Thailand")
                if shp_thai_boundary is not None:
                    weighted_da_overview = calc_weighted_mean(
                        da=current_da, # indices_annual[var], 
                        region_name="Thailand", 
                        gdf_region=shp_thai_boundary,
                        target_col="shapeName" # Use column name from your geoBoundaries file
                    )

                    if weighted_da_overview is not None and not weighted_da_overview.isnull().all():
                        export_yearly_timeseries(
                            index_data=weighted_da_overview, 
                            index_name=var, 
                            output_base_dir=output_base_dir, 
                            region_name="Thailand", 
                            province_name=None # Will save to 'overview' folder
                        )
                    else:
                        print(f"Skipping Thailand Overview timeseries for {var}")
            '''
            

            
            for province in THAILAND_PROVINCES_LIST:
                print(f"Start {province}")

                province_shp = shp_thai_provinces[shp_thai_provinces['ADM1_EN'] == province]

                try:
                    da_province = current_da.rio.clip( # indices_annual[var].rio.clip(
                        province_shp.geometry.values, 
                        province_shp.crs, 
                        drop=True,
                        all_touched=True,)
                    # print(f"Clip {province}")

                except Exception as e:
                    print(f"Skipping maps for {province} (No data in boundary or clipping error): {e}")
                    da_province = None
                '''
                if da_province is not None:
                    # print(f"Export Actual Map : {province}")
                    
                    actual_json_path = export_actual_maps_xesmf(
                        index_data=da_province, 
                        index_name=var, 
                        output_base_dir=output_base_dir,
                        region_name="Thailand",
                        province_name=province
                    )
                    
                    # print(f"Export Trend Map : {province}")
                    trend_json_path = export_trend_map_xesmf(
                        index_data=da_province, 
                        index_name=var, 
                        output_base_dir=output_base_dir,
                        region_name="Thailand",
                        province_name=province
                    )
                    
                    # Overlay Map 
                    if shp_thai_provinces is not None:
                        overlay_with_shapefile(actual_json_path, province_shp.to_crs("EPSG:4326")) # shp_thai_provinces
                        overlay_with_shapefile(trend_json_path, province_shp.to_crs("EPSG:4326")) # shp_thai_provinces
                '''
                
                if not is_spi_event:
                    # print(f"Calculate Weight Provinces: {var}")
                    weighted_da = calc_weighted_mean(
                        da=current_da, #indices_annual[var], 
                        region_name=province, 
                        gdf_region=shp_thai_provinces,
                        target_col="ADM1_EN" # Change to "ADM1_TH" if you want Thai names
                    )

                    # print(f"Export Timeseries: {var}")
                    if weighted_da is not None and not weighted_da.isnull().all():

                        provincial_ts_dict[province] = weighted_da
                        '''

                        # Export using the province flag to route to the correct folder
                        export_yearly_timeseries(
                            index_data=weighted_da, 
                            index_name=var, 
                            output_base_dir=output_base_dir, 
                            region_name="Thailand", 
                            province_name=province
                        )
                        '''
                    else:
                        print(f"Skipping {province} for {var} (No data coverage or error)")

            # ==========================================
            # ---> NEW: Shapefile Mode Maps <---
            # Pass the dictionary of clipped time-series to export maps.
            # The export functions will calculate Actual and Trend inside.
            # ==========================================
            if shp_thai_provinces is not None and provincial_ts_dict:
                # Actual Map for Shapefile Mode
                actual_shp_path = export_actual_map_shapefile(
                    provincial_ts_dict=provincial_ts_dict,
                    index_name=var,
                    output_base_dir=output_base_dir,
                    gdf_provinces=shp_thai_provinces,
                    target_col="ADM1_EN",
                    region_name="Thailand"
                )
                
                # Trend Map for Shapefile Mode
                trend_shp_path = export_trend_map_shapefile(
                    provincial_ts_dict=provincial_ts_dict,
                    index_name=var,
                    output_base_dir=output_base_dir,
                    gdf_provinces=shp_thai_provinces,
                    target_col="ADM1_EN",
                    region_name="Thailand"
                )
            # ==========================================
                
        # --- Monthly Export ---
        '''
        for var in indices_monthly.data_vars:
            print(f"Exporting monthly: {var}")

            # indices_monthly = indices_monthly[var].rio.write_crs("EPSG:4326")
            # indices_monthly[var]
            current_da = prep_for_rio(indices_monthly[var]).load()

            # SEA
            """
            # SEA Avg
            export_seasonal_cycle(indices_monthly[var], var, output_base_dir, region_name="SEA")
            
            # Country Avg
            for country in SEA_COUNTRIES:
                weighted_da = calc_weighted_mean(indices_monthly[var], country, shp_countries, target_col="ADMIN") # COUNTRY_SHAPEFILE_PATH
                if weighted_da is not None and not weighted_da.isnull().all():
                    export_seasonal_cycle(weighted_da, var, output_base_dir, region_name=country)
            """


            is_spi_event = var.startswith("SPI") and any(evt in var for evt in ["_Drought_", "_Flood_"])
            if is_spi_event:
                print(f"Skipped Seasonal Cycle for {var}")
                continue

            if shp_thai_boundary is not None:
                weighted_da_overview = calc_weighted_mean(
                    da=current_da, #indices_monthly[var], 
                    region_name="Thailand", 
                    gdf_region=shp_thai_boundary,
                    target_col="shapeName" # Use column name from your geoBoundaries file
                )

                if weighted_da_overview is not None and not weighted_da_overview.isnull().all():
                    export_seasonal_cycle(
                        index_data=weighted_da_overview, 
                        index_name=var, 
                        output_base_dir=output_base_dir, 
                        region_name="Thailand", 
                        province_name=None # Will save to 'overview' folder
                    )
                else:
                    print(f"Skipping Thailand Overview seasonal for {var}")

            for province in THAILAND_PROVINCES_LIST:
                weighted_da = calc_weighted_mean(
                    da=current_da, #indices_monthly[var], 
                    region_name=province, 
                    gdf_region=shp_thai_provinces,
                    target_col="ADM1_EN" # Change to "ADM1_TH" if you want Thai names
                )

                if weighted_da is not None and not weighted_da.isnull().all():
                    # Export using the province flag to route to the correct folder
                    export_seasonal_cycle(
                        index_data=weighted_da, 
                        index_name=var, 
                        output_base_dir=output_base_dir, 
                        region_name="Thailand", 
                        province_name=province
                    )
                else:
                    print(f"Skipping {province} for {var} (No data coverage or error)")
        
    
        '''
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

def generate_custom_map_pipeline(
    file_input: str, 
    output_base_dir: str, 
    index_name: str, 
    start_year: int, 
    end_year: int, 
    country: str, 
    province: str, 
    supports_trend: bool, 
    baseline=None
):
    """
    Lightweight pipeline:
    1. Load merged dataset
    2. Clip to boundary
    3. Calculate ONLY the requested index
    4. Export Actual & Trend map for specific year range
    5. Overlay masking for the specific area
    """
    # 1. Load Dataset
    ds = load_dataset(file_input)
    print(f"Dataset loaded for on-demand map: {index_name} ({start_year}-{end_year})")

    try:
        # 2. Clip Dataset to SEA shapefile first to reduce data size before calculation
        clipped_vars = {}
        for var in ds.data_vars:
            da = prep_for_rio(ds[var])
            clipped_vars[var] = clip_to_shape(da, THAILAND_BOUNDARY_SHAPEFILE_PATH)
        ds_clip = xr.Dataset(clipped_vars)

        # 3. Calculate ONLY the specific index requested (saves huge amount of time)
        print(f"Calculating index: {index_name}")
        # Note: We pass [index_name] as the selected_indices list
        indices_annual = calculate_all_indices(ds_clip, "YS", [index_name], baseline)

        if index_name not in indices_annual.data_vars:
            raise ValueError(f"Failed to calculate index {index_name}")

        # index_data = indices_annual[index_name]
        index_data = prep_for_rio(indices_annual[index_name]).load()

        da_target = index_data
        target_shp = shp_thai_boundary # Default to country boundary

        if province and province.strip(): # Check if province is provided and not empty
            if shp_thai_provinces is not None:
                province_shp = shp_thai_provinces[shp_thai_provinces['ADM1_EN'] == province]
                target_shp = province_shp # Update target shape for overlay later
                
                print(f"Clipping data to province: {province}")
                try:
                    # Clip the calculated index to the specific province boundary
                    da_target = index_data.rio.clip(
                        province_shp.geometry.values, 
                        province_shp.crs, 
                        drop=True,
                        all_touched=True
                    )
                except Exception as e:
                    print(f"Skipping maps for {province} (No data in boundary or clipping error): {e}")
                    da_target = None

        if da_target is not None:

        # 4. Export Maps (The export functions handle slicing the data by start_year and end_year)
            actual_json_path = export_actual_maps_xesmf(
                index_data=da_target,
                index_name=index_name,
                output_base_dir=output_base_dir,
                start_year=start_year,
                end_year=end_year,
                region_name=country,
                province_name=province
            )

            trend_json_path = None
            if supports_trend:
                trend_json_path = export_trend_map_xesmf(
                    index_data=da_target,
                    index_name=index_name,
                    output_base_dir=output_base_dir,
                    start_year=start_year,
                    end_year=end_year,
                    region_name=country,
                    province_name=province
                )

        # 5. Overlay Map with Shapefile (Masking)
        if target_shp is not None:
            print("Applying boundary overlay...")
            overlay_with_shapefile(actual_json_path, target_shp)
            if supports_trend and trend_json_path:
                overlay_with_shapefile(trend_json_path, target_shp)

            print(f"On-demand map generation completed for {index_name} in {province if province else country}")
        else:
            raise ValueError(f"No valid data remaining after clipping for {province}")

    except Exception as e:
        print(f"Custom Pipeline Error: {e}")
        raise e
    finally:
        ds.close()
        print("Dataset closed.")