import pytest
import shutil
import os
import xarray as xr
import numpy as np
import pandas as pd
from types import SimpleNamespace
from processing.indices import (
    slice_baseline,
    compute_pr_percentiles, 
    compute_temp_percentiles, 
    event_characteristics, 
    calc_event_maps, 
    calculate_all_indices, 
    BASELINE_REQUIRED_INDICES
)
from unittest.mock import patch, MagicMock

# --- Fixtures for creating dummy data ---

@pytest.fixture
def sample_da():
    """
    Creates a sample DataArray with daily data from 2000 to 2005.
    Values are random.
    """
    times = pd.date_range("2000-01-01", "2005-12-31", freq="D")
    data = np.random.rand(len(times)) * 10  # Values between 0 and 10
    da = xr.DataArray(
        data,
        coords={"time": times},
        dims="time",
        name="data"
    )
    return da

@pytest.fixture
def sample_ds(sample_da):
    """
    Creates a sample Dataset containing 'pr', 'tmin', and 'tmax'.
    """
    # Create precipitation with some dry days (< 1.0) and wet days (>= 1.0)
    pr_data = sample_da.copy()
    pr_data.values[:10] = 0.5   # Ensure some dry days
    pr_data.values[10:20] = 5.0 # Ensure some wet days
    
    # Create temperature data
    tmin = sample_da.copy() - 5
    tmax = sample_da.copy() + 5
    
    return xr.Dataset({
        "pr": pr_data,
        "tmin": tmin,
        "tmax": tmax
    })

@pytest.fixture
def constant_ds():
    """
    Creates a dataset with CONSTANT values for calculation verification.
    """
    times = pd.date_range("2000-01-01", "2002-12-31", freq="D")
    # PR: Mixture of 0.0 (Dry) and 100.0 (Wet) to test filtering
    pr_data = np.zeros(len(times))
    pr_data[::2] = 100.0  # Every alternate day is wet (100.0)
    
    # tmin is always 10.0, tmax is always 30.0
    tmin_data = np.full(len(times), 10.0)
    tmax_data = np.full(len(times), 30.0)
    
    ds = xr.Dataset({
        "pr": xr.DataArray(pr_data, coords={"time": times}, dims="time"),
        "tmin": xr.DataArray(tmin_data, coords={"time": times}, dims="time"),
        "tmax": xr.DataArray(tmax_data, coords={"time": times}, dims="time")
    })
    return ds

@pytest.fixture
def mock_baseline():
    """
    Creates a mock object acting as the baseline configuration.
    """
    return SimpleNamespace(start_year=2001, end_year=2002)


def setUp(self):
        
        base_dir = os.path.dirname(os.path.abspath(__file__)) # .../backend/tests
        self.upload_dir = os.path.join(base_dir, "..", "uploads", "merged") # .../backend/tests/../uploads/merged
        
        os.makedirs(self.upload_dir, exist_ok=True)

def tearDown(self):
        """
        Runs AFTER each test method.
        Clean up the artifact files.
        """
        if os.path.exists(self.upload_dir):
            try:
                shutil.rmtree(self.upload_dir) # Delete folder & all contents
                os.makedirs(self.upload_dir)   # Re-create empty folder
                # print(f"Cleaned up: {self.upload_dir}")
            except Exception as e:
                print(f"Error cleaning up {self.upload_dir}: {e}")


# --- Tests for slice_baseline ---

def test_slice_baseline_valid_range(sample_da):
    """
    Test ensuring slice_baseline returns correct subset of data when years are valid.
    """
    # Arrange
    start_year = 2001
    end_year = 2002
    
    # Act
    result = slice_baseline(sample_da, start_year, end_year)
    
    # Assert
    assert result.time.dt.year.min() == 2001
    assert result.time.dt.year.max() == 2002
    assert result.sizes['time'] < sample_da.sizes['time']

