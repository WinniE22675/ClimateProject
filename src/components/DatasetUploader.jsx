// import { useState } from "react";
// import { uploadDataset } from "../api";

// export default function DatasetUploader({ onUploadSuccess }) {
//   const [file, setFile] = useState(null);
//   const [loading, setLoading] = useState(false);
//   const [error, setError] = useState("");

//   const handleFileChange = (event) => {
//     setFile(event.target.files[0]);
//   };

//   const handleUpload = async () => {
//     if (!file) {
//       setError("Please select a file to upload.");
//       return;
//     }

//     setLoading(true);
//     setError("");

//     try {
//       const result = await uploadDataset(file);
//       console.log("Upload successful:", result);
//       if (onUploadSuccess) {
//         onUploadSuccess(result); 
//       }
//     } catch (err) {
//       console.error(err);
//       setError("Upload failed. Please try again.");
//     } finally {
//       setLoading(false);
//     }
//   };

//   return (
//     <div className="dataset-uploader">
//       <input type="file" onChange={handleFileChange} />
//       <button onClick={handleUpload} disabled={loading}>
//         {loading ? "Uploading..." : "Upload Dataset"}
//       </button>
//       {error && <p style={{ color: "red" }}>{error}</p>}
//     </div>
//   );
// }




// import { useState } from "react";

// export default function DatasetUploader({ onPreview }) {
//   const [files, setFiles] = useState([]);
//   const [loading, setLoading] = useState(false);
//   const [error, setError] = useState("");

//   const handleUpload = async () => {
//     if (files.length === 0) {
//       setError("Please select at least one file.");
//       return;
//     }

//     setLoading(true);
//     setError("");

//     const formData = new FormData();
//     Array.from(files).forEach((f) => formData.append("files", f));
//     // Array.from(files).forEach((f) => formData.append("file", f));
//     console.log(files);

//     try {
//       const res = await fetch("http://localhost:8000/api/preview_merge", {
//         method: "POST",
//         body: formData,
//       });

//       const data = await res.json();
//       console.log("RESPONSE FROM BACKEND:", data);

//       if (onPreview) onPreview(data); 
//     } catch (err) {
//       console.error(err);
//       setError("Upload failed.");
//     } finally {
//       setLoading(false);
//     }
//   };

//   return (
//     <div>
//       <input
//         type="file"
//         accept=".nc,.grib,.csv" // .grib,.csv can't use with Backend Now : 18/11/2025
//         multiple
//         onChange={(e) => setFiles(Array.from(e.target.files))}
//       />

//       <button onClick={handleUpload} disabled={loading}>
//         {loading ? "Uploading..." : "Upload for Preview"}
//       </button>

//       {error && <p style={{ color: "red" }}>{error}</p>}
//     </div>
//   );
// }

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
    <div className="flex gap-2 items-center">
      <input
        type="file"
        multiple
        accept=".nc"
        onChange={(e) => setFiles(e.target.files)}
        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
      />
      <button 
        onClick={handleUpload} 
        disabled={uploading || files.length === 0}
        className="bg-blue-600 text-white px-4 py-2 rounded disabled:bg-gray-400"
      >
        {uploading ? "Uploading..." : "Upload Raw"}
      </button>
    </div>
  );
}