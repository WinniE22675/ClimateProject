// import { useState, useEffect, useRef } from "react";

// export default function RawLegend({ bins, scale, unit }) {
//   const [width, setWidth] = useState(240);
//   const height = 20;
//   const ref = useRef(null);

//   useEffect(() => {
//     if (!ref.current) return;

//     const resizeObserver = new ResizeObserver((entries) => {
//       for (let e of entries) {
//         setWidth(e.contentRect.width);
//       }
//     });

//     resizeObserver.observe(ref.current);
//     return () => resizeObserver.disconnect();
//   }, []);

//   const formatValue = (v) => {
//     const span = Math.abs(bins[bins.length - 1] - bins[0]);
//     if (span < 0.05) return v.toFixed(3);
//     if (span < 1) return v.toFixed(2);
//     if (span < 10) return v.toFixed(1);
//     return Math.round(v);
//   };

//   return (
//     <div ref={ref} style={{ width: "100%" }}>
//       <svg
//         width={width}
//         height={60}
//         style={{ display: "block", margin: "0 auto" }}
//       >
//         {/* Color bins */}
//         {bins.slice(0, -1).map((b, i) => {
//           const x0 = (i / (bins.length - 1)) * width;
//           const x1 = ((i + 1) / (bins.length - 1)) * width;
//           const mid = (bins[i] + bins[i + 1]) / 2;

//           return (
//             <rect
//               key={i}
//               x={x0}
//               y={0}
//               width={x1 - x0}
//               height={height}
//               fill={scale(mid)}
//               stroke="white"
//               strokeWidth={0.5}
//             />
//           );
//         })}

//         {/* tick labels */}
//         {bins.map((b, i) => {
//           const x = (i / (bins.length - 1)) * width;
//           return (
//             <g key={`tick-${i}`} transform={`translate(${x},${height})`}>
//               <line y2="6" stroke="black" />
//               <text
//                 dy="1.4em"
//                 fontSize="10"
//                 textAnchor={
//                   i === 0 ? "start" : i === bins.length - 1 ? "end" : "middle"
//                 }
//               >
//                 {formatValue(b)}
//               </text>
//             </g>
//           );
//         })}

//         <text x={width / 2} y={height + 30} textAnchor="middle" fontSize="12">
//           Value ({unit})
//         </text>
//       </svg>
//     </div>
//   );
// }


import { useState, useEffect, useRef } from "react";

export default function RawLegend({ bins, scale, unit }) {
  const [width, setWidth] = useState(240);
  const height = 20;
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (let e of entries) {
        setWidth(e.contentRect.width);
      }
    });

    resizeObserver.observe(ref.current);
    return () => resizeObserver.disconnect();
  }, []);

  const formatValue = (v) => {
    if (!bins || bins.length < 2) return v;
    const span = Math.abs(bins[bins.length - 1] - bins[0]);
    if (span < 0.05) return v.toFixed(3);
    if (span < 1) return v.toFixed(2);
    if (span < 10) return v.toFixed(1);
    return Math.round(v);
  };

  if (!bins || bins.length === 0 || !scale) return null;

  return (
    <div ref={ref} style={{ width: "100%" }}>
      <svg
        width={width}
        height={60}
        style={{ display: "block", margin: "0 auto" }}
      >
        {/* Color bins */}
        {bins.slice(0, -1).map((b, i) => {
          const x0 = (i / (bins.length - 1)) * width;
          const x1 = ((i + 1) / (bins.length - 1)) * width;
          const mid = (bins[i] + bins[i + 1]) / 2;

          return (
            <rect
              key={i}
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

        {/* tick labels */}
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
                {formatValue(b)}
              </text>
            </g>
          );
        })}

        <text x={width / 2} y={height + 30} textAnchor="middle" fontSize="12">
          {unit}
        </text>
      </svg>
    </div>
  );
}
