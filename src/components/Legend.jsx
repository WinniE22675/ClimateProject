import { useState, useEffect, useRef } from "react";

export default function Legend({ bins, scale, mode, unit }) {
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

  const formatLegendValue = (v) => {
    const span = Math.abs(bins[bins.length - 1] - bins[0]);
    if (span < 0.05) return v.toFixed(3);
    if (span < 1) return v.toFixed(2);
    // if (span < 10) return v.toFixed(1);
    return Math.round(v).toString();
  };

  return (
    <div ref={containerRef} style={{ width: "100%" }}>
      <svg
        width={width}
        height={60}
        style={{ display: "block", margin: "0 auto" }}
      >
        {/* สีของ bin */}
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
