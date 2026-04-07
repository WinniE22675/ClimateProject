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
    // add slot_id into formData or use for path parameter 
    // Array.from(files).forEach((f) => formData.append("files", f));

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
      // const res = await fetch(`http://localhost:8000/api/datasets/${slotId}/upload`, {
      //   method: "POST",
      //   body: formData,
      // });
      // It handles the formData automatically behind the scenes
      // const res = await datasetAPI.uploadFiles(slotId, formData);
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
    // Converted to Bootstrap Input Group for a seamless, attached button look
    <div className="input-group input-group-sm shadow-sm">
      <input
        type="file"
        id="ncFileInput"
        ref={fileInputRef} // ADDED ref
        multiple={!isShapefileMode} // Disable multiple for shapefile
        accept={isShapefileMode ? ".zip" : ".nc"} // Change accept based on mode
        onChange={(e) => setFiles(e.target.files)}
        className="form-control"
      />
      <button 
        onClick={handleUpload} 
        disabled={uploading || files.length === 0}
        className="btn btn-primary px-3"
      >
        {uploading ? (
          <><span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span></>
        ) : (
          isShapefileMode ? "Upload Shapefile" : "Upload Raw" // Dynamic button text
        )}
      </button>
    </div>
  );
}