import pytest
import numpy as np
import xarray as xr
import pandas as pd
from unittest.mock import patch, MagicMock
from typing import Dict, Any

from processing.upload_validation import (
    map_and_rename_coord,
    get_spatial_resolution,
    inspect_file,
    detect_mode,
    validate_compatibility
)

# Test: map_and_rename_coord

def test_map_and_rename_coord_success():
    """Should rename 'lat' to 'latitude'."""
    ds = xr.Dataset(coords={"lat": [10, 20]})

    ds_new, coord_name = map_and_rename_coord(
        ds,
        canonical_name="latitude",
        aliases=["lat", "latitude"]
    )

    assert coord_name == "latitude"
    assert "latitude" in ds_new.coords

def test_map_and_rename_coord_not_found():
    """Should raise KeyError if no valid coordinate found."""
    ds = xr.Dataset(coords={"x": [1, 2]})

    with pytest.raises(KeyError):
        map_and_rename_coord(ds, "latitude", ["lat", "latitude"])

# Test: get_spatial_resolution

def test_get_spatial_resolution_from_coords():
    """Should calculate resolution from coordinate values difference."""
    ds = xr.Dataset(
        coords={
            "lat": [0.0, 0.25, 0.5],
            "lon": [100.0, 100.25, 100.5],
            "time": [0]
        }
    )

    lat_res, lon_res = get_spatial_resolution(ds)

    assert lat_res == pytest.approx(0.25)
    assert lon_res == pytest.approx(0.25)

def test_get_spatial_resolution_from_attrs():
    """Should extract resolution from global attributes."""
    ds = xr.Dataset()
    ds.attrs["geospatial_lat_resolution"] = "0.25 degrees"
    ds.attrs["geospatial_lon_resolution"] = "0.25 degrees"
    
    lat_res, lon_res = get_spatial_resolution(ds)
    
    assert lat_res == 0.25
    assert lon_res == 0.25

# Test: inspect_file (Using Mocks)

@patch("processing.upload_validation.os.path.getsize")
@patch("processing.upload_validation.xr.open_dataset")
def test_inspect_file_success(mock_open_dataset, mock_getsize):
    # Arrange
    mock_getsize.return_value = 5 * 1024 * 1024  # 5 MB

    times = np.array(
        np.arange(
            np.datetime64("2020-01-01"),
            np.datetime64("2020-01-11")
        ),
        dtype="datetime64[D]"
    )

    ds = xr.Dataset(
        data_vars={
            "precip": (("time", "latitude", "longitude"), np.random.rand(10, 2, 2))
        },
        coords={
            "time": times,
            "latitude": [10.0, 11.0],
            "longitude": [100.0, 101.0],
        },
    )

    ds["precip"].attrs["units"] = "mm/day"
    ds.time.attrs["calendar"] = "gregorian"

    # First open_dataset (decode_times=True)
    # Second open_dataset (decode_times=False)
    mock_open_dataset.side_effect = [ds, ds]

    # Act
    result = inspect_file("dummy.nc")

    # Assert
    assert result["file_size"] == "5.00 MB"
    assert result["variables"] == ["pr"]  # precip -> pr
    assert result["time_start"].startswith("2020-01-01")
    assert result["time_end"].startswith("2020-01-10")
    assert result["calendar"] == "gregorian"
    assert result["lat_res"] == 1.0
    assert result["lon_res"] == 1.0
    assert result["spatial_resolution"] == "1.000° x 1.000°"
    
@patch("processing.upload_validation.xr.open_dataset")
def test_inspect_file_open_error(mock_open_dataset):
    mock_open_dataset.side_effect = Exception("Cannot open file")

    result = inspect_file("bad.nc")

    assert "error" in result


# Test: detect_mode

def test_detect_mode_time():
    """All files have same variable ('pr') -> Time Mode."""
    metas = [
        {"variables": ["pr"], "time_start": "2000", "time_end": "2001"},
        {"variables": ["pr"], "time_start": "2001", "time_end": "2002"},
    ]

    mode, info, diag = detect_mode(metas)

    assert mode == "time"
    assert info["variable"] == "pr"

def test_detect_mode_attribute():
    """Files have different variables ('pr', 'tas') but same time -> Attribute Mode."""
    metas = [
        {"variables": ["pr"], "time_start": "2000", "time_end": "2001"},
        {"variables": ["tas"], "time_start": "2000", "time_end": "2001"},
    ]

    mode, info, diag = detect_mode(metas)

    assert mode == "attribute"
    assert "pr" in info["variables"]
    assert "tas" in info["variables"]

def test_detect_mode_mixed():
    """Files have different variables AND different times -> Mixed Mode."""
    metas = [
        {"variables": ["pr"], "time_start": "2020", "time_end": "2021"},
        {"variables": ["tas"], "time_start": "2022", "time_end": "2023"}
    ]
    
    mode, info, diag = detect_mode(metas)
    assert mode == "mixed"
    assert "Mixed mode detected" in diag[0]

# Test: validate_compatibility

def test_validate_compatibility_success():
    metas = [
        {"calendar": "gregorian", "lat_res": 0.25, "lon_res": 0.25},
        {"calendar": "gregorian", "lat_res": 0.2500001, "lon_res": 0.2499999},
    ]

    ok, errors = validate_compatibility(metas)

    assert ok is True
    assert errors == []

def test_validate_compatibility_diff_resolution():
    """Different resolutions should fail."""
    metas = [
        {"calendar": "standard", "lat_res": 0.5, "lon_res": 0.5},
        {"calendar": "standard", "lat_res": 0.25, "lon_res": 0.25} # Resolution mismatch
    ]
    is_valid, errors = validate_compatibility(metas)
    assert is_valid is False
    assert len(errors) > 0

def test_validate_compatibility_calendar_mismatch():
    metas = [
        {"calendar": "gregorian"},
        {"calendar": "360_day"},
    ]

    ok, errors = validate_compatibility(metas)

    assert ok is False
    assert len(errors) > 0
