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
            {/* MODIFIED: Dashboard is now a protected route. 
              Both 'viewer' and 'analyst' can access this page. 
            */}
            <Route 
              path="/" 
              element={
                <ProtectedRoute allowedRoles={["viewer", "analyst"]}>
                  <ClimateDashboard />
                </ProtectedRoute>
              } 
            />
            
            {/* Public Routes: Anyone can access these to authenticate */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            
            {/* MODIFIED: Manipulate page is restricted. 
              ONLY users with the 'analyst' role can access this page. 
            */}
            <Route
              path="/manipulate"
              element={
                <ProtectedRoute allowedRoles={["analyst"]}>
                  <UploadDatasetPage />
                </ProtectedRoute>
              }
            />
            
            {/* MODIFIED: Process page is restricted. 
              ONLY users with the 'analyst' role can access this page. 
            */}
            <Route
              path="/process"
              element={
                <ProtectedRoute allowedRoles={["analyst"]}>
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