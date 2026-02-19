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

def calc_weighted_mean(da: xr.DataArray, country_name: str, gdf_countries: gpd.GeoDataFrame):
    """
    Calculate the weighted mean of a DataArray for a specific country.
    Formula: Σ(Value * Area) / Σ(Area)
    """
    try:
        # 1. Resolve country geometry
        # Find column dynamically
        target_col = next((c for c in ["ADMIN", "NAME", "NAME_EN"] if c in gdf_countries.columns), None)
        if not target_col:
            raise ValueError("No valid country name column found in shapefile.")

        country_gdf = gdf_countries[gdf_countries[target_col] == country_name]
        if country_gdf.empty:
            return None
            
        country_geom = country_gdf.geometry.iloc[0]

        # 2. Get weights (Area of intersection)
        # We only need to calculate weights once for the spatial layout
        weights = get_spatial_weights(da, country_geom)
        
        # 3. Apply formula: (Value * Area) / Total_Area
        # xarray handles broadcasting (Time x Lat x Lon) * (Lat x Lon) automatically
        weighted_sum = (da * weights).sum(dim=['latitude', 'longitude'])
        total_weight = weights.sum()
        
        if total_weight == 0:
            return None
            
        result = weighted_sum / total_weight
        return result

    except Exception as e:
        print(f"Error processing {country_name}: {e}")
        return None