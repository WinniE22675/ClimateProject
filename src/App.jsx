// // import { useState } from "react";

// import Home from "./components/pages/Home";

// function App() {
//   // const [age, setAge] = useState(30);

//   // function add() {
//   //   setAge(age + 1);
//   // }

//   return (
//     <>
//       <h1>Hello World</h1>
//       <h3>winnie</h3>
//       <Home />
//       {/* <button onClick={() => setAge(age + 1)}>add</button>
//       <button onClick={() => setAge(age - 1)}>subtract</button>
//       <button onClick={() => setAge(30)}>reset</button> */}
//     </>
//   );
// }

// export default App;





// import React from "react";
// import IndicesViewer from "./components/IndicesViewer";
// import "./App.css";

// function App() {
//   return (
//     <div className="App">
//       <IndicesViewer />
//     </div>
//   );
// }

// export default App;

// import React from "react";
// import MapViewer from "./components/MapViewer";
// import "./App.css";

// function App() {
//   return (
//     <div className="App" style={{ height: "100vh", width: "100vw" }}>
//       <MapViewer />
//     </div>
//   );
// }

// export default App;


// import ClimateDashboard from "./components/ClimateDashboard";
// import "bootstrap/dist/css/bootstrap.min.css";
// import "./App.css";

// function App() {
//   return (
//     <div className="App" style={{ height: "100vh", width: "100vw" }}>
//       <ClimateDashboard />
//     </div>
//   );
// }

// export default App;

import { BrowserRouter, Routes, Route } from "react-router-dom";
import ClimateDashboard from "./pages/ClimateDashboard";
import UploadDatasetPage from "./pages/UploadDatasetPage";
import DatasetProcessPage from "./pages/DatasetProcessPage";
import Navbar from "./components/Navbar";

// function App() {
//   return (
//     <BrowserRouter>
//       <Routes>
//         <Route path="/" element={<ClimateDashboard />} />
//         <Route path="/upload" element={<UploadDatasetPage />} />
//         <Route path="/process" element={<DatasetProcessPage />} />
//       </Routes>
//     </BrowserRouter>
//   );
// }
function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <div className="content-container">
        <Routes>
          <Route path="/" element={<ClimateDashboard />} />
          <Route path="/manipulate" element={<UploadDatasetPage />} />
          <Route path="/process" element={<DatasetProcessPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;

// use "npm run dev" for start frontend app
// use "npm run dev -- --host 0.0.0.0" for Available via the internet.