import React, { useState, useContext } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AuthContext } from '../contexts/AuthContext';
import { authAPI } from '../services/api';

const RegisterPage = () => {
    // 1. Component State
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [errorMsg, setErrorMsg] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    // 2. Hooks
    const { login } = useContext(AuthContext);
    const navigate = useNavigate();

    // 3. Form Submission Handler
    const handleRegister = async (e) => {
        e.preventDefault();
        setErrorMsg('');

        // Basic password validation
        if (password !== confirmPassword) {
            setErrorMsg("Passwords do not match.");
            return;
        }

        setIsLoading(true);

        try {
            // Call the API service to register
            const response = await authAPI.register({ email, password });

            // Handle backend errors (e.g., Email already exists)
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Registration failed. Please try again.');
            }

            // Extract token from successful registration
            const data = await response.json();
            
            // Auto-login the user
            login(data.access_token);

            // Redirect to the protected page
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
            <h2 className="mb-4 text-center">Create an Account</h2>
            
            {errorMsg && <div className="alert alert-danger mb-3">{errorMsg}</div>}

            <form onSubmit={handleRegister}>
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

                <div className="mb-3">
                    <label className="form-label">Password:</label>
                    <input 
                        type="password" 
                        className="form-control"
                        value={password} 
                        onChange={(e) => setPassword(e.target.value)} 
                        required 
                    />
                </div>

                <div className="mb-4">
                    <label className="form-label">Confirm Password:</label>
                    <input 
                        type="password" 
                        className="form-control"
                        value={confirmPassword} 
                        onChange={(e) => setConfirmPassword(e.target.value)} 
                        required 
                    />
                </div>

                <button type="submit" className="btn btn-success w-100" disabled={isLoading}>
                    {isLoading ? 'Creating Account...' : 'Register'}
                </button>
            </form>

            {/* Link back to Login Page */}
            <div className="mt-4 text-center">
                <span className="text-muted">Already have an account? </span>
                <Link to="/login" className="text-decoration-none fw-bold text-primary">
                    Login here
                </Link>
            </div>
        </div>
    );
};

export default RegisterPage;