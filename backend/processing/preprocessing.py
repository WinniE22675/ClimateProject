import xarray as xr

# Dictionary of aliases 
VAR_ALIASES = {
    "pr": ["pr", "tp", "precip", "precipitation", "rainfall", "rr"],
    "tas": ["tas", "t2m", "temp", "temperature", "air_temperature"],
    "tmax": ["tasmax", "tmax", "tas_max", "t2m_max", "mx2t"],
    "tmin": ["tasmin", "tmin", "tas_min", "t2m_min", "mn2t"],
}

COORD_ALIASES = {
    "latitude": ["lat", "latitude", "nav_lat", "y", "rlat"],
    "longitude": ["lon", "longitude", "nav_lon", "x", "rlon"],
    "time": ["time", "Times", "datetime", "date", "valid_time"],
}

def normalize_var_name(name: str) -> str:
    """
    Normalize variable name to standard name.
    """
    for std, aliases in VAR_ALIASES.items():
        if name.lower() in aliases:
            return std
    return name

def standardize_coords(ds):
    rename_dict = {}
    for standard_name, aliases in COORD_ALIASES.items():
        # if dataset already have standard_name, it will not do anything 
        if standard_name in ds.coords or standard_name in ds.dims:
            continue
            
        # if don't have, will find in alias 
        for alias in aliases:
            if alias in ds.coords or alias in ds.dims:
                rename_dict[alias] = standard_name
                break
    
    if rename_dict:
        print(f"Renaming coords: {rename_dict}")
        ds = ds.rename(rename_dict)
    
    return ds

def ensure_pr_unit(pr_da: xr.DataArray) -> xr.DataArray:
    """
    Ensure precipitation variable is converted to mm/day.
    Supported input units:
      - "mm/day", "mm d-1", "mm per day"
      - "m", "meter", "metre" (convert m/day → mm/day)
      - "mm/s", "kg m-2 s-1" (convert to mm/day)
    """
    units = pr_da.attrs.get("units", "").lower().strip()
    original_attrs = pr_da.attrs.copy()

    if units in ["mm/day", "mm d-1", "mm per day", "mm"]:
        return pr_da

    elif units in ["m", "meter", "metre"]:
        pr_converted = pr_da * 1000
        pr_converted.attrs = original_attrs
        pr_converted.attrs["units"] = "mm/day"
        return pr_converted

    elif units in ["mm/s", "kg m-2 s-1"]:
        pr_converted = pr_da * 86400
        pr_converted.attrs = original_attrs
        pr_converted.attrs["units"] = "mm/day"
        return pr_converted

    else:
        raise ValueError(f"The unit '{units}' is unknown, please check the information.")


def ensure_temperature_unit(da: xr.DataArray) -> xr.DataArray:
    """
    Ensure temperature variables are in Celsius (°C).
    Supported input units:
      - "c", "°c", "celsius", "degc"
      - "k", "kelvin" (convert to C)
    """
    units = da.attrs.get("units", "").lower().strip()
    original_attrs = da.attrs.copy()

    if units in ["c", "°c", "celsius", "degc"]:
        return da

    elif units in ["k", "kelvin", "degk"]:
        da_converted = da - 273.15
        da_converted.attrs = original_attrs
        da_converted.attrs["units"] = "C"
        return da_converted

    else:
        raise ValueError(f"The unit '{units}' is unknown, please check the information.")


