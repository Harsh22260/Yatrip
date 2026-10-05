import { useState } from "react";
import { Link } from "react-router-dom";
import Logo from "./Logo";
import Icon from "./Icon";
import { allFallbackCredits } from "../utils/foodFallbackImages";
import "./Footer.css";

const COLUMNS = {
  Explore: [
    { label: "Hotels", path: "/hotels", icon: "hotel" },
    { label: "Attractions", path: "/attractions", icon: "landmark" },
    { label: "Food", path: "/food", icon: "utensils" },
    { label: "Transport", path: "/transport", icon: "bus" },
    { label: "Rentals", path: "/rentals", icon: "car" },
    { label: "AI Planner", path: "/chatbot", icon: "sparkles" },
  ],
  Account: [
    { label: "Login", path: "/login", icon: "logout" },
    { label: "Create account", path: "/register", icon: "userPlus" },
    { label: "My bookings", path: "/my-bookings", icon: "calendar" },
    { label: "List your property", path: "/register-hotel", icon: "building" },
  ],
  Company: [
    { label: "About us", path: "/about", icon: "compass" },
    { label: "Contact", path: "/contact", icon: "mail" },
    { label: "Privacy", path: "/privacy", icon: "shield" },
    { label: "Terms", path: "/terms", icon: "badgeCheck" },
  ],
};

const STATS = [
  { num: "500+", label: "Destinations" },
  { num: "10K+", label: "Travelers" },
  { num: "4.9", label: "Avg rating", star: true },
];

// Food photographs are bundled with the app, and several are CC BY / CC BY-SA,
// which require attribution. Listing them here is the other half of the credit
// shown on the card itself.
const PHOTO_CREDITS = allFallbackCredits();

export default function Footer() {
  const [email, setEmail] = useState("");
  const [state, setState] = useState("idle"); // idle | done | error

  // There is no newsletter endpoint on the backend yet. Until one exists this
  // validates and acknowledges locally rather than posting into the void.
  const subscribe = (e) => {
    e.preventDefault();
    const ok = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email.trim());
    setState(ok ? "done" : "error");
    if (ok) setEmail("");
  };

  return (
    <footer className="footer">
      {/* See the note on .footer-wave in Footer.css. */}
      <div className="footer-wave" aria-hidden="true">
        <svg viewBox="0 0 1440 90" preserveAspectRatio="none">
          {/* Filled with the PAGE colour, not the footer colour, and sitting at
              top:0 inside the footer. That makes it carve a curved notch out of
              the footer's top edge: the page-coloured shape meets the page above
              seamlessly, so the curve is the boundary between the two colours.
              Painting the footer colour instead just redrew the footer's own
              background and was invisible.

              The trace is a single S: it leaves both ends at mid height (y=45),
              crests at y=16 right of centre, and dips to y=74 left of centre.
              One crest plus one trough is what makes it read as an S -- the
              earlier path peaked once in the middle and came down at both ends,
              which is a dome.

              Direction is reversed on purpose: this path is drawn right-to-left
              because the filled region has to sit ABOVE the curve. */}
          <path
            d="M0,0 L1440,0 L1440,45 C1260,45 1120,16 940,16 C760,16 620,74 440,74 C260,74 180,45 0,45 Z"
            fill="var(--bg-body)"
          />
        </svg>
      </div>

      <div className="footer__inner">
        <div className="footer-brand-col">
          <Link to="/" className="footer-logo" aria-label="Yatrip home">
            <Logo size={42} />
          </Link>

          <p className="footer-tagline">
            Hotels, food, attractions, transport and rentals across India — with an
            AI planner that turns a rough idea into a real itinerary.
          </p>

          <ul className="footer-badges">
            <li className="footer-badge">
              <Icon name="shield" size={15} /> Secure bookings
            </li>
            <li className="footer-badge">
              <Icon name="zap" size={15} /> Instant confirmation
            </li>
            <li className="footer-badge">
              <Icon name="sparkles" size={15} /> AI trip planner
            </li>
          </ul>

          <div className="footer-newsletter">
            <h4 className="footer-col-title">Trip ideas, monthly</h4>
            <p className="newsletter-text">
              One email a month: new destinations, seasonal guides and price drops.
            </p>
            <form className="newsletter-form" onSubmit={subscribe} noValidate>
              <label htmlFor="footer-email" className="u-sr">
                Email address
              </label>
              <Icon name="mail" size={16} className="newsletter-icon" />
              <input
                id="footer-email"
                type="email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (state !== "idle") setState("idle");
                }}
                placeholder="you@example.com"
                className="newsletter-input"
                aria-invalid={state === "error"}
              />
              <button type="submit" className="newsletter-btn" aria-label="Subscribe">
                <Icon name="arrowRight" size={17} />
              </button>
            </form>
            {state === "done" && (
              <p className="newsletter-msg newsletter-msg--ok">
                <Icon name="check" size={13} /> You are on the list.
              </p>
            )}
            {state === "error" && (
              <p className="newsletter-msg newsletter-msg--bad">
                <Icon name="close" size={13} /> Please enter a valid email.
              </p>
            )}
          </div>
        </div>

        {Object.entries(COLUMNS).map(([title, items]) => (
          <nav key={title} className="footer-link-col" aria-label={title}>
            <h4 className="footer-col-title">{title}</h4>
            <ul className="footer-link-list">
              {items.map((item) => (
                <li key={item.path}>
                  <Link to={item.path} className="footer-link">
                    <Icon name={item.icon} size={15} className="footer-link-icon" />
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        ))}
      </div>

      <div className="footer-stats">
        {STATS.map((s) => (
          <div key={s.label} className="footer-stat">
            <span className="stat-num">
              {s.num}
              {s.star && <Icon name="star" size={16} filled className="stat-star" />}
            </span>
            <span className="stat-label">{s.label}</span>
          </div>
        ))}
      </div>

      <div className="footer-bottom">
        <p>
          © {new Date().getFullYear()} Yatrip. Built for Indian travellers.
        </p>
        <ul className="footer-bottom-links">
          <li><Link to="/privacy">Privacy</Link></li>
          <li><Link to="/terms">Terms</Link></li>
          <li><Link to="/contact">Contact</Link></li>
        </ul>
      </div>

      <details className="footer-credits">
        <summary>Photo credits</summary>
        <p className="footer-credits-note">
          Food cards without a photograph of the place itself show a bundled
          photograph of that category. Place names and business data come from
          OpenStreetMap contributors.
        </p>
        <ul className="footer-credits-list">
          {PHOTO_CREDITS.map((photo) => (
            <li key={photo.category}>
              <a href={photo.commonsPage} target="_blank" rel="noreferrer noopener">
                {photo.source}
              </a>
              <span>
                {" "}— {photo.author}, {photo.licence}
              </span>
            </li>
          ))}
        </ul>
      </details>
    </footer>
  );
}