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