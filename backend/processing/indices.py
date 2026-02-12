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


# def compute_pr_percentiles(ds: xr.Dataset, t_type: None):
#     pr_base = ds['pr'].sel(time=slice(str(ds.time.dt.year.min().item()),str(ds.time.dt.year.min().item() + 29)))
#     wet_days = pr_base.where(pr_base >= 1.0)
    
#     if t_type == "pr_95" :
#         out  = percentile_doy(wet_days, per=95, window=5).sel(percentiles=95)
#     if t_type == "pr_99" : 
#         out  = percentile_doy(wet_days, per=99, window=5).sel(percentiles=99)

#     return out 

def compute_pr_percentiles(ds: xr.Dataset, baseline=None, per_list=(95,)):
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

    out = {}
    for p in per_list:
        out[p] = percentile_doy(wet_days, per=p, window=5).sel(percentiles=p, drop=True)

    return out



# def compute_temp_percentiles(ds: xr.Dataset, t_type: None):
#     tmin_base = ds["tmin"].sel(time=slice(str(ds.time.dt.year.min().item()),str(ds.time.dt.year.min().item() + 29)))
#     tmax_base = ds["tmax"].sel(time=slice(str(ds.time.dt.year.min().item()),str(ds.time.dt.year.min().item() + 29)))

#     if t_type == "tmin_10":
#         out = percentile_doy(tmin_base, per=10, window=5).sel(percentiles=10)
#     if t_type == "tmin_90":
#         out = percentile_doy(tmin_base, per=90, window=5).sel(percentiles=90)
#     if t_type == "tmax_10":
#         out = percentile_doy(tmax_base, per=10, window=5).sel(percentiles=10)
#     if t_type == "tmax_90":
#         out = percentile_doy(tmax_base, per=90, window=5).sel(percentiles=90)
        
#     return out

def compute_temp_percentiles(ds: xr.Dataset, t_type: str, baseline=None):
    """
    Compute temperature percentiles using a baseline period.
    """
    # if baseline and baseline.start_year and baseline.end_year:
    tmin_base = slice_baseline(
        ds["tmin"],
        baseline.start_year if baseline else None,
        baseline.end_year if baseline else None,
    )

    tmax_base = slice_baseline(
        ds["tmax"],
        baseline.start_year if baseline else None,
        baseline.end_year if baseline else None,
    )

    if t_type == "tmin_10":
        return percentile_doy(tmin_base, per=10, window=5).sel(percentiles=10, drop=True)
    if t_type == "tmin_90":
        return percentile_doy(tmin_base, per=90, window=5).sel(percentiles=90, drop=True)
    if t_type == "tmax_10":
        return percentile_doy(tmax_base, per=10, window=5).sel(percentiles=10, drop=True)
    if t_type == "tmax_90":
        return percentile_doy(tmax_base, per=90, window=5).sel(percentiles=90, drop=True)


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
    pr_per = compute_pr_percentiles(ds, baseline=baseline, per_list=(95,))[95]
    return xc.indicators.icclim.R95p(pr=ds["pr"], pr_per=pr_per, freq=freq)

def r99p(ds: xr.Dataset, freq="YS", baseline=None):
    pr_per = compute_pr_percentiles(ds, baseline=baseline, per_list=(99,))[99]
    return xc.indicators.icclim.R99p(pr=ds["pr"], pr_per=pr_per, freq=freq)

def r95ptot(ds: xr.Dataset, freq="YS", baseline=None):
    pr_per = compute_pr_percentiles(ds, baseline=baseline, per_list=(95,))[95]
    return xc.indicators.icclim.R95pTOT(pr=ds["pr"], pr_per=pr_per, freq=freq)

def r99ptot(ds: xr.Dataset, freq="YS", baseline=None):
    pr_per = compute_pr_percentiles(ds, baseline=baseline, per_list=(99,))[99]
    return xc.indicators.icclim.R99pTOT(pr=ds["pr"], pr_per=pr_per, freq=freq)

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
    tmax_90 = compute_temp_percentiles(ds, t_type="tmax_90", baseline=baseline)
    return xc.indicators.icclim.WSDI(tasmax=ds["tmax"], tasmax_per=tmax_90, freq=freq)

def csdi(ds: xr.Dataset, freq="YS", baseline=None):
    tmin_10 = compute_temp_percentiles(ds, t_type="tmin_10", baseline=baseline)
    return xc.indicators.icclim.CSDI(tasmin=ds["tmin"], tasmax_per=tmin_10, freq=freq)

def tn10p(ds: xr.Dataset, freq="YS", baseline=None):
    tmin_10 = compute_temp_percentiles(ds, t_type="tmin_10", baseline=baseline)
    return xc.indicators.icclim.TN10p(tasmin=ds["tmin"], tasmin_per=tmin_10, freq=freq)

def tx10p(ds: xr.Dataset, freq="YS", baseline=None):
    tmax_10 = compute_temp_percentiles(ds, t_type="tmax_10", baseline=baseline)
    return xc.indicators.icclim.TX10p(tasmax=ds["tmax"], tasmax_per=tmax_10, freq=freq)

