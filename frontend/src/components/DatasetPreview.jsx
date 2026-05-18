import React, { useState, useEffect } from "react";

export default function DatasetPreview({ metadata, selectedFile, onSelectFile }) {
  const [error, setError] = useState(null);

  if (error)
    return <p style={{ color: "red" }}>Error: {JSON.stringify(error)}</p>;
  if (!metadata) return <p>No metadata available.</p>;

  const metaList = Array.isArray(metadata) ? metadata : [];
  const current = metaList[selectedFile] || null;

  if (!current) return <p>No metadata found.</p>;

  const {
    variables = [],
    standard_names,
    variable_units = {},
    shape = {},
    lat_min,
    lat_max,
    lon_min,
    lon_max,
    time_start,
    time_end,
    time_years,
    spatial_resolution,
    calendar,
  } = current;

  return (
    <div className="bg-white rounded-lg border border-gray-200 h-full overflow-hidden">
      
      {/* Header of Preview */}
      <div className="bg-white border-b border-gray-200 py-3 px-4 flex justify-between items-center min-h-[60px]">
        <h5 className="m-0 font-bold text-gray-900 text-lg">Dataset Preview</h5>
        
        {metaList.length > 1 && (
          <select
            className="block w-auto text-sm border border-gray-300 rounded-md px-2 py-1 shadow-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white"
            value={selectedFile}
            onChange={(e) => onSelectFile(parseInt(e.target.value))}
          >
            {metaList.map((m, i) => (
              <option key={i} value={i}>
                {m.filename || `File ${i + 1}`}
              </option>
            ))}
          </select>
        )}
      </div>

      <div className="p-4 text-[0.9rem]">
        
        {/* VARIABLES */}
        <h6 className="font-bold text-blue-600 mb-3 text-base">Variables</h6>
        <div className="flex flex-col border border-gray-200 rounded-md mb-4 shadow-sm divide-y divide-gray-200">
          {variables.map((v) => {
            const std = standard_names?.[v] || null;
            const unit = variable_units?.[v] || null;
            return (
              <div key={v} className="bg-gray-50 p-3">
                <span className="font-bold text-gray-900">{std || v}</span>
                {unit && <span className="inline-block bg-gray-500 text-white text-xs font-bold px-2 py-0.5 rounded-full ml-2">{unit}</span>}
                {!std && unit && <div className="text-gray-500 text-sm mt-1">({v})</div>}
              </div>
            );
          })}
        </div>

        {/* Tailwind Grid replaces Bootstrap Row/Col */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* DIMENSIONS */}
          <div>
            <h6 className="font-bold text-blue-600 mb-2 text-base">Dimensions</h6>
            <ul className="list-none text-gray-500 m-0 p-0">
              {Object.entries(shape).map(([key, value]) => (
                <li key={key} className="mb-1">
                  <span className="font-bold text-gray-900 capitalize">{key}:</span> {value}
                </li>
              ))}
            </ul>
          </div>

          {/* SPATIAL INFO */}
          <div>
            <h6 className="font-bold text-blue-600 mb-2 text-base">Spatial Coverage</h6>
            <ul className="list-none text-gray-500 m-0 p-0">
              <li className="mb-1"><span className="font-bold text-gray-900">Latitude:</span> {lat_min ?? "-"} → {lat_max ?? "-"}</li>
              <li className="mb-1"><span className="font-bold text-gray-900">Longitude:</span> {lon_min ?? "-"} → {lon_max ?? "-"}</li>
              {spatial_resolution && (
                <li><span className="font-bold text-gray-900">Resolution:</span> {spatial_resolution}</li>
              )}
            </ul>
          </div>
        </div>

        <hr className="my-4 border-gray-200" />

        {/* TEMPORAL INFO */}
        <h6 className="font-bold text-blue-600 mb-2 text-base">Temporal Coverage</h6>
        <ul className="list-none text-gray-500 m-0 p-0">
          <li className="mb-1">
            <span className="font-bold text-gray-900">Time Range:</span> {time_start ?? "-"} → {time_end ?? "-"}
          </li>
          {time_years && (
            <li className="mb-1">
              <span className="font-bold text-gray-900">Time Span:</span> {time_years} years
            </li>
          )}
          {calendar && (
            <li className="mb-1">
              <span className="font-bold text-gray-900">Calendar:</span> {calendar}
            </li>
          )}
        </ul>

      </div>
    </div>
  );
}