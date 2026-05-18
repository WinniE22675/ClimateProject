// src/pages/UploadDatasetPage.jsx
import React from 'react';
import { Link } from "react-router-dom";
import DatasetManager from '../components/DatasetManager';

export default function UploadDatasetPage() {
  return (
    <div className="container mx-auto px-4 py-2 mt-4">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-2xl font-bold m-0 text-gray-900">Upload Datasets</h2>
      </div>
      <p className="text-gray-500 mb-6">
        Upload raw NetCDF files to a slot, then select the area/time to process
        for the Climate Risk Map.
      </p>
      
      {/* Main Manager Component */}
      <DatasetManager />
    </div>
  );
}