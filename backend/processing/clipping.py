import xarray as xr
import geopandas as gpd
import regionmask
from shapely.geometry import mapping

COUNTRY_ALIAS = {
    "Timor-Leste": ["Timor Leste", "East Timor"],
}

def resolve_country_names(country_name: str) -> list[str]:
    """
    Return list of possible names to match in shapefile
    """
    names = [country_name]
    if country_name in COUNTRY_ALIAS:
        names.extend(COUNTRY_ALIAS[country_name])
    return names

def prep_for_rio(da: xr.DataArray, lon: str = "longitude", lat: str = "latitude") -> xr.DataArray:
    """
    Prepare DataArray for clipping with rioxarray.
    - Set spatial dimensions (lon, lat)
    - Assign CRS (EPSG:4326)
    """
    da = da.rio.set_spatial_dims(x_dim=lon, y_dim=lat, inplace=False)
    da = da.rio.write_crs("EPSG:4326")
    return da

def clip_to_shape(ds: xr.Dataset | xr.DataArray, shapefile_path: str) -> xr.Dataset | xr.DataArray:
    """
    Clip dataset or dataarray to polygon shapefile.
    - If input is Dataset: clip each variable
    - If input is DataArray: clip directly
    """
    shp = gpd.read_file(shapefile_path).to_crs("EPSG:4326")

    if isinstance(ds, xr.DataArray):
        da_rio = prep_for_rio(ds)
        return da_rio.rio.clip(shp.geometry, shp.crs, drop=True, all_touched=True,).astype("float64")

    else:
        raise TypeError("Input must be xarray.Dataset") 

# def diagnose_clip_issue(da, country_gdf):
#     print("Data CRS:", da.rio.crs)
#     print("Country CRS:", country_gdf.crs)

#     print("Data bounds:", da.rio.bounds())
#     print("Country bounds:", country_gdf.total_bounds)

#     print("Resolution:", da.rio.resolution())
#     print("Country area:", country_gdf.geometry.area.values)
#     print("Geometry valid:", country_gdf.is_valid.values)

import numpy as np
import xarray as xr
import geopandas as gpd
from shapely.geometry import box, Polygon

def get_spatial_weights(da: xr.DataArray, country_geom: Polygon):
    """
    Calculate area weights for each grid cell based on its intersection 
    with the country geometry.
    """
    lon = da.coords['longitude'].values
    lat = da.coords['latitude'].values
    
    # Calculate resolution (assuming regular grid)
    d_lon = abs(lon[1] - lon[0])
    d_lat = abs(lat[1] - lat[0])
    
    # Initialize weight matrix
    weights = np.zeros((len(lat), len(lon)))
    
    # Iterate through each grid cell
    for i, y in enumerate(lat):
        for j, x in enumerate(lon):
            # Define cell bounds (create a square polygon for the pixel)
            cell_poly = box(
                x - d_lon/2, 
                y - d_lat/2, 
                x + d_lon/2, 
                y + d_lat/2
            )
            
            # Check if cell intersects with country
            if cell_poly.intersects(country_geom):
                # Calculate intersection area
                intersected_area = cell_poly.intersection(country_geom).area
                weights[i, j] = intersected_area
                
    return xr.DataArray(weights, coords=[lat, lon], dims=["latitude", "longitude"])

def calc_weighted_mean(da: xr.DataArray, region_name: str, gdf_region: gpd.GeoDataFrame, target_col: str):
    """
    Calculate the area-weighted mean of a DataArray for a specific region.
    Formula: Σ(Value * Area) / Σ(Area)
    """
    try:
        # 1. Strict column checking
        if target_col not in gdf_region.columns:
            raise ValueError(f"Target column '{target_col}' not found in shapefile columns: {list(gdf_region.columns)}")

        region_gdf = gdf_region[gdf_region[target_col] == region_name]
        
        if region_gdf.empty:
            print(f"Region '{region_name}' not found in column '{target_col}'.")
            return None
            
        region_geom = region_gdf.geometry.iloc[0]

        # 2. Get weights (Area of intersection)
        # We only need to calculate weights once for the spatial layout
        weights = get_spatial_weights(da, region_geom)
        
        # 3. Apply formula: (Value * Area) / Total_Area
        # xarray handles broadcasting (Time x Lat x Lon) * (Lat x Lon) automatically
        weighted_sum = (da * weights).sum(dim=['latitude', 'longitude'])
        total_weight = weights.sum()
        
        if total_weight == 0:
            return None
            
        result = weighted_sum / total_weight
        return result

    except Exception as e:
        print(f"Error processing region '{region_name}': {e}")
        return None

