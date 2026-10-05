import { Link } from "react-router-dom";
import Icon from "../components/Icon";
import "./NotFound.css";

/**
 * Catch-all route. Previously an unrecognised path matched no <Route>, so
 * React rendered nothing between the navbar and footer — a blank page with
 * working chrome and no explanation.
 */

const SUGGESTIONS = [
  { to: "/hotels",      label: "Hotels",      icon: "hotel" },
  { to: "/attractions", label: "Attractions", icon: "landmark" },
  { to: "/food",        label: "Food",        icon: "utensils" },
  { to: "/transport",   label: "Transport",   icon: "bus" },
  { to: "/chatbot",     label: "AI Planner",  icon: "sparkles" },
];

export default function NotFound() {
  return (
    <div className="nf">
      <div className="nf-inner">
        <p className="nf-code">404</p>
        <h1 className="nf-title">This route doesn't exist</h1>
        <p className="nf-sub">
          The page you were looking for has moved or never existed. Nothing was
          charged and nothing was lost — try one of these instead.
        </p>

        <div className="nf-actions">
          <Link to="/" className="yt-btn yt-btn--primary yt-btn--lg">
            <Icon name="compass" size={17} /> Back to home
          </Link>
          <Link to="/hotels" className="yt-btn yt-btn--ghost yt-btn--lg">
            Browse hotels
          </Link>
        </div>

        <div className="nf-suggestions">
          <p className="nf-suggestions-label">Popular sections</p>
          <ul>
            {SUGGESTIONS.map((s) => (
              <li key={s.to}>
                <Link to={s.to} className="nf-suggestion">
                  <Icon name={s.icon} size={16} /> {s.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}