def test_slice_baseline_returns_full_data_when_args_none(sample_da):
    """
    Test ensuring slice_baseline returns the original data if start or end year is None.
    """
    # Arrange
    start_year = None
    end_year = None
    
    # Act
    result = slice_baseline(sample_da, start_year, end_year)
    
    # Assert
    xr.testing.assert_identical(result, sample_da)

def test_slice_baseline_raises_error_outside_range(sample_da):
    """
    Test ensuring ValueError is raised when baseline is strictly outside data range.
    """
    # Arrange
    start_year = 1990 # Before data starts (2000)
    end_year = 1995
    
    # Act & Assert
    with pytest.raises(ValueError, match="is outside data range"):
        slice_baseline(sample_da, start_year, end_year)

def test_slice_baseline_raises_error_when_start_year_greater_than_end_year(sample_da):
    """
    Test ensuring ValueError is raised when start_year is greater than end_year.
    In xarray, slicing with start > end results in an empty DataArray, 
    triggering the 'empty data' check.
    """
    # Arrange
    # Data range is 2000-2005
    start_year = 2003
    end_year = 2001  # Invalid: End is before Start
    
    # Act & Assert
    # This should trigger "Baseline slicing produced empty data"
    with pytest.raises(ValueError, match="Baseline slicing produced empty data"):
        slice_baseline(sample_da, start_year, end_year)

# --- Tests for compute_pr_percentiles (1 Cases) ---

def test_compute_pr_percentiles_calculation_logic(constant_ds, mock_baseline):
    """
    Case 2: Calculation & Logic Check
    Verifies that dry days (< 1.0) are ignored in percentile calculation.
    Input: Alternating 0.0 and 100.0
    Expected: Percentile should be calculated ONLY from 100.0 values.
              So, the 95th percentile of [100, 100, ...] must be 100.
    """
    # Arrange
    # constant_ds has 0.0 and 100.0 alternating.
    
    # Act
    res_50 = compute_pr_percentiles(constant_ds, percentile=50, baseline=mock_baseline)
    res_95 = compute_pr_percentiles(constant_ds, percentile=95, baseline=mock_baseline)
    
    # Assert
    # If 0.0 was included, the median (50th) would be closer to 50 or 0.
    # Since 0.0 is filtered, we only have 100s. Median of 100s is 100.
    np.testing.assert_allclose(res_50.values, 100.0, rtol=1e-5)
    np.testing.assert_allclose(res_95.values, 100.0, rtol=1e-5)

# --- Tests for compute_temp_percentiles (1 Cases) ---

def test_compute_temp_percentiles_calculation_correctness(constant_ds, mock_baseline):
    """
    Case 2: Calculation Check
    Verifies that percentiles are calculated correctly using constant data.
    Input: Constant 25.0 degrees.
    Expected: Any percentile of a constant set is that constant.
    """
    # Arrange
    # constant_ds has tmin=25.0 and tmax=25.0
    
    # Act
    res_10 = compute_temp_percentiles(constant_ds, var_name="tmin", percentile=10, baseline=mock_baseline)
    res_90 = compute_temp_percentiles(constant_ds, var_name="tmax", percentile=90, baseline=mock_baseline)
    
    # Assert
    # We use allclose to handle potential floating point nuances, 
    # though exact matches are expected for constants.
    np.testing.assert_allclose(res_10.values, 10.0, rtol=1e-5)
    np.testing.assert_allclose(res_90.values, 30.0, rtol=1e-5)

# --- Tests for event_characteristics (6 Case) ---

