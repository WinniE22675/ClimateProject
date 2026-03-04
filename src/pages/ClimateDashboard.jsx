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
  const [activeDataset, setActiveDataset] = useState("default");
  const [province, setProvince] = useState("");

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
      {/* <h2 className="text-xl font-bold whitespace-nowrap">Climate Change</h2> */}
      {/* Controls Container bg-light rounded shadow-sm*/}
      <div className="d-flex align-items-end gap-3 p-2">
        {/* 2. Dataset Selector (รวม Default) */}
        <div>
          <label className="form-label small fw-bold text-muted ">
            Dataset Source
          </label>
          {/* <select
            className="form-select form-select-sm"
            value={datasetId}
            onChange={(e) => setDatasetId(e.target.value)}
          >
            <option value="default">Default Dataset</option>
            <option value="1">Dataset 1</option>
            <option value="2">Dataset 2</option>
            <option value="3">Dataset 3</option>
            <option value="4">Dataset 4</option>
          </select> */}
          <select
            className="form-select form-select-sm"
            value={activeDataset}
            onChange={(e) => setActiveDataset(e.target.value)}
          >
            <option value="default">Default Dataset</option>

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

        {/* 1. Country Selector */}
        <div>
          <label className="form-label small fw-bold text-muted">Country</label>
          <select
            className="form-select form-select-sm"
            value={country}
            onChange={(e) => {
              setCountry(e.target.value)
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

        {country === "Thailand" && (
          <div>
            <label className="form-label small fw-bold text-muted">Province</label>
            <select
              className="form-select form-select-sm"
              value={province}
              onChange={(e) => setProvince(e.target.value)}
            >
              <option value="">Whole Country</option> {/* Default option */}
              {provinces.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="">
          <Link to="/manipulate" className="btn btn-sm btn-primary">
            <button className="btn btn-sm btn-primary">Upload New Data</button>
          </Link>
        </div>
      </div>

      {/* <div>
        <label className="form-label small fw-bold text-muted">
          Climate Index
        </label>
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
      </div> */}
      <div className="flex gap-2 items-center">
        <label>Index:</label>
        <select
          value={indexName}
          onChange={(e) => setIndexName(e.target.value)}
          className="border p-1 rounded"
        >
          {ALL_INDICES.map((idx) => (
            <option key={idx} value={idx}>
              {idx}
            </option>
          ))}
        </select>
      </div>

      {/* Dataset Source Selector */}
      {/* <div className="mb-3">
        <label className="form-label fw-bold me-2">Dataset source:</label>
        <select
          className="form-select form-select-sm d-inline-block w-auto"
          value={datamode}
          onChange={(e) => setDataMode(e.target.value)}
        >
          <option value="default">Default dataset</option>
          <option value="upload">Uploaded dataset</option>
        </select>
      </div> */}

      {/* Dataset Mode Selector */}
      {/* <div className="mb-3">
        <Link to="/manipulate" className="btn btn-sm btn-primary">
          <button className="btn btn-sm btn-primary">Upload New Data</button>
        </Link>
      </div> */}

      <div className="row">
        {/*col-12 col-lg-6*/}
        <div className="col-12 col-lg-6">
          <IndicesViewer
            indexName={indexName}
            // setIndexName={setIndexName}
            // datamode={datamode} //"default"
            datasetName={activeDataset} //datasetId
            country={country}
          />
        </div>
        {/*col-12 col-lg-6*/}
        <div className="col-12 col-lg-6">
          <GridMapViewer
            indexName={indexName}
            mode={mode}
            setMode={setMode}
            // datamode={datamode} //"default"
            datasetName={activeDataset} //datasetId
            country={country}
          />
        </div>
      </div>
    </div>
  );
}
