import os
import json
import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd
from shapely.geometry import Polygon, mapping
from cf_xarray import vertices_to_bounds

from processing.overlay import overlay_with_shapefile
from processing.clipping import prep_for_rio, calc_weighted_mean

# ============================
#  Base Output Folder
# ============================
PREVIEW_OUT = "output/preview_output"
os.makedirs(PREVIEW_OUT, exist_ok=True)

# ============================
#  CF Grid Helper (from original)
# ============================

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


# ============================
#  Export Preview Functions
# ============================

# def export_preview_timeseries(da: xr.DataArray, out_dir: str):
#     """Export annual preview timeseries (mean over space)."""

#     years = da.time.dt.year.values
#     annual = (
#         da.groupby("time.year")
#         .mean("time")
#         .mean(dim=["latitude", "longitude"], skipna=True)
#     )

#     records = [
#         {"year": int(y), "value": round(float(v), 4)}
#         for y, v in zip(annual.year.values, annual.values)
#         if not np.isnan(v)
#     ]

#     out = {
#         "type": "PreviewTimeSeries",
#         "metadata": {
#             "start_date": str(da.time.min().values)[:10],
#             "end_date": str(da.time.max().values)[:10],
#             "years": [int(years.min()), int(years.max())],
#         },
#         "data": records,
#     }

#     # with open(os.path.join(out_dir, "timeseries.json"), "w") as f:
#     #     json.dump(out, f, indent=2)
#     out_path = os.path.join(out_dir, "timeseries.json")
#     with open(out_path, "w") as f:
#         json.dump(out, f, indent=2)

#     return out_path  
def export_preview_timeseries(
    data: xr.DataArray,
    output_base_dir: str,
    var_name: str,
    region_name: str | None = None,
):
    """Export annual preview timeseries (mean over space)."""

    years = data.time.dt.year.values

    # annual = (
    #     da.groupby("time.year")
    #     .mean("time")
    #     .mean(dim=["latitude", "longitude"], skipna=True)
    # )
    # spatial_dims = {"latitude", "longitude"}
    # has_spatial = spatial_dims.issubset(set(data.dims))

    # if has_spatial:
    #     da_spatial_mean = data.mean(dim=["latitude", "longitude"], skipna=True)
    # else:
    #     # already reduced (e.g. nearest-neighbor fallback)
    #     da_spatial_mean = data

    # annual = (
    #     da_spatial_mean
    #     .groupby("time.year")
    #     .mean(skipna=True)
    # )

    if data.ndim == 1:
        annual = data.groupby("time.year").mean("time")

    # ---- CASE 2: raster (SEA or large region) ----
    else:
        spatial_dims = [d for d in data.dims if d not in ["time"]]
        annual = (
            data.groupby("time.year")
            .mean("time")
            .mean(dim=spatial_dims, skipna=True)
        )

    records = [
        {"year": int(y), "value": round(float(v), 4)}
        for y, v in zip(annual.year.values, annual.values)
        if not np.isnan(v)
    ]

    out = {
        "type": "PreviewTimeSeries",
        "metadata": {
            "index": var_name,
            "unit": getattr(data, "units", ""),
            "method": "annual mean",
            "start_date": str(data.time.min().values)[:10],
            "end_date": str(data.time.max().values)[:10],
            "years": [int(years.min()), int(years.max())],
        },
        "data": records,
    }

    out_dir = os.path.join(output_base_dir, "indices", "annual")
    os.makedirs(out_dir, exist_ok=True)

    suffix = f"_{region_name}" if region_name else ""
    filename = f"{var_name}{suffix}_timeseries.json"
    out_path = os.path.join(out_dir, filename)

    print(f"[PREVIEW] Writing → {out_path}")

    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

    return out_path

# def export_preview_monthly(da: xr.DataArray, out_dir: str):
#     """Export preview monthly (space-averaged)."""

#     area_mean = da.mean(dim=["latitude", "longitude"], skipna=True)

#     monthly = area_mean.resample(time="MS").mean()

#     records = []
#     for t, v in zip(monthly["time"].values, monthly.values):
#         ts = pd.Period(str(t))
#         records.append({
#             "year": int(ts.year),
#             "month": int(ts.month),
#             "value": round(float(v), 4),
#         })

#     out = {
#         "type": "PreviewMonthly",
#         "metadata": {
#             "start_date": str(da.time.min().values)[:10],
#             "end_date": str(da.time.max().values)[:10],
#         },
#         "data": records,
#     }

