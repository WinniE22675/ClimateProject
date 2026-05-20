import { useEffect, useState, useMemo, useRef } from "react";
import { MapContainer, GeoJSON, CircleMarker, useMap } from "react-leaflet"; // Circle,
import L from "leaflet";
import * as d3 from "d3";
import * as turf from "@turf/turf"; // help compute centroid
import Legend from "./Legend";

import { apiFetch } from '../services/api';

function MapBoundsController({ province, allProvincesData, targetCol }) { 
  const map = useMap();

  useEffect(() => {
    if (!allProvincesData || !allProvincesData.features) return;

    if (province && targetCol) {
      // 1. Zoom to a specific province
      const provinceFeature = allProvincesData.features.find(
        (f) => f.properties[targetCol] === province // Use dynamic column!
      );

      if (provinceFeature) {
        const layer = L.geoJSON(provinceFeature);
        const bounds = layer.getBounds();
        if (bounds.isValid()) {
          map.fitBounds(bounds, { animate: true }); // padding: [30, 30],
        }
      }
    } else {
      // 2. Zoom to the entire workspace (Auto-Center on the whole shapefile)
      const fullLayer = L.geoJSON(allProvincesData);
      const fullBounds = fullLayer.getBounds();
      
      if (fullBounds.isValid()) {
        map.fitBounds(fullBounds, { animate: true }); // padding: [20, 20],
      }
    }
  }, [province, allProvincesData, targetCol, map]);

  return null;
}

function BoundaryLayer({ data , weight = 0.5 }) {
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
      smoothFactor: 0.8,
      style: {
        interactive: false,
        weight: weight,
        color: "black",
        fillOpacity: 0,
      },
    }).addTo(map);
    return () => {
      map.removeLayer(layer); // each data change
    };
  }, [map, data, weight]);
  return null;
}

function CountryContextLayer({ data, selectedProvince }) {
  const map = useMap();

  useEffect(() => {
    if (!data || !data.features) return;

    // Create a specific pane to control z-index
    if (!map.getPane("contextPane")) {
      map.createPane("contextPane");
      // zIndex 350 keeps it above base map (200) but below grid data (400)
      map.getPane("contextPane").style.zIndex = 350; 
      map.getPane("contextPane").style.pointerEvents = "none";
    }

    const layer = L.geoJSON(data, {
      pane: "contextPane",
      smoothFactor: 0.8,
      style: (feature) => {
        // Check if the current feature matches the selected province
        const isSelected = feature.properties.ADM1_EN === selectedProvince;
        
        // If a province is selected AND this feature is NOT the selected one, dim it
        const shouldDim = selectedProvince && !isSelected;

        return {
          color: isSelected ? "#000000" : "#888888", // Highlight selected border
          weight: isSelected ? 2.0 : 0.75,            // Thicker border for selected
          fillColor: "#eeeeee",                      // Light gray for background
          fillOpacity: shouldDim ? 0.7 : 0,          // Show gray only for non-selected
          interactive: false,
        };
      },
    }).addTo(map);

    return () => {
      map.removeLayer(layer);
    };
  }, [map, data, selectedProvince]);

  return null;
}

function getBaseIndexName(name) {
  const match = name.match(/(SPI\d+)/);
  if (match) {
    return match[1]; // Extracts SPI3, SPI6, etc.
  }
  return name;
}

