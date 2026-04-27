import { useState, useEffect, useRef } from "react";
import { Link, useLocation } from "react-router-dom";
import { isLoggedIn, logout, getUserProfile } from "../services/authService";
import "./Navbar.css";

const NAV_LINKS = [
  { label: "Hotels",      path: "/hotels"},
  { label: "Attractions", path: "/attractions"},
  { label: "Food",        path: "/food"},
  { label: "Transport",   path: "/transport"},
  { label: "Rentals",     path: "/rentals"},
  { label: "AI Chatbot",  path: "/chatbot"},
];

export default function Navbar() {
  const [scrolled, setScrolled]       = useState(false);
  const [menuOpen, setMenuOpen]       = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [user, setUser]               = useState(null);
  const dropdownRef                   = useRef(null);
  const location                      = useLocation();
  const loggedIn                      = isLoggedIn();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (loggedIn) {
      getUserProfile().then(setUser).catch(() => {});
    }
  }, [loggedIn]);

  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  useEffect(() => { setMenuOpen(false); setProfileOpen(false); }, [location]);

  const initials = user?.username?.[0]?.toUpperCase() || "U";

  return (
    <>
      <nav className={`navbar ${scrolled ? "navbar--solid" : "navbar--transparent"}`}>
        <div className="navbar__inner">

          {/* Logo */}
          <Link to="/" className="navbar__logo">
            <span className="logo-plane">✈</span>
            <span className="logo-text">Ya<span className="logo-accent">trip</span></span>
          </Link>

          {/* Right group */}
          <div className="navbar__right-group">

            <ul className="navbar__links">
              {NAV_LINKS.map((l) => (
                <li key={l.path}>
                  <Link
                    to={l.path}
                    className={`nav-link ${location.pathname.startsWith(l.path) ? "nav-link--active" : ""}`}
                  >
                    <span className="nav-link__icon">{l.icon}</span>
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>

            <div className="navbar__auth">
              {loggedIn ? (
                <div className="profile-wrap" ref={dropdownRef}>
                  <button
                    className={`profile-trigger ${profileOpen ? "profile-trigger--open" : ""}`}
                    onClick={() => setProfileOpen(!profileOpen)}
                  >
                    <div className="profile-avatar-circle">{initials}</div>
                    <div className="profile-trigger-info">
                      <span className="profile-trigger-name">{user?.username || "User"}</span>
                      <span className="profile-trigger-role">
                        {user?.is_owner ? "Business Owner" : "Traveler"}
                      </span>
                    </div>
                    <span className={`chevron ${profileOpen ? "chevron--up" : ""}`}>▾</span>
                  </button>

                  {profileOpen && (
                    <div className="profile-dropdown">

                      {/* Header */}
                      <div className="dropdown-header">
                        <div className="dropdown-avatar">{initials}</div>
                        <div className="dropdown-userinfo">
                          <p className="dropdown-username">{user?.username}</p>
                          <p className="dropdown-email">{user?.email}</p>
                          {user?.phone && <p className="dropdown-phone">📞 {user.phone}</p>}
                        </div>
                      </div>

                      {/* Badges */}
                      <div className="dropdown-badges">
                        {user?.is_verified && <span className="dbadge dbadge--green">✓ Verified</span>}
                        {user?.is_owner
                          ? <span className="dbadge dbadge--blue">🏢 Owner</span>
                          : <span className="dbadge dbadge--orange">✈ Traveler</span>
                        }
                      </div>

                      {/* Joined & Last Login */}
                      <div className="dropdown-meta">
                        <span>📅 Member since 2024</span>
                      </div>

                      <div className="dropdown-divider" />

                      <Link to="/profile"      className="dropdown-item"><span className="di-icon">👤</span> My Profile</Link>
                      <Link to="/bookings"     className="dropdown-item"><span className="di-icon">🏨</span> My Bookings</Link>
                      <Link to="/reviews"      className="dropdown-item"><span className="di-icon">⭐</span> My Reviews</Link>
                      <Link to="/profile/edit" className="dropdown-item"><span className="di-icon">✏️</span> Edit Profile</Link>

                      {user?.is_owner && (
                        <>
                          <div className="dropdown-divider" />
                          <Link to="/dashboard" className="dropdown-item dropdown-item--purple">
                            <span className="di-icon">📊</span> Owner Dashboard
                          </Link>
                        </>
                      )}

                      <div className="dropdown-divider" />

                      <button className="dropdown-logout" onClick={logout}>
                        <span className="di-icon">🚪</span> Logout
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <div className="auth-btns">
                  <Link to="/login"    className="btn-ghost">Login</Link>
                  <Link to="/register" className="btn-solid">Get Started</Link>
                </div>
              )}
            </div>

            <button
              className={`hamburger ${menuOpen ? "hamburger--open" : ""}`}
              onClick={() => setMenuOpen(!menuOpen)}
            >
              <span /><span /><span />
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile Drawer */}
      <div className={`mobile-drawer ${menuOpen ? "mobile-drawer--open" : ""}`}>
        <div className="mobile-drawer__inner">
          {loggedIn && user && (
            <div className="mobile-user-card">
              <div className="mobile-avatar">{initials}</div>
              <div>
                <p className="mobile-uname">{user.username}</p>
                <p className="mobile-uemail">{user.email}</p>
              </div>
            </div>
          )}
          <div className="mobile-divider" />
          {NAV_LINKS.map((l) => (
            <Link key={l.path} to={l.path} className="mobile-nav-link">
              <span>{l.icon}</span> {l.label}
            </Link>
          ))}
          <div className="mobile-divider" />
          {loggedIn ? (
            <>
              <Link to="/profile"      className="mobile-nav-link">👤 Profile</Link>
              <Link to="/bookings"     className="mobile-nav-link">🏨 Bookings</Link>
              <Link to="/profile/edit" className="mobile-nav-link">✏️ Edit Profile</Link>
              <button className="mobile-nav-link mobile-logout" onClick={logout}>🚪 Logout</button>
            </>
          ) : (
            <>
              <Link to="/login"    className="mobile-auth-btn mobile-auth-btn--ghost">Login</Link>
              <Link to="/register" className="mobile-auth-btn mobile-auth-btn--solid">Get Started</Link>
            </>
          )}
        </div>
      </div>

      {menuOpen && <div className="drawer-overlay" onClick={() => setMenuOpen(false)} />}
    </>
  );
}
