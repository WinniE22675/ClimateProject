import { useEffect, useState, useMemo, useRef } from "react";
import { MapContainer, GeoJSON, CircleMarker, useMap } from "react-leaflet"; // Circle,
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

function MapBoundsController({ province, allProvincesData, fallbackView }) { // geojsonData
  const map = useMap();

  useEffect(() => {
    // 1. If a specific province is selected, calculate its bounds and zoom
    // if (province && geojsonData && geojsonData.features && geojsonData.features.length > 0) {
    // Create a temporary Leaflet layer to calculate the bounding box
    // 1. If a province is selected, find its specific boundary and zoom to it
    if (province && allProvincesData && allProvincesData.features) {
      const provinceFeature = allProvincesData.features.find(
        (f) => f.properties.ADM1_EN === province
      );

      if (provinceFeature) {
        // Create a temporary layer JUST for this province to calculate perfect bounds
        const layer = L.geoJSON(provinceFeature); // geojsonData
        const bounds = layer.getBounds();
        
        if (bounds.isValid()) {
          // fitBounds automatically calculates the perfect center and zoom level!
          // padding ensures the map doesn't touch the exact edges of the container
          map.fitBounds(bounds, { padding: [30, 30], animate: true });
        }
      }
    } 
    // 2. If no province is selected (Whole Country), use the default COUNTRY_VIEW
    else if (fallbackView) {
      map.setView(fallbackView.center, fallbackView.zoom, { animate: true });
    }
  }, [province, allProvincesData, fallbackView, map]); // geojsonData

  return null;
}

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
        stroke: false,
        weight: 0,
        interactive: false,
      },
    }).addTo(map);

    return () => map.removeLayer(layer);
  }, [map, mask]);

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
      smoothFactor: 0.99,
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
      smoothFactor: 0.99,
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
      "r99ptot"
    ];
    
    // Check if the current index is related to rain/precipitation
    const isRain = rainIndices.includes(indexName.toLowerCase());

    setColorSchemes({
      actual: isRain ? "Blues" : "YlOrRd",
      trend: "RdBu",
    });
  }, [indexName]);

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

      // Dynamically select folder based on mapStyle state
      const mapFolder = mapStyle === "shapefile" ? "maps_shp" : "maps_grid";
      const fileSuffix = mapStyle === "shapefile" ? "shp" : "grid";
      // const mapFolder = mapStyle === "shapefile" ? "maps_grid" : "maps_grid";
      // const fileSuffix = mapStyle === "shapefile" ? "grid" : "grid";

      // Construct file paths based on the domain-centric structure
      // const actualGridPath = `${datasetPath}/${country}/${area}/${indexName}/maps_grid/actual/${startYear}_${endYear}_actual_grid.geojson?v=${cacheKey}`;
      // const trendGridPath = `${datasetPath}/${country}/${area}/${indexName}/maps_grid/trend/${startYear}_${endYear}_trend_grid.geojson?v=${cacheKey}`;
      const actualGridPath = `${datasetPath}/${country}/${area}/${indexName}/${mapFolder}/actual/${startYear}_${endYear}_actual_${fileSuffix}.geojson?v=${cacheKey}`;
      const trendGridPath = `${datasetPath}/${country}/${area}/${indexName}/${mapFolder}/trend/${startYear}_${endYear}_trend_${fileSuffix}.geojson?v=${cacheKey}`;

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

          // Re-fetch after generation ---
          const newCacheKey = Date.now(); 
          // const retryActualPath = `${datasetPath}/${country}/${area}/${indexName}/maps_grid/actual/${startYear}_${endYear}_actual_grid.geojson?v=${newCacheKey}`;
          // const retryTrendPath = `${datasetPath}/${country}/${area}/${indexName}/maps_grid/trend/${startYear}_${endYear}_trend_grid.geojson?v=${newCacheKey}`;
          const retryActualPath = `${datasetPath}/${country}/${area}/${indexName}/${mapFolder}/actual/${startYear}_${endYear}_actual_${fileSuffix}.geojson?v=${newCacheKey}`;
          const retryTrendPath = `${datasetPath}/${country}/${area}/${indexName}/${mapFolder}/trend/${startYear}_${endYear}_trend_${fileSuffix}.geojson?v=${newCacheKey}`;

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
  }, [indexName, datasetName, country, province, startYear, endYear , mapStyle]);

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

