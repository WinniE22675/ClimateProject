import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend as ReLegend,
  BarChart,
  Bar,
  Cell,
  ReferenceLine,
} from "recharts";

// Separate Index base name from Index name
function getBaseIndexName(name) {
  const match = name.match(/(SPI\d+)/);
  if (match) {
    return match[1]; // such as SPI6_Drought_Frequency >> SPI6
  }
  return name; // such as PRCPTOT >> PRCPTOT
}

// Convert monthly SPI data to chart-ready format
function prepareSPIMonthlyData(rawMonthly) {
  return rawMonthly
    // .filter((d) => d.value !== null)
    .filter((d) => Number.isFinite(d.value))
    .map((d) => ({
      date: `${d.year}-${String(d.month).padStart(2, "0")}`,
      spi: d.value,
      color: "#bdbdbd", // default (neutral)
    }));
}

// Assign colors for drought / wet events (>= 2 consecutive months)
function assignSPIEventColors(data, threshold = 1) {
  // const result = [...data];
  const result = data.map((d) => ({ ...d }));
  let i = 0;

  while (i < result.length) {
    const v = result[i].spi;

    // Drought
    if (v <= -threshold) {
      let start = i;
      while (i < result.length && result[i].spi <= -threshold) i++;
      if (i - start >= 2) {
        for (let j = start; j < i; j++) {
          result[j].color = "#d62728"; // red
        }
      }
    }
    // Wet
    else if (v >= threshold) {
      let start = i;
      while (i < result.length && result[i].spi >= threshold) i++;
      if (i - start >= 2) {
        for (let j = start; j < i; j++) {
          result[j].color = "#1f77b4"; // blue
        }
      }
    } else {
      i++;
    }
  }

  return result;
}

function resolveSPIColor(d, indexName) {
  if (indexName.includes("Drought")) {
    return d.color === "#d62728" ? "#d62728" : "#bdbdbd";
  }

  if (indexName.includes("Flood")) {
    return d.color === "#1f77b4" ? "#1f77b4" : "#bdbdbd";
  }

  return d.color; // SPI ปกติ
}


