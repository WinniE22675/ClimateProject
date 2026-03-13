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
            # indices_annual = calculate_all_indices(ds_clip, "YS", selected_indices, baseline)
            # indices_monthly = calculate_all_indices(ds_clip, "MS", selected_indices, baseline)

            # 1. Calculate EVERYTHING in the annual pass (SPI will use 'MS' internally)
            indices_annual = calculate_all_indices(ds_clip, "YS", selected_indices, baseline)
            
            # 2. Filter out all SPI-related variables to PREVENT duplicate calculation in the monthly pass
            if selected_indices is not None:
                # User specified indices: keep only non-SPI
                monthly_selected = [idx for idx in selected_indices if not str(idx).startswith("SPI")]
            else:
                # Calculate all: get all non-SPI keys from the annual dataset
                monthly_selected = [str(var) for var in indices_annual.data_vars if not str(var).startswith("SPI")]

            # 3. Calculate Monthly ONLY for Non-SPI variables
            indices_monthly = calculate_all_indices(ds_clip, "MS", monthly_selected, baseline)
            
            # 4. Inject the pre-calculated SPI variables from annual back into monthly
            # This ensures the "--- Monthly Export ---" loop below has the SPI data it needs
            for var in indices_annual.data_vars:
                if str(var).startswith("SPI"):
                    # This is just a memory pointer, doesn't duplicate RAM
                    indices_monthly[var] = indices_annual[var]
                    
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

            current_da = prep_for_rio(indices_annual[var]).load()

            is_spi_event = var.startswith("SPI") and any(evt in var for evt in ["_Drought_", "_Flood_"])
            
            # '''
            # Actual and Trend Maps Overview
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
            # '''

            provincial_ts_dict = {}
            
            # '''
            # Annual Timeseries Overview
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
            # '''

            # '''
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
                # """
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
                # """
                
                
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
                    # """
                    if not is_spi_event:
                        # Export using the province flag to route to the correct folder
                        export_yearly_timeseries(
                            index_data=weighted_da, 
                            index_name=var, 
                            output_base_dir=output_base_dir, 
                            region_name="Thailand", 
                            province_name=province
                        )
                    # """
                else:
                    print(f"Skipping {province} for {var} (No data coverage or error)")
            # '''
            # '''

            #  Shapefile Mode Maps Overview
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
            # '''
        # --- Monthly Export ---
        # '''
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

            # Seasonal Cycle Overview
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
            
            if is_spi_event:
                # Actual and Trend Maps Overview
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
        
    
        # '''
    except Exception as e:
        print(f"Pipeline Error: {e}")
        raise e

    finally:
        ds.close() 
        print("Dataset closed.")

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
    
    # 0. Check existing files 
    area_name = province if province and province.strip() else "overview"

    # Define paths to check if files already exist
    grid_file = os.path.join(output_base_dir, country, area_name, index_name, "maps_grid", "actual", f"{start_year}_{end_year}_actual_grid.geojson")
    # shp_file = os.path.join(output_base_dir, country, area_name, index_name, "maps_shp", "actual", f"{start_year}_{end_year}_actual_shp.geojson")

    if not province: # <-- if it is Overview
        shp_file = os.path.join(output_base_dir, country, "overview", index_name, "maps_shp", "actual", f"{start_year}_{end_year}_actual_shp.geojson")
        need_shp = not os.path.exists(shp_file)
    else:
        need_shp = False # <-- if select province don't do Shapefile mode map

    need_grid = not os.path.exists(grid_file)
    # need_shp = not os.path.exists(shp_file)

    # If both files already exist, exit early to save CPU time
    if not need_grid and not need_shp:
        print(f"Maps already exist for {index_name} ({start_year}-{end_year}). Skipping computation.")
        return

    # 1. Load Dataset
    ds = load_dataset(file_input)
    print(f"Dataset loaded for on-demand map: {index_name} ({start_year}-{end_year})")

    try:
        # 2. Clip Dataset to boundary 
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

            da_target_sliced = da_target.sel(time=slice(str(start_year), str(end_year)))
            # ====================================================
            # 4.1 Export Grid Maps (Only if missing)
            # ====================================================
            if need_grid:
                print("Generating Grid Maps...")
                # 4. Export Maps (The export functions handle slicing the data by start_year and end_year)
                actual_json_path = export_actual_maps_xesmf(
                    index_data=da_target_sliced,
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
                        index_data=da_target_sliced,
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

            if need_shp:
                print("Generating Shapefile Maps...")
                provincial_ts_dict = {}

                # Calculate weight for ALL provinces (Whole Country mode)
                for prov in THAILAND_PROVINCES_LIST:
                    weighted_da = calc_weighted_mean(da_target_sliced, prov, shp_thai_provinces, "ADM1_EN")
                    if weighted_da is not None:
                        provincial_ts_dict[prov] = weighted_da

                if provincial_ts_dict:
                    # Export actual shapefile map
                    export_actual_map_shapefile(
                        provincial_ts_dict=provincial_ts_dict,
                        index_name=index_name,
                        output_base_dir=output_base_dir,
                        gdf_provinces=shp_thai_provinces,
                        target_col="ADM1_EN",
                        region_name=country,
                        start_year=start_year, # Requires function modification (see note below)
                        end_year=end_year      # Requires function modification (see note below)
                    )
                    
                    if supports_trend:
                        # Export trend shapefile map
                        export_trend_map_shapefile(
                            provincial_ts_dict=provincial_ts_dict,
                            index_name=index_name,
                            output_base_dir=output_base_dir,
                            gdf_provinces=shp_thai_provinces,
                            target_col="ADM1_EN",
                            region_name=country,
                            start_year=start_year, 
                            end_year=end_year      
                        )

            print(f"On-demand map generation completed for {index_name} in {province if province else country}")
        else:
            raise ValueError(f"No valid data remaining after clipping for {province}")

    except Exception as e:
        print(f"Custom Pipeline Error: {e}")
        raise e
    finally:
        ds.close()
        print("Dataset closed.")