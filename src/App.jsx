import { BrowserRouter, Routes, Route } from "react-router-dom";
import ClimateDashboard from "./pages/ClimateDashboard";
import UploadDatasetPage from "./pages/UploadDatasetPage";
import DatasetProcessPage from "./pages/DatasetProcessPage";
import Navbar from "./components/Navbar";

import { AuthProvider } from "./contexts/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";

import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Navbar />
        <div className="content-container">
          <Routes>
            <Route path="/" element={<ClimateDashboard />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route
              path="/manipulate"
              element={
                <ProtectedRoute>
                  <UploadDatasetPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/process"
              element={
                <ProtectedRoute>
                  <DatasetProcessPage />
                </ProtectedRoute>
              }
            />
          </Routes>
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;

// use "npm run dev" for start frontend app
// use "npm run dev -- --host 0.0.0.0" for Available via the internet.