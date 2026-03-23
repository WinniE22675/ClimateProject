import React, { useContext } from 'react';
import { Navigate } from 'react-router-dom';
import { AuthContext } from '../contexts/AuthContext';

const ProtectedRoute = ({ children, allowedRoles }) => {
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

    // If 'allowedRoles' is provided AND the user's role is NOT in the list
    if (allowedRoles && !allowedRoles.includes(user.role)) {
        // Redirect unauthorized users back to the Dashboard
        // (You could also redirect to a custom "/unauthorized" error page if you prefer)
        return <Navigate to="/" replace />;
    }

    // 4. If logged in, render the protected component
    return children;
};

export default ProtectedRoute;