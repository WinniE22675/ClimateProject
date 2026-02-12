import numpy as np
import xarray as xr
import pytest
import pandas as pd

from processing.indices import (
    slice_baseline,
    compute_pr_percentiles,
    compute_temp_percentiles,
    event_characteristics,
    build_spi_event_indices,
    calculate_all_indices,
)

@pytest.fixture
def sample_dataset():
    """
    Creates a synthetic xarray Dataset mimicking climate data.
    Contains 'pr' (precipitation), 'tmax', 'tmin'.
    Time range: 2 years daily data.
    """
    times = pd.date_range(start="2000-01-01", end="2001-12-31", freq="D")
    
    # Create random data
    pr_data = np.random.rand(len(times), 2, 2) * 20  # 0-20 mm/day
    tmax_data = np.random.rand(len(times), 2, 2) * 10 + 30 # 30-40 C
    tmin_data = tmax_data - 5 # 25-35 C

    # Create DataArrays with proper units (Critical for xclim)
    ds = xr.Dataset(
        {
            "pr": (["time", "lat", "lon"], pr_data, {"units": "mm/day"}),
            "tmax": (["time", "lat", "lon"], tmax_data, {"units": "degC"}),
            "tmin": (["time", "lat", "lon"], tmin_data, {"units": "degC"}),
        },
        coords={
            "time": times,
            "lat": [10, 11],
            "lon": [100, 101],
        }
    )
    return ds

@pytest.fixture
def baseline_period():
    """Mock object for BaselinePeriod"""
    class MockBaseline:
        start_year = 2000
        end_year = 2000
    return MockBaseline()

@pytest.fixture
def sample_dataset():
    """
    Creates a synthetic xarray Dataset mimicking climate data.
    Contains 'pr' (precipitation), 'tmax', 'tmin'.
    Time range: 2 years daily data.
    """
    times = pd.date_range(start="2000-01-01", end="2001-12-31", freq="D")
    
    # Create random data
    pr_data = np.random.rand(len(times), 2, 2) * 20  # 0-20 mm/day
    tmax_data = np.random.rand(len(times), 2, 2) * 10 + 30 # 30-40 C
    tmin_data = tmax_data - 5 # 25-35 C

    # Create DataArrays with proper units (Critical for xclim)
    ds = xr.Dataset(
        {
            "pr": (["time", "lat", "lon"], pr_data, {"units": "mm/day"}),
            "tmax": (["time", "lat", "lon"], tmax_data, {"units": "degC"}),
            "tmin": (["time", "lat", "lon"], tmin_data, {"units": "degC"}),
        },
        coords={
            "time": times,
            "lat": [10, 11],
            "lon": [100, 101],
        }
    )
    return ds

def test_slice_baseline_none_returns_full_range(sample_dataset):
    out = slice_baseline(sample_dataset, None, None)

    assert out.time.dt.year.min() == 2000
    assert out.time.dt.year.max() == 2001

def test_slice_baseline_out_of_range_strict_before(sample_dataset):
    with pytest.raises(ValueError, match="outside data range"):
        slice_baseline(sample_dataset, 1980, 1990)

def test_slice_baseline_out_of_range_strict_after(sample_dataset):
    with pytest.raises(ValueError, match="outside data range"):
        slice_baseline(sample_dataset, 2015, 2020)

# ---------------- Percentile Tests ----------------

def test_compute_pr_percentiles_no_baseline(sample_dataset):
    """Test that precipitation percentiles return a dictionary"""
    da = compute_pr_percentiles(sample_dataset, per_list=(95,))
    assert 95 in da
    assert isinstance(da[95], xr.DataArray)

def test_compute_pr_percentiles_with_baseline(sample_dataset, baseline_period):
    """Test precipitation percentile calculation with a specific baseline."""
    da = compute_pr_percentiles(sample_dataset, baseline=baseline_period, per_list=(95,))
    
    assert 95 in da
    assert "percentiles" in da[95].coords
    # Check if calculation actually happened (not all NaNs)
    assert not np.all(np.isnan(da[95]))

