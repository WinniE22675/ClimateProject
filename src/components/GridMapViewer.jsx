import { useEffect, useState, useMemo, useRef } from "react";
import { MapContainer, GeoJSON, Circle, useMap } from "react-leaflet";
import L from "leaflet";
import * as d3 from "d3";
import * as turf from "@turf/turf"; // help compute centroid
import Legend from "./Legend";
import MapViewUpdater from "./MapViewUpdater";

// function createMask(sea, country) {
//   return turf.difference(sea, country);
// }

// function BoundaryMaskLayer({ mask }) {
//   const map = useMap();

//   useEffect(() => {
//     if (!mask) return;

//     if (!map.getPane("mask")) {
//       map.createPane("mask");
//       map.getPane("mask").style.zIndex = 1000;
//       map.getPane("mask").style.pointerEvents = "none";
//     }

//     const layer = L.geoJSON(mask, {
//       pane: "mask",
//       style: {
//         fillColor: "#cccccc",
//         fillOpacity: 0.6,
//         weight: 0,
//         interactive: false,
//       },
//     }).addTo(map);

//     return () => map.removeLayer(layer);
//   }, [map, mask]);

//   return null;
// }

// function BoundaryLayer({ data, type }) {
//   const map = useMap();

//   useEffect(() => {
//     if (!data) return;

//     if (!map.getPane("boundary")) {
//       map.createPane("boundary");
//       map.getPane("boundary").style.zIndex = 500;
//       map.getPane("boundary").style.pointerEvents = "none";
//     }

//     const layer = L.geoJSON(data, {
//       pane: "boundary",
//       style: {
//         color: "black",
//         weight: type === "country" ? 2 : 0.5,
//         fillOpacity: 0,
//         opacity: type === "country" ? 1 : 0.4, // dim SEA
//         interactive: false,
//       },
//     }).addTo(map);

//     return () => map.removeLayer(layer);
//   }, [map, data, type]);

//   return null;
// }

function BoundaryMaskLayer({ mask }) {
  const map = useMap();

  useEffect(() => {
    if (!mask) return;

    if (!map.getPane("mask")) {
      map.createPane("mask");
      map.getPane("mask").style.zIndex = 500; // on top of everything
      map.getPane("mask").style.pointerEvents = "none";
    }

    const layer = L.geoJSON(mask, {
      pane: "mask",
      style: {
        fillColor: "#dddddd", // background color
        fillOpacity: 1, // IMPORTANT: must be 1
        weight: 0,
        interactive: false,
      },
    }).addTo(map);

    return () => map.removeLayer(layer);
  }, [map, mask]);

  return null;
}


function BoundaryLayer({ data }) {
  const map = useMap();
  useEffect(() => {
    if (!data) return;
    if (!map.getPane("boundary")) {
      map.createPane("boundary");
      map.getPane("boundary").style.zIndex = 600; // boundary layer more than base map but less than interactive layer
      map.getPane("boundary").style.pointerEvents = "none"; // not block mouse event
    }
    const layer = L.geoJSON(data, {
      pane: "boundary",
      style: {
        interactive: false,
        color: "black",
        weight: 0.5,
        fillOpacity: 0,
      },
    }).addTo(map);
    return () => {
      map.removeLayer(layer); // each data change
    };
  }, [map, data]);
  return null;
}

