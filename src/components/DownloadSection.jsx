// src/components/DownloadSection.jsx (หรือแทรกใน DatasetProcessPage)

import React, { useState } from "react";

export default function DownloadSection({ datasetName, datasetStatus }) {
  // State สำหรับ Scope (ค่า Default อาจดึงมาจาก Metadata รวมก็ได้)
  // const [scope, setScope] = useState({
  //   startYear: 1960,
  //   endYear: 2024,
  //   minLat: 5,
  //   maxLat: 21,
  //   minLon: 97,
  //   maxLon: 106,
  // });
  const [downloading, setDownloading] = useState(false);

  const isReady = datasetStatus === "ready";
  const isDisabled = !isReady || downloading;

  const handleDownload = async () => {
    if (!isReady) return;

    setDownloading(true);
    try {
      const response = await fetch(
        // `http://localhost:8000/api/datasets/${slotId}/download_custom`,
        `http://localhost:8000/api/datasets/${datasetName}/download_merged`,
        {
          method: "GET",
          headers: { "Content-Type": "application/json" },
          // body: JSON.stringify(scope),
        }
      );

      if (response.ok) {
        // Blob trick เพื่อดาวน์โหลดไฟล์จาก POST request
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
      className={`btn w-100 fw-bold shadow-sm ${
        isReady && !downloading
          ? "btn-primary"
          : "btn-secondary"
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

//   return (
//     <div className="bg-gray-50 rounded mt-4">
//       {/* <h4 className="font-bold mb-2">Download Options</h4> */}

//       {/* <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6 p-4 bg-gray-50 rounded">
//         <div>
//           Inputs for Time/Lat/Lon (Copy UI มาจากหน้า Upload ได้เลย)
//           <label className="block font-semibold">Time Range (Year)</label>
//           <div className="flex gap-2">
//             <input
//               type="number"
//               placeholder="Start Year"
//               value={scope.startYear}
//               onChange={(e) =>
//                 setScope({ ...scope, startYear: parseInt(e.target.value) })
//               }
//               className="border p-1 rounded"
//             />
//             <input
//               type="number"
//               placeholder="End Year"
//               value={scope.endYear}
//               onChange={(e) =>
//                 setScope({ ...scope, endYear: parseInt(e.target.value) })
//               }
//               className="border p-1 rounded"
//             />
//           </div>
//           <div>
//             <label className="block font-semibold">Latitude (Min - Max)</label>
//             <div className="flex gap-2">
//               <input
//                 type="number"
//                 value={scope.minLat}
//                 onChange={(e) =>
//                   setScope({ ...scope, minLat: Number(e.target.value) })
//                 }
//                 className="border p-1 w-full"
//               />
//               <input
//                 type="number"
//                 value={scope.maxLat}
//                 onChange={(e) =>
//                   setScope({ ...scope, maxLat: Number(e.target.value) })
//                 }
//                 className="border p-1 w-full"
//               />
//             </div>
//           </div>
//           <div>
//             <label className="block font-semibold">Longitude (Min - Max)</label>
//             <div className="flex gap-2">
//               <input
//                 type="number"
//                 value={scope.minLon}
//                 onChange={(e) =>
//                   setScope({ ...scope, minLon: Number(e.target.value) })
//                 }
//                 className="border p-1 w-full"
//               />
//               <input
//                 type="number"
//                 value={scope.maxLon}
//                 onChange={(e) =>
//                   setScope({ ...scope, maxLon: Number(e.target.value) })
//                 }
//                 className="border p-1 w-full"
//               />
//             </div>
//           </div>
//         </div>
//       </div> */}

//       {/* <button
//         onClick={handleDownload}
//         disabled={downloading}
//         className="bg-blue-600 text-white px-4 py-2 rounded w-full disabled:bg-gray-400"
//       >
//         {downloading
//           ? "Processing & Downloading..."
//           : "Download Merged Dataset"}
//       </button>
//     </div>
//   );
// } */}
//       <button
//         onClick={handleDownload}
//         disabled={isDisabled}
//         className={`w-full px-4 py-2 rounded font-medium transition
//           ${
//             isReady && !downloading
//               ? "bg-blue-600 text-white hover:bg-blue-700"
//               : "bg-gray-300 text-gray-500 cursor-not-allowed"
//           }
//         `}
//       >
//         {downloading
//           ? "Downloading..."
//           : isReady
//           ? "Download Merged Dataset"
//           : "Wait for Dataset"} 
//       </button>

//       {/* {!isReady && (
//         <p className="text-xs text-gray-400 mt-2 text-center">
//           Download will be available after processing is completed
//         </p>
//       )} */}
//     </div>
//   );
// }