def calculate_all_provincial_means(da: xr.DataArray, shapefile_path: str, target_col: str) -> dict:
    """
    Calculate area-weighted means for all provinces (or regions) within a shapefile.
    
    Args:
        da (xr.DataArray): The input climate data array (e.g., precipitation, temperature).
        shapefile_path (str): Path to the regional shapefile.
        target_col (str): The column name in the shapefile containing the region names (e.g., 'PROV_NAMT').
        
    Returns:
        dict: A dictionary mapping region names to their calculated spatial mean DataArray.
    """
    # 1. Load shapefile and ensure correct CRS
    gdf = gpd.read_file(shapefile_path).to_crs("EPSG:4326")
    
    # 2. Verify that the target column exists
    if target_col not in gdf.columns:
        raise ValueError(f"Column '{target_col}' not found in shapefile columns: {list(gdf.columns)}")
        
    provincial_data = {}
    
    # 3. Iterate over each unique region in the shapefile
    unique_regions = gdf[target_col].unique()
    
    for region_name in unique_regions:
        # print(f"Calculating spatial mean for: {region_name}...") # Uncomment for debugging
        
        # Extract the specific region as a new GeoDataFrame
        gdf_region = gdf[gdf[target_col] == region_name]
        
        # Calculate the weighted mean using the existing function
        mean_da = calc_weighted_mean(da, region_name, gdf_region, target_col)
        
        # Store the result if successful
        if mean_da is not None:
            provincial_data[region_name] = mean_da
            
    return provincial_data

# def calculate_provincial_means_regionmask(da: xr.DataArray, gdf: gpd.GeoDataFrame, target_col: str) -> dict:
#     """
#     Calculate spatial mean for all regions using regionmask from an existing GeoDataFrame.
#     Optimized for xarray processing.
    
#     Args:
#         da (xr.DataArray): The input climate data array (must have 'latitude', 'longitude' coords).
#         gdf (gpd.GeoDataFrame): GeoDataFrame containing the polygon boundaries.
#         target_col (str): The column name containing region/province names.
        
#     Returns:
#         dict: A dictionary mapping region names to their calculated spatial mean DataArray (time series).
#     """
    
#     if target_col not in gdf.columns:
#         raise ValueError(f"Column '{target_col}' not found in shapefile.")
        
#     # Create regionmask object from GeoDataFrame
#     # This maps each polygon to an integer index and stores the names
#     regions = regionmask.from_geopandas(gdf, names=target_col)
    
#     # Create a 2D mask array
#     # Each pixel gets an integer ID corresponding to the region it falls into (NaN if outside)
#     mask = regions.mask(da.coords["longitude"], da.coords["latitude"])
    
#     # Group by the mask and calculate the mean
#     # This computes the mean for ALL regions simultaneously over the spatial dimensions
#     # da_grouped = da.groupby(mask).mean(dim=["latitude", "longitude"])
#     da_grouped = da.groupby(mask).mean()
    
#     # Map the results back to a dictionary with region names as keys
#     provincial_data = {}
    
#     # Iterate through the valid region IDs found in the grouped data
#     for region_idx in da_grouped.coords["mask"].values:
#         region_idx = int(region_idx)
#         region_name = regions.names[region_idx]
        
#         # Extract the DataArray (e.g., time series) for this specific region
#         # We drop the 'mask' coordinate as it's no longer needed
#         da_region = da_grouped.sel(mask=region_idx).drop_vars("mask")
        
#         provincial_data[region_name] = da_region
        
#     return provincial_data