import pytest
import numpy as np
import xarray as xr
from unittest.mock import patch, MagicMock

from processing.preprocessing import (
    normalize_var_name,
    standardize_coords,
    ensure_pr_unit,
    ensure_temperature_unit,
    load_dataset
)

# --- 1. Test: normalize_var_name ---
# เทสต์ฟังก์ชันแปลงชื่อตัวแปร แบบง่ายๆ (Input String -> Output String)

def test_normalize_var_name_match():
    """ทดสอบว่าชื่อที่เป็น Alias ถูกแปลงเป็นชื่อมาตรฐานถูกต้อง"""
    assert normalize_var_name("precip") == "pr"
    assert normalize_var_name("T2M") == "tas"  # try uppercase
    assert normalize_var_name("tasmax") == "tmax"

def test_normalize_var_name_no_match():
    """ทดสอบว่าถ้าชื่อไม่มีในลิสต์ ต้องคืนค่าเดิมกลับมา"""
    assert normalize_var_name("wind_speed") == "wind_speed"
    assert normalize_var_name("unknown_var") == "unknown_var"

# --- 2. Test: standardize_coords ---
# เทสต์การเปลี่ยนชื่อ Coordinate ใน xarray

def test_standardize_coords():
    """ทดสอบว่าเปลี่ยนชื่อ lat/lon เป็น latitude/longitude ได้ถูกต้อง"""
    # Arrange: สร้าง Dataset จำลองที่มีชื่อแปลกๆ
    ds = xr.Dataset(coords={"lat": [1, 2], "lon": [10, 20]})
    
    ds_new = standardize_coords(ds)
    
    # Assert: really change name
    assert "latitude" in ds_new.coords
    assert "longitude" in ds_new.coords
    assert "lat" not in ds_new.coords 
    assert "lon" not in ds_new.coords

def test_standardize_coords_already_standard():
    """ทดสอบว่าถ้าชื่อถูกอยู่แล้ว ต้องไม่ทำอะไร"""
    ds = xr.Dataset(coords={"latitude": [1, 2], "longitude": [10, 20]})
    ds_new = standardize_coords(ds)

    assert ds_new is not None
    assert "latitude" in ds_new.coords
    assert "longitude" in ds_new.coords


# --- 3. Test: ensure_pr_unit (Precipitation) ---
# เทสต์การแปลงหน่วยน้ำฝน

def test_ensure_pr_unit_mm_per_sec():
    """ทดสอบการแปลงจาก mm/s เป็น mm/day (* 86400)"""
    # Arrange: สร้าง DataArray จำลองที่มีค่า 1 และหน่วย mm/s
    da = xr.DataArray([1.0], attrs={"units": "mm/s"})
    
    # Act
    da_new = ensure_pr_unit(da)
    
    # Assert
    expected_value = 1.0 * 86400
    assert da_new.values[0] == expected_value
    assert da_new.attrs["units"] == "mm/day"

def test_ensure_pr_unit_mm_per_day():
    da = xr.DataArray([1, 2, 3], attrs={"units": "mm/day"})
    out = ensure_pr_unit(da)

    assert out.attrs["units"] == "mm/day"
    assert np.all(out.values == da.values)


def test_ensure_pr_unit_meter_to_mm():
    da = xr.DataArray([1], attrs={"units": "m"})
    out = ensure_pr_unit(da)

    assert out.attrs["units"] == "mm/day"
    assert out.values[0] == 1000

def test_ensure_pr_unit_unknown_raises_error():
    """ทดสอบว่าถ้าหน่วยมั่วมา ต้องแจ้ง Error"""
    da = xr.DataArray([1.0], attrs={"units": "unknown_unit"})
    
    # วิธีเช็คว่าฟังก์ชัน Error จริงไหมใน Pytest
    with pytest.raises(ValueError, match="unknown"):
        ensure_pr_unit(da)

# --- 4. Test: ensure_temperature_unit ---
# เทสต์การแปลงอุณหภูมิ

def test_ensure_temperature_celsius():
    da = xr.DataArray([20], attrs={"units": "celsius"})
    out = ensure_temperature_unit(da)

    assert out.attrs["units"].lower() in ["celsius", "°c", "degc"]
    assert out.values[0] == 20


def test_ensure_temperature_kelvin():
    da = xr.DataArray([273.15], attrs={"units": "kelvin"})
    out = ensure_temperature_unit(da)

    assert out.attrs["units"] == "°C"
    assert np.isclose(out.values[0], 0.0)

def test_ensure_temperature_invalid():
    da = xr.DataArray([20], attrs={"units": "fahrenheit"})
    with pytest.raises(ValueError):
        ensure_temperature_unit(da)

# --- 5. Test: load_dataset (Advance: Mocking) ---
# ฟังก์ชันนี้ยากสุด เพราะมันพยายามเปิดไฟล์จริง
# เราต้องใช้ 'patch' เพื่อหลอกว่าเปิดไฟล์แล้ว โดยไม่ต้องมีไฟล์จริง

@patch("processing.preprocessing.xr.open_dataset")
def test_load_netcdf_success(mock_open_dataset):
    """ทดสอบการโหลดไฟล์ .nc โดยจำลองว่า xarray เปิดไฟล์สำเร็จ"""
    
    # 1. Arrange (เตรียมของปลอม)
    # สร้าง Dataset ปลอมๆ รอไว้
    mock_ds = xr.Dataset(
        data_vars={
            "precip": (("time", "lat", "lon"), [[[0.0001]]]) # ชื่อเดิม precip
        },
        coords={
            "lat": [10], "lon": [100], "time": [1]
        },
        attrs={"units": "mm/s"} # หน่วยต้องแปลง
    )
    # ใส่ attributes ให้ตัวแปรข้างในด้วย (สำคัญสำหรับ logic convert unit)
    mock_ds["precip"].attrs = {"units": "mm/s"}
    
    # สั่งให้ mock_open_dataset ส่งค่าของปลอมกลับไปแทนการเปิดไฟล์จริง
    mock_open_dataset.return_value = mock_ds

    # 2. Act (เรียกใช้งานฟังก์ชันจริง)
    result_ds = load_dataset("dummy_file.nc")

    # 3. Assert (ตรวจสอบ)
    # เช็คว่า xarray.open_dataset ถูกเรียกจริงไหม
    mock_open_dataset.assert_called_once_with("dummy_file.nc", chunks={"time": 100})
    
    # เช็คว่าชื่อตัวแปรถูกเปลี่ยนจาก precip -> pr (Logic normalize_var_name ทำงานไหม)
    assert "pr" in result_ds
    assert "precip" not in result_ds
    
    # เช็คว่าหน่วยถูกแปลง (Logic ensure_pr_unit ทำงานไหม) 
    # 0.0001 * 86400 = 8.64
    assert np.isclose(result_ds["pr"].values[0,0,0], 8.64)