import { useEffect, useState } from "react";
import { datasetAPI } from "../services/api";

export default function IndicesSelector({ availableVars, activeWorkspace, workspaceConfig, onCalculate }) {
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

  // Check if user is using an existing workspace
  const isExistingWorkspace = activeWorkspace && activeWorkspace !== "__NEW__";

  // Validation logic for the Calculate button
  const isFormValid = isExistingWorkspace 
    ? selected.length > 0 // If existing workspace, only require indices selection
    : selected.length > 0 && shapefileName && selectedCol && countryName; // If new, require all config

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
    <div className="bg-white rounded-lg border border-gray-200 h-full flex flex-col overflow-hidden">
      
      {/* ========================================== */}
      {/* BOUNDARY CONFIGURATION SECTION (Top) */}
      {/* ========================================== */}
      <div className="bg-gray-50 border-b border-gray-200 p-4" style={{ flex: "0 0 auto" }}>
        <h6 className="font-bold text-gray-900 mb-4 flex items-center">
          {/* Replaced bi-geo-alt icon */}
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
             <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
             <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Boundary Configuration
        </h6>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          
          {/* Shapefile Selector */}
          <div>
            <label className="block text-sm font-bold text-gray-500 mb-1">Select Shapefile</label>
            <select 
              className="block w-full text-sm border border-gray-300 rounded-md px-3 py-1.5 shadow-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
              value={isExistingWorkspace ? (workspaceConfig?.shapefile_name || "") : shapefileName}
              onChange={(e) => setShapefileName(e.target.value)}
              disabled={isExistingWorkspace}
            >
              {isExistingWorkspace ? (
                <option value={workspaceConfig?.shapefile_name || ""}>
                  {workspaceConfig?.shapefile_name || "Unknown"}
                </option>
              ) : (
                <>
                  <option value="" disabled>-- Choose Shapefile --</option>
                  {shapefileList.map((sf) => (
                    <option key={sf.name} value={sf.name}>
                      {sf.name} {sf.is_global ? "(Default)" : ""}
                    </option>
                  ))}
                </>
              )}
            </select>
          </div>
          
          {/* Column Selector */}
          <div>
            <label className="flex items-center text-sm font-bold text-gray-500 mb-1">
              Target Area Column
              {loadingCols && (
                <svg className="animate-spin h-3.5 w-3.5 ml-2 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              )}
            </label>
            <select 
              className="block w-full text-sm border border-gray-300 rounded-md px-3 py-1.5 shadow-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
              value={isExistingWorkspace ? (workspaceConfig?.target_col || "") : selectedCol}
              onChange={(e) => setSelectedCol(e.target.value)}
              disabled={isExistingWorkspace || availableCols.length === 0 || loadingCols}
            >
              {isExistingWorkspace ? (
                <option value={workspaceConfig?.target_col || ""}>
                  {workspaceConfig?.target_col || "Unknown"}
                </option>
              ) : (
                <>
                  <option value="">Select Column...</option>
                  {availableCols.map(col => (
                    <option key={col} value={col}>
                      {col} {col === defaultCol ? "(Recommend)" : ""}
                    </option>
                  ))}
                </>
              )}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-bold text-gray-500 mb-1">Workspace Name (Country/Region)</label>
          <input 
            type="text" 
            className="block w-full text-sm border border-gray-300 rounded-md px-3 py-1.5 shadow-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:text-gray-500" 
            placeholder="e.g. Thailand, MyProject (Used for grouping files)"
            value={isExistingWorkspace ? `${activeWorkspace} (Current)` : countryName}
            onChange={(e) => setCountryName(e.target.value)}
            disabled={isExistingWorkspace}
          />
        </div>
      </div>

      {/* ========================================== */}
      {/* INDICES SELECTION SECTION (Middle/Bottom) */}
      {/* ========================================== */}
      <div className="bg-white border-b border-gray-200 py-3 px-4 flex justify-between items-center min-h-[60px]" style={{ flex: "0 0 auto" }}>
        <h5 className="m-0 font-bold text-gray-900 text-lg">Select Indices</h5>
        
        {/* Helper variable to check if ALL indices across ALL categories are selected */}
        {(() => {
          const isAllSelected = Object.values(availableIndices).flat().every((i) => selected.includes(i)) && selected.length > 0;
          return (
            <button 
              onClick={selectAll} 
              className={`text-sm py-1.5 px-4 rounded-md shadow-sm transition-colors font-medium border ${
                isAllSelected 
                  ? "bg-blue-600 text-white border-blue-600 hover:bg-blue-700" /* Active State: Solid Blue */
                  : "bg-white text-blue-600 border-blue-600 hover:bg-blue-50"  /* Default State: Outline Blue */
              }`}
            >
              {isAllSelected ? "Unselect All" : "Select All"}
            </button>
          );
        })()}
      </div>

      <div className="flex flex-col p-4 bg-white" style={{ flex: "1 1 auto", overflow: "hidden" }}>
        
        {/* Baseline & SPI Threshold Input */}
        <div className={`grid grid-cols-1 ${hasSPISelected ? 'lg:grid-cols-12' : ''} gap-4 mb-4`} style={{ flex: "0 0 auto" }}>
          
          {/* Baseline Column */}
          <div className={hasSPISelected ? "lg:col-span-7" : "col-span-1"}>
            <div className="bg-gray-50 border border-gray-200 rounded-md p-4 h-full shadow-sm">
              <label className="block font-bold text-sm text-gray-500 mb-2">
                Baseline Period (for percentile-based)
              </label>
              <div className="flex border border-gray-300 rounded-md overflow-hidden bg-white text-sm">
                <span className="flex items-center px-3 bg-gray-50 border-r border-gray-300 text-gray-600 whitespace-nowrap">Start Year</span>
                <input
                  type="number"
                  className="w-full text-center px-2 py-1.5 focus:outline-none"
                  placeholder="e.g. 1981"
                  value={baselineStart}
                  onChange={(e) => setBaselineStart(e.target.value)}
                />
                <span className="flex items-center px-2 bg-gray-50 border-x border-gray-300 text-gray-500">-</span>
                <span className="flex items-center px-3 bg-gray-50 border-r border-gray-300 text-gray-600 whitespace-nowrap">End Year</span>
                <input
                  type="number"
                  className="w-full text-center px-2 py-1.5 focus:outline-none"
                  placeholder="e.g. 2010"
                  value={baselineEnd}
                  onChange={(e) => setBaselineEnd(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* SPI Threshold Column */}
          {hasSPISelected && (
            <div className="lg:col-span-5">
              <div className="bg-gray-50 border border-gray-200 rounded-md p-4 h-full shadow-sm">
                <label className="block font-bold text-sm text-gray-500 mb-2">
                  SPI Threshold (for SPI Event)
                </label>
                <div className="flex border border-gray-300 rounded-md overflow-hidden bg-white text-sm">
                  <span className="flex items-center px-3 bg-gray-50 border-r border-gray-300 text-gray-600">Threshold</span>
                  <input
                    type="number"
                    step="0.1"
                    className="w-full text-center px-2 py-1.5 focus:outline-none"
                    value={spiThreshold}
                    onChange={(e) => setSpiThreshold(e.target.value)}
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Indices Checkboxes (Scrollable area) */}
        <div className="overflow-y-auto pr-2 mt-2" style={{ flex: "1 1 auto", maxHeight: "280px" }}>
          {Object.keys(availableIndices).map((variable) => {
            
            {/* Check if ALL indices in THIS specific category are selected */}
            const isCategorySelected = availableIndices[variable].every((ind) => selected.includes(ind)) && availableIndices[variable].length > 0;

            return (
              <div key={variable} className="mb-5">
                
                {/* Category Header: Changes background slightly when fully selected */}
                <div
                  className={`flex justify-between items-center p-3 rounded-md mb-3 border cursor-pointer transition-colors ${
                    isCategorySelected 
                      ? "bg-blue-50 border-blue-200 hover:bg-blue-100" /* Active State: Light blue background */
                      : "bg-gray-50 border-gray-200 hover:bg-gray-100"   /* Default State: Light gray background */
                  }`}
                  onClick={() => selectCategory(variable)}
                >
                  <h6 className={`m-0 font-bold uppercase tracking-wide text-sm ${isCategorySelected ? "text-blue-700" : "text-blue-600"}`}>
                    {variable}
                  </h6>
                  
                  {/* Category Toggle Badge */}
                  <span 
                    className={`text-[0.7rem] px-2 py-1 rounded-md font-medium border transition-colors ${
                      isCategorySelected
                        ? "bg-blue-500 text-white border-blue-500"      /* Active State: Solid Blue */
                        : "bg-transparent text-gray-500 border-gray-400" /* Default State: Outline Gray */
                    }`}
                  >
                    {isCategorySelected ? "Unselect All" : "Select All"}
                  </span>
                </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 px-1">
                {availableIndices[variable].map((ind) => (
                  <div key={ind}>
                    <label 
                      className="flex items-center border border-gray-200 rounded-md p-2.5 bg-white shadow-sm cursor-pointer hover:border-blue-400 transition-colors"
                      htmlFor={`check-${ind}`}
                    >
                      <input
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded cursor-pointer mr-3"
                        type="checkbox"
                        id={`check-${ind}`}
                        checked={selected.includes(ind)}
                        onChange={() => toggleSelect(ind)}
                      />
                      <span className="w-full font-bold text-gray-800 text-[0.85rem] cursor-pointer">
                        {ind}
                      </span>
                    </label>
                  </div>
                ))}
              </div>
            </div>
          )})}
        </div>

        {/* Action Button */}
        <button
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2.5 px-4 rounded-md shadow-sm mt-5 transition-colors disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center"
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
                name: isExistingWorkspace ? "" : shapefileName.trim(),
                targetCol: isExistingWorkspace ? "" : selectedCol,
                country: isExistingWorkspace ? activeWorkspace : countryName.trim(),
                is_existing: isExistingWorkspace
              }
            )
          }
          disabled={!isFormValid}
        >
          {/* Replaced bi-calculator icon */}
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
          Calculate Selected Indices ({selected.length})
        </button>

      </div>
    </div>
  );
}