export default function GridMapViewer({
  indexName,
  mode,
  setMode,
  datasetName,
  country,
  province,
  startYear,
  endYear
}) {
  const [gridData, setGridData] = useState({ actual: null, trend: null });
  const [scales, setScales] = useState({ actual: null, trend: null });
  const [binsAll, setBinsAll] = useState({ actual: [], trend: [] });
  const [showSig, setShowSig] = useState(true);
  const [unit, setUnit] = useState("");
  const [boundaryData, setBoundaryData] = useState(null);
  const layersRef = useRef({ actual: null, trend: null });

  // state: loading / error / no-data
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [noData, setNoData] = useState(false);

  const [maskData, setMaskData] = useState(null);

  const [isGenerating, setIsGenerating] = useState(false);

  // const [seaBoundary, setSeaBoundary] = useState(null);
  // const [countryBoundary, setCountryBoundary] = useState(null);
  // const [maskData, setMaskData] = useState(null);

  // useEffect(() => {
  //   setGridData({ actual: null, trend: null });
  //   setScales({ actual: null, trend: null });
  //   setBinsAll({ actual: [], trend: [] });
  //   setUnit("");
  //   const apiBase = "http://localhost:8000";
  //   const basePath = datamode === "upload" ? `${apiBase}/output` : "/data";

  //   Promise.all([
  //     fetch(
  //       `${basePath}/maps_grid/actual/${indexName}_actual_grid.geojson`
  //     ).then((res) => res.json()),
  //     fetch(`${basePath}/maps_grid/trend/${indexName}_trend_grid.geojson`).then(
  //       (res) => res.json()
  //     ),
  //   ]).then(([actualData, trendData]) => {
  //     setGridData({ actual: actualData, trend: trendData });
  //     const u = actualData.metadata?.unit || trendData.metadata?.unit || "";
  //     setUnit(u);
  //   });
  // }, [indexName, datamode]);

  // user-defined legend range (null = auto)
  const [legendRange, setLegendRange] = useState({
    actual: { min: null, max: null },
    trend: { min: null, max: null },
  });

  const COUNTRY_VIEW = {
    Thailand: {
      center: [15.0, 101.0],
      zoom: 5,
    },
    Vietnam: {
      center: [16.0, 107.5],
      zoom: 6,
    },
    Laos: {
      center: [18.0, 104.0],
      zoom: 6,
    },
    Cambodia: {
      center: [12.5, 104.9],
      zoom: 6,
    },
    Myanmar: {
      center: [20.5, 96.0],
      zoom: 5,
    },
    Malaysia: {
      center: [4.5, 102.0],
      zoom: 6,
    },
    Philippines: {
      center: [12.5, 122.0],
      zoom: 5,
    },
    Indonesia: {
      center: [-2.5, 118.0],
      zoom: 5,
    },
    Singapore: {
      center: [1.35, 103.8],
      zoom: 9,
    },
    Brunei: {
      center: [4.5, 114.7],
      zoom: 7,
    },
    "Timor-Leste": {
      center: [-8.8, 125.9],
      zoom: 7,
    },

    // Default regional view (Southeast Asia)
    SEA: {
      center: [8.0, 117.5],
      zoom: 4,
    },
  };

  // const mapView =
  //   country && COUNTRY_VIEW[country]
  //     ? COUNTRY_VIEW[country]
  //     : COUNTRY_VIEW.default;

  const mapView = COUNTRY_VIEW[country] || COUNTRY_VIEW.SEA;

  useEffect(() => {
    setLoading(true);
    setError(null);
    setNoData(false);
    setIsGenerating(false);

    setGridData({ actual: null, trend: null });
    setScales({ actual: null, trend: null });
    setBinsAll({ actual: [], trend: [] });
    setUnit("");

    const NO_TREND_INDICES = [
      "pr",
      "tmax",
      "tmin",
    ];

    const supportsTrend = !NO_TREND_INDICES.includes(indexName);

    if (!supportsTrend && mode === "trend") {
      setMode("actual");
    }

    let isMounted = true;

    const fetchAllMaps = async () => {
      setLoading(true);
      setError(null);
      setNoData(false);
      setIsGenerating(false);

      const apiBase = "http://localhost:8000";
      // Determine base path based on dataset type
      const datasetPath = datasetName === "default" ? "/data" : `${apiBase}/output/${datasetName}`;
      
      // Determine area (use "overview" for country-level data)
      const area = province ? province : "overview";
      const cacheKey = Date.now();

      // Construct file paths based on the domain-centric structure
      const actualGridPath = `${datasetPath}/${country}/${area}/${indexName}/maps_grid/actual/${startYear}_${endYear}_actual_grid.geojson?v=${cacheKey}`;
      const trendGridPath = `${datasetPath}/${country}/${area}/${indexName}/maps_grid/trend/${startYear}_${endYear}_trend_grid.geojson?v=${cacheKey}`;

      // Helper function to handle fetch and return 404 gracefully instead of breaking
      const fetchGracefully = async (url) => {
        try {
          const res = await fetch(url);
          if (res.status === 404) return { status: 404, data: null };
          if (!res.ok) throw new Error(`HTTP Error: ${res.status}`);
          return { status: 200, data: await res.json() };
        } catch (err) {
          throw new Error(`Fetch failed for ${url}: ${err.message}`);
        }
      };

      try {
        // --- Step 1: Initial Fetch ---
        const requests = [fetchGracefully(actualGridPath)];
        if (supportsTrend) {
          requests.push(fetchGracefully(trendGridPath));
        }

        let results = await Promise.all(requests);
        let actualRes = results[0];
        let trendRes = supportsTrend ? results[1] : { status: 200, data: null };

        // --- Step 2: Lazy Generation Check ---
        // If file doesn't exist (404), ask backend to generate it
        if (actualRes.status === 404 || (supportsTrend && trendRes.status === 404)) {
          setIsGenerating(true);

          // Trigger generation API
          const generateRes = await fetch(`${apiBase}/api/maps/generate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              indexName,
              datasetName,
              country,
              province: province || null, // Send null if empty string
              startYear: parseInt(startYear, 10),
              endYear: parseInt(endYear, 10),
              supportsTrend
            }),
          });

          if (!generateRes.ok) {
            throw new Error("Backend failed to generate map data.");
          }

          // --- Step 3: Re-fetch after generation ---
          const newCacheKey = Date.now(); 
          const retryActualPath = `${datasetPath}/${country}/${area}/${indexName}/maps_grid/actual/${startYear}_${endYear}_actual_grid.geojson?v=${newCacheKey}`;
          const retryTrendPath = `${datasetPath}/${country}/${area}/${indexName}/maps_grid/trend/${startYear}_${endYear}_trend_grid.geojson?v=${newCacheKey}`;

          const retryRequests = [fetchGracefully(retryActualPath)];
          if (supportsTrend) retryRequests.push(fetchGracefully(retryTrendPath));

          const retryResults = await Promise.all(retryRequests);
          actualRes = retryResults[0];
          trendRes = supportsTrend ? retryResults[1] : { status: 200, data: null };

          if (actualRes.status === 404 || (supportsTrend && trendRes.status === 404)) {
            throw new Error("Map generation succeeded, but files are still missing on the server.");
          }
        }

        // --- Step 4: Update State ---
        if (isMounted) {
          const actualData = actualRes.data;
          const trendData = trendRes.data;

          // Check if data is truly empty
          if (!actualData?.features?.length && (!supportsTrend || !trendData?.features?.length)) {
            setNoData(true);
          } else {
            setGridData({ actual: actualData, trend: trendData });
            // Extract unit from metadata
            const u = actualData?.metadata?.unit || trendData?.metadata?.unit || "";
            setUnit(u);
          }
        }

      } catch (err) {
        if (isMounted) {
          console.error("Map Load Error:", err);
          setError(err.message);
        }
      } finally {
        if (isMounted) {
          setIsGenerating(false);
          setLoading(false);
        }
      }
    };

    if (startYear && endYear && indexName && datasetName && country) {
      fetchAllMaps();
    }

    return () => { isMounted = false; };
  }, [indexName, datasetName, country, province, startYear, endYear]);

  // Define which dataset to render based on the current mode
  const currentMapData = mode === "trend" ? gridData.trend : gridData.actual;

    // const apiBase = "http://localhost:8000";
    // // const basePath = datamode === "upload" ? `${apiBase}/output` : "/data";
    // const datasetPath =
    //   datasetName === "default" ? "/data" : `${apiBase}/output/${datasetName}`;

    // const cacheKey = Date.now();

    // const area = province ? province : "overview";

    // // New Path Structure: datasetPath / country / area / indexName / maps_grid / [actual|trend] / {start}_{end}_[type]_grid.geojson
    // const actualGridPath = `${datasetPath}/${country}/${area}/${indexName}/maps_grid/actual/${startYear}_${endYear}_actual_grid.geojson?v=${cacheKey}`;
    // const trendGridPath = `${datasetPath}/${country}/${area}/${indexName}/maps_grid/trend/${startYear}_${endYear}_trend_grid.geojson?v=${cacheKey}`;

    // const requests = [
    //   fetch(
    //     `${datasetPath}/maps_grid/actual/${indexName}_actual_grid.geojson?v=${cacheKey}`
    //   ).then((res) => {
    //     if (!res.ok) throw new Error("Actual grid fetch failed");
    //     return res.json();
    //   }),
    // ];

    // if (supportsTrend) {

    //   requests.push(
    //     fetch(
    //       `${datasetPath}/maps_grid/trend/${indexName}_trend_grid.geojson?v=${cacheKey}`
    //     ).then((res) => {
    //     if (!res.ok) throw new Error("Trend grid fetch failed");
    //     return res.json();
    //   }),
    //   );
    // }

    // Promise.all([
    //   fetch(
    //     `${datasetPath}/maps_grid/actual/${indexName}_actual_grid.geojson?v=${cacheKey}`
    //   ).then((res) => {
    //     if (!res.ok) throw new Error("Actual grid fetch failed");
    //     return res.json();
    //   }),
    //   fetch(
    //     `${datasetPath}/maps_grid/trend/${indexName}_trend_grid.geojson?v=${cacheKey}`
    //   ).then((res) => {
    //     if (!res.ok) throw new Error("Trend grid fetch failed");
    //     return res.json();
    //   }),
    // ])
  //   Promise.all(requests)
  //     .then(([actualData, trendData]) => {
  //       if (!actualData?.features?.length && !trendData?.features?.length) {
  //         setNoData(true);
  //         return;
  //       }

  //       setGridData({ actual: actualData, trend: trendData });
  //       const u = actualData?.metadata?.unit || trendData?.metadata?.unit || "";
  //       setUnit(u);
  //     })
  //     .catch((err) => {
  //       setError(err.message);
  //     })
  //     .finally(() => {
  //       setLoading(false);
  //     });
  // }, [indexName, datasetName]); // , datamode

  // useEffect(() => {
  //   fetch("/data/southeast-asia-boundary.geojson")
  //     .then((res) => res.json())
  //     // .then(setSeaBoundary)
  //     .then((data) => setBoundaryData(data));
  // }, []);

  useEffect(() => {
    fetch(`/data/boundary/${country}.geojson`)
      .then((res) => res.json())
      // .then(setSeaBoundary)
      .then((data) => setBoundaryData(data));
  }, [country]);

  useEffect(() => {
    if (!country || country === "SEA") {
      setMaskData(null);
      return;
    }

    fetch(`/data/mask/${country}_mask.geojson`)
      .then((res) => res.json())
      .then(setMaskData);
  }, [country]);

  // useEffect(() => {
  //   if (!country || country === "SEA") {
  //     setCountryBoundary(null);
  //     return;
  //   }

  //   fetch(`/data/boundary/${country}.geojson`)
  //     .then((res) => res.json())
  //     .then(setCountryBoundary);
  // }, [country]);

  // useEffect(() => {
  //   if (mode !== "trend") {
  //     setShowSig(false);
  //   }
  // }, [mode]);

  // calculate color scale
  useEffect(() => {
    const nBins = 9; // Divide color level (9 is max for color code YlOrRd and RdBu)
    ["actual", "trend"].forEach((m) => {
      const data = gridData[m];
      if (!data) return;
      const col = m === "trend" ? "slope" : "value";
      const values = data.features
        .map((f) => f.properties[col])
        .filter((v) => v !== null && !isNaN(v))
        .sort(d3.ascending);

      if (values.length === 0) return;
      // const p2 = d3.quantile(values, 0.02);
      // const p98 = d3.quantile(values, 0.98);

      const userMin = legendRange[m].min;
      const userMax = legendRange[m].max;

      const autoMin = d3.quantile(values, 0.02);
      const autoMax = d3.quantile(values, 0.98);

      const minVal = userMin != null ? userMin : autoMin;
      const maxVal = userMax != null ? userMax : autoMax;

      if (!isFinite(minVal) || !isFinite(maxVal) || minVal >= maxVal) return;

      // if (!isFinite(p2) || !isFinite(p98)) return;

      if (m === "actual") {
        // const thresholds = d3.ticks(p2, p98, nBins);
        // const scale = d3
        //   .scaleThreshold()
        //   .domain(thresholds.slice(1, -1)) // edge each bin
        //   .range(d3.schemeYlOrRd[nBins]);
        // setScales((s) => ({ ...s, actual: scale }));
        // setBinsAll((b) => ({ ...b, actual: thresholds }));
        const thresholds = d3.ticks(minVal, maxVal, nBins);
        const scale = d3
          .scaleThreshold()
          .domain(thresholds.slice(1, -1))
          .range(d3.schemeYlOrRd[nBins]);

        setScales((s) => ({ ...s, actual: scale }));
        setBinsAll((b) => ({ ...b, actual: thresholds }));
      } else {
        // const maxAbs = Math.max(Math.abs(p2), Math.abs(p98)); // make balance
        // if (maxAbs === 0) return;
        // const thresholds = d3.ticks(-maxAbs, maxAbs, nBins);
        // const colors = [...d3.schemeRdBu[nBins]].reverse();
        // const scale = d3
        //   .scaleThreshold()
        //   .domain(thresholds.slice(1, -1))
        //   .range(colors);
        // setScales((s) => ({ ...s, trend: scale }));
        // setBinsAll((b) => ({ ...b, trend: thresholds }));
        const absMax =
          userMin != null || userMax != null
            ? Math.max(Math.abs(minVal), Math.abs(maxVal))
            : Math.max(Math.abs(autoMin), Math.abs(autoMax));

        if (absMax === 0) return;

        const thresholds = d3.ticks(-absMax, absMax, nBins);
        const colors = [...d3.schemeRdBu[nBins]]; //.reverse()

        const scale = d3
          .scaleThreshold()
          .domain(thresholds.slice(1, -1))
          .range(colors);

        setScales((s) => ({ ...s, trend: scale }));
        setBinsAll((b) => ({ ...b, trend: thresholds }));
      }
    });
  }, [gridData, indexName, legendRange]);

  // style grid cell
  const style = (modeKey) => (feature) => {
    const col = modeKey === "trend" ? "slope" : "value";
    const val = feature.properties[col];
    // const isActive = mode === modeKey;
    return {
      fillColor:
        scales[modeKey] && val != null && !isNaN(val) // from color scale func. if have scale fill color, but if have not is gray color
          ? scales[modeKey](val)
          : "#dddddd",
      weight: 0,
      color: "none",
      fillOpacity: 0.8,
      interactive: true,
      // fillOpacity: isActive ? 0.8 : 0,
      // interactive: isActive,
    };
  };

  // Significant Points
  const significantPoints = useMemo(() => {
    // useMemo >> calculate again if gridData or mode change
    const data = gridData[mode];
    if (!data) return [];
    return data.features.filter(
      (f) => f.properties.p != null && +f.properties.p < 0.05
    );
  }, [gridData, mode]);

  // calculate centroid and radius follow grid
  function SigPoint({ feature }) {
    const geom = feature.geometry;
    if (!geom || !geom.coordinates || !Array.isArray(geom.coordinates)) {
      console.warn("Invalid geometry:", geom);
      return null; // skip if feature is broken (not polygon)
    }

    let center;
    try {
      const bbox = turf.bbox(feature); // [minX, minY, maxX, maxY]
      center = [(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2];
    } catch (e) {
      console.warn("Failed to compute bbox center:", feature, e);
      return null;
    }

    // this line use before overlay only after overlay is error
    // const centroid = turf.centroid(feature).geometry.coordinates; // [lng, lat] | centroid is center point of polygon grid cell

    // calculate cell (distance between 2 angles)
    const coords = feature.geometry?.coordinates?.[0];
    if (!coords || coords.length < 4) return null;
    // const coords = feature.geometry.coordinates[0];
    const pt1 = turf.point(coords[0]); // left up
    const pt2 = turf.point(coords[1]); // right down (diagonal opposite)
    const cellSizeKm = turf.distance(pt1, pt2, { units: "kilometers" });
    const radiusMeters = (cellSizeKm * 1000) / 10; // convert to m and * 10 for make circle
    return (
      <Circle
        center={[center[1], center[0]]}
        radius={radiusMeters}
        pathOptions={{
          color: "black",
          fillColor: "black",
          fillOpacity: 0.9,
          interactive: false,
        }}
      />
    );
  }

  // p-2 small padding

  const onEachFeature = (modeKey) => (feature, layer) => {
    // layer.on("click", () => console.log("clicked"));
    // console.log("bind tooltip:", modeKey);
    // layer.on("click", () => {
    //   console.log("clicked", modeKey);
    // });
    let html = "";
    if (modeKey === "actual") {
      const val = feature.properties.value;
      html = `Value: ${val != null ? val.toFixed(2) : "N/A"} ${unit}`;
    } else if (modeKey === "trend") {
      const slope = feature.properties.slope;
      const pval = feature.properties.p;
      html = `Slope: ${slope != null ? slope.toFixed(2) : "N/A"}<br/>p-value: ${
        pval != null ? pval.toFixed(2) : "N/A"
      }`;
    }
    // layer.bindTooltip(html, { sticky: true, direction: "top" });
    layer.bindPopup(html);
  };

  // useEffect(() => {
  //   Object.entries(layersRef.current).forEach(([key, layer]) => {
  //     if (!layer) return;
  //     layer.setStyle({ fillOpacity: key === mode ? 0.8 : 0 });

  //     layer.eachLayer((l) => {
  //       if (key === mode) {
  //         l.options.interactive = true;
  //       } else {
  //         l.options.interactive = false;
  //       }
  //     });
  //     if (key === mode) layer.bringToFront();
  //   });
  // }, [mode]);

  // useEffect(() => {
  //   if (!seaBoundary) return;

  //   // ถ้าเลือก SEA → ไม่ต้อง mask
  //   if (!countryBoundary) {
  //     setMaskData(null);
  //     return;
  //   }

  //   try {
  //     const mask = createMask(seaBoundary, countryBoundary);
  //     setMaskData(mask);
  //   } catch (e) {
  //     console.error("Failed to create mask", e);
  //     setMaskData(null);
  //   }
  // }, [seaBoundary, countryBoundary]);

  // useEffect(() => {
  //   console.log("SEA:", seaBoundary?.features?.length);
  //   console.log("Country:", countryBoundary?.features?.length);
  //   console.log("Mask:", maskData);
  // }, [seaBoundary, countryBoundary, maskData]);

  // if (loading) return <div>Loading map...</div>;
  // if (error) return <div style={{ color: "red" }}>Error: {error}</div>;
  // if (noData) return <div>No map data available.</div>;

  if (loading || isGenerating) {
    return (
      <div className="d-flex flex-column justify-content-center align-items-center" style={{ height: "450px", border: "1px solid #ddd", borderRadius: "8px", background: "#f8f9fa" }}>
        <div className="spinner-border text-primary mb-2" role="status"></div>
        <span className="fw-bold text-primary">
          {isGenerating ? `Calculating map data for ${startYear} - ${endYear}...` : "Loading maps..."}
        </span>
      </div>
    );
  }
  
  if (error) return <div className="p-3 text-danger border rounded">Error: {error}</div>;
  if (noData) return <div className="p-3 text-warning border rounded">No map data available for the selected parameters.</div>;

  return (
    <div>
      {/* mode button */}
      {/* <div className="flex gap-2 p-2">
        <button
          onClick={() => setMode("actual")}
          className={mode === "actual" ? "bg-blue-500 text-white px-2" : "px-2"}
        >
          Actual Map
        </button>
        <button
          onClick={() => setMode("trend")}
          className={mode === "trend" ? "bg-blue-500 text-white px-2" : "px-2"}
        >
          Trend Map
        </button>
      </div> */}
      <div className="d-flex gap-2 p-2">
        <button
          onClick={() => setMode("actual")}
          className={`btn ${mode === "actual" ? "btn-primary shadow-sm" : "btn-light border"}`}
        >
          Actual Map
        </button>
        <button
          onClick={() => setMode("trend")}
          className={`btn ${mode === "trend" ? "btn-primary shadow-sm" : "btn-light border"}`}
        >
          Trend Map
        </button>
      </div>

      {/* toggle significant points */}
      {mode === "trend" && (
        <div className="p-2">
          <label>
            <input
              type="checkbox"
              checked={showSig}
              onChange={() => setShowSig((s) => !s)}
            />{" "}
            Significant Points
          </label>
        </div>
      )}
      <div className="flex flex-col">
        <MapContainer
          // center={[15, 101]}
          // zoom={5}
          center={mapView.center}
          zoom={mapView.zoom}
          style={{ height: "450px", width: "100%" }}
        >
          <MapViewUpdater center={mapView.center} zoom={mapView.zoom} />

          {/* {maskData && <BoundaryMaskLayer mask={maskData} />} */}

          {/* Mask first */}
          {maskData && <BoundaryMaskLayer mask={maskData} />}

          {/* Boundary always on top */}
          {boundaryData && <BoundaryLayer data={boundaryData} />}

          {/* SEA view */}
          {/* {seaBoundary && !countryBoundary && (
            <BoundaryLayer data={seaBoundary} type="sea" />
          )} */}

          {/* Country view */}
          {/* {countryBoundary && (
            <BoundaryLayer data={countryBoundary} type="country" />
          )} */}

          {mode === "trend" && gridData.trend && (
            <GeoJSON
              data={gridData.trend}
              style={style("trend")}
              onEachFeature={onEachFeature("trend")}
              ref={(ref) => (layersRef.current.trend = ref)}
            />
          )}
          {mode === "actual" && gridData.actual && (
            <GeoJSON
              data={gridData.actual}
              style={style("actual")}
              onEachFeature={onEachFeature("actual")}
              ref={(ref) => (layersRef.current.actual = ref)}
            />
          )}

          {showSig &&
            significantPoints.map((f, i) => <SigPoint key={i} feature={f} />)}
        </MapContainer>

        {scales[mode] && binsAll[mode]?.length > 0 && (
          <Legend
            bins={binsAll[mode]}
            scale={scales[mode]}
            mode={mode}
            unit={unit}
          />
        )}
      </div>

      {/* legend range control */}
      <div className="flex gap-2 p-2 items-center">
        <span className="text-sm">Legend range:</span>

        <input
          type="number"
          placeholder="Min"
          value={legendRange[mode].min ?? ""}
          onChange={(e) =>
            setLegendRange((r) => ({
              ...r,
              [mode]: {
                ...r[mode],
                min: e.target.value === "" ? null : +e.target.value,
              },
            }))
          }
          className="border px-1 w-24"
        />

        <input
          type="number"
          placeholder="Max"
          value={legendRange[mode].max ?? ""}
          onChange={(e) =>
            setLegendRange((r) => ({
              ...r,
              [mode]: {
                ...r[mode],
                max: e.target.value === "" ? null : +e.target.value,
              },
            }))
          }
          className="border px-1 w-24"
        />

        <button
          className="text-sm underline"
          onClick={() =>
            setLegendRange((r) => ({
              ...r,
              [mode]: { min: null, max: null },
            }))
          }
        >
          Auto
        </button>
      </div>

    </div>
  );
}
