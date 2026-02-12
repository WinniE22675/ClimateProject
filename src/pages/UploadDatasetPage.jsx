// import { useState } from "react";
// import DatasetUploader from "../components/DatasetUploader";
// import DatasetPreview from "../components/DatasetPreview";

// export default function UploadDatasetPage() {
//   const [preview, setPreview] = useState(null);

//   return (
//     <div className="container mt-4">
//       <h2 className="mb-4">Upload New Climate Dataset</h2>

//       {/* Step 1: Upload */}
//       <DatasetUploader
//         onPreview={(data) => {
//           console.log("PREVIEW CALLBACK:", data);
//           setPreview(data.metadata);
//         }}
//       />

//       {/* Step 2: Preview */}
//       {preview && (
//         <div className="mt-4">
//           <DatasetPreview metadata={preview} />
//         </div>
//       )}
//     </div>
//   );
// }





// import { useState } from "react";
// import DatasetUploader from "../components/DatasetUploader";
// import DatasetPreview from "../components/DatasetPreview";
// import RawTimeseriesViewer from "../components/RawTimeseriesViewer";
// import RawMapViewer from "../components/RawMapViewer";

// export default function UploadDatasetPage() {
//   const [metadata, setMetadata] = useState(null);
//   const [selectedVar, setSelectedVar] = useState(null);
//   const [selectedFile, setSelectedFile] = useState(0);

//   return (
//     <div className="container mt-4">
//       <h2 className="mb-4">Upload New Climate Dataset</h2>

//       {/* Step 1 — Upload */}
//       <DatasetUploader
//         onPreview={(data) => {
//           console.log("PREVIEW CALLBACK:", data);
//           setMetadata(data.metadata);
//         }}
//       />

//       {/* Step 2 — Preview Metadata */}
//       {metadata && (
//         <>
//           <DatasetPreview
//             metadata={metadata}
//             selectedFile={selectedFile}
//             onSelectFile={setSelectedFile}
//           />

//           {/* Step 3 — Select Variable */}
//           <div className="mt-3">
//             <label>Select Variable:</label>
//             <select
//               className="form-select w-25"
//               value={selectedVar ?? ""}
//               onChange={(e) => setSelectedVar(e.target.value)}
//             >
//               <option value="">-- Select --</option>
//               {metadata[selectedFile].variables.map((v) => (
//                 <option key={v} value={v}>
//                   {v}
//                 </option>
//               ))}
//             </select>
//           </div>

//           {/* Step 4 — Raw Viewers */}
//           {selectedVar && (
//             <div className="row mt-4">
//               <div className="col-12 col-lg-6">
//                 <RawTimeseriesViewer
//                   fileIndex={selectedFile}
//                   variable={selectedVar}
//                 />
//               </div>

//               <div className="col-12 col-lg-6">
//                 <RawMapViewer fileIndex={selectedFile} variable={selectedVar} />
//               </div>
//             </div>
//           )}
//         </>
//       )}
//     </div>
//   );
// }


// import { useState, useEffect } from "react";
// import DatasetUploader from "../components/DatasetUploader";
// import DatasetPreview from "../components/DatasetPreview";
// import RawTimeseriesViewer from "../components/RawTimeseriesViewer";
// import RawMapViewer from "../components/RawMapViewer";
// import IndicesSelector from "../components/IndicesSelector";

// export default function UploadDatasetPage() {
//   const [metadata, setMetadata] = useState(null);
//   const [selectedVar, setSelectedVar] = useState(null);
//   const [selectedFile, setSelectedFile] = useState(0);
//   const [mergedInfo, setMergedInfo] = useState(null);

//   useEffect(() => {
//     setSelectedVar("");
//   }, [selectedFile]);

//   return (
//     <div className="container mt-4 pb-20">
//       <h2 className="mb-4">Upload New Dataset</h2>

//       <div className="text-muted mb-2">
//         Only .nc (NetCDF) files are supported. (Limit 200 MB)
//       </div>

//       {/* Step 1 — Upload */}
//       <DatasetUploader
//         onPreview={(data) => {
//           console.log("PREVIEW CALLBACK:", data);
//           setMetadata(data.metadata);
//           setMergedInfo({
//             metadata: data.preview.metadata,
//             merged_path: data.merged_path,
//           });
//         }}
//       />

//       {/* Step 2 — Preview Metadata */}
//       {metadata && (
//         <>
//           <div className="row mt-4">
//             {/* LEFT PANEL — Metadata Preview */}
//             <div className="col-12 col-lg-6">
//               <DatasetPreview
//                 metadata={metadata}
//                 selectedFile={selectedFile}
//                 onSelectFile={setSelectedFile}
//               />
//             </div>

//             {/* RIGHT PANEL — Index Selection */}
//             <div className="col-12 col-lg-6">
//               {mergedInfo && (
//                 <IndicesSelector
//                   availableVars={mergedInfo.metadata.variables}
//                   onCalculate={async (selected) => {
//                     console.log("SENDING TO BACKEND:", {
//                       selected_indices: selected,
//                       dataset_name: mergedInfo.merged_path,
//                     });
//                     const res = await fetch(
//                       "http://localhost:8000/api/indices/calc",
//                       {
//                         method: "POST",
//                         headers: { "Content-Type": "application/json" },
//                         body: JSON.stringify({
//                           selected_indices: selected,
//                           dataset_name: mergedInfo.merged_path,
//                         }),
//                       }
//                     );

//                     const data = await res.json();
//                     console.log("Indices Results:", data);
//                   }}
//                 />
//               )}
//             </div>
//           </div>

//           {/* Step 3 — Select Variable */}
//           <div className="mt-3">
//             <label>Select Variable:</label>
//             <select
//               className="form-select w-25"
//               value={selectedVar ?? ""}
//               onChange={(e) => setSelectedVar(e.target.value)}
//             >
//               <option value="">-- Select --</option>
//               {metadata[selectedFile].variables.map((v) => (
//                 <option key={v} value={v}>
//                   {v}
//                 </option>
//               ))}
//             </select>
//           </div>

//           {/* Step 4 — Raw Viewers */}
//           {selectedVar && (
//             <div className="row mt-4">
//               <div className="col-12 col-lg-6">
//                 <RawTimeseriesViewer
//                   fileIndex={selectedFile}
//                   variable={selectedVar}
//                 />
//               </div>

//               <div className="col-12 col-lg-6">
//                 <RawMapViewer fileIndex={selectedFile} variable={selectedVar} />
//               </div>
//             </div>
//           )}
//         </>
//       )}
//     </div>
//   );
// }

// src/pages/UploadDatasetPage.jsx
import React from 'react';
import { Link } from "react-router-dom";
import DatasetManager from '../components/DatasetManager';

export default function UploadDatasetPage() {
  return (
    <div className="container mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">Upload Datasets</h1>
      </div>
      <p className="mb-4 text-gray-600">
        Upload raw NetCDF files to a slot, then select the area/time to process
        for the Climate Risk Map.
      </p>
      <DatasetManager />
    </div>
  );
}