// src/components/DatasetManager.jsx
import React, { useState, useEffect } from "react";
import DatasetUploader from "./DatasetUploader";
import { useNavigate } from "react-router-dom";
import { apiFetch, datasetAPI } from '../services/api';

// const DATASET_SLOTS = [1, 2, 3, 4];
const DATASET_SLOTS = [
  { id: 1, label: "Preset 1" },
  { id: 2, label: "Preset 2" },
  { id: 3, label: "Preset 3" },
  { id: 4, label: "Preset 4" },
  { id: 5, label: "Shapefile" } // Slot 5 สำหรับ Shapefile
];

export default function DatasetManager() {
  const [activeTab, setActiveTab] = useState("presets"); // "presets" | "shapefile"
  const [activeSlot, setActiveSlot] = useState(1);
  const [fileList, setFileList] = useState([]);
  const [scope, setScope] = useState({
    startYear: "",//1960,
    endYear: "",//2024,
    minLat: "",//4, //-15,
    maxLat: "",//22, //30,
    minLon: "",//95, //90,
    maxLon: "",//107 //145,
  });
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate(); // Add hook

  const [datasetName, setDatasetName] = useState("");

  const isShapefileMode = activeSlot === 5;

  // Fetch file list when slot changes
  useEffect(() => {
    fetchFiles(activeSlot);
  }, [activeSlot]);

  const fetchFiles = async (slotId) => {
    try {
      // const res = await fetch(
      //   `http://localhost:8000/api/datasets/${slotId}/files`
      // );
      // const res = await apiFetch(`/datasets/${slotId}/files`);
      const endpoint = slotId === 5 ? `/shapefiles?user_only=true` : `/datasets/${slotId}/files`;
      const res = await apiFetch(endpoint);

      if (res.ok) {
        const data = await res.json();
        if (slotId === 5) {
            // const sfList = (data.shapefiles || []).map(name => ({ name }));
            setFileList(data.shapefiles || []);
            // setFileList(sfList);
        } else {
            setFileList(data.files || []); // Expecting { files: [{name:Str, year:Int}, ...] }
        }
        // setFileList(data.files || []); // Expecting { files: [{name:Str, year:Int}, ...] }
      } else {
        setFileList([]);
      }
    } catch (err) {
      console.error("Failed to fetch files", err);
    }
  };

  const handleDelete = async (filename) => {
    if (!window.confirm(`Delete ${filename}?`)) return;

    try {
      // const res = await fetch(
      //   `http://localhost:8000/api/datasets/${activeSlot}/files/${filename}`,
      //   {
      //     method: "DELETE",
      //   }
      // );
      const endpoint = isShapefileMode 
        ? `/shapefiles/${filename}` 
        : `/datasets/${activeSlot}/files/${filename}`;
      const res = await apiFetch(endpoint, {
        method: "DELETE",
      });
      if (res.ok) {
        fetchFiles(activeSlot); // Refresh list
      } else {
        alert("Failed to delete");
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleProcessSelection = async () => {
    // Prevent processing without a dataset name
    if (!datasetName.trim()) {
      alert("Please enter a Dataset Name.");
      return;
    }

    setLoading(true);
    if (isShapefileMode) {
      alert("Shapefile cannot be processed here. Please select a Data Preset (1-4) and apply the Shapefile in the next step.");
      return;
    }
    try {
      // send Scope to Backend manage file follow Metadata
      // const res = await fetch(
      //   `http://localhost:8000/api/datasets/process_selection`, 
      //   {
      //     method: "POST",
      //     headers: { "Content-Type": "application/json" },
      //     body: JSON.stringify({
      //       slot_id: activeSlot,
      //       dataset_name: datasetName,
      //       scope: scope,
      //     }),
      //   }
      // );

      // 2. Clean the scope payload: Convert empty strings "" to null
      const cleanScope = {
        startYear: scope.startYear === "" ? null : Number(scope.startYear),
        endYear: scope.endYear === "" ? null : Number(scope.endYear),
        minLat: scope.minLat === "" || scope.minLat === "-" ? null : Number(scope.minLat),
        maxLat: scope.maxLat === "" || scope.maxLat === "-" ? null : Number(scope.maxLat),
        minLon: scope.minLon === "" || scope.minLon === "-" ? null : Number(scope.minLon),
        maxLon: scope.maxLon === "" || scope.maxLon === "-" ? null : Number(scope.maxLon),
      };

      const res = await datasetAPI.processSelection({
        slot_id: activeSlot,
        dataset_name: datasetName.trim(), // Remove accidental spaces
        scope: cleanScope, //scope,
      });
      if (res.ok) {
        // const result = await res.json();
        // alert(result.message || "Data processed successfully!");
        // TODO: Navigate to Result Page or Show success
        navigate("/process", { state: { datasetName } }); //slotId: activeSlot
      }
      else {
        const errorData = await res.json();
        alert(`Error: ${errorData.detail || "Failed to start processing."}`);
        // alert("Failed to start processing.");
        // const errorData = await res.json();
        
        // if (Array.isArray(errorData.detail)) {
        //   const errorMessages = errorData.detail
        //     .map(err => `- ${err.loc[err.loc.length - 1]}: ${err.msg}`)
        //     .join('\n');
        //   alert(`Data Validation Error:\n${errorMessages}`);
        // } else {
        //   alert(`Error: ${errorData.detail || "Failed to start processing."}`);
        // }
      }
    } catch (err) {
      console.error(err);
      alert("Error processing data");
    } finally {
      setLoading(false);
    }
  };

  // return (
  //   <div className="card shadow-sm border-0">
  //     <div className="card-body p-3">
        
  //       {/* 1. Slot Selector (5 Tabs) */}
  //       <div className="mb-3">
  //         <label className="form-label fw-bold small text-muted mb-2">Select Target</label>
  //         <div className="btn-group d-flex w-100 shadow-sm" role="group">
  //           {DATASET_SLOTS.map((slot) => (
  //             <button
  //               key={slot.id}
  //               onClick={() => {
  //                 setActiveSlot(slot.id);
  //                 setDatasetName(""); 
  //               }}
  //               className={`btn py-2 ${
  //                 activeSlot === slot.id ? "btn-primary shadow-sm" : "btn-outline-secondary"
  //               }`}
  //             >
  //               {slot.label}
  //             </button>
  //           ))}
  //         </div>
  //       </div>

  //       {isShapefileMode && (
  //          <div className="alert alert-info py-2 mb-3 shadow-sm border-0 small">
  //            <i className="bi bi-info-circle me-2"></i>
  //            Upload a single <strong>.zip</strong> file containing all shapefile components (.shp, .shx, .dbf, ...).
  //          </div>
  //       )}

  //       <div className="row mb-3 align-items-end g-3">
  //         <div className="col-12 col-md-5">
  //           {/* FIX: Show input field for both modes, just change the label/placeholder */}
  //           <label className="form-label fw-bold small mb-1">
  //             {isShapefileMode ? 'Shapefile Name' : 'Dataset Name'}
  //           </label>
  //           <input
  //             type="text"
  //             value={datasetName}
  //             onChange={(e) => setDatasetName(e.target.value)}
  //             className="form-control form-control-sm"
  //             placeholder={isShapefileMode ? "e.g. My_Custom_Area" : "e.g. ERA5_Thailand_1960_2020"}
  //           />
  //         </div>
  //         <div className="col-12 col-md-7">
  //           <label className="form-label fw-bold small mb-1 text-primary">
  //             Upload to {isShapefileMode ? 'Shapefile (zip)' : `Preset ${activeSlot}`}
  //           </label>
  //           <DatasetUploader
  //             slotId={activeSlot}
  //             isShapefileMode={isShapefileMode} 
  //             datasetName={datasetName} 
  //             onUploadSuccess={() => fetchFiles(activeSlot)}
  //           />
  //         </div>
  //       </div>

  //           {/* Scope Selection */}
  //           {!isShapefileMode && (
  //           <div className="card bg-light border-0 mb-3">
  //             <div className="card-body p-3">
  //               <div className="row g-3">
  //                 {/* Time Range */}
  //                 <div className="col-12 col-md-4">
  //                   <label className="form-label small fw-bold text-muted mb-1">Time Range (Year)</label>
  //                   <div className="input-group input-group-sm">
  //                     <input
  //                       type="number"
  //                       value={scope.startYear}
  //                       // onChange={(e) => setScope({ ...scope, startYear: Number(e.target.value) })}
  //                       onChange={(e) => {
  //                         const val = e.target.value;
  //                         setScope({ ...scope, startYear: val === "" ? "" : Number(val) });
  //                       }}
  //                       className="form-control text-center"
  //                       placeholder="start"
  //                     />
  //                     <span className="input-group-text bg-white">-</span>
  //                     <input
  //                       type="number"
  //                       value={scope.endYear}
  //                       // onChange={(e) => setScope({ ...scope, endYear: Number(e.target.value) })}
  //                       onChange={(e) => {
  //                         const val = e.target.value;
  //                         setScope({ ...scope, endYear: val === "" ? "" : Number(val) });
  //                       }}
  //                       className="form-control text-center"
  //                       placeholder="end"
  //                     />
  //                   </div>
  //                 </div>

  //                 {/* Latitude */}
  //                 <div className="col-12 col-md-4">
  //                   <label className="form-label small fw-bold text-muted mb-1">Latitude (Min - Max)</label>
  //                   <div className="input-group input-group-sm">
  //                     <input
  //                       type="number"
  //                       min="-90" max="90"
  //                       value={scope.minLat}
  //                       onChange={(e) => {
  //                         const val = e.target.value;
  //                         setScope({ ...scope, minLat: val === "" || val === "-" ? val : Number(val) });
  //                       }}
  //                       className="form-control text-center"
  //                       placeholder="min"
  //                     />
  //                     <span className="input-group-text bg-white">-</span>
  //                     <input
  //                       type="number"
  //                       min="-90" max="90"
  //                       value={scope.maxLat}
  //                       onChange={(e) => {
  //                         const val = e.target.value;
  //                         setScope({ ...scope, maxLat: val === "" || val === "-" ? val : Number(val) });
  //                       }}
  //                       className="form-control text-center"
  //                       placeholder="max"
  //                     />
  //                   </div>
  //                 </div>

  //                 {/* Longitude */}
  //                 <div className="col-12 col-md-4">
  //                   <label className="form-label small fw-bold text-muted mb-1">Longitude (Min - Max)</label>
  //                   <div className="input-group input-group-sm">
  //                     <input
  //                       type="number"
  //                       min="-180" max="180"
  //                       value={scope.minLon}
  //                       onChange={(e) => {
  //                         const val = e.target.value;
  //                         setScope({ ...scope, minLon: val === "" || val === "-" ? val : Number(val) });
  //                       }}
  //                       className="form-control text-center"
  //                       placeholder="min"
  //                     />
  //                     <span className="input-group-text bg-white">-</span>
  //                     <input
  //                       type="number"
  //                       min="-180" max="180"
  //                       value={scope.maxLon}
  //                       onChange={(e) => {
  //                         const val = e.target.value;
  //                         setScope({ ...scope, maxLon: val === "" || val === "-" ? val : Number(val) });
  //                       }}
  //                       className="form-control text-center"
  //                       placeholder="max"
  //                     />
  //                   </div>
  //                 </div>
  //               </div>
  //             </div>
  //           </div>
  //           )}

  //           {/* Action Button */}
  //           {!isShapefileMode && (
  //           <div className="text-center mb-4">
  //             <button
  //               onClick={handleProcessSelection}
  //               disabled={loading || fileList.length === 0}
  //               className="btn btn-sm btn-success px-5 fw-bold shadow-sm"
  //             >
  //               {loading ? (
  //                 <><span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Processing (Clipping)...</>
  //               ) : (
  //                 "Confirm & Clip Data"
  //               )}
  //             </button>
  //           </div>
  //       )}

  //       {/* File List Visualization */}
  //       <div>
  //         <h6 className="fw-bold mb-2">Uploaded {isShapefileMode ? 'Shapefiles' : 'Files'} <span className="badge bg-secondary">{fileList.length}</span></h6>
          
  //         <div className="list-group overflow-auto border rounded shadow-sm" style={{ maxHeight: "250px" }}>
  //           {fileList.length === 0 && (
  //             <div className="list-group-item text-center text-muted p-4 bg-light">
  //               No {isShapefileMode ? 'shapefiles' : 'files'} uploaded yet.
  //             </div>
  //           )}

  //           {fileList.map((file, idx) => (
  //             <div key={idx} className="list-group-item list-group-item-action d-flex justify-content-between align-items-center p-2">
  //               <span className="text-truncate small" style={{ maxWidth: "80%" }} title={file.name}>
  //                 {file.name}
  //               </span>
  //               <button
  //                 onClick={() => handleDelete(file.name)}
  //                 className="btn btn-sm btn-outline-danger py-0 px-2"
  //                 style={{ fontSize: "0.8rem" }}
  //               >
  //                 Delete
  //               </button>
  //             </div>
  //           ))}
  //         </div>
  //       </div>

  //     </div>
  //   </div>
  // );
  return (
    <div className="bg-white rounded-lg border border-gray-200">
      <div className="p-4">
        
        {/* 1. Slot Selector (5 Tabs) */}
        <div className="mb-4">
          <label className="block font-bold text-sm text-gray-500 mb-2">Select Target</label>
          <div className="flex w-full shadow-sm rounded-md overflow-hidden" role="group">
            {DATASET_SLOTS.map((slot) => (
              <button
                key={slot.id}
                onClick={() => {
                  setActiveSlot(slot.id);
                  setDatasetName(""); 
                }}
                className={`flex-1 py-2 text-sm font-medium transition-colors border-y border-r first:border-l first:rounded-l-md last:rounded-r-md border-gray-300 ${
                  activeSlot === slot.id 
                    ? "bg-blue-600 text-white border-blue-600 z-10 shadow-sm" 
                    : "bg-white text-gray-700 hover:bg-gray-50"
                }`}
              >
                {slot.label}
              </button>
            ))}
          </div>
        </div>

        {isShapefileMode && (
           <div className="bg-blue-50 text-blue-800 py-2 px-4 mb-4 rounded-md shadow-sm border-0 text-sm flex items-center">
             {/* Using an inline SVG icon to replace bootstrap-icons bi-info-circle */}
             <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
             </svg>
             <span>Upload a single <strong>.zip</strong> file containing all shapefile components (.shp, .shx, .dbf, ...).</span>
           </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-end mb-4">
          <div className="md:col-span-5">
            {/* FIX: Show input field for both modes, just change the label/placeholder */}
            <label className="block font-bold text-sm text-gray-700 mb-1">
              {isShapefileMode ? 'Shapefile Name' : 'Dataset Name'}
            </label>
            <input
              type="text"
              value={datasetName}
              onChange={(e) => setDatasetName(e.target.value)}
              className="block w-full text-sm border border-gray-300 rounded-md px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              placeholder={isShapefileMode ? "e.g. My_Custom_Area" : "e.g. ERA5_Thailand_1960_2020"}
            />
          </div>
          <div className="md:col-span-7">
            <label className="block font-bold text-sm text-blue-600 mb-1">
              Upload to {isShapefileMode ? 'Shapefile (zip)' : `Preset ${activeSlot}`}
            </label>
            <DatasetUploader
              slotId={activeSlot}
              isShapefileMode={isShapefileMode} 
              datasetName={datasetName} 
              onUploadSuccess={() => fetchFiles(activeSlot)}
            />
          </div>
        </div>

        {/* Scope Selection */}
        {!isShapefileMode && (
        <div className="bg-gray-50 border-0 rounded-lg mb-4">
          <div className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Time Range */}
              <div>
                <label className="block text-sm font-bold text-gray-500 mb-1">Time Range (Year)</label>
                <div className="flex border border-gray-300 rounded-md overflow-hidden bg-white text-sm">
                  <input
                    type="number"
                    value={scope.startYear}
                    onChange={(e) => {
                      const val = e.target.value;
                      setScope({ ...scope, startYear: val === "" ? "" : Number(val) });
                    }}
                    className="w-full text-center px-2 py-1.5 focus:outline-none"
                    placeholder="start"
                  />
                  <span className="flex items-center px-2 bg-white text-gray-500 border-x border-gray-300">-</span>
                  <input
                    type="number"
                    value={scope.endYear}
                    onChange={(e) => {
                      const val = e.target.value;
                      setScope({ ...scope, endYear: val === "" ? "" : Number(val) });
                    }}
                    className="w-full text-center px-2 py-1.5 focus:outline-none"
                    placeholder="end"
                  />
                </div>
              </div>

              {/* Latitude */}
              <div>
                <label className="block text-sm font-bold text-gray-500 mb-1">Latitude (Min - Max)</label>
                <div className="flex border border-gray-300 rounded-md overflow-hidden bg-white text-sm">
                  <input
                    type="number"
                    min="-90" max="90"
                    value={scope.minLat}
                    onChange={(e) => {
                      const val = e.target.value;
                      setScope({ ...scope, minLat: val === "" || val === "-" ? val : Number(val) });
                    }}
                    className="w-full text-center px-2 py-1.5 focus:outline-none"
                    placeholder="min"
                  />
                  <span className="flex items-center px-2 bg-white text-gray-500 border-x border-gray-300">-</span>
                  <input
                    type="number"
                    min="-90" max="90"
                    value={scope.maxLat}
                    onChange={(e) => {
                      const val = e.target.value;
                      setScope({ ...scope, maxLat: val === "" || val === "-" ? val : Number(val) });
                    }}
                    className="w-full text-center px-2 py-1.5 focus:outline-none"
                    placeholder="max"
                  />
                </div>
              </div>

              {/* Longitude */}
              <div>
                <label className="block text-sm font-bold text-gray-500 mb-1">Longitude (Min - Max)</label>
                <div className="flex border border-gray-300 rounded-md overflow-hidden bg-white text-sm">
                  <input
                    type="number"
                    min="-180" max="180"
                    value={scope.minLon}
                    onChange={(e) => {
                      const val = e.target.value;
                      setScope({ ...scope, minLon: val === "" || val === "-" ? val : Number(val) });
                    }}
                    className="w-full text-center px-2 py-1.5 focus:outline-none"
                    placeholder="min"
                  />
                  <span className="flex items-center px-2 bg-white text-gray-500 border-x border-gray-300">-</span>
                  <input
                    type="number"
                    min="-180" max="180"
                    value={scope.maxLon}
                    onChange={(e) => {
                      const val = e.target.value;
                      setScope({ ...scope, maxLon: val === "" || val === "-" ? val : Number(val) });
                    }}
                    className="w-full text-center px-2 py-1.5 focus:outline-none"
                    placeholder="max"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
        )}

        {/* Action Button */}
        {!isShapefileMode && (
        <div className="text-center mb-6">
          <button
            onClick={handleProcessSelection}
            disabled={loading || fileList.length === 0}
            className="bg-green-600 hover:bg-green-700 text-white text-sm font-bold py-2 px-10 rounded-md shadow-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed inline-flex items-center justify-center"
          >
            {loading ? (
              <>
                <svg className="animate-spin h-4 w-4 mr-2 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Processing (Clipping)...
              </>
            ) : (
              "Confirm & Clip Data"
            )}
          </button>
        </div>
        )}

        {/* File List Visualization */}
        <div>
          <h6 className="font-bold mb-2 text-gray-900">
            Uploaded {isShapefileMode ? 'Shapefiles' : 'Files'} 
            <span className="inline-block bg-gray-500 text-white text-xs px-2 py-0.5 rounded-full ml-2">{fileList.length}</span>
          </h6>
          
          <div className="flex flex-col border border-gray-200 rounded-md shadow-sm overflow-y-auto divide-y divide-gray-200" style={{ maxHeight: "250px" }}>
            {fileList.length === 0 && (
              <div className="text-center text-gray-500 p-6 bg-gray-50">
                No {isShapefileMode ? 'shapefiles' : 'files'} uploaded yet.
              </div>
            )}

            {fileList.map((file, idx) => (
              <div key={idx} className="flex justify-between items-center p-3 hover:bg-gray-50 bg-white">
                <span className="truncate text-sm text-gray-800" style={{ maxWidth: "80%" }} title={file.name}>
                  {file.name}
                </span>
                <button
                  onClick={() => handleDelete(file.name)}
                  className="border border-red-500 text-red-500 hover:bg-red-50 hover:text-red-600 text-[0.8rem] py-1 px-3 rounded transition-colors"
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}
//   return (
//     <div className="card shadow-sm border-0">
//       <div className="card-body p-3">
        
//         {/* 1. Slot Selector (Converted to Bootstrap Button Group) */}
//         <div className="mb-3">
//           <label className="form-label fw-bold small text-muted mb-2">Select Preset Slot</label>
//           <div className="btn-group d-flex w-100 shadow-sm" role="group">
//             {DATASET_SLOTS.map((slot) => (
//               <button
//                 key={slot}
//                 onClick={() => setActiveSlot(slot)}
//                 className={`btn py-2 ${
//                   activeSlot === slot ? "btn-primary shadow-sm" : "btn-outline-secondary"
//                 }`}
//               >
//                 Preset {slot}
//               </button>
//             ))}
//           </div>
//         </div>

//         {/* 2. Dataset Name & Uploader (Side by Side to save space) */}
//         <div className="row mb-3 align-items-end g-3">
//           <div className="col-12 col-md-5">
//             <label className="form-label fw-bold small mb-1">Dataset Name</label>
//             <input
//               type="text"
//               value={datasetName}
//               onChange={(e) => setDatasetName(e.target.value)}
//               className="form-control form-control-sm"
//               placeholder="e.g. ERA5_Thailand_1960_2020"
//             />
//           </div>
//           <div className="col-12 col-md-7">
//             <label className="form-label fw-bold small mb-1 text-primary">
//               Upload to Preset {activeSlot}
//             </label>
//             <DatasetUploader
//               slotId={activeSlot}
//               onUploadSuccess={() => fetchFiles(activeSlot)}
//             />
//           </div>
//         </div>

//         {/* 3. Scope Selection (Compact Grid) */}
//         <div className="card bg-light border-0 mb-3">
//           <div className="card-body p-3">
//             <div className="row g-3">
//               {/* Time Range */}
//               <div className="col-12 col-md-4">
//                 <label className="form-label small fw-bold text-muted mb-1">Time Range (Year)</label>
//                 <div className="input-group input-group-sm">
//                   <input
//                     type="number"
//                     value={scope.startYear}
//                     onChange={(e) => setScope({ ...scope, startYear: Number(e.target.value) })}
//                     className="form-control text-center"
//                     placeholder="Start"
//                   />
//                   <span className="input-group-text bg-white">-</span>
//                   <input
//                     type="number"
//                     value={scope.endYear}
//                     onChange={(e) => setScope({ ...scope, endYear: Number(e.target.value) })}
//                     className="form-control text-center"
//                     placeholder="End"
//                   />
//                 </div>
//               </div>

//               {/* Latitude */}
//               <div className="col-12 col-md-4">
//                 <label className="form-label small fw-bold text-muted mb-1">Latitude (Min - Max)</label>
//                 <div className="input-group input-group-sm">
//                   <input
//                     type="number"
//                     min="-90" max="90"
//                     value={scope.minLat}
//                     onChange={(e) => {
//                       const val = e.target.value;
//                       setScope({ ...scope, minLat: val === "" || val === "-" ? val : Number(val) });
//                     }}
//                     className="form-control text-center"
//                   />
//                   <span className="input-group-text bg-white">-</span>
//                   <input
//                     type="number"
//                     min="-90" max="90"
//                     value={scope.maxLat}
//                     onChange={(e) => {
//                       const val = e.target.value;
//                       setScope({ ...scope, maxLat: val === "" || val === "-" ? val : Number(val) });
//                     }}
//                     className="form-control text-center"
//                   />
//                 </div>
//               </div>

//               {/* Longitude */}
//               <div className="col-12 col-md-4">
//                 <label className="form-label small fw-bold text-muted mb-1">Longitude (Min - Max)</label>
//                 <div className="input-group input-group-sm">
//                   <input
//                     type="number"
//                     min="-180" max="180"
//                     value={scope.minLon}
//                     onChange={(e) => {
//                       const val = e.target.value;
//                       setScope({ ...scope, minLon: val === "" || val === "-" ? val : Number(val) });
//                     }}
//                     className="form-control text-center"
//                   />
//                   <span className="input-group-text bg-white">-</span>
//                   <input
//                     type="number"
//                     min="-180" max="180"
//                     value={scope.maxLon}
//                     onChange={(e) => {
//                       const val = e.target.value;
//                       setScope({ ...scope, maxLon: val === "" || val === "-" ? val : Number(val) });
//                     }}
//                     className="form-control text-center"
//                   />
//                 </div>
//               </div>
//             </div>
//           </div>
//         </div>

//         {/* Action Button */}
//         <div className="text-center mb-4">
//         <button
//           onClick={handleProcessSelection}
//           disabled={loading || fileList.length === 0}
//           className="btn btn-sm btn-success px-5 fw-bold shadow-sm"
//         >
//           {loading ? (
//             <><span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Processing (Clipping)...</>
//           ) : (
//             "Confirm & Clip Data"
//           )}
//         </button>
//         </div>

//         {/* 4. File List Visualization */}
//         <div>
//           <h6 className="fw-bold mb-2">Uploaded Files <span className="badge bg-secondary">{fileList.length}</span></h6>
          
//           <div className="list-group overflow-auto border rounded shadow-sm" style={{ maxHeight: "250px" }}>
//             {fileList.length === 0 && (
//               <div className="list-group-item text-center text-muted p-4 bg-light">
//                 No files uploaded yet.
//               </div>
//             )}

//             {fileList.map((file, idx) => (
//               <div key={idx} className="list-group-item list-group-item-action d-flex justify-content-between align-items-center p-2">
//                 <span className="text-truncate small" style={{ maxWidth: "80%" }} title={file.name}>
//                   {file.name}
//                 </span>
//                 <button
//                   onClick={() => handleDelete(file.name)}
//                   className="btn btn-sm btn-outline-danger py-0 px-2"
//                   style={{ fontSize: "0.8rem" }}
//                 >
//                   Delete
//                 </button>
//               </div>
//             ))}
//           </div>
//         </div>

//       </div>
//     </div>
//   );
// }