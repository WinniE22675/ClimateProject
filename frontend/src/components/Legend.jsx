import { useState, useEffect, useRef } from "react";

export default function Legend({ bins, scale, mode, unit, indexName, isSPIEvent }) {
  const [width, setWidth] = useState(240); // default width
  const height = 20;
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // ResizeObserver catch container size
    const resizeObserver = new ResizeObserver((entries) => {
      for (let entry of entries) {
        if (entry.contentRect) {
          setWidth(entry.contentRect.width); // update width
        }
      }
    });

    resizeObserver.observe(containerRef.current);

    // cleanup
    return () => resizeObserver.disconnect();
  }, []);
  
  // if (mode === "trend" && isSPIEvent) {
  //   return (
  //     <div className="d-flex flex-column align-items-center w-100 mt-2 px-4">
  //       <div className="d-flex flex-wrap justify-content-center align-items-center gap-4">
          
  //         {/* Increasing Box */}
  //         <div className="d-flex align-items-center gap-2">
  //           <div style={{ width: "30px", height: "16px", backgroundColor: "#d73027", borderRadius: "2px" }}></div>
  //           <span className="small fw-bold text-dark">Increasing</span>
  //         </div>
          
  //         {/* No Trend Box */}
  //         <div className="d-flex align-items-center gap-2">
  //           <div style={{ width: "30px", height: "16px", backgroundColor: "#dddddd", border: "1px solid #bbbbbb", borderRadius: "2px" }}></div>
  //           <span className="small fw-bold text-dark">No Trend</span>
  //         </div>
          
  //         {/* Decreasing Box */}
  //         <div className="d-flex align-items-center gap-2">
  //           <div style={{ width: "30px", height: "16px", backgroundColor: "#1f77b4", borderRadius: "2px" }}></div>
  //           <span className="small fw-bold text-dark">Decreasing</span>
  //         </div>

  //       </div>
        
  //       {/* Legend Title */}
  //       <div className="text-center mt-2">
  //         <small className="text-muted fw-bold">Trend Direction</small>
  //       </div>
  //     </div>
  //   );
  // }
  if (mode === "trend" && isSPIEvent) {
    return (
      <div className="flex flex-col items-center w-full mt-2 px-4">
        <div className="flex flex-wrap justify-center items-center gap-4">
          
          {/* Increasing Box */}
          <div className="flex items-center gap-2">
            <div style={{ width: "30px", height: "16px", backgroundColor: "#d73027", borderRadius: "2px" }}></div>
            <span className="text-sm font-bold text-gray-900">Increasing</span>
          </div>
          
          {/* No Trend Box */}
          <div className="flex items-center gap-2">
            <div style={{ width: "30px", height: "16px", backgroundColor: "#dddddd", border: "1px solid #bbbbbb", borderRadius: "2px" }}></div>
            <span className="text-sm font-bold text-gray-900">No Trend</span>
          </div>
          
          {/* Decreasing Box */}
          <div className="flex items-center gap-2">
            <div style={{ width: "30px", height: "16px", backgroundColor: "#1f77b4", borderRadius: "2px" }}></div>
            <span className="text-sm font-bold text-gray-900">Decreasing</span>
          </div>

        </div>
        
        {/* Legend Title */}
        <div className="text-center mt-2">
          <small className="text-gray-500 font-bold">Trend Direction</small>
        </div>
      </div>
    );
  }

  if (!bins || !scale) return null;

  const formatLegendValue = (v) => {
    // 1. Force 0 decimals if the unit is "days"
    if (unit && unit.toLowerCase().includes("days")) {
      return Math.round(v).toString();
    }

    // 2. SPI Event Specific Rules
    if (indexName.startsWith("SPI")) {
      if (indexName.includes("Frequency")) {
        // Frequency: no forced decimal, but usually it's an integer
        return Math.round(v).toString();
      }
      if (indexName.includes("Duration") || indexName.includes("Peak") || indexName.includes("Severity")) {
        // Duration, Peak, Severity: 2 decimals
        return v.toFixed(2);
      }
    }

    // 3. Value-based Rules
    // If absolute value is greater than or equal to 10, force 0 decimals
    if (Math.abs(v) >= 10) {
      return Math.round(v).toString();
    }
    
    // If value is less than 0 (and not handled by above rules), use 2 decimals
    if (v < 0) {
      return v.toFixed(2);
    }

    // 4. Default rules based on data span (Fallback for other indices)
    const span = Math.abs(bins[bins.length - 1] - bins[0]);
    if (span < 0.05) return v.toFixed(3);
    if (span < 1) return v.toFixed(2);
    
    return Math.round(v).toString();
  };

  // return (
  //   <div ref={containerRef} style={{ width: "100%" }}>
  //     <svg
  //       width={width}
  //       height={60}
  //       style={{ display: "block", margin: "0 auto" }}
  //     >
  return (
    <div ref={containerRef} className="w-full">
      <svg
        width={width}
        height={60}
        className="block mx-auto"
      >
        {/* color of bin */}
        {bins.slice(0, -1).map((b, i) => {
          const x0 = (i / (bins.length - 1)) * width;
          const x1 = ((i + 1) / (bins.length - 1)) * width;
          const mid = (bins[i] + bins[i + 1]) / 2;

          // sample
          // bins [0, 10, 20, 30], width=240, height=20
          // i=0: x0=0, x1=80, mid=5 → rect at x=0 width=80 fill=scale(5)
          // i=1: x0=80, x1=160, mid=15 → rect at x=80 width=80 fill=scale(15)
          // i=2: x0=160,x1=240, mid=25 → rect at x=160 width=80 fill=scale(25)

          return (
            <rect
              key={`bin-${i}`}
              x={x0}
              y={0}
              width={x1 - x0}
              height={height}
              fill={scale(mid)}
              stroke="white"
              strokeWidth={0.5}
            />
          );
        })}

        {/* tick marks + labels */}
        {bins.map((b, i) => {
          const x = (i / (bins.length - 1)) * width;
          return (
            <g key={`tick-${i}`} transform={`translate(${x},${height})`}>
              <line y2="6" stroke="black" />
              <text
                dy="1.4em"
                fontSize="10"
                textAnchor={
                  i === 0 ? "start" : i === bins.length - 1 ? "end" : "middle"
                }
              >
                {formatLegendValue(b)}
              </text>
            </g>
          );
        })}

        {/* Title/Unit */}
        <text x={width / 2} y={height + 30} textAnchor="middle" fontSize="12">
          {mode === "actual" ? unit || "" : `Trend (${unit || ""}/decade)`}
        </text>
      </svg>
    </div>
  );
}
