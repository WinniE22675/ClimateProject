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


def test_get_raw_path_creates_directory(temp_workdir):
    """
    get_raw_path should return correct path and create directory
    """
    slot_id = 1
    path = dp.get_raw_path(slot_id)

    expected = os.path.join("uploads", "raw", "dataset_1")

    assert path == expected
    assert os.path.isdir(path)

def test_get_processed_path_creates_directory(temp_workdir):
    """
    get_processed_path should create processed dataset directory
    """
    dataset_name = "spi_monthly"
    path = dp.get_processed_path(dataset_name)

    expected = os.path.join("uploads", "processed", dataset_name)

    assert path == expected
    assert os.path.isdir(path)

def test_get_processed_path_with_different_names(temp_workdir):
    """
    Different dataset names should result in different directories
    """
    p1 = dp.get_processed_path("ds1")
    p2 = dp.get_processed_path("ds2")

    assert p1 != p2
    assert os.path.isdir(p1)
    assert os.path.isdir(p2)

def test_get_dataset_output_dir_creates_directory(temp_workdir):
    """
    get_dataset_output_dir should create output directory
    """
    dataset_name = "climate_risk_map"
    path = dp.get_dataset_output_dir(dataset_name)

    expected = os.path.join("output", dataset_name)

    assert path == expected
    assert os.path.isdir(path)

def test_output_dir_is_independent_from_uploads(temp_workdir):
    """
    Output directory should not be under uploads/
    """
    path = dp.get_dataset_output_dir("test_ds")

    assert path.startswith("output")
    assert not path.startswith("uploads")