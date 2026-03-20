import os
import json
import numpy as np
import pandas as pd
import xarray as xr

def export_yearly_timeseries(index_data: xr.DataArray, index_name: str, output_base_dir: str, region_name: str = "Thailand", province_name: str = None):
    """Export annual timeseries (mean over space, grouped by year)."""
    years = index_data.time.dt.year.values

    if index_data.ndim == 1:
        annual = index_data.groupby("time.year").mean("time")

    else:
        spatial_dims = [d for d in index_data.dims if d not in ["time"]]
        annual = (
            index_data.groupby("time.year")
            .mean("time")
            .mean(dim=spatial_dims, skipna=True)
        )

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

    records = [
        {"year": int(y), "value": round(float(v), decimals)}
        for y, v in zip(annual.year.values, annual.values)
        if not np.isnan(v)
    ]

    out = {
        "type": "TimeSeries",
        "metadata": {
            "index": index_name,
            "unit": index_data.attrs.get("units", ""), # getattr(index_data, "units", ""),
            "method": "annual mean",
            "start_date": str(index_data.time.min().values)[:10],
            "end_date": str(index_data.time.max().values)[:10],
            "years": [int(years.min()), int(years.max())],
        },
        "data": records,
    }
        
    area_name = province_name if province_name else "overview"

    # New structure: base_dir / country / area / index / indices / annual
    out_dir = os.path.join(output_base_dir, region_name, area_name, index_name, "indices", "annual")
    os.makedirs(out_dir, exist_ok=True)

    filename = f"{index_name}_timeseries.json"
    out_path = os.path.join(out_dir, filename)

    # Assuming 'out' dictionary is prepared before this block in your actual code
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

def export_seasonal_cycle(index_data: xr.DataArray, index_name: str, output_base_dir: str, region_name: str = "Thailand", province_name: str = None):
    """Export monthly climatology (mean over space)."""
    years = index_data.time.dt.year.values

    # monthly mean (space averaged only)
    # monthly = index_data.mean(dim=["latitude", "longitude"], skipna=True)

    # ---- CASE 1: already aggregated ----
    if index_data.ndim == 1:
        monthly = index_data

    # ---- CASE 2: raster ----
    else:
        spatial_dims = [d for d in index_data.dims if d not in ["time"]]
        monthly = index_data.mean(dim=spatial_dims, skipna=True)

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

    records = []
    for t, v in zip(monthly["time"].values, monthly.values):
        ts = pd.to_datetime(str(t))
        records.append({
            "year": int(ts.year),
            "month": int(ts.month),
            "value": round(float(v), decimals),
        })

    out = {
        "type": "Climatology",
        "metadata": {
            "index": index_name,
            "unit": index_data.attrs.get("units", ""), # getattr(index_data, "units", ""),
            "method": "seasonal cycle",
            "start_date": str(index_data.time.min().values)[:10],
            "end_date": str(index_data.time.max().values)[:10],
            "period": [int(years.min()), int(years.max())],
        },
        "data": records,
    }

    area_name = province_name if province_name else "overview"
    
    # New structure: base_dir / country / area / index / indices / seasonal
    out_dir = os.path.join(output_base_dir, region_name, area_name, index_name, "indices", "seasonal")
    os.makedirs(out_dir, exist_ok=True)

    filename = f"{index_name}_seasonal.json"
    out_path = os.path.join(out_dir, filename)

    # Assuming 'out' dictionary is prepared before this block in your actual code
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