useEffect(() => {
    if (country === "Thailand") {
      fetch(`/data/boundary/Thailand_provinces.geojson`)
        .then((res) => {
          if (!res.ok) throw new Error("Province boundary file not found");
          return res.json();
        })
        .then((data) => setAllProvincesData(data))
        .catch(console.error);
    } else {
      setAllProvincesData(null);
    }
  }, [country]);

  const displayProvinceBoundary = useMemo(() => {
    if (!allProvincesData) return null;
    
    // if select "Whole Country" (province is space ("")) will show province line 
    if (!province) {
      return allProvincesData;
    }

    // if select province will Filter select only Feature of that province
    // Note: check Property name in GeoJSON files 
    const filteredFeatures = allProvincesData.features.filter(
      (f) => f.properties.ADM1_EN === province
    );

    // Reassemble back into GeoJSON Object
    return {
      type: "FeatureCollection",
      features: filteredFeatures,
    };
  }, [allProvincesData, province]);

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
    return {
      fillColor:
        scales[modeKey] && val != null && !isNaN(val) // from color scale func. if have scale fill color, but if have not is gray color
          ? scales[modeKey](val)
          : "#dddddd",
      stroke: false,
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
    // const coords = feature.geometry?.coordinates?.[0];
    // if (!coords || coords.length < 4) return null;

    // const coords = feature.geometry.coordinates[0];
    // const pt1 = turf.point(coords[0]); // left up
    // const pt2 = turf.point(coords[1]); // right down (diagonal opposite)
    // const cellSizeKm = turf.distance(pt1, pt2, { units: "kilometers" });
    // const radiusMeters = (cellSizeKm * 1000) / 10; // convert to m and * 10 for make circle

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
  //   return (
  //     <Circle
  //       center={[center[1], center[0]]}
  //       radius={radiusMeters}
  //       pathOptions={{
  //         color: "black",
  //         fillColor: "black",
  //         fillOpacity: 0.9,
  //         interactive: false,
  //       }}
  //     />
  //   );
  // }


  // p-2 small padding

  const onEachFeature = (modeKey) => (feature, layer) => {
    // layer.on("click", () => console.log("clicked"));
    // console.log("bind tooltip:", modeKey);
    // layer.on("click", () => {
    //   console.log("clicked", modeKey);
    // });
    let html = "";
    const namePrefix = feature.properties.name ? `<strong>${feature.properties.name}</strong><br/>` : "";

    if (modeKey === "actual") {
      const val = feature.properties.value;
      html = `${namePrefix} Value: ${val != null ? val.toFixed(2) : "N/A"} ${unit}`;
    } else if (modeKey === "trend") {
      const slope = feature.properties.slope;
      const pval = feature.properties.p;
      html = `${namePrefix} Slope: ${slope != null ? slope.toFixed(2) : "N/A"}<br/>p-value: ${
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
    <div className="card  border-0">
      
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
              Show Significant Points (p &lt; 0.05)
            </label>
          </div>
        )}

        {/* Right: Dynamic Map Title */}
        <div className="text-end">
          <h6 className="mb-0 fw-bold text-secondary">
            {indexName} {mode === "actual" ? "Average" : "Trend"} Map
          </h6>
          <small className="text-muted">
            {startYear} - {endYear} {province ? `| ${province}` : "| Whole Country"}
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
          center={mapView.center}
          zoom={mapView.zoom}
          zoomSnap={0.25}  // Enable fractional zoom snapping to 0.25 increments
          zoomDelta={0.25} // Set zoom step for +/- buttons to 0.25
          style={{ height: "450px", width: "100%", zIndex: 0 }} //450px
          preferCanvas={true} //  Use Canvas instead of SVG for crisp vector edges
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
            fallbackView={mapView} 
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
              key={`trend-${indexName}-${startYear}-${endYear}-${province}-${mapStyle}`}
              data={gridData.trend}
              style={style("trend")}
              onEachFeature={onEachFeature("trend")}
              ref={(ref) => (layersRef.current.trend = ref)}
            />
          )}
          {mode === "actual" && gridData.actual && (
            <GeoJSON
              key={`actual-${indexName}-${startYear}-${endYear}-${province}-${mapStyle}`}
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
        {scales[mode] && binsAll[mode]?.length > 0 && (
          <div className="mb-2">
            <Legend
              bins={binsAll[mode]}
              scale={scales[mode]}
              mode={mode}
              unit={unit}
            />
          </div>
        )}
        {/* d-flex justify-content-between align-items-center px-3 */}
        <div className="d-flex flex-wrap justify-content-between align-items-center px-3 gap-3">

        {/* d-flex align-items-center gap-3 */}
        <div className=" d-flex flex-wrap align-items-center gap-3">

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
            title="Show as Shapefile Area Average"
            disabled={!!province}
          >
            Shapefile
          </button>
        </div>
        </div>
      </div>
    </div>
  );
}
//   return (
//     <div>
//       {/* mode button */}
//       <div className="d-flex gap-2 p-2">
//         <button
//           onClick={() => setMode("actual")}
//           className={`btn ${mode === "actual" ? "btn-primary shadow-sm" : "btn-light border"}`}
//         >
//           Actual Map
//         </button>
//         <button
//           onClick={() => setMode("trend")}
//           className={`btn ${mode === "trend" ? "btn-primary shadow-sm" : "btn-light border"}`}
//         >
//           Trend Map
//         </button>
//       </div>

//       {/* toggle significant points */}
//       {mode === "trend" && (
//         <div className="p-2">
//           <label>
//             <input
//               type="checkbox"
//               checked={showSig}
//               onChange={() => setShowSig((s) => !s)}
//             />{" "}
//             Significant Points
//           </label>
//         </div>
//       )}
//       <div className="flex flex-col">
//         <MapContainer
//           // center={[15, 101]}
//           // zoom={5}
//           center={mapView.center}
//           zoom={mapView.zoom}
//           style={{ height: "450px", width: "100%" }}
//         >
//           <MapViewUpdater center={mapView.center} zoom={mapView.zoom} />

//           {/* {maskData && <BoundaryMaskLayer mask={maskData} />} */}

//           {/* Mask first */}
//           {maskData && <BoundaryMaskLayer mask={maskData} />}

//           {/* Boundary always on top */}
//           {boundaryData && <BoundaryLayer data={boundaryData} weight={2.0}/>}

//           {/* Province Boundaries */}
//           {displayProvinceBoundary && (
//             <BoundaryLayer data={displayProvinceBoundary} weight={1.0} />
//           )}

//           {/* SEA view */}
//           {/* {seaBoundary && !countryBoundary && (
//             <BoundaryLayer data={seaBoundary} type="sea" />
//           )} */}

//           {/* Country view */}
//           {/* {countryBoundary && (
//             <BoundaryLayer data={countryBoundary} type="country" />
//           )} */}

//           {mode === "trend" && gridData.trend && (
//             <GeoJSON
//               data={gridData.trend}
//               style={style("trend")}
//               onEachFeature={onEachFeature("trend")}
//               ref={(ref) => (layersRef.current.trend = ref)}
//             />
//           )}
//           {mode === "actual" && gridData.actual && (
//             <GeoJSON
//               data={gridData.actual}
//               style={style("actual")}
//               onEachFeature={onEachFeature("actual")}
//               ref={(ref) => (layersRef.current.actual = ref)}
//             />
//           )}

//           {showSig &&
//             significantPoints.map((f, i) => <SigPoint key={i} feature={f} />)}
//         </MapContainer>

//         {scales[mode] && binsAll[mode]?.length > 0 && (
//           <Legend
//             bins={binsAll[mode]}
//             scale={scales[mode]}
//             mode={mode}
//             unit={unit}
//           />
//         )}
//       </div>

//       {/* legend range control */}
//       <div className="flex gap-2 p-2 items-center">
//         <span className="text-sm">Legend range:</span>

//         <input
//           type="number"
//           placeholder="Min"
//           value={legendRange[mode].min ?? ""}
//           onChange={(e) =>
//             setLegendRange((r) => ({
//               ...r,
//               [mode]: {
//                 ...r[mode],
//                 min: e.target.value === "" ? null : +e.target.value,
//               },
//             }))
//           }
//           className="border px-1 w-24"
//         />

//         <input
//           type="number"
//           placeholder="Max"
//           value={legendRange[mode].max ?? ""}
//           onChange={(e) =>
//             setLegendRange((r) => ({
//               ...r,
//               [mode]: {
//                 ...r[mode],
//                 max: e.target.value === "" ? null : +e.target.value,
//               },
//             }))
//           }
//           className="border px-1 w-24"
//         />

//         <button
//           className="text-sm underline"
//           onClick={() =>
//             setLegendRange((r) => ({
//               ...r,
//               [mode]: { min: null, max: null },
//             }))
//           }
//         >
//           Auto
//         </button>
//       </div>

//     </div>
//   );
// }
