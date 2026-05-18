import pytest
import numpy as np
import xarray as xr
import rioxarray
import geopandas as gpd
from shapely.geometry import box, Polygon
from unittest.mock import patch, MagicMock

# Import functions from the source module
# Adjust the import path according to your project structure
from processing.clipping import (
    resolve_country_names,
    prep_for_rio,
    clip_to_shape,
    get_spatial_weights,
    calc_weighted_mean
)

# ==========================================
# Fixtures (Setup common data for tests)
# ==========================================

@pytest.fixture
def sample_dataarray():
    """
    Arrange: Create a synthetic xarray.DataArray for testing.
    Grid: 10x10 degrees, covering 0-10 lat/lon.
    """
    lon = np.arange(0, 10, 1)
    lat = np.arange(0, 10, 1)
    data = np.ones((len(lat), len(lon))) * 10.0  # Constant value 10
    
    da = xr.DataArray(
        data,
        coords={'latitude': lat, 'longitude': lon},
        dims=('latitude', 'longitude'),
        name='test_data'
    )
    return da

@pytest.fixture
def sample_dataarray_with_time():
    """
    Arrange: Create a synthetic DataArray with Time dimension.
    Shape: (2 time steps, 10 lat, 10 lon)
    Values: 
        - Time 0: All values = 10.0
        - Time 1: All values = 20.0
    """
    lon = np.arange(0, 10, 1)
    lat = np.arange(0, 10, 1)
    time = np.array(['2024-01-01', '2024-01-02'], dtype='datetime64[ns]')
    
    # Create data with shape (2, 10, 10)
    data = np.zeros((2, len(lat), len(lon)))
    data[0, :, :] = 10.0
    data[1, :, :] = 20.0
    
    da = xr.DataArray(
        data,
        coords={'time': time, 'latitude': lat, 'longitude': lon},
        dims=('time', 'latitude', 'longitude'),
        name='test_data_time'
    )
    return da

@pytest.fixture
def sample_geodataframe():
    """
    Arrange: Create a synthetic GeoDataFrame with a known polygon.
    Polygon: A box from (1,1) to (4,4).
    """
    geometry = [box(1, 1, 4, 4)]
    gdf = gpd.GeoDataFrame(
        {'NAME_EN': ['TestCountry'], 'geometry': geometry},
        crs="EPSG:4326"
    )
    return gdf

# ==========================================
# Unit Tests
# ==========================================

def test_resolve_country_names():
    """
    Test logic for resolving country aliases.
    """
    # Arrange & Act
    res_normal = resolve_country_names("Thailand")
    res_alias = resolve_country_names("Timor-Leste")

    # Assert
    assert res_normal == ["Thailand"], "Should return list with single name if no alias exists"
    assert "East Timor" in res_alias, "Should include alias for Timor-Leste"
    assert "Timor Leste" in res_alias, "Should include alias for Timor-Leste"

def test_prep_for_rio(sample_dataarray):
    """
    Test if rioxarray metadata is correctly assigned.
    """
    # Arrange
    da = sample_dataarray

    # Act
    da_processed = prep_for_rio(da)

    # Assert
    assert da_processed.rio.crs == "EPSG:4326", "CRS should be set to EPSG:4326"
    assert da_processed.rio.x_dim == "longitude", "X dim should be longitude"
    assert da_processed.rio.y_dim == "latitude", "Y dim should be latitude"

@patch('geopandas.read_file')
def test_clip_to_shape_success(mock_read_file, sample_dataarray, sample_geodataframe):
    """
    Test clipping functionality with a mocked shapefile.
    """
    # Arrange
    mock_read_file.return_value = sample_geodataframe  # Mock reading shapefile
    da = sample_dataarray
    
    # Act
    clipped = clip_to_shape(da, "dummy_path.shp")

    # Assert
    # Original was 0-9, Clip is box(1,1,4,4). 
    # Bounds should be tighter than original.
    assert clipped.shape != da.shape, "Shape should change after clipping"
    assert not np.isnan(clipped.values).all(), "Result should not be all NaN"
    assert clipped.rio.crs == "EPSG:4326", "Result should maintain CRS"

@patch('geopandas.read_file')
def test_clip_to_shape_invalid_input(mock_read_file, sample_geodataframe, sample_dataarray):
    """
    Test that TypeError is raised when input is not a DataArray.
    """
    # Arrange
    mock_read_file.return_value = sample_geodataframe
    ds = sample_dataarray.to_dataset()  # Convert to Dataset (which code says raises TypeError)

    # Act & Assert
    with pytest.raises(TypeError) as excinfo:
        clip_to_shape(ds, "dummy_path.shp")
    
    assert "Input must be xarray.Dataset" in str(excinfo.value), \
        "Should raise TypeError for Dataset input (based on current implementation)"

