import React, { useState, useContext } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AuthContext } from '../contexts/AuthContext';
import { authAPI } from '../services/api';

const RegisterPage = () => {
    // 1. Component State
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');

    const [role, setRole] = useState('viewer');

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
            const response = await authAPI.register({ email, password, role });

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
        <div className="d-flex justify-content-center align-items-center mt-5">
            {/* Card UI */}
            <div className="card shadow-lg border-0 rounded-4" style={{ width: '100%', maxWidth: '450px' }}>
                <div className="card-body p-5">
                    {/* <h2 className="mb-4 text-center fw-bold">Create an Account</h2> */}
                    <div className="text-center mb-4">
                        <h2 className="fw-bold">Create an Account</h2>
                        <p className="text-muted">Join the climate data services platform</p>
                    </div>
                    {errorMsg && <div className="alert alert-danger mb-3">{errorMsg}</div>}

                    <form onSubmit={handleRegister}>
                        <div className="custom-outlined-input">
                            <input 
                                type="email" 
                                id="regEmailInput" 
                                placeholder=" " /* MUST BE A SPACE */
                                value={email} 
                                onChange={(e) => setEmail(e.target.value)} 
                                required 
                            />
                            <label htmlFor="regEmailInput">Email address</label>
                        </div>

                        <div className="custom-outlined-input">
                            <input 
                                type="password" 
                                id="regPasswordInput" 
                                placeholder=" " 
                                value={password} 
                                onChange={(e) => setPassword(e.target.value)} 
                                required 
                            />
                            <label htmlFor="regPasswordInput">Password</label>
                        </div>

                        <div className="custom-outlined-input">
                            <input 
                                type="password" 
                                id="regConfirmInput" 
                                placeholder=" " 
                                value={confirmPassword} 
                                onChange={(e) => setConfirmPassword(e.target.value)} 
                                required 
                            />
                            <label htmlFor="regConfirmInput">Confirm Password</label>
                        </div>

                        <div className="custom-outlined-input">
                            <select 
                                id="regRoleInput" 
                                value={role} 
                                onChange={(e) => setRole(e.target.value)} 
                                required
                            >
                                <option value="viewer">Viewer (Dashboard Only)</option>
                                <option value="analyst">Analyst (Full Access)</option>
                            </select>
                            <label htmlFor="regRoleInput">Account Role</label>
                        </div>

                        <button type="submit" className="btn btn-primary w-100" disabled={isLoading}>
                            {isLoading ? 'Creating Account...' : 'Sign up'}
                        </button>
                    </form>

                    {/* Link back to Login Page */}
                    <div className="mt-4 text-center">
                        <span className="text-muted">Already have an account? </span>
                        <Link to="/login" className="text-decoration-none fw-bold text-primary" >
                            Sign in here
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default RegisterPage;