def load_dataset(file_path: str) -> xr.Dataset:
    """
    Load dataset (NetCDF/GRIB/CSV).
    - For NetCDF/GRIB: use xarray
    - For CSV: use pandas → xarray
    """
    if file_path.endswith((".nc", ".nc4", ".grib")):
        ds = xr.open_dataset(file_path, chunks={"time": 100})
    elif file_path.endswith(".csv"):
        import pandas as pd
        df = pd.read_csv(file_path)
        if "time" not in df.columns:
            raise ValueError("CSV must have a 'time' column.")
        ds = df.set_index("time").to_xarray()
    else:
        raise ValueError(f"Unsupported file format: {file_path}")

    # normalize variable names
    rename_map = {}
    for var in ds.data_vars:
        std_name = normalize_var_name(var)
        if std_name != var:
            rename_map[var] = std_name
    if rename_map:
        ds = ds.rename(rename_map)

    # ensure units
    if "pr" in ds:
        ds["pr"] = ensure_pr_unit(ds["pr"])
    if "tas" in ds:
        ds["tas"] = ensure_temperature_unit(ds["tas"])
    if "tasmax" in ds:
        ds["tmax"] = ensure_temperature_unit(ds["tmax"])
    if "tasmin" in ds:
        ds["tmin"] = ensure_temperature_unit(ds["tmin"])

    return ds














































# import os
# import json
# import pandas as pd
# import numpy as np
# import xarray as xr
# import geopandas as gpd
# import xclim as xc
# import xclim.indicators as xci
# import rioxarray  # ต้องมีเพราะใช้ clip
# from shapely.geometry import Polygon
# import pymannkendall as mk
# from cf_xarray import vertices_to_bounds


# # -------------------------------
# # 1. Config Path
# # -------------------------------
# FRONTEND_DATA = os.path.abspath(
#     os.path.join(os.path.dirname(__file__), "../../frontend/public/data")
# )
# OUT_INDICES = os.path.join(FRONTEND_DATA, "indices")
# OUT_MAPS = os.path.join(FRONTEND_DATA, "maps_grid")

# os.makedirs(OUT_INDICES, exist_ok=True)
# os.makedirs(os.path.join(OUT_INDICES, "annual"), exist_ok=True)
# os.makedirs(os.path.join(OUT_INDICES, "monthly"), exist_ok=True)
# os.makedirs(os.path.join(OUT_MAPS, "actual"), exist_ok=True)
# os.makedirs(os.path.join(OUT_MAPS, "trend"), exist_ok=True)


# # -------------------------------
# # 2. Unit conversion
# # -------------------------------
# def ensure_pr_unit(pr_da: xr.DataArray) -> xr.DataArray:
#     units = pr_da.attrs.get("units", "").lower()
#     if units in ["mm/day", "mm d-1", "mm per day"]:
#         return pr_da
#     elif units in ["m", "meter", "metre"]:
#         pr_converted = pr_da * 1000
#         pr_converted.attrs["units"] = "mm/day"
#         return pr_converted
#     elif units in ["mm/s", "kg m-2 s-1"]:
#         pr_converted = pr_da * 86400
#         pr_converted.attrs["units"] = "mm/day"
#         return pr_converted
#     else:
#         raise ValueError(f"Unknown precipitation unit: {units}")


# def ensure_temperature_unit(da: xr.DataArray) -> xr.DataArray:
#     units = da.attrs.get("units", "").lower()
#     if units in ["c", "°c", "celsius", "degc"]:
#         return da
#     elif units in ["k", "kelvin"]:
#         da_converted = da - 273.15
#         da_converted.attrs["units"] = "°C"
#         return da_converted
#     else:
#         raise ValueError(f"Unknown temperature unit: {units}")


# # -------------------------------
# # 3. Export Functions
# # -------------------------------
# def export_timeseries(index_data: xr.DataArray, index_name: str):
#     years = index_data.time.dt.year.values
#     annual = (
#         index_data.groupby("time.year")
#         .mean("time")
#         .mean(dim=["latitude", "longitude"], skipna=True)
#     )

#     records = [
#         {"year": int(y), "value": float(v)}
#         for y, v in zip(annual.year.values, annual.values)
#         if not np.isnan(v)
#     ]

#     out = {
#         "type": "TimeSeries",
#         "metadata": {
#             "index": index_name,
#             "unit": getattr(index_data, "units", ""),
#             "method": "annual mean",
#             "years": [int(years.min()), int(years.max())],
#         },
#         "data": records,
#     }
#     with open(f"{OUT_INDICES}/annual/{index_name}_timeseries.json", "w") as f:
#         json.dump(out, f, indent=2)


