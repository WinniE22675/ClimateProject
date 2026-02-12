// src/pages/DatasetProcessPage.jsx
import React, { useState, useEffect } from "react";
import { useLocation, Link, useNavigate } from "react-router-dom"; 
import IndicesSelector from "../components/IndicesSelector";
// import RawTimeseriesViewer from "../components/RawTimeseriesViewer"; // ใช้ component เดิม
// import RawMapViewer from "../components/RawMapViewer"; // ใช้ component เดิม
import DatasetPreview from "../components/DatasetPreview";

import DownloadSection from "../components/DownloadSection";

export default function DatasetProcessPage() {
  const location = useLocation();
  const navigate = useNavigate();
  // get slotId from Upload page (if don't have set default = 1)
  // const initialSlot = location.state?.slotId || 1;
  // const [activeSlot, setActiveSlot] = useState(initialSlot);

  // Data States
  // const [files, setFiles] = useState([]);
  const [metadata, setMetadata] = useState(null);
  const [loadingMeta, setLoadingMeta] = useState(false);

  // Visualization States
  // const [selectedVar, setSelectedVar] = useState("");
  // const [previewReady, setPreviewReady] = useState(false); // check if backend generated preview
  // const [previewBaseUrl, setPreviewBaseUrl] = useState(""); // keep path at backend send back

  // Overlay Loading
  const [isCalculating, setIsCalculating] = useState(false);

  const [status, setStatus] = useState("loading");

  // const [step, setStep] = useState(null);
  // const [progress, setProgress] = useState(0);
  // const [statusMessage, setStatusMessage] = useState("");

  const [datasetList, setDatasetList] = useState([]);
  const [activeDataset, setActiveDataset] = useState(
    location.state?.datasetName || ""
  );
  // const [activeDataset, setActiveDataset] = useState("");

  // const location = useLocation();
  const pendingDataset = location.state?.datasetName || null;

  useEffect(() => {
    if (!activeDataset) return;
    // setPreviewReady(false);
    // setSelectedVar("");
    setMetadata(null);
    setStatus("loading");
    // setFiles([]);
    // setPreviewBaseUrl("");

    fetchData(activeDataset);
  }, [activeDataset]);

  const fetchData = async (activeDataset) => {
    setLoadingMeta(true);

    try {
      // 1. Fetch File List
      // const resFiles = await fetch(
      //   `http://localhost:8000/api/datasets/${slotId}/processed_files`
      // );
      // const dataFiles = await resFiles.json();
      // setFiles(dataFiles.files || []);

      // 2. Fetch Merged Metadata
      const resMeta = await fetch(
        `http://localhost:8000/api/datasets/${activeDataset}/metadata`
      );
      if (resMeta.ok) {
        const dataMeta = await resMeta.json();
        setMetadata(dataMeta);
        // Default select first variable
        // if (dataMeta.variables && dataMeta.variables.length > 0) {
        //   setSelectedVar(dataMeta.variables[0]);
        // }
      } else {
        // Handle case where metadata is 404 (dataset empty)
        setMetadata(null);
      }
    } catch (err) {
      console.error("Error fetching dataset info:", err);
      setMetadata(null);
    } finally {
      setLoadingMeta(false);
    }
  };

  // เรียก Backend ให้คำนวณและสร้างไฟล์ JSON/GeoJSON สำหรับ Preview
  // const handleGeneratePreview = async () => {
  //   if (!selectedVar) return;
  //   setPreviewReady(false);
  //   try {
  //     const res = await fetch(
  //       `http://localhost:8000/api/datasets/${activeSlot}/preview`,
  //       {
  //         method: "POST",
  //         headers: { "Content-Type": "application/json" },
  //         body: JSON.stringify({ variable: selectedVar }),
  //       }
  //     );
  //     if (res.ok) {
  //       const data = await res.json();
  //       // Backend send base_url back (from export_preview.py)
  //       // if not create by yourself: /output/preview_output/dataset_{activeSlot}/{selectedVar}
  //       setPreviewBaseUrl(
  //         data.base_url ||
  //           `/output/preview_output/dataset_${activeSlot}/${selectedVar}`
  //       );
  //       setPreviewReady(true);
  //     }
  //   } catch (err) {
  //     console.error("Preview generation failed", err);
  //   }
  // };

  // const handleCalculateIndices = (selectedIndices) => {
  //   console.log("Calculate:", selectedIndices);
  //   // TODO: เรียก API Calculate และ Redirect ไปหน้า Dashboard
  //   alert(
  //     `Calculating ${selectedIndices.join(", ")}... (Logic to be implemented)`
  //   );
  //   navigate("/");
  // };

  const handleCalculateIndices = async (selectedIndices, baseline) => {
    console.log("Calculate:", selectedIndices);

    // tell user will start
    const confirm = window.confirm(
      `Confirm calculate ${selectedIndices.length} indices? This may take a while.`
    );
    if (!confirm) return;
    setIsCalculating(true);

    try {
      const res = await fetch(
        `http://localhost:8000/api/datasets/${activeDataset}/calculate_indices`, //${activeSlot}
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
            selected_indices: selectedIndices,
            baseline: baseline,
           }),
        }
      );

      if (res.ok) {
        alert("Calculation started. You can leave this page to Dashboard...");
        navigate("/");
      } else {
        const err = await res.json();
        alert(`Error: ${err.detail}`);
        setIsCalculating(false);
      }
    } catch (e) {
      alert("Failed to connect to server");
      console.error(e);
      setIsCalculating(false);
    }
  };

  useEffect(() => {
    if (!activeDataset) return;

    setStatus("loading");

    const interval = setInterval(async () => {
      // if (status === "ready" || status === "error") {
      //   clearInterval(interval);
      //   return;
      // }

      try {
        const res = await fetch(
          `http://localhost:8000/api/datasets/${activeDataset}/status`
        );

        if (!res.ok) return;
        const data = await res.json();

        setStatus(data.status);

        // if (data.status === "processing") {
        //   setStep(data.step || null);
        //   setProgress(data.progress || 0);
        //   setStatusMessage(data.message || "");
        // }

        if (data.status === "ready") {
          // setStatus("ready");
          setMetadata(data);
          clearInterval(interval);
        } else if (data.status === "error") {
          // setStatus("error");
          clearInterval(interval);
        }
        // else status is "processing" -> continue polling
      } catch (e) {
        console.error("Polling error", e);
      }
    }, 2000); // Check every 2 seconds

    return () => clearInterval(interval);
  }, [activeDataset]); //, status

  useEffect(() => {
    fetchDatasetList();
  },);

  const fetchDatasetList = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/datasets");
      if (!res.ok) return 
        const data = await res.json();
        setDatasetList(data.datasets || []);

        // auto-select first dataset
        // if (data.datasets.length > 0) {
        //   setActiveDataset(data.datasets[0]);
        // }

        if (!activeDataset && data.datasets.length > 0) {
          setActiveDataset(data.datasets[0]);
        }
      } catch (err) {
      console.error("Failed to fetch dataset list", err);
    }
  };

  useEffect(() => {
    if (!pendingDataset) return;

    let tries = 0;
    const maxTries = 60; // ~3 minutes (3s * 60)

    const interval = setInterval(async () => {
      try {
        const res = await fetch("http://localhost:8000/api/datasets");
        if (!res.ok) return;

        const data = await res.json();
        const datasets = data.datasets || [];

        setDatasetList(datasets);

        if (datasets.includes(pendingDataset)) {
          setActiveDataset(pendingDataset);

          alert(`Dataset "${pendingDataset}" is ready.`);
          clearInterval(interval);
        }

        tries++;
        if (tries >= maxTries) {
          clearInterval(interval);
          alert("Processing is taking longer than expected.");
        }
      } catch (err) {
        console.error("Dataset polling failed", err);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [pendingDataset]);

  const fetchDatasets = async () => {
    const res = await fetch("http://localhost:8000/api/datasets");
    const data = await res.json();
    setDatasetList(data.datasets);
  };

  const handleDeleteDataset = async () => {
    try {
      const res = await fetch(
        `http://localhost:8000/api/datasets/${activeDataset}`,
        { method: "DELETE" }
      );

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Delete failed");
      }

      alert(`Dataset "${activeDataset}" deleted`);

      // reset selection
      setActiveDataset("");

      setStatus("loading");

      // reload dataset list
      fetchDatasets();
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div className="container mx-auto p-6 pb-20 relative">
      {/* Header & Navigation */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-800">Dataset Processor</h1>
          {/* Slot Selector (Dataset 1, 2, 3, 4) */}
          {/* {[1, 2, 3, 4].map((id) => (
            <button
              key={id}
              onClick={() => setActiveSlot(id)}
              className={`px-3 py-1 rounded border ${
                activeSlot === id
                  ? "bg-blue-600 text-white"
                  : "bg-white text-gray-700"
              }`}
            >
              Selected Dataset {id}
            </button>
          ))} */}
          <div className="flex gap-2 items-center">
            <label>Dataset:</label>
            <select
              value={activeDataset}
              onChange={(e) => setActiveDataset(e.target.value)}
              className="border px-3 py-1 rounded"
            >
              {datasetList.length === 0 && (
                <option value="">No dataset available</option>
              )}

              {datasetList.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </div>
      </div>

      {/* Loading State */}
      {/* {status === "processing" && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="w-2/3 bg-gray-200 rounded-full h-3 mb-4">
            <div
              className="bg-blue-600 h-3 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>

          <p className="text-lg font-medium text-gray-700">
            {step ? step.toUpperCase() : "PROCESSING"}
          </p>

          <p className="text-sm text-gray-500 mt-1">
            {statusMessage || "Processing dataset..."}
          </p>

          <p className="text-xs text-gray-400 mt-2">{progress}% completed</p>
        </div>
      )} */}

      {/* Error State */}
      {status === "error" && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative">
          <strong className="font-bold">Error!</strong>
          <span className="block sm:inline">
            {" "}
            Something went wrong during processing.
          </span>
        </div>
      )}

      {/* --- Part 1: Selected Files (Updated UI) --- */}
      <div className="bg-white p-4 rounded shadow mb-6 border">
        {/* File List Container */}
        <h4 className="text-md font-semibold mb-2 text-gray-700">
          Download Select Dataset
        </h4>
        <p className="text-sm text-gray-500 mb-3">
          Download as a single merged NetCDF file.
          {/* Select a specific range (Time/Area) to  */}
        </p>
        {/* sent slotId to Component use API */}
        <DownloadSection datasetName={activeDataset} datasetStatus={status} />
      </div>

      <div className="row mb-5">
        {/* LEFT: Metadata */}
        <div className="col-12 col-lg-6 mb-4 lg:mb-0">
          <div className="card h-100 shadow-sm">
            <div className="card-body">
              {metadata ? (
                // send [metadata] is array
                <DatasetPreview
                  metadata={[metadata]}
                  selectedFile={0}
                  onSelectFile={() => {}}
                />
              ) : (
                <div className="text-center p-5 text-muted">
                  {loadingMeta
                    ? "Loading..."
                    : "No Metadata (Please clip data first)"}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT: Indices Selector */}
        <div className="col-12 col-lg-6">
          <div className="card h-100 shadow-sm">
            <div className="card-body">
              {metadata && metadata.variables ? (
                <IndicesSelector
                  availableVars={metadata.variables}
                  onCalculate={handleCalculateIndices}
                />
              ) : (
                <div className="text-center p-5 text-muted">
                  Waiting for metadata...
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* --- Part 4 (Bottom): Visualization --- */}
      {/* <div className="bg-white p-6 rounded shadow border">
        <h3 className="font-bold text-xl mb-4 border-b pb-2">
          Visualization Preview
        </h3> */}

      {/* Controls */}
      {/* <div className="flex gap-4 mb-6 items-end">
          <div>
            <label className="block text-sm font-bold text-gray-700 mb-1">
              Select Variable
            </label>
            <select
              value={selectedVar}
              onChange={(e) => {
                setSelectedVar(e.target.value);
                setPreviewReady(false);
              }}
              className="border p-2 rounded w-40"
              disabled={!metadata}
            >
              {metadata?.variables?.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
          </div>
          <button
            onClick={handleGeneratePreview}
            disabled={!selectedVar || loadingMeta}
            className="bg-indigo-600 text-white px-4 py-2 rounded font-medium hover:bg-indigo-700 disabled:bg-gray-400"
          >
            Load Graphs & Map
          </button>
        </div> */}

      {/* Graphs & Maps Area */}
      {/* {previewReady && previewBaseUrl ? (
          <div className="row">
            ใช้ row class ของ bootstrap หรือ flex ของ tailwind ตาม existing css
            <div className="col-12 col-lg-6 mb-4">
              <h4 className="text-md font-semibold mb-2">
                Timeseries (Area Average)
              </h4>
              Reuse Existing Component
              <RawTimeseriesViewer
                fileIndex={activeSlot}
                variable={selectedVar}
              />
            </div>
            <div className="col-12 col-lg-6">
              <h4 className="text-md font-semibold mb-2">
                Spatial Map (Time Average)
              </h4>
              Reuse Existing Component
              <RawMapViewer fileIndex={activeSlot} variable={selectedVar} />
            </div>
          </div>
        ) : (
          <div className="h-64 bg-gray-50 flex items-center justify-center border-2 border-dashed rounded text-gray-400">
            Select a variable and click "Load Graphs & Map" to visualize.
          </div>
        )}
      </div> */}

      <button
        className="btn btn-sm btn-danger"
        disabled={!activeDataset || activeDataset === "default"}
        onClick={handleDeleteDataset}
      >
        Delete Dataset
      </button>

      {isCalculating && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60">
          <div className="bg-white p-8 rounded-xl shadow-xl max-w-md w-full text-center">
            <div className="animate-spin rounded-full h-14 w-14 border-4 border-gray-200 border-t-blue-600 mx-auto mb-6"></div>

            <h3 className="text-xl font-semibold mb-2">Calculating Indices</h3>

            <p className="text-gray-600 text-sm mb-4">
              Please wait while indices are being calculated.
            </p>

            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-blue-600 h-2 rounded-full animate-pulse w-3/4" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