def test_event_characteristics_drought_logic():
    """
    Test logic for detecting drought events (values < threshold).
    
    Data: [0, -0.5, -1.2, -2.0, -0.9, 0, -1.5, 0]
    Threshold: -1.0
    
    Expected Analysis:
    - Event 1 (Indices 2, 3): Values [-1.2, -2.0]
        - Duration: 2
        - Peak: -2.0 (Min)
        - Severity: |-1.2| + |-2.0| = 3.2
    - Event 2 (Index 6): Value [-1.5]
        - Duration: 1
        - Peak: -1.5
        - Severity: 1.5
        
    Aggregates:
    - Frequency: 1
    - Max Duration: 2
    - Extreme Peak: -2.0 (Min of peaks)
    - Mean Severity: 3.2
    """
    # Arrange
    spi_ts = [0, -0.5, -1.2, -2.0, -0.9, 0, -1.5, 0]
    threshold = -1.0
    
    # Act
    freq, max_dur, ext_peak, mean_sev = event_characteristics(
        spi_ts, threshold=threshold, event_type="drought", min_duration=2
    )
    
    # Assert
    assert freq == 1
    assert max_dur == 2
    np.testing.assert_allclose(ext_peak, -2.0, rtol=1e-5)
    np.testing.assert_allclose(mean_sev, 3.2, rtol=1e-5)

def test_event_characteristics_flood_logic():
    """
    Test logic for detecting flood events (values > abs(threshold)).
    
    Data: [0, 1.5, 2.5, 0]
    Threshold: 1.0 (checks > 1.0)
    
    Expected Analysis:
    - Event 1 (Indices 1, 2): Values [1.5, 2.5]
        - Duration: 2
        - Peak: 2.5 (Max)
        - Severity: 1.5 + 2.5 = 4.0
    """
    # Arrange
    spi_ts = [0, 1.5, 2.5, 0]
    threshold = 1.0 # Logic uses abs(threshold), so 1.0 works
    
    # Act
    freq, max_dur, ext_peak, mean_sev = event_characteristics(
        spi_ts, threshold=threshold, event_type="flood", min_duration=2
    )
    
    # Assert
    assert freq == 1
    assert max_dur == 2
    np.testing.assert_allclose(ext_peak, 2.5, rtol=1e-5)
    np.testing.assert_allclose(mean_sev, 4.0, rtol=1e-5)

def test_event_characteristics_boundary_events():
    """
    Test events that start at index 0 or end at the last index.
    Ensures the loop handles boundaries correctly.
    
    Data: [-2.0, -2.0] (All below threshold -1.0)
    """
    # Arrange
    spi_ts = [-2.0, -2.0]
    threshold = -1.0
    
    # Act
    freq, max_dur, _, _ = event_characteristics(spi_ts, threshold=threshold, event_type="drought", min_duration=2)
    
    # Assert
    assert freq == 1
    assert max_dur == 2 # Should cover the entire array

def test_event_characteristics_filters_short_events():
    """
    Test ensuring that events shorter than min_duration are filtered out.
    Data: [-2.0] (Duration 1) -> Should be ignored if min_duration=2
    """
    # Arrange
    spi_ts = [-2.0]  # only 1 month
    threshold = -1.0
    
    # Act
    freq, max_dur, _, _ = event_characteristics(
        spi_ts, threshold=threshold, event_type="drought", min_duration=2
    )
    
    # Assert
    assert np.isnan(freq)
    assert np.isnan(max_dur)

def test_event_characteristics_no_events():
    """
    Test when no data crosses the threshold.
    """
    # Arrange
    spi_ts = [0, 0, 0]
    threshold = -1.0
    
    # Act
    freq, max_dur, ext_peak, mean_sev = event_characteristics(spi_ts, threshold=threshold)
    
    # Assert
    # Logic returns np.nan for metrics if freq is 0 (or technically freq is nan based on implementation logic check)
    # Based on code: if len(events) > 0 freq=len else freq=np.nan
    assert np.isnan(freq) 
    assert np.isnan(max_dur)

def test_event_characteristics_all_nan():
    """
    Test input with all NaN values.
    """
    # Arrange
    spi_ts = [np.nan, np.nan]
    
    # Act
    result = event_characteristics(spi_ts)
    
    # Assert
    # Should return tuple of (nan, nan, nan, nan)
    assert all(np.isnan(x) for x in result)

# --- Tests for calc_event_maps (2 Case) ---

