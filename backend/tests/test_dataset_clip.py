import pytest
import xarray as xr
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, patch
from services.dataset_clip import (
    standardize_coords,
    get_smart_slice,
    core_process_file
)

# ==========================================
# Create data
# ==========================================
@pytest.fixture
def messy_coord_ds():
    """Dataset with non-standard coordinate names (e.g., nav_lat, nav_lon)"""
    return xr.Dataset(
        {"temp": (("y", "x"), [[1, 2], [3, 4]])},
        coords={
            "lat": (("y"), [10, 11]),
            "lon": (("x"), [100, 101]),
            "time": [1]
        }
    )

@pytest.fixture
def mock_scope():
    """Mock object representing the user selection scope"""
    class Scope:
        startYear = 2000
        endYear = 2010
        minLat = 0
        maxLat = 20
        minLon = 90
        maxLon = 110
    return Scope()

# ==========================================
# 2. Test standardize_coords
# ==========================================
def test_standardize_coords_renaming(messy_coord_ds):
    """Test if the function correctly identifies and renames aliases."""
    ds_clean = standardize_coords(messy_coord_ds)
    
    assert "latitude" in ds_clean.coords
    assert "longitude" in ds_clean.coords
    assert "nav_lat" not in ds_clean.coords # Should be gone (renamed)

def test_standardize_coords_already_standard():
    """Test if dataset is already standard, it remains unchanged."""
    ds = xr.Dataset(coords={"latitude": [1], "longitude": [1]})
    ds_clean = standardize_coords(ds)
    assert "latitude" in ds_clean.coords
    assert "longitude" in ds_clean.coords

# ==========================================
# 3. Test get_smart_slice (CRITICAL LOGIC)
# ==========================================
def test_get_smart_slice_ascending():
    """
    Test slicing logic when coordinates are increasing (0, 10, 20...).
    Expect: slice(min, max)
    """
    # Create DataArray: [0, 10, 20, 30]
    da = xr.DataArray([0, 10, 20, 30], coords={"lat": [0, 10, 20, 30]})
    ds = xr.Dataset({"lat": da})
    
    # Request slice 5 to 25
    sl = get_smart_slice(ds, "lat", min_val=5, max_val=25)
    
    # Logic: 0 < 30 (Ascending) -> slice(5, 25)
    assert sl == slice(5, 25)
    assert sl.start == 5
    assert sl.stop == 25

def test_get_smart_slice_descending():
    """
    Test slicing logic when coordinates are decreasing (30, 20, 10...).
    Expect: slice(max, min) -> SWAPPED!
    """
    # Create DataArray: [30, 20, 10, 0]
    da = xr.DataArray([30, 20, 10, 0], coords={"lat": [30, 20, 10, 0]})
    ds = xr.Dataset({"lat": da})
    
    # Request slice 5 to 25
    sl = get_smart_slice(ds, "lat", min_val=5, max_val=25)
    
    # Logic: 30 > 0 (Descending) -> slice(25, 5)
    assert sl == slice(25, 5) 
    assert sl.start == 25
    assert sl.stop == 5

# ==========================================
# 4. Test core_process_file (Mocking IO)
# ==========================================
@patch("services.dataset_clip.xr.open_dataset")
def test_core_process_file_skip_year(mock_open, mock_scope):
    """
    Test if function skips file when file years are outside scope.
    Scope: 2000-2010
    File: 1990-1995
    """
    # 1. Setup Mock DS with year 1990
    ds_mock = MagicMock()
    # Mocking Context Manager for `with xr.open_dataset(...) as ds:`
    mock_open.return_value.__enter__.return_value = ds_mock
    
    ds_mock.dims = {'time': 10}
    # Mock .dt.year.min() and .max()
    ds_mock.time.dt.year.min.return_value = 1990
    ds_mock.time.dt.year.max.return_value = 1995

    # 2. Run function
    result = core_process_file("dummy_raw.nc", "dummy_save.nc", mock_scope)

    # 3. Assert
    assert result is False # Should return False (Skipped)
    # Removing ds_mock.close.assert_called() because we now use 'with' block 
    # which automatically calls __exit__ (close equivalent)

@patch("services.dataset_clip.xr.open_dataset")
def test_core_process_file_success(mock_open, mock_scope):
    """
    Test the happy path where file is processed and saved.
    """
    # 1. Setup Mock DS that fits the scope (2005)
    ds_mock = MagicMock()
    # Mocking Context Manager
    mock_open.return_value.__enter__.return_value = ds_mock
    
    ds_mock.dims = {'time': 10, 'latitude': 10, 'longitude': 10}
    ds_mock.coords = {} # simulate standard coords
    
    # Time matches scope (2000-2010)
    ds_mock.time.dt.year.min.return_value = 2005
    ds_mock.time.dt.year.max.return_value = 2005
    
    # Slicing returns valid size
    # We mock the return of .sel() to be another mock that has size > 0
    ds_subset = MagicMock()
    ds_subset.time.size = 5
    ds_subset.latitude.size = 5
    ds_subset.longitude.size = 5
    
    # Needs to be iterable dictionaries for unit conversion & encoding cleanup logic
    mock_var = MagicMock()
    mock_var.attrs = {}
    ds_subset.variables = {'temp': mock_var}
    ds_subset.data_vars = {'temp': mock_var}
    
    # Mock methods returning self
    ds_mock.sel.return_value = ds_subset
    ds_subset.drop_vars.return_value = ds_subset
    ds_subset.copy.return_value = ds_subset 
    
    # 2. Run
    result = core_process_file("dummy.nc", "dummy_out.nc", mock_scope)

    # 3. Assert
    assert result is True, "Result was False, possibly due to an unhandled Exception in core_process_file logic."
    # Assert saving logic (adding compute=True to match implementation)
    ds_subset.to_netcdf.assert_called_with("dummy_out.nc", format='NETCDF4', compute=True)

def test_core_process_no_time_dim(messy_coord_ds, mock_scope):
    """
    Test that core_process_file returns False
    when dataset has no time dimension.
    """
    ds = messy_coord_ds.drop_vars("temp").assign_coords(latitude=[0, 1], longitude=[0, 1])

    with patch("xarray.open_dataset", return_value=ds):
        result = core_process_file("dummy.nc", "out.nc", mock_scope)

    assert result is False

def test_core_process_empty_slice(messy_coord_ds, mock_scope):
    """
    Test that function returns False
    when spatial slicing results in empty dataset.
    """
    mock_scope.minLat = 50
    mock_scope.maxLat = 60  # outside data range

    with patch("xarray.open_dataset", return_value=messy_coord_ds):
        result = core_process_file("dummy.nc", "out.nc", mock_scope)

    assert result is False

@patch("xarray.open_dataset", side_effect=Exception("boom"))
def test_core_process_exception(mock_open, mock_scope):
    """
    Test that unexpected exception
    results in False, not crash.
    """
    result = core_process_file("dummy.nc", "out.nc", mock_scope)

    assert result is False