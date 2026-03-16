import os
import json
import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd
from shapely.geometry import Polygon, mapping
from cf_xarray import vertices_to_bounds

from processing.overlay import overlay_with_shapefile
from processing.clipping import prep_for_rio, calc_weighted_mean ,clip_to_shape

from processing.export_timeseries import export_yearly_timeseries, export_seasonal_cycle
from processing.export_maps import (
    export_actual_maps_xesmf,
    export_trend_map_xesmf,
    export_actual_map_shapefile,
    export_trend_map_shapefile
)

# ============================
# Shapefile Configurations (Adjust paths to match your project)
# ============================
THAILAND_PROVINCES_SHAPEFILE_PATH = "data/tha_admbnda_adm1_rtsd_20190221.shp"
THAILAND_BOUNDARY_SHAPEFILE_PATH = r"data/geoBoundaries-THA-ADM0.geojson"
# THAILAND_BOUNDARY_SHAPEFILE_PATH = "data/shapefiles/thailand_boundary.geojson" 
# THAILAND_PROVINCES_SHAPEFILE_PATH = "data/shapefiles/thailand_provinces.geojson"

# Load Shapefiles safely
try:
    shp_thai_boundary = gpd.read_file(THAILAND_BOUNDARY_SHAPEFILE_PATH).to_crs("EPSG:4326")
    shp_thai_provinces = gpd.read_file(THAILAND_PROVINCES_SHAPEFILE_PATH).to_crs("EPSG:4326")
    THAILAND_PROVINCES_LIST = shp_thai_provinces['ADM1_EN'].unique().tolist()
except Exception as e:
    print(f"[WARNING] Could not load Thailand shapefiles: {e}")
    shp_thai_boundary = None
    shp_thai_provinces = None
    THAILAND_PROVINCES_LIST = []

# SEA_COUNTRIES = [
#     "Thailand",
#     "Vietnam",
#     "Laos",
#     "Cambodia",
#     "Myanmar",
#     "Malaysia",
#     "Indonesia",
#     "Philippines",
#     "Brunei",
#     "Singapore",
#     "Timor-Leste",
# ]

# COUNTRY_SHAPEFILE_PATH = "data/sea_boundary/southeast-asia-boundary.shp"

# SEA_SHAPEFILE_PATH = "data/sea_boundary_dissolved/sea_boundary_dissolved.geojson"
# shp_sea = gpd.read_file(SEA_SHAPEFILE_PATH).to_crs("EPSG:4326")

# shp_countries = gpd.read_file(COUNTRY_SHAPEFILE_PATH).to_crs("EPSG:4326")