export default function GridMapViewer({
  indexName,
  mode,
  setMode,
  datasetName,
  country,
  province,
  startYear,
  endYear, 
  availableIndices,
  spiThreshold,
  shapefileName,
  targetCol
}) {
  const [gridData, setGridData] = useState({ actual: null, trend: null });
  const [scales, setScales] = useState({ actual: null, trend: null });
  const [binsAll, setBinsAll] = useState({ actual: [], trend: [] });
  const [showSig, setShowSig] = useState(true);
  const [unit, setUnit] = useState("");
  const layersRef = useRef({ actual: null, trend: null });

  // state: loading / error / no-data
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [noData, setNoData] = useState(false);

  const [isGenerating, setIsGenerating] = useState(false);

  const [allProvincesData, setAllProvincesData] = useState(null);

  const [mapStyle, setMapStyle] = useState("grid"); // "grid" or "shapefile"
  const [colorSchemes, setColorSchemes] = useState({
    actual: "YlOrRd",
    trend: "RdBu",
  });

  const [errorType, setErrorType] = useState(null);

  useEffect(() => {
    if (!indexName) return;

    // Define a list of precipitation-related indices 
    // (Adjust these array items to match your actual backend indices)
    const rainIndices = [
      "pr",
      "prcptot",
      "rx1day",
      "rx5day",
      "sdii",
      "r10mm",
      "r20mm",
      "cdd",
      "cwd",
      "r95p",
      "r99p",
      "r95ptot",
      "r99ptot",
      "spi1",
      "spi3",
      "spi6",
      "spi9",
      "spi12",
      "spi24",
      "spi36",
      "spi48",
      "spi60",
    ];
    
    // Convert indexName to lowercase once for efficiency
    const indexLower = indexName.toLowerCase();

    const isRain = rainIndices.includes(indexLower) || indexLower.includes("flood");

    setColorSchemes({
      actual: isRain ? "Blues" : "YlOrRd",
      trend: "RdBu",
    });
  }, [indexName]);

  // user-defined legend range (null = auto)
  const [legendRange, setLegendRange] = useState({
    actual: { min: null, max: null },
    trend: { min: null, max: null },
  });

  const COUNTRY_VIEW = {
    Thailand: {
      center: [13.25, 101.0],
      zoom: 5.25,
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

  const mapView = COUNTRY_VIEW[country] || COUNTRY_VIEW.SEA;

  const NO_TREND_INDICES = [
    "pr",
    "tmax",
    "tmin",
  ];

  const isSPI = indexName.startsWith("SPI");

  const isSPIEvent = indexName.startsWith("SPI") && (indexName.includes("_Drought_") || indexName.includes("_Flood_"));

  const isSPIFrequency = isSPIEvent && indexName.includes("Frequency");

  const supportsTrend = !NO_TREND_INDICES.includes(indexName) && !isSPIFrequency;

  // Check if the current shapefile has multiple sub-areas (e.g., provinces)
  const hasSubAreas = allProvincesData?.features?.length > 1;

  // Auto-switch back to "grid" mode if the selected country has no sub-areas
  // but the user was previously in "shapefile" mode
  useEffect(() => {
    if (allProvincesData && !hasSubAreas && mapStyle === "shapefile") {
      setMapStyle("grid");
    }
  }, [allProvincesData, hasSubAreas, mapStyle]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setNoData(false);
    setIsGenerating(false);

    setGridData({ actual: null, trend: null });
    setScales({ actual: null, trend: null });
    setBinsAll({ actual: [], trend: [] });
    setUnit("");

    if (!supportsTrend && mode === "trend") {
      setMode("actual");
    }

    let isMounted = true;

    if (!availableIndices || availableIndices.length === 0) {
      console.log(`[Guard] Metadata loading. Waiting...`);
      return; 
    }

    if (!availableIndices.includes(indexName)) {
      console.log(`[Guard] Index '${indexName}' not found in dataset. Waiting...`);
      return; 
    }

    const fetchAllMaps = async () => {
      setLoading(true);
      setError(null);
      setNoData(false);
      setIsGenerating(false);

      // Check SPI event and add thresholdPart for fetch
      // const thresholdPart = isSPIEvent ? `_${spiThreshold}` : "";
      // Convert the value to a floating-point number
      const num = parseFloat(spiThreshold);

      // Check if it's an integer (e.g., 1) or has decimals (e.g., 1.15)
      // - Number.isInteger(num) returns true if num is 1 -> we use .toFixed(1) to get "1.0"
      // - If it's false (e.g., 1.15) -> we convert it directly to String("1.15") to keep all decimals
      const formatThreshold = Number.isInteger(num) ? num.toFixed(1) : String(num);

      // Append to the string
      const thresholdPart = isSPIEvent && !isNaN(num) ? `_${formatThreshold}` : "";

      const apiBase = "http://172.16.2.110:10001";
      // Determine base path based on dataset type
      const datasetPath = datasetName === "default" ? "/data" : `${apiBase}/output/${datasetName}`;
      
      // Determine area (use "overview" for country-level data)
      const area = province ? province : "overview";
      const cacheKey = Date.now();

      // Dynamically select folder based on mapStyle state
      const mapFolder = mapStyle === "shapefile" ? "maps_shp" : "maps_grid";
      const fileSuffix = mapStyle === "shapefile" ? "shp" : "grid";
      
      // Construct file paths based on the domain-centric structure
      const actualGridPath = `${datasetPath}/${country}/${area}/${indexName}/${mapFolder}/actual/${startYear}_${endYear}${thresholdPart}_actual_${fileSuffix}.geojson?v=${cacheKey}`;
      const trendGridPath = `${datasetPath}/${country}/${area}/${indexName}/${mapFolder}/trend/${startYear}_${endYear}${thresholdPart}_trend_${fileSuffix}.geojson?v=${cacheKey}`;

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
        // Initial Fetch ---
        const requests = [fetchGracefully(actualGridPath)];
        if (supportsTrend) {
          requests.push(fetchGracefully(trendGridPath));
        }

        let results = await Promise.all(requests);
        let actualRes = results[0];
        let trendRes = supportsTrend ? results[1] : { status: 200, data: null };

        // Lazy Generation Check ---
        // If file doesn't exist (404), ask backend to generate it
        if (actualRes.status === 404 || (supportsTrend && trendRes.status === 404)) {
          setIsGenerating(true);

          const generateRes = await apiFetch(`/maps/generate`, {
            method: "POST",
            body: JSON.stringify({
              indexName,
              datasetName,
              country,
              province: province || null,
              startYear: parseInt(startYear, 10),
              endYear: parseInt(endYear, 10),
              shapefileName,
              targetCol,
              supportsTrend,
              spi_threshold: parseFloat(spiThreshold)
            }),
          });

          if (!generateRes.ok) {
            // throw new Error("Backend failed to generate map data.");
            // throw new Error(`Map generation API failed with status: ${generateRes.status}`);
            console.warn(`Map generation API returned status: ${generateRes.status}. Continuing to check if files exist...`);
          }

          // Re-fetch after generation ---
          const newCacheKey = Date.now(); 
          const retryActualPath = `${datasetPath}/${country}/${area}/${indexName}/${mapFolder}/actual/${startYear}_${endYear}${thresholdPart}_actual_${fileSuffix}.geojson?v=${newCacheKey}`;
          const retryTrendPath = `${datasetPath}/${country}/${area}/${indexName}/${mapFolder}/trend/${startYear}_${endYear}${thresholdPart}_trend_${fileSuffix}.geojson?v=${newCacheKey}`;

          const retryRequests = [fetchGracefully(retryActualPath)];
          if (supportsTrend) retryRequests.push(fetchGracefully(retryTrendPath));

          const retryResults = await Promise.all(retryRequests);
          actualRes = retryResults[0];
          trendRes = supportsTrend ? retryResults[1] : { status: 200, data: null };

          if (actualRes.status === 404 || (supportsTrend && trendRes.status === 404)) {
            // throw new Error("Map generation succeeded, but files are still missing on the server.");
            if (isMounted) {
              setErrorType("DATA_UNAVAILABLE");
              setIsGenerating(false);
              setLoading(false);
              return; 
            }
          }
        }

        // Update State ---
        if (isMounted) {
          setErrorType(null);
          const actualData = actualRes.data;
          const trendData = trendRes.data;

          // Check if data is truly empty
          if (!actualData?.features?.length && (!supportsTrend || !trendData?.features?.length)) {
            setNoData(true);
          } else {
            setGridData({ actual: actualData, trend: trendData });
            // Extract unit from metadata
            let u = actualData?.metadata?.unit || trendData?.metadata?.unit || "";
            // Check if the current index is an SPI event
            if (indexName.startsWith("SPI")) {
              // Override the unit with the base SPI name (e.g., "SPI6")
              u = getBaseIndexName(indexName);
            }
            setUnit(u);
          }
        }

      } catch (err) {
        if (isMounted) {
          console.error("Map Load Error:", err);
          setErrorType("GENERAL_ERROR");
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
  }, [indexName, datasetName, country, province, startYear, endYear , mapStyle, availableIndices, supportsTrend, spiThreshold]);

  useEffect(() => {
    // Check if we have both datasetName and country before fetching
    if (datasetName && country) {
      const fetchBoundary = async () => {
        try {
          const apiBase = "http://172.16.2.110:10001";
          const datasetPath = datasetName === "default" ? "/data" : `${apiBase}/output/${datasetName}`;
          
          const cacheKey = new Date().getTime(); // Prevent browser caching
          const boundaryUrl = `${datasetPath}/${country}/boundary.geojson?v=${cacheKey}`;
          
          // Use standard fetch (no need for apiFetch/Auth token for public output files)
          const res = await fetch(boundaryUrl);
          
          if (!res.ok) throw new Error(`Static boundary file not found at ${boundaryUrl}`);
          
          const data = await res.json();
          setAllProvincesData(data);
        } catch (error) {
          console.error("Failed to load static boundary geojson:", error);
          setAllProvincesData(null);
        }
      };
      
      fetchBoundary();
    } else {
      setAllProvincesData(null);
    }
  }, [datasetName, country]); // Trigger when dataset or country changes

  const displayProvinceBoundary = useMemo(() => {
    if (!allProvincesData) return null;
    
    // if select "Whole Country" (province is space ("")) will show province line 
    if (!province) {
      return allProvincesData;
    }

    // if select province will Filter select only Feature of that province
    // Note: check Property name in GeoJSON files 
    const filteredFeatures = allProvincesData.features.filter(
      (f) => targetCol && f.properties[targetCol] === province
    );

    // Reassemble back into GeoJSON Object
    return {
      type: "FeatureCollection",
      features: filteredFeatures,
    };
  }, [allProvincesData, province, targetCol]);

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

      const userMin = legendRange[m].min;
      const userMax = legendRange[m].max;

      const autoMin = d3.quantile(values, 0.02);
      const autoMax = d3.quantile(values, 0.98);

      const minVal = userMin != null ? userMin : autoMin;
      const maxVal = userMax != null ? userMax : autoMax;

      if (!isFinite(minVal) || !isFinite(maxVal) || minVal >= maxVal) return;

      if (m === "actual") {
        const thresholds = d3.ticks(minVal, maxVal, nBins);

        // Intercept "Blues" selection to apply custom darker starting shade
        const schemeName = colorSchemes.actual;
        let selectedScheme;
        if (schemeName === "Blues") {
          // Use interpolateBlues but skip the lightest 20% (t * 0.8 + 0.2)
          selectedScheme = d3.quantize((t) => d3.interpolateBlues(t * 0.8 + 0.2), nBins);
        } else {
          // Fallback to standard D3 schemes
          selectedScheme = d3[`scheme${schemeName}`] 
            ? d3[`scheme${schemeName}`][nBins] 
            : d3.schemeYlOrRd[nBins];
        }
        
        const scale = d3
          .scaleThreshold()
          .domain(thresholds.slice(1, -1))
          .range(selectedScheme);

        setScales((s) => ({ ...s, actual: scale }));
        setBinsAll((b) => ({ ...b, actual: thresholds }));
      } else {
        const absMax =
          userMin != null || userMax != null
            ? Math.max(Math.abs(minVal), Math.abs(maxVal))
            : Math.max(Math.abs(autoMin), Math.abs(autoMax));

        if (absMax === 0) return;

        const thresholds = d3.ticks(-absMax, absMax, nBins);

        const rawSchemeName = colorSchemes.trend;
        const isReversed = rawSchemeName.startsWith("-");
        const cleanSchemeName = isReversed ? rawSchemeName.substring(1) : rawSchemeName;

        const selectedScheme = d3[`scheme${cleanSchemeName.trend}`]
          ? [...d3[`scheme${cleanSchemeName.trend}`][nBins]]
          : [...d3.schemeRdBu[nBins]];

        // Reverse the array if the prefix '-' is present (e.g., for Temperature Trend)
        if (isReversed) {
          selectedScheme.reverse();
        }

        const scale = d3
          .scaleThreshold()
          .domain(thresholds.slice(1, -1))
          .range(selectedScheme);

        setScales((s) => ({ ...s, trend: scale }));
        setBinsAll((b) => ({ ...b, trend: thresholds }));
      }
    });
  }, [gridData, indexName, legendRange, colorSchemes]);

  // style grid cell
  const style = (modeKey) => (feature) => {
    const col = modeKey === "trend" ? "slope" : "value";
    const val = feature.properties[col];
    // const isActive = mode === modeKey;

    // Default color calculation using D3 scales
    let cellColor = scales[modeKey] && val != null && !isNaN(val) 
      ? scales[modeKey](val)
      : "#dddddd";
    
    let opacity = 0.8;

    // --- Override color specifically for SPI Event Trends ---
    if (modeKey === "trend" && isSPIEvent) {
      const { trend } = feature.properties;
      
      // Color based ONLY on trend direction (ignore p-value)
      if (trend === "increasing") {
        cellColor = "#d73027"; // Red color for increasing trend
      } else if (trend === "decreasing") {
        cellColor = "#1f77b4"; // Green color for decreasing trend
      } else {
        cellColor = "#dddddd"; // Gray color for no trend (or slope = 0)
      }
    }
    return {
      fillColor: cellColor,
      // stroke: false,
      // weight: 0,
      // color: "none",
      stroke: true,         
      color: cellColor,     
      weight: 0.5,
      fillOpacity: 0.8,
      interactive: true,
    };
  };

  // Significant Points
  const significantPoints = useMemo(() => {
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

    const pointRadius = province ? 4 : 1;
    return (
      <CircleMarker
        center={[center[1], center[0]]}
        radius={pointRadius} // Set fixed size in pixels (e.g., 3 or 4)
        pathOptions={{
          color: "none",       // Remove border stroke for cleaner look
          fillColor: "black",
          fillOpacity: 0.85,   // Slightly transparent so map beneath is visible
          interactive: false,
        }}
      />
    );
  }

  const onEachFeature = (modeKey) => (feature, layer) => {
    let html = "";
    const namePrefix = feature.properties.name ? `<strong>${feature.properties.name}</strong><br/>` : "";

    if (modeKey === "actual") {
      const val = feature.properties.value;
      html = `${namePrefix} Value: ${
        val != null 
      ? (indexName.includes("Frequency") ? val.toFixed(0) 
        : indexName.includes("Duration") ? val.toFixed(2)
        : indexName.includes("Peak") ? val.toFixed(2) 
        : isSPI ? val.toFixed(4) 
        : val.toFixed(2))
      : "N/A"
      } ${unit}`;
    } else if (modeKey === "trend") {
      const slope = feature.properties.slope;
      const pval = feature.properties.p;
      const trendDir = feature.properties.trend;
      
      html = `${namePrefix} Slope: ${slope != null ? slope.toFixed(2) : "N/A"}<br/>p-value: ${
        pval != null ? pval.toFixed(2) : "N/A"
      }`;

      if (isSPIEvent && trendDir) {
        const trendText = trendDir.charAt(0).toUpperCase() + trendDir.slice(1);
        
        // Add text color based on direction
        const color = trendDir === "increasing" ? "red" : trendDir === "decreasing" ? "blue" : "gray";
        html += `<br/>Trend: <strong style="color: ${color}">${trendText}</strong>`;
      }
    }
    // layer.bindTooltip(html, { sticky: true, direction: "top" });
    layer.bindPopup(html);
  };

if (loading || isGenerating) {
    return (
      /* Added mt-[60px] to align with left side, and changed h-[450px] to h-[500px] */
      <div className="flex flex-col items-center justify-center w-full h-[500px] mt-[60px] bg-gray-50 border border-gray-200 rounded-lg">
        <svg className="animate-spin h-10 w-10 text-blue-600 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span className="font-bold text-blue-600 animate-pulse text-base">
          {isGenerating ? `Calculating map data for ${startYear} - ${endYear}...` : "Loading maps..."}
        </span>
      </div>
    );
  }
  
  if (error) return <div className="p-3 text-danger border rounded">Error: {error}</div>;
  if (noData) return <div className="p-3 text-warning border rounded">No map data available for the selected parameters.</div>;

  return (
    <div className="w-full overflow-hidden">
      
      {/* 1. Header Section: Mode Buttons & Map Title */}
      <div className="flex flex-wrap justify-between items-center py-2 gap-4">
        
        {/* Left: Mode Buttons (Grouped for better UI) */}
        <div className="flex rounded-md shadow-sm" role="group">
          <button
            onClick={() => setMode("actual")}
            className={`px-4 py-1.5 text-base font-medium border transition-colors rounded-l-md ${
              mode === "actual" 
                ? "bg-blue-600 text-white border-blue-600 z-10" 
                : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
            }`}
          >
            Actual Map
          </button>
          <button
            onClick={() => setMode("trend")}
            className={`px-4 py-1.5 text-base font-medium border-y border-r transition-colors rounded-r-md disabled:opacity-60 disabled:cursor-not-allowed ${
              mode === "trend" 
                ? "bg-blue-600 text-white border-blue-600 z-10" 
                : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
            }`}
            title={!supportsTrend ? "Trend map is not available for raw variables" : "View Trend Map"}
            disabled={!supportsTrend}
          >
            Trend Map
          </button>
        </div>

        {/* Center: Checkbox for Significant Points (Only in Trend mode) */}
        {mode === "trend" && (
          <div className="flex items-center ml-4 mr-auto">
            <label className="flex items-center cursor-pointer relative" htmlFor="sigPointsToggle">
              <input
                type="checkbox"
                id="sigPointsToggle"
                className="sr-only peer"
                checked={showSig}
                onChange={() => setShowSig((s) => !s)}
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              <span className="ml-3 text-base font-bold text-gray-500">
                Significant Points (p &lt; 0.05)
              </span>
            </label>
          </div>
        )}

        {/* Right: Dynamic Map Title */}
        <div className="text-right ml-auto">
          <h6 className="m-0 font-bold text-gray-700 text-base">
            {indexName} {
              mode === "actual" 
                ? (indexName.includes("Frequency") ? "Sum" : "Average") 
                : "Trend"
            } Map
          </h6>
          <small className="text-gray-500">
            {startYear} - {endYear} {isSPIEvent && `| Threshold ${spiThreshold}`} {province ? `| ${province}` : "| Whole Country"}
          </small>
        </div>
      </div>

      {/* 3. Map Container */}
      <div className="p-0 relative">
        {errorType === "DATA_UNAVAILABLE" ? (
          
          <div className="flex justify-center items-center w-full h-[450px]">
            <div className="p-6 rounded-lg bg-white border border-gray-300 mx-4 max-w-[550px] shadow-sm">
              <div className="flex items-center mb-4">
                {/* Custom Info Icon */}
                <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10 text-gray-800 mr-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <h5 className="text-gray-900 font-bold m-0 text-lg">Map Visualization Unavailable</h5>
              </div>
              <p className="text-gray-500 text-base mb-4">
                The system could not generate a map for <strong>{province || country}</strong>. This typically happens due to one of the following reasons:
              </p>
              <ul className="text-gray-500 text-base mb-4 list-disc pl-5">
                <li className="mb-1"><strong>Resolution Limit:</strong> The selected area is too small (less than 1 grid cell).</li>
                <li className="mb-1"><strong>Spatial Mismatch:</strong> The dataset does not cover this geographic area.</li>
                <li><strong>Missing Values:</strong> The area contains only invalid or No-Data values (NaN).</li>
              </ul>
              <div className="text-gray-500 text-base flex items-start mt-6 bg-gray-50 p-3 rounded-md">
                {/* Custom Lightbulb Icon */}
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-800 mr-2 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                <span><strong>Tip:</strong> If the <em>Timeseries charts</em> on the left are also empty, it confirms a <strong>Spatial Mismatch</strong> or <strong>Missing Values</strong>.</span>
              </div>
            </div>
          </div>

        ) : errorType === "GENERAL_ERROR" || error ? (

          <div className="flex justify-center items-center w-full h-[450px] text-gray-900">
            <div className="text-center bg-white p-6 rounded-lg border border-gray-300 mx-4 max-w-[500px] shadow-sm">
                {/* Custom Exclamation Icon */}
               <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 text-gray-800 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
               </svg>
               <h5 className="font-bold mb-3 text-lg">System Error Encountered</h5>
               <p className="text-base text-gray-500 mb-4">
                 An unexpected error has occurred while processing the map data. <br/>
                 Please contact the system administrator for assistance.
               </p>
               
               {error && (
                 <div className="bg-gray-50 p-3 rounded-md border border-gray-200 text-base text-left break-words text-gray-600">
                   <strong>Details:</strong> {error}
                 </div>
               )}
            </div>
          </div>

        ) : (
          <MapContainer
            key={`map-container-${country}`} // Force re-mount of map ONLY when country changes
            zoomSnap={0.25}  // Enable fractional zoom snapping to 0.25 increments
            zoomDelta={0.25} // Set zoom step for +/- buttons to 0.25
            style={{ height: "450px", width: "100%", zIndex: 0 }} // inline styles are kept for react-leaflet
          >
            {/* Boundary always on top */}
            {displayProvinceBoundary && (
              <BoundaryLayer data={displayProvinceBoundary} weight={1.0} />
            )}

            <MapBoundsController 
              province={province} 
              allProvincesData={allProvincesData} 
              targetCol={targetCol} 
            />

            {allProvincesData && (
              <CountryContextLayer 
                data={allProvincesData} 
                selectedProvince={province} 
              />
            )}

            {/* Map Data Layers */}
            {mode === "trend" && gridData.trend && (
              <GeoJSON
                key={`geojson-trend-${indexName}-${startYear}-${endYear}-${province}-${mapStyle}-${spiThreshold}`}
                data={gridData.trend}
                style={style("trend")}
                onEachFeature={onEachFeature("trend")}
                ref={(ref) => (layersRef.current.trend = ref)}
              />
            )}
            {mode === "actual" && gridData.actual && (
              <GeoJSON
                key={`geojson-actual-${indexName}-${startYear}-${endYear}-${province}-${mapStyle}-${spiThreshold}`}
                data={gridData.actual}
                style={style("actual")}
                onEachFeature={onEachFeature("actual")}
                ref={(ref) => (layersRef.current.actual = ref)}
              />
            )}

            {showSig &&
              significantPoints.map((f, i) => <SigPoint key={i} feature={f} />)}
          </MapContainer>
        )}
      </div>

      {/* 4. Legend & Controls Footer */}
      <div className="bg-white border-t border-gray-200 pt-3 pb-4 px-0">
        
        {/* Color Bar */}
        {((scales[mode] && binsAll[mode]?.length > 0) || (mode === "trend" && isSPIEvent && gridData[mode])) && (
          <div className="mb-3">
            <Legend
              key={`legend-${indexName}-${mode}-${isSPIEvent}`} 
              bins={binsAll[mode]}
              scale={scales[mode]}
              mode={mode}
              unit={unit}
              indexName={indexName}
              isSPIEvent={isSPIEvent}
            />
          </div>
        )}
        
        <div className="flex flex-wrap justify-between items-center gap-y-3 gap-x-4">

          <div className="flex flex-wrap items-center gap-3">

            {!(mode === "trend" && isSPIEvent) && (
              <>
                  {/* 1. Color Palette Selector */}
                  <div className="flex items-center gap-2">
                    <span className="text-base font-bold text-gray-500">Color</span>
                    <select
                      className="block text-base border border-gray-300 rounded-md px-1 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
                      value={colorSchemes[mode]}
                      onChange={(e) =>
                        setColorSchemes((prev) => ({ ...prev, [mode]: e.target.value }))
                      }
                    >
                      {mode === "actual" ? (
                        <>
                          <optgroup label="Temperature">
                            <option value="YlOrRd">Yl-Or-Rd</option>
                            <option value="OrRd">Orange-Red</option>
                            <option value="Reds">Reds</option>
                          </optgroup>
                          <optgroup label="Precipitation">
                            <option value="Blues">Blues</option>
                            <option value="YlGnBu">Yl-Gn-Bu</option>
                            <option value="GnBu">Green-Blue</option>
                          </optgroup>
                        </>
                      ) : (
                        <>
                            {/* Note: -RdBu means we will reverse it in the logic */}
                            <option value="RdBu">Red-Blue</option>
                            <option value="-RdBu">Blue-Red</option>
                            <option value="BrBG">Brown-Green</option>
                        </>
                      )}
                    </select>
                  </div>

                  {/* Legend Range Controls */}
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="text-base font-bold text-gray-500 mr-1">Legend Range</span>

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
                      className="block text-center text-sm border border-gray-300 rounded-md px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white w-16"
                      // style={{ width: "65px" }}
                    />
                    
                    <span className="text-gray-400">-</span>

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
                      className="block text-center text-sm border border-gray-300 rounded-md px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white w-16"
                      // style={{ width: "65px" }}
                    />

                    <button
                      className="ml-1 px-3 py-1.5 text-sm font-medium bg-white text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
                      onClick={() =>
                        setLegendRange((r) => ({
                          ...r,
                          [mode]: { min: null, max: null },
                        }))
                      }
                    >
                      Auto Fix
                    </button>
                  </div>
              </>
            )}
          </div>

          <div className="inline-flex items-center rounded-md shadow-sm">
            <button
              className={`px-3 py-1.5 text-base font-medium border transition-colors disabled:opacity-60 disabled:cursor-not-allowed rounded-l-md ${
                mapStyle === "grid" 
                  ? "bg-gray-400 text-white border-gray-400 z-10" /* Lighter gray for active state */
                  : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"
              }`}
              onClick={() => setMapStyle("grid")}
              title="Show as Grid"
              disabled={!!province}
            >
              Grid
            </button>
            <button
              className={`px-3 py-1.5 text-base font-medium border-y border-r transition-colors disabled:opacity-60 disabled:cursor-not-allowed rounded-r-md -ml-px ${
                mapStyle === "shapefile" 
                  ? "bg-gray-400 text-white border-gray-400 z-10" /* Lighter gray for active state */
                  : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"
              }`}
              onClick={() => setMapStyle("shapefile")}
              title={!hasSubAreas ? "Shapefile mode requires multiple sub-areas" : "Show as Shapefile Area Average"}
              disabled={!!province || !hasSubAreas}
            >
              Shapefile
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}