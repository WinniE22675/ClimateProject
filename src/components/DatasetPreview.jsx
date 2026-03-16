import React, { useState, useEffect } from "react";

export default function DatasetPreview({ metadata, selectedFile, onSelectFile }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(false);

    if (metadata?.status === "error") {
      setError(metadata.errors || "Failed to load metadata");
    }
  }, [metadata]);

  if (loading) return <p>Loading metadata...</p>;
  if (error)
    return <p style={{ color: "red" }}>Error: {JSON.stringify(error)}</p>;
  if (!metadata) return <p>No metadata available.</p>;

  // const metaList = Array.isArray(metadata) ? metadata : [metadata];
  // const metaList = Array.isArray(metadata)
  //   ? metadata.filter((m) => !m.error)
    // : [];
  // const current = metaList[selectedFile];
  const metaList = Array.isArray(metadata) ? metadata : [];
  const current = metaList[selectedFile] || null;

  if (!current) return <p>No metadata found.</p>;

  const {
    // filename,
    // file_size,
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
    // error,
  } = current;

  return (
    <div className="card shadow-sm border-0 h-100">
      
      {/* Header ของ Preview */}
      <div className="card-header bg-white border-bottom py-2 d-flex justify-content-between align-items-center" style={{ minHeight: "60px" }}>
        <h5 className="mb-0 fw-bold text-dark">Dataset Preview</h5>
        
        {metaList.length > 1 && (
          <select
            className="form-select form-select-sm w-auto shadow-sm"
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

      <div className="card-body p-3" style={{ fontSize: "0.9rem" }}>
        
        {/* VARIABLES */}
        <h6 className="fw-bold text-primary mb-3">Variables</h6>
        <div className="list-group list-group-flush border rounded mb-4 shadow-sm">
          {variables.map((v) => {
            const std = standard_names?.[v] || null;
            const unit = variable_units?.[v] || null;
            return (
              <div key={v} className="list-group-item bg-light p-2">
                <span className="fw-bold text-dark">{std || v}</span>
                {unit && <span className="badge bg-secondary ms-2">{unit}</span>}
                {!std && unit && <div className="text-muted small mt-1">({v})</div>}
              </div>
            );
          })}
        </div>

        <div className="row g-4">
          {/* DIMENSIONS */}
          <div className="col-12 col-md-6">
            <h6 className="fw-bold text-primary mb-2">Dimensions</h6>
            <ul className="list-unstyled text-muted mb-0">
              {Object.entries(shape).map(([key, value]) => (
                <li key={key} className="mb-1">
                  <span className="fw-bold text-dark text-capitalize">{key}:</span> {value}
                </li>
              ))}
            </ul>
          </div>

          {/* SPATIAL INFO (ปรับเป็นชื่อเต็ม) */}
          <div className="col-12 col-md-6">
            <h6 className="fw-bold text-primary mb-2">Spatial Coverage</h6>
            <ul className="list-unstyled text-muted mb-0">
              <li className="mb-1"><span className="fw-bold text-dark">Latitude:</span> {lat_min} → {lat_max}</li>
              <li className="mb-1"><span className="fw-bold text-dark">Longitude:</span> {lon_min} → {lon_max}</li>
              {spatial_resolution && (
                <li><span className="fw-bold text-dark">Resolution:</span> {spatial_resolution}</li>
              )}
            </ul>
          </div>
        </div>

        <hr className="my-3 text-muted" />

        {/* TEMPORAL INFO (เอาแบบกล่องออก และใช้ชื่อเต็ม / ข้อมูลเต็ม) */}
        <h6 className="fw-bold text-primary mb-2">Temporal Coverage</h6>
        <ul className="list-unstyled text-muted mb-0">
          <li className="mb-1">
            <span className="fw-bold text-dark">Time Range:</span> {time_start} → {time_end}
          </li>
          {time_years && (
            <li className="mb-1">
              <span className="fw-bold text-dark">Time Span:</span> {time_years} years
            </li>
          )}
          {calendar && (
            <li className="mb-1">
              <span className="fw-bold text-dark">Calendar:</span> {calendar}
            </li>
          )}
        </ul>

      </div>
    </div>
  );
}