import xarray as xr
import xclim as xc
import numpy as np
from xclim.core.calendar import percentile_doy

def slice_baseline(
    da: xr.DataArray,
    start_year: int | None,
    end_year: int | None,
) -> xr.DataArray:
    """
    Slice baseline safely.
    """

    data_start = da.time.dt.year.min().item()
    data_end = da.time.dt.year.max().item()

    # baseline not provided → full data
    if start_year is None or end_year is None:
        return da.sel(time=slice(str(data_start), str(data_end)))

    # baseline outside data
    if end_year < data_start or start_year > data_end:
        raise ValueError(
                f"Baseline {start_year}-{end_year} "
                f"is outside data range {data_start}-{data_end}"
        )

    baseline = da.sel(
        time=slice(str(start_year), str(end_year))
    )

    if baseline.time.size == 0:
        raise ValueError("Baseline slicing produced empty data")

    return baseline

def compute_pr_percentiles(ds: xr.Dataset, percentile: int, baseline=None):
    """
    Compute precipitation percentiles using a baseline period.
    If baseline is None, fallback to first 30 years.
    """
    # if baseline and baseline.start_year and baseline.end_year:
    pr_base = slice_baseline(
        ds["pr"],
        baseline.start_year if baseline else None,
        baseline.end_year if baseline else None,
    )

    wet_days = pr_base.where(pr_base >= 1.0)

    return percentile_doy(wet_days, per=percentile, window=5).sel(percentiles=percentile, drop=True)

def compute_temp_percentiles(ds: xr.Dataset, var_name: str, percentile: int, baseline=None):
    """
    Compute temperature percentiles using a baseline period.
    """
    temp_data = ds[var_name]

    temp_base = slice_baseline(
        temp_data,
        baseline.start_year if baseline else None,
        baseline.end_year if baseline else None,
    )
    
    return percentile_doy(temp_base, per=percentile, window=5).sel(percentiles=percentile, drop=True)

# ==================== Precipitation Indices ====================
def sdii(ds: xr.Dataset, freq="YS"):
    return xc.indicators.icclim.SDII(pr=ds["pr"], freq=freq)

def rx1day(ds: xr.Dataset, freq="YS"):
    return xc.indicators.icclim.RX1day(pr=ds["pr"], freq=freq)

def rx5day(ds: xr.Dataset, freq="YS"):
    return xc.indicators.icclim.RX5day(pr=ds["pr"], freq=freq)

def r10mm(ds: xr.Dataset, freq="YS"):
    return xc.indicators.icclim.R10mm(pr=ds["pr"], freq=freq)

def r20mm(ds: xr.Dataset, freq="YS"):
    return xc.indicators.icclim.R20mm(pr=ds["pr"], freq=freq)

def prcptot(ds: xr.Dataset, freq="YS"):
    return xc.indicators.icclim.PRCPTOT(pr=ds["pr"], freq=freq)

def r95p(ds: xr.Dataset, freq="YS", baseline=None):
    pr_95 = compute_pr_percentiles(ds, percentile=95, baseline=baseline)
    return xc.indicators.icclim.R95p(pr=ds["pr"], pr_per=pr_95, freq=freq)

def r99p(ds: xr.Dataset, freq="YS", baseline=None):
    pr_99 = compute_pr_percentiles(ds, percentile=99, baseline=baseline)
    return xc.indicators.icclim.R99p(pr=ds["pr"], pr_per=pr_99, freq=freq)

def r95ptot(ds: xr.Dataset, freq="YS", baseline=None):
    pr_95 = compute_pr_percentiles(ds, percentile=95, baseline=baseline)
    return xc.indicators.icclim.R95pTOT(pr=ds["pr"], pr_per=pr_95, freq=freq)

def r99ptot(ds: xr.Dataset, freq="YS", baseline=None):
    pr_99 = compute_pr_percentiles(ds, percentile=99, baseline=baseline)
    return xc.indicators.icclim.R99pTOT(pr=ds["pr"], pr_per=pr_99, freq=freq)

# ==================== Temperature Indices ====================
def txx(ds: xr.Dataset, freq="YS"):
    return xc.indicators.icclim.TXx(tasmax=ds["tmax"], freq=freq)

