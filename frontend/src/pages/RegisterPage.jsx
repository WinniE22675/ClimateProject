import React, { useState, useContext } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AuthContext } from '../contexts/AuthContext';
import { authAPI } from '../services/api';

const RegisterPage = () => {
    // Component State
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');

    const [role, setRole] = useState('viewer');

    // State to store the admin authorization code
    const [adminCode, setAdminCode] = useState('');

    const [errorMsg, setErrorMsg] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    // Hooks
    const { login } = useContext(AuthContext);
    const navigate = useNavigate();

    // Form Submission Handler
    const handleRegister = async (e) => {
        e.preventDefault();
        setErrorMsg('');

        // Basic password validation
        if (password !== confirmPassword) {
            setErrorMsg("Passwords do not match.");
            return;
        }

        if (role === 'analyst' && adminCode !== 'Cdti_2026') {
            setErrorMsg("Invalid Administrator Code. You cannot register as an Analyst.");
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

    // UI Rendering
    return (
        <div className="flex justify-center items-center mt-12 mb-12">
            {/* Card UI */}
            <div className="bg-white shadow-lg rounded-2xl w-full max-w-[450px]">
                <div className="p-12">
                    {/* <h2 className="mb-6 text-center font-bold">Create an Account</h2> */}
                    <div className="text-center mb-6">
                        <h2 className="text-3xl font-bold text-gray-800">Create an Account</h2>
                        <p className="text-gray-500 mt-2">Join the climate data services platform</p>
                    </div>
                    
                    {/* Error Message */}
                    {errorMsg && (
                        <div className="bg-red-100 text-red-700 border border-red-200 px-4 py-3 rounded-md mb-4">
                            {errorMsg}
                        </div>
                    )}

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

                        {role === 'analyst' && (
                            <div className="custom-outlined-input">
                                <input 
                                    type="text" 
                                    id="regAdminCode" 
                                    placeholder=" " 
                                    value={adminCode} 
                                    onChange={(e) => setAdminCode(e.target.value)} 
                                    required={role === 'analyst'} 
                                />
                                <label htmlFor="regAdminCode">Administrator Code</label>
                            </div>
                        )}

                        <button 
                            type="submit" 
                            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors disabled:opacity-60 disabled:cursor-not-allowed" 
                            disabled={isLoading}
                        >
                            {isLoading ? 'Creating Account...' : 'Sign up'}
                        </button>
                    </form>

                    {/* Link back to Login Page */}
                    <div className="mt-6 text-center">
                        <span className="text-gray-500">Already have an account? </span>
                        <Link to="/login" className="font-bold text-blue-600 hover:text-blue-800 no-underline">
                            Sign in here
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default RegisterPage;