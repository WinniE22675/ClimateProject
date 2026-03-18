import React, { useState, useContext } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AuthContext } from '../contexts/AuthContext';
import { authAPI } from '../services/api';

const LoginPage = () => {
    // 1. Component State
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [errorMsg, setErrorMsg] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    // 2. Hooks for Context and Navigation
    const { login } = useContext(AuthContext);
    const navigate = useNavigate();

    // 3. Form Submission Handler
    const handleLogin = async (e) => {
        e.preventDefault(); // Prevent page reload
        setErrorMsg('');
        setIsLoading(true);

        try {
            // Call the API service to authenticate
            const response = await authAPI.login({ email, password });

            // If Backend returns 401 Unauthorized or other errors
            if (!response.ok) {
                throw new Error('Invalid email or password. Please try again.');
            }

            // Extract the token from the JSON response
            const data = await response.json();
            
            // Save token to Context (which also saves to localStorage)
            login(data.access_token);

            // Redirect user to the main manipulation page or dashboard
            navigate('/manipulate'); 

        } catch (err) {
            setErrorMsg(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    // 4. UI Rendering
    return (
        <div className="container mt-5" style={{ maxWidth: '400px' }}>
            <h2 className="mb-4 text-center">Login</h2>
            
            {errorMsg && <div className="alert alert-danger mb-3">{errorMsg}</div>}

            <form onSubmit={handleLogin}>
                <div className="mb-3">
                    <label className="form-label">Email:</label>
                    <input 
                        type="email" 
                        className="form-control"
                        value={email} 
                        onChange={(e) => setEmail(e.target.value)} 
                        required 
                    />
                </div>

                <div className="mb-4">
                    <label className="form-label">Password:</label>
                    <input 
                        type="password" 
                        className="form-control"
                        value={password} 
                        onChange={(e) => setPassword(e.target.value)} 
                        required 
                    />
                </div>

                <button type="submit" className="btn btn-primary w-100" disabled={isLoading}>
                    {isLoading ? 'Signing In...' : 'Login'}
                </button>
            </form>

            {/* Link to Register Page */}
            <div className="mt-4 text-center">
                <span className="text-muted">Don't have an account? </span>
                <Link to="/register" className="text-decoration-none fw-bold text-primary">
                    Register here
                </Link>
            </div>
        </div>
    );
};

export default LoginPage;