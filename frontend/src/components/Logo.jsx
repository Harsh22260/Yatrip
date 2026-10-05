import { useId } from "react";
import "./Logo.css";

/**
 * The Yatrip mark: a paper plane climbing out of a saffron squircle on a
 * dotted flight trail. Saffron because the brand colour is warm Indian
 * saffron; the plane because the product is travel; the trail because most of
 * what Yatrip actually sells -- transport, routes, nearby stops -- is the
 * getting-there.
 *
 * `public/favicon.svg` is the same geometry at a fixed 48px for the browser
 * tab. Keep the two in step if the mark changes.
 *
 * The plane path is Material's "send" icon scaled by 1.4 into a 48-unit box,
 * which is why it is expressed as literal coordinates rather than a transform:
 * it then scales cleanly at 16px in the tab and 40px in the navbar without a
 * separate small-size variant.
 */
export default function Logo({
  variant = "full",
  size = 36,
  className = "",
  tagline = false,
}) {
  // Several Logos render on a page at once (navbar + footer). useId keeps the
  // gradient references unique so they cannot collide.
  const uid = useId().replace(/:/g, "");
  const g = `yt-logo-fill-${uid}`;
  const s = `yt-logo-sheen-${uid}`;

  return (
    <span className={`logo logo--${variant} ${className}`.trim()}>
      <svg
        className="logo__mark"
        width={size}
        height={size}
        viewBox="0 0 48 48"
        role="img"
        aria-label="Yatrip"
        focusable="false"
      >
        <defs>
          <linearGradient id={g} x1="4" y1="3" x2="44" y2="45" gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor="var(--brand-300)" />
            <stop offset=".5" stopColor="var(--brand-500)" />
            <stop offset="1" stopColor="var(--brand-700)" />
          </linearGradient>
          <linearGradient id={s} x1="24" y1="1" x2="24" y2="47" gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor="#fff" stopOpacity=".3" />
            <stop offset=".55" stopColor="#fff" stopOpacity="0" />
          </linearGradient>
        </defs>

        <rect x="1" y="1" width="46" height="46" rx="14" fill={`url(#${g})`} />
        <rect x="1" y="1" width="46" height="46" rx="14" fill={`url(#${s})`} />
        <rect
          x="1.5"
          y="1.5"
          width="45"
          height="45"
          rx="13.5"
          fill="none"
          stroke="rgba(255,255,255,.22)"
        />

        {/* dotted trail, tucked under the tail */}
        <path
          d="M8.5 42.5c0-5.2 3.1-8.4 7.2-10.4"
          fill="none"
          stroke="#fff"
          strokeOpacity=".5"
          strokeWidth="2"
          strokeLinecap="round"
          strokeDasharray="0.1 3.8"
        />

        {/* paper plane */}
        <path d="M10 36.6 39.4 24 10 11.4v9.8l21 2.8-21 2.8z" fill="#fff" />
      </svg>

      {variant !== "mark" && (
        <span className="logo__word">
          <span className="logo__word-a">Ya</span>
          <span className="logo__word-b">trip</span>
          {tagline && <span className="logo__tagline">Explore India</span>}
        </span>
      )}
    </span>
  );
}