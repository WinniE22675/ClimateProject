import React, { createContext, useState, useEffect } from 'react';

// 1. Create the Context
export const AuthContext = createContext();

const decodeTokenPayload = (token) => {
    try {
        // JWT is structured as: header.payload.signature
        // We split by '.' and decode the middle part (payload) using atob()
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));

        return JSON.parse(jsonPayload);
    } catch (error) {
        console.error("Failed to decode token", error);
        return null;
    }
};

// 2. Create the Provider Component
export const AuthProvider = ({ children }) => {
    // State to store the JWT token
    const [token, setToken] = useState(null);
    
    // State to store user status (can be expanded to store user email/details later)
    const [user, setUser] = useState(null);
    
    // State to handle initial loading while checking localStorage
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const storedToken = localStorage.getItem('jwt_token');
        
        if (storedToken) {
            // MODIFIED: Decode the stored token to extract user info (like role)
            const decodedPayload = decodeTokenPayload(storedToken);
            
            if (decodedPayload) {
                setToken(storedToken);
                // Save both login status AND the user's role
                setUser({ 
                    isLoggedIn: true, 
                    role: decodedPayload.role,  // <-- Example: 'viewer' or 'analyst'
                    id: decodedPayload.sub      // Optional: Store user ID too
                });
            } else {
                // If token is invalid, clear it
                localStorage.removeItem('jwt_token');
            }
        }
        
        // Finish loading
        setLoading(false);
    }, []);

    // Function to handle login success
    const login = (newToken) => {
        localStorage.setItem('jwt_token', newToken);
        setToken(newToken);
        
        // Decode the new token right after login
        const decodedPayload = decodeTokenPayload(newToken);
        if (decodedPayload) {
            setUser({ 
                isLoggedIn: true, 
                role: decodedPayload.role,
                id: decodedPayload.sub
            });
        }
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