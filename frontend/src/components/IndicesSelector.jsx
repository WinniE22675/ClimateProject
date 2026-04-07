import { useEffect, useState } from "react";
import { datasetAPI } from "../services/api";

export default function IndicesSelector({ availableVars, onCalculate }) {
  const [availableIndices, setAvailableIndices] = useState({});
  const [selected, setSelected] = useState([]);

  const [baselineStart, setBaselineStart] = useState("");
  const [baselineEnd, setBaselineEnd] = useState("");

  const [spiThreshold, setSpiThreshold] = useState(1);

  const [shapefileName, setShapefileName] = useState("");
  const [countryName, setCountryName] = useState(""); // Workspace Name

  const [availableCols, setAvailableCols] = useState([]);
  const [selectedCol, setSelectedCol] = useState("");
  const [loadingCols, setLoadingCols] = useState(false);
  
  // State to track the recommended column for UI rendering
  const [defaultCol, setDefaultCol] = useState("");

  // State to hold the list of available shapefiles for the dropdown
  const [shapefileList, setShapefileList] = useState([]);

  useEffect(() => {
    const fetchShapefiles = async () => {
      try {
        const res = await datasetAPI.getShapefiles(); // Ensure this is defined in your api.js
        if (res.ok) {
          const data = await res.json();
          setShapefileList(data.shapefiles || []);
        }
      } catch (err) {
        console.error("Failed to fetch shapefiles", err);
      }
    };
    fetchShapefiles();
  }, []);

  useEffect(() => {
    if (!availableVars || availableVars.length === 0) return;

    const map = {
      pr: [
        "PRCPTOT",
        "Rx1day",
        "Rx5day",
        "SDII",
        "R10mm",
        "R20mm",
        "CDD",
        "CWD",
        "R95p",
        "R99p",
        "R95pTOT",
        "R99pTOT",
        "SPI3",
        "SPI6",
        "SPI9",
        "SPI12",
      ],
      tmax: ["TXx", "TXn", "SU", "TR", "TX10p", "TX90p", "WSDI"],
      tmin: ["TNx", "TNn", "FD", "ID", "TN10p", "TN90p", "CSDI"],
    };

    let result = {};
    availableVars.forEach((v) => {
      result[v] = map[v] || [];
    });

    setAvailableIndices(result);
  }, [availableVars]);
  // create object for user select like
  // {
  //   pr: ["PRCPTOT", "Rx1day", "Rx5day"],
  //   tmax: ["TXx"]
  // }

  const toggleSelect = (name) => {
    setSelected((prev) =>
      prev.includes(name) ? prev.filter((x) => x !== name) : [...prev, name]
    );
  };

  // Select All Functions
  const selectAll = () => {
    const all = Object.values(availableIndices).flat();
    // (Toggle All)
    if (all.every((i) => selected.includes(i))) {
      setSelected([]);
    } else {
      setSelected([...new Set(all)]); // Unique
    }
  };

  // const handleClick = () => {
  //   onCalculate(selected);
  // };
  
  const selectCategory = (variable) => {
    const indicesInCat = availableIndices[variable];

    const allSelected = indicesInCat.every((i) => selected.includes(i));

    if (allSelected) {
      // Unselect all in category
      setSelected((prev) => prev.filter((i) => !indicesInCat.includes(i)));
    } else {
      // Select all in category
      setSelected((prev) => [...new Set([...prev, ...indicesInCat])]);
    }
  };

  const hasSPISelected = selected.some((idx) => idx.startsWith("SPI"));

  // Auto-fetch columns when shapefileName changes (Replaces the Load button)
  useEffect(() => {
    if (shapefileName) {
      fetchColumns();
    }
  }, [shapefileName]);

  const fetchColumns = async () => {
    if (!shapefileName.trim()) return;
    setLoadingCols(true);
    setAvailableCols([]);
    setSelectedCol("");
    setDefaultCol("");
    
    try {
      const res = await datasetAPI.getShapefileColumns(shapefileName.trim());
      if (res.ok) {
        const data = await res.json();

        const recommendedCol = data.default || "";
        setDefaultCol(recommendedCol); // Save it to state

        // Sort the columns array: Move the recommended column to index 0
        const sortedCols = (data.columns || []).sort((a, b) => {
          if (a === recommendedCol) return -1; // 'a' comes first
          if (b === recommendedCol) return 1;  // 'b' comes first
          return 0; // No change
        });

        setAvailableCols(data.columns || []);
        setSelectedCol(data.default || ""); // Auto-select the guessed column
      } else {
        alert("Shapefile not found on server.");
      }
    } catch (err) {
      console.error("Failed to fetch columns", err);
      alert("Error fetching shapefile columns.");
    } finally {
      setLoadingCols(false);
    }
  };

return (
    <div className="card shadow-sm border-0 h-100">
      
      {/* ========================================== */}
      {/* BOUNDARY CONFIGURATION SECTION (Top) */}
      {/* ========================================== */}
      <div className="card-body bg-light border-bottom p-3" style={{ flex: "0 0 auto" }}>
        <h6 className="fw-bold text-dark mb-3">
          <i className="bi bi-geo-alt me-2"></i>Boundary Configuration
        </h6>
        <div className="row g-2 mb-2">
          
          {/* Shapefile Selector */}
          <div className="col-12 col-md-6">
            <label className="form-label small fw-bold text-muted mb-1">Select Shapefile</label>
            <select 
              className="form-select form-select-sm shadow-sm"
              value={shapefileName}
              onChange={(e) => setShapefileName(e.target.value)}
            >
              <option value="" disabled>-- Choose Shapefile --</option>
              {shapefileList.map((sf) => (
                // Handle object structure {name: "...", is_global: true/false}
                <option key={sf.name} value={sf.name}>
                  {sf.name} {sf.is_global ? "(Default)" : ""}
                </option>
              ))}
            </select>
          </div>
          
          {/* Column Selector */}
          <div className="col-12 col-md-6">
            <label className="form-label small fw-bold text-muted mb-1">
              Target Area Column
              {/* Optional UI feedback while loading */}
              {loadingCols && <span className="spinner-border spinner-border-sm ms-2 text-primary" role="status"></span>}
            </label>
            <select 
              className="form-select form-select-sm shadow-sm"
              value={selectedCol}
              onChange={(e) => setSelectedCol(e.target.value)}
              disabled={availableCols.length === 0 || loadingCols}
            >
              <option value="">Select Column...</option>
              {availableCols.map(col => (
                // Append (Recommend) if it matches the defaultCol state
                <option key={col} value={col}>
                  {col} {col === defaultCol ? "(Recommend)" : ""}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="row g-2">
          <div className="col-12">
            <label className="form-label small fw-bold text-muted mb-1">Workspace Name (Country/Region)</label>
            <input 
              type="text" 
              className="form-control form-control-sm shadow-sm" 
              placeholder="e.g. Thailand, MyProject (Used for grouping files)"
              value={countryName}
              onChange={(e) => setCountryName(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* ========================================== */}
      {/* INDICES SELECTION SECTION (Middle/Bottom) */}
      {/* ========================================== */}
      <div className="card-header bg-white border-bottom py-2 d-flex justify-content-between align-items-center" style={{ minHeight: "60px", flex: "0 0 auto" }}>
        <h5 className="mb-0 fw-bold text-dark">Select Indices</h5>
        <button onClick={selectAll} className="btn btn-sm btn-outline-primary shadow-sm">
          {Object.values(availableIndices).flat().every((i) => selected.includes(i)) && selected.length > 0
            ? "Unselect All"
            : "Select All"}
        </button>
      </div>

      <div className="card-body d-flex flex-column p-3" style={{ flex: "1 1 auto", overflow: "hidden" }}>
        
        {/* Baseline & SPI Threshold Input */}
        <div className="row g-0 mb-3" style={{ flex: "0 0 auto" }}>
          
          {/* Baseline Column */}
          <div className={hasSPISelected ? "col-12 col-lg-7" : "col-12"}>
            <div className="bg-light border rounded p-3 h-100 shadow-sm">
              <label className="form-label fw-bold small text-muted mb-2">
                Baseline Period (for percentile-based)
              </label>
              <div className="input-group input-group-sm">
                <span className="input-group-text bg-white">Start Year</span>
                <input
                  type="number"
                  className="form-control text-center"
                  placeholder="e.g. 1981"
                  value={baselineStart}
                  onChange={(e) => setBaselineStart(e.target.value)}
                />
                <span className="input-group-text bg-white border-start-0 border-end-0">-</span>
                <span className="input-group-text bg-white">End Year</span>
                <input
                  type="number"
                  className="form-control text-center"
                  placeholder="e.g. 2010"
                  value={baselineEnd}
                  onChange={(e) => setBaselineEnd(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* SPI Threshold Column */}
          {hasSPISelected && (
            <div className="col-12 col-lg-5">
              <div className="bg-light border rounded p-3 h-100 shadow-sm">
                <label className="form-label fw-bold small text-muted mb-2">
                  SPI Threshold (for SPI Event)
                </label>
                <div className="input-group input-group-sm">
                  <span className="input-group-text bg-white">Threshold</span>
                  <input
                    type="number"
                    step="0.1"
                    className="form-control text-center"
                    value={spiThreshold}
                    onChange={(e) => setSpiThreshold(e.target.value)}
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Indices Checkboxes (Scrollable area) */}
        <div className="overflow-auto mt-2 pe-2" style={{ flex: "1 1 auto", maxHeight: "280px" }}>
          {Object.keys(availableIndices).map((variable) => (
            <div key={variable} className="mb-4">
              
              <div
                className="d-flex justify-content-between align-items-center bg-light p-2 rounded mb-2 border"
                onClick={() => selectCategory(variable)}
                style={{ cursor: "pointer" }}
              >
                <h6 className="mb-0 fw-bold text-primary text-uppercase">{variable}</h6>
                <span className="badge bg-secondary" style={{ fontSize: "0.7rem" }}>Click to select all</span>
              </div>

              <div className="row g-2 px-1">
                {availableIndices[variable].map((ind) => (
                  <div key={ind} className="col-6 col-md-3">
                    <div className="form-check border rounded p-2 ps-4 bg-white shadow-sm" style={{ cursor: "pointer" }}>
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id={`check-${ind}`}
                        checked={selected.includes(ind)}
                        onChange={() => toggleSelect(ind)}
                        style={{ cursor: "pointer" }}
                      />
                      <label className="form-check-label w-100 fw-bold text-dark" htmlFor={`check-${ind}`} style={{ cursor: "pointer", fontSize: "0.85rem" }}>
                        {ind}
                      </label>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Action Button */}
        <button
          className="btn btn-primary w-100 mt-4 py-2 fw-bold shadow-sm"
          style={{ flex: "0 0 auto" }}
          onClick={() =>
            onCalculate(
              selected, 
              {
                start_year: baselineStart ? parseInt(baselineStart) : null,
                end_year: baselineEnd ? parseInt(baselineEnd) : null,
              }, 
              parseFloat(spiThreshold),
              {
                name: shapefileName.trim(),
                targetCol: selectedCol,
                country: countryName.trim()
              }
            )
          }
          disabled={selected.length === 0 || !shapefileName || !selectedCol || !countryName}
        >
          <i className="bi bi-calculator me-2"></i>
          Calculate Selected Indices ({selected.length})
        </button>

      </div>
    </div>
  );
}

//   return (
//     <div className="card shadow-sm border-0 h-100">
//       <div className="card-header bg-white border-bottom py-2 d-flex justify-content-between align-items-center" style={{ minHeight: "60px" }}>
//         <h5 className="mb-0 fw-bold text-dark">Select Indices</h5>
//         <button onClick={selectAll} className="btn btn-sm btn-outline-primary shadow-sm">
//           {Object.values(availableIndices).flat().every((i) => selected.includes(i)) && selected.length > 0
//             ? "Unselect All"
//             : "Select All"}
//         </button>
//       </div>

//       {/* Baseline & SPI Threshold Input (Side-by-Side) */}
//         <div className="row g-0 mb-3">
          
//           {/* Baseline Column (Takes 12 cols if no SPI, 7 cols if SPI is selected) */}
//           <div className={hasSPISelected ? "col-12 col-lg-7" : "col-12"}>
//             <div className="bg-light border rounded p-3 h-100 shadow-sm">
//               <label className="form-label fw-bold small text-muted mb-2">
//                 Baseline Period (for percentile-based)
//               </label>
//               <div className="input-group input-group-sm">
//                 <span className="input-group-text bg-white">Start Year</span>
//                 <input
//                   type="number"
//                   className="form-control text-center"
//                   placeholder="e.g. 1981"
//                   value={baselineStart}
//                   onChange={(e) => setBaselineStart(e.target.value)}
//                 />
//                 <span className="input-group-text bg-white border-start-0 border-end-0">-</span>
//                 <span className="input-group-text bg-white">End Year</span>
//                 <input
//                   type="number"
//                   className="form-control text-center"
//                   placeholder="e.g. 2010"
//                   value={baselineEnd}
//                   onChange={(e) => setBaselineEnd(e.target.value)}
//                 />
//               </div>
//             </div>
//           </div>

//           {/* SPI Threshold Column (Shows only if SPI is selected, takes 5 cols) */}
//           {hasSPISelected && (
//             <div className="col-12 col-lg-5">
//               <div className="bg-light border rounded p-3 h-100 shadow-sm">
//                 <label className="form-label fw-bold small text-muted mb-2">
//                   SPI Threshold (for SPI Event)
//                 </label>
//                 <div className="input-group input-group-sm">
//                   <span className="input-group-text bg-white">Threshold</span>
//                   <input
//                     type="number"
//                     step="0.1"
//                     className="form-control text-center"
//                     value={spiThreshold}
//                     onChange={(e) => setSpiThreshold(e.target.value)}
//                   />
//                 </div>
//               </div>
//             </div>
//           )}

//         {/* Indices Checkboxes (Scrollable) */}
//         <div className="overflow-auto mt-2 pe-2 flex-grow-1" style={{ maxHeight: "280px" }}>
//           {Object.keys(availableIndices).map((variable) => (
//             <div key={variable} className="mb-4">
              
//               <div
//                 className="d-flex justify-content-between align-items-center bg-light p-2 rounded mb-2 border"
//                 onClick={() => selectCategory(variable)}
//                 style={{ cursor: "pointer" }}
//               >
//                 <h6 className="mb-0 fw-bold text-primary text-uppercase">{variable}</h6>
//                 <span className="badge bg-secondary" style={{ fontSize: "0.7rem" }}>Click to select all</span>
//               </div>

//               <div className="row g-2 px-1">
//                 {availableIndices[variable].map((ind) => (
//                   <div key={ind} className="col-6 col-md-3">
//                     <div className="form-check border rounded p-2 ps-4 bg-white shadow-sm" style={{ cursor: "pointer" }}>
//                       <input
//                         className="form-check-input"
//                         type="checkbox"
//                         id={`check-${ind}`}
//                         checked={selected.includes(ind)}
//                         onChange={() => toggleSelect(ind)}
//                         style={{ cursor: "pointer" }}
//                       />
//                       <label className="form-check-label w-100 fw-bold text-dark" htmlFor={`check-${ind}`} style={{ cursor: "pointer", fontSize: "0.85rem" }}>
//                         {ind}
//                       </label>
//                     </div>
//                   </div>
//                 ))}
//               </div>
//             </div>
//           ))}
//         </div>

//         {/* Action Button */}
//         <button
//           className="btn btn-primary w-100 mt-4 py-2 fw-bold shadow-sm"
//           onClick={() =>
//             onCalculate(selected, {
//               start_year: baselineStart ? parseInt(baselineStart) : null,
//               end_year: baselineEnd ? parseInt(baselineEnd) : null,
//             }, parseFloat(spiThreshold))
//           }
//           disabled={selected.length === 0}
//         >
//           <i className="bi bi-calculator me-2"></i>
//           Calculate Selected Indices ({selected.length})
//         </button>

//       </div>
//     </div>
//   );
// }