import os
import json
import numpy as np
import xarray as xr
from shapely.geometry import Polygon
from cf_xarray import vertices_to_bounds
import pymannkendall as mk
# import regionmask
import geopandas as gpd

# ========== helper functions ==========

LON_CF_ATTRS = {"standard_name": "longitude", "units": "degrees_east"}
LAT_CF_ATTRS = {"standard_name": "latitude", "units": "degrees_north"}


def _grid_1d(start_b, end_b, step):
    bounds = np.arange(start_b, end_b + step / 2, step)
    centers = (bounds[:-1] + bounds[1:]) / 2
    return centers, bounds


def cf_grid_2d(lon0_b, lon1_b, d_lon, lat0_b, lat1_b, d_lat):
    lon_1d, lon_b_1d = _grid_1d(lon0_b, lon1_b, d_lon)
    lat_1d, lat_b_1d = _grid_1d(lat0_b, lat1_b, d_lat)

    ds = xr.Dataset(
        coords={
            "lon": ("lon", lon_1d, {"bounds": "lon_bounds", **LON_CF_ATTRS}),
            "lat": ("lat", lat_1d, {"bounds": "lat_bounds", **LAT_CF_ATTRS}),
            "latitude_longitude": xr.DataArray(),
        },
        data_vars={
            "lon_bounds": vertices_to_bounds(lon_b_1d, ("bound", "lon")),
            "lat_bounds": vertices_to_bounds(lat_b_1d, ("bound", "lat")),
        },
    )
    return ds


# ========== 1. Export Actual Map ==========
def export_actual_maps_xesmf(index_data: xr.DataArray, index_name: str, output_base_dir: str, start_year: int = None, end_year: int = None, region_name: str = "Thailand", province_name: str = None):
    """Export average map (GeoJSON grid) over a the dataset's time range."""

    if start_year is None:
        start_year = int(index_data.time.dt.year.min())
    if end_year is None:
        end_year = int(index_data.time.dt.year.max())

    # Determine decimal places based on index characteristics
    if "SPI" in index_name:
        # Frequency and Duration are counts/months, 2 decimals are enough for spatial averages
        if "Frequency" in index_name or "Duration" in index_name:
            decimals = 2 
        else:
            # Base SPI, Peak, and Severity require higher precision
            decimals = 4 
    else:
        # Default for PR and Temp indices
        decimals = 2
    
    # Filter data by selected year range before processing
    index_data = index_data.sel(time=slice(str(start_year), str(end_year)))

    actual = index_data.sortby("latitude", "longitude")
    avg_map = actual.mean("time", skipna=True)

    # create grid from latitude/longitude of dataset
    lat = avg_map.latitude.values
    lon = avg_map.longitude.values
    d_lat = abs(lat[1] - lat[0])
    d_lon = abs(lon[1] - lon[0])

    grid = cf_grid_2d(
        lon.min() - d_lon / 2,
        lon.max() + d_lon / 2,
        d_lon,
        lat.min() - d_lat / 2,
        lat.max() + d_lat / 2,
        d_lat,
    )

    avg_map_values = avg_map.values 
    
    features = []
    for i in range(len(lat)):
        for j in range(len(lon)):
            
            val = avg_map_values[i, j]
            
            if np.isnan(val):
                continue

            poly = Polygon(
                [
                    (grid["lon_bounds"][j, 0], grid["lat_bounds"][i, 0]),
                    (grid["lon_bounds"][j, 1], grid["lat_bounds"][i, 0]),
                    (grid["lon_bounds"][j, 1], grid["lat_bounds"][i, 1]),
                    (grid["lon_bounds"][j, 0], grid["lat_bounds"][i, 1]),
                ]
            )

            features.append(
                {
                    "type": "Feature",
                    "geometry": poly.__geo_interface__,
                    "properties": {"value": round(float(val), decimals)},
                }
            )
    # print("www")
    out = {
        "type": "FeatureCollection",
        "metadata": {
            "index": index_name,
            "unit": getattr(index_data, "units", ""),
            "start_date": str(index_data.time.min().values)[:10],
            "end_date": str(index_data.time.max().values)[:10],
            "years": [
                int(index_data.time.dt.year.min()),
                int(index_data.time.dt.year.max()),
            ],
        },
        "features": features,
    }

    area_name = province_name if province_name else "overview"
    
    # structure: base_dir / country / area / index / maps_grid / actual
    out_dir = os.path.join(output_base_dir, region_name, area_name, index_name, "maps_grid", "actual")
    os.makedirs(out_dir, exist_ok=True)
    
    # filename with dynamic year range
    filename = f"{start_year}_{end_year}_actual_grid.geojson"
    out_path = os.path.join(out_dir, filename)

    with open(out_path, "w") as f:
        json.dump(out, f, indent=2) 
        
    print(f"  Saved actual map to {out_path}")
    return out_path

