import { useState, useEffect, useRef } from "react";
import { Link, useLocation } from "react-router-dom";
import { logout, getUserProfile, getStoredUser, hasSessionHint } from "../services/authService";
import Logo from "./Logo";
import Icon from "./Icon";
import "./Navbar.css";

/* Every link carries an `icon`. The previous NAV_LINKS had no icon key while
   the markup rendered one, so the icon slot rendered empty on every desktop
   nav item. */
const NAV_LINKS = [
  { label: "Hotels",      path: "/hotels",      icon: "hotel"    },
  { label: "Attractions", path: "/attractions", icon: "landmark" },
  { label: "Food",        path: "/food",        icon: "utensils" },
  { label: "Transport",   path: "/transport",   icon: "bus"      },
  { label: "Rentals",     path: "/rentals",     icon: "car"      },
  { label: "AI Planner",  path: "/chatbot",     icon: "sparkles" },
];

/** Owner sections, shown as one group in the dropdown. */
const OWNER_LINKS = [
  { label: "My Hotels",      path: "/my-hotels",      icon: "hotel"    },
  { label: "My Rentals",     path: "/my-rentals",     icon: "car"      },
  { label: "My Food Places", path: "/my-food-places", icon: "utensils" },
  { label: "My Attractions", path: "/my-attractions", icon: "landmark" },
];

