import os
import json
import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd

from processing.overlay import overlay_with_shapefile
from processing.clipping import prep_for_rio, calc_weighted_mean ,clip_to_shape

from processing.export_timeseries import export_yearly_timeseries, export_seasonal_cycle
from processing.export_maps import (
    export_actual_maps_xesmf,
    export_actual_map_shapefile,
)

def export_preview_all(
    ds: xr.Dataset,
    dataset_name: str,
    shapefile_path: str = None, 
    target_col: str = None,
    country_name: str = "custom_workspace"
    ):
    """
    Generate Maps Actual for Raw Data constrained to Thailand.
    Includes both Grid (GeoJSON) and Shapefile modes.
    """
    output_base_dir = f"output/{dataset_name}"
    os.makedirs(output_base_dir, exist_ok=True)

    if not shapefile_path or not os.path.exists(shapefile_path):
        print("[Preview] Shapefile missing. Aborting preview generation.")
        return

    print(f"[Preview] Loading dynamic shapefile for preview: {shapefile_path}")
    shp_areas = gpd.read_file(shapefile_path).to_crs("EPSG:4326")

    area_list = shp_areas[target_col].dropna().unique().tolist()
    
    shp_boundary = shp_areas.dissolve()
    shp_boundary['overview_col'] = 'overview_area'

    for var in ds.data_vars:
        print(f"[Preview] Processing Maps for variable: {var}")
        
        # Prepare data and clip to Thailand bounding box to reduce size
        da = prep_for_rio(ds[var])
        
        try:
            print(f"[Preview] Clipping {var} to Thailand boundary...")
            da = clip_to_shape(da, shp_boundary) # THAILAND_BOUNDARY_SHAPEFILE_PATH
        except Exception as e:
            print(f"[WARNING] Failed to clip base data to Thailand boundary: {e}")

        # Resample to Annual data before generating maps.
        # Running Mann-Kendall on daily/monthly data takes too long.
        print(f"[Preview] Resampling {var} to Annual for map generation...")
        if var == "pr":
            # Precipitation should ideally be summed yearly, but mean is also used for rates
            da_annual = da.resample(time="YS").sum(skipna=True) 
        else:
            # Temperatures (tmax, tmin) are averaged
            da_annual = da.resample(time="YS").mean(skipna=True)

        da_annual.attrs = da.attrs.copy()
        if da.rio.crs is not None:
             da_annual = da_annual.rio.write_crs(da.rio.crs)
            
        da_annual = da_annual.load() # Load into memory for faster processing

        print(f"[Preview] Resampling {var} to Monthly for seasonal cycle...")
        if var == "pr":
            da_monthly = da.resample(time="MS").sum(skipna=True)
        else:
            da_monthly = da.resample(time="MS").mean(skipna=True)

        da_monthly.attrs = da.attrs.copy()
        if da.rio.crs is not None:
             da_monthly = da_monthly.rio.write_crs(da.rio.crs)
            
        da_monthly = da_monthly.load()

        # ==========================================
        # Grid Maps (Overview Mode - Thailand)
        # ==========================================
        print(f"[Preview] Generating Grid Maps for {var}...")
        try:
            actual_json_path_overview = export_actual_maps_xesmf(
                index_data=da_annual, 
                index_name=var, 
                output_base_dir=output_base_dir,
                region_name=country_name,
                province_name=None 
            )
            
            # Optional: Overlay shapefile boundary on grid maps
            if shp_boundary is not None: 
                overlay_with_shapefile(actual_json_path_overview, shp_boundary) 
                
        except Exception as e:
            print(f"[ERROR] Failed generating Grid maps for {var}: {e}")

        if shp_boundary is not None: 
            # Annual Timeseries Overview
            weighted_annual_overview = calc_weighted_mean(da_annual, "overview_area", shp_boundary, "overview_col")
            if weighted_annual_overview is not None:
                export_yearly_timeseries(
                    index_data=weighted_annual_overview, 
                    index_name=var, 
                    output_base_dir=output_base_dir, 
                    region_name=country_name,  
                    province_name=None
                )
            
            # Seasonal Cycle Overview
            weighted_monthly_overview = calc_weighted_mean(da_monthly, "overview_area", shp_boundary, "overview_col")
            if weighted_monthly_overview is not None:
                export_seasonal_cycle(
                    index_data=weighted_monthly_overview, 
                    index_name=var, 
                    output_base_dir=output_base_dir, 
                    region_name=country_name, 
                    province_name=None
                )

        # ==========================================
        # 4. Shapefile Mode & Provincial Data
        # ==========================================
        if shp_areas is not None: 
            print(f"[Preview] Extracting Provincial Data for Shapefile Maps...")
            provincial_ts_dict = {}
            
            for province in area_list: 
                # Calculate spatial average for each province over time
                weighted_da = calc_weighted_mean(
                    da=da_annual, 
                    region_name=province, 
                    gdf_region=shp_areas, 
                    target_col=target_col 
                )

                if weighted_da is not None and not weighted_da.isnull().all():
                    provincial_ts_dict[province] = weighted_da
                
                weighted_monthly_prov = calc_weighted_mean(
                    da=da_monthly, 
                    region_name=province, 
                    gdf_region=shp_areas, 
                    target_col=target_col 
                )

                # ADD THIS: Export Timeseries & Seasonal for Province
                if province in provincial_ts_dict: # If annual data exists
                    export_yearly_timeseries(
                        index_data=provincial_ts_dict[province], 
                        index_name=var, 
                        output_base_dir=output_base_dir, 
                        region_name=country_name, 
                        province_name=province
                    )
                
                if weighted_monthly_prov is not None and not weighted_monthly_prov.isnull().all():
                    export_seasonal_cycle(
                        index_data=weighted_monthly_prov, 
                        index_name=var, 
                        output_base_dir=output_base_dir, 
                        region_name=country_name, 
                        province_name=province
                    )

            # Generate Shapefile Actual Maps
            if provincial_ts_dict:
                print(f"[Preview] Generating Shapefile Maps for {var}...")
                try:
                    export_actual_map_shapefile(
                        provincial_ts_dict=provincial_ts_dict,
                        index_name=var,
                        output_base_dir=output_base_dir,
                        gdf_provinces=shp_areas, 
                        target_col=target_col, 
                        region_name=country_name 
                    )
                    
                except Exception as e:
                     print(f"[ERROR] Failed generating Shapefile maps for {var}: {e}")

    print(f"[Preview] All preview generation completed for {dataset_name}")
    return {"status": "success"}