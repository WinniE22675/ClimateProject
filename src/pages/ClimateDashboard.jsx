import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import IndicesViewer from "../components/IndicesViewer";
import GridMapViewer from "../components/GridMapViewer";
import { datasetAPI } from '../services/api';

export default function ClimateDashboard() {

  
  const countries = [
    "Thailand",
    // "Vietnam",
    // "Laos",
    // "Cambodia",
    // "Myanmar",
    // "Malaysia",
    // "Philippines",
    // "Indonesia",
    // "Singapore",
    // "Brunei",
    // "Timor-Leste",
    // "SEA",
  ];

  const provinces = [
    "Amnat Charoen",
    "Ang Thong",
    "Bangkok",
    "Bueng Kan",
    "Buri Ram",
    "Chachoengsao",
    "Chai Nat",
    "Chaiyaphum",
    "Chanthaburi",
    "Chiang Mai",
    "Chiang Rai",
    "Chon Buri",
    "Chumphon",
    "Kalasin",
    "Kamphaeng Phet",
    "Kanchanaburi",
    "Khon Kaen",
    "Krabi",
    "Lampang",
    "Lamphun",
    "Loei",
    "Lop Buri",
    "Mae Hong Son",
    "Maha Sarakham",
    "Mukdahan",
    "Nakhon Nayok",
    "Nakhon Pathom",
    "Nakhon Phanom",
    "Nakhon Ratchasima",
    "Nakhon Sawan",
    "Nakhon Si Thammarat",
    "Nan",
    "Narathiwat",
    "Nong Bua Lam Phu",
    "Nong Khai",
    "Nonthaburi",
    "Pathum Thani",
    "Pattani",
    "Phangnga",
    "Phatthalung",
    "Phayao",
    "Phetchabun",
    "Phetchaburi",
    "Phichit",
    "Phitsanulok",
    "Phra Nakhon Si Ayutthaya",
    "Phrae",
    "Phuket",
    "Prachin Buri",
    "Prachuap Khiri Khan",
    "Ranong",
    "Ratchaburi",
    "Rayong",
    "Roi Et",
    "Sa Kaeo",
    "Sakon Nakhon",
    "Samut Prakan",
    "Samut Sakhon",
    "Samut Songkhram",
    "Saraburi",
    "Satun",
    "Si Sa Ket",
    "Sing Buri",
    "Songkhla",
    "Sukhothai",
    "Suphan Buri",
    "Surat Thani",
    "Surin",
    "Tak",
    "Trang",
    "Trat",
    "Ubon Ratchathani",
    "Udon Thani",
    "Uthai Thani",
    "Uttaradit",
    "Yala",
    "Yasothon",
  ];

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
  // const [datamode, setDataMode] = useState("default"); // default | upload

  const [country, setCountry] = useState("Thailand"); //"SEA"
  // const [datasetId, setDatasetId] = useState("default"); // default, 1, 2, 3, 4
  const [datasetList, setDatasetList] = useState([]);
  const [activeDataset, setActiveDataset] = useState("ERA5_1960_2024"); //default
  const [province, setProvince] = useState("");

  const [inputStartYear, setInputStartYear] = useState("1960");
  const [inputEndYear, setInputEndYear] = useState("2024");

  const [startYear, setStartYear] = useState("1960");
  const [endYear, setEndYear] = useState("2024");  

  const [metadata, setMetadata] = useState(null);
  const [datasetBounds, setDatasetBounds] = useState({ min: null, max: null });

  const [availableIndices, setAvailableIndices] = useState(ALL_INDICES);

  useEffect(() => {
    const fetchMetadata = async () => {
      // Guard clause: Do nothing if no dataset is selected
      if (!activeDataset) return; 

      setAvailableIndices([]);

      try {
        // Fetch the metadata file from the backend
        const response = await fetch(`http://localhost:8000/output/${activeDataset}/metadata.json?v=${new Date().getTime()}`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch metadata: HTTP ${response.status}`);
        }

        const data = await response.json();

        console.log("Fetched Metadata Data:", data); 
        console.log("Has available_indices?", !!data.available_indices);
        
        // Save raw metadata state in case other components need it
        setMetadata(data); 

        const rawVariables = data.variables || [];
        const climateIndices = data.available_indices || [];
        
        // Merge both arrays: ['pr', 'tmax', 'tmin', 'SPI3', 'PRCPTOT', ...]
        const combinedOptions = [...rawVariables, ...climateIndices];

        // Extract available indices from metadata
        if (combinedOptions.length > 0) {
          // Set the combined list to your state
          setAvailableIndices(combinedOptions);
          
          // Auto-adjust indexName if the current one is NOT in the new combined list
          setIndexName((currentIndex) => {
            if (!combinedOptions.includes(currentIndex)) {
              return combinedOptions[0]; // Select the first available (likely 'pr')
            }
            return currentIndex; // Keep the same if it exists
          });
        } else {
          // Fallback if backend doesn't provide the list
          setAvailableIndices(ALL_INDICES);
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
  };

  useEffect(() => {
    fetchDatasetList();
  }, []);

  const fetchDatasetList = async () => {
    try {
      // const res = await fetch("http://localhost:8000/api/datasets");
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
    <div className="container-fluid">
      {/* Controls Container */}
      <div className="d-flex align-items-end gap-3 flex-wrap mb-3">

        {/* 1. Dataset Selector */}
        <div>
          <label className="form-label small fw-bold text-muted">
            Dataset Source
          </label>
          <select
            className="form-select form-select-sm"
            value={activeDataset}
            onChange={(e) => {
              setActiveDataset(e.target.value)
              setAvailableIndices([]);
            }
            }
          >
            {/* <option value="default">Default Dataset</option> */}
            {datasetList.length === 0 && (
              <option disabled>No uploaded dataset</option>
            )}
            {datasetList.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </div>

        {/* 2. Country Selector */}
        <div>
          <label className="form-label small fw-bold text-muted">Country</label>
          <select
            className="form-select form-select-sm"
            value={country}
            onChange={(e) => {
              setCountry(e.target.value);
              setProvince("");
            }}
          >
            {countries.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>

        {/* 3. Province Selector (Conditional) */}
        {country === "Thailand" && (
          <div>
            <label className="form-label small fw-bold text-muted">Province</label>
            <select
              className="form-select form-select-sm"
              value={province}
              onChange={(e) => setProvince(e.target.value)}
            >
              <option value="">Whole Country</option>
              {provinces.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* 4. Index Selector (Moved here & formatted to match) */}
        <div>
          <label className="form-label small fw-bold text-muted">Index</label>
          <select
            className="form-select form-select-sm"
            value={indexName}
            onChange={(e) => setIndexName(e.target.value)}
          >
            {/* ALL_INDICES.map((idx) => ( */}
            {availableIndices.map((idx) => (
              <option key={idx} value={idx}>
                {idx}
              </option>
            ))}
          </select>
        </div>

        {/* 5. Start Year Input (Moved here & formatted to match) */}
        <div className="d-flex align-items-end gap-3">
          <div>
            <label className="form-label small fw-bold text-muted">Start Year</label>
            <input
              type="number"
              className="form-control form-control-sm"
              style={{ width: "85px" }}
              value={inputStartYear}
              onChange={(e) => setInputStartYear(e.target.value)}
            />
          </div>

          {/* 6. End Year Input (Moved here & formatted to match) */}
          <div>
            <label className="form-label small fw-bold text-muted">End Year</label>
            <input
              type="number"
              className="form-control form-control-sm"
              style={{ width: "85px" }}
              value={inputEndYear}
              onChange={(e) => setInputEndYear(e.target.value)}
            />
          </div>
        </div>

        {/* 7. Apply Button (Moved here) */}
        <div>
          <button 
            className="btn btn-sm btn-primary" 
            onClick={handleApplyYearRange}
          >
            Apply Years for Maps
          </button>
        </div>

        {/* 8. Upload New Data Button (Moved to the end of the line) */}
        <div className="ms-lg-auto mt-3 mt-lg-0 flex-grow-1 flex-lg-grow-0 text-center text-lg-end"> {/* 'ms-auto' pushes this button to the far right if there is extra space */}
          <Link to="/manipulate">
            <button className="btn btn-sm btn-primary p-2">Upload New Data</button>
          </Link>
        </div>

      </div>

      {/* Map and Chart Section */}
      <div className="row">
        <div className="col-12 col-lg-6">
          <IndicesViewer
            indexName={indexName}
            datasetName={activeDataset}
            country={country}
            province={province}   
            startYear={inputStartYear}
            endYear={inputEndYear}
            availableIndices={availableIndices}     
          />
        </div>
        <div className="col-12 col-lg-6">
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
          />
        </div>
      </div>
    </div>
  );
}