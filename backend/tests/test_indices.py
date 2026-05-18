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
    event_characteristics_annual_continuous, 
    calc_event_maps, 
    calculate_all_indices, 
    BASELINE_REQUIRED_INDICES,
    convert_temperature_unit
)
from unittest.mock import patch, MagicMock

# --- Fixtures for creating dummy data ---

@pytest.fixture(autouse=True)
def setup_and_teardown():
    """
    Fixture for setting up and tearing down the uploads directory.
    Runs before and after each test.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    upload_dir = os.path.join(base_dir, "..", "uploads", "merged")
    
    os.makedirs(upload_dir, exist_ok=True)
    yield  # Test runs here
    
    if os.path.exists(upload_dir):
        try:
            shutil.rmtree(upload_dir)
            os.makedirs(upload_dir)
        except Exception as e:
            print(f"Error cleaning up {upload_dir}: {e}")

@pytest.fixture
def sample_da():
    """
    Creates a sample DataArray with daily data from 2000 to 2005.
    """
    times = pd.date_range("2000-01-01", "2005-12-31", freq="D")
    data = np.random.rand(len(times)) * 10
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
    pr_data = sample_da.copy()
    pr_data.values[:10] = 0.5   # Dry days
    pr_data.values[10:20] = 5.0 # Wet days
    
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
    pr_data = np.zeros(len(times))
    pr_data[::2] = 100.0  # Alternate days are wet
    
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
    """Mock object acting as the baseline configuration."""
    return SimpleNamespace(start_year=2001, end_year=2002)


# --- Tests for Unit Conversion ---

def test_convert_temperature_unit_kelvin():
    """Test converting Kelvin to Celsius."""
    da = xr.DataArray([300.15, 273.15], attrs={"units": "K", "long_name": "Temperature"})
    res = convert_temperature_unit(da)
    
    np.testing.assert_allclose(res.values, [27.0, 0.0])
    assert res.attrs["units"] == "C"
    assert res.attrs["long_name"] == "Temperature" # Preserves other attrs

def test_convert_temperature_unit_celsius():
    """Test that Celsius (and other units) remain unchanged."""
    da = xr.DataArray([27.0], attrs={"units": "C"})
    res = convert_temperature_unit(da)
    
    np.testing.assert_allclose(res.values, [27.0])
    assert res.attrs["units"] == "C"

# --- Tests for slice_baseline ---

def test_slice_baseline_valid_range(sample_da):
    """Test ensuring slice_baseline returns correct subset of data."""
    result = slice_baseline(sample_da, 2001, 2002)
    
    assert result.time.dt.year.min() == 2001
    assert result.time.dt.year.max() == 2002
    assert result.sizes['time'] < sample_da.sizes['time']

def test_slice_baseline_returns_full_data_when_args_none(sample_da):
    """Test returning full data if start or end year is None."""
    result = slice_baseline(sample_da, None, None)
    xr.testing.assert_identical(result, sample_da)

def test_slice_baseline_raises_error_outside_range(sample_da):
    """Test ValueError is raised when baseline is outside data range."""
    with pytest.raises(ValueError, match="is outside data range"):
        slice_baseline(sample_da, 1990, 1995)

def test_slice_baseline_raises_error_when_start_year_greater_than_end_year(sample_da):
    """Test ValueError is raised for empty data (start > end)."""
    with pytest.raises(ValueError, match="Baseline slicing produced empty data"):
        slice_baseline(sample_da, 2003, 2001)

# --- Tests for Percentiles ---

def test_compute_pr_percentiles_calculation_logic(constant_ds, mock_baseline):
    """Verifies that dry days (< 1.0) are ignored in percentile calculation."""
    res_50 = compute_pr_percentiles(constant_ds, percentile=50, baseline=mock_baseline)
    res_95 = compute_pr_percentiles(constant_ds, percentile=95, baseline=mock_baseline)
    
    np.testing.assert_allclose(res_50.values, 100.0, rtol=1e-5)
    np.testing.assert_allclose(res_95.values, 100.0, rtol=1e-5)

def test_compute_temp_percentiles_calculation_correctness(constant_ds, mock_baseline):
    """Verifies that temp percentiles are calculated correctly."""
    res_10 = compute_temp_percentiles(constant_ds, var_name="tmin", percentile=10, baseline=mock_baseline)
    res_90 = compute_temp_percentiles(constant_ds, var_name="tmax", percentile=90, baseline=mock_baseline)
    
    np.testing.assert_allclose(res_10.values, 10.0, rtol=1e-5)
    np.testing.assert_allclose(res_90.values, 30.0, rtol=1e-5)

# --- Tests for event_characteristics_annual_continuous ---

def test_event_characteristics_drought_logic():
    """Test extracting continuous drought events and grouping by year."""
    # 24 months (2 years)
    spi_ts = np.zeros(24)
    spi_ts[2:4] = [-1.2, -2.0]  # Event 1 (Year 0): Duration 2, Peak -2.0, Sev 3.2
    spi_ts[6] = -1.5            # Too short, filtered out
    
    res = event_characteristics_annual_continuous(spi_ts, threshold=-1.0, event_type="drought", min_duration=2)
    
    # Assert Year 0 (Index 0)
    assert res[0, 0] == 1.0  # freq
    assert res[0, 1] == 2.0  # dur
    np.testing.assert_allclose(res[0, 2], -2.0)  # peak
    np.testing.assert_allclose(res[0, 3], 3.2)   # sev
    
    # Assert Year 1 (Index 1) -> No events
    assert res[1, 0] == 0.0
    assert np.isnan(res[1, 1])

def test_event_characteristics_flood_logic():
    """Test logic for detecting flood events (values > abs(threshold))."""
    spi_ts = np.zeros(24)
    spi_ts[1:3] = [1.5, 2.5]  # Event (Year 0): Duration 2, Peak 2.5, Sev 4.0
    
    res = event_characteristics_annual_continuous(spi_ts, threshold=1.0, event_type="flood", min_duration=2)
    
    assert res[0, 0] == 1.0
    assert res[0, 1] == 2.0
    np.testing.assert_allclose(res[0, 2], 2.5)
    np.testing.assert_allclose(res[0, 3], 4.0)

def test_event_characteristics_all_nan():
    """Test input with all NaN values (ocean pixels)."""
    spi_ts = np.full(24, np.nan)
    res = event_characteristics_annual_continuous(spi_ts)
    
    assert np.all(np.isnan(res))

# --- Tests for calc_event_maps ---

def test_calc_event_maps_calculation_accuracy():
    """Test calc_event_maps applying function over time for multiple pixels."""
    times = pd.date_range("2000-01-01", periods=24, freq="MS") # 2 years
    data = np.zeros((24, 2, 2))
    
    # Scenario: Drought event at Lat 0, Lon 0
    data[0, 0, 0] = -1.5
    data[1, 0, 0] = -2.5
    
    # แก้ไขชื่อ coords และ dims ให้ตรงกับ Source Code (latitude, longitude)
    da = xr.DataArray(
        data, 
        coords={"time": times, "latitude": [10, 20], "longitude": [100, 110]}, 
        dims=("time", "latitude", "longitude")
    )
    
    output = calc_event_maps(da, threshold=-1.0, event_type="drought")
    
    # Check Pixel (0,0) at Year 0
    assert output["Frequency"].isel(time=0, latitude=0, longitude=0).values == 1.0
    assert output["Duration"].isel(time=0, latitude=0, longitude=0).values == 2.0
    assert output["Peak"].isel(time=0, latitude=0, longitude=0).values == -2.5
    assert output["Severity"].isel(time=0, latitude=0, longitude=0).values == 4.0
    
    # Check Pixel (0,1) at Year 0 -> No event
    assert output["Frequency"].isel(time=0, latitude=0, longitude=1).values == 0.0
    assert np.isnan(output["Duration"].isel(time=0, latitude=0, longitude=1).values)

# --- Tests for calculate_all_indices (Main Orchestrator) ---

@patch("processing.indices.PR_INDICES", new_callable=dict)
@patch("processing.indices.BASELINE_REQUIRED_INDICES", {"R95p"})
def test_calculate_all_indices_general_routing(mock_pr_indices, sample_ds, mock_baseline):
    """Test routing for standard vs baseline-required indices."""
    mock_prcptot = MagicMock(return_value=xr.DataArray([1], name="prcptot"))
    mock_pr_indices["PRCPTOT"] = mock_prcptot
    
    mock_r95p = MagicMock(return_value=xr.DataArray([2], name="r95p"))
    mock_pr_indices["R95p"] = mock_r95p
    
    selected = ["PRCPTOT", "R95p"]
    result_ds = calculate_all_indices(sample_ds, freq="YS", selected_indices=selected, baseline=mock_baseline)

    assert "PRCPTOT" in result_ds
    assert "R95p" in result_ds
    
    mock_prcptot.assert_called_once_with(sample_ds, freq="YS")
    mock_r95p.assert_called_once_with(sample_ds, freq="YS", baseline=mock_baseline)


@patch("processing.indices.spi")
@patch("processing.indices.calc_event_maps")
def test_calculate_all_indices_spi_full_group(mock_calc_maps, mock_spi, sample_ds):
    """Test that SPI selects trigger both raw SPI and Maps generation."""
    mock_spi_data = xr.DataArray([1.0], coords={"time": sample_ds.time[:1]}, dims="time", name="SPI3")
    mock_spi.return_value = mock_spi_data
    
    mock_maps = {
        "Frequency": xr.DataArray([10], name="freq"),
        "Duration": xr.DataArray([20], name="dur"),
        "Peak": xr.DataArray([30], name="peak"),
        "Severity": xr.DataArray([40], name="sev"),
    }
    mock_calc_maps.return_value = mock_maps
    
    # แก้ไข freq เป็น "YS" เพื่อให้เข้าเงื่อนไข if freq == "YS": ใน calculate_all_indices
    result_ds = calculate_all_indices(sample_ds, freq="YS", selected_indices=["SPI3"])

    mock_spi.assert_called_once_with(ds=sample_ds, window=3, freq="MS")
    assert mock_calc_maps.call_count == 2 # Drought & Flood
    
    expected_keys = [
        "SPI3", 
        "SPI3_Drought_Frequency", "SPI3_Drought_Severity",
        "SPI3_Flood_Frequency", "SPI3_Flood_Severity"
    ]
    for key in expected_keys:
        assert key in result_ds

@patch("processing.indices.PR_INDICES", new_callable=dict)
def test_calculate_all_indices_error_handling(mock_pr_indices, sample_ds):
    """Test that ValueError is raised on failed calculation."""
    mock_pr_indices["PRCPTOT"] = MagicMock(side_effect=Exception("Calculation Error"))
    
    with pytest.raises(ValueError, match="Failed calculating PRCPTOT"):
        calculate_all_indices(sample_ds, selected_indices=["PRCPTOT"])