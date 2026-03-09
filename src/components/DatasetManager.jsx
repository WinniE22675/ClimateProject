// src/components/DatasetManager.jsx
import React, { useState, useEffect } from "react";
import DatasetUploader from "./DatasetUploader";
import { useNavigate } from "react-router-dom";

const DATASET_SLOTS = [1, 2, 3, 4];

export default function DatasetManager() {
  const [activeSlot, setActiveSlot] = useState(1);
  const [fileList, setFileList] = useState([]);
  const [scope, setScope] = useState({
    startYear: 1960,
    endYear: 2024,
    minLat: 4, //-15,
    maxLat: 22, //30,
    minLon: 95, //90,
    maxLon: 107 //145,
  });
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate(); // Add hook

  const [datasetName, setDatasetName] = useState("");


  // Fetch file list when slot changes
  useEffect(() => {
    fetchFiles(activeSlot);
  }, [activeSlot]);

  const fetchFiles = async (slotId) => {
    try {
      const res = await fetch(
        `http://localhost:8000/api/datasets/${slotId}/files`
      );
      if (res.ok) {
        const data = await res.json();
        setFileList(data.files || []); // Expecting { files: [{name:Str, year:Int}, ...] }
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
      const res = await fetch(
        `http://localhost:8000/api/datasets/${activeSlot}/files/${filename}`,
        {
          method: "DELETE",
        }
      );
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
    setLoading(true);
    try {
      // send Scope to Backend manage file follow Metadata
      const res = await fetch(
        `http://localhost:8000/api/datasets/process_selection`, //`http://localhost:8000/api/datasets/${activeSlot}/process_selection`
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            slot_id: activeSlot,
            dataset_name: datasetName,
            scope: scope,
          }),
        }
      );
      if (res.ok) {
        // const result = await res.json();
        // alert(result.message || "Data processed successfully!");
        // TODO: Navigate to Result Page or Show success
        navigate("/process", { state: { datasetName } }); //slotId: activeSlot
      }
      else {
        alert("Failed to start processing.");
      }
    } catch (err) {
      console.error(err);
      alert("Error processing data");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card shadow-sm border-0">
      <div className="card-body p-3">
        
        {/* 1. Slot Selector (Converted to Bootstrap Button Group) */}
        <div className="mb-3">
          <label className="form-label fw-bold small text-muted mb-2">Select Preset Slot</label>
          <div className="btn-group d-flex w-100 shadow-sm" role="group">
            {DATASET_SLOTS.map((slot) => (
              <button
                key={slot}
                onClick={() => setActiveSlot(slot)}
                className={`btn py-2 ${
                  activeSlot === slot ? "btn-primary shadow-sm" : "btn-outline-secondary"
                }`}
              >
                Preset {slot}
              </button>
            ))}
          </div>
        </div>

        {/* 2. Dataset Name & Uploader (Side by Side to save space) */}
        <div className="row mb-3 align-items-end g-3">
          <div className="col-12 col-md-5">
            <label className="form-label fw-bold small mb-1">Dataset Name</label>
            <input
              type="text"
              value={datasetName}
              onChange={(e) => setDatasetName(e.target.value)}
              className="form-control form-control-sm"
              placeholder="e.g. ERA5_Thailand_1960_2020"
            />
          </div>
          <div className="col-12 col-md-7">
            <label className="form-label fw-bold small mb-1 text-primary">
              Upload to Preset {activeSlot}
            </label>
            <DatasetUploader
              slotId={activeSlot}
              onUploadSuccess={() => fetchFiles(activeSlot)}
            />
          </div>
        </div>

        {/* 3. Scope Selection (Compact Grid) */}
        <div className="card bg-light border-0 mb-3">
          <div className="card-body p-3">
            <div className="row g-3">
              {/* Time Range */}
              <div className="col-12 col-md-4">
                <label className="form-label small fw-bold text-muted mb-1">Time Range (Year)</label>
                <div className="input-group input-group-sm">
                  <input
                    type="number"
                    value={scope.startYear}
                    onChange={(e) => setScope({ ...scope, startYear: Number(e.target.value) })}
                    className="form-control text-center"
                    placeholder="Start"
                  />
                  <span className="input-group-text bg-white">-</span>
                  <input
                    type="number"
                    value={scope.endYear}
                    onChange={(e) => setScope({ ...scope, endYear: Number(e.target.value) })}
                    className="form-control text-center"
                    placeholder="End"
                  />
                </div>
              </div>

              {/* Latitude */}
              <div className="col-12 col-md-4">
                <label className="form-label small fw-bold text-muted mb-1">Latitude (Min - Max)</label>
                <div className="input-group input-group-sm">
                  <input
                    type="number"
                    min="-90" max="90"
                    value={scope.minLat}
                    onChange={(e) => {
                      const val = e.target.value;
                      setScope({ ...scope, minLat: val === "" || val === "-" ? val : Number(val) });
                    }}
                    className="form-control text-center"
                  />
                  <span className="input-group-text bg-white">-</span>
                  <input
                    type="number"
                    min="-90" max="90"
                    value={scope.maxLat}
                    onChange={(e) => {
                      const val = e.target.value;
                      setScope({ ...scope, maxLat: val === "" || val === "-" ? val : Number(val) });
                    }}
                    className="form-control text-center"
                  />
                </div>
              </div>

              {/* Longitude */}
              <div className="col-12 col-md-4">
                <label className="form-label small fw-bold text-muted mb-1">Longitude (Min - Max)</label>
                <div className="input-group input-group-sm">
                  <input
                    type="number"
                    min="-180" max="180"
                    value={scope.minLon}
                    onChange={(e) => {
                      const val = e.target.value;
                      setScope({ ...scope, minLon: val === "" || val === "-" ? val : Number(val) });
                    }}
                    className="form-control text-center"
                  />
                  <span className="input-group-text bg-white">-</span>
                  <input
                    type="number"
                    min="-180" max="180"
                    value={scope.maxLon}
                    onChange={(e) => {
                      const val = e.target.value;
                      setScope({ ...scope, maxLon: val === "" || val === "-" ? val : Number(val) });
                    }}
                    className="form-control text-center"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Action Button */}
        <div className="text-center mb-4">
        <button
          onClick={handleProcessSelection}
          disabled={loading || fileList.length === 0}
          className="btn btn-sm btn-success px-5 fw-bold shadow-sm"
        >
          {loading ? (
            <><span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Processing (Clipping)...</>
          ) : (
            "Confirm & Clip Data"
          )}
        </button>
        </div>

        {/* 4. File List Visualization */}
        <div>
          <h6 className="fw-bold mb-2">Uploaded Files <span className="badge bg-secondary">{fileList.length}</span></h6>
          
          <div className="list-group overflow-auto border rounded shadow-sm" style={{ maxHeight: "250px" }}>
            {fileList.length === 0 && (
              <div className="list-group-item text-center text-muted p-4 bg-light">
                No files uploaded yet.
              </div>
            )}

            {fileList.map((file, idx) => (
              <div key={idx} className="list-group-item list-group-item-action d-flex justify-content-between align-items-center p-2">
                <span className="text-truncate small" style={{ maxWidth: "80%" }} title={file.name}>
                  {file.name}
                </span>
                <button
                  onClick={() => handleDelete(file.name)}
                  className="btn btn-sm btn-outline-danger py-0 px-2"
                  style={{ fontSize: "0.8rem" }}
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
//     <div className="p-4 border rounded shadow bg-white">
//       {/* 1. Slot Selector */}
//       <div className="flex gap-2 mb-4">
//         {DATASET_SLOTS.map((slot) => (
//           <button
//             key={slot}
//             onClick={() => setActiveSlot(slot)}
//             className={`px-4 py-2 rounded ${
//               activeSlot === slot ? "bg-blue-600 text-white" : "bg-gray-200"
//             }`}
//           >
//             Preset {slot}
//           </button>
//         ))}
//       </div>

//       {/* 2. Uploader for Active Slot */}
//       <div className="mb-6">
//         <h3 className="font-bold mb-2">Upload to Preset {activeSlot}</h3>
//         <DatasetUploader
//           slotId={activeSlot}
//           onUploadSuccess={() => fetchFiles(activeSlot)}
//         />
//       </div>

//       <div className="mb-4">
//         <label className="block font-semibold mb-1">Dataset Name</label>
//         <input
//           type="text"
//           value={datasetName}
//           onChange={(e) => setDatasetName(e.target.value)}
//           className="border p-2 w-full"
//           placeholder="e.g. SEA_ERA5_1960_2020"
//         />
//       </div>

//       {/* 3. Scope Selection (Time, Lat, Lon) */}
//       <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6 p-4 bg-gray-50 rounded">
//         <div>
//           <label className="block font-semibold">Time Range (Year)</label>
//           <div className="flex gap-2">
//             <input
//               type="number"
//               value={scope.startYear}
//               onChange={(e) =>
//                 setScope({ ...scope, startYear: Number(e.target.value) })
//               }
//               className="border p-1 w-full"
//               placeholder="Start"
//             />
//             <input
//               type="number"
//               value={scope.endYear}
//               onChange={(e) =>
//                 setScope({ ...scope, endYear: Number(e.target.value) })
//               }
//               className="border p-1 w-full"
//               placeholder="End"
//             />
//           </div>
//         </div>
//         <div>
//           <label className="block font-semibold">Latitude (Min - Max)</label>
//           <div className="flex gap-2">
//             <input
//               type="number"
//               min="-90"
//               max="90"
//               value={scope.minLat}
//               // onChange={(e) =>
//               //   setScope({ ...scope, minLat: Number(e.target.value) })
//               // }
//               onChange={(e) => {
//                 const val = e.target.value;
//                 setScope({
//                   ...scope,
//                   minLat: val === "" || val === "-" ? val : Number(val),
//                 });
//               }}
//               className="border p-1 w-full"
//             />
//             <input
//               type="number"
//               value={scope.maxLat}
//               min="-90"
//               max="90"
//               onChange={(e) => {
//                 const val = e.target.value;
//                 setScope({
//                   ...scope,
//                   maxLat: val === "" || val === "-" ? val : Number(val),
//                 });
//               }}
//               // onChange={(e) =>
//               //   setScope({ ...scope, maxLat: Number(e.target.value) })
//               // }
//               className="border p-1 w-full"
//             />
//           </div>
//         </div>
//         <div>
//           <label className="block font-semibold">Longitude (Min - Max)</label>
//           <div className="flex gap-2">
//             <input
//               type="number"
//               min="-180"
//               max="180"
//               value={scope.minLon}
//               // onChange={(e) =>
//               //   setScope({ ...scope, minLon: Number(e.target.value) })
//               // }
//               onChange={(e) => {
//                 const val = e.target.value;
//                 setScope({
//                   ...scope,
//                   minLon: val === "" || val === "-" ? val : Number(val),
//                 });
//               }}
//               className="border p-1 w-full"
//             />
//             <input
//               type="number"
//               min="-180"
//               max="180"
//               value={scope.maxLon}
//               // onChange={(e) =>
//               //   setScope({ ...scope, maxLon: Number(e.target.value) })
//               // }
//               onChange={(e) => {
//                 const val = e.target.value;
//                 setScope({
//                   ...scope,
//                   maxLon: val === "" || val === "-" ? val : Number(val),
//                 });
//               }}
//               className="border p-1 w-full"
//             />
//           </div>
//         </div>
//         <button
//           onClick={handleProcessSelection}
//           disabled={loading || fileList.length === 0}
//           className="col-span-1 md:col-span-3 bg-green-600 text-white py-2 rounded disabled:bg-gray-400"
//         >
//           {loading ? "Processing (Clipping)..." : "Confirm & Clip Data"}
//         </button>
//       </div>

//       {/* File List Visualization (Scrollable + Delete) */}
//       <div>
//         <h3 className="font-bold mb-2">Uploaded Files ({fileList.length})</h3>

//         {/* ข้อ 4: ใช้ max-h และ overflow-y-auto เพื่อให้มี Scrollbar เมื่อไฟล์เยอะ */}
//         <div className="max-h-60 overflow-y-auto border rounded p-2 grid grid-cols-1 gap-2 bg-gray-50">
//           {fileList.length === 0 && (
//             <p className="text-gray-400 text-center text-sm">
//               No files uploaded yet.
//             </p>
//           )}

//           {fileList.map((file, idx) => (
//             <div
//               key={idx}
//               className="p-2 text-sm border bg-white rounded flex justify-between items-center shadow-sm hover:shadow-md transition"
//             >
//               <span className="truncate w-3/4" title={file.name}>
//                 {file.name}
//               </span>

//               {/* ข้อ 2: ปุ่มลบไฟล์ */}
//               <button
//                 onClick={() => handleDelete(file.name)}
//                 className="text-red-500 hover:text-red-700 font-bold px-2 py-1 text-xs border border-red-200 rounded hover:bg-red-50"
//               >
//                 Delete
//               </button>
//             </div>
//           ))}
//         </div>
//       </div>
//     </div>
//   );
// }
