import pytest
import xarray as xr
import numpy as np
import geopandas as gpd
import rioxarray 
from shapely.geometry import Polygon, Point
from processing.clipping import (
    resolve_country_names,
    prep_for_rio,
    mask_by_country,
    clip_to_shape
)
from unittest.mock import patch, MagicMock

# ==========================================
# Create Synthetic Spatial Data
# ==========================================
@pytest.fixture
def spatial_da():
    """
    Creates a 10x10 degree DataArray covering lat/lon (0-10, 0-10).
    Value is 1.0 everywhere.
    Resolution is 1.0 degree per pixel.
    """
    lon = np.arange(0.5, 10.5, 1)  # 0.5, 1.5, ... 9.5
    lat = np.arange(0.5, 10.5, 1)
    data = np.ones((10, 10))
    
    da = xr.DataArray(
        data,
        coords={"latitude": lat, "longitude": lon},
        dims=("latitude", "longitude"),
        name="test_var"
    )
    return da

@pytest.fixture
def mock_countries_gdf():
    """
    Creates a GeoDataFrame with two polygons:
    1. 'BigCountry': Covers half the map.
    2. 'SmallIsland': Tiny point/polygon inside a pixel.
    """
    # Big square from (-1 ถึง 6)
    poly_big = Polygon([(-1, -1), (6, -1), (6, 6), (-1, 6)])
    
    # Tiny square at (8.1, 8.1) to (8.2, 8.2) - smaller than grid resolution
    poly_small = Polygon([(8.1, 8.1), (8.2, 8.1), (8.2, 8.2), (8.1, 8.2)])
    
    gdf = gpd.GeoDataFrame(
        {
            "ADMIN": ["BigCountry", "SmallIsland"],
            "geometry": [poly_big, poly_small]
        },
        crs="EPSG:4326"
    )
    return gdf

# ==========================================
# Test Helper Functions
# ==========================================
def test_resolve_country_names_no_alias():
    # Test that country without alias returns itself only
    names = resolve_country_names("Thailand")
    assert names == ["Thailand"]

def test_resolve_country_names_with_alias():
    # Test that country with alias returns all possible names
    names = resolve_country_names("Timor-Leste")
    assert "Timor-Leste" in names
    assert "East Timor" in names

def test_prep_for_rio_sets_crs(spatial_da):
    # Test CRS assignment
    assert spatial_da.rio.crs is None
    da = prep_for_rio(spatial_da)
    assert da.rio.crs is not None
    assert da.rio.crs.to_string() == "EPSG:4326"

def test_prep_for_rio_sets_spatial_dims(spatial_da):
    # Test spatial dimension names
    da = prep_for_rio(spatial_da)
    assert da.rio.x_dim == "longitude"
    assert da.rio.y_dim == "latitude"

# ==========================================
# Test Masking
# ==========================================
def test_mask_by_country_normal_clip(spatial_da, mock_countries_gdf):
    """
    Test standard clipping logic.
    'BigCountry' covers top-left 5x5 area.
    Expect: Data inside is 1.0, outside is NaN.
    """
    da_ready = prep_for_rio(spatial_da)
    
    clipped = mask_by_country(da_ready, "BigCountry", mock_countries_gdf)
    
    assert clipped is not None
    # Check that we have some valid data
    assert clipped.notnull().any()
    
    # Check size (Should be smaller or equal to original bounding box)
    assert clipped.shape != spatial_da.shape

def test_mask_by_country_fallback_logic(spatial_da, mock_countries_gdf):
    """
    Test the critical 'Fallback' logic for small islands.
    'SmallIsland' is too small for standard clip (might fall between grid centers).
    The code should switch to 'nearest' neighbor interpolation.
    """
    da_ready = prep_for_rio(spatial_da)
    log_dict = {}
    
    # SmallIsland is at 8.5, 8.5. Grid has point at 8.5, 8.5.
    result = mask_by_country(da_ready, "SmallIsland", mock_countries_gdf, log=log_dict)
    
    assert result is not None
    
    # It should return a single point (0D or 1x1 2D array depending on impl)
    # The 'nearest' selection usually returns a scalar or reduced dim
    assert result.size == 1 
    assert result.item() == 1.0 # The value in our data
    
    # Verify log indicates fallback was used
    assert "SmallIsland" in log_dict
    assert log_dict["SmallIsland"]["method"] == "nearest"

@patch("geopandas.read_file")
def test_clip_to_shape_file_io(mock_read_file, spatial_da):
    """
    Test clip_to_shape without real files.
    We mock geopandas.read_file to return a dummy GeoDataFrame.
    """
    # Setup Mock
    dummy_gdf = gpd.GeoDataFrame(
        {"geometry": [Polygon([(0,0), (1,0), (1,1), (0,1)])]},
        crs="EPSG:4326"
    )
    mock_read_file.return_value = dummy_gdf
    
    # Prepare Input
    da_ready = prep_for_rio(spatial_da)
    
    # Run Function
    result = clip_to_shape(da_ready, "dummy_path.shp")
    
    # Assert
    mock_read_file.assert_called_with("dummy_path.shp")
    assert result is not None
    # Should be clipped to the dummy polygon (0-1)
    assert result.shape == (1, 1) # roughly, depending on grid alignment