// , datamode setIndexName,
export default function IndicesViewer({ indexName, datasetName, country }) {
  const [allData, setAllData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [allMonthlyData, setAllMonthlyData] = useState([]);
  const [monthlyData, setMonthlyData] = useState([]);
  const [unit, setUnit] = useState("");
  const [startDate, setStartDate] = useState("1960");
  const [endDate, setEndDate] = useState("2024");
  const [windowSize, setWindowSize] = useState(21);

  // state: loading / error / no-data
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [noData, setNoData] = useState(false);

  const baseIndexName = getBaseIndexName(indexName);

  const [allSPIData, setallSPIData] = useState([]);
  const [spiSeries, setSpiSeries] = useState([]);

  const isSPI = baseIndexName.startsWith("SPI");

  const [spiThreshold, setSpiThreshold] = useState(1);
  const [spiPrepared, setSpiPrepared] = useState([]);

  const safeFormat = (v) => (Number.isFinite(v) ? v.toFixed(2) : "–");
  

  // useEffect(() => {
  //   const apiBase = "http://localhost:8000";
  //   const basePath = datamode === "upload" ? `${apiBase}/output` : "/data";

  //   // annual
  //   fetch(`${basePath}/indices/annual/${baseIndexName}_timeseries.json`)
  //     .then((res) => res.json())
  //     .then((d) => {
  //       setAllData(d.data);
  //       setFilteredData(d.data);
  //       setUnit(d.metadata.unit || "");
  //       if (d.data?.length > 0) {
  //         setStartDate(String(d.data[0].year));
  //         setEndDate(String(d.data[d.data.length - 1].year));
  //       }
  //     });

  //   // monthly
  //   fetch(`${basePath}/indices/monthly/${baseIndexName}_monthly.json`)
  //     .then((res) => res.json())
  //     .then((d) => {
  //       setAllMonthlyData(d.data);
  //       setUnit(d.metadata.unit || "");
  //     });
  // }, [indexName, datamode, baseIndexName]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setNoData(false);

    const apiBase = "http://localhost:8000";
    // const basePath = datamode === "upload" ? `${apiBase}/output` : "/data";
    const datasetPath =
      datasetName === "default" ? "/data" : `${apiBase}/output/${datasetName}`; //{datasetName}  `${apiBase}/output/dataset_${datasetId}`;

    const cacheKey = Date.now();

    const annualPath = province
    ? `${datasetPath}/indices/annual/${country}/${province}/${baseIndexName}_timeseries.json?v=${cacheKey}`
    : `${datasetPath}/indices/annual/${country}/${baseIndexName}_timeseries.json?v=${cacheKey}`;

  const seasonalPath = province
    ? `${datasetPath}/indices/seasonal/${country}/${province}/${baseIndexName}_seasonal.json?v=${cacheKey}`
    : `${datasetPath}/indices/seasonal/${country}/${baseIndexName}_seasonal.json?v=${cacheKey}`;

    Promise.all([
      fetch(
        `${datasetPath}/indices/annual/${baseIndexName}_${country}_timeseries.json?v=${cacheKey}` //basePath
      ).then((res) => {
        if (!res.ok) throw new Error("Annual fetch failed");
        return res.json();
      }),
      fetch(
        `${datasetPath}/indices/monthly/${baseIndexName}_${country}_monthly.json?v=${cacheKey}`
      ).then((res) => {
        if (!res.ok) throw new Error("Monthly fetch failed");
        return res.json();
      }),
    ])
      .then(([annual, monthly]) => {
        if (!annual?.data?.length) {
          setNoData(true);
          return;
        }

        setAllData(annual.data);
        setFilteredData(annual.data);
        setUnit(annual.metadata.unit || "");
        setAllMonthlyData(monthly?.data || []);

        if (baseIndexName.startsWith("SPI") && monthly?.data?.length) {
          const prepared = prepareSPIMonthlyData(monthly.data);
          // const colored = assignSPIEventColors(prepared);
          setSpiPrepared(prepared);
          // setallSPIData(colored);
        }
      })
      .catch((err) => {
        setError(err.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [indexName, baseIndexName, datasetName, country]); //datamode,

  // Help Threshold change
  useEffect(() => {
    if (!spiPrepared.length) return;

    const colored = assignSPIEventColors(spiPrepared, spiThreshold);
    setallSPIData(colored);
  }, [spiPrepared, spiThreshold]);

  function computeMovingAverage(data, window = 21) {
    if (!data || data.length === 0) return [];
    return data.map((d, i) => {
      const start = Math.max(0, i - Math.floor(window / 2));
      const end = Math.min(data.length, i + Math.floor(window / 2) + 1); // not count end then +1
      const slice = data.slice(start, end);
      const avg = slice.reduce((sum, d) => sum + d.value, 0) / slice.length;
      return { year: d.year, yearAvg: avg };
    });
  }

  useEffect(() => {
    const f = allData.filter(
      (d) => d.year >= parseInt(startDate) && d.year <= parseInt(endDate)
    );
    setFilteredData(f);
  }, [allData, startDate, endDate]);

  const movingAvgData = computeMovingAverage(filteredData, windowSize);
  const mergedData = filteredData.map((d, i) => ({
    year: d.year,
    annual: d.value,
    yearAvg: movingAvgData[i]?.yearAvg ?? null,
  }));

  useEffect(() => {
    if (!allMonthlyData || allMonthlyData.length === 0) return; // check sure no data
    const start = parseInt(startDate);
    const end = parseInt(endDate);
    const filtered = allMonthlyData.filter(
      (d) => d.year >= start && d.year <= end
    );

    let monthlyAgg = [];
    for (let m = 1; m <= 12; m++) {
      const vals = filtered.filter((d) => d.month === m).map((d) => d.value);
      if (vals.length > 0) {
        const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
        monthlyAgg.push({ month: m, value: avg });
      }
    }
    setMonthlyData(monthlyAgg);
  }, [allMonthlyData, startDate, endDate]);

  // useEffect(() => {
  //   if (!allSPIData || allSPIData.length === 0) return;

  //   const start = parseInt(startDate);
  //   const end = parseInt(endDate);

  //   const filtered = allSPIData.filter((d) => d.year >= start && d.year <= end);

  //   setSpiSeries(filtered);
  // }, [allSPIData, startDate, endDate]);
  useEffect(() => {
    if (!allSPIData?.length) return;

    const start = new Date(`${startDate}-01-01`);
    const end = new Date(`${endDate}-12-31`);

    const filtered = allSPIData.filter((d) => {
      const t = new Date(d.date);
      return t >= start && t <= end;
    });

    setSpiSeries(filtered);
  }, [allSPIData, startDate, endDate]);


  // const formatTooltip = (value) =>
  //   ["SPI3", "SPI6", "SPI9", "SPI12"].includes(indexName)
  //     ? Number(value).toFixed(4)
  //     : Number(value).toFixed(2);

  //flex-wrap >> if not enought space, will new line
  //items-center >> align vertical center

  //strokeDasharray="3 3" >> 3px line 3px space

  if (loading) return <div>Loading...</div>;
  if (error) return <div style={{ color: "red" }}>Error: {error}</div>;
  if (noData) return <div>No data available for this index.</div>;

  return (
    <div className="flex flex-wrap gap-2 items-center">
      {/* Select Indices */}
      {/* <div className="flex gap-2 items-center">
        <label>Index:</label>
        <select
          value={indexName}
          onChange={(e) => setIndexName(e.target.value)}
          className="border p-1 rounded"
        >
          {[
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
          ].map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
      </div> */}

      {/* Select Start/End Year */}
      <div className="flex flex-wrap gap-2 items-center">
        <div className="flex items-center gap-2">
          <label>Start Year :</label>
          <input
            type="number"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="border p-1 w-20 rounded"
          />
        </div>
        <div className="flex items-center gap-2">
          <label>End Year :</label>
          <input
            type="number"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="border p-1 w-20 rounded"
          />
        </div>
      </div>

      {/* Select average window size */}
      <div className="flex gap-2 items-center">
        <label>Year Average Window:</label>
        <input
          type="number"
          value={windowSize}
          onChange={(e) => setWindowSize(parseInt(+e.target.value))}
          className="border p-1 w-20 rounded"
        />
      </div>

      {isSPI && (
        <div className="flex gap-2 items-center">
          <label>SPI Threshold:</label>
          <input
            type="number"
            step="0.1"
            value={spiThreshold}
            onChange={(e) => setSpiThreshold(parseFloat(e.target.value))}
            className="border p-1 w-20 rounded"
          />
        </div>
      )}

      {isSPI ? (
        // <SPIBarChart data={spiMonthlyData} />
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={spiSeries}>
            {/* <CartesianGrid strokeDasharray="3 3" /> */}

            <XAxis dataKey="date" interval="preserveStartEnd" tick={{ fontSize: 11 }} />

            <YAxis
              width={70}
              domain={[-3, 3]}
              label={{
                value: "SPI",
                angle: -90,
                position: "insideLeft",
              }}
            />

            {/* <Tooltip formatter={(v) => v.toFixed(2)} /> */}
            <Tooltip formatter={safeFormat} />

            {/* Reference lines */}
            <ReferenceLine y={0} stroke="#000" />
            {/* <ReferenceLine y={1} stroke="#1f77b4" strokeDasharray="4 4" />
            <ReferenceLine y={-1} stroke="#d62728" strokeDasharray="4 4" /> */}
            <ReferenceLine
              y={spiThreshold}
              stroke="#1f77b4"
              strokeDasharray="4 4"
            />
            <ReferenceLine
              y={-spiThreshold}
              stroke="#d62728"
              strokeDasharray="4 4"
            />

            <Bar dataKey="spi">
              {spiSeries.map((d, i) => (
                <Cell key={i} fill={resolveSPIColor(d, indexName)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={mergedData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="year" interval={9} allowDecimals={false} />
            <YAxis
              width={70}
              label={{ value: unit, angle: -90, position: "insideLeft" }}
            />
            <Tooltip formatter={(value) => value.toFixed(2)} />
            <ReLegend />
            <Line
              dataKey="annual"
              stroke="#000"
              name={`${baseIndexName} Annual Avg`}
              dot={false}
            />
            <Line
              dataKey="yearAvg"
              stroke="#800080"
              name={`${windowSize}-Year Avg`}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}

      {/* Annual Graph */}
      {/* <ResponsiveContainer width="100%" height={250}>
        <LineChart data={mergedData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="year" />
          <YAxis label={{ value: unit, angle: -90, position: "insideLeft" }} />
          <Tooltip formatter={(value) => value.toFixed(2)} />
          <ReLegend />
          <Line
            dataKey="annual"
            stroke="#000"
            name={`${baseIndexName} Annual Avg`}
            dot={false}
          />
          <Line
            dataKey="yearAvg"
            stroke="#800080"
            name={`${windowSize}-Year Avg`}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer> */}

      {/* Monthly Graph 100%*/}
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={monthlyData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="month"
            ticks={[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]}
            interval={0}
            tick={{ textAnchor: "end" }}
            tickFormatter={(v) => {
              const short = [
                "J",
                "F",
                "M",
                "A",
                "M",
                "J",
                "J",
                "A",
                "S",
                "O",
                "N",
                "D",
              ];
              const full = [
                "JAN",
                "FEB",
                "MAR",
                "APR",
                "MAY",
                "JUN",
                "JUL",
                "AUG",
                "SEP",
                "OCT",
                "NOV",
                "DEC",
              ];
              return window.innerWidth < 450 ? short[v - 1] : full[v - 1]; // window.innerWidth is now width if less than 450px use short | v-1 because month start 1 but index start 0
            }}
          />
          <YAxis width={70} tickFormatter={(v) => (isSPI ? v.toFixed(3): v)} label={{ value: unit, angle: -90, position: "insideLeft" }} />
          <Tooltip formatter={(value) => value.toFixed(2)} />
          <ReLegend />
          <Line
            dataKey="value"
            stroke="#0077cc"
            name={`${baseIndexName} Seasonal Cycle (${startDate}-${endDate})`}
            dot
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
//value: unit