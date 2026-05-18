import unittest
import os
import shutil
import tempfile
import numpy as np
import pandas as pd
import xarray as xr
from typing import List

# Assuming your code is in backend/processing/merge_datasets.py
# Adjust the import according to your actual folder structure
# For this example, let's assume we import the functions directly.
from processing.merge_datasets import (
    merge_attribute_mode,
    merge_time_mode,
    merge_mixed_mode,
)

class TestMergeDatasets(unittest.TestCase):
    
    def setUp(self):
        """
        Runs before each test. Creates a temporary directory for dummy .nc files.
        """
        self.test_dir = tempfile.mkdtemp()
        self.output_dir = os.path.join(self.test_dir, "output")
        os.makedirs(self.output_dir, exist_ok=True)

    def tearDown(self):
        """
        Runs after each test. Cleans up the temporary directory.
        """
        shutil.rmtree(self.test_dir)

    def create_dummy_nc(self, filename: str, var_name: str, 
                        start_time: str, days: int, 
                        value_offset: float = 0.0) -> str:
        """
        Helper function to generate a valid NetCDF file for testing.
        
        Args:
            filename: Name of the file.
            var_name: Name of the data variable.
            start_time: Start date string (e.g., '2023-01-01').
            days: Number of time steps.
            value_offset: Value to add to data to distinguish files.
            
        Returns:
            Full path to the created file.
        """
        # Create coordinates
        times = pd.date_range(start=start_time, periods=days, freq='D')
        lats = np.array([10.0, 11.0])
        lons = np.array([100.0, 101.0])
        
        # Create dummy data
        data = np.random.rand(len(times), len(lats), len(lons)) + value_offset
        
        # Create Dataset
        ds = xr.Dataset(
            {var_name: (("time", "lat", "lon"), data)},
            coords={
                "time": times,
                "lat": lats,
                "lon": lons
            }
        )
        
        # Add a dummy skip variable to test filtering (e.g., 'height')
        ds["height"] = (("lat", "lon"), np.ones((2, 2)))
        
        path = os.path.join(self.test_dir, filename)
        ds.to_netcdf(path)
        ds.close()
        return path
    
    def test_merge_attribute_mode_success(self):
        """
        Test merging two files with different variables (Spatial Merge).
        """
        # Prepare: Create tempmax.nc and precip.nc (same time/space)
        path1 = self.create_dummy_nc("tempmax.nc", "tmax", "2023-01-01", 5)
        path2 = self.create_dummy_nc("precip.nc", "pr", "2023-01-01", 5)
        
        # Act
        success, result, errors = merge_attribute_mode([path1, path2], self.output_dir)
        
        # Assert
        self.assertTrue(success, f"Merge failed with errors: {errors}")
        self.assertEqual(len(errors), 0)
        
        # Load result to verify
        ds_out = xr.open_dataset(result['path'])
        self.assertIn("tmax", ds_out.data_vars)
        self.assertIn("pr", ds_out.data_vars)
        
        # Check if SKIP_VARS ('height') was removed
        self.assertNotIn("height", ds_out.data_vars)
        self.assertNotIn("height", ds_out.coords)
        ds_out.close()

    def test_merge_attribute_mode_both_gaps(self):
        """
        Test Attribute Merge when both input files have missing time steps.
        Scenario:
          - File 1 (tmax): Has Jan 01, Jan 03. (Missing Jan 02)
          - File 2 (pr):  Has Jan 02, Jan 03. (Missing Jan 01)
        Expectation:
          - Result Time: Jan 01, 02, 03 (Union of times)
          - tmax at Jan 02 should be NaN
          - pr at Jan 01 should be NaN
        """
        import xarray as xr
        import numpy as np

        # 1. สร้างไฟล์ tmax (มี 3 วัน แล้วลบวันที่ 2 ออก)
        path1 = self.create_dummy_nc("tmax_gapped.nc", "tmax", "2023-01-01", 3, value_offset=10.0)
        with xr.open_dataset(path1) as ds_temp:
            ds1 = ds_temp.drop_sel(time="2023-01-02")
            ds1.load()
        ds1.to_netcdf(path1) # บันทึกทับ
        ds1.close()

        # 2. สร้างไฟล์ pr (มี 3 วัน แล้วลบวันที่ 1 ออก)
        path2 = self.create_dummy_nc("pr_gapped.nc", "pr", "2023-01-01", 3, value_offset=20.0)
        with xr.open_dataset(path2) as ds_temp:
            ds2 = ds_temp.drop_sel(time="2023-01-01")
            ds2.load()
        ds2.to_netcdf(path2) # บันทึกทับ
        ds2.close()

        # 3. รวมไฟล์ (Attribute Mode)
        success, result, errors = merge_attribute_mode([path1, path2], self.output_dir)
        self.assertTrue(success, f"Merge failed: {errors}")
        ds = xr.open_dataset(result['path'])

        # --- ตรวจสอบผลลัพธ์ ---
        
        # ต้องมีเวลาครบ 3 วัน (1, 2, 3) เพราะมันเอาเวลาของทั้งคู่มารวมกัน (Outer Join)
        self.assertEqual(ds.sizes['time'], 3)
        
        # เรียงเวลาให้แน่ใจ (xarray merge มักจะเรียงให้อัตโนมัติ แต่กันพลาด)
        ds = ds.sortby("time")

        # เช็ค tmax (วันที่ 2 ต้องเป็น NaN เพราะไฟล์ tmax ไม่มีวันที่ 2)
        val_tas_jan02 = ds['tmax'].sel(time="2023-01-02").values
        self.assertTrue(np.isnan(val_tas_jan02).all(), "tmax should be NaN on Jan 02")
        
        # เช็ค pr (วันที่ 1 ต้องเป็น NaN เพราะไฟล์ pr ไม่มีวันที่ 1)
        val_pr_jan01 = ds['pr'].sel(time="2023-01-01").values
        self.assertTrue(np.isnan(val_pr_jan01).all(), "pr should be NaN on Jan 01")

        # เช็ควันที่ 3 (มีทั้งคู่ ต้องมีค่าทั้งคู่)
        val_tas_jan03 = ds['tmax'].sel(time="2023-01-03").values
        val_pr_jan03 = ds['pr'].sel(time="2023-01-03").values
        self.assertFalse(np.isnan(val_tas_jan03).any())
        self.assertFalse(np.isnan(val_pr_jan03).any())

        ds.close()

    def test_merge_attribute_missing_same_gap(self):
        """
        Test Case: Both input files are missing the SAME date.
        Scenario:
            - File 1 (tmax): Jan 01, Jan 03 (Missing Jan 02)
            - File 2 (pr):  Jan 01, Jan 03 (Missing Jan 02)
        Expectation:
            - The merged result will ALSO miss Jan 02.
            - This test proves that without gap filling, the output is discontinuous.
        """
        import xarray as xr
        import numpy as np
        import pandas as pd

        # 1. สร้างไฟล์ tmax (มี 3 วัน แล้วลบวันที่ 2 ทิ้ง)
        path1 = self.create_dummy_nc("tmax_gap_same.nc", "tmax", "2023-01-01", 3, value_offset=10.0)
        with xr.open_dataset(path1) as ds_temp:
            ds1 = ds_temp.drop_sel(time="2023-01-02")
            ds1.load()
        ds1.to_netcdf(path1)
        ds1.close()

        # 2. สร้างไฟล์ pr (ทำเหมือนกัน ลบวันที่ 2 ทิ้ง)
        path2 = self.create_dummy_nc("pr_gap_same.nc", "pr", "2023-01-01", 3, value_offset=20.0)
        with xr.open_dataset(path2) as ds_temp:
            ds2 = ds_temp.drop_sel(time="2023-01-02")
            ds2.load()
        ds2.to_netcdf(path2)
        ds2.close()

        # 3. สั่งรวมไฟล์ (Attribute Mode)
        success, result, errors = merge_attribute_mode([path1, path2], self.output_dir)
        self.assertTrue(success, f"Merge failed: {errors}")
        
        # โหลดผลลัพธ์มาเช็ค
        ds_out = xr.open_dataset(result['path'])
        
        try:
            # --- ตรวจสอบผลลัพธ์ ---
            
            # 1. เช็คจำนวนวัน: ควรเหลือแค่ 2 วัน (Jan 1, Jan 3)
            # self.assertEqual(ds_out.sizes['time'], 2, "Should have only 2 days because gap is not filled yet")
            self.assertEqual(ds_out.sizes['time'], 3, "Should fill the gap to 3 days")
            
            # 2. เช็คว่าวันที่ 2 ม.ค. หายไปจริงๆ
            target_date = "2023-01-02"
            times = pd.to_datetime(ds_out.time.values)
            time_strs = [t.strftime('%Y-%m-%d') for t in times]
            self.assertIn(target_date, time_strs, "Gap date should be filled")
            
            val_tmax = ds_out.sel(time=target_date)['tmax'].values
            val_pr  = ds_out.sel(time=target_date)['pr'].values
            
            self.assertTrue(np.isnan(val_tmax).all(), f"tmax at {target_date} should be NaN")
            self.assertTrue(np.isnan(val_pr).all(),  f"pr at {target_date} should be NaN")

        finally:
            ds_out.close()

    def test_merge_attribute_mode_misalignment(self):
        """
        Test Attribute Merge when files have completely different time ranges.
        Scenario:
          - File 1 (tmax): Jan 2023 (31 days)
          - File 2 (pr):  Jan 2024 (31 days)
        Expectation:
          - Result has both years.
          - tmax is NaN in 2024.
          - pr is NaN in 2023.
        """
        import numpy as np
        
        # 1. สร้างไฟล์คนละปี
        path1 = self.create_dummy_nc("tmax_2023.nc", "tmax", "2023-01-01", 31, value_offset=10.0)
        path2 = self.create_dummy_nc("pr_2024.nc", "pr", "2024-01-01", 31, value_offset=20.0)

        # 2. รวมไฟล์
        success, result, errors = merge_attribute_mode([path1, path2], self.output_dir)
        self.assertTrue(success, f"Merge failed: {errors}")
        ds= xr.open_dataset(result['path'])

        # --- ตรวจสอบผลลัพธ์ ---

        # *สำคัญ*
        # ถ้าคุณใช้ `standardize_time_axis` (Gap Filling) ที่เราคุยกันก่อนหน้า
        # จำนวนวันจะเป็น: 31 (Jan 23) + 334 (Gap ก.พ.-ธ.ค. 23) + 31 (Jan 24) = 396 วัน
        # แต่ถ้ายังไม่ใส่ Gap Filling จำนวนวันจะเป็น 31 + 31 = 62 วัน
        # (ในที่นี้สมมติว่าเช็คแค่หัวท้ายก่อน)
        
        self.assertIn("2023-01-01", ds.time.dt.strftime("%Y-%m-%d"))
        self.assertIn("2024-01-01", ds.time.dt.strftime("%Y-%m-%d"))

        # 3. เช็คค่าข้ามปี (Cross-check)
        
        # ปี 2023: มี tmax แต่ไม่มี pr
        tmax_2023 = ds['tmax'].sel(time="2023-01-01", method="nearest").values
        pr_2023 = ds['pr'].sel(time="2023-01-01", method="nearest").values
        
        self.assertFalse(np.isnan(tmax_2023).any(), "tmax 2023 should exist")
        self.assertTrue(np.isnan(pr_2023).all(), "pr 2023 should be NaN (it only exists in 2024)")

        # ปี 2024: มี pr แต่ไม่มี tmax
        tmax_2024 = ds['tmax'].sel(time="2024-01-01", method="nearest").values
        pr_2024 = ds['pr'].sel(time="2024-01-01", method="nearest").values

        self.assertTrue(np.isnan(tmax_2024).all(), "tmax 2024 should be NaN (it only exists in 2023)")
        self.assertFalse(np.isnan(pr_2024).any(), "pr 2024 should exist")

        ds.close()

    def test_merge_time_mode_basic(self):
        """
        Test concatenating files along time dimension.
        """
        # Prepare: Day 1-2 and Day 3-4
        path1 = self.create_dummy_nc("t1.nc", "tmax", "2023-01-01", 2) # Jan 1, 2
        path2 = self.create_dummy_nc("t2.nc", "tmax", "2023-01-03", 2) # Jan 3, 4
        
        # Act
        success, result, errors = merge_time_mode([path1, path2], self.output_dir)
        
        # Assert
        self.assertTrue(success)
        ds_res = xr.open_dataset(result['path']) # changed from result['dataset'] since it returns path now
        
        # Should be 4 days total
        self.assertEqual(ds_res.sizes['time'], 4)
        # Verify SKIP_VARS removed
        self.assertNotIn("height", ds_res.data_vars)
        ds_res.close()

    def test_merge_time_mode_cross_year(self):
        """
        Test cross-year merging (Crucial for climate data).
        """
        # Prepare: End of 2023 and Start of 2024
        path1 = self.create_dummy_nc("2023.nc", "tmax", "2023-12-30", 2) # Dec 30, 31
        path2 = self.create_dummy_nc("2024.nc", "tmax", "2024-01-01", 2) # Jan 01, 02
        
        # Act
        success, result, errors = merge_time_mode([path1, path2], self.output_dir)
        
        # Assert
        self.assertTrue(success)
        ds = xr.open_dataset(result['path'])
        
        # Check continuity
        times = pd.to_datetime(ds.time.values)
        self.assertEqual(len(times), 4)
        self.assertEqual(times[0].year, 2023)
        self.assertEqual(times[-1].year, 2024)
        ds.close()

    def test_merge_time_mode_unordered_input(self):
        """
        Test if function correctly sorts unsorted file inputs.
        """
        # Prepare
        path1 = self.create_dummy_nc("jan1.nc", "tmax", "2023-01-01", 1)
        path2 = self.create_dummy_nc("jan2.nc", "tmax", "2023-01-02", 1)
        path3 = self.create_dummy_nc("jan3.nc", "tmax", "2023-01-03", 1)
        
        # Act: Pass in wrong order [3, 1, 2]
        success, result, errors = merge_time_mode([path3, path1, path2], self.output_dir)
        
        # Assert
        self.assertTrue(success)
        ds = xr.open_dataset(result['path'])
        
        # Check if time is sorted
        times = pd.to_datetime(ds.time.values)
        self.assertTrue(times[0] < times[1] < times[2], "Time coordinate is not sorted!")
        ds.close()

    def test_merge_time_mode_with_gap(self):
        """
        Test merging files with a large time gap (e.g., missing year).
        Expectation: Merge success, time coordinate contains the gap, no data invention.
        """

        # Arrange
        # Prepare: File 1 (End of 2023)
        path1 = self.create_dummy_nc("gap_2023.nc", "tmax", "2023-12-31", 1)
        
        # Prepare: File 2 (Start of 2025) -> Skipped entire 2024
        path2 = self.create_dummy_nc("gap_2025.nc", "tmax", "2025-01-01", 1)
        
        ds = None # Init variable for cleanup safety

        try:
            # Act
            success, result, errors = merge_time_mode([path1, path2], self.output_dir)
            
            # Assert
            self.assertTrue(success, f"Merge with gap failed: {errors}")
            
            ds = xr.open_dataset(result['path'])
            
            # 1. จำนวนวันต้องรวมกันได้ถูกต้อง 
            # (1 วันปี 23 + 366 วันปี 24 + 1 วันปี 25 = 368 วัน)
            self.assertEqual(ds.sizes['time'], 368, f"Expected 368 days, got {ds.sizes['time']}")
            
            # 2. ตรวจสอบค่าเวลา
            times = pd.to_datetime(ds.time.values)
            
            # time[0] should be 2023-12-31
            self.assertEqual(times[0].year, 2023)
            self.assertEqual(times[0].month, 12)
            
            # time[-1] (ตัวสุดท้าย) should be 2025-01-01
            # หมายเหตุ: index 1 คือวันที่ 2 มกรา (ถ้า gap filled) 
            # ดังนั้นต้องเช็คตัวสุดท้าย (-1) หรือเช็ค Gap ตรงกลาง
            self.assertEqual(times[-1].year, 2025)
            self.assertEqual(times[-1].month, 1)
            
            # เช็คระยะห่างระหว่างตัวแรกกับตัวสุดท้าย
            time_diff = times[-1] - times[0]
            self.assertTrue(time_diff.days > 360, f"Gap should be large, but found {time_diff.days} days")

        finally:
            # Cleanup: การันตีการปิดไฟล์เสมอ
            if ds:
                ds.close()

    def test_merge_time_mode_missing_months(self):
        """
        Test merging files where entire months are missing within years.
        Scenario: 
          - File 1: Jan 2023 (31 days) -> Missing Feb-Dec 2023
          - File 2: Jan 2024 (31 days) -> Missing Feb-Dec 2024
        Expectation: 
          - Successfully merged.
          - Total time steps = 365 + 31 = 396.
        """
        # 1. เตรียมข้อมูลปี 2023 (มีแค่เดือนมกราคม)
        path1 = self.create_dummy_nc("2023_jan.nc", "tmax", "2023-01-01", 31)
        
        # 2. เตรียมข้อมูลปี 2024 (มีแค่เดือนมกราคม)
        path2 = self.create_dummy_nc("2024_jan.nc", "tmax", "2024-01-01", 31)
        
        # Act: รวมไฟล์
        success, result, errors = merge_time_mode([path1, path2], self.output_dir)
        
        # Assert: ตรวจสอบผลลัพธ์
        self.assertTrue(success, f"Merge failed: {errors}")
        ds = xr.open_dataset(result['path'])
        
        # 1. เช็คจำนวนวันรวม (ต้องได้ 62 วันเป๊ะ ไม่ใช่ 365+365)
        self.assertEqual(ds.sizes['time'], 396)
        
        # 2. เช็คความต่อเนื่องของข้อมูล (จุดเชื่อมต่อ)
        times = pd.to_datetime(ds.time.values)
        
        time_strs = [str(t)[:7] for t in times]
        self.assertIn("2023-06", time_strs) # ตอนนี้ต้องมีเดือน 6 แล้ว
        
        # ลองเช็คค่าของเดือน 6 ว่าเป็น NaN ไหม
        val_june = ds.sel(time="2023-06-01")['tmax'].values # , method="nearest"
        self.assertTrue(np.isnan(val_june).all(), "Filled gap should be NaN")
        
        ds.close()

    def test_xclim_full_year_gap(self):
        """
        Test how calculation behaves when data is missing.
        """
        ds = None
        out = None

        import xclim as xc 
        

        path1 = self.create_dummy_nc("pr2023.nc", "pr", "2023-01-01", 365, value_offset=10.0) 
        path2 = self.create_dummy_nc("pr2025.nc", "pr", "2025-01-01", 365, value_offset=10.0)
        
        try :
            success, result, _ = merge_time_mode([path1, path2], self.output_dir)
            ds = xr.open_dataset(result['path'])
            
            ds['pr'].attrs['units'] = 'mm/day' 

            out = xc.indicators.icclim.RX1day(ds.pr, freq='YS')
            # with xc.set_options(check_missing="pct", missing_options={"pct": {"tolerance": 0.1}}):
            #     out = xc.indicators.icclim.PRCPTOT(ds.pr, freq='YS').load()

            print("\nResult PRCPTOT with partial data:")
            print(out)

            val_2023 = out.sel(time="2023-01-01").values # , method="nearest"
            # เช็คว่าค่าทั้งหมดของปี 2023 ต้อง "ไม่เป็น NaN" (คือมีค่าทุกจุด)
            self.assertFalse(np.isnan(val_2023).any(), "2023 should have valid values everywhere")

            # 2024 ควรเป็น NaN ! 
            # เพราะข้อมูลหายไปเกิน 90% (มีแค่ 5 วัน) xclim ไม่ควรคำนวณออกมาเป็นตัวเลข
            val_2024 = out.sel(time="2024-01-01").values # , method="nearest"
            
            # ถ้า xclim ฉลาดพอ มันต้องคืนค่า NaN
            # เช็คว่าค่าทั้งหมดของปี 2024 ต้อง "เป็น NaN" (คือหายไปทั้งหมด)
            self.assertTrue(np.isnan(val_2024).all(), "2024 should be all NaN")
            # self.assertFalse(np.isnan(val_2024).any(), "2024 should have valid values everywhere")

            val_2025 = out.sel(time="2025-01-01").values # , method="nearest"
            self.assertFalse(np.isnan(val_2025).any(), "2025 should have valid values everywhere")
        
        finally:   
            if ds is not None:
                ds.close()
            
            if out is not None:
                out.close()

    def test_xclim_behavior_with_gap(self):
        """
        Test how calculation behaves when data is missing.
        """
        ds = None
        out = None

        import xclim as xc 
        
        path1 = self.create_dummy_nc("pr2023.nc", "pr", "2023-01-01", 365, value_offset=10.0) 
        path2 = self.create_dummy_nc("pr2024.nc", "pr", "2024-01-01", 5, value_offset=10.0)
        
        # รวมไฟล์
        try :
            success, result, _ = merge_time_mode([path1, path2], self.output_dir)
            ds = xr.open_dataset(result['path'])
            
            ds['pr'].attrs['units'] = 'mm/day' 

            out = xc.indicators.icclim.RX1day(ds.pr, freq='YS')
            # with xc.set_options(check_missing="pct", missing_options={"pct": {"tolerance": 0.1}}):
            #     out = xc.indicators.icclim.PRCPTOT(ds.pr, freq='YS').load()

            print("\nResult PRCPTOT with partial data:")
            print(out)

            val_2023 = out.sel(time="2023-01-01").values # , method="nearest"
            # เช็คว่าค่าทั้งหมดของปี 2023 ต้อง "ไม่เป็น NaN" (คือมีค่าทุกจุด)
            self.assertFalse(np.isnan(val_2023).any(), "2023 should have valid values everywhere")

            # 2024 ควรเป็น NaN ! 
            # เพราะข้อมูลหายไปเกิน 90% (มีแค่ 5 วัน) xclim ไม่ควรคำนวณออกมาเป็นตัวเลข
            val_2024 = out.sel(time="2024-01-01").values # , method="nearest"
            
            self.assertTrue(np.isnan(val_2024).all(), "2024 should be all NaN")
            # self.assertFalse(np.isnan(val_2024).any(), "2024 should have valid values everywhere")
        
        finally:   
            if ds is not None:
                ds.close()
            
            if out is not None:
                out.close()
                    
    def test_merge_mixed_mode_success(self):
        """
        Test mixed mode (Happy Path): 
        Multiple variables (tmax, pr), each variable consists of multiple time-split files.
        Scenario:
          - tmax: file1 (Jan 1-2), file2 (Jan 3-4) -> Total 4 days
          - pr:   file1 (Jan 1-2), file2 (Jan 3-4) -> Total 4 days
        """
        # Arrange
        # Group 1: Temperature (2 files, continuous time)
        t1 = self.create_dummy_nc("temp_p1.nc", "tmax", "2023-01-01", 2) # Jan 1, 2
        t2 = self.create_dummy_nc("temp_p2.nc", "tmax", "2023-01-03", 2) # Jan 3, 4
        
        # Group 2: Precipitation (2 files, continuous time)
        p1 = self.create_dummy_nc("precip_p1.nc", "pr", "2023-01-01", 2) # Jan 1, 2
        p2 = self.create_dummy_nc("precip_p2.nc", "pr", "2023-01-03", 2) # Jan 3, 4
        
        # Setup arguments for mixed mode
        # The 'paths' list usually comes from the uploaded files list
        all_paths = [t1, t2, p1, p2] 
        
        # Groups: indices mapping to all_paths
        groups = {
            "tmax": [0, 1], # indices for t1, t2
            "pr":   [2, 3]  # indices for p1, p2
        }
        
        metas = [] # Not used in logic directly but required by function signature
        
        # Act
        success, result, errors = merge_mixed_mode(
            paths=all_paths, 
            groups=groups, 
            metas=metas, 
            temp_paths=all_paths,
            merged_dir=self.output_dir
        )
        
        # Assert
        self.assertTrue(success, f"Mixed merge failed: {errors}")
        self.assertIsNotNone(result)
        
        # Verify output content
        with xr.open_dataset(result['path']) as ds_out:
            # Check variables existence
            self.assertIn("tmax", ds_out.data_vars)
            self.assertIn("pr", ds_out.data_vars)
            
            # Check dimensions
            # Should have concatenated time: Jan 1, 2, 3, 4 = 4 days
            self.assertEqual(ds_out.sizes['time'], 4) 
            
            # Verify time values
            times = ds_out.indexes['time'].astype(str)
            self.assertEqual(times[0], "2023-01-01")
            self.assertEqual(times[-1], "2023-01-04")

    def test_merge_mixed_mode_global_gap(self):
        """
        [CRITICAL] Test Global Gap Filling in Mixed Mode.
        Scenario:
            - File 1 (tmax): End of 2023 (2023-12-31)
            - File 2 (pr):   Start of 2025 (2025-01-01)
            - GAP: Entire year of 2024 is missing.
        Expectation:
            - The merged dataset MUST contain the gap (2024).
            - Variables in the gap must be filled with NaN.
        """
        import xarray as xr
        import numpy as np
        
        # ---------------------------------------------------------------------
        # 1. Arrange
        # ---------------------------------------------------------------------
        # tmax: 1 day (2023-12-31)
        path1 = self.create_dummy_nc("mixed_tmax_2023.nc", "tmax", "2023-12-31", 1, value_offset=10.0)
        # pr: 1 day (2025-01-01)
        path2 = self.create_dummy_nc("mixed_pr_2025.nc", "pr", "2025-01-01", 1, value_offset=20.0)
        
        paths = [path1, path2]
        
        # Mock metadata (usually comes from detect_mode)
        metas = [
            {"variables": ["tmax"], "time_start": "2023-12-31"},
            {"variables": ["pr"],   "time_start": "2025-01-01"}
        ]
        
        # Groups: map variable -> index in paths list
        groups = {
            "tmax": [0], # path1
            "pr":   [1]  # path2
        }

        # ---------------------------------------------------------------------
        # 2. Act
        # ---------------------------------------------------------------------
        success, result, errors = merge_mixed_mode(
            paths=paths, 
            groups=groups, 
            metas=metas, 
            temp_paths=paths,
            merged_dir=self.output_dir
        )

        # ---------------------------------------------------------------------
        # 3. Assert
        # ---------------------------------------------------------------------
        self.assertTrue(success, f"Mixed merge failed: {errors}")
        
        # Verify Global Gap Filling
        with xr.open_dataset(result['path']) as ds:
            # Calculate expected total days:
            # 2023: 1 day (Dec 31)
            # 2024: 366 days (Leap Year) <-- The Gap
            # 2025: 1 day (Jan 01)
            # Total = 368 days
            self.assertEqual(ds.sizes['time'], 368, 
                             f"Time axis mismatch. Gap filling might be missing. Got {ds.sizes['time']}")
            
            # Check values in the gap (e.g., mid-year 2024) -> Must be NaN
            val_tmax = ds.sel(time="2024-07-01")['tmax'].values
            val_pr   = ds.sel(time="2024-07-01")['pr'].values
            
            self.assertTrue(np.isnan(val_tmax).all(), "tmax in global gap should be NaN")
            self.assertTrue(np.isnan(val_pr).all(), "pr in global gap should be NaN")
            
            # Check original data validity (should NOT be NaN)
            val_tmax_orig = ds.sel(time="2023-12-31")['tmax'].values
            val_pr_orig   = ds.sel(time="2025-01-01")['pr'].values
            
            self.assertFalse(np.isnan(val_tmax_orig).any(), "Original tmax data should remain valid")
            self.assertFalse(np.isnan(val_pr_orig).any(), "Original pr data should remain valid")

    def test_merge_mixed_mode_internal_gap(self):
        """
        Test Mixed Mode with internal gaps inside specific variables.
        Scenario:
            - File 1 (tmax): Jan 1, Jan 3 (Missing Jan 2)
            - File 2 (pr):   Jan 1, Jan 2, Jan 3 (Complete)
        Expectation:
            - Result time axis has Jan 1, 2, 3.
            - tmax at Jan 2 is NaN (filled by internal merge logic).
            - pr at Jan 2 is Valid (from original file).
        """
        import xarray as xr
        import numpy as np

        # Arrange
        # Prepare tmax: Create 3 days, then physically remove Jan 2 to simulate gap
        path1 = self.create_dummy_nc("mixed_tmax_gap.nc", "tmax", "2023-01-01", 3, value_offset=10.0)
        
        # Open, drop Jan 2, and save back
        ds_to_modify = None
        with xr.open_dataset(path1) as ds_temp:
            ds_to_modify = ds_temp.drop_sel(time="2023-01-02")
            ds_to_modify.load() # Load into memory before saving
        
        ds_to_modify.to_netcdf(path1) # Overwrite file
        ds_to_modify.close()
            
        # Prepare pr: 3 days continuous (Jan 1, 2, 3)
        path2 = self.create_dummy_nc("mixed_pr_full.nc", "pr", "2023-01-01", 3, value_offset=20.0)
        
        paths = [path1, path2]
        groups = {"tmax": [0], "pr": [1]}
        metas = [{}, {}] # Dummy metas

        # Act
        success, result, errors = merge_mixed_mode(
            paths=paths, 
            groups=groups, 
            metas=metas, 
            temp_paths=paths,
            merged_dir=self.output_dir
        )

        # Assert
        self.assertTrue(success, f"Merge failed: {errors}")

        with xr.open_dataset(result['path']) as ds:
            # Must cover the union of all times (Jan 1, 2, 3)
            self.assertEqual(ds.sizes['time'], 3)
            
            target_date = "2023-01-02"
            
            val_tmax = ds.sel(time=target_date)['tmax'].values
            val_pr   = ds.sel(time=target_date)['pr'].values

            # CHECK 1: tmax should be NaN (because it was missing in file 1)
            self.assertTrue(np.isnan(val_tmax).all(), f"tmax at {target_date} should be NaN due to internal gap")

            # CHECK 2: pr should be valid (because it existed in file 2)
            # Use ~np.isnan().any() to ensure data is present
            self.assertFalse(np.isnan(val_pr).any(), f"pr at {target_date} should be valid (Not NaN)")
    
    def test_error_handling_invalid_file(self):
        """
        Test robustness against missing or invalid files.
        """
        # Act
        fake_path = os.path.join(self.test_dir, "non_existent.nc")
        success, result, errors = merge_attribute_mode([fake_path], self.output_dir)
        
        # Assert
        self.assertFalse(success)
        self.assertIsNone(result)
        self.assertTrue(len(errors) > 0)
        # Check error code that file cannot be opened (Failed to open)
        self.assertIn("Failed to open", errors[0])
        # Check more to make sure the file isn't found
        self.assertIn("No such file or directory", errors[0])
    
if __name__ == '__main__':
    unittest.main()