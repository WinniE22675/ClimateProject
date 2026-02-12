# tests/processing/test_merge_datasets.py

import pytest
import xarray as xr
import numpy as np
from unittest.mock import patch, MagicMock

from processing.merge_datasets import (
    save_dataset_to_netcdf,
    merge_attribute_mode,
    merge_time_mode,
    merge_mixed_mode
)

# --------------------------------------------------
# Test save_dataset_to_netcdf
# --------------------------------------------------

@patch("processing.merge_datasets.tempfile._get_candidate_names")
def test_save_dataset_to_netcdf(mock_names, tmp_path, monkeypatch):
    # Arrange
    mock_names.return_value = iter(["abc123"])
    monkeypatch.setattr("processing.merge_datasets.PREVIEW_MERGED_DIR", tmp_path)

    ds = xr.Dataset({"a": ("x", [1, 2, 3])})

    # Act
    path = save_dataset_to_netcdf(ds, prefix="test")

    # Assert
    assert path.endswith("test_abc123.nc")
    assert str(tmp_path) in path


# --------------------------------------------------
# Test merge_attribute_mode
# --------------------------------------------------

@patch("processing.merge_datasets.save_dataset_to_netcdf")
@patch("processing.merge_datasets.xr.open_dataset")
def test_merge_attribute_mode_success(mock_open, mock_save):
    # Arrange
    ds1 = xr.Dataset({"var1": ("x", [1])})
    ds2 = xr.Dataset({"var2": ("x", [2])})

    mock_open.side_effect = [ds1, ds2]
    mock_save.return_value = "merged.nc"

    paths = ["a.nc", "b.nc"]

    # Act
    ok, result, errors = merge_attribute_mode(paths)

    # Assert
    assert ok is True
    assert result["path"] == "merged.nc"
    assert errors == []


@patch("processing.merge_datasets.xr.open_dataset", side_effect=Exception("boom"))
def test_merge_attribute_mode_fail(mock_open):
    ok, result, errors = merge_attribute_mode(["bad.nc"])

    assert ok is False
    assert result is None
    assert errors


# --------------------------------------------------
# Test merge_time_mode
# --------------------------------------------------

@patch("processing.merge_datasets.save_dataset_to_netcdf")
@patch("processing.merge_datasets.xr.open_mfdataset")
def test_merge_time_mode_success(mock_open_mf, mock_save):
    # Arrange
    ds = xr.Dataset(
        {"var": ("time", [1, 2])},
        coords={"time": np.array(["2000-01-01", "2000-01-02"], dtype="datetime64")}
    )
    mock_open_mf.return_value = ds
    mock_save.return_value = "time.nc"

    # Act
    ok, result, errors = merge_time_mode(["a.nc", "b.nc"])

    # Assert
    assert ok is True
    assert result["path"] == "time.nc"
    assert errors == []


@patch("processing.merge_datasets.xr.open_mfdataset", side_effect=Exception("fail"))
def test_merge_time_mode_fail(mock_open_mf):
    ok, result, errors = merge_time_mode(["x.nc"])

    assert ok is False
    assert result is None
    assert errors


# --------------------------------------------------
# Test merge_mixed_mode
# --------------------------------------------------

@patch("processing.merge_datasets.merge_time_mode")
@patch("processing.merge_datasets.save_dataset_to_netcdf")
def test_merge_mixed_mode_success(mock_save, mock_merge_time):
    # Arrange
    ds1 = xr.Dataset({"a": ("time", [1])})
    ds2 = xr.Dataset({"b": ("time", [2])})

    mock_merge_time.side_effect = [
        (True, {"dataset": ds1}, []),
        (True, {"dataset": ds2}, []),
    ]

    mock_save.return_value = "mixed.nc"

    groups = {"a": [0], "b": [1]}
    temp_paths = ["a.nc", "b.nc"]

    # Act
    ok, result, errors = merge_mixed_mode(
        paths=[],
        groups=groups,
        metas=[],
        temp_paths=temp_paths
    )

    # Assert
    assert ok is True
    assert result["path"] == "mixed.nc"
    assert errors == []


@patch("processing.merge_datasets.merge_time_mode", return_value=(False, None, ["err"]))
def test_merge_mixed_mode_fail(mock_merge_time):
    ok, result, errors = merge_mixed_mode(
        paths=[],
        groups={"a": [0]},
        metas=[],
        temp_paths=["a.nc"]
    )

    assert ok is False
    assert result is None
    assert errors