# ========== 2. Export Trend Map ==========
def export_trend_map_xesmf(index_data: xr.DataArray, index_name: str, output_base_dir: str, start_year: int = None, end_year: int = None, region_name: str = "Thailand", province_name: str = None):
    """Export trend map using Mann-Kendall test (GeoJSON grid)."""

    if start_year is None:
        start_year = int(index_data.time.dt.year.min())
    if end_year is None:
        end_year = int(index_data.time.dt.year.max())

    # Determine decimal places based on index characteristics
    if "SPI" in index_name:
        # Frequency and Duration are counts/months, 2 decimals are enough for spatial averages
        if "Frequency" in index_name or "Duration" in index_name:
            decimals = 2 
        else:
            # Base SPI, Peak, and Severity require higher precision
            decimals = 4 
    else:
        # Default for PR and Temp indices
        decimals = 2
    
    # Filter data by selected year range before processing
    index_data = index_data.sel(time=slice(str(start_year), str(end_year)))

    trend = index_data.sortby("latitude", "longitude")
    lats = trend.latitude.values
    lons = trend.longitude.values
    d_lat = abs(lats[1] - lats[0])
    d_lon = abs(lons[1] - lons[0])

    grid = cf_grid_2d(
        lons.min() - d_lon / 2,
        lons.max() + d_lon / 2,
        d_lon,
        lats.min() - d_lat / 2,
        lats.max() + d_lat / 2,
        d_lat,
    )
    
    # Shape is typically (time, lat, lon)
    trend_values = trend.values 

    features = []
    
    # Combine MK calculation and Polygon creation into a SINGLE double-loop.
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            
            # Fast numpy indexing to get the 1D time series for this specific pixel
            series = trend_values[:, i, j] 
            
            # Check if there is enough valid data (at least 70% non-NaN)
            if np.sum(~np.isnan(series)) >= len(series) * 0.7:
                try:
                    # Run Mann-Kendall test
                    result = mk.original_test(series)
                    slope = result.slope * 10  # per decade
                    pval = result.p
                    
                    # If calculation succeeds, immediately create the Polygon
                    poly = Polygon(
                        [
                            (grid["lon_bounds"][j, 0], grid["lat_bounds"][i, 0]),
                            (grid["lon_bounds"][j, 1], grid["lat_bounds"][i, 0]),
                            (grid["lon_bounds"][j, 1], grid["lat_bounds"][i, 1]),
                            (grid["lon_bounds"][j, 0], grid["lat_bounds"][i, 1]),
                        ]
                    )

                    features.append(
                        {
                            "type": "Feature",
                            "geometry": poly.__geo_interface__,
                            "properties": {
                                "slope": round(float(slope), decimals), 
                                "p": round(float(pval), 2)
                            },
                        }
                    )
                except Exception as e:
                    # Skip if MK test fails (e.g., constant data values)
                    print(f"MK Test Error at [{i},{j}]: {e}")
                    pass
    out = {
        "type": "FeatureCollection",
        "metadata": {
            "index": index_name,
            "method": "Mann-Kendall",
            "unit": getattr(index_data, "units", ""),
            "start_date": str(index_data.time.min().values)[:10],
            "end_date": str(index_data.time.max().values)[:10],
            "years": [
                int(index_data.time.dt.year.min()),
                int(index_data.time.dt.year.max()),
            ],
        },
        "features": features,
    }

    # Determine area directory
    area_name = province_name if province_name else "overview"
    
    # structure: base_dir / country / area / index / maps_grid / trend
    out_dir = os.path.join(output_base_dir, region_name, area_name, index_name, "maps_grid", "trend")
    os.makedirs(out_dir, exist_ok=True)
    
    # filename with dynamic year range
    filename = f"{start_year}_{end_year}_trend_grid.geojson"
    out_path = os.path.join(out_dir, filename)

    with open(out_path, "w") as f:
        json.dump(out, f, indent=2) 
        
    print(f"  Saved trend map to {out_path}")
    return out_path

