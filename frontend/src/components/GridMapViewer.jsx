import { useEffect, useState, useMemo, useRef } from "react";
import { MapContainer, GeoJSON, CircleMarker, useMap } from "react-leaflet"; // Circle,
import L from "leaflet";
import * as d3 from "d3";
import * as turf from "@turf/turf"; // help compute centroid
import Legend from "./Legend";

import { apiFetch } from '../services/api';

// function MapBoundsController({ province, allProvincesData, fallbackView }) { // geojsonData
//   const map = useMap();

//   useEffect(() => {
//     // 1. If a specific province is selected, calculate its bounds and zoom
//     // if (province && geojsonData && geojsonData.features && geojsonData.features.length > 0) {
//     // Create a temporary Leaflet layer to calculate the bounding box
//     // 1. If a province is selected, find its specific boundary and zoom to it
//     if (province && allProvincesData && allProvincesData.features) {
//       const provinceFeature = allProvincesData.features.find(
//         (f) => f.properties.ADM1_EN === province
//       );

//       if (provinceFeature) {
//         // Create a temporary layer JUST for this province to calculate perfect bounds
//         const layer = L.geoJSON(provinceFeature); // geojsonData
//         const bounds = layer.getBounds();
        
//         if (bounds.isValid()) {
//           // fitBounds automatically calculates the perfect center and zoom level!
//           // padding ensures the map doesn't touch the exact edges of the container
//           map.fitBounds(bounds, { padding: [30, 30], animate: true });
//         }
//       }
//     } 
//     // 2. If no province is selected (Whole Country), use the default COUNTRY_VIEW
//     else if (fallbackView) {
//       map.setView(fallbackView.center, fallbackView.zoom, { animate: true });
//     }
//   }, [province, allProvincesData, fallbackView, map]); // geojsonData

//   return null;
// }
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

// function BoundaryMaskLayer({ mask }) {
//   const map = useMap();

//   useEffect(() => {
//     if (!mask) return;

//     if (!map.getPane("mask")) {
//       map.createPane("mask");
//       map.getPane("mask").style.zIndex = 500; // on top of everything
//       map.getPane("mask").style.pointerEvents = "none";
//     }

//     const layer = L.geoJSON(mask, {
//       pane: "mask",
//       style: {
//         fillColor: "#dddddd", // background color
//         fillOpacity: 1, // IMPORTANT: must be 1
//         stroke: false,
//         weight: 0,
//         interactive: false,
//       },
//     }).addTo(map);

//     return () => map.removeLayer(layer);
//   }, [map, mask]);

