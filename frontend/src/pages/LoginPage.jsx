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
            navigate('/'); // /manipulate

        } catch (err) {
            setErrorMsg(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    // 4. UI Rendering
    return (
        <div className="d-flex justify-content-center align-items-center mt-5">
            {/* Card UI */}
            <div className="card shadow-lg border-0 rounded-4" style={{ width: '100%', maxWidth: '450px' }}>
                <div className="card-body p-5">
                    {/* <h2 className="mb-4 text-center">Login</h2> */}
                    <div className="text-center mb-4">
                        <h2 className="fw-bold">Sign in</h2>
                        <p className="text-muted">Sign in to access your climate workspace</p>
                    </div>
                    
                    {/* Error Message */}
                    {errorMsg && <div className="alert alert-danger mb-3">{errorMsg}</div>}

                    <form onSubmit={handleLogin}>
                        <div className="custom-outlined-input">
                            <input 
                                type="email" 
                                id="emailInput" 
                                placeholder=" " /* MUST BE A SPACE for CSS to detect empty state */
                                value={email} 
                                onChange={(e) => setEmail(e.target.value)} 
                                required 
                            />
                            <label htmlFor="emailInput">Email address</label>
                        </div>

                        {/* Custom Outlined Password Input */}
                        <div className="custom-outlined-input">
                            <input 
                                type="password" 
                                id="passwordInput" 
                                placeholder=" " /* MUST BE A SPACE */
                                value={password} 
                                onChange={(e) => setPassword(e.target.value)} 
                                required 
                            />
                            <label htmlFor="passwordInput">Password</label>
                        </div>

                        <button type="submit" className="btn btn-primary w-100" disabled={isLoading}>
                            {isLoading ? 'Signing In...' : 'Sign in'}
                        </button>
                    </form>

                    {/* Link to Register Page */}
                    {/* <div className="mt-4 text-center">
                        <span className="text-muted">Don't have an account? </span>
                        <Link to="/register" className="text-decoration-none fw-bold text-primary">
                            Register here
                        </Link>
                    </div> */}
                </div>
            </div>
        </div>
    );
};

export default LoginPage;