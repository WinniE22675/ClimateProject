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
    // Responsive Navbar container
    <nav className="w-full bg-climate-primary shadow">
      <div className="w-full px-4 py-3 md:py-0 min-h-[64px] flex flex-col md:flex-row items-center justify-between gap-3 md:gap-0">
        
        {/* === LEFT SECTION: Logo === */}
        <div className="flex w-full md:flex-1 justify-between md:justify-start items-center">
          <div className="text-white">
            <h2 className="m-0 text-lg md:text-xl font-bold truncate">CDTI Climate Data Services</h2>
          </div>
          
          {/* Authentication */}
          <div className="block md:hidden">
            {user ? (
              <button 
                onClick={handleLogout}
                className="border border-white text-white hover:bg-white hover:text-climate-primary text-xs px-3 py-1.5 rounded transition-colors"
              >
                Logout
              </button>
            ) : (
              <Link to="/login" className="bg-white text-blue-600 text-xs px-3 py-1.5 rounded font-bold hover:bg-gray-100 transition-colors">
                Login
              </Link>
            )}
          </div>
        </div>

        {/* === CENTER SECTION: Main Menu === */}
        <div className="flex justify-center gap-4 w-full md:w-auto overflow-x-auto pb-1 md:pb-0">
          {user && (
            <Link to="/" className={getLinkClass("/")}>
              Dashboard
            </Link>
          )}

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
        <div className="hidden md:flex md:flex-1 justify-end items-center">
          {user ? (
            <button 
              onClick={handleLogout}
              className="border border-white text-white hover:bg-white hover:text-climate-primary text-sm px-4 py-1.5 rounded transition-colors"
            >
              Logout
            </button>
          ) : (
            <Link to="/login" className="bg-white text-blue-600 px-4 py-2 rounded font-bold hover:bg-gray-100 transition-colors">
              Login
            </Link>
          )}
        </div>

      </div>
    </nav>
  );
}