def tn90p(ds: xr.Dataset, freq="YS", baseline=None):
    per = compute_temp_percentiles(ds, t_type="tmin_90", baseline=baseline)
    return xc.indicators.icclim.TN90p(tasmin=ds["tmin"], tasmin_per=per, freq=freq)

def tx90p(ds: xr.Dataset, freq="YS", baseline=None):
    per = compute_temp_percentiles(ds, t_type="tmax_90", baseline=baseline)
    return xc.indicators.icclim.TX90p(tasmax=ds["tmax"], tasmax_per=per, freq=freq)

# ========================= SPI CALCULATION =========================
def spi(ds: xr.Dataset, window: int, freq="MS"):
    return xc.atmos.standardized_precipitation_index(
        pr=ds["pr"], freq=freq, window=window, dist="gamma", method="ML", ds=ds
    )

# ========================= Event characteristic per time series =========================
def event_characteristics(spi_ts, threshold=-1.0, event_type="drought"):
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

# ==================== Registry ====================
# INDICES_REGISTRY = {
    # "SDII": sdii,
    # "Rx1day": rx1day,
    # "Rx5day": rx5day,
    # "R10mm": r10mm,
    # "R20mm": r20mm,
    # "PRCPTOT": prcptot,
    # "TXx": txx,
    # "TNx": tnx,
    # "TXn": txn,
    # "TNn": tnn,
    # "DTR": dtr,
    # "ETR": etr,
    # "FD": fd,
    # "SU": su,
    # "ID": id,
    # "TR": tr,
    # "CDD": cdd,
    # "CWD": cwd,
    # "WSDI": wsdi,
    # "CSDI": csdi,
    # "R95p": r95p,
    # "R99p": r99p,
    # "R95pTOT": r95ptot,
    # "R99pTOT": r99ptot,
    # "TN10p": tn10p,
    # "TX10p": tx10p,
    # "TN90p": tn90p,
    # "TX90p": tx90p,
# }

def calculate_spi_group(ds, window: int) -> dict:
    """
    Calculate SPI only window (3,6,9,12)
    """
    base_spi = f"SPI{window}"
    spi_data = spi(ds=ds, window=window, freq="MS")

    return {base_spi: spi_data}


def spi_event_factory(window, event_type, threshold, metric):
    """
    create event metrics for window, event_type, metric
    only user call
    """
    def compute(ds, freq):
        # calulate SPI
        spi_data = spi(ds=ds, window=window, freq="MS")

        # calulate event map
        maps = calc_event_maps(spi_data, threshold, event_type.lower())

        return maps[metric]

    return compute

def build_spi_event_indices(selected_indices):
    """
    check user select SPI window ? (like SPI3)
    creat event indices only that window 
    """
    event_indices = {}

    spi_windows = []
    for idx in selected_indices:
        if idx.startswith("SPI") and idx[3:].isdigit():
            spi_windows.append(int(idx[3:]))

    for window in spi_windows:
        for event_type, threshold in [("Drought", -1.0), ("Flood", 1.0)]:
            for metric in ["Frequency", "Duration", "Peak", "Severity"]:
                name = f"SPI{window}_{event_type}_{metric}"
                event_indices[name] = spi_event_factory(window, event_type, threshold, metric)

    return event_indices

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
}

TMIN_INDICES = {
    "TNx": tnx,
    "TNn": tnn,
    "FD": fd,
    "ID": id,
    "TN10p": tn10p,
    "TN90p": tn90p,
}

SPI_INDICES = {
    "SPI3": lambda ds, freq: calculate_spi_group(ds, 3)["SPI3"],
    "SPI6": lambda ds, freq: calculate_spi_group(ds, 6)["SPI6"],
    "SPI9": lambda ds, freq: calculate_spi_group(ds, 9)["SPI9"],
    "SPI12": lambda ds, freq: calculate_spi_group(ds, 12)["SPI12"],
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

def calculate_all_indices(ds: xr.Dataset, freq="YS", selected_indices=None, baseline=None) -> xr.Dataset:

    print(f"Calculating Indices")

    results = {}

    active_registry = {
        **PR_INDICES,
        **TMAX_INDICES,
        **TMIN_INDICES,
        **SPI_INDICES,
    }

    if selected_indices is not None:
        spi_event_registry = build_spi_event_indices(selected_indices)
        active_registry.update(spi_event_registry)

    for name, func in active_registry.items():

        if selected_indices is not None:
            if name not in selected_indices:
                continue
            
        print(f"Calculating {name} ...")
            
        # try:
        #     results[name] = func(ds, freq=freq)
        # except Exception as e:
        #     print(f"Error calculating {name}: {e}")
        try:
            # results[name] = func(ds, freq=freq)
            if name in BASELINE_REQUIRED_INDICES:
                results[name] = func(ds, freq=freq, baseline=baseline)
            else:
                results[name] = func(ds, freq=freq)
        except KeyError:
            raise ValueError(f"Index {name} requires missing variables")
        except Exception as e:
            print(f"Error calculating {name}: {e}")
            raise ValueError(f"Failed calculating {name}: {e}")
    
    return xr.Dataset(results)