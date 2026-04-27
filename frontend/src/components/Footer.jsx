import { Link } from "react-router-dom";
import "./Footer.css";

const LINKS = {
  Explore: [
    { label: "Hotels",      path: "/hotels" },
    { label: "Attractions", path: "/attractions" },
    { label: "Food",        path: "/food" },
    { label: "Transport",   path: "/transport" },
    { label: "Rentals",     path: "/rentals" },
  ],
  Account: [
    { label: "Login",    path: "/login" },
    { label: "Register", path: "/register" },
    { label: "Profile",  path: "/profile" },
    { label: "Bookings", path: "/bookings" },
  ],
  Support: [
    { label: "About Us",    path: "/about" },
    { label: "Contact",     path: "/contact" },
    { label: "Privacy",     path: "/privacy" },
    { label: "Terms",       path: "/terms" },
  ],
};

export default function Footer() {
  return (
    <footer className="footer">
      {/* Wave top */}
      <div className="footer-wave">
        <svg viewBox="0 0 1440 80" preserveAspectRatio="none">
          <path d="M0,40 C360,80 1080,0 1440,40 L1440,80 L0,80 Z" fill="#0d0d1a" />
        </svg>
      </div>

      <div className="footer__inner">
        {/* Brand col */}
        <div className="footer-brand-col">
          <Link to="/" className="footer-logo">
            <span>✈</span>
            <span>Ya<span className="footer-accent">trip</span></span>
          </Link>
          <p className="footer-tagline">
            Discover India's finest destinations. Book hotels, explore attractions,
            taste local cuisine & travel in comfort.
          </p>

          {/* Social */}
          <div className="footer-socials">
            {[
              { icon: "𝕏", label: "Twitter",   href: "#" },
              { icon: "in", label: "LinkedIn",  href: "#" },
              { icon: "f",  label: "Facebook",  href: "#" },
              { icon: "▶",  label: "YouTube",   href: "#" },
            ].map((s) => (
              <a key={s.label} href={s.href} className="social-btn" title={s.label}>
                {s.icon}
              </a>
            ))}
          </div>

          {/* App badges */}
          <div className="app-badges">
            <div className="app-badge">
              <span className="badge-icon">🍎</span>
              <div>
                <p className="badge-sub">Download on the</p>
                <p className="badge-main">App Store</p>
              </div>
            </div>
            <div className="app-badge">
              <span className="badge-icon">▶</span>
              <div>
                <p className="badge-sub">Get it on</p>
                <p className="badge-main">Google Play</p>
              </div>
            </div>
          </div>
        </div>

        {/* Link cols */}
        {Object.entries(LINKS).map(([title, items]) => (
          <div key={title} className="footer-link-col">
            <h4 className="footer-col-title">{title}</h4>
            <ul className="footer-link-list">
              {items.map((item) => (
                <li key={item.path}>
                  <Link to={item.path} className="footer-link">{item.label}</Link>
                </li>
              ))}
            </ul>
          </div>
        ))}

        {/* Newsletter */}
        <div className="footer-newsletter-col">
          <h4 className="footer-col-title">Stay Updated</h4>
          <p className="newsletter-text">
            Get the best travel deals & destination guides in your inbox.
          </p>
          <div className="newsletter-form">
            <input
              type="email"
              placeholder="your@email.com"
              className="newsletter-input"
            />
            <button className="newsletter-btn">→</button>
          </div>
          <div className="footer-stats">
            {[
              { num: "500+", label: "Destinations" },
              { num: "10K+", label: "Happy Travelers" },
              { num: "4.9★", label: "Avg Rating" },
            ].map((s) => (
              <div key={s.label} className="footer-stat">
                <span className="stat-num">{s.num}</span>
                <span className="stat-label">{s.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom bar */}
      <div className="footer-bottom">
        <p>© {new Date().getFullYear()} Yatrip. Made with ❤️ for Indian travelers.</p>
        <div className="footer-bottom-links">
          <Link to="/privacy">Privacy</Link>
          <span>·</span>
          <Link to="/terms">Terms</Link>
          <span>·</span>
          <Link to="/sitemap">Sitemap</Link>
        </div>
      </div>
    </footer>
  );
}
