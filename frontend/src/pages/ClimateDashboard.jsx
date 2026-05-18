import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import IndicesViewer from "../components/IndicesViewer";
import GridMapViewer from "../components/GridMapViewer";
import { datasetAPI } from '../services/api';

export default function ClimateDashboard() {
  const ALL_INDICES = [
    "pr",
    "tmax",
    "tmin",
    "SPI3",
    "SPI6",
    "SPI9",
    "SPI12",
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
    "FD",
    "SU",
    "ID",
    "TR",
    "TXx",
    "TNx",
    "TXn",
    "TNn",
    "TN10p",
    "TX10p",
    "TN90p",
    "TX90p",
    "WSDI",
    "CSDI",
    // "DTR",
    // "ETR",
    "SPI3_Drought_Frequency",
    "SPI3_Drought_Duration",
    "SPI3_Drought_Peak",
    "SPI3_Drought_Severity",
    "SPI3_Flood_Frequency",
    "SPI3_Flood_Duration",
    "SPI3_Flood_Peak",
    "SPI3_Flood_Severity",

    "SPI6_Drought_Frequency",
    "SPI6_Drought_Duration",
    "SPI6_Drought_Peak",
    "SPI6_Drought_Severity",
    "SPI6_Flood_Frequency",
    "SPI6_Flood_Duration",
    "SPI6_Flood_Peak",
    "SPI6_Flood_Severity",

    "SPI9_Drought_Frequency",
    "SPI9_Drought_Duration",
    "SPI9_Drought_Peak",
    "SPI9_Drought_Severity",
    "SPI9_Flood_Frequency",
    "SPI9_Flood_Duration",
    "SPI9_Flood_Peak",
    "SPI9_Flood_Severity",

    "SPI12_Drought_Frequency",
    "SPI12_Drought_Duration",
    "SPI12_Drought_Peak",
    "SPI12_Drought_Severity",
    "SPI12_Flood_Frequency",
    "SPI12_Flood_Duration",
    "SPI12_Flood_Peak",
    "SPI12_Flood_Severity",
  ];

  const [indexName, setIndexName] = useState("PRCPTOT");
  const [mode, setMode] = useState("actual"); // trend / actual

  const [country, setCountry] = useState("Thailand"); //"SEA"
  const [datasetList, setDatasetList] = useState([]);
  const [activeDataset, setActiveDataset] = useState("ERA5"); //default
  const [province, setProvince] = useState("");

  const [inputStartYear, setInputStartYear] = useState("1960");
  const [inputEndYear, setInputEndYear] = useState("2024");

  const [startYear, setStartYear] = useState("1960");
  const [endYear, setEndYear] = useState("2024");  

  const [metadata, setMetadata] = useState(null);
  const [datasetBounds, setDatasetBounds] = useState({ min: null, max: null });

  const [availableIndices, setAvailableIndices] = useState(ALL_INDICES);

  const [spiThreshold, setSpiThreshold] = useState(1.0);
  const [appliedSpiThreshold, setAppliedSpiThreshold] = useState(1.0);

  const [shapefileName, setShapefileName] = useState("");
  const [targetCol, setTargetCol] = useState("");
  // In a real app, you might want to fetch this list from the backend

  const [availableAreas, setAvailableAreas] = useState([]);

  // States for Workspace Management
  const [availableWorkspaces, setAvailableWorkspaces] = useState([]);
  const [workspaceConfigObj, setWorkspaceConfigObj] = useState({}); // Stores the entire "workspaces" object

  useEffect(() => {
    const fetchMetadata = async () => {
      // Guard clause: Do nothing if no dataset is selected
      if (!activeDataset) return; 

      setAvailableIndices([]);

      try {
        // Fetch the metadata file from the backend
        const response = await fetch(`http://172.16.2.110:10001/output/${activeDataset}/metadata.json?v=${new Date().getTime()}`);

        if (!response.ok) {
          throw new Error(`Failed to fetch metadata: HTTP ${response.status}`);
        }

        const data = await response.json();

        console.log("Fetched Metadata Data:", data); 
        console.log("Has available_indices?", !!data.available_indices);
        
        // Save raw metadata state in case other components need it
        setMetadata(data); 

        const wsData = data.workspaces || {};
        const wsNames = Object.keys(wsData);
        
        setWorkspaceConfigObj(wsData);
        setAvailableWorkspaces(wsNames);

        if (wsNames.length > 0) {
          const firstWs = wsNames[0];
          setCountry(firstWs); // This will trigger the next useEffect to load areas/indices
        } else {
          // Reset if no workspaces calculated yet
          setCountry("");
          setAvailableAreas([]);
          setAvailableIndices([]);
        }

        // Extract years from ISO string format (e.g., "1960-01-01T00:00:00" -> 1960)
        if (data.time_start && data.time_end) {
          const minYear = parseInt(data.time_start.substring(0, 4), 10);
          const maxYear = parseInt(data.time_end.substring(0, 4), 10);

          // 1. Update the logical bounds limit
          setDatasetBounds({ min: minYear, max: maxYear });

          // 2. Auto-set the draft inputs (UI) to the absolute min/max range
          setInputStartYear(minYear.toString());
          setInputEndYear(maxYear.toString());

          // 3. Auto-set the active state to trigger Map and Chart rendering
          setStartYear(minYear.toString());
          setEndYear(maxYear.toString());
        }
      } catch (error) {
        console.error("Error fetching dataset metadata:", error);
        
        // Reset states if fetch fails (e.g., file not found)
        setMetadata(null);
        setDatasetBounds({ min: null, max: null });
      }
    };

    fetchMetadata();
  }, [activeDataset]);

  useEffect(() => {
    console.log("Current Available Indices State:", availableIndices);
  }, [availableIndices]);

  useEffect(() => {
    if (!country || !workspaceConfigObj[country]) return;

    const currentConfig = workspaceConfigObj[country];

    // 1. Sync shapefile configuration
    setShapefileName(currentConfig.shapefile_name || "");
    setTargetCol(currentConfig.target_col || "");

    // 2. Sync Available Areas for this country
    setAvailableAreas(currentConfig.available_areas || []);
    setProvince(""); // Reset area selection to "Whole Workspace"

    // 3. Sync Available Indices (Raw Variables + Calculated Indices for this specific country)
    const rawVariables = metadata?.variables || [];
    const calculatedIndices = currentConfig.available_indices || [];
    const combinedOptions = [...rawVariables, ...calculatedIndices];

    setAvailableIndices(combinedOptions);

    // Auto-adjust indexName if the current one is not valid for this new country
    setIndexName((currentIndex) => {
      if (combinedOptions.length > 0 && !combinedOptions.includes(currentIndex)) {
        return combinedOptions[0];
      }
      return currentIndex;
    });

    if (datasetBounds && datasetBounds.min && datasetBounds.max) {
      // 1. Reset the UI input fields
      setInputStartYear(datasetBounds.min.toString());
      setInputEndYear(datasetBounds.max.toString());
      
      // 2. Reset the actual state used by Maps and Charts
      setStartYear(datasetBounds.min.toString());
      setEndYear(datasetBounds.max.toString());
    }

  }, [country, workspaceConfigObj, metadata]);

  const handleApplyYearRange = () => {
    let start = parseInt(inputStartYear, 10);
    let end = parseInt(inputEndYear, 10);

    // 1. Check for empty or invalid input
    if (isNaN(start) || isNaN(end)) {
      alert("Please enter valid years.");
      return;
    }

    // Auto-swap if start > end
    if (start > end) {
      // const temp = start;
      // start = end;
      // end = temp;
      // alert(`Start year was greater than End year. They have been swapped to ${start} - ${end}.`);
      alert("Start year cannot be greater than End year. Please correct it.");
      return; // Stop right here!
    }

    if (datasetBounds && datasetBounds.min !== null && datasetBounds.max !== null) {
      let isAdjusted = false;

      // Clamp Start Year
      if (start < datasetBounds.min) {
        start = datasetBounds.min;
        isAdjusted = true;
      }
      
      // Clamp End Year
      if (end > datasetBounds.max) {
        end = datasetBounds.max;
        isAdjusted = true;
      }

      // Notify user if we auto-adjusted their input
      if (isAdjusted) {
        alert(`Years automatically adjusted to fit the dataset range: ${datasetBounds.min} - ${datasetBounds.max}.`);
      }
    } else {
      console.warn("Warning: datasetBounds is null. Skipping clamp validation. Please check metadata fetch.");
    }

    // Update Active for send to sub Component (GridMapViewer, IndicesViewer)
    setStartYear(start.toString());
    setEndYear(end.toString());
    setAppliedSpiThreshold(spiThreshold);
  };

  useEffect(() => {
    fetchDatasetList();
  }, []);

  const fetchDatasetList = async () => {
    try {
      const res = await datasetAPI.getDatasets();
      if (!res.ok) return;

      const data = await res.json();
      const datasets = data.datasets || [];

      setDatasetList(datasets);

    } catch (err) {
      console.error("Failed to fetch datasets", err);
    }
  };

  return (
    <div className="w-full px-4 mt-4">
      {/* Controls Container */}
      <div className="flex items-end gap-4 flex-wrap mb-2">

        {/* 1. Dataset Selector */}
        <div>
          <label className="block text-base font-bold text-gray-500 mb-1">
            Dataset Source
          </label>
          <select
            className="block h-[36px] text-base border border-gray-300 rounded-md px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
            value={activeDataset}
            onChange={(e) => {
              setActiveDataset(e.target.value)
              setCountry("");
              setProvince("");
              setAvailableIndices([]);
            }
            }
          >
            {datasetList.length === 0 && (
              <option disabled>No uploaded dataset</option>
            )}
            {[...datasetList]
              .sort((a, b) => a.localeCompare(b))
              .map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
            ))}
          </select>
        </div>

        {/* 2. Workspace / Country */}
        <div>
          <label className="block text-base font-bold text-gray-500 mb-1">Workspace / Country</label>
          <select
            className="block h-[36px] text-base min-w-[160px] border border-gray-300 rounded-md px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white disabled:bg-gray-100 disabled:text-gray-500"
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            disabled={availableWorkspaces.length === 0}
          >
            {availableWorkspaces.length === 0 && (
              <option value="">No calculations yet</option>
            )}
            {[...availableWorkspaces]
              .sort((a, b) => a.localeCompare(b))
              .map((ws) => (
                <option key={ws} value={ws}>
                  {ws}
                </option>
            ))}
          </select>
        </div>

        {/* 3. Province Selector (Conditional) */}
        <div>
          <label className="block text-base font-bold text-gray-500 mb-1">Select Area</label>
          <select
            /* Added h-[38px] for equal height, max-w-[200px] and truncate to prevent long names from breaking layout */
            className="block h-[36px] max-w-[200px] truncate text-base border border-gray-300 rounded-md px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white disabled:bg-gray-100 disabled:text-gray-500"
            value={province}
            onChange={(e) => setProvince(e.target.value)}
            disabled={availableAreas.length === 0}
          >
            <option value="">Whole Country</option>
            {availableAreas.map((area) => (
              <option key={area} value={area}>
                {area}
              </option>
            ))}
          </select>
        </div>

        {/* 4. Index Selector */}
        <div>
          <label className="block text-base font-bold text-gray-500 mb-1">Index</label>
          <select
            /* Added h-[38px] */
            className="block h-[36px] text-base border border-gray-300 rounded-md px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
            value={indexName}
            onChange={(e) => setIndexName(e.target.value)}
          >
            {availableIndices.map((idx) => (
              <option key={idx} value={idx}>
                {idx}
              </option>
            ))}
          </select>
        </div>

        {/* 5. Start Year Input */}
        <div className="flex items-end gap-3">
          <div>
            <label className="block text-base font-bold text-gray-500 mb-1">Start Year</label>
            <input
              type="number"
              /* Added h-[38px] to perfectly match select boxes, removed style inline */
              className="block h-[36px] w-[85px] text-base border border-gray-300 rounded-md px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
              value={inputStartYear}
              onChange={(e) => setInputStartYear(e.target.value)}
            />
          </div>

          {/* 6. End Year Input */}
          <div>
            <label className="block text-base font-bold text-gray-500 mb-1">End Year</label>
            <input
              type="number"
              /* Added h-[38px] to perfectly match select boxes, removed style inline */
              className="block h-[36px] w-[85px] text-base border border-gray-300 rounded-md px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
              value={inputEndYear}
              onChange={(e) => setInputEndYear(e.target.value)}
            />
          </div>
        </div>

        {/* 7. Apply Button */}
        <div>
          <button 
            /* Added h-[38px] so the button aligns perfectly with inputs */
            className="h-[36px] bg-blue-600 hover:bg-blue-700 text-white text-base font-medium px-4 rounded-md transition-colors whitespace-nowrap" 
            onClick={handleApplyYearRange}
          >
            {/* Shortened text to save horizontal space */}
            {indexName.startsWith("SPI") && (indexName.includes("Drought") || indexName.includes("Flood"))
              ? "Apply SPI & Update Map" 
              : "Apply Update Map"}
          </button>
        </div>

        {/* 8. Upload New Data Button */}
        <div className="lg:ml-auto mt-4 lg:mt-0 flex-grow lg:flex-grow-0 text-center lg:text-right"> 
          <Link to="/manipulate">
            <button className="h-[36px] bg-blue-600 hover:bg-blue-700 text-white text-base font-medium px-4 rounded-md transition-colors shadow-sm whitespace-nowrap">
              Upload New Data
            </button>
          </Link>
        </div>

      </div>

      {/* Map and Chart Section using Tailwind Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="w-full">
          <IndicesViewer
            indexName={indexName}
            datasetName={activeDataset}
            country={country}
            province={province}   
            startYear={inputStartYear}
            endYear={inputEndYear}
            availableIndices={availableIndices}
            spiThreshold={spiThreshold} 
            setSpiThreshold={setSpiThreshold} 
          />
        </div>
        <div className="w-full">
          <GridMapViewer
            indexName={indexName}
            mode={mode}
            setMode={setMode}
            datasetName={activeDataset}
            country={country}
            province={province}   
            startYear={startYear}
            endYear={endYear}
            availableIndices={availableIndices}
            spiThreshold={appliedSpiThreshold} 
            shapefileName={shapefileName}
            targetCol={targetCol}
          />
        </div>
      </div>
    </div>
  );
}