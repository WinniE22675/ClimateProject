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
export default function IndicesViewer({ indexName, datasetName, country, province, startYear, endYear, availableIndices, spiThreshold, setSpiThreshold }) {
  const [allData, setAllData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [allMonthlyData, setAllMonthlyData] = useState([]);
  const [monthlyData, setMonthlyData] = useState([]);
  const [unit, setUnit] = useState("");
  // const [startYear, setStartYear] = useState("1960");
  // const [endYear, setEndYear] = useState("2024");
  const [windowSize, setWindowSize] = useState(21);

  // state: loading / error / no-data
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [noData, setNoData] = useState(false);

  const baseIndexName = getBaseIndexName(indexName);

  const [allSPIData, setallSPIData] = useState([]);
  const [spiSeries, setSpiSeries] = useState([]);

  const isSPI = baseIndexName.startsWith("SPI");

  // const [spiThreshold, setSpiThreshold] = useState(1);
  const [spiPrepared, setSpiPrepared] = useState([]);

  const safeFormat = (v) => (Number.isFinite(v) ? v.toFixed(2) : "–");

  useEffect(() => {
    setLoading(true);
    setError(null);
    setNoData(false);

    if (!availableIndices || availableIndices.length === 0) return;
    if (!availableIndices.includes(indexName)) return;

    const apiBase = "http://localhost:8000";
    // const basePath = datamode === "upload" ? `${apiBase}/output` : "/data";
    const datasetPath =
      datasetName === "default" ? "/data" : `${apiBase}/output/${datasetName}`; //{datasetName}  `${apiBase}/output/dataset_${datasetId}`;

    const cacheKey = Date.now();

    // Determine if we are looking at a province or the national overview
    const area = province ? province : "overview";
    // const baseIndexName = indexName; // Adjust this if your base name logic differs

    // New Path Structure: datasetPath / country / area / indexName / indices / [annual|seasonal]
    const annualPath = `${datasetPath}/${country}/${area}/${baseIndexName}/indices/annual/${baseIndexName}_timeseries.json?v=${cacheKey}`;
    const seasonalPath = `${datasetPath}/${country}/${area}/${baseIndexName}/indices/seasonal/${baseIndexName}_seasonal.json?v=${cacheKey}`;
    
    Promise.all([
      fetch(annualPath).then((res) => {
        if (!res.ok) throw new Error("Annual fetch failed");
        return res.json();
      }),
      fetch(seasonalPath).then((res) => {
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
        // setUnit(annual.metadata.unit || "");
        let apiUnit = annual.metadata.unit || "";
        if (baseIndexName.startsWith("SPI")) {
          // Force unit to be the base SPI name (e.g., "SPI6")
          apiUnit = baseIndexName;
        }
        setUnit(apiUnit);

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
  }, [indexName, baseIndexName, datasetName, country, province, startYear, endYear]); //datamode,

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
      (d) => d.year >= parseInt(startYear) && d.year <= parseInt(endYear)
    );
    setFilteredData(f);
  }, [allData, startYear, endYear]);

  const movingAvgData = computeMovingAverage(filteredData, windowSize);
  const mergedData = filteredData.map((d, i) => ({
    year: d.year,
    annual: d.value,
    yearAvg: movingAvgData[i]?.yearAvg ?? null,
  }));

  useEffect(() => {
    if (!allMonthlyData || allMonthlyData.length === 0) return; // check sure no data
    const start = parseInt(startYear);
    const end = parseInt(endYear);
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
  }, [allMonthlyData, startYear, endYear]);

  // useEffect(() => {
  //   if (!allSPIData || allSPIData.length === 0) return;

  //   const start = parseInt(startYear);
  //   const end = parseInt(endYear);

  //   const filtered = allSPIData.filter((d) => d.year >= start && d.year <= end);

  //   setSpiSeries(filtered);
  // }, [allSPIData, startYear, endYear]);
  useEffect(() => {
    if (!allSPIData?.length) return;

    const start = new Date(`${startYear}-01-01`);
    const end = new Date(`${endYear}-12-31`);

    const filtered = allSPIData.filter((d) => {
      const t = new Date(d.date);
      return t >= start && t <= end;
    });

    setSpiSeries(filtered);
  }, [allSPIData, startYear, endYear]);


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
      
      {/* Select average window size */}
      {!isSPI && (
      <div className="flex gap-2 items-center mb-2">
        <label>Year Average Window:</label>
        <input
          type="number"
          value={windowSize}
          onChange={(e) => setWindowSize(parseInt(e.target.value))}
          className="border p-1 w-20 rounded"
        />
      </div>
      )}

      {isSPI && (
        <div className="flex gap-2 items-center mb-2">
          <label>SPI Threshold (for event):</label>
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
        <>
          <ResponsiveContainer width="100%" height={250}>
            {/* Added margin left to align nicely */}
            <BarChart data={spiSeries}>
              <XAxis dataKey="date" interval="preserveStartEnd" minTickGap={0} tick={{ fontSize: 11 }} />
              <YAxis
                width={70}
                domain={[-3, 3]}
                label={{
                  value: unit,
                  angle: -90,
                  position: "insideLeft",
                }}
              />
              <Tooltip formatter={safeFormat} />
              <ReferenceLine y={0} stroke="#000" />
              <ReferenceLine y={spiThreshold} stroke="#1f77b4" strokeDasharray="4 4" />
              <ReferenceLine y={-spiThreshold} stroke="#d62728" strokeDasharray="4 4" />
              <Bar dataKey="spi">
                {spiSeries.map((d, i) => (
                  <Cell key={i} fill={resolveSPIColor(d, indexName)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>

          <div className="d-flex justify-content-center align-items-center gap-3 mb-3 small text-muted w-100">
            <span className="d-flex align-items-center gap-2">
              <span style={{ width: 12, height: 12, backgroundColor: "#bdbdbd", display: "inline-block", borderRadius: "2px" }}></span>
              Normal
            </span>
            
            {!indexName.includes("Flood") && (
              <span className="d-flex align-items-center gap-2">
                <span style={{ width: 12, height: 12, backgroundColor: "#d62728", display: "inline-block", borderRadius: "2px" }}></span>
                Drought (≤ -{spiThreshold})
              </span>
            )}
            
            {!indexName.includes("Drought") && (
              <span className="d-flex align-items-center gap-2">
                <span style={{ width: 12, height: 12, backgroundColor: "#1f77b4", display: "inline-block", borderRadius: "2px" }}></span>
                Wet / Flood (≥ {spiThreshold})
              </span>
            )}
          </div>
        </>
      ) : (
        <div className="mb-3">
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={mergedData} margin={{ left: 5, right: 20 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="year" interval="preserveStartEnd" minTickGap={0} allowDecimals={false} />
            <YAxis
              width={70}
              label={{ value: unit, angle: -90, position: "insideLeft" }}
              // padding={{ top: 35 }}
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
        </div>
      )}

      {/* Monthly Graph 100%*/}
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={monthlyData} margin={{ left: 5, right: 20 }}>
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
            name={`${baseIndexName} Seasonal Cycle (${startYear}-${endYear})`}
            dot
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}