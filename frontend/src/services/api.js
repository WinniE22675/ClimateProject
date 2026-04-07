// export async function uploadDataset(file) {
//   const formData = new FormData();
//   formData.append("file", file);

//   const response = await fetch("http://localhost:8000/api/indices/upload", {
//     method: "POST",
//     body: formData,
//   });

//   if (!response.ok) {
//     throw new Error("Failed to upload file");
//   }

//   const data = await response.json();
//   return data;
// }

// src/services/api.js

// 1. Setup Base URL from Environment Variables
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

// 2. Helper function to get token and prepare headers
const getAuthHeaders = () => {
    const token = localStorage.getItem('jwt_token');
    const headers = {
        'Content-Type': 'application/json',
    };
    
    // If token exists, attach it to the Authorization header
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    return headers;
};

// 3. Centralized Fetch Wrapper
export const apiFetch = async (endpoint, options = {}) => {
    const url = `${BASE_URL}${endpoint}`;
    const headers = getAuthHeaders();

    // Merge any custom headers passed from the component
    if (options.headers) {
        Object.assign(headers, options.headers);
    }

    // SPECIAL CASE FOR CLIMATE DATA UPLOAD:
    // If we are uploading files (FormData), the browser must automatically 
    // set the Content-Type with a specific 'boundary'. 
    // We must delete our default Content-Type to prevent corrupted uploads.
    if (options.body instanceof FormData) {
        delete headers['Content-Type'];
    }

    const config = {
        ...options,
        headers,
    };

    try {
        const response = await fetch(url, config);
        
        // 4. Global Error Handling for Unauthorized (Token Expired)
        if (response.status === 401) {
            console.warn("Token expired or unauthorized. Logging out...");
            // Remove invalid token
            localStorage.removeItem('jwt_token');
            // Optional: You can force a page reload to redirect user to login
            // window.location.href = '/login'; 
        }

        return response;
        
    } catch (error) {
        console.error(`API Fetch Error [${endpoint}]:`, error);
        throw error;
    }
};

// ==========================================
// 5. Pre-defined API Methods (Clean & Reusable)
// ==========================================

export const authAPI = {
    login: (credentials) => apiFetch('/auth/login', {
        method: 'POST',
        body: JSON.stringify(credentials)
    }),
    register: (userData) => apiFetch('/auth/register', {
        method: 'POST',
        body: JSON.stringify(userData)
    })
};

export const datasetAPI = {
    // Uses the customized apiFetch to automatically attach the token
    getDatasets: () => apiFetch('/datasets', {
        method: 'GET'
    }),
    
    // Ready for your multi-user slot upload
    uploadFiles: (slotId, formData) => apiFetch(`/datasets/${slotId}/upload`, {
        method: 'POST',
        body: formData // apiFetch will handle the FormData headers automatically
    }),

    processSelection: (data) => apiFetch('/datasets/process_selection', {
        method: 'POST',
        body: JSON.stringify(data)
    }),

    // Uploads a customized shapefile (.zip) to the server
    uploadShapefile: (formData) => apiFetch('/shapefiles/upload', {
        method: 'POST',
        body: formData // apiFetch will automatically handle the multipart/form-data boundary
    }),

    // Retrieves available text columns from the uploaded shapefile
    getShapefileColumns: (shapefileName) => apiFetch(`/shapefiles/${shapefileName}/columns`, {
        method: 'GET'
    }),

    getShapefiles: () => apiFetch('/shapefiles', { method: 'GET' })
};