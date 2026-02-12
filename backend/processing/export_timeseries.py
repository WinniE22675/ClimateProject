import os
import json
import numpy as np
import pandas as pd
import xarray as xr

# base output folder (configurable)
# OUT_INDICES = "output/indices"
# os.makedirs(OUT_INDICES, exist_ok=True)


def export_yearly_timeseries(index_data: xr.DataArray, index_name: str, output_base_dir: str, region_name: str = ""):
    """Export annual timeseries (mean over space, grouped by year)."""
    years = index_data.time.dt.year.values

    if index_data.ndim == 1:
        annual = index_data.groupby("time.year").mean("time")

    # ---- CASE 2: raster (SEA or large region) ----
    else:
        spatial_dims = [d for d in index_data.dims if d not in ["time"]]
        annual = (
            index_data.groupby("time.year")
            .mean("time")
            .mean(dim=spatial_dims, skipna=True)
        )
    # annual mean (area + time aggregated)
    # annual = (
    #     index_data.groupby("time.year")
    #     .mean("time")
    #     .mean(dim=["latitude", "longitude"], skipna=True)
    # )

    records = [
        {"year": int(y), "value": round(float(v),2)}
        for y, v in zip(annual.year.values, annual.values)
        if not np.isnan(v)
    ]

    out = {
        "type": "TimeSeries",
        "metadata": {
            "index": index_name,
            "unit": getattr(index_data, "units", ""),
            "method": "annual mean",
            "start_date": str(index_data.time.min().values)[:10],
            "end_date": str(index_data.time.max().values)[:10],
            "years": [int(years.min()), int(years.max())],
        },
        "data": records,
    }

    # ensure folder exists
    out_dir = os.path.join(output_base_dir, "indices", "annual") # OUT_INDICES
    os.makedirs(out_dir, exist_ok=True)

    # with open(os.path.join(out_dir, f"{index_name}_timeseries.json"), "w") as f:
    #     json.dump(out, f, indent=2)

    suffix = f"_{region_name}" if region_name else ""
    filename = f"{index_name}{suffix}_timeseries.json" # ex: PRCPTOT_Thailand_timeseries.json

    with open(os.path.join(out_dir, filename), "w") as f:
        json.dump(out, f, indent=2)


def export_seasonal_cycle(index_data: xr.DataArray, index_name: str, output_base_dir: str, region_name: str = ""):
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

    records = []
    for t, v in zip(monthly["time"].values, monthly.values):
        ts = pd.to_datetime(str(t))
        records.append({
            "year": int(ts.year),
            "month": int(ts.month),
            "value": round(float(v),2),
        })

    out = {
        "type": "Climatology",
        "metadata": {
            "index": index_name,
            "unit": getattr(index_data, "units", ""),
            "method": "monthly climatology",
            "start_date": str(index_data.time.min().values)[:10],
            "end_date": str(index_data.time.max().values)[:10],
            "period": [int(years.min()), int(years.max())],
        },
        "data": records,
    }

    # ensure folder exists
    out_dir = os.path.join(output_base_dir, "indices", "monthly") # OUT_INDICES
    os.makedirs(out_dir, exist_ok=True)

    # with open(os.path.join(out_dir, f"{index_name}_monthly.json"), "w") as f:
    #     json.dump(out, f, indent=2)

    suffix = f"_{region_name}" if region_name else ""
    filename = f"{index_name}{suffix}_monthly.json"

    with open(os.path.join(out_dir, filename), "w") as f:
        json.dump(out, f, indent=2)