# ========== 3. Export Actual Map (Shapefile Mode) ==========
def export_actual_map_shapefile(provincial_ts_dict: dict, index_name: str, output_base_dir: str, gdf_provinces: gpd.GeoDataFrame, target_col: str, region_name: str = "Thailand"):
    """Export average map (GeoJSON Polygon). Calculation is inside, clipping is done outside."""

    # Get metadata (year range and units) from the first available province data
    first_da = next(iter(provincial_ts_dict.values()))
    start_year = int(first_da.time.dt.year.min())
    end_year = int(first_da.time.dt.year.max())
    units = getattr(first_da, "units", "")
    
    # Determine decimal places based on index characteristics
    if "SPI" in index_name:
        # Frequency and Duration are counts/months, 2 decimals are enough for spatial averages
        if "Frequency" in index_name or "Duration" in index_name:
            decimals = 2 
        else:
            # Base SPI, Peak, and Severity require higher precision
            decimals = 4 
    else:
        # Default for PR and Temp indices
        decimals = 2

    features = []
    
    for idx, row in gdf_provinces.iterrows():
        prov_name = row[target_col]
        
        # Get the clipped 1D time-series data for this province
        ts_da = provincial_ts_dict.get(prov_name)
        
        if ts_da is not None:
            # 1. Calculate Actual (Time Average) INSIDE the function
            val = float(ts_da.mean(skipna=True).values)
            
            if not np.isnan(val):
                features.append({
                    "type": "Feature",
                    "geometry": row.geometry.__geo_interface__,
                    "properties": {
                        "name": prov_name,
                        "value": round(val, decimals)
                    }
                })

    out = {
        "type": "FeatureCollection",
        "metadata": {
            "index": index_name,
            "unit": units,
            "start_date": str(first_da.time.min().values)[:10],
            "end_date": str(first_da.time.max().values)[:10],
            "years": [start_year, end_year],
            "mode": "shapefile"
        },
        "features": features,
    }

    out_dir = os.path.join(output_base_dir, region_name, "overview", index_name, "maps_shp", "actual")
    os.makedirs(out_dir, exist_ok=True)
    
    filename = f"{start_year}_{end_year}_actual_shp.geojson"
    out_path = os.path.join(out_dir, filename)

    with open(out_path, "w") as f:
        json.dump(out, f, indent=2) 
        
    print(f"  Saved actual shapefile map to {out_path}")
    return out_path


# ========== 4. Export Trend Map (Shapefile Mode) ==========
def export_trend_map_shapefile(provincial_ts_dict: dict, index_name: str, output_base_dir: str, gdf_provinces: gpd.GeoDataFrame, target_col: str, region_name: str = "Thailand"):
    """Export trend map using Mann-Kendall test. Calculation is inside, clipping is done outside."""

    # Get metadata
    first_da = next(iter(provincial_ts_dict.values()))
    start_year = int(first_da.time.dt.year.min())
    end_year = int(first_da.time.dt.year.max())
    units = getattr(first_da, "units", "")

    # Determine decimal places based on index characteristics
    if "SPI" in index_name:
        # Frequency and Duration are counts/months, 2 decimals are enough for spatial averages
        if "Frequency" in index_name or "Duration" in index_name:
            decimals = 2 
        else:
            # Base SPI, Peak, and Severity require higher precision
            decimals = 4 
    else:
        # Default for PR and Temp indices
        decimals = 2

    features = []
    
    for idx, row in gdf_provinces.iterrows():
        prov_name = row[target_col]
        
        # Get the clipped 1D time-series data for this province
        ts_da = provincial_ts_dict.get(prov_name)
        
        if ts_da is not None:
            series = ts_da.values
            
            # Check for valid data threshold
            if np.sum(~np.isnan(series)) >= len(series) * 0.7:
                try:
                    # 2. Calculate Trend (Mann-Kendall) INSIDE the function
                    result = mk.original_test(series)
                    slope = result.slope * 10  # per decade
                    pval = result.p
                    
                    features.append({
                        "type": "Feature",
                        "geometry": row.geometry.__geo_interface__,
                        "properties": {
                            "name": prov_name,
                            "slope": round(float(slope), decimals),
                            "p": round(float(pval), 2)
                        }
                    })
                except Exception as e:
                    pass

    out = {
        "type": "FeatureCollection",
        "metadata": {
            "index": index_name,
            "method": "Mann-Kendall",
            "unit": units,
            "start_date": str(first_da.time.min().values)[:10],
            "end_date": str(first_da.time.max().values)[:10],
            "years": [start_year, end_year],
            "mode": "shapefile"
        },
        "features": features,
    }

    out_dir = os.path.join(output_base_dir, region_name, "overview", index_name, "maps_shp", "trend")
    os.makedirs(out_dir, exist_ok=True)
    
    filename = f"{start_year}_{end_year}_trend_shp.geojson"
    out_path = os.path.join(out_dir, filename)

    with open(out_path, "w") as f:
        json.dump(out, f, indent=2) 
        
    print(f"  Saved trend shapefile map to {out_path}")
    return out_path