// src/components/DownloadSection.jsx 
import React, { useState } from "react";
import { apiFetch } from '../services/api';

export default function DownloadSection({ datasetName, datasetStatus }) {
  const [downloading, setDownloading] = useState(false);

  const isReady = datasetStatus === "ready";
  const isDisabled = !isReady || downloading;

  const handleDownload = async () => {
    if (!isReady) return;

    setDownloading(true);
    try {
      const response = await apiFetch(`/datasets/${datasetName}/download_merged`, {
        method: "GET"
      });

      if (response.ok) {
        // Blob trick for download file from POST request
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${datasetName}_merged.nc`;
        document.body.appendChild(a);
        a.click();
        a.remove();
      } else {
        alert("Download failed");
      }
    } catch (err) {
      console.error(err);
      alert("Error downloading");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <button
      onClick={handleDownload}
      disabled={isDisabled}
      className={`w-full font-bold shadow-sm py-2 px-4 rounded-md transition-colors ${
        isReady && !downloading
          ? "bg-blue-600 hover:bg-blue-700 text-white"
          : "bg-gray-400 text-white cursor-not-allowed"
      }`}
    >
      {downloading
        ? "Downloading..."
        : isReady
        ? "Download Merged Dataset"
        : "Wait for Dataset"} 
    </button>
  );
}