def export_preview_all(ds: xr.Dataset, dataset_name: str):
    """
    Generate Maps (Actual & Trend) for Raw Data constrained to Thailand.
    Includes both Grid (GeoJSON) and Shapefile modes.
    """
    output_base_dir = f"output/{dataset_name}"
    os.makedirs(output_base_dir, exist_ok=True)

    for var in ds.data_vars:
        print(f"[Preview] Processing Maps for variable: {var}")
        
        # 1. Prepare data and clip to Thailand bounding box to reduce size
        da = prep_for_rio(ds[var])
        
        try:
            print(f"[Preview] Clipping {var} to Thailand boundary...")
            da = clip_to_shape(da, THAILAND_BOUNDARY_SHAPEFILE_PATH)
        except Exception as e:
            print(f"[WARNING] Failed to clip base data to Thailand boundary: {e}")

        # 2. OPTIMIZATION: Resample to Annual data before generating maps/trends.
        # Running Mann-Kendall on daily/monthly data takes too long.
        print(f"[Preview] Resampling {var} to Annual for map generation...")
        if var == "pr":
            # Precipitation should ideally be summed yearly, but mean is also used for rates
            da_annual = da.resample(time="YS").sum(skipna=True) 
        else:
            # Temperatures (tmax, tmin) are averaged
            da_annual = da.resample(time="YS").mean(skipna=True)
            
        da_annual = da_annual.load() # Load into memory for faster processing

        print(f"[Preview] Resampling {var} to Monthly for seasonal cycle...")
        if var == "pr":
            da_monthly = da.resample(time="MS").sum(skipna=True)
        else:
            da_monthly = da.resample(time="MS").mean(skipna=True)
            
        da_monthly = da_monthly.load()

        # ==========================================
        # 3. Grid Maps (Overview Mode - Thailand)
        # ==========================================
        print(f"[Preview] Generating Grid Maps for {var}...")
        try:
            actual_json_path_overview = export_actual_maps_xesmf(
                index_data=da_annual, 
                index_name=var, 
                output_base_dir=output_base_dir,
                region_name="Thailand",
                province_name=None 
            )
            
            trend_json_path_overview = export_trend_map_xesmf(
                index_data=da_annual, 
                index_name=var, 
                output_base_dir=output_base_dir,
                region_name="Thailand",
                province_name=None
            )
            
            # Optional: Overlay shapefile boundary on grid maps
            if shp_thai_boundary is not None:
                overlay_with_shapefile(actual_json_path_overview, shp_thai_boundary)
                overlay_with_shapefile(trend_json_path_overview, shp_thai_boundary)
                
        except Exception as e:
            print(f"[ERROR] Failed generating Grid maps for {var}: {e}")

        if shp_thai_boundary is not None:
            # Annual Timeseries Overview
            weighted_annual_overview = calc_weighted_mean(da_annual, "Thailand", shp_thai_boundary, "shapeName")
            if weighted_annual_overview is not None:
                export_yearly_timeseries(
                    index_data=weighted_annual_overview, 
                    index_name=var, 
                    output_base_dir=output_base_dir, 
                    region_name="Thailand", 
                    province_name=None
                )
            
            # Seasonal Cycle Overview
            weighted_monthly_overview = calc_weighted_mean(da_monthly, "Thailand", shp_thai_boundary, "shapeName")
            if weighted_monthly_overview is not None:
                export_seasonal_cycle(
                    index_data=weighted_monthly_overview, 
                    index_name=var, 
                    output_base_dir=output_base_dir, 
                    region_name="Thailand", 
                    province_name=None
                )


        # ==========================================
        # 4. Shapefile Mode & Provincial Data
        # ==========================================
        if shp_thai_provinces is not None:
            print(f"[Preview] Extracting Provincial Data for Shapefile Maps...")
            provincial_ts_dict = {}
            
            for province in THAILAND_PROVINCES_LIST:
                # Calculate spatial average for each province over time
                weighted_da = calc_weighted_mean(
                    da=da_annual, 
                    region_name=province, 
                    gdf_region=shp_thai_provinces,
                    target_col="ADM1_EN" 
                )

                if weighted_da is not None and not weighted_da.isnull().all():
                    provincial_ts_dict[province] = weighted_da
                
                weighted_monthly_prov = calc_weighted_mean(
                    da=da_monthly, 
                    region_name=province, 
                    gdf_region=shp_thai_provinces,
                    target_col="ADM1_EN"
                )

                # ADD THIS: Export Timeseries & Seasonal for Province
                if province in provincial_ts_dict: # If annual data exists
                    export_yearly_timeseries(
                        index_data=provincial_ts_dict[province], 
                        index_name=var, 
                        output_base_dir=output_base_dir, 
                        region_name="Thailand", 
                        province_name=province
                    )
                
                if weighted_monthly_prov is not None and not weighted_monthly_prov.isnull().all():
                    export_seasonal_cycle(
                        index_data=weighted_monthly_prov, 
                        index_name=var, 
                        output_base_dir=output_base_dir, 
                        region_name="Thailand", 
                        province_name=province
                    )

            # Generate Shapefile Actual & Trend Maps
            if provincial_ts_dict:
                print(f"[Preview] Generating Shapefile Maps for {var}...")
                try:
                    export_actual_map_shapefile(
                        provincial_ts_dict=provincial_ts_dict,
                        index_name=var,
                        output_base_dir=output_base_dir,
                        gdf_provinces=shp_thai_provinces,
                        target_col="ADM1_EN",
                        region_name="Thailand"
                    )
                    
                    export_trend_map_shapefile(
                        provincial_ts_dict=provincial_ts_dict,
                        index_name=var,
                        output_base_dir=output_base_dir,
                        gdf_provinces=shp_thai_provinces,
                        target_col="ADM1_EN",
                        region_name="Thailand"
                    )
                except Exception as e:
                     print(f"[ERROR] Failed generating Shapefile maps for {var}: {e}")

    print(f"[Preview] All preview generation completed for {dataset_name}")
    return {"status": "success"}