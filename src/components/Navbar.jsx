import { Link, useLocation, useNavigate } from "react-router-dom";
import { useContext } from "react";
import { AuthContext } from "../contexts/AuthContext";

export default function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();

  // Extract user data and logout function from Context
  const { user, logout } = useContext(AuthContext);

  // Helper function to set active class
  const getLinkClass = (path) => {
    // Basic styling + active state styling
    const baseClass =
      "text-decoration-none px-3 py-2 rounded-md transition-colors duration-200";
    const activeClass = "bg-primary text-white fw-bold"; // Active style
    const inactiveClass = "text-dark hover:bg-gray-200"; // Inactive style

    return location.pathname === path
      ? `${baseClass} ${activeClass}`
      : `${baseClass} ${inactiveClass}`;
  };

  const handleLogout = () => {
    logout();
    navigate("/"); // Redirect to Dashboard after logout
  };

//   return (
//     <nav className="navbar navbar-expand-lg navbar-light bg-white shadow-sm mb-4">
//       <div className="container-fluid px-4">
//         {/* Brand / Logo */}
//         <div className="text-xl font-bold text-blue-600">
//           <h2>CDTI Climate Data Services</h2>
//         </div>

//         {/* Menu Items */}
//         <div className="flex space-x-4">
//           <Link to="/" className={getLinkClass("/")}>
//             Dashboard
//           </Link>
//           <Link to="/manipulate" className={getLinkClass("/manipulate")}>
//             Manipulate
//           </Link>
//           <Link to="/process" className={getLinkClass("/process")}>
//             Process
//           </Link>
//         </div>
//       </div>
//     </nav>
//   );
// }
return (
    <nav className="navbar navbar-expand-lg navbar-light bg-white shadow-sm mb-4">
      {/* UPDATE: Use justify-content-between to split left and right sections */}
      <div className="container-fluid px-4 d-flex justify-content-between align-items-center">
        
        {/* === LEFT SECTION: Logo & Main Menu === */}
        <div className="d-flex align-items-center space-x-6">
          {/* Brand / Logo */}
          <div className="text-xl font-bold text-blue-600 me-4">
            <h2>CDTI Climate Data Services</h2>
          </div>

          {/* Menu Items */}
          <div className="flex space-x-4">
            <Link to="/" className={getLinkClass("/")}>
              Dashboard
            </Link>
            <Link to="/manipulate" className={getLinkClass("/manipulate")}>
              Manipulate
            </Link>
            <Link to="/process" className={getLinkClass("/process")}>
              Process
            </Link>
          </div>
        </div>

        {/* === RIGHT SECTION: Authentication (Login/Logout) === */}
        <div className="d-flex align-items-center">
          {user ? (
            // If user is logged in: Show Email and Logout button
            <div className="flex items-center space-x-4">
              <span className="text-gray-600 fw-bold">
                Hello, User! 
                {/* Note: You can change 'Hello, User!' to 'user.email' if you pass email in context */}
              </span>
              <button 
                onClick={handleLogout}
                className="btn btn-outline-danger btn-sm ms-3 px-3 py-2"
              >
                Logout
              </button>
            </div>
          ) : (
            // If user is NOT logged in: Show Login button
            <Link to="/login" className="btn btn-primary px-4 py-2">
              Login
            </Link>
          )}
        </div>

      </div>
    </nav>
  );
}