import { Link, useLocation, useNavigate } from "react-router-dom";
import { useContext } from "react";
import { AuthContext } from "../contexts/AuthContext";

export default function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();

  // Extract user data and logout function from Context
  const { user, logout } = useContext(AuthContext);

  // Hide Navbar completely on Login and Register pages
  const hideOnPages = ["/login", "/register"];
  if (hideOnPages.includes(location.pathname)) {
    return null; // Return nothing, so the navbar disappears
  }

  // Helper function to set custom active class
  const getLinkClass = (path) => {
    // Only apply "active" if the current path matches
    return location.pathname === path
      ? "nav-link-custom active"
      : "nav-link-custom";
  };

  const handleLogout = () => {
    logout();
    navigate("/"); // Redirect to Dashboard after logout
  };

return (
    // Removed mb-4 to clear white space below. Applied custom blue background.
    <nav className="navbar navbar-expand-lg bg-climate-primary shadow">
      <div className="container-fluid px-4 d-flex align-items-center">
        
        {/* === LEFT SECTION: Logo (Uses flex: 1 to balance the center) === */}
        <div className="d-flex" style={{ flex: 1 }}>
          <div className="text-xl font-bold text-white">
            <h2 className="mb-0 fs-4">CDTI Climate Data Services</h2>
          </div>
        </div>

        {/* === CENTER SECTION: Main Menu === */}
        {/* Justify content center ensures it stays strictly in the middle */}
        <div className="d-flex justify-content-center gap-4" style={{ flex: 1 }}>
          
          {/* Dashboard is visible to everyone who can see the Navbar (both viewer and analyst) */}
          {user && (
            <Link to="/" className={getLinkClass("/")}>
              Dashboard
            </Link>
          )}

          {/* MODIFIED: Conditionally render Manipulate and Process links ONLY for 'analyst' role */}
          {user && user.role === "analyst" && (
            <>
              <Link to="/manipulate" className={getLinkClass("/manipulate")}>
                Manipulate
              </Link>
              <Link to="/process" className={getLinkClass("/process")}>
                Process
              </Link>
            </>
          )}
          
        </div>

        {/* === RIGHT SECTION: Authentication === */}
        {/* Justify content end pushes items to the far right */}
        <div className="d-flex justify-content-end align-items-center" style={{ flex: 1 }}>
          {user ? (
            <div className="d-flex align-items-center">
              {/* <span className="text-white opacity-75 me-3">
                Hello, User!
              </span> */}
              <button 
                onClick={handleLogout}
                className="btn btn-outline-light btn-sm px-3"
              >
                Logout
              </button>
            </div>
          ) : (
            <Link to="/login" className="btn btn-light text-primary px-4 fw-bold">
              Login
            </Link>
          )}
        </div>

      </div>
    </nav>
  );
}