export default function Navbar() {
  const [menuOpen, setMenuOpen]       = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [user, setUser]               = useState(() => getStoredUser());
  const dropdownRef                   = useRef(null);
  const location                      = useLocation();
  // The access token is an HttpOnly cookie, so there is nothing synchronous to
  // read: the session hint in sessionStorage only avoids a flash of the
  // signed-out navbar, and /profile/ is what actually decides.
  const [loggedIn, setLoggedIn]       = useState(() => hasSessionHint() || !!getStoredUser());

  useEffect(() => {
    let active = true;
    // Always ask the server, even without a hint: a hint can be stale after a
    // cookie expired, and the old code skipped the check entirely and left
    // stale user data on screen.
    getUserProfile()
      .then((profile) => {
        if (!active) return;
        setUser(profile);
        setLoggedIn(true);
      })
      .catch(() => {
        if (!active) return;
        setLoggedIn(false);
        setUser(null);
      });
    return () => { active = false; };
  }, [location.pathname]);

  const handleLogout = async () => {
    setLoggedIn(false);
    setUser(null);
    await logout();
  };

  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Escape closes whichever menu is open. Without this the mobile drawer can
  // only be dismissed by hitting the hamburger again or the overlay.
  useEffect(() => {
    if (!menuOpen && !profileOpen) return undefined;
    const onKey = (e) => {
      if (e.key !== "Escape") return;
      setMenuOpen(false);
      setProfileOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [menuOpen, profileOpen]);

  // The drawer covers the viewport, so the page behind it must not scroll.
  useEffect(() => {
    if (!menuOpen) return undefined;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = prev; };
  }, [menuOpen]);

  // Close the open menus when a link is followed. Done in the click handler
  // rather than an effect: it avoids a frame where the drawer is still open on
  // the new page, and avoids setState inside an effect.
  const closeMenus = () => {
    setMenuOpen(false);
    setProfileOpen(false);
  };

  const initials = user?.username?.[0]?.toUpperCase() || "U";

  return (
    <>
      <nav className="navbar">
        <div className="navbar__inner">
          <Link to="/" className="navbar__logo" onClick={closeMenus} aria-label="Yatrip home">
            <Logo size={38} tagline />
          </Link>

          <div className="navbar__right-group">
            <ul className="navbar__links">
              {NAV_LINKS.map((l) => (
                <li key={l.path}>
                  <Link
                    to={l.path}
                    onClick={closeMenus}
                    className={`nav-link ${location.pathname.startsWith(l.path) ? "nav-link--active" : ""}`}
                  >
                    <Icon name={l.icon} size={17} className="nav-link__icon" />
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
                    aria-expanded={profileOpen}
                    aria-haspopup="true"
                  >
                    <div className="profile-avatar-circle">{initials}</div>
                    <div className="profile-trigger-info">
                      <span className="profile-trigger-name">{user?.username || "User"}</span>
                      <span className="profile-trigger-role">
                        {user?.is_owner ? "Business Owner" : "Traveler"}
                      </span>
                    </div>
                    <Icon name="chevronDown" size={15} className={`chevron ${profileOpen ? "chevron--up" : ""}`} />
                  </button>

                  {profileOpen && (
                    <div className="profile-dropdown">
                      <div className="dropdown-header">
                        <div className="dropdown-avatar">{initials}</div>
                        <div className="dropdown-userinfo">
                          <p className="dropdown-username">{user?.username}</p>
                          <p className="dropdown-email">{user?.email}</p>
                          {user?.phone && (
                            <p className="dropdown-phone">
                              <Icon name="phone" size={12} /> {user.phone}
                            </p>
                          )}
                        </div>
                      </div>

                      <div className="dropdown-badges">
                        {user?.is_verified && (
                          <span className="dbadge dbadge--green">
                            <Icon name="badgeCheck" size={12} /> Verified
                          </span>
                        )}
                        <span className={`dbadge ${user?.is_owner ? "dbadge--blue" : "dbadge--orange"}`}>
                          <Icon name={user?.is_owner ? "building" : "plane"} size={12} />
                          {user?.is_owner ? "Owner" : "Traveler"}
                        </span>
                      </div>

                      <div className="dropdown-meta">
                        <Icon name="calendar" size={12} />
                        {user?.created_at
                          ? `Member since ${new Date(user.created_at).getFullYear()}`
                          : "Yatrip member"}
                      </div>

                      <div className="dropdown-divider" />

                      <Link to="/profile" onClick={closeMenus} className="dropdown-item">
                        <Icon name="user" size={15} /> My Profile
                      </Link>
                      <Link to="/my-bookings" onClick={closeMenus} className="dropdown-item">
                        <Icon name="hotel" size={15} /> My Bookings
                      </Link>

                      {user?.is_owner && (
                        <>
                          <div className="dropdown-divider" />
                          <p className="dropdown-group">My Listings</p>
                          {OWNER_LINKS.map((l) => (
                            <Link key={l.path} to={l.path} onClick={closeMenus} className="dropdown-item dropdown-item--purple">
                              <Icon name={l.icon} size={15} /> {l.label}
                            </Link>
                          ))}
                        </>
                      )}

                      <div className="dropdown-divider" />

                      <button className="dropdown-logout" onClick={handleLogout}>
                        <Icon name="logout" size={15} /> Logout
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
              aria-label={menuOpen ? "Close menu" : "Open menu"}
              aria-expanded={menuOpen}
            >
              <span /><span /><span />
            </button>
          </div>
        </div>
      </nav>

      <div
        className={`mobile-drawer ${menuOpen ? "mobile-drawer--open" : ""}`}
        aria-hidden={!menuOpen}
      >
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
            <Link
              key={l.path}
              to={l.path}
              onClick={closeMenus}
              tabIndex={menuOpen ? 0 : -1}
              className={`mobile-nav-link ${location.pathname.startsWith(l.path) ? "mobile-nav-link--active" : ""}`}
            >
              <Icon name={l.icon} size={18} /> {l.label}
            </Link>
          ))}

          <div className="mobile-divider" />

          {loggedIn ? (
            <>
              <Link to="/profile" onClick={closeMenus} tabIndex={menuOpen ? 0 : -1} className="mobile-nav-link">
                <Icon name="user" size={18} /> Profile
              </Link>
              <Link to="/my-bookings" onClick={closeMenus} tabIndex={menuOpen ? 0 : -1} className="mobile-nav-link">
                <Icon name="hotel" size={18} /> My Bookings
              </Link>
              {user?.is_owner && OWNER_LINKS.map((l) => (
                <Link key={l.path} to={l.path} onClick={closeMenus} tabIndex={menuOpen ? 0 : -1} className="mobile-nav-link">
                  <Icon name={l.icon} size={18} /> {l.label}
                </Link>
              ))}
              <button className="mobile-nav-link mobile-logout" onClick={handleLogout}>
                <Icon name="logout" size={18} /> Logout
              </button>
            </>
          ) : (
            <div className="mobile-auth-row">
              <Link to="/login"    onClick={closeMenus} tabIndex={menuOpen ? 0 : -1} className="yt-btn yt-btn--ghost">Login</Link>
              <Link to="/register" onClick={closeMenus} tabIndex={menuOpen ? 0 : -1} className="yt-btn yt-btn--primary">Get Started</Link>
            </div>
          )}
        </div>
      </div>

      {menuOpen && <div className="drawer-overlay" onClick={() => setMenuOpen(false)} />}
    </>
  );
}