#     # with open(os.path.join(out_dir, "monthly.json"), "w") as f:
#     #     json.dump(out, f, indent=2)
#     out_path = os.path.join(out_dir, "monthly.json")
#     with open(out_path, "w") as f:
#         json.dump(out, f, indent=2)

#     return out_path 

def export_preview_monthly(
    data: xr.DataArray,
    output_base_dir: str,
    var_name: str,
    region_name: str | None = None,
):
    """Export preview monthly (space-averaged)."""

    # spatial_dims = {"latitude", "longitude"}
    # has_spatial = spatial_dims.issubset(set(data.dims))

    # if has_spatial:
    #     da_spatial_mean = data.mean(dim=["latitude", "longitude"], skipna=True)
    # else:
    #     da_spatial_mean = data
    

    years = data.time.dt.year.values

    # monthly = da_spatial_mean.resample(time="MS").mean(skipna=True)

    
    # ---- CASE 1: already aggregated ----
    if data.ndim == 1:
        monthly = data

    # ---- CASE 2: raster ----
    else:
        spatial_dims = [d for d in data.dims if d not in ["time"]]
        monthly = data.mean(dim=spatial_dims, skipna=True)

    # area_mean = da.mean(dim=["latitude", "longitude"], skipna=True)
    # monthly = area_mean.resample(time="MS").mean()

    records = []
    for t, v in zip(monthly["time"].values, monthly.values):
        ts = pd.Period(str(t))
        records.append({
            "year": int(ts.year),
            "month": int(ts.month),
            "value": round(float(v), 4),
        })

    out = {
        "type": "PreviewMonthly",
        "metadata": {
            "index": var_name,
            "unit": getattr(data, "units", ""),
            "method": "monthly climatology",
            "start_date": str(data.time.min().values)[:10],
            "end_date": str(data.time.max().values)[:10],
            "period": [int(years.min()), int(years.max())],
        },
        "data": records,
    }

    out_dir = os.path.join(output_base_dir, "indices", "monthly")
    os.makedirs(out_dir, exist_ok=True)

    suffix = f"_{region_name}" if region_name else ""
    filename = f"{var_name}{suffix}_monthly.json"
    out_path = os.path.join(out_dir, filename)

    print(f"[PREVIEW] Writing → {out_path}")

    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

    return out_path


# def export_preview_map(da: xr.DataArray, out_dir: str):
#     """Export average map (GeoJSON grid) over a the dataset's time range."""
    
#     actual = da.sortby("latitude", "longitude")
#     avg_map = actual.mean("time", skipna=True)

#     lat = avg_map.latitude.values
#     lon = avg_map.longitude.values
#     d_lat = abs(lat[1] - lat[0])
#     d_lon = abs(lon[1] - lon[0])

#     grid = cf_grid_2d(
#         lon.min() - d_lon / 2,
#         lon.max() + d_lon / 2,
#         d_lon,
#         lat.min() - d_lat / 2,
#         lat.max() + d_lat / 2,
#         d_lat,
#     )

#     features = []
#     for i in range(len(lat)):
#         for j in range(len(lon)):
#             val = (
#                 avg_map.sel(latitude=lat[i], longitude=lon[j], method="nearest")
#                 .values.item()
#             )
#             if np.isnan(val):
#                 continue

#             poly = Polygon(
#                 [
#                     (grid["lon_bounds"][j, 0], grid["lat_bounds"][i, 0]),
#                     (grid["lon_bounds"][j, 1], grid["lat_bounds"][i, 0]),
#                     (grid["lon_bounds"][j, 1], grid["lat_bounds"][i, 1]),
#                     (grid["lon_bounds"][j, 0], grid["lat_bounds"][i, 1]),
#                 ]
#             )

#             features.append(
#                 {
#                     "type": "Feature",
#                     "geometry": poly.__geo_interface__,
#                     "properties": {"value": round(float(val),4)},
#                 }
#             )

#     geojson = {
#         "type": "FeatureCollection",
#         "features": features
#     }

#     # with open(os.path.join(out_dir, "map.geojson"), "w") as f:
#     #     json.dump(geojson, f, indent=2)
#     out_path = os.path.join(out_dir, "map.geojson")
#     with open(out_path, "w") as f:
#         json.dump(geojson, f, indent=2)

#     return out_path 

