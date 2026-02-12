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
        raise TypeError("Input must be xarray.Dataset") #or xarray.DataArray

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

def mask_by_country(da: xr.DataArray, country_name: str, gdf_countries: gpd.GeoDataFrame,): # , shapefile_path: str
    """
    Mask DataArray by country name using shapefile.
    Assumes shapefile has a column like 'ADMIN' or 'NAME' for country names.
    """
    """
    Try clipping DataArray by country polygon.
    Returns clipped DataArray or None if not possible.
    """
    try:
        # --- Guard: CRS must exist ---
        if not hasattr(da, "rio") or da.rio.crs is None:
            raise ValueError("DataArray has no CRS. Call prep_for_rio() first.")
        
        # gdf = gpd.read_file(shapefile_path)

        # target_column = 'ADMIN'
        
        target_column = None
        for col in ["ADMIN"]: # , "ADM0_EN", "NAME", "NAME_EN"
            if col in gdf_countries.columns:
                target_column = col
                break
        else:
            raise ValueError("No country name column found")
        
        possible_names = resolve_country_names(country_name)

        mask = gdf_countries[target_column].astype(str).isin(possible_names)
        country_gdf = gdf_countries.loc[mask].copy()
        
        print("Using column:", target_column)
        print(gdf_countries[target_column].unique())


        # country_gdf = gdf_countries[gdf_countries[target_column] == country_name]
        print("Rows after filter:", len(country_gdf))

        # diagnose_clip_issue(da, country_gdf)

        # if country_gdf.empty:
        #     print(f"Country '{country_name}' not found in shapefile.")
        #     return None

        if country_gdf.empty or country_gdf.geometry.isna().all():
            print(f"Invalid geometry after filtering: {country_name}")
            return None
        
        # CRS safety
        if not country_gdf.crs or not country_gdf.crs.equals(da.rio.crs):
            country_gdf = country_gdf.to_crs(da.rio.crs)

        # geoms = [mapping(geom) for geom in country_gdf.geometry]

        # da_masked = da.rio.clip(country_gdf.geometry.apply(mapping), country_gdf.crs, drop=True)
        # return da_masked
    
        # return da.rio.clip(
        #     country_gdf.geometry.__geo_interface__,
        #     country_gdf.crs,
        #     drop=True,
        # )

        try:
            clipped = da.rio.clip(
                country_gdf.geometry.apply(mapping),
                country_gdf.crs,
                drop=True,
                all_touched=True,
            )

            if clipped.size > 0:
                # if log is not None:
                #     log[country_name] = {
                #         "method": "clip",
                #         "n_cells": int(clipped.count().item()),
                #     }
                return clipped

        except Exception:
            pass

        # centroid = country_gdf.geometry.unary_union.centroid

        # nn = da.sel(
        #     longitude=centroid.x,
        #     latitude=centroid.y,
        #     method="nearest",
        # )

        # if log is not None:
        #     log[country_name] = {
        #         "method": "nearest",
        #         "note": "fallback due to insufficient spatial coverage",
        #     }

        # return nn

        clipped = da.rio.clip(
                country_gdf.geometry.apply(mapping),
                country_gdf.crs,
                drop=True,
                all_touched=True,
            )

        if clipped.size > 0:
            # if log is not None:
            #     log[country_name] = {
            #         "method": "clip all touched",
            #         "n_cells": int(clipped.count().item()),
            #     }
            return clipped

    except Exception as e:
        print(f"Error masking {country_name}: {e}")
        return None
    
    
import numpy as np
import geopandas as gpd
import shapely.geometry as geom
import xarray as xr