def test_get_spatial_weights():
    """
    Test calculation of intersection area weights.
    """
    # Arrange
    # Create a small 2x2 grid (0,0) to (2,2)
    lon = [0.5, 1.5]
    lat = [0.5, 1.5]
    data = np.zeros((2, 2))
    da = xr.DataArray(data, coords={'latitude': lat, 'longitude': lon}, dims=('latitude', 'longitude'))
    
    # Create a polygon that covers ONLY the bottom-left pixel (0,0) to (1,1)
    # The pixel center is at 0.5, 0.5. Grid spacing is 1.0. 
    # Pixel bounds are 0-1.
    country_geom = box(0, 0, 1, 1)

    # Act
    weights = get_spatial_weights(da, country_geom)

    # Assert
    # Bottom-left pixel (index 0,0) should have area = 1.0 * 1.0 = 1.0
    assert np.isclose(weights.values[0, 0], 1.0), "Full intersection should be area 1.0"
    # Top-right pixel (index 1,1) should have area = 0.0
    assert weights.values[1, 1] == 0.0, "No intersection should be 0.0"

def test_calc_weighted_mean_variable_values():
    """
    Test with VARYING values to ensure weights are actually applied.
    Scenario:
    - Pixel 1: Value=10, Weight=1.0 (Full overlap)
    - Pixel 2: Value=50, Weight=0.5 (Half overlap)
    
    Expected: (10*1.0 + 50*0.5) / (1.0 + 0.5) = 35 / 1.5 = 23.333...
    If weights were ignored (simple mean), result would be 30.
    """
    # 1. Arrange DataArray (2 rows, 2 cols) to provide safe grid spacing
    # Grid centers at 0.5 and 1.5 (Pixel width=1.0)
    lon = np.array([0.5, 1.5]) 
    lat = np.array([0.5, 1.5]) # เพิ่มให้มีอย่างน้อย 2 ค่าเพื่อไม่ให้เกิด IndexError ตอนหา d_lat
    
    # Row 1 (y=0.5): จะถูกนำไปคำนวณตรงตาม Scenario ของเรา (ค่า 10.0 และ 50.0)
    # Row 2 (y=1.5): อยู่นอกพื้นที่ Polygon (box), จะได้ Weight=0 (ค่าจะเป็นอะไรก็ได้)
    data = np.array([
        [10.0, 50.0],
        [ 0.0,  0.0]
    ]) 
    
    da = xr.DataArray(
        data,
        coords={'latitude': lat, 'longitude': lon},
        dims=('latitude', 'longitude'),
        name='test_data_var'
    )

    # 2. Arrange Geometry
    # Create a box from x=0 to x=1.5 (Full coverage of first pixel, half of second)
    # y=0 to y=1 (Full height coverage)
    geometry = [box(0, 0, 1.5, 1)]
    gdf = gpd.GeoDataFrame(
        {'NAME_EN': ['VariableCountry'], 'geometry': geometry},
        crs="EPSG:4326"
    )

    # 3. Act
    result = calc_weighted_mean(da, "VariableCountry", gdf, "NAME_EN")

    # 4. Assert
    assert result is not None, "calc_weighted_mean returned None, check for errors in the function."
    
    # แปลง result กลับเป็น float (กรณี xarray คืนค่าเป็น 0d array) เพื่อความชัวร์ในการเช็คด้วย np.isclose
    result_val = float(result) if hasattr(result, '__float__') else result
    
    expected_value = 23.333333
    assert np.isclose(result_val, expected_value, rtol=1e-5), \
        f"Expected weighted mean ~{expected_value}, but got {result_val}. Weights might be ignored."

def test_calc_weighted_mean_country_not_found(sample_dataarray, sample_geodataframe):
    """
    Test behavior when country name is not found in GeoDataFrame.
    """
    # Arrange
    target_country = "NonExistentCountry"

    # Act - Added 'NAME_EN' as target_col
    result = calc_weighted_mean(sample_dataarray, target_country, sample_geodataframe, "NAME_EN")

    # Assert
    assert result is None, "Should return None if country not found"

def test_calc_weighted_mean_missing_column(sample_dataarray):
    """
    Test error handling when GDF lacks name columns.
    """
    # Arrange
    # Create GDF without NAME, ADMIN, or NAME_EN
    gdf_broken = gpd.GeoDataFrame({'WRONG_COL': ['A'], 'geometry': [box(0,0,1,1)]})
    
    # Act - Requested missing column 'NAME_EN'
    # The function prints error and returns None due to try-except block
    result = calc_weighted_mean(sample_dataarray, "A", gdf_broken, "NAME_EN")

    # Assert
    assert result is None, "Should return None if column lookup fails"

def test_calc_weighted_mean_with_time_dimension(sample_dataarray_with_time, sample_geodataframe):
    """
    Test if the function correctly handles data with a 'time' dimension.
    It should broadcast the 2D weights over the time dimension and return a time series.
    """
    # Arrange
    da = sample_dataarray_with_time
    target_country = "TestCountry" # Corresponds to sample_geodataframe fixture

    # Act - Added 'NAME_EN' as target_col
    result = calc_weighted_mean(da, target_country, sample_geodataframe, "NAME_EN")

    # Assert
    # 1. Check if result is not None
    assert result is not None, "Result should not be None for valid input"

    # 2. Check dimensions - 'time' should be preserved, lat/lon should be gone
    assert 'time' in result.dims, "Result should preserve the 'time' dimension"
    assert 'latitude' not in result.dims, "Spatial dims should be reduced"
    assert result.shape == (2,), "Result shape should match number of time steps (2,)"

    # 3. Check values
    # Time 0 should average to 10.0, Time 1 should average to 20.0
    expected_values = np.array([10.0, 20.0])
    np.testing.assert_allclose(result.values, expected_values, err_msg="Weighted mean should be calculated independently for each time step")