def tnx(ds: xr.Dataset, freq="YS"):
    return xc.indicators.icclim.TNx(tasmin=ds["tmin"], freq=freq)

def txn(ds: xr.Dataset, freq="YS"):
    return xc.indicators.icclim.TXn(tasmax=ds["tmax"], freq=freq)

def tnn(ds: xr.Dataset, freq="YS"):
    return xc.indicators.icclim.TNn(tasmin=ds["tmin"], freq=freq)

# def dtr(ds: xr.Dataset, freq="YS"):
#     return xc.indicators.icclim.DTR(tasmax=ds["tasmax"], tasmin=ds["tasmin"], freq=freq)

# def etr(ds: xr.Dataset, freq="YS"):
#     return xc.indicators.icclim.ETR(tasmax=ds["tasmax"], tasmin=ds["tasmin"], freq=freq)

def fd(ds: xr.Dataset, freq="YS"):
    return xc.indicators.icclim.FD(tasmin=ds["tmin"], freq=freq)

def su(ds: xr.Dataset, freq="YS"):
    return xc.indicators.icclim.SU(tasmax=ds["tmax"], freq=freq)

def id(ds: xr.Dataset, freq="YS"):
    return xc.indicators.icclim.ID(tasmax=ds["tmax"], freq=freq)

def tr(ds: xr.Dataset, freq="YS"):
    return xc.indicators.icclim.TR(tasmin=ds["tmin"], freq=freq)

def cdd(ds: xr.Dataset, freq="YS"):
    return xc.indicators.icclim.CDD(pr=ds["pr"], freq=freq)

def cwd(ds: xr.Dataset, freq="YS"):
    return xc.indicators.icclim.CWD(pr=ds["pr"], freq=freq)

def wsdi(ds: xr.Dataset, freq="YS", baseline=None):
    tmax_90 = compute_temp_percentiles(ds, var_name="tmax", percentile=90, baseline=baseline)
    return xc.indicators.icclim.WSDI(tasmax=ds["tmax"], tasmax_per=tmax_90, freq=freq)

def csdi(ds: xr.Dataset, freq="YS", baseline=None):
    tmin_10 = compute_temp_percentiles(ds, var_name="tmin", percentile=10, baseline=baseline)
    return xc.indicators.icclim.CSDI(tasmin=ds["tmin"], tasmin_per=tmin_10, freq=freq)

def tn10p(ds: xr.Dataset, freq="YS", baseline=None):
    tmin_10 = compute_temp_percentiles(ds, var_name="tmin", percentile=10, baseline=baseline)
    return xc.indicators.icclim.TN10p(tasmin=ds["tmin"], tasmin_per=tmin_10, freq=freq)

def tx10p(ds: xr.Dataset, freq="YS", baseline=None):
    tmax_10 = compute_temp_percentiles(ds, var_name="tmax", percentile=10, baseline=baseline)
    return xc.indicators.icclim.TX10p(tasmax=ds["tmax"], tasmax_per=tmax_10, freq=freq)

def tn90p(ds: xr.Dataset, freq="YS", baseline=None):
    tmin_90 = compute_temp_percentiles(ds, var_name="tmin", percentile=90, baseline=baseline)
    return xc.indicators.icclim.TN90p(tasmin=ds["tmin"], tasmin_per=tmin_90, freq=freq)

def tx90p(ds: xr.Dataset, freq="YS", baseline=None):
    tmax_90 = compute_temp_percentiles(ds, var_name="tmax", percentile=90, baseline=baseline)
    return xc.indicators.icclim.TX90p(tasmax=ds["tmax"], tasmax_per=tmax_90, freq=freq)

# ========================= SPI CALCULATION =========================
def spi(ds: xr.Dataset, window: int, freq="MS"):
    return xc.atmos.standardized_precipitation_index(
        pr=ds["pr"], freq=freq, window=window, dist="gamma", method="ML", ds=ds
    )

