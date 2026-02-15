import unittest
import xarray as xr
import numpy as np
import pandas as pd
from typing import List, Dict, Any

# Import functions to test
from processing.upload_validation import (
    filter_dataset_vars, 
    map_and_rename_coord, 
    detect_mode
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
        aliases = ["lat", "latitude", "nav_lat"]

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

if __name__ == '__main__':
    unittest.main()

# import unittest
# from typing import List, Dict, Any

# # =============================================================================
# # สมมติว่า detect_mode ถูก import มาจาก Module หลักของคุณ
# # (ปรับแก้ path ตามโครงสร้างโปรเจกต์จริง เช่น from app.services.upload import detect_mode)
# # =============================================================================
# from processing.upload_validation import detect_mode 

# class TestUploadValidation(unittest.TestCase):
#     """
#     Unit Tests for `detect_mode` function.
#     Focuses on Set Theory logic to categorize upload modes:
#     1. Time Mode: Sets are identical (A == B)
#     2. Attribute Mode: Sets are disjoint (A intersect B == empty)
#     3. Mixed Mode: Everything else (Overlaps, Subsets)
#     """

#     def make_meta(self, variables: List[str], start="2023-01-01", end="2023-12-31") -> Dict[str, Any]:
#         """Helper to create dummy metadata dict."""
#         return {
#             "variables": variables,
#             "time_start": start,
#             "time_end": end,
#             "filename": "dummy.nc"
#         }

#     # =========================================================================
#     # 1. TIME MODE TESTS (Variable Sets must be Identical)
#     # =========================================================================

#     def test_time_mode_single_var_identical(self):
#         """
#         Case 1.1: Single variable, identical across files.
#         File A: ['tmax']
#         File B: ['tmax']
#         -> Expect: TIME
#         """
#         metas = [
#             self.make_meta(['tmax']),
#             self.make_meta(['tmax'])
#         ]
#         mode, info, _ = detect_mode(metas)
        
#         self.assertEqual(mode, "time")
#         self.assertCountEqual(info['variables'], ['tmax'])

#     def test_time_mode_multi_vars_identical(self):
#         """
#         Case 1.2: Multiple variables, identical sets (Exact Match).
#         File A: ['tmax', 'pr']
#         File B: ['tmax', 'pr']
#         -> Expect: TIME
#         """
#         metas = [
#             self.make_meta(['tmax', 'pr']),
#             self.make_meta(['tmax', 'pr']) # Order doesn't matter for set equality usually, but input is list
#         ]
#         # Note: detect_mode logic uses list comparison or set comparison. 
#         # If your logic converts to set, order implies equality.
#         mode, info, _ = detect_mode(metas)
        
#         self.assertEqual(mode, "time")
#         # เช็คว่า info เก็บตัวแปรครบ
#         self.assertTrue('tmax' in info['variables'])
#         self.assertTrue('pr' in info['variables'])

#     # =========================================================================
#     # 2. ATTRIBUTE MODE TESTS (Variable Sets must be Disjoint)
#     # =========================================================================

#     def test_attribute_mode_single_var_disjoint(self):
#         """
#         Case 2.1: Single variable, completely different.
#         File A: ['tmax']
#         File B: ['pr']
#         -> Expect: ATTRIBUTE
#         """
#         metas = [
#             self.make_meta(['tmax']),
#             self.make_meta(['pr'])
#         ]
#         mode, info, _ = detect_mode(metas)
        
#         self.assertEqual(mode, "attribute")
#         # Check var_map structure
#         self.assertEqual(info['var_map']['tmax'], 0) # File index 0
#         self.assertEqual(info['var_map']['pr'], 1)  # File index 1

#     def test_attribute_mode_multi_vars_disjoint(self):
#         """
#         Case 2.2: Multiple variables, no overlap at all.
#         File A: ['tmax', 'tasmax']
#         File B: ['pr', 'hurs']
#         -> Expect: ATTRIBUTE
#         """
#         metas = [
#             self.make_meta(['tmax', 'tmin']),
#             self.make_meta(['pr', 'hurs'])
#         ]
#         mode, info, _ = detect_mode(metas)
        
#         self.assertEqual(mode, "attribute")
#         self.assertEqual(len(info['var_map']), 4) # Should map 4 variables

#     def test_attribute_mode_misaligned_time(self):
#         """
#         Case 2.3: Disjoint variables but different times.
#         (Logic should ignore time and look only at variables)
#         File A: ['tmax'] (2023)
#         File B: ['pr']  (2025)
#         -> Expect: ATTRIBUTE
#         """
#         metas = [
#             self.make_meta(['tmax'], start="2023-01-01"),
#             self.make_meta(['pr'],  start="2025-01-01")
#         ]
#         mode, _, _ = detect_mode(metas)
        
#         self.assertEqual(mode, "attribute")

#     # =========================================================================
#     # 3. MIXED MODE TESTS (Partial Overlap / Complex)
#     # =========================================================================

#     def test_mixed_mode_subset_overlap(self):
#         """
#         Case 3.1: Subset (Variable missing in one file).
#         File A: ['tmax', 'pr']
#         File B: ['tmax']       (Missing pr)
#         -> Expect: MIXED
#         """
#         metas = [
#             self.make_meta(['tmax', 'pr']),
#             self.make_meta(['tmax'])
#         ]
#         mode, info, _ = detect_mode(metas)
        
#         self.assertEqual(mode, "mixed")
#         # 'tmax' should be in both files (index 0 and 1)
#         self.assertCountEqual(info['groups']['tmax'], [0, 1])
#         # 'pr' should be only in file 0
#         self.assertCountEqual(info['groups']['pr'], [0])

#     def test_mixed_mode_cross_overlap(self):
#         """
#         Case 3.2: Cross Overlap (Chained).
#         File A: ['tmax', 'pr']
#         File B: ['pr', 'hurs']
#         -> Expect: MIXED (Because 'pr' is repeated, fails Attribute check)
#         """
#         metas = [
#             self.make_meta(['tmax', 'pr']),
#             self.make_meta(['pr', 'hurs'])
#         ]
#         mode, info, _ = detect_mode(metas)
        
#         self.assertEqual(mode, "mixed")
#         # 'pr' is the link causing mixed mode
#         self.assertCountEqual(info['groups']['pr'], [0, 1])
#         self.assertEqual(info['groups']['tmax'], [0])
#         self.assertEqual(info['groups']['hurs'], [1])

#     def test_mixed_mode_three_files_hybrid(self):
#         """
#         Case 3.3: Hybrid case (A and B match, but C is different).
#         File A: ['tmax']
#         File B: ['tmax']
#         File C: ['pr']
#         -> Expect: MIXED
#         (Why? Time check fails because A!=C. Attribute check fails because A overlaps B.)
#         """
#         metas = [
#             self.make_meta(['tmax']), # 0
#             self.make_meta(['tmax']), # 1
#             self.make_meta(['pr'])   # 2
#         ]
#         mode, info, _ = detect_mode(metas)
        
#         self.assertEqual(mode, "mixed")
#         # Logic should group them correctly
#         self.assertCountEqual(info['groups']['tmax'], [0, 1])
#         self.assertCountEqual(info['groups']['pr'], [2])

# if __name__ == "__main__":
#     unittest.main()