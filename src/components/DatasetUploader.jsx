// src/components/DatasetUploader.jsx
import { useState } from "react";

export default function DatasetUploader({ slotId, onUploadSuccess }) {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);

    const formData = new FormData();
    // เพิ่ม slot_id ลงไปใน formData หรือใช้เป็น path parameter ก็ได้
    Array.from(files).forEach((f) => formData.append("files", f));

    try {
      // ส่งไป Route ใหม่
      const res = await fetch(`http://localhost:8000/api/datasets/${slotId}/upload`, {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        setFiles([]); // Clear selection
        if (onUploadSuccess) onUploadSuccess();
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
        multiple
        accept=".nc"
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
          "Upload Raw"
        )}
      </button>
    </div>
  );
}