def export_preview_map(
    data: xr.DataArray,
    output_base_dir: str,
    var_name: str,
):
    """Export average map (GeoJSON grid) over dataset time range."""

    actual = data.sortby("latitude", "longitude")
    avg_map = actual.mean("time", skipna=True)

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

    features = []
    for i in range(len(lat)):
        for j in range(len(lon)):
            val = avg_map.values[i, j]
            if np.isnan(val):
                continue

            poly = Polygon([
                (grid["lon_bounds"][j, 0], grid["lat_bounds"][i, 0]),
                (grid["lon_bounds"][j, 1], grid["lat_bounds"][i, 0]),
                (grid["lon_bounds"][j, 1], grid["lat_bounds"][i, 1]),
                (grid["lon_bounds"][j, 0], grid["lat_bounds"][i, 1]),
            ])

            features.append({
                "type": "Feature",
                "geometry": poly.__geo_interface__,
                "properties": {"value": round(float(val), 4)},
            })

    geojson = {
        "type": "FeatureCollection",
        "metadata": {
            "index": var_name,
            "unit": getattr(data, "units", ""),
            "start_date": str(data.time.min().values)[:10],
            "end_date": str(data.time.max().values)[:10],
            "years": [
                int(data.time.dt.year.min()),
                int(data.time.dt.year.max()),
            ],
        },
        "features": features,
    }

    out_dir = os.path.join(output_base_dir, "maps_grid", "actual")
    os.makedirs(out_dir, exist_ok=True)

    filename = f"{var_name}_actual_grid.geojson"
    out_path = os.path.join(out_dir, filename)

    print(f"[PREVIEW] Writing → {out_path}")

    with open(out_path, "w") as f:
        json.dump(geojson, f, indent=2)

    return out_path


# ============================
#  Main Helper Entry
# ============================

# def export_preview_all(da: xr.DataArray, dataset_id: int, var_name: str):
#     """
#     Export all preview products:
#       - timeseries.json
#       - monthly.json
#       - map.geojson
#     Saved to: output/preview_output/dataset_{id}/{var_name}/
#     """

#     var_dir = os.path.join(PREVIEW_OUT, f"dataset_{dataset_id}", var_name)
#     os.makedirs(var_dir, exist_ok=True)

#     ts_path = export_preview_timeseries(da, var_dir)
#     monthly_path = export_preview_monthly(da, var_dir)
#     map_path = export_preview_map(da, var_dir)

#     print(f"[Preview Exported] -> {var_dir}")

#     return {
#         "timeseries_path": ts_path,
#         "monthly_path": monthly_path,
#         "map_path": map_path,
#         "base_url": f"/output/preview_output/dataset_{dataset_id}/{var_name}" # Helper for frontend
#     }

SEA_COUNTRIES = [
    "Thailand",
    "Vietnam",
    "Laos",
    "Cambodia",
    "Myanmar",
    "Malaysia",
    "Indonesia",
    "Philippines",
    "Brunei",
    "Singapore",
    "Timor-Leste",
]

COUNTRY_SHAPEFILE_PATH = "data/sea_boundary/southeast-asia-boundary.shp"


SEA_SHAPEFILE_PATH = "data/sea_boundary_dissolved/sea_boundary_dissolved.geojson"
shp_sea = gpd.read_file(SEA_SHAPEFILE_PATH).to_crs("EPSG:4326")

shp_countries = gpd.read_file(COUNTRY_SHAPEFILE_PATH).to_crs("EPSG:4326")


# def export_preview_all(
#     da: xr.DataArray,
#     dataset_name: str,
#     var_name: str,
#     region_name: str | None = None,
# ):
#     """
#     Export preview products following production structure.
#     """

#     output_base_dir = f"output/{dataset_name}"
#     os.makedirs(output_base_dir, exist_ok=True)

#     ts_path = export_preview_timeseries(
#         da, output_base_dir, var_name, region_name
#     )
#     monthly_path = export_preview_monthly(
#         da, output_base_dir, var_name, region_name
#     )
#     map_path = export_preview_map(
#         da, output_base_dir, var_name
#     )

#     overlay_with_shapefile(map_path , shp_sea)

#     return {
#         "timeseries_path": ts_path,
#         "monthly_path": monthly_path,
#         "map_path": map_path,
#         "base_dir": output_base_dir,
#     }