# def export_monthly_series(index_data: xr.DataArray, index_name: str):
#     years = index_data.time.dt.year.values
#     monthly = index_data.mean(dim=["latitude", "longitude"], skipna=True)

#     records = []
#     for t, v in zip(monthly["time"].values, monthly.values):
#         ts = pd.to_datetime(str(t))
#         records.append(
#             {"year": int(ts.year), "month": int(ts.month), "value": float(v)}
#         )

#     out = {
#         "type": "Climatology",
#         "metadata": {
#             "index": index_name,
#             "unit": getattr(index_data, "units", ""),
#             "method": "monthly climatology",
#             "period": [int(years.min()), int(years.max())],
#         },
#         "data": records,
#     }

#     with open(f"{OUT_INDICES}/monthly/{index_name}_monthly.json", "w") as f:
#         json.dump(out, f, indent=2)


# # -------------------------------
# # 4. Main Processing Function
# # -------------------------------
# def process_dataset(pr_path: str, tmax_path: str, tmin_path: str, shapefile: str):
#     """
#     Main entry point:
#     - Read dataset from upload
#     - Clip to Thailand shapefile
#     - Compute indices
#     - Export to JSON/GeoJSON
#     """

#     # Load data
#     pr = xr.open_dataset(pr_path)["tp"]
#     tmax = xr.open_dataset(tmax_path)["mx2t"]
#     tmin = xr.open_dataset(tmin_path)["mn2t"]

#     # Convert units
#     pr = ensure_pr_unit(pr)
#     tmax = ensure_temperature_unit(tmax)
#     tmin = ensure_temperature_unit(tmin)

#     # Rename
#     pr.name, tmax.name, tmin.name = "pr", "tasmax", "tasmin"

#     # Fix time
#     for da in [pr, tmax, tmin]:
#         da["time"] = pd.to_datetime(da["time"].values)

#     # Clip with shapefile
#     shp = gpd.read_file(shapefile).to_crs("EPSG:4326")
#     pr = pr.rio.set_spatial_dims(x_dim="longitude", y_dim="latitude").rio.write_crs("EPSG:4326")
#     tmax = tmax.rio.set_spatial_dims(x_dim="longitude", y_dim="latitude").rio.write_crs("EPSG:4326")
#     tmin = tmin.rio.set_spatial_dims(x_dim="longitude", y_dim="latitude").rio.write_crs("EPSG:4326")

#     pr = pr.rio.clip(shp.geometry, shp.crs, drop=True)
#     tmax = tmax.rio.clip(shp.geometry, shp.crs, drop=True)
#     tmin = tmin.rio.clip(shp.geometry, shp.crs, drop=True)

#     # Merge
#     ds = xr.Dataset({"pr": pr, "tasmax": tmax, "tasmin": tmin})

#     # ---------------------------
#     # Compute indices (ตัวอย่าง)
#     # ---------------------------
#     results_lib = {}
#     results_lib_m = {}

#     results_lib["PRCPTOT"] = xc.indicators.icclim.PRCPTOT(pr=ds["pr"], freq="YS")
#     results_lib_m["PRCPTOT"] = xc.indicators.icclim.PRCPTOT(pr=ds["pr"], freq="MS")

#     spi6 = xci.atmos.standardized_precipitation_index(
#         pr="pr", freq="MS", window=6, dist="gamma", method="ML", ds=ds
#     )
#     results_lib["SPI6"] = spi6
#     results_lib_m["SPI6"] = spi6

#     # ---------------------------
#     # Export results
#     # ---------------------------
#     for idx_name, idx_data in results_lib.items():
#         export_timeseries(idx_data, idx_name)

#     for idx_name, idx_data in results_lib_m.items():
#         export_monthly_series(idx_data, idx_name)

#     print("✅ Finished preprocessing, results saved to public/data/")
