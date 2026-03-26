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
                        {/* <div className="mb-3">
                            <label className="form-label">Email</label>
                            <input 
                                type="email" 
                                className="form-control"
                                value={email} 
                                onChange={(e) => setEmail(e.target.value)} 
                                required 
                            />
                        </div>

                        <div className="mb-4">
                            <label className="form-label">Password</label>
                            <input 
                                type="password" 
                                className="form-control"
                                value={password} 
                                onChange={(e) => setPassword(e.target.value)} 
                                required 
                            />
                        </div> */}
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
                    <div className="mt-4 text-center">
                        <span className="text-muted">Don't have an account? </span>
                        <Link to="/register" className="text-decoration-none fw-bold text-primary">
                            Register here
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    );
};

// return (
//         <div className="row g-0 vh-100">
//             {/* Left Side - Image/Branding */}
//             <div className="col-md-6 d-none d-md-flex flex-column justify-content-center align-items-center text-white" 
//                  style={{ 
//                      backgroundImage: "url('https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=2072&auto=format&fit=crop')", 
//                      backgroundSize: 'cover', 
//                      backgroundPosition: 'center' 
//                  }}>
//                  <div style={{ backgroundColor: 'rgba(0,0,0,0.5)', padding: '2rem', borderRadius: '1rem', textAlign: 'center' }}>
//                     <h1 className="fw-bold">CDTI Climate Services</h1>
//                     <p>Advanced Data Manipulation & Processing</p>
//                  </div>
//             </div>

//             {/* Right Side - Form */}
//             <div className="col-md-6 d-flex justify-content-center align-items-center bg-light">
//                 {/* INSERT THE CARD UI HERE, remove the 'border-0 shadow-lg' if you want it to blend seamlessly */}
//                 <div className="card border-0 bg-transparent" style={{ width: '100%', maxWidth: '400px' }}>
//                     {/* <h2 className="mb-4 text-center">Login</h2> */}
//                     <div className="text-center mb-4">
//                         <h2 className="fw-bold">Sign in</h2>
//                         <p className="text-muted">Sign in to access your climate workspace</p>
//                     </div>
                    
//                     {/* Error Message */}
//                     {errorMsg && <div className="alert alert-danger mb-3">{errorMsg}</div>}

//                     <form onSubmit={handleLogin}>
//                         <div className="mb-3">
//                             <label className="form-label">Email</label>
//                             <input 
//                                 type="email" 
//                                 className="form-control"
//                                 value={email} 
//                                 onChange={(e) => setEmail(e.target.value)} 
//                                 required 
//                             />
//                         </div>

//                         <div className="mb-4">
//                             <label className="form-label">Password</label>
//                             <input 
//                                 type="password" 
//                                 className="form-control"
//                                 value={password} 
//                                 onChange={(e) => setPassword(e.target.value)} 
//                                 required 
//                             />
//                         </div>

//                         <button type="submit" className="btn btn-primary w-100" disabled={isLoading}>
//                             {isLoading ? 'Signing In...' : 'Sign in'}
//                         </button>
//                     </form>

//                     {/* Link to Register Page */}
//                     <div className="mt-4 text-center">
//                         <span className="text-muted">Don't have an account? </span>
//                         <Link to="/register" className="text-decoration-none fw-bold text-primary">
//                             Register here
//                         </Link>
//                     </div>
//                 </div>
//             </div>
//         </div>
//     );
// };

// return (
//         <div className="d-flex justify-content-center align-items-center min-vh-100" 
//              style={{ 
//                  backgroundImage: "url('https://images.unsplash.com/photo-1504608524841-42fe6f032b4b?q=80&w=2065&auto=format&fit=crop')",
//                  backgroundSize: 'cover'
//              }}>
            
//             {/* Glassmorphism Card */}
//             <div className="card shadow-lg border-0 rounded-4" 
//                  style={{ 
//                      width: '100%', 
//                      maxWidth: '450px',
//                      // Apply Frosted Glass Effect
//                      backgroundColor: 'rgba(255, 255, 255, 0.85)',
//                      backdropFilter: 'blur(10px)',
//                      WebkitBackdropFilter: 'blur(10px)' 
//                  }}>
                
//                 <div className="card-body p-5">
//                     {/* <h2 className="mb-4 text-center">Login</h2> */}
//                     <div className="text-center mb-4">
//                         <h2 className="fw-bold">Sign in</h2>
//                         <p className="text-muted">Sign in to access your climate workspace</p>
//                     </div>
                    
//                     {/* Error Message */}
//                     {errorMsg && <div className="alert alert-danger mb-3">{errorMsg}</div>}

//                     <form onSubmit={handleLogin}>
//                         <div className="mb-3">
//                             <label className="form-label">Email</label>
//                             <input 
//                                 type="email" 
//                                 className="form-control"
//                                 value={email} 
//                                 onChange={(e) => setEmail(e.target.value)} 
//                                 required 
//                             />
//                         </div>

//                         <div className="mb-4">
//                             <label className="form-label">Password</label>
//                             <input 
//                                 type="password" 
//                                 className="form-control"
//                                 value={password} 
//                                 onChange={(e) => setPassword(e.target.value)} 
//                                 required 
//                             />
//                         </div>

//                         <button type="submit" className="btn btn-primary w-100" disabled={isLoading}>
//                             {isLoading ? 'Signing In...' : 'Sign in'}
//                         </button>
//                     </form>

//                     {/* Link to Register Page */}
//                     <div className="mt-4 text-center">
//                         <span className="text-muted">Don't have an account? </span>
//                         <Link to="/register" className="text-decoration-none fw-bold text-primary">
//                             Register here
//                         </Link>
//                     </div>
//                 </div>
//             </div>
//         </div>
//     );
// };

export default LoginPage;