import React, { useContext } from 'react';
import { Navigate } from 'react-router-dom';
import { AuthContext } from '../contexts/AuthContext';

const ProtectedRoute = ({ children }) => {
    // 1. Get user status and loading state from Context
    const { user, loading } = useContext(AuthContext);

    // 2. Wait until localStorage check is finished
    if (loading) {
        return <div>Loading...</div>; 
    }

    // 3. If no user is found (not logged in), redirect to login page
    if (!user) {
        return <Navigate to="/login" replace />;
    }

    // 4. If logged in, render the protected component
    return children;
};

export default ProtectedRoute;