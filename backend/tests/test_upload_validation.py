import unittest
from typing import List, Dict, Any

# =============================================================================
# สมมติว่า detect_mode ถูก import มาจาก Module หลักของคุณ
# (ปรับแก้ path ตามโครงสร้างโปรเจกต์จริง เช่น from app.services.upload import detect_mode)
# =============================================================================
from processing.upload_validation import detect_mode 

class TestUploadValidation(unittest.TestCase):
    """
    Unit Tests for `detect_mode` function.
    Focuses on Set Theory logic to categorize upload modes:
    1. Time Mode: Sets are identical (A == B)
    2. Attribute Mode: Sets are disjoint (A intersect B == empty)
    3. Mixed Mode: Everything else (Overlaps, Subsets)
    """

    def make_meta(self, variables: List[str], start="2023-01-01", end="2023-12-31") -> Dict[str, Any]:
        """Helper to create dummy metadata dict."""
        return {
            "variables": variables,
            "time_start": start,
            "time_end": end,
            "filename": "dummy.nc"
        }

    # =========================================================================
    # 1. TIME MODE TESTS (Variable Sets must be Identical)
    # =========================================================================

    def test_time_mode_single_var_identical(self):
        """
        Case 1.1: Single variable, identical across files.
        File A: ['tmax']
        File B: ['tmax']
        -> Expect: TIME
        """
        metas = [
            self.make_meta(['tmax']),
            self.make_meta(['tmax'])
        ]
        mode, info, _ = detect_mode(metas)
        
        self.assertEqual(mode, "time")
        self.assertCountEqual(info['variables'], ['tmax'])

    def test_time_mode_multi_vars_identical(self):
        """
        Case 1.2: Multiple variables, identical sets (Exact Match).
        File A: ['tmax', 'pr']
        File B: ['tmax', 'pr']
        -> Expect: TIME
        """
        metas = [
            self.make_meta(['tmax', 'pr']),
            self.make_meta(['tmax', 'pr']) # Order doesn't matter for set equality usually, but input is list
        ]
        # Note: detect_mode logic uses list comparison or set comparison. 
        # If your logic converts to set, order implies equality.
        mode, info, _ = detect_mode(metas)
        
        self.assertEqual(mode, "time")
        # เช็คว่า info เก็บตัวแปรครบ
        self.assertTrue('tmax' in info['variables'])
        self.assertTrue('pr' in info['variables'])

    # =========================================================================
    # 2. ATTRIBUTE MODE TESTS (Variable Sets must be Disjoint)
    # =========================================================================

    def test_attribute_mode_single_var_disjoint(self):
        """
        Case 2.1: Single variable, completely different.
        File A: ['tmax']
        File B: ['pr']
        -> Expect: ATTRIBUTE
        """
        metas = [
            self.make_meta(['tmax']),
            self.make_meta(['pr'])
        ]
        mode, info, _ = detect_mode(metas)
        
        self.assertEqual(mode, "attribute")
        # Check var_map structure
        self.assertEqual(info['var_map']['tmax'], 0) # File index 0
        self.assertEqual(info['var_map']['pr'], 1)  # File index 1

    def test_attribute_mode_multi_vars_disjoint(self):
        """
        Case 2.2: Multiple variables, no overlap at all.
        File A: ['tmax', 'tasmax']
        File B: ['pr', 'hurs']
        -> Expect: ATTRIBUTE
        """
        metas = [
            self.make_meta(['tmax', 'tmin']),
            self.make_meta(['pr', 'hurs'])
        ]
        mode, info, _ = detect_mode(metas)
        
        self.assertEqual(mode, "attribute")
        self.assertEqual(len(info['var_map']), 4) # Should map 4 variables

    def test_attribute_mode_misaligned_time(self):
        """
        Case 2.3: Disjoint variables but different times.
        (Logic should ignore time and look only at variables)
        File A: ['tmax'] (2023)
        File B: ['pr']  (2025)
        -> Expect: ATTRIBUTE
        """
        metas = [
            self.make_meta(['tmax'], start="2023-01-01"),
            self.make_meta(['pr'],  start="2025-01-01")
        ]
        mode, _, _ = detect_mode(metas)
        
        self.assertEqual(mode, "attribute")

    # =========================================================================
    # 3. MIXED MODE TESTS (Partial Overlap / Complex)
    # =========================================================================

    def test_mixed_mode_subset_overlap(self):
        """
        Case 3.1: Subset (Variable missing in one file).
        File A: ['tmax', 'pr']
        File B: ['tmax']       (Missing pr)
        -> Expect: MIXED
        """
        metas = [
            self.make_meta(['tmax', 'pr']),
            self.make_meta(['tmax'])
        ]
        mode, info, _ = detect_mode(metas)
        
        self.assertEqual(mode, "mixed")
        # 'tmax' should be in both files (index 0 and 1)
        self.assertCountEqual(info['groups']['tmax'], [0, 1])
        # 'pr' should be only in file 0
        self.assertCountEqual(info['groups']['pr'], [0])

    def test_mixed_mode_cross_overlap(self):
        """
        Case 3.2: Cross Overlap (Chained).
        File A: ['tmax', 'pr']
        File B: ['pr', 'hurs']
        -> Expect: MIXED (Because 'pr' is repeated, fails Attribute check)
        """
        metas = [
            self.make_meta(['tmax', 'pr']),
            self.make_meta(['pr', 'hurs'])
        ]
        mode, info, _ = detect_mode(metas)
        
        self.assertEqual(mode, "mixed")
        # 'pr' is the link causing mixed mode
        self.assertCountEqual(info['groups']['pr'], [0, 1])
        self.assertEqual(info['groups']['tmax'], [0])
        self.assertEqual(info['groups']['hurs'], [1])

    def test_mixed_mode_three_files_hybrid(self):
        """
        Case 3.3: Hybrid case (A and B match, but C is different).
        File A: ['tmax']
        File B: ['tmax']
        File C: ['pr']
        -> Expect: MIXED
        (Why? Time check fails because A!=C. Attribute check fails because A overlaps B.)
        """
        metas = [
            self.make_meta(['tmax']), # 0
            self.make_meta(['tmax']), # 1
            self.make_meta(['pr'])   # 2
        ]
        mode, info, _ = detect_mode(metas)
        
        self.assertEqual(mode, "mixed")
        # Logic should group them correctly
        self.assertCountEqual(info['groups']['tmax'], [0, 1])
        self.assertCountEqual(info['groups']['pr'], [2])

if __name__ == "__main__":
    unittest.main()