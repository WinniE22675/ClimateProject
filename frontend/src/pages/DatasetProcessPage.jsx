// src/pages/DatasetProcessPage.jsx
import React, { useState, useEffect } from "react";
import { useLocation, Link, useNavigate } from "react-router-dom"; 
import IndicesSelector from "../components/IndicesSelector";
import DatasetPreview from "../components/DatasetPreview";
import DownloadSection from "../components/DownloadSection";
import { apiFetch, datasetAPI } from '../services/api';

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

  const [workspaceList, setWorkspaceList] = useState([]);
  const [activeWorkspace, setActiveWorkspace] = useState("");

  // Add this array near the top of your component or outside it
  const PROTECTED_DATASETS = ["ERA5", "CMIP6_SSP245", "CMIP6_SSP585"];

  // Add a helper boolean inside your component
  const isProtectedDataset = PROTECTED_DATASETS.includes(activeDataset);

  // Add logic to protect specific workspaces within those datasets ---
  const PROTECTED_WORKSPACES = ["Thailand"];
  // It is protected ONLY IF the active dataset is a protected dataset AND the workspace name matches
  const isProtectedWorkspace = isProtectedDataset && PROTECTED_WORKSPACES.includes(activeWorkspace);

    useEffect(() => {
    if (metadata && metadata.workspaces) {
      const workspaces = Object.keys(metadata.workspaces);
      setWorkspaceList(workspaces);
      // Auto-select first workspace if available
      if (workspaces.length > 0 && !activeWorkspace) {
        setActiveWorkspace(workspaces[0]);
      } else if (workspaces.length === 0) {
        setActiveWorkspace("__NEW__"); // Special flag for new workspace
      }
    } else {
      setWorkspaceList([]);
      setActiveWorkspace("__NEW__");
    }
  }, [metadata]);

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
      // Fetch Merged Metadata
      // const resMeta = await fetch(
      //   `http://localhost:8000/api/datasets/${activeDataset}/metadata`
      // );
      const resMeta = await apiFetch(`/datasets/${activeDataset}/metadata`);
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

  const handleCalculateIndices = async (selectedIndices, baseline, spiThreshold, shapefileConfig) => {
    console.log("Calculate:", selectedIndices);

    // tell user will start
    const confirm = window.confirm(
      `Confirm calculate ${selectedIndices.length} indices? This may take a while.`
    );
    if (!confirm) return;
    setIsCalculating(true);

    try {
      // const res = await fetch(
      //   `http://localhost:8000/api/datasets/${activeDataset}/calculate_indices`, //${activeSlot}
      //   {
      //     method: "POST",
      //     headers: { "Content-Type": "application/json" },
      //     body: JSON.stringify({ 
      //       selected_indices: selectedIndices,
      //       baseline: baseline,
      //      }),
      //   }
      // );
      const res = await apiFetch(`/datasets/${activeDataset}/calculate_indices`, {
        method: "POST",
        body: JSON.stringify({ 
          selected_indices: selectedIndices,
          baseline: baseline,
          spi_threshold: spiThreshold,
          shapefile_name: shapefileConfig.name, 
          target_col: shapefileConfig.targetCol,
          country: shapefileConfig.country || "custom_workspace",
          is_existing: shapefileConfig.is_existing
        }),
      });

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
        // const res = await fetch(
        //   `http://localhost:8000/api/datasets/${activeDataset}/status`
        // );
        const res = await apiFetch(`/datasets/${activeDataset}/status`);

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
  }, []);

  const fetchDatasetList = async () => {
    try {
      // const res = await fetch("http://localhost:8000/api/datasets");
      const res = await datasetAPI.getDatasets();
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
    const maxTries = 300; // ~15 minutes (3s * 300) // ~3 minutes (3s * 60)

    const interval = setInterval(async () => {
      try {
        // const res = await fetch("http://localhost:8000/api/datasets");
        const res = await datasetAPI.getDatasets();
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
          // alert("Processing is taking longer than expected.");
          console.warn("Processing is taking a long time, continuing to wait in background...");
        }
      } catch (err) {
        console.error("Dataset polling failed", err);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [pendingDataset]);

  const fetchDatasets = async () => {
    // const res = await fetch("http://localhost:8000/api/datasets");
    const res = await datasetAPI.getDatasets();
    const data = await res.json();
    setDatasetList(data.datasets);
  };

  const handleDeleteDataset = async () => {
    try {
      // const res = await fetch(
      //   `http://localhost:8000/api/datasets/${activeDataset}`,
      //   { method: "DELETE" }
      // );
      const res = await apiFetch(`/datasets/${activeDataset}`, { 
        method: "DELETE" 
      });

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

  const handleDeleteWorkspace = async () => {
    if (!activeWorkspace) return;
    
    const confirm = window.confirm(`Are you sure you want to delete workspace "${activeWorkspace}"?`);
    if (!confirm) return;

    try {
      // Set loading state if you have a global one, or just wait
      const res = await apiFetch(`/datasets/${activeDataset}/workspaces/${activeWorkspace}`, {
        method: "DELETE"
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to delete workspace");
      }

      alert(`Workspace "${activeWorkspace}" deleted successfully`);
      
      // Reset active workspace and refresh metadata to update the UI
      setActiveWorkspace("");
      fetchData(activeDataset); // Re-fetch metadata to update dropdown
      
    } catch (err) {
      alert(err.message);
    }
  };

  // return (
  //   <div className="container-fluid position-relative mt-4">
      
  //     {/* 1. Header & Navigation */}
  //     <div className="d-flex justify-content-between align-items-center mb-2 pb-3 border-bottom">
  //       <h2 className="h3 fw-bold mb-0 text-dark"> Dataset Processor</h2>
        
  //       {/* <div className="d-flex gap-2 align-items-center">
  //         <div className="input-group input-group-sm shadow-sm">
  //           <span className="input-group-text bg-white fw-bold text-muted">Dataset:</span>
  //           <select
  //             value={activeDataset}
  //             onChange={(e) => setActiveDataset(e.target.value)}
  //             className="form-select"
  //           >
  //             {datasetList.length === 0 && (
  //               <option value="">No dataset available</option>
  //             )}
  //             {datasetList.map((name) => (
  //               <option key={name} value={name}>{name}</option>
  //             ))}
  //           </select>
  //         </div>
          
  //         <button
  //           className="btn btn-sm btn-outline-danger shadow-sm"
  //           disabled={!activeDataset || activeDataset === "default"}
  //           onClick={handleDeleteDataset}
  //         >
  //           Delete
  //         </button>
  //       </div> */}
  //       {/* Wrap in a flex container to hold both Dataset and Workspace groups */}
  //       <div className="d-flex flex-wrap gap-3 align-items-center">
          
  //         {/* Dataset Selector Group */}
  //         <div className="d-flex gap-2 align-items-center">
  //           <div className="input-group input-group-sm shadow-sm">
  //             <span className="input-group-text bg-white fw-bold text-muted">Dataset:</span>
  //             <select
  //               value={activeDataset}
  //               onChange={(e) => setActiveDataset(e.target.value)}
  //               className="form-select"
  //             >
  //               {datasetList.length === 0 && (
  //                 <option value="">No dataset available</option>
  //               )}
  //               {[...datasetList]
  //                 .sort((a, b) => a.localeCompare(b))
  //                 .map((name) => (
  //                   <option key={name} value={name}>{name}</option>
  //               ))}
  //               {/* {datasetList.map((name) => (
  //                 <option key={name} value={name}>{name}</option>
  //               ))} */}
  //             </select>
  //           </div>
            
  //           <button
  //             className="btn btn-sm btn-outline-danger shadow-sm"
  //             disabled={!activeDataset || activeDataset === "default"}
  //             onClick={handleDeleteDataset}
  //           >
  //             Delete
  //           </button>
  //         </div>

  //         {/* Workspace Selector Group */}
  //         <div className="d-flex gap-2 align-items-center">
  //           <div className="input-group input-group-sm shadow-sm">
  //             <span className="input-group-text bg-white fw-bold text-muted">Workspace:</span>
  //             <select
  //               value={activeWorkspace}
  //               onChange={(e) => setActiveWorkspace(e.target.value)}
  //               className="form-select"
  //               // disabled={workspaceList.length === 0}
  //             >
  //               <option value="__NEW__" >
  //                 -- New Workspace --
  //               </option>
  //               {/* {workspaceList.length === 0 && (
  //                 <option value="">No workspace</option>
  //               )} */}
  //               {[...workspaceList]
  //                 .sort((a, b) => a.localeCompare(b))
  //                 .map((ws) => (
  //                   <option key={ws} value={ws}>{ws}</option>
  //               ))}
  //               {/* {workspaceList.map((ws) => (
  //                 <option key={ws} value={ws}>{ws}</option>
  //               ))} */}
  //             </select>
  //           </div>
            
  //           <button
  //             className="btn btn-sm btn-outline-danger shadow-sm"
  //             // disabled={!activeWorkspace}
  //             disabled={!activeWorkspace || activeWorkspace === "__NEW__"}
  //             onClick={handleDeleteWorkspace}
  //           >
  //             Delete
  //           </button>
  //         </div>

  //       </div>
  //     </div>

  //     {/* Error State */}
  //     {status === "error" && (
  //       <div className="alert alert-danger shadow-sm mb-4" role="alert">
  //         <i className="bi bi-exclamation-triangle-fill me-2"></i>
  //         <strong>Error!</strong> Something went wrong during processing.
  //       </div>
  //     )}

  //     {/* 2. Download Section */}
  //     <div className="card shadow-sm border-0 mb-2">
  //       <div className="card-body d-flex flex-column flex-md-row justify-content-between align-items-center p-3">
  //         <div className="mb-3 mb-md-0">
  //           <h5 className="fw-bold mb-1 text-dark">Download Merged Dataset</h5>
  //           <p className="text-muted small mb-0">Download the selected area and time as a single merged NetCDF file.</p>
  //         </div>
  //         <div style={{ minWidth: "250px" }}>
  //           <DownloadSection datasetName={activeDataset} datasetStatus={status} />
  //         </div>
  //       </div>
  //     </div>

  //     {/* 3. Main Content (Preview & Indices) */}
  //     <div className="row g-4 mb-5">
        
  //       {/* LEFT: Metadata */}
  //       <div className="col-12 col-lg-6">
  //         {metadata && metadata.variables ? (
  //           <DatasetPreview
  //             metadata={[metadata]}
  //             selectedFile={0}
  //             onSelectFile={() => {}}
  //           />
  //         ) : (
  //           <div className="card h-100 shadow-sm border-0">
  //             <div className="card-body d-flex align-items-center justify-content-center text-muted bg-light rounded">
  //               {loadingMeta ? "Loading..." : "No Metadata (Please clip data first)"}
  //             </div>
  //           </div>
  //         )}
  //       </div>

  //       {/* RIGHT: Indices Selector */}
  //       <div className="col-12 col-lg-6">
  //         {metadata && metadata.variables ? (
  //           <IndicesSelector
  //             availableVars={metadata.variables}
  //             activeWorkspace={activeWorkspace}
  //             workspaceConfig={metadata?.workspaces?.[activeWorkspace] || null}
  //             onCalculate={handleCalculateIndices}
  //           />
  //         ) : (
  //           <div className="card h-100 shadow-sm border-0">
  //             <div className="card-body d-flex align-items-center justify-content-center text-muted bg-light rounded">
  //               Waiting for metadata...
  //             </div>
  //           </div>
  //         )}
  //       </div>
  //     </div>

  //     {/* Loading Overlay */}
  //     {isCalculating && (
  //       <div className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center" style={{ backgroundColor: "rgba(0,0,0,0.6)", zIndex: 9999 }}>
  //         <div className="bg-white p-5 rounded-4 shadow-lg text-center" style={{ maxWidth: "400px", width: "100%" }}>
  //           <div className="spinner-border text-primary mb-4" style={{ width: "3rem", height: "3rem" }} role="status">
  //             <span className="visually-hidden">Loading...</span>
  //           </div>
  //           <h4 className="fw-bold mb-2">Calculating Indices</h4>
  //           <p className="text-muted small mb-0">Please wait while indices are being calculated. This may take a while.</p>
  //         </div>
  //       </div>
  //     )}
  //   </div>
  // );
  return (
    <div className="w-full px-4 relative mt-6">
      
      {/* 1. Header & Navigation */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
        <h2 className="text-2xl font-bold m-0 text-gray-900">Dataset Processor</h2>
        
        {/* Wrap in a flex container to hold both Dataset and Workspace groups */}
        <div className="flex flex-wrap gap-4 items-center">
          
          {/* Dataset Selector Group */}
          <div className="flex gap-2 items-center">
            <div className="flex shadow-sm rounded-md overflow-hidden border border-gray-300 text-sm">
              <span className="flex items-center px-3 bg-white font-bold text-gray-500 border-r border-gray-300">Dataset:</span>
              <select
                value={activeDataset}
                onChange={(e) => setActiveDataset(e.target.value)}
                className="block w-full border-0 px-3 py-1.5 focus:ring-0 focus:outline-none bg-white text-gray-700"
              >
                {datasetList.length === 0 && (
                  <option value="">No dataset available</option>
                )}
                {[...datasetList]
                  .sort((a, b) => a.localeCompare(b))
                  .map((name) => (
                    <option key={name} value={name}>{name}</option>
                ))}
              </select>
            </div>
            
            <button
              className="border border-red-500 text-red-500 hover:bg-red-50 hover:text-red-600 text-sm font-medium py-1.5 px-3 rounded-md shadow-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent"
              disabled={!activeDataset || activeDataset === "default" || isProtectedDataset}
              onClick={handleDeleteDataset}
              title={isProtectedDataset ? "System datasets cannot be deleted" : "Delete Dataset"}
            >
              Delete
            </button>
          </div>

          {/* Workspace Selector Group */}
          <div className="flex gap-2 items-center">
            <div className="flex shadow-sm rounded-md overflow-hidden border border-gray-300 text-sm">
              <span className="flex items-center px-3 bg-white font-bold text-gray-500 border-r border-gray-300">Workspace:</span>
              <select
                value={activeWorkspace}
                onChange={(e) => setActiveWorkspace(e.target.value)}
                className="block w-full border-0 px-3 py-1.5 focus:ring-0 focus:outline-none bg-white text-gray-700"
              >
                <option value="__NEW__" >
                  -- New Workspace --
                </option>
                {[...workspaceList]
                  .sort((a, b) => a.localeCompare(b))
                  .map((ws) => (
                    <option key={ws} value={ws}>{ws}</option>
                ))}
              </select>
            </div>
            
            <button
              className="border border-red-500 text-red-500 hover:bg-red-50 hover:text-red-600 text-sm font-medium py-1.5 px-3 rounded-md shadow-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent"
              disabled={!activeWorkspace || activeWorkspace === "__NEW__" || isProtectedWorkspace}
              onClick={handleDeleteWorkspace}
              title={isProtectedWorkspace ? "System workspaces cannot be deleted" : "Delete Workspace"}
            >
              Delete
            </button>
          </div>

        </div>
      </div>

      {/* Error State */}
      {status === "error" && (
        <div className="bg-red-100 border border-red-200 text-red-700 px-4 py-3 rounded-md shadow-sm mb-6 flex items-center" role="alert">
          {/* Custom Alert Icon */}
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <div><strong>Error!</strong> Something went wrong during processing.</div>
        </div>
      )}

      {/* 2. Download Section */}
      <div className="bg-white rounded-lg border border-gray-200 mb-4">
        <div className="p-5 flex flex-col md:flex-row justify-between items-start md:items-center">
          <div className="mb-4 md:mb-0">
            <h5 className="font-bold text-lg mb-1 text-gray-900">Download Merged Dataset</h5>
            <p className="text-gray-500 text-sm m-0">Download the selected area and time as a single merged NetCDF file.</p>
          </div>
          <div className="w-full md:w-auto" style={{ minWidth: "250px" }}>
            <DownloadSection datasetName={activeDataset} datasetStatus={status} />
          </div>
        </div>
      </div>

      {/* 3. Main Content (Preview & Indices) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-12">
        
        {/* LEFT: Metadata */}
        <div className="w-full">
          {metadata && metadata.variables ? (
            <DatasetPreview
              metadata={[metadata]}
              selectedFile={0}
              onSelectFile={() => {}}
            />
          ) : (
            <div className="bg-white h-full shadow-sm rounded-lg border border-gray-100 flex flex-col">
              <div className="p-4 flex-1 flex items-center justify-center text-gray-500 bg-gray-50 rounded-lg min-h-[300px]">
                {loadingMeta ? "Loading..." : "No Metadata (Please clip data first)"}
              </div>
            </div>
          )}
        </div>

        {/* RIGHT: Indices Selector */}
        <div className="w-full">
          {metadata && metadata.variables ? (
            <IndicesSelector
              availableVars={metadata.variables}
              activeWorkspace={activeWorkspace}
              workspaceConfig={metadata?.workspaces?.[activeWorkspace] || null}
              onCalculate={handleCalculateIndices}
            />
          ) : (
            <div className="bg-white h-full shadow-sm rounded-lg border border-gray-100 flex flex-col">
              <div className="p-4 flex-1 flex items-center justify-center text-gray-500 bg-gray-50 rounded-lg min-h-[300px]">
                Waiting for metadata...
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Loading Overlay */}
      {isCalculating && (
        <div className="fixed inset-0 w-full h-full flex items-center justify-center z-[9999] bg-black/60">
          <div className="bg-white p-10 rounded-2xl shadow-xl text-center w-full max-w-[400px] mx-4">
            {/* Custom SVG Spinner (Blue) */}
            <svg className="animate-spin mx-auto h-12 w-12 text-blue-600 mb-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <h4 className="text-xl font-bold mb-2 text-gray-900">Calculating Indices</h4>
            <p className="text-gray-500 text-sm m-0">Please wait while indices are being calculated. This may take a while.</p>
          </div>
        </div>
      )}
    </div>
  );
}