def export_preview_all(
    ds: xr.Dataset,
    dataset_name: str,
):
    """
    Post-merge preview export
    - split by variable
    - SEA + country aggregation
    """

    output_base_dir = f"output/{dataset_name}"
    os.makedirs(output_base_dir, exist_ok=True)

    results = {}
    extraction_log = {}

    for var in ds.data_vars:
        extraction_log[var] = {}
        print(f"[Preview] Exporting variable: {var}")
        da = prep_for_rio(ds[var])

        # ------------------
        #  Annual (SEA)
        # ------------------    
        export_preview_timeseries(
            data=da,
            output_base_dir=output_base_dir,
            var_name=var,
            region_name="SEA",
        )

        # ------------------
        #  Monthly (SEA)
        # ------------------
        export_preview_monthly(
            data=da,
            output_base_dir=output_base_dir,
            var_name=var,
            region_name="SEA",
        )

        # ------------------
        #  Annual & Monthly (Country)
        # ------------------
        for country in SEA_COUNTRIES:
            print(f"   -> Masking for: {country}...", end=" ")
            # country_log = {}
            
            try:
                # --- จุดที่น่าสงสัยที่สุด (Wrap with Try-Catch) ---
                weighted_da = calc_weighted_mean(
                    da,
                    country,
                    shp_countries,
                    # log=country_log
                )
                
                # บันทึก Log
                # extraction_log[var][country] = country_log.get(country, {"status": "no_log_returned"})

                if weighted_da is None:
                    print(f"SKIPPED (No intersection or empty result)")
                    # extraction_log[var][country]["result"] = "empty"
                    continue

                if weighted_da.isnull().all():
                     print(f"SKIPPED (All values are NaN)")
                    #  extraction_log[var][country]["result"] = "all_nan"
                     continue

                print(f"SUCCESS (Shape: {weighted_da.shape})")
                # extraction_log[var][country]["result"] = "success"

                # Export Data
                export_preview_timeseries(
                    data=weighted_da,
                    output_base_dir=output_base_dir,
                    var_name=var,
                    region_name=country,
                )

                export_preview_monthly(
                    data=weighted_da,
                    output_base_dir=output_base_dir,
                    var_name=var,
                    region_name=country,
                )
            
            except Exception as e:
                # ถ้าพังตรงนี้ เราจะเห็น Error ชัดเจน แต่ไม่ทำให้ Loop หยุด
                print(f"FAILED!")
                print(f"      [CRITICAL ERROR] Could not process {country}: {e}")
                # print(traceback.format_exc()) # เปิดบรรทัดนี้ถ้าอยากเห็นบรรทัดที่พัง
                # extraction_log[var][country] = {
                #     "status": "error", 
                #     "error_msg": str(e)
                # }

        # Save Log
        # with open(f"{output_base_dir}/extraction_log.json", "w") as f:
        #     json.dump(extraction_log, f, indent=2)

        # ------------------
        #  Map (SEA only)
        # ------------------
        try:
            print(f"   -> Generating Map for {var}...")
            map_path = export_preview_map(
                data=da,
                output_base_dir=output_base_dir,
                var_name=var,
            )
            overlay_with_shapefile(map_path, shp_sea)
            print("      Map Done.")
        except Exception as e:
             print(f"[ERROR] Failed generating Map for {var}: {e}")

        results[var] = "done"

    return results
    #     for country in SEA_COUNTRIES:
    #         country_log = {}
    #         masked_da = mask_by_country(
    #             da,
    #             country,
    #             shp_countries,
    #             log=country_log
    #         )
    #         extraction_log[var][country] = country_log.get(country, {"status": "no_log_data"})

    #         if masked_da is not None and not masked_da.isnull().all():
    #             export_preview_timeseries(
    #                 data=masked_da,
    #                 output_base_dir=output_base_dir,
    #                 var_name=var,
    #                 region_name=country,
    #             )

    #             export_preview_monthly(
    #                 data=masked_da,
    #                 output_base_dir=output_base_dir,
    #                 var_name=var,
    #                 region_name=country,
    #             )

    #     with open(f"{output_base_dir}/extraction_log.json", "w") as f:
    #         json.dump(extraction_log, f, indent=2)

    #     # ------------------
    #     #  Map (SEA only)
    #     # ------------------
    #     map_path = export_preview_map(
    #         data=da,
    #         output_base_dir=output_base_dir,
    #         var_name=var,
    #     )
    #     overlay_with_shapefile(map_path, shp_sea)

    #     results[var] = "done"

    # return results
