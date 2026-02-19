import unittest
from unittest.mock import MagicMock, patch
import xarray as xr
import numpy as np
import pandas as pd
from typing import List, Dict, Any

# Import functions to test
from processing.upload_validation import (
    filter_dataset_vars, 
    map_and_rename_coord, 
    detect_mode,
    get_spatial_resolution,
    inspect_file,
    validate_compatibility
)

class TestUploadValidation(unittest.TestCase):

    def setUp(self):
        """
        Runs before each test method.
        Prepare common data structures here.
        """
        self.coords = {
            "time": pd.date_range("2024-01-01", periods=2),
            "lat": [10.0, 11.0],
            "lon": [100.0, 101.0]
        }

    # Helper method for detect_mode tests
    def make_meta(self, variables: List[str], filename="dummy.nc") -> Dict[str, Any]:
        """Helper to create dummy metadata dict for testing detect_mode."""
        return {
            "variables": variables,
            "filename": filename,
            # Add dummy time range if needed by other logic, though detect_mode focuses on vars
            "time_start": "2023-01-01",
            "time_end": "2023-12-31"
        }

    # ==========================================
    # Tests for filter_dataset_vars
    # ==========================================

    def test_filter_dataset_vars_should_drop_unallowed_vars(self):
        """
        Test that variables NOT in ALLOWED_VARS are removed, 
        and ALLOWED_VARS are kept.
        """
        # Arrange
        # Create a dataset with 'pr' (allowed) and 'unknown_var' (not allowed)
        data_vars = {
            "pr": (["time", "lat", "lon"], np.random.rand(2, 2, 2)),
            "unknown_var": (["time", "lat", "lon"], np.random.rand(2, 2, 2))
        }
        ds = xr.Dataset(data_vars=data_vars, coords=self.coords)

        # Act
        result_ds = filter_dataset_vars(ds)

        # Assert
        self.assertIn("pr", result_ds.data_vars, "Allowed variable 'pr' should remain.")
        self.assertNotIn("unknown_var", result_ds.data_vars, "Unallowed variable 'unknown_var' should be dropped.")

    def test_filter_dataset_vars_should_keep_coordinates(self):
        """
        Test that coordinates (like lat, lon, time) are NOT dropped 
        even if they are not in ALLOWED_VARS.
        """
        # Arrange
        data_vars = {"pr": (["time", "lat", "lon"], np.random.rand(2, 2, 2))}
        ds = xr.Dataset(data_vars=data_vars, coords=self.coords)

        # Act
        result_ds = filter_dataset_vars(ds)

        # Assert
        # Coordinates should still exist
        self.assertIn("lat", result_ds.coords)
        self.assertIn("lon", result_ds.coords)
        self.assertIn("time", result_ds.coords)

    def test_filter_dataset_vars_with_all_unallowed_vars(self):
        """
        Test that if all variables are unallowed, the resulting dataset 
        should have empty data_vars.
        """
        # Arrange
        data_vars = {
            "random1": (["time"], [1, 2]),
            "random2": (["time"], [3, 4])
        }
        ds = xr.Dataset(data_vars=data_vars, coords={"time": self.coords["time"]})

        # Act
        result_ds = filter_dataset_vars(ds)

        # Assert
        self.assertEqual(len(result_ds.data_vars), 0, "Dataset should have no data variables left.")

    # ==========================================
    # Tests for map_and_rename_coord
    # ==========================================

    def test_map_and_rename_coord_should_rename_alias_to_canonical(self):
        """
        Test that if an alias exists (e.g., 'lat'), it is renamed to the 
        canonical name (e.g., 'latitude').
        """
        # Arrange
        # Dataset uses 'lat', but we want 'latitude'
        ds = xr.Dataset(coords={"lat": [10, 20], "lon": [100, 110]})
        canonical_name = "latitude"
        aliases = ["lat", "latitude"]

        # Act
        result_ds, result_name = map_and_rename_coord(ds, canonical_name, aliases)

        # Assert
        self.assertIn("latitude", result_ds.coords, "Coordinate should be renamed to 'latitude'.")
        self.assertNotIn("lat", result_ds.coords, "Old alias 'lat' should not exist.")
        self.assertEqual(result_name, canonical_name, "Should return the canonical name.")

    def test_map_and_rename_coord_should_do_nothing_if_canonical_exists(self):
        """
        Test that if the canonical name already exists, no renaming occurs.
        """
        # Arrange
        # Dataset already uses 'latitude'
        ds = xr.Dataset(coords={"latitude": [10, 20]})
        canonical_name = "latitude"
        aliases = ["lat", "latitude"]

        # Act
        result_ds, result_name = map_and_rename_coord(ds, canonical_name, aliases)

        # Assert
        self.assertIn("latitude", result_ds.coords)
        self.assertEqual(result_name, canonical_name)

    def test_map_and_rename_coord_should_raise_keyerror_if_missing(self):
        """
        Test that KeyError is raised if neither the canonical name 
        nor any aliases are found in the dataset.
        """
        # Arrange
        # Dataset has 'x', 'y' but we look for 'latitude' or 'lat'
        ds = xr.Dataset(coords={"x": [1, 2], "y": [3, 4]})
        canonical_name = "latitude"
        aliases = ["lat", "latitude"]

        # Act & Assert
        with self.assertRaises(KeyError) as context:
            map_and_rename_coord(ds, canonical_name, aliases)
        
        # Verify exception message contains useful info
        self.assertIn("Required coordinate 'latitude' not found", str(context.exception))

    # =========================================================================
    # Tests for detect_mode
    # Logic: 
    #   - Time: Sets are identical (A == B)
    #   - Attribute: Sets are disjoint (A intersect B == empty)
    #   - Mixed: Everything else
    # =========================================================================

    def test_detect_mode_time_identical_variables(self):
        """
        Case: All files have exactly the same variables.
        Expect: 'time' mode.
        """
        # Arrange
        metas = [
            self.make_meta(['tmax', 'pr'], "file1.nc"),
            self.make_meta(['pr', 'tmax'], "file2.nc") # Different order, same set
        ]

        # Act
        mode, info, diagnostics = detect_mode(metas)

        # Assert
        self.assertEqual(mode, "time", "Should detect time mode when variables are identical.")
        # Check that info contains the variables list
        self.assertCountEqual(info['variables'], ['tmax', 'pr'])
        self.assertEqual(len(diagnostics), 0, "Time mode should be clean with no diagnostics.")

    def test_detect_mode_attribute_disjoint_variables(self):
        """
        Case: Files have completely different variables (No overlap).
        Expect: 'attribute' mode.
        """
        # Arrange
        metas = [
            self.make_meta(['tmax'], "file1.nc"),
            self.make_meta(['pr'], "file2.nc")
        ]

        # Act
        mode, info, diagnostics = detect_mode(metas)

        # Assert
        self.assertEqual(mode, "attribute", "Should detect attribute mode when variables are disjoint.")
        
        # Check var_map correctness (variable -> file_index)
        self.assertEqual(info['var_map']['tmax'], 0)
        self.assertEqual(info['var_map']['pr'], 1)

    def test_detect_mode_mixed_subset_variables(self):
        """
        Case: One file has a subset of another (Partial Overlap).
        File A: [tmax, pr]
        File B: [tmax]
        Expect: 'mixed' mode.
        """
        # Arrange
        metas = [
            self.make_meta(['tmax', 'pr'], "file1.nc"),
            self.make_meta(['tmax'], "file2.nc")
        ]

        # Act
        mode, info, diagnostics = detect_mode(metas)

        # Assert
        self.assertEqual(mode, "mixed", "Subset overlap should result in mixed mode.")
        
        # Check groups: 'tmax' appears in both files (0 and 1)
        self.assertCountEqual(info['groups']['tmax'], [0, 1])
        # 'pr' appears only in file 0
        self.assertEqual(info['groups']['pr'], [0])
        
        # Check diagnostics message
        self.assertTrue(len(diagnostics) > 0)
        self.assertIn("Mixed mode detected", diagnostics[0])

    def test_detect_mode_mixed_chain_overlap(self):
        """
        Case: Chained overlap.
        File A: [tmax, pr]
        File B: [pr, hurs]
        Expect: 'mixed' mode (because 'pr' connects them).
        """
        # Arrange
        metas = [
            self.make_meta(['tmax', 'pr'], "file1.nc"),
            self.make_meta(['pr', 'hurs'], "file2.nc")
        ]

        # Act
        mode, info, diagnostics = detect_mode(metas)

        # Assert
        self.assertEqual(mode, "mixed")
        self.assertCountEqual(info['groups']['pr'], [0, 1])

    def test_detect_mode_mixed_hybrid_case(self):
        """
        Case: 3 Files. A and B match (Time-like), but C is different (Attribute-like).
        File A: [tmax]
        File B: [tmax]
        File C: [pr]
        Expect: 'mixed' mode (Pattern is not consistent across ALL files).
        """
        # Arrange
        metas = [
            self.make_meta(['tmax'], "file1.nc"), # 0
            self.make_meta(['tmax'], "file2.nc"), # 1
            self.make_meta(['pr'], "file3.nc")    # 2
        ]

        # Act
        mode, info, _ = detect_mode(metas)

        # Assert
        self.assertEqual(mode, "mixed")
        self.assertCountEqual(info['groups']['tmax'], [0, 1])
        self.assertEqual(info['groups']['pr'], [2])

    
    # =========================================================================
    # Tests for get_spatial_resolution
    # Priority: Rio > Attributes > Coordinates
    # =========================================================================

    def test_get_spatial_resolution_priority_1_rioxarray(self):
        """
        Test Priority 1: If 'rio' accessor exists (rioxarray), use it.
        Fix: Use a full MagicMock instead of real xr.Dataset to avoid AttributeError.
        """
        # Arrange
        # use MagicMock instead xr.Dataset to avoid limit __setattr__ of xarray
        ds = MagicMock()
        
        # Setup behavior for .rio.resolution()
        # Returns (x_res, y_res) -> (lon_res, lat_res)
        ds.rio.resolution.return_value = (0.5, -0.5)

        # Setup attributes 
        ds.attrs = {"geospatial_lat_resolution": "999.0"} 

        # Act
        lat_res, lon_res = get_spatial_resolution(ds)

        # Assert
        self.assertEqual(lat_res, 0.5)
        self.assertEqual(lon_res, 0.5)

    def test_get_spatial_resolution_priority_2_attributes(self):
        """
        Test Priority 2: If no rio, parse global attributes.
        """
        # Arrange
        ds = xr.Dataset(coords={"latitude": [10, 20], "longitude": [100, 110]})
        
        # Mock no .rio (default xr.Dataset don't have)
        if hasattr(ds, "rio"): 
            del ds.rio 
            
        ds.attrs = {
            "geospatial_lat_resolution": "0.1 degrees",
            "geospatial_lon_resolution": 0.1
        }

        # Act
        lat_res, lon_res = get_spatial_resolution(ds)

        # Assert
        self.assertEqual(lat_res, 0.1)
        self.assertEqual(lon_res, 0.1)

    def test_get_spatial_resolution_priority_3_calculation(self):
        """
        Test Priority 3: Calculate from coordinate arrays.
        """
        # Arrange
        lat_vals = [10.0, 12.5, 15.0]
        lon_vals = [100.0, 102.5, 105.0]
        time_vals = pd.date_range("2024-01-01", periods=3)

        ds = xr.Dataset(
            coords={
                "latitude": lat_vals,
                "longitude": lon_vals,
                "time": time_vals 
            }
        )
        ds.attrs = {}

        # Act
        lat_res, lon_res = get_spatial_resolution(ds)

        # Assert
        self.assertEqual(lat_res, 2.5)
        self.assertEqual(lon_res, 2.5)

    def test_get_spatial_resolution_fail_single_coordinate(self):
        """
        Edge Case: Single point.
        """
        # Arrange
        ds = xr.Dataset(
            coords={
                "latitude": [10.0],
                "longitude": [100.0],
                "time": [1] 
            }
        )

        # Act
        lat_res, lon_res = get_spatial_resolution(ds)

        # Assert
        self.assertIsNone(lat_res)
        self.assertIsNone(lon_res)

    def test_get_spatial_resolution_fail_missing_coords(self):
        """
        Edge Case: Missing standard coordinates entirely.
        """
        # Arrange
        ds = xr.Dataset(coords={"x": [1, 2], "y": [3, 4]}) 

        # Act & Assert
        # will Raise KeyError because can't find Time (follow Logic map_and_rename_coord)
        
        with self.assertRaises(KeyError):
            get_spatial_resolution(ds)

    # =========================================================================
    # Tests for inspect_file
    # Complexity: High (Involves File I/O, xarray, time conversion)
    # Strategy: Mock ALL external dependencies (xarray, os, helpers)
    # =========================================================================

    @patch("processing.upload_validation.xr.open_dataset")
    @patch("processing.upload_validation.os.path.getsize")
    @patch("processing.upload_validation.get_spatial_resolution")
    @patch("processing.upload_validation.map_and_rename_coord")
    @patch("processing.upload_validation.normalize_var_name")
    @patch("processing.upload_validation.ALLOWED_VARS", {"tmax"}) # Mock constant
    def test_inspect_file_success_standard_metadata(
        self, 
        mock_normalize, 
        mock_map_coord, 
        mock_get_res, 
        mock_getsize, 
        mock_open_ds
    ):
        """
        Test Case: A standard NetCDF file with Time, Lat, Lon, and variables.
        Expectation: Returns a full dictionary with parsed metadata.
        """
        
        # Arrange 
    
        path = "dummy_data.nc"
        
        # Mock file size (e.g., 1 MB)
        mock_getsize.return_value = 1024 * 1024 

        # Mock Helper: normalize_var_name
        mock_normalize.return_value = "tmax"

        # Mock Helper: get_spatial_resolution
        mock_get_res.return_value = (0.5, 0.5)

        # Mock Helper: map_and_rename_coord
        mock_map_coord.side_effect = lambda ds, name, aliases: (ds, name)

        # Mock xarray Dataset
        mock_ds = MagicMock()
        
        # Mock Coordinates (Time, Lat, Lon)
        mock_ds.coords = {
            "time": MagicMock(),
            "latitude": MagicMock(),
            "longitude": MagicMock()
        }
        mock_ds.data_vars = {"tmax": MagicMock()} 
        mock_ds.sizes = {"time": 10, "latitude": 20, "longitude": 20}

        # Mock Time Values 
        # create datetime array 2020-01-01 to 2020-12-31 (1 year)
        mock_time_obj = MagicMock()
        t_start = np.datetime64("2020-01-01")
        t_end = np.datetime64("2020-12-31")
        mock_time_obj.values = np.array([t_start, t_end])
        mock_time_obj.min.return_value = t_start
        mock_time_obj.max.return_value = t_end
        # Mock Attributes for Calendar
        mock_time_obj.encoding = {"calendar": "gregorian"}
        
        # Mock Attributes for Units/Standard Names
        mock_var_obj = MagicMock()
        mock_var_obj.attrs = {"units": "K", "standard_name": "air_temperature"}
        
        def getitem_side_effect(key):
            if key == "time":
                return mock_time_obj
            else:
                return mock_var_obj
        
        mock_ds.__getitem__.side_effect = getitem_side_effect
        # connect Mock Dataset to xr.open_dataset
        mock_open_ds.return_value = mock_ds

        # Act 
        result = inspect_file(path)

        # Assert 
        # Check File Info
        self.assertEqual(result["file_size"], "1.00 MB")
        self.assertEqual(result["shape"], {"time": 10, "latitude": 20, "longitude": 20})
        
        # Check Time Logic
        self.assertEqual(result["time_start"], "2020-01-01T00:00:00")
        self.assertEqual(result["time_end"], "2020-12-31T00:00:00")
        # 365 days / 365.25 approx 0.99 or 1.00 depending on rounding in code
        self.assertIsNotNone(result["time_years"]) 

        # Check Spatial Resolution (Logic: f"{lat:.3f}° x {lon:.3f}°")
        self.assertEqual(result["spatial_resolution"], "0.500° x 0.500°")
        
        # Check Variables & Units
        self.assertIn("tmax", result["variables"])
        self.assertEqual(result["variable_units"]["tmax"], "K")

    @patch("processing.upload_validation.xr.open_dataset")
    @patch("processing.upload_validation.os.path.getsize")
    def test_inspect_file_io_error(self, mock_getsize, mock_open_ds):
        """
        Test Case: File is corrupted or cannot be opened.
        Expectation: Returns a dict with "error" key.
        """
        # Arrange
        path = "bad_file.nc"
        mock_getsize.return_value = 0
        # xr.open_dataset Raise Exception
        mock_open_ds.side_effect = Exception("File corrupted")

        # Act
        result = inspect_file(path)

        # Assert
        self.assertIn("error", result, "Should return dictionary with error key.")
        self.assertEqual(result["error"], "File corrupted")

    # =========================================================================
    # Tests for validate_compatibility
    # Checks: Empty list, File errors, Calendar mismatch, Resolution mismatch
    # =========================================================================

    # def test_validate_compatibility_empty_input(self, mock_detect_mode):
    #     """
    #     Test Case: Input list is empty.
    #     Expectation: Returns False with specific error message.
    #     """
    #     # Arrange
    #     metas = []

    #     # Act
    #     from processing.upload_validation import validate_compatibility
    #     is_valid, errors = validate_compatibility(metas)

    #     # Assert
    #     self.assertFalse(is_valid)
    #     self.assertIn("No files provided.", errors)
    #     # Verify detect_mode was NOT called (it should return early)
    #     mock_detect_mode.assert_not_called()

    def test_validate_compatibility_with_error_files(self):
        """
        Test Case: Input contains files that failed inspection (have "error" key).
        Expectation: Returns False immediately.
        """
        # Arrange
        metas = [
            {"filename": "good.nc", "calendar": "gregorian"}, # Valid file
            {"filename": "bad.nc", "error": "Corrupted file"} # Error file
        ]

        # Act
        is_valid, errors = validate_compatibility(metas)

        # Assert
        self.assertFalse(is_valid)
        self.assertIn("Some files could not be read.", errors)

    def test_validate_compatibility_inconsistent_calendar(self):
        """
        Test Case: Files have different calendar systems.
        Expectation: Returns False with calendar error.
        """
        # Arrange
        metas = [
            {"filename": "f1.nc", "calendar": "gregorian", "lat_res": 0.5, "lon_res": 0.5},
            {"filename": "f2.nc", "calendar": "noleap",    "lat_res": 0.5, "lon_res": 0.5}
        ]

        # Act
        is_valid, errors = validate_compatibility(metas)

        # Assert
        self.assertFalse(is_valid)
        # Check if error message mentions inconsistent calendars
        self.assertTrue(any("Inconsistent calendars" in e for e in errors))

    def test_validate_compatibility_inconsistent_resolution(self):
        """
        Test Case: Files have significantly different spatial resolutions.
        Expectation: Returns False with resolution error.
        """
        # Arrange
        metas = [
            {"filename": "f1.nc", "calendar": "gregorian", "lat_res": 0.5, "lon_res": 0.5},
            {"filename": "f2.nc", "calendar": "gregorian", "lat_res": 0.25, "lon_res": 0.25}
        ]

        # Act
        is_valid, errors = validate_compatibility(metas)

        # Assert
        self.assertFalse(is_valid)
        # Check specific error content
        self.assertTrue(any("Inconsistent spatial resolution" in e for e in errors))
        self.assertTrue(any("0.25" in e for e in errors))

    # def test_validate_compatibility_resolution_tolerance_success(self, mock_detect_mode):
    #     """
    #     Test Case: Files have slightly different resolutions (floating point noise).
    #     Expectation: Returns True because np.isclose allows small tolerance (1e-05).
    #     """
    #     # Arrange
    #     metas = [
    #         # Base file: 0.5
    #         {"filename": "f1.nc", "calendar": "standard", "lat_res": 0.5, "lon_res": 0.5},
    #         # Second file: 0.5000001 (very small difference)
    #         {"filename": "f2.nc", "calendar": "standard", "lat_res": 0.5000001, "lon_res": 0.5}
    #     ]
    #     # Mock detect_mode to allow passing through
    #     mock_detect_mode.return_value = ("time", {}, [])

    #     # Act
    #     is_valid, errors = validate_compatibility(metas)

    #     # Assert
    #     self.assertTrue(is_valid, "Should allow small floating point differences.")
    #     self.assertEqual(len(errors), 0)

    def test_validate_compatibility_happy_path(self):
        """
        Test Case: All files are perfectly compatible.
        Expectation: Returns True with no errors.
        """
        # Arrange
        metas = [
            {"filename": "f1.nc", "calendar": "gregorian", "lat_res": 0.5, "lon_res": 0.5},
            {"filename": "f2.nc", "calendar": "gregorian", "lat_res": 0.5, "lon_res": 0.5}
        ]

        # Act
        is_valid, errors = validate_compatibility(metas)

        # Assert
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

if __name__ == '__main__':
    unittest.main()