//   return null;
// }


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
  // const [boundaryData, setBoundaryData] = useState(null);
  const layersRef = useRef({ actual: null, trend: null });

  // state: loading / error / no-data
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [noData, setNoData] = useState(false);

  // const [maskData, setMaskData] = useState(null);

  const [isGenerating, setIsGenerating] = useState(false);

  const [allProvincesData, setAllProvincesData] = useState(null);

  const [mapStyle, setMapStyle] = useState("grid"); // "grid" or "shapefile"
  const [colorSchemes, setColorSchemes] = useState({
    actual: "YlOrRd",
    trend: "RdBu",
  });

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
    
    // Check if the current index is related to rain/precipitation
    // const isRain = rainIndices.includes(indexName.toLowerCase());

    // Convert indexName to lowercase once for efficiency
    const indexLower = indexName.toLowerCase();

    const isRain = rainIndices.includes(indexLower) || indexLower.includes("flood");

    setColorSchemes({
      actual: isRain ? "Blues" : "YlOrRd",
      trend: "RdBu",
    });
  }, [indexName]);

  // const [seaBoundary, setSeaBoundary] = useState(null);
  // const [countryBoundary, setCountryBoundary] = useState(null);
  // const [maskData, setMaskData] = useState(null);

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

  // const mapView =
  //   country && COUNTRY_VIEW[country]
  //     ? COUNTRY_VIEW[country]
  //     : COUNTRY_VIEW.default;

  const mapView = COUNTRY_VIEW[country] || COUNTRY_VIEW.SEA;

  const NO_TREND_INDICES = [
    "pr",
    "tmax",
    "tmin",
  ];

  const supportsTrend = !NO_TREND_INDICES.includes(indexName);

  const isSPI = indexName.startsWith("SPI");

  const isSPIEvent = indexName.startsWith("SPI") && (indexName.includes("_Drought_") || indexName.includes("_Flood_"));

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

    // if (availableIndices && availableIndices.length > 0) {
    //   if (!availableIndices.includes(indexName)) {
    //     console.log(`[Guard] Index '${indexName}' not found in current dataset. Waiting for update...`);
    //     return; 
    //   }
    // }

    const fetchAllMaps = async () => {
      setLoading(true);
      setError(null);
      setNoData(false);
      setIsGenerating(false);

      // Check SPI event and add thresholdPart for fetch
      // const thresholdPart = isSPIEvent ? `_${spiThreshold}` : "";
      // const thresholdPart = isSPIEvent ? `_${Number(spiThreshold).toFixed(1)}` : "";
      // 1. Convert the value to a floating-point number
      const num = parseFloat(spiThreshold);

      // 2. Check if it's an integer (e.g., 1) or has decimals (e.g., 1.15)
      // - Number.isInteger(num) returns true if num is 1 -> we use .toFixed(1) to get "1.0"
      // - If it's false (e.g., 1.15) -> we convert it directly to String("1.15") to keep all decimals
      const formatThreshold = Number.isInteger(num) ? num.toFixed(1) : String(num);

      // 3. Append to the string
      const thresholdPart = isSPIEvent && !isNaN(num) ? `_${formatThreshold}` : "";

      const apiBase = "http://localhost:8000";
      // Determine base path based on dataset type
      const datasetPath = datasetName === "default" ? "/data" : `${apiBase}/output/${datasetName}`;
      
      // Determine area (use "overview" for country-level data)
      const area = province ? province : "overview";
      const cacheKey = Date.now();

      // Dynamically select folder based on mapStyle state
      const mapFolder = mapStyle === "shapefile" ? "maps_shp" : "maps_grid";
      const fileSuffix = mapStyle === "shapefile" ? "shp" : "grid";
      // const mapFolder = mapStyle === "shapefile" ? "maps_grid" : "maps_grid";
      // const fileSuffix = mapStyle === "shapefile" ? "grid" : "grid";

      // Construct file paths based on the domain-centric structure
      // const actualGridPath = `${datasetPath}/${country}/${area}/${indexName}/${mapFolder}/actual/${startYear}_${endYear}_actual_${fileSuffix}.geojson?v=${cacheKey}`;
      const actualGridPath = `${datasetPath}/${country}/${area}/${indexName}/${mapFolder}/actual/${startYear}_${endYear}${thresholdPart}_actual_${fileSuffix}.geojson?v=${cacheKey}`;
      // const trendGridPath = `${datasetPath}/${country}/${area}/${indexName}/${mapFolder}/trend/${startYear}_${endYear}_trend_${fileSuffix}.geojson?v=${cacheKey}`;
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

          // Trigger generation API
          // const generateRes = await fetch(`${apiBase}/api/maps/generate`, {
          //   method: "POST",
          //   headers: { "Content-Type": "application/json" },
          //   body: JSON.stringify({
          //     indexName,
          //     datasetName,
          //     country,
          //     province: province || null, // Send null if empty string
          //     startYear: parseInt(startYear, 10),
          //     endYear: parseInt(endYear, 10),
          //     supportsTrend
          //   }),
          // });
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
            throw new Error("Backend failed to generate map data.");
          }

          // Re-fetch after generation ---
          const newCacheKey = Date.now(); 
          // const retryActualPath = `${datasetPath}/${country}/${area}/${indexName}/${mapFolder}/actual/${startYear}_${endYear}_actual_${fileSuffix}.geojson?v=${newCacheKey}`;
          // const retryTrendPath = `${datasetPath}/${country}/${area}/${indexName}/${mapFolder}/trend/${startYear}_${endYear}_trend_${fileSuffix}.geojson?v=${newCacheKey}`;
          const retryActualPath = `${datasetPath}/${country}/${area}/${indexName}/${mapFolder}/actual/${startYear}_${endYear}${thresholdPart}_actual_${fileSuffix}.geojson?v=${newCacheKey}`;
          const retryTrendPath = `${datasetPath}/${country}/${area}/${indexName}/${mapFolder}/trend/${startYear}_${endYear}${thresholdPart}_trend_${fileSuffix}.geojson?v=${newCacheKey}`;

          const retryRequests = [fetchGracefully(retryActualPath)];
          if (supportsTrend) retryRequests.push(fetchGracefully(retryTrendPath));

          const retryResults = await Promise.all(retryRequests);
          actualRes = retryResults[0];
          trendRes = supportsTrend ? retryResults[1] : { status: 200, data: null };

          if (actualRes.status === 404 || (supportsTrend && trendRes.status === 404)) {
            throw new Error("Map generation succeeded, but files are still missing on the server.");
          }
        }

        // Update State ---
        if (isMounted) {
          const actualData = actualRes.data;
          const trendData = trendRes.data;

          // Check if data is truly empty
          if (!actualData?.features?.length && (!supportsTrend || !trendData?.features?.length)) {
            setNoData(true);
          } else {
            setGridData({ actual: actualData, trend: trendData });
            // Extract unit from metadata
            // const u = actualData?.metadata?.unit || trendData?.metadata?.unit || "";
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

  // useEffect(() => {
  //   fetch("/data/southeast-asia-boundary.geojson")
  //     .then((res) => res.json())
  //     // .then(setSeaBoundary)
  //     .then((data) => setBoundaryData(data));
  // }, []);

  // useEffect(() => {
  //   fetch(`/data/boundary/${country}.geojson`)
  //     .then((res) => res.json())
  //     // .then(setSeaBoundary)
  //     .then((data) => setBoundaryData(data));
  // }, [country]);

  // useEffect(() => {
  //   if (!country || country === "SEA") {
  //     setMaskData(null);
  //     return;
  //   }

  //   fetch(`/data/mask/${country}_mask.geojson`)
  //     .then((res) => res.json())
  //     .then(setMaskData);
  // }, [country]);

  // useEffect(() => {
  //   fetch(`/data/mask/Thailand_mask.geojson`)
  //     .then((res) => res.json())
  //     .then(setMaskData);
  // }, []);

// useEffect(() => {
//     if (country === "Test") {
//       fetch(`/data/boundary/Thailand_provinces.geojson`)
//         .then((res) => {
//           if (!res.ok) throw new Error("Province boundary file not found");
//           return res.json();
//         })
//         .then((data) => setAllProvincesData(data))
//         .catch(console.error);
//     } else {
//       setAllProvincesData(null);
//     }
//   }, [country]);
// ==========================================
  // UPDATED: Fetch dynamic shapefile from Backend
  // ==========================================
  // useEffect(() => {
  //   // Check if we have a valid shapefile name
  //   if (shapefileName && shapefileName.trim() !== "") {
  //     const fetchBoundary = async () => {
  //       try {
  //         const res = await apiFetch(`/shapefiles/${shapefileName}/geojson`);
  //         if (!res.ok) throw new Error("Shapefile boundary not found");
          
  //         const data = await res.json();
  //         setAllProvincesData(data);
  //       } catch (error) {
  //         console.error("Failed to load boundary geojson:", error);
  //         setAllProvincesData(null);
  //       }
  //     };
  //     fetchBoundary();
  //   } else {
  //     setAllProvincesData(null);
  //   }
  // }, [shapefileName]); // Trigger only when shapefileName changes
  useEffect(() => {
    // Check if we have both datasetName and country before fetching
    if (datasetName && country) {
      const fetchBoundary = async () => {
        try {
          const apiBase = "http://localhost:8000";
          const datasetPath = datasetName === "default" ? "/data" : `${apiBase}/output/${datasetName}`;
          
          // Construct the static URL: e.g., http://localhost:8000/output/ERA5/Thailand/boundary.geojson
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

        // const customBlueRange = d3.schemeBlues[11].slice(-nBins);
        // const customBlueRange = d3.quantize((t) => d3.interpolateBlues(t * 0.8 + 0.2), nBins);
        
        // const selectedScheme = d3[`scheme${colorSchemes.actual}`] 
        //   ? d3[`scheme${colorSchemes.actual}`][nBins] 
        //   : d3.schemeYlOrRd[nBins];

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
          // .range(d3.schemeYlOrRd[nBins]);
          // .range(customBlueRange);
          // .range(d3.schemeBlues[nBins]); //d3.schemeBlues d3.schemeYlOrRd

        setScales((s) => ({ ...s, actual: scale }));
        setBinsAll((b) => ({ ...b, actual: thresholds }));
      } else {
        const absMax =
          userMin != null || userMax != null
            ? Math.max(Math.abs(minVal), Math.abs(maxVal))
            : Math.max(Math.abs(autoMin), Math.abs(autoMax));

        if (absMax === 0) return;

        const thresholds = d3.ticks(-absMax, absMax, nBins);

        // const colors = [...d3.schemeRdBu[nBins]]; //.reverse()
        const rawSchemeName = colorSchemes.trend;
        const isReversed = rawSchemeName.startsWith("-");
        const cleanSchemeName = isReversed ? rawSchemeName.substring(1) : rawSchemeName;

        // const selectedScheme = d3[`scheme${colorSchemes.trend}`]
        //   ? [...d3[`scheme${colorSchemes.trend}`][nBins]]
        //   : [...d3.schemeRdBu[nBins]];
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
          // .range(colors);

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
      stroke: false,
      weight: 0,
      color: "none",
      fillOpacity: 0.8,
      interactive: true,
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
    <div className="card border-0">
      
      {/* 1. Header Section: Mode Buttons & Map Title */}
      <div className="card-header bg-white d-flex justify-content-between align-items-center p-3 border-bottom">
        
        {/* Left: Mode Buttons (Grouped for better UI) */}
        <div className="btn-group" role="group">
          <button
            onClick={() => setMode("actual")}
            className={`btn btn-sm ${mode === "actual" ? "btn-primary shadow-sm" : "btn-outline-secondary"}`}
          >
            Actual Map
          </button>
          <button
            onClick={() => setMode("trend")}
            className={`btn btn-sm ${mode === "trend" ? "btn-primary shadow-sm" : "btn-outline-secondary"}`}
            title={!supportsTrend ? "Trend map is not available for raw variables" : "View Trend Map"}
            disabled={!supportsTrend}
          >
            Trend Map
          </button>
        </div>

        {/* Center: Checkbox for Significant Points (Only in Trend mode) */}
        {mode === "trend" && (
          <div className="form-check form-switch mb-0 ms-3 me-auto">
            <input
              className="form-check-input"
              type="checkbox"
              id="sigPointsToggle"
              checked={showSig}
              onChange={() => setShowSig((s) => !s)}
            />
            <label className="form-check-label small text-muted fw-bold" htmlFor="sigPointsToggle">
              Significant Points (p &lt; 0.05)
            </label>
          </div>
        )}

        {/* Right: Dynamic Map Title */}
        <div className="text-end">
          <h6 className="mb-0 fw-bold text-secondary">
            {indexName} {
              mode === "actual" 
                ? (indexName.includes("Frequency") ? "Sum" : "Average") 
                : "Trend"
            } Map
          </h6>
          <small className="text-muted">
            {startYear} - {endYear} {isSPIEvent && `| Threshold ${spiThreshold}`} {province ? `| ${province}` : "| Whole Country"}
          </small>
        </div>
      </div>

      {/* 2. Checkbox for Significant Points (Only in Trend mode) */}
      {/* {mode === "trend" && (
        <div className="px-3 pt-2">
          <div className="form-check form-switch">
            <input
              className="form-check-input"
              type="checkbox"
              id="sigPointsToggle"
              checked={showSig}
              onChange={() => setShowSig((s) => !s)}
            />
            <label className="form-check-label small text-muted" htmlFor="sigPointsToggle">
              Show Significant Points (p &lt; 0.05)
            </label>
          </div>
        </div>
      )} */}

      {/* 3. Map Container */}
      <div className="card-body p-0 position-relative">
        <MapContainer
          key={`map-container-${country}`} // Force re-mount of map ONLY when country changes
          // center={mapView.center}
          // zoom={mapView.zoom}
          zoomSnap={0.25}  // Enable fractional zoom snapping to 0.25 increments
          zoomDelta={0.25} // Set zoom step for +/- buttons to 0.25
          style={{ height: "750px", width: "100%", zIndex: 0 }} //450px
          // preferCanvas={true} //  Use Canvas instead of SVG for crisp vector edges
        >
          {/* Boundary always on top */}
          {/* {allProvincesData && <BoundaryLayer data={allProvincesData} weight={1.0} />} */}
          {displayProvinceBoundary && (
            <BoundaryLayer data={displayProvinceBoundary} weight={1.0} />
          )}

          {/* <MapViewUpdater center={mapView.center} zoom={mapView.zoom} /> */}
          <MapBoundsController 
            province={province} 
            allProvincesData={allProvincesData} // geojsonData={displayProvinceBoundary} 
            targetCol={targetCol} // fallbackView={mapView} 
          />

          {/* Mask first */}
          {/* {maskData && <BoundaryMaskLayer mask={maskData} />} */}


          {/* Province Boundaries */}
          {/* {displayProvinceBoundary && (
            <BoundaryLayer data={displayProvinceBoundary} weight={1.0} />
          )} */}

          {allProvincesData && (
            <CountryContextLayer 
              data={allProvincesData} 
              selectedProvince={province} 
            />
          )}

          {/* Map Data Layers */}
          {mode === "trend" && gridData.trend && (
            <GeoJSON
              // key={`trend-${indexName}-${startYear}-${endYear}-${province}-${mapStyle}`}
              // key={`geojson-trend-${indexName}-${startYear}-${endYear}-${province}-${mapStyle}-${Date.now()}`}
              key={`geojson-trend-${indexName}-${startYear}-${endYear}-${province}-${mapStyle}-${spiThreshold}`}
              data={gridData.trend}
              style={style("trend")}
              onEachFeature={onEachFeature("trend")}
              ref={(ref) => (layersRef.current.trend = ref)}
            />
          )}
          {mode === "actual" && gridData.actual && (
            <GeoJSON
              // key={`actual-${indexName}-${startYear}-${endYear}-${province}-${mapStyle}`}
              // key={`geojson-actual-${indexName}-${startYear}-${endYear}-${province}-${mapStyle}-${Date.now()}`}
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
      </div>

      {/* 4. Legend & Controls Footer */}
      <div className="card-footer bg-white border-top pt-2 pb-3 px-0">
        
        {/* Color Bar */}
        {/* {scales[mode] && binsAll[mode]?.length > 0 && (
          <div className="mb-2">
            <Legend
              bins={binsAll[mode]}
              scale={scales[mode]}
              mode={mode}
              unit={unit}
              indexName={indexName}
              isSPIEvent={isSPIEvent}
            />
          </div>
        )} */}
        {((scales[mode] && binsAll[mode]?.length > 0) || (mode === "trend" && isSPIEvent && gridData[mode])) && (
          <div className="mb-2">
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
        {/* d-flex justify-content-between align-items-center px-3 */}
        <div className="d-flex flex-wrap justify-content-between align-items-center px-3 gap-3">

        {/* d-flex align-items-center gap-3 */}
        <div className=" d-flex flex-wrap align-items-center gap-3">

          {!(mode === "trend" && isSPIEvent) && (
            <>

                {/* 1. Color Palette Selector */}
                <div className="d-flex align-items-center gap-2">
                  <span className="small fw-bold text-muted">Color:</span>
                  <select
                    className="form-select form-select-sm"
                    style={{ width: "140px" }}
                    value={colorSchemes[mode]}
                    onChange={(e) =>
                      setColorSchemes((prev) => ({ ...prev, [mode]: e.target.value }))
                    }
                  >
                    {mode === "actual" ? (
                      <>
                        <optgroup label="Temperature">
                          <option value="YlOrRd">Yellow-Orange-Red</option>
                          <option value="OrRd">Orange-Red</option>
                          <option value="Reds">Reds</option>
                        </optgroup>
                        <optgroup label="Precipitation">
                          <option value="Blues">Blues</option>
                          <option value="YlGnBu">Yellow-Green-Blue</option>
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
              {/* d-flex justify-content-center align-items-center gap-1 */}
                <div className="d-flex flex-wrap align-items-center gap-1">
                  <span className="small fw-bold text-muted me-2">Legend Range:</span>

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
                    className="form-control form-control-sm text-center"
                    style={{ width: "65px" }}
                  />
                  
                  <span className="text-muted">-</span>

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
                    className="form-control form-control-sm text-center"
                    style={{ width: "65px" }}
                  />

                  <button
                    className="btn btn-sm btn-outline-secondary ms-2"
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

        {/* d-flex justify-content-end gap-1 */}
          <div 
            className="d-flex align-items-center gap-1" 
          >
            <button
              className={`btn btn-sm ${mapStyle === "grid" ? "btn-secondary" : "btn-outline-secondary"}`}
              onClick={() => setMapStyle("grid")}
              title="Show as Grid"
              disabled={!!province}
            >
              Grid
            </button>
            <button
              className={`btn btn-sm ${mapStyle === "shapefile" ? "btn-secondary" : "btn-outline-secondary"}`}
              onClick={() => setMapStyle("shapefile")}
              // title="Show as Shapefile Area Average"
              // disabled={!!province}
              // Dynamic title based on availability
              title={!hasSubAreas ? "Shapefile mode requires multiple sub-areas" : "Show as Shapefile Area Average"}
              // Disable if a province is selected OR if there are no sub-areas
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