def test_calc_event_maps_calculation_accuracy():
    """
    Test calc_event_maps with CONTROLLED data to verify calculation accuracy per pixel.
    
    Setup:
    - Grid 2x2 (Lat, Lon)
    - Time: 5 steps
    - Threshold: -1.0 (Drought)
    
    Pixel Scenario:
    1. Lat 0, Lon 0 (Drought Event):
       Values: [-1.5, -2.5, 0, 0, 0]
       - Event: Indices 0-1
       - Duration: 2
       - Peak: -2.5 (Min value)
       - Severity: |-1.5| + |-2.5| = 4.0
       - Frequency: 1
       
    2. Lat 0, Lon 1 (No Event):
       Values: [0, 0, 0, 0, 0]
       - Result should be NaN for all metrics.
    """
    # Arrange
    times = pd.date_range("2000-01-01", periods=5, freq="D")
    
    # Create empty data (2 lats, 2 lons, 5 times)
    data = np.zeros((5, 2, 2))
    
    # -- Inject Scenario 1 at (0,0) --
    data[0, 0, 0] = -1.5
    data[1, 0, 0] = -2.5
    # data[2:, 0, 0] is already 0.0
    
    # -- Inject Scenario 2 at (0,1) --
    # data[:, 0, 1] is already 0.0 (No event < -1.0)
    
    da = xr.DataArray(
        data,
        coords={"time": times, "lat": [10, 20], "lon": [100, 110]},
        dims=("time", "lat", "lon")
    )
    
    # Act
    # Calling the function
    output = calc_event_maps(da, threshold=-1.0, event_type="drought")
    
    # Assert
    # Note: calc_event_maps expands dims with 'time' (start, end). 
    # We select .isel(time=0) to check the value maps.
    
    # --- Check Pixel (0,0): The Drought Event ---
    freq_00 = output["Frequency"].isel(time=0, lat=0, lon=0).values
    dur_00 = output["Duration"].isel(time=0, lat=0, lon=0).values
    peak_00 = output["Peak"].isel(time=0, lat=0, lon=0).values
    sev_00 = output["Severity"].isel(time=0, lat=0, lon=0).values
    
    assert freq_00 == 1.0
    assert dur_00 == 2.0
    np.testing.assert_allclose(peak_00, -2.5, rtol=1e-5)
    np.testing.assert_allclose(sev_00, 4.0, rtol=1e-5)
    
    # --- Check Pixel (0,1): No Event ---
    freq_01 = output["Frequency"].isel(time=0, lat=0, lon=1).values
    
    # Expecting NaN because no event occurred
    assert np.isnan(freq_01)

def test_calc_event_maps_all_nan_input():
    """
    Test ensuring the function handles an All-NaN map (e.g., ocean masking)
    gracefully without crashing, returning NaN maps.
    """
    # Arrange
    times = pd.date_range("2000-01-01", periods=5, freq="D")
    # Create data full of NaNs
    data = np.full((5, 2, 2), np.nan)
    
    da = xr.DataArray(
        data,
        coords={"time": times, "lat": [10, 20], "lon": [100, 110]},
        dims=("time", "lat", "lon")
    )
    
    # Act
    output = calc_event_maps(da, threshold=-1.0)
    
    # Assert
    # Every metric should be entirely NaN
    assert output["Frequency"].isnull().all()
    assert output["Severity"].isnull().all()

# --- Tests for calculate_all_indices (Main Orchestrator) ---