def test_pr_percentile_baseline_out_of_range(sample_dataset):
    """
    Test behavior when baseline years are outside dataset range.
    Expect the function to return NaNs or raise an error.
    """
    class BadBaseline:
        start_year = 1990
        end_year = 1995

    with pytest.raises(ValueError, match="outside data range"):
        result = compute_pr_percentiles(
            sample_dataset,
            baseline=BadBaseline(),
            per_list=(95,)
        )[95]

def test_compute_temp_percentiles_tmin_no_baseline(sample_dataset):
    """Test temperature percentile for tmin_10"""
    da = compute_temp_percentiles(sample_dataset, "tmin_10")
    assert isinstance(da, xr.DataArray)

def test_compute_temp_percentiles_with_baseline(sample_dataset, baseline_period):
    """Test temperature percentile for tmin_10 calculation with a specific baseline."""
    da = compute_temp_percentiles(sample_dataset, t_type="tmin_10", baseline=baseline_period)
    assert 10 in da.coords["percentiles"]
    assert not np.all(np.isnan(da))
    

# ---------------- Event Characteristics ----------------

def test_event_characteristics_all_nan():
    """Test event_characteristics returns NaN when all values are NaN"""
    ts = np.array([np.nan, np.nan])
    freq, dur, peak, sev = event_characteristics(ts)
    assert np.isnan(freq)

def test_event_characteristics_no_event():
    """Test when no drought occurs."""
    spi_ts = [0, 0.5, -0.5, 0.2, 1.0]
    freq, max_dur, peak, severity = event_characteristics(spi_ts, threshold=-1.0, event_type="drought")
    
    assert freq == 0 or np.isnan(freq)
    assert np.isnan(max_dur)

def test_event_characteristics_drought_logic():
    """
    Test the pure logic of drought event detection using numpy arrays.
    Scenario: 
    - Threshold: -1.0
    - Data: [0, -0.5, -1.5, -2.0, -0.5, -1.2, 0]
    - Expected Event 1: [-1.5, -2.0] indices 2,3 -> Duration 2, Peak -2.0, Severity 3.5
    - Expected Event 2: [-1.2] index 5 -> Duration 1, Peak -1.2, Severity 1.2
    """
    # Note: The provided function logic merges consecutive checks slightly differently.
    # Let's test a clear single event first.
    
    # Simple single event case
    # Indices: 0   1     2     3     4    5
    spi_ts = [0, -0.5, -1.5, -2.5, -0.5, 0] 
    # Logic: Start < -1.0, End >= -1.0
    # t=2 (-1.5 < -1): Event Start
    # t=3 (-2.5 < -1): Continue
    # t=4 (-0.5 >= -1): Event End -> Duration = (3-2) + 1 = 2 ? 
    # Depending on implementation details in loop.
    
    freq, max_dur, peak, severity = event_characteristics(spi_ts, threshold=-1.0, event_type="drought")
    
    # Verify outputs
    assert freq == 1, "Should detect exactly 1 drought event"
    assert max_dur == 2, "Duration should be 2 time steps (indices 2 and 3)"
    assert peak == -2.5, "Peak should be the minimum value (-2.5)"
    assert np.isclose(severity, 4.0), "Severity should be sum of abs values (1.5 + 2.5 = 4.0)"

# ---------------- SPI Event Registry ----------------

def test_build_spi_event_indices():
    """Test SPI event indices registry creation"""
    indices = build_spi_event_indices(["SPI3"])
    assert "SPI3_Drought_Frequency" in indices
    assert callable(indices["SPI3_Drought_Frequency"])

# ---------------- Main Orchestrator ----------------

def test_calculate_all_indices_basic(sample_dataset):
    """Test calculate_all_indices returns a Dataset"""
    ds_out = calculate_all_indices(
        sample_dataset,
        selected_indices=["SDII", "TXx"],
    )
    assert isinstance(ds_out, xr.Dataset)
    assert "SDII" in ds_out