# ========================= Event characteristic per time series =========================
def event_characteristics(spi_ts, threshold=-1.0, event_type="drought", min_duration=2):
    values = np.asarray(spi_ts)
    n = len(values)
    if np.all(np.isnan(values)):
        return np.nan, np.nan, np.nan, np.nan

    events = []
    in_event = False
    start = None

    for t in range(n):
        if event_type == "drought":
            cond_start = values[t] < threshold
            cond_end = values[t] >= threshold
        else:
            cond_start = values[t] > abs(threshold)
            cond_end = values[t] <= abs(threshold)

        if cond_start and not in_event:
            in_event = True
            start = t
        elif cond_end and in_event:
            end = t - 1
            events.append((start, end))
            in_event = False
    if in_event:
        events.append((start, n - 1))

    events = [e for e in events if (e[1] - e[0] + 1) >= min_duration]

    durations, peaks, severities = [], [], []
    for (s, e) in events:
        dur = e - s + 1
        peak = np.min(values[s:e+1]) if event_type == "drought" else np.max(values[s:e+1])
        sev = np.sum(-values[s:e+1]) if event_type == "drought" else np.sum(values[s:e+1])
        durations.append(dur)
        peaks.append(peak)
        severities.append(sev)

    freq = len(events) if len(events) > 0 else np.nan
    max_duration = np.max(durations) if durations else np.nan
    extreme_peak = np.min(peaks) if event_type == "drought" and peaks else (np.max(peaks) if peaks else np.nan)
    mean_severity = np.mean(severities) if severities else np.nan

    return freq, max_duration, extreme_peak, mean_severity

def calc_event_maps(spi: xr.DataArray, threshold=-1.0, event_type="drought"):
    results = xr.apply_ufunc(
        lambda x: np.array(event_characteristics(x, threshold, event_type)),
        spi,
        input_core_dims=[["time"]],
        output_core_dims=[["metric"]],
        vectorize=True,
        dask="parallelized",
        output_dtypes=[float],
        dask_gufunc_kwargs={"output_sizes": {"metric": 4}}
    )

    results = results.assign_coords(metric=["freq", "duration", "peak", "severity"])

    freq_map = results.sel(metric="freq")
    dur_map = results.sel(metric="duration")
    peak_map = results.sel(metric="peak")
    sev_map = results.sel(metric="severity")

    t_start = spi.time.min().values
    t_end = spi.time.max().values

    out = {
        "Frequency": freq_map.expand_dims(time=[t_start, t_end]).drop_vars("metric"),
        "Duration": dur_map.expand_dims(time=[t_start, t_end]).drop_vars("metric"),
        "Peak": peak_map.expand_dims(time=[t_start, t_end]).drop_vars("metric"),
        "Severity": sev_map.expand_dims(time=[t_start, t_end]).drop_vars("metric"),
    }

    return out

PR_INDICES = {
    "SDII": sdii,
    "Rx1day": rx1day,
    "Rx5day": rx5day,
    "R10mm": r10mm,
    "R20mm": r20mm,
    "PRCPTOT": prcptot,
    "CDD": cdd,
    "CWD": cwd,
    "R95p": r95p,
    "R99p": r99p,
    "R95pTOT": r95ptot,
    "R99pTOT": r99ptot,
}

TMAX_INDICES = {
    "TXx": txx,
    "TXn": txn,
    "SU": su,
    "TR": tr,
    "TX10p": tx10p,
    "TX90p": tx90p,
    "WSDI": wsdi,
}

TMIN_INDICES = {
    "TNx": tnx,
    "TNn": tnn,
    "FD": fd,
    "ID": id,
    "TN10p": tn10p,
    "TN90p": tn90p,
    "CSDI": csdi,
}

SPI_INDICES = {
    "SPI3": lambda ds, freq: spi(ds=ds, window=3, freq="MS"),
    "SPI6": lambda ds, freq: spi(ds=ds, window=6, freq="MS"),
    "SPI9": lambda ds, freq: spi(ds=ds, window=9, freq="MS"),
    "SPI12": lambda ds, freq: spi(ds=ds, window=12, freq="MS"),
}

BASELINE_REQUIRED_INDICES = {
    # Precipitation percentiles
    "R95p",
    "R99p",
    "R95pTOT",
    "R99pTOT",

    # Temperature percentiles
    "TX10p",
    "TX90p",
    "TN10p",
    "TN90p",

    # Extreme duration indices (if used)
    "WSDI",
    "CSDI",
}

