import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import IndicesViewer from "../components/IndicesViewer";
import GridMapViewer from "../components/GridMapViewer";

export default function ClimateDashboard() {
  const [indexName, setIndexName] = useState("PRCPTOT");
  const [mode, setMode] = useState("actual"); // trend / actual
  // const [datamode, setDataMode] = useState("default"); // default | upload

  const [country, setCountry] = useState("Thailand"); //"SEA"
  // const [datasetId, setDatasetId] = useState("default"); // default, 1, 2, 3, 4
  const [datasetList, setDatasetList] = useState([]);
  const [activeDataset, setActiveDataset] = useState("ERA5"); //default
  const [province, setProvince] = useState("");

  const [inputStartYear, setInputStartYear] = useState("1960");
  const [inputEndYear, setInputEndYear] = useState("2024");

  const [startYear, setStartYear] = useState("1960");
  const [endYear, setEndYear] = useState("2024");  

  const [metadata, setMetadata] = useState(null);
  const [datasetBounds, setDatasetBounds] = useState({ min: null, max: null });

  // const [inputCountry, setInputCountry] = useState("Thailand");
  // const [inputProvince, setInputProvince] = useState("");

  useEffect(() => {
    const fetchMetadata = async () => {
      // Guard clause: Do nothing if no dataset is selected
      if (!activeDataset) return; 

      try {
        // Fetch the metadata file from the backend
        const response = await fetch(`http://localhost:8000/output/${activeDataset}/metadata.json`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch metadata: HTTP ${response.status}`);
        }

        const data = await response.json();
        
        // Save raw metadata state in case other components need it
        setMetadata(data); 

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

  // const handleApplyYearRange = () => {
  //   // Validate start > end alert
  //   if (parseInt(inputStartYear) > parseInt(inputEndYear)) {
  //     alert("Start Year less than or equal End Year.");
  //     return;
  //   }
  //   // update Active for send to sub Component
  //   setStartYear(inputStartYear);
  //   setEndYear(inputEndYear);
  // };
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

    // 2. Validate against Dataset Bounds (if metadata is loaded)
    // if (datasetBounds && datasetBounds.min !== null && datasetBounds.max !== null) {
    //   if (start < datasetBounds.min || end > datasetBounds.max) {
    //     alert(`Years out of range! The dataset only covers ${datasetBounds.min} to ${datasetBounds.max}. Please select within this range.`);
        
    //     // Optional: Revert input boxes back to the valid active states
    //     setInputStartYear(startYear);
    //     setInputEndYear(endYear);
        
    //     return; // Stop right here! No API call.
    //   }
    // }

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

    // 4. Trend Map specific validation (Requires at least 3 years to calculate Mann-Kendall)
    // Optional: Add this if your map viewer has a 'mode' state accessible here
    // if (mode === "trend" && (end - start < 2)) {
    //   alert("Trend map requires at least a 3-year range.");
    //   return; // Or auto-expand the range
    // }

    // Update the UI inputs so the user sees the corrected values
    // setInputStartYear(start.toString());
    // setInputEndYear(end.toString());

    // Update Active for send to sub Component (GridMapViewer, IndicesViewer)
    setStartYear(start.toString());
    setEndYear(end.toString());
    // setCountry(inputCountry);    
    // setProvince(inputProvince);
  };

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

  useEffect(() => {
    fetchDatasetList();
  }, []);

  const fetchDatasetList = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/datasets");
      if (!res.ok) return;

      const data = await res.json();
      const datasets = data.datasets || [];

      setDatasetList(datasets);

      // if really have dataset, will select first dataset
      // if (datasets.length > 0) {
      //   setActiveDataset(datasets[0]);
      // }
    } catch (err) {
      console.error("Failed to fetch datasets", err);
    }
  };

  return (
    <div className="container-fluid">
      {/* Controls Container: Added 'flex-wrap' to prevent overflow on smaller screens */}
      <div className="d-flex align-items-end gap-3 flex-wrap mb-3">

        {/* 1. Dataset Selector */}
        <div>
          <label className="form-label small fw-bold text-muted">
            Dataset Source
          </label>
          <select
            className="form-select form-select-sm"
            value={activeDataset}
            onChange={(e) => setActiveDataset(e.target.value)}
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
            {ALL_INDICES.map((idx) => (
              <option key={idx} value={idx}>
                {idx}
              </option>
            ))}
          </select>
        </div>

        {/* 5. Start Year Input (Moved here & formatted to match) */}
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
        <div className="ms-auto"> {/* 'ms-auto' pushes this button to the far right if there is extra space */}
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
          />
        </div>
      </div>
    </div>
  );
}
//   return (
//     <div className="container-fluid">
//       {/* <h2 className="text-xl font-bold whitespace-nowrap">Climate Change</h2> */}
//       {/* Controls Container bg-light rounded shadow-sm*/}
//       <div className="d-flex align-items-end gap-3 p-2">

//         {/*Dataset Selector*/}
//         <div>
//           <label className="form-label small fw-bold text-muted ">
//             Dataset Source
//           </label>
//           {/* <select
//             className="form-select form-select-sm"
//             value={datasetId}
//             onChange={(e) => setDatasetId(e.target.value)}
//           >
//             <option value="default">Default Dataset</option>
//             <option value="1">Dataset 1</option>
//             <option value="2">Dataset 2</option>
//             <option value="3">Dataset 3</option>
//             <option value="4">Dataset 4</option>
//           </select> */}
//           <select
//             className="form-select form-select-sm"
//             value={activeDataset}
//             onChange={(e) => setActiveDataset(e.target.value)}
//           >
//             <option value="default">Default Dataset</option>

//             {datasetList.length === 0 && (
//               <option disabled>No uploaded dataset</option>
//             )}

//             {datasetList.map((name) => (
//               <option key={name} value={name}>
//                 {name}
//               </option>
//             ))}
//           </select>
//         </div>

//         {/* 1. Country Selector */}
//         <div>
//           <label className="form-label small fw-bold text-muted">Country</label>
//           <select
//             className="form-select form-select-sm"
//             value={country}
//             onChange={(e) => {
//               setCountry(e.target.value)
//               setProvince("");
//             }}
//           >
//             {countries.map((c) => (
//               <option key={c} value={c}>
//                 {c}
//               </option>
//             ))}
//           </select>
//         </div>

//         {country === "Thailand" && (
//           <div>
//             <label className="form-label small fw-bold text-muted">Province</label>
//             <select
//               className="form-select form-select-sm"
//               value={province}
//               onChange={(e) => setProvince(e.target.value)}
//             >
//               <option value="">Whole Country</option> {/* Default option */}
//               {provinces.map((p) => (
//                 <option key={p} value={p}>
//                   {p}
//                 </option>
//               ))}
//             </select>
//           </div>
//         )}

//         <div className="">
//           <Link to="/manipulate" className="btn btn-sm btn-primary">
//             <button className="btn btn-sm btn-primary">Upload New Data</button>
//           </Link>
//         </div>
//       </div>

//       {/* <div>
//         <label className="form-label small fw-bold text-muted">
//           Climate Index
//         </label>
//         <select
//           className="form-select form-select-sm"
//           value={indexName}
//           onChange={(e) => setIndexName(e.target.value)}
//         >
//           {ALL_INDICES.map((idx) => (
//             <option key={idx} value={idx}>
//               {idx}
//             </option>
//           ))}
//         </select>
//       </div> */}
//       <div className="flex gap-2 items-center">
//         <label>Index:</label>
//         <select
//           value={indexName}
//           onChange={(e) => setIndexName(e.target.value)}
//           className="border p-1 rounded"
//         >
//           {ALL_INDICES.map((idx) => (
//             <option key={idx} value={idx}>
//               {idx}
//             </option>
//           ))}
//         </select>
//       </div>

//       {/* <div className="flex flex-wrap gap-2 items-center">
//         <div className="flex items-center gap-2">
//           <label>Start Year :</label>
//           <input
//             type="number"
//             value={startYear}
//             onChange={(e) => setStartYear(e.target.value)}
//             className="border p-1 w-20 rounded"
//           />
//         </div>
//         <div className="flex items-center gap-2">
//           <label>End Year :</label>
//           <input
//             type="number"
//             value={endYear}
//             onChange={(e) => setEndYear(e.target.value)}
//             className="border p-1 w-20 rounded"
//           />
//         </div>
//       </div> */}

//       <div className="flex flex-wrap gap-2 items-center">
//           <label>Start Year:</label>
//           <input
//             type="number"
//             value={inputStartYear}
//             onChange={(e) => setInputStartYear(e.target.value)}
//             className="border p-1 w-20 rounded"
//           />
//         </div>
//         <div className="flex items-center gap-2">
//           <label>End Year:</label>
//           <input
//             type="number"
//             value={inputEndYear}
//             onChange={(e) => setInputEndYear(e.target.value)}
//             className="border p-1 w-20 rounded"
//           />
//         </div>
//         <button 
//           className="btn btn-sm btn-primary" 
//           onClick={handleApplyYearRange}
//         >
//           Apply Years
//         </button>

//       {/* Dataset Source Selector */}
//       {/* <div className="mb-3">
//         <label className="form-label fw-bold me-2">Dataset source:</label>
//         <select
//           className="form-select form-select-sm d-inline-block w-auto"
//           value={datamode}
//           onChange={(e) => setDataMode(e.target.value)}
//         >
//           <option value="default">Default dataset</option>
//           <option value="upload">Uploaded dataset</option>
//         </select>
//       </div> */}

//       {/* Dataset Mode Selector */}
//       {/* <div className="mb-3">
//         <Link to="/manipulate" className="btn btn-sm btn-primary">
//           <button className="btn btn-sm btn-primary">Upload New Data</button>
//         </Link>
//       </div> */}

//       <div className="row">
//         {/*col-12 col-lg-6*/}
//         <div className="col-12 col-lg-6">
//           <IndicesViewer
//             indexName={indexName}
//             datasetName={activeDataset}
//             country={country}
//             province={province}   
//             startYear={inputStartYear}
//             endYear={inputEndYear}     
//           />
//         </div>
//         <div className="col-12 col-lg-6">
//           <GridMapViewer
//             indexName={indexName}
//             mode={mode}
//             setMode={setMode}
//             datasetName={activeDataset}
//             country={country}
//             province={province}   
//             startYear={startYear}
//             endYear={endYear}    
//           />
//         </div>
//       </div>
//     </div>
//   );
// }
