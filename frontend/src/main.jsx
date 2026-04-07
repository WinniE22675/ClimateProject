// import { StrictMode } from 'react'
// import { createRoot } from 'react-dom/client'
// import App from './App.jsx'
// import 'leaflet/dist/leaflet.css'      
// import "bootstrap/dist/css/bootstrap.min.css";

// createRoot(document.getElementById('root')).render(
//   <StrictMode>
//     <App />
//   </StrictMode>,
// )

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import 'leaflet/dist/leaflet.css'      
import "bootstrap/dist/css/bootstrap.min.css";
import { AuthProvider } from './contexts/AuthContext.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {/* Wrap the App with AuthProvider */}
    <AuthProvider>
      <App />
    </AuthProvider>
  </StrictMode>,
)