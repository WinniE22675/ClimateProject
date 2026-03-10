import { Link, useLocation } from "react-router-dom";

export default function Navbar() {
  const location = useLocation();

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

  return (
    <nav className="navbar navbar-expand-lg navbar-light bg-white shadow-sm mb-4">
      <div className="container-fluid px-4">
        {/* Brand / Logo */}
        <div className="text-xl font-bold text-blue-600">
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
    </nav>
  );
}
