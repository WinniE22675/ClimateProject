import os
import pytest

# Import module under test
import services.dataset_paths as dp


@pytest.fixture
def temp_workdir(tmp_path, monkeypatch):
    """
    Create isolated working directory for filesystem tests
    """
    monkeypatch.chdir(tmp_path)
    return tmp_path


# ==========================================
# 1. Tests for Upload / Raw / Processed Paths
# ==========================================

def test_get_raw_path_creates_directory(temp_workdir):
    """
    get_raw_path should return correct path and create directory
    """
    # Arrange
    user_id = "user123"
    slot_id = 1
    expected = os.path.join("uploads", f"user_{user_id}", "raw", f"dataset_{slot_id}")

    # Act
    path = dp.get_raw_path(user_id, slot_id)

    # Assert
    assert path == expected
    assert os.path.isdir(path)

def test_get_processed_path_creates_directory(temp_workdir):
    """
    get_processed_path should create processed dataset directory
    """
    # Arrange
    user_id = "user123"
    dataset_name = "spi_monthly"
    expected = os.path.join("uploads", f"user_{user_id}", "processed", dataset_name)

    # Act
    path = dp.get_processed_path(user_id, dataset_name)

    # Assert
    assert path == expected
    assert os.path.isdir(path)

def test_get_processed_path_with_different_names(temp_workdir):
    """
    Different dataset names should result in different directories
    """
    # Arrange
    user_id = "user123"

    # Act
    p1 = dp.get_processed_path(user_id, "ds1")
    p2 = dp.get_processed_path(user_id, "ds2")

    # Assert
    assert p1 != p2
    assert os.path.isdir(p1)
    assert os.path.isdir(p2)

def test_get_dataset_output_dir_creates_directory(temp_workdir):
    """
    get_dataset_output_dir should create output directory
    """
    # Arrange
    dataset_name = "climate_risk_map"
    expected = os.path.join("output", dataset_name)

    # Act
    path = dp.get_dataset_output_dir(dataset_name)

    # Assert
    assert path == expected
    assert os.path.isdir(path)

def test_output_dir_is_independent_from_uploads(temp_workdir):
    """
    Output directory should not be under uploads/
    """
    # Arrange & Act
    path = dp.get_dataset_output_dir("test_ds")

    # Assert
    assert path.startswith("output")
    assert not path.startswith("uploads")


# ==========================================
# 2. Tests for Shapefile Paths
# ==========================================

def test_get_user_shapefile_dir(temp_workdir):
    """
    get_user_shapefile_dir should create and return the user shapefile directory.
    """
    # Arrange
    user_id = "user123"
    expected = os.path.join("uploads", f"user_{user_id}", "shapefiles")

    # Act
    path = dp.get_user_shapefile_dir(user_id)

    # Assert
    assert path == expected
    assert os.path.isdir(path)

def test_get_global_shapefile_dir(temp_workdir):
    """
    get_global_shapefile_dir should create and return the global shapefile directory.
    """
    # Arrange
    expected = os.path.join("data", "shapefiles")

    # Act
    path = dp.get_global_shapefile_dir()

    # Assert
    assert path == expected
    assert os.path.isdir(path)

def test_get_shapefile_path_user_dir_success(temp_workdir):
    """
    Test finding a shapefile (.shp) in the user directory successfully.
    """
    # Arrange
    user_id = "user123"
    shape_name = "my_boundary"
    
    # Create the mocked folder and file structure
    target_dir = os.path.join("uploads", f"user_{user_id}", "shapefiles", shape_name)
    os.makedirs(target_dir, exist_ok=True)
    
    # Create a dummy .shp file
    dummy_shp = os.path.join(target_dir, "boundary.shp")
    open(dummy_shp, 'w').close()

    # Act
    path = dp.get_shapefile_path(user_id, shape_name)

    # Assert
    assert path == dummy_shp

def test_get_shapefile_path_global_dir_fallback_success(temp_workdir):
    """
    Test fallback to global directory when shapefile is not in the user directory.
    Checks for .geojson file support.
    """
    # Arrange
    user_id = "user123"
    shape_name = "thailand_map"
    
    # Create ONLY the global folder and file structure
    target_dir = os.path.join("data", "shapefiles", shape_name)
    os.makedirs(target_dir, exist_ok=True)
    
    # Create a dummy .geojson file
    dummy_geojson = os.path.join(target_dir, "th_boundary.geojson")
    open(dummy_geojson, 'w').close()

    # Act
    path = dp.get_shapefile_path(user_id, shape_name)

    # Assert
    assert path == dummy_geojson

def test_get_shapefile_path_dir_not_found(temp_workdir):
    """
    Test that Exception is raised if the shapefile directory doesn't exist anywhere.
    """
    # Arrange
    user_id = "user123"
    shape_name = "missing_shape"

    # Act & Assert
    with pytest.raises(Exception, match=f"Shapefile '{shape_name}' directory not found"):
        dp.get_shapefile_path(user_id, shape_name)

def test_get_shapefile_path_no_valid_files(temp_workdir):
    """
    Test that Exception is raised if the directory exists but contains no .shp or .geojson files.
    """
    # Arrange
    user_id = "user123"
    shape_name = "empty_shape"
    
    # Create folder but NO valid shapefiles inside
    target_dir = os.path.join("uploads", f"user_{user_id}", "shapefiles", shape_name)
    os.makedirs(target_dir, exist_ok=True)
    
    dummy_txt = os.path.join(target_dir, "readme.txt")
    open(dummy_txt, 'w').close()

    # Act & Assert
    with pytest.raises(Exception, match="No .shp or .geojson file found inside the directory"):
        dp.get_shapefile_path(user_id, shape_name)