SPI_WINDOWS = [3, 6, 9, 12] 

import xarray as xr

def convert_temperature_unit(da: xr.DataArray) -> xr.DataArray:
    """
    Convert Kelvin to Celsius if the unit is Kelvin.
    Leave other units (like 'days', '%', 'mm', 'C') unchanged.
    """
    units = da.attrs.get("units", "").lower().strip()
    original_attrs = da.attrs.copy()

    # If the unit is Kelvin, perform the conversion
    if units in ["k", "kelvin", "degk"]:
        da_converted = da - 273.15
        da_converted.attrs = original_attrs
        da_converted.attrs["units"] = "C"
        return da_converted

    # For all other units ('c', 'days', '%', 'mm'), return as-is safely
    return da

def calculate_all_indices(ds: xr.Dataset, freq="YS", selected_indices=None, baseline=None, spi_threshold: float = 1) -> xr.Dataset:
    print(f"Calculating Indices")

    results = {}

    active_registry = {
        **PR_INDICES,
        **TMAX_INDICES,
        **TMIN_INDICES,
    }

    requested_spi_windows = set()
    if selected_indices is None:
        requested_spi_windows = set(SPI_WINDOWS)
    else:
        for idx in selected_indices:
            if idx.startswith("SPI") and idx[3:].isdigit():
                # Extract window e.g., "SPI3" -> 3, "SPI3_Drought_..." -> 3
                try:
                    window_str = "".join(filter(str.isdigit, idx.split("_")[0]))
                    if window_str:
                        requested_spi_windows.add(int(window_str))
                except ValueError:
                    continue

    # 3. Calculate General Indices (Non-SPI)
    for name, func in active_registry.items():
        if selected_indices is not None:
            if name not in selected_indices:
                continue
            
        print(f"Calculating {name} ...")
        try:
            if name in BASELINE_REQUIRED_INDICES:
                # results[name] = func(ds, freq=freq, baseline=baseline)
                index_result = func(ds, freq=freq, baseline=baseline)
            else:
                # results[name] = func(ds, freq=freq)
                index_result = func(ds, freq=freq)

            index_result = convert_temperature_unit(index_result)

            # Store the final result
            results[name] = index_result

        except KeyError:
            raise ValueError(f"Index {name} requires missing variables")
        except Exception as e:
            print(f"Error calculating {name}: {e}")
            raise ValueError(f"Failed calculating {name}: {e}")

    # 4. Calculate SPI and related Event Indices (Optimized Block)
    for window in requested_spi_windows:
        if window not in SPI_WINDOWS:
            continue

        base_name = f"SPI{window}"
        print(f"Calculating {base_name} and events ...")

        try:
            # Step 4.1: Calculate SPI ONCE
            # Ensure freq matches your SPI requirements (e.g., "MS")
            spi_data = spi(ds=ds, window=window, freq="MS")
            
            if selected_indices is None or base_name in selected_indices:
                results[base_name] = spi_data

            # Step 4.2: Calculate Event Maps using the SAME spi_data
            # Define event configurations
            if freq == "YS":
                safe_threshold = abs(spi_threshold)
                # event_configs = [("Drought", -1.0), ("Flood", 1.0)]
                event_configs = [("Drought", -safe_threshold), ("Flood", safe_threshold)]
                metrics = ["Frequency", "Duration", "Peak", "Severity"]

                for event_type, threshold in event_configs:
                    # Calculate maps once per event type
                    spi_data_rechunked = spi_data.chunk({"time": -1})

                    maps = calc_event_maps(spi_data_rechunked, threshold=threshold, event_type=event_type.lower())

                    for metric in metrics:
                        # Construct key: e.g., "SPI3_Drought_Frequency"
                        full_key = f"{base_name}_{event_type}_{metric}"
                        
                        if selected_indices is None or base_name in selected_indices:
                            results[full_key] = maps[metric]

        except Exception as e:
            print(f"Error calculating SPI{window} group: {e}")
            raise ValueError(f"Failed calculating SPI{window} group: {e}")

    return xr.Dataset(results)