import React, { createContext, useState, useEffect } from 'react';

// 1. Create the Context
export const AuthContext = createContext();

// 2. Create the Provider Component
export const AuthProvider = ({ children }) => {
    // State to store the JWT token
    const [token, setToken] = useState(null);
    
    // State to store user status (can be expanded to store user email/details later)
    const [user, setUser] = useState(null);
    
    // State to handle initial loading while checking localStorage
    const [loading, setLoading] = useState(true);

    // Run this only once when the application starts
    useEffect(() => {
        const storedToken = localStorage.getItem('jwt_token');
        
        if (storedToken) {
            setToken(storedToken);
            setUser({ isLoggedIn: true });
        }
        
        // Finish loading
        setLoading(false);
    }, []);

    // Function to handle login success
    const login = (newToken) => {
        localStorage.setItem('jwt_token', newToken);
        setToken(newToken);
        setUser({ isLoggedIn: true });
    };

    // Function to handle logout
    const logout = () => {
        localStorage.removeItem('jwt_token');
        setToken(null);
        setUser(null);
    };

    // Provide the states and functions to the rest of the app
    const value = {
        token,
        user,
        loading,
        login,
        logout
    };

    return (
        <AuthContext.Provider value={value}>
            {!loading && children}
        </AuthContext.Provider>
    );
};