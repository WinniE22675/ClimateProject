// src/pages/UploadDatasetPage.jsx
import React from 'react';
import { Link } from "react-router-dom";
import DatasetManager from '../components/DatasetManager';

export default function UploadDatasetPage() {
  return (
    <div className="container py-1">
      <div className="d-flex align-items-center justify-content-between mb-3">
        <h2 className="h3 fw-bold mb-0">Upload Datasets</h2>
      </div>
      <p className="text-muted mb-4">
        Upload raw NetCDF files to a slot, then select the area/time to process
        for the Climate Risk Map.
      </p>
      
      {/* Main Manager Component */}
      <DatasetManager />
    </div>
  );
}