@patch("processing.indices.PR_INDICES", new_callable=dict)
@patch("processing.indices.BASELINE_REQUIRED_INDICES", {"R95p"}) # Force R95p to require baseline
def test_calculate_all_indices_general_routing(mock_pr_indices, sample_ds, mock_baseline):
    """
    Test routing for general indices:
    1. Standard index (PRCPTOT) -> Called without baseline
    2. Baseline index (R95p)    -> Called WITH baseline
    """
    # Arrange
    # Mock PRCPTOT (Standard)
    mock_prcptot = MagicMock(return_value=xr.DataArray([1], name="prcptot"))
    mock_pr_indices["PRCPTOT"] = mock_prcptot
    
    # Mock R95p (Requires Baseline)
    mock_r95p = MagicMock(return_value=xr.DataArray([2], name="r95p"))
    mock_pr_indices["R95p"] = mock_r95p
    
    selected = ["PRCPTOT", "R95p"]
    
    # Act
    result_ds = calculate_all_indices(sample_ds, freq="YS", selected_indices=selected, baseline=mock_baseline)

    # Assert
    assert "PRCPTOT" in result_ds
    assert "R95p" in result_ds
    
    # PRCPTOT should NOT receive baseline
    mock_prcptot.assert_called_once_with(sample_ds, freq="YS")
    
    # R95p SHOULD receive baseline
    mock_r95p.assert_called_once_with(sample_ds, freq="YS", baseline=mock_baseline)


@patch("processing.indices.spi")
@patch("processing.indices.calc_event_maps")
def test_calculate_all_indices_spi_full_group(mock_calc_maps, mock_spi, sample_ds):
    """
    Test selecting a base SPI name (e.g., "SPI3").
    Expectation:
    - spi() called ONCE.
    - Raw SPI3 saved in result.
    - All Event metrics (Drought/Flood) saved in result.
    """
    # Arrange
    # Use REAL DataArrays instead of MagicMock to play nicely with xr.Dataset and assertions
    mock_spi_data = xr.DataArray([1.0], coords={"time": sample_ds.time[:1]}, dims="time", name="SPI3")
    mock_spi.return_value = mock_spi_data
    
    # Mock Event Maps return (Dict of real DataArrays)
    mock_maps = {
        "Frequency": xr.DataArray([10], name="freq"),
        "Duration": xr.DataArray([20], name="dur"),
        "Peak": xr.DataArray([30], name="peak"),
        "Severity": xr.DataArray([40], name="sev"),
    }
    mock_calc_maps.return_value = mock_maps
    
    selected = ["SPI3"] # Select the group
    
    # Act
    result_ds = calculate_all_indices(sample_ds, freq="MS", selected_indices=selected)

    # Assert
    # 1. SPI Calculation
    mock_spi.assert_called_once_with(ds=sample_ds, window=3, freq="MS")
    assert "SPI3" in result_ds
    
    # Use xarray testing functions for robust comparison
    xr.testing.assert_identical(result_ds["SPI3"], mock_spi_data)
    
    # 2. Event Maps Calculation
    # Should be called twice: once for Drought (-1.0), once for Flood (1.0)
    assert mock_calc_maps.call_count == 2
    
    # 3. Check Keys in Result (Should have ALL metrics)
    # 2 events * 4 metrics = 8 keys + 1 raw SPI3 = 9 keys total
    expected_keys = [
        "SPI3", 
        "SPI3_Drought_Frequency", "SPI3_Drought_Severity",
        "SPI3_Flood_Frequency", "SPI3_Flood_Severity"
    ]
    for key in expected_keys:
        assert key in result_ds
        
    expected_freq = mock_maps["Frequency"].rename("SPI3_Drought_Frequency")
    xr.testing.assert_identical(result_ds["SPI3_Drought_Frequency"], expected_freq)

@patch("processing.indices.PR_INDICES", new_callable=dict)
def test_calculate_all_indices_error_handling(mock_pr_indices, sample_ds):
    """
    Test that ValueError is raised with a descriptive message 
    when an underlying index function fails.
    """
    # Arrange
    # Function raises generic Exception
    mock_pr_indices["PRCPTOT"] = MagicMock(side_effect=Exception("Calculation Error"))
    
    selected = ["PRCPTOT"]
    
    # Act & Assert
    with pytest.raises(ValueError, match="Failed calculating PRCPTOT"):
        calculate_all_indices(sample_ds, selected_indices=selected)