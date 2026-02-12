import { useEffect, useState } from "react";

export default function IndicesSelector({ availableVars, onCalculate }) {
  const [availableIndices, setAvailableIndices] = useState({});
  const [selected, setSelected] = useState([]);

  const [baselineStart, setBaselineStart] = useState("");
  const [baselineEnd, setBaselineEnd] = useState("");

  useEffect(() => {
    if (!availableVars || availableVars.length === 0) return;

    const map = {
      pr: [
        "PRCPTOT",
        "Rx1day",
        "Rx5day",
        "SDII",
        "R10mm",
        "R20mm",
        "CDD",
        "CWD",
        "R95p",
        "R99p",
        "R95pTOT",
        "R99pTOT",
        "SPI3",
        "SPI6",
        "SPI9",
        "SPI12",
      ],
      tmax: ["TXx", "TXn", "SU", "TR", "TX10p", "TX90p"],
      tmin: ["TNx", "TNn", "FD", "ID", "TN10p", "TN90p"],
    };

    let result = {};
    availableVars.forEach((v) => {
      result[v] = map[v] || [];
    });

    setAvailableIndices(result);
  }, [availableVars]);
  // create object for user select like
  // {
  //   pr: ["PRCPTOT", "Rx1day", "Rx5day"],
  //   tmax: ["TXx"]
  // }

  const toggleSelect = (name) => {
    setSelected((prev) =>
      prev.includes(name) ? prev.filter((x) => x !== name) : [...prev, name]
    );
  };

  // Select All Functions
  const selectAll = () => {
    const all = Object.values(availableIndices).flat();
    // (Toggle All)
    if (all.every((i) => selected.includes(i))) {
      setSelected([]);
    } else {
      setSelected([...new Set(all)]); // Unique
    }
  };

  // const handleClick = () => {
  //   onCalculate(selected);
  // };

  const selectCategory = (variable) => {
    const indicesInCat = availableIndices[variable];
    // เช็คว่าในหมวดนี้เลือกครบยัง
    const allSelected = indicesInCat.every((i) => selected.includes(i));

    if (allSelected) {
      // Unselect all in category
      setSelected((prev) => prev.filter((i) => !indicesInCat.includes(i)));
    } else {
      // Select all in category
      setSelected((prev) => [...new Set([...prev, ...indicesInCat])]);
    }
  };

  //   return (
  //     <div className="card p-3">
  //       <h4>Select Indices to Calculate</h4>

  //       {Object.keys(availableIndices).map((variable) => (
  //         <div key={variable}>
  //           <h5>{variable}</h5>
  //           {availableIndices[variable].map((ind) => (
  //             <label key={ind} className="d-block">
  //               <input
  //                 type="checkbox"
  //                 checked={selected.includes(ind)}
  //                 onChange={() => toggleSelect(ind)}
  //               />
  //               {ind}
  //             </label>
  //           ))}
  //         </div>
  //       ))}
  //       {/* if select same indices, indices is out */}
  //       {/* if select new indices, indices is add */}

  //       <button
  //         className="btn btn-primary mt-3"
  //         onClick={handleClick}
  //         disabled={selected.length === 0}
  //       >
  //         Calculate Indices
  //       </button>
  //     </div>
  //   );
  // }
  return (
    <div className="card p-4 h-full">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h4 className="mb-0">Select Indices</h4>
        {/* ปุ่ม Select All Global */}
        <button onClick={selectAll} className="btn btn-sm btn-outline-primary">
          {Object.values(availableIndices)
            .flat()
            .every((i) => selected.includes(i)) && selected.length > 0
            ? "Unselect All"
            : "Select All"}
        </button>
      </div>

      <div className="border rounded p-2 mb-3 bg-light">
        <h6 className="mb-2">Baseline Period (for percentile-based indices)</h6>

        <div className="d-flex gap-2">
          <input
            type="number"
            className="form-control form-control-sm"
            placeholder="Start Year (e.g. 1981)"
            value={baselineStart}
            onChange={(e) => setBaselineStart(e.target.value)}
          />

          <input
            type="number"
            className="form-control form-control-sm"
            placeholder="End Year (e.g. 2010)"
            value={baselineEnd}
            onChange={(e) => setBaselineEnd(e.target.value)}
          />
        </div>
      </div>

      <div className="overflow-auto" style={{ maxHeight: "600px" }}>
        {Object.keys(availableIndices).map((variable) => (
          <div key={variable} className="mb-3 border p-2 rounded">
            <div
              className="d-flex justify-content-between align-items-center cursor-pointer bg-light p-1 rounded mb-2"
              onClick={() => selectCategory(variable)}
              style={{ cursor: "pointer" }}
            >
              <h5 className="mb-0 font-bold text-uppercase text-primary">
                {variable}
              </h5>
              <small className="text-muted">Click to select all</small>
            </div>

            <div className="row g-2">
              {availableIndices[variable].map((ind) => (
                <div key={ind} className="col-6">
                  <label className="d-flex align-items-center gap-2 border p-1 rounded hover:bg-gray-50 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selected.includes(ind)}
                      onChange={() => toggleSelect(ind)}
                    />
                    <span>{ind}</span>
                  </label>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* <button
        className="btn btn-primary w-100 mt-3 py-2 fw-bold"
        onClick={() => onCalculate(selected)}
        disabled={selected.length === 0}
      >
        Calculate Selected Indices ({selected.length})
      </button> */}
      <button
        className="btn btn-primary w-100 mt-3 py-2 fw-bold"
        onClick={() =>
          onCalculate(selected, {
            start_year: baselineStart ? parseInt(baselineStart) : null,
            end_year: baselineEnd ? parseInt(baselineEnd) : null,
          })
        }
        disabled={selected.length === 0}
      >
        Calculate Selected Indices ({selected.length})
      </button>
    </div>
  );
}