def mask_by_country_oo(
    da: xr.DataArray,
    country_name: str,
    gdf_countries: gpd.GeoDataFrame,
    log: dict | None = None,
):
    """
    Compute area-weighted mean time series for a given country
    using polygon-grid intersection with spatial subsetting.

    Parameters
    ----------
    da : xr.DataArray
        DataArray with dimensions (time, latitude, longitude)
    country_name : str
        Target country name
    gdf_countries : gpd.GeoDataFrame
        Country shapefile (ADMIN / NAME column expected)

    Returns
    -------
    xr.DataArray or None
        Area-weighted country mean (time series)
    """

    # --------------------------------------------------
    # 1. CRS safety
    # --------------------------------------------------
    if not hasattr(da, "rio") or da.rio.crs is None:
        raise ValueError("DataArray has no CRS. Call prep_for_rio() first.")

    # --------------------------------------------------
    # 2. Resolve country polygon
    # --------------------------------------------------
    target_col = None
    for col in ["ADMIN", "ADM0_EN", "NAME", "NAME_EN"]:
        if col in gdf_countries.columns:
            target_col = col
            break
    if target_col is None:
        raise ValueError("No country name column found in shapefile")

    possible_names = resolve_country_names(country_name)
    country_gdf = gdf_countries[
        gdf_countries[target_col].astype(str).isin(possible_names)
    ].copy()

    if country_gdf.empty or country_gdf.geometry.isna().all():
        return None

    if not country_gdf.crs.equals(da.rio.crs):
        country_gdf = country_gdf.to_crs(da.rio.crs)

    country_geom = country_gdf.unary_union

    # --------------------------------------------------
    # 3. Spatial subsetting (KEY POINT)
    # --------------------------------------------------
    minx, miny, maxx, maxy = country_gdf.total_bounds

    da_sub = da.sel(
        longitude=slice(minx, maxx),
        latitude=slice(miny, maxy),
    )

    if da_sub.sizes.get("latitude", 0) == 0 or da_sub.sizes.get("longitude", 0) == 0:
        return None

    lats = da_sub["latitude"].values
    lons = da_sub["longitude"].values

    dlat = np.abs(lats[1] - lats[0])
    dlon = np.abs(lons[1] - lons[0])

    # --------------------------------------------------
    # 4. Build grid-cell polygons (subset only)
    # --------------------------------------------------
    cell_polygons = []
    cell_indices = []

    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            cell = geom.box(
                lon - dlon / 2,
                lat - dlat / 2,
                lon + dlon / 2,
                lat + dlat / 2,
            )

            # cheap bbox pre-check
            if not cell.intersects(country_geom):
                continue

            cell_polygons.append(cell)
            cell_indices.append((i, j))

    if not cell_polygons:
        return None

    grid_gdf = gpd.GeoDataFrame(
        {
            "i": [i for i, j in cell_indices],
            "j": [j for i, j in cell_indices],
        },
        geometry=cell_polygons,
        crs=da.rio.crs,
    )

    # --------------------------------------------------
    # 5. Reproject to equal-area CRS
    # --------------------------------------------------
    grid_gdf = grid_gdf.to_crs("EPSG:6933")
    country_geom_eq = (
        gpd.GeoSeries([country_geom], crs=da.rio.crs)
        .to_crs("EPSG:6933")
        .iloc[0]
    )

    # --------------------------------------------------
    # 6. Polygon intersection area
    # --------------------------------------------------
    grid_gdf["intersect_area"] = (
        grid_gdf.geometry.intersection(country_geom_eq).area
    )
    grid_gdf = grid_gdf[grid_gdf["intersect_area"] > 0]

    if grid_gdf.empty:
        return None

    # --------------------------------------------------
    # 7. Area-weighted aggregation
    # --------------------------------------------------
    weights = grid_gdf["intersect_area"].values
    weights = weights / weights.sum()

    values = []
    for row in grid_gdf.itertuples():
        values.append(da_sub.isel(latitude=row.i, longitude=row.j))

    stacked = xr.concat(values, dim="cell")
    weighted_mean = (stacked * xr.DataArray(weights, dims="cell")).sum("cell")

    weighted_mean.name = da.name
    weighted_mean.attrs.update(
        {
            "aggregation": "area_weighted_mean",
            "region": country_name,
            "method": "polygon_grid_intersection",
        }
    )

    return weighted_mean
