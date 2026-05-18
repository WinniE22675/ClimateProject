// src/components/DatasetUploader.jsx
import { useState, useRef } from "react";
import { datasetAPI } from '../services/api';

// File size limits ---
const MAX_PAYLOAD_SIZE = 1 * 1024 * 1024 * 1024; // 1 GB limit per NetCDF upload request
const MAX_SHAPEFILE_SIZE = 1 * 1024 * 1024 * 1024;    // 1 GB limit for Shapefile (.zip)

export default function DatasetUploader({ slotId, isShapefileMode, datasetName, onUploadSuccess }) {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null); // reference to reset input later

  const handleUpload = async () => {
    if (files.length === 0) return;

    // File size validation before proceeding ---
    if (isShapefileMode) {
      // Validate Shapefile size
      if (files[0].size > MAX_SHAPEFILE_SIZE) {
        alert("Shapefile exceeds the 500 MB limit. Please simplify your geometry.");
        return; // Stop execution
      }
    } else {
      // Validate NetCDF payload size
      const totalPayloadSize = Array.from(files).reduce((sum, file) => sum + file.size, 0);
      if (totalPayloadSize > MAX_PAYLOAD_SIZE) {
        alert("The selected files exceed the 1 GB limit per upload. Please select fewer files and try uploading in batches.");
        return; // Stop execution
      }
    }

    setUploading(true);

    const formData = new FormData();

    if (isShapefileMode) {
      // Shapefile Mode: Server expects a single file named "file", and an optional "custom_name"
      formData.append("file", files[0]); 
      
      // If user typed a name, send it along!
      if (datasetName && datasetName.trim()) {
        formData.append("custom_name", datasetName.trim());
      }
    } else {
      // NetCDF Mode: Server expects an array of files named "files"
      Array.from(files).forEach((f) => formData.append("files", f));
    }

    try {
      const res = isShapefileMode 
        ? await datasetAPI.uploadShapefile(formData) 
        : await datasetAPI.uploadFiles(slotId, formData);
      if (res.ok) {
        setFiles([]); // Clear selection
        if (fileInputRef.current) fileInputRef.current.value = ""; // RESET UI INPUT
        if (onUploadSuccess) onUploadSuccess();
        // alert("Upload Successful!");
      } else {
        alert("Upload Failed");
      }
    } catch (err) {
      console.error(err);
      alert("Error uploading");
    } finally {
      setUploading(false);
    }
  };

  return (
    // Simulated Bootstrap Input Group using Flexbox
    <div className="flex shadow-sm text-sm rounded-md overflow-hidden border border-gray-300">
      <input
        type="file"
        id="ncFileInput"
        ref={fileInputRef} // ADDED ref
        multiple={!isShapefileMode} // Disable multiple for shapefile
        accept={isShapefileMode ? ".zip,.geojson" : ".nc"} // Change accept based on mode
        onChange={(e) => setFiles(e.target.files)}
        className="block w-full text-sm text-gray-500 bg-white cursor-pointer focus:outline-none file:cursor-pointer file:mr-3 file:py-1.5 file:px-4 file:rounded-none file:border-0 file:border-r file:border-gray-300 file:text-sm file:font-medium file:bg-gray-50 file:text-gray-700 hover:file:bg-gray-100"
      />
      <button 
        onClick={handleUpload} 
        disabled={uploading || files.length === 0}
        className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-1.5 font-medium transition-colors disabled:opacity-60 disabled:cursor-not-allowed whitespace-nowrap flex items-center justify-center"
      >
        {uploading ? (
          // Tailwind custom SVG Spinner
          <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        ) : (
          isShapefileMode ? "Upload Shapefile" : "Upload Raw" // Dynamic button text
        )}
      </button>
    </div>
  );
}