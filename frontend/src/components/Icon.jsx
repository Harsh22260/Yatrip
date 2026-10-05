/**
 * Stroke icon set, replacing the emoji that were doing duty as icons.
 *
 * Emoji rendered differently on every platform, broke alignment against text,
 * and could not inherit `currentColor`, so a whole icon could not change hue
 * with its state. These are 24x24, 2px stroke, round caps and joins, drawn on
 * the same grid so they sit evenly next to 15px DM Sans.
 *
 * Usage:  <Icon name="hotel" size={20} />
 *         <Icon name="star" filled />        // solid, for ratings
 */

const P = {
  /* ── Browse categories ─────────────────────────────────────────────── */
  hotel: (
    <>
      <path d="M2 18v-6a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v6" />
      <path d="M2 14h20M2 18v2M22 18v2" />
      <path d="M6 10V7a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v3" />
    </>
  ),
  landmark: (
    <>
      <path d="M3 22h18M6 18v-7M10 18v-7M14 18v-7M18 18v-7" />
      <path d="M4 10.5V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v4.5" />
    </>
  ),
  utensils: (
    <>
      <path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2" />
      <path d="M7 2v20" />
      <path d="M21 15V2a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3zM21 15v7" />
    </>
  ),
  bus: (
    <>
      <rect x="3" y="3" width="18" height="12" rx="3" />
      <path d="M3 9.5h18" />
      <circle cx="7.5" cy="16.5" r="1.5" />
      <circle cx="16.5" cy="16.5" r="1.5" />
    </>
  ),
  car: (
    <>
      <path d="M4 17v-4l2-5.5A2 2 0 0 1 7.9 6h8.2a2 2 0 0 1 1.9 1.5L20 13v4" />
      <path d="M3 17h18M6.5 17v2M17.5 17v2" />
      <circle cx="8" cy="13.5" r="1.1" />
      <circle cx="16" cy="13.5" r="1.1" />
    </>
  ),
  sparkles: (
    <>
      <path d="M11 3.5 12.7 8l4.5 1.7-4.5 1.7L11 16l-1.7-4.6L4.8 9.7 9.3 8z" />
      <path d="M18 14.5l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z" />
    </>
  ),

  /* ── Owner / business ──────────────────────────────────────────────── */
  building: (
    <>
      <path d="M4 21V5a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v16" />
      <path d="M15 9h3a2 2 0 0 1 2 2v10M2 21h20" />
      <path d="M8 7h2M8 11h2M8 15h2" />
    </>
  ),
  wallet: (
    <>
      <path d="M3 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v1" />
      <path d="M3 7v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7a2 2 0 0 0-2-2H5" />
      <circle cx="17" cy="13" r="1.3" />
    </>
  ),
  users: (
    <>
      <circle cx="9" cy="8" r="3.5" />
      <path d="M2.5 20a6.5 6.5 0 0 1 13 0" />
      <path d="M16.5 5.2a3.5 3.5 0 0 1 0 5.6M17.5 14.6a6.5 6.5 0 0 1 4 5.4" />
    </>
  ),
  award: (
    <>
      <circle cx="12" cy="9" r="5.5" />
      <path d="m8.5 13.5-1.5 8L12 19l5 2.5-1.5-8" />
    </>
  ),

  /* ── Chrome ────────────────────────────────────────────────────────── */
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m20.5 20.5-4.2-4.2" />
    </>
  ),
  menu: <path d="M3 6h18M3 12h18M3 18h18" />,
  close: <path d="M18 6 6 18M6 6l12 12" />,
  chevronDown: <path d="m6 9 6 6 6-6" />,
  chevronRight: <path d="m9 6 6 6-6 6" />,
  arrowRight: <path d="M4 12h15M13 6l6 6-6 6" />,
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1" />
    </>
  ),
  logout: (
    <>
      <path d="M9 21H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3" />
      <path d="m15 16 5-4-5-4M20 12H9" />
    </>
  ),
  userPlus: (
    <>
      <circle cx="9" cy="8" r="4" />
      <path d="M2 21v-1a6 6 0 0 1 6-6h3M19 8v6M16 11h6" />
    </>
  ),

  /* ── Detail & meta ─────────────────────────────────────────────────── */
  pin: (
    <>
      <path d="M12 21.5S19 16 19 10.5a7 7 0 1 0-14 0C5 16 12 21.5 12 21.5z" />
      <circle cx="12" cy="10.5" r="2.6" />
    </>
  ),
  compass: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="m15.6 8.4-2 5.2-5.2 2 2-5.2z" />
    </>
  ),
  star: <path d="m12 3.5 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17.5l-5.4 2.9 1-6.1L3.2 10l6.1-.9z" />,
  heart: (
    <path d="M20.8 5.9a5 5 0 0 0-7.1 0L12 7.6l-1.7-1.7a5 5 0 1 0-7.1 7.1l8.8 8.8 8.8-8.8a5 5 0 0 0 0-7.1z" />
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5.3l3.4 2" />
    </>
  ),
  calendar: (
    <>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M3 10h18M8 3v4M16 3v4" />
    </>
  ),
  phone: <path d="M5 3h3l1.8 5-2.4 1.5a11 11 0 0 0 5.1 5.1L14 12.2 19 14v3a2 2 0 0 1-2 2A15 15 0 0 1 3 5a2 2 0 0 1 2-2z" />,
  mail: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="m3.5 7 8.5 6 8.5-6" />
    </>
  ),
  badgeCheck: (
    <>
      <path d="M3.9 8.6a4 4 0 0 1 4.8-4.8 4 4 0 0 1 6.7 0 4 4 0 0 1 4.7 4.8 4 4 0 0 1 0 6.7 4 4 0 0 1-4.8 4.8 4 4 0 0 1-6.7 0 4 4 0 0 1-4.8-4.8 4 4 0 0 1 0-6.7z" />
      <path d="m9 12 2.2 2.2L15.5 10" />
    </>
  ),
  shield: (
    <>
      <path d="M12 22s8-3.6 8-10.2V5.6L12 2.4 4 5.6v6.2C4 18.4 12 22 12 22z" />
      <path d="m9 11.8 2.2 2.2 4.3-4.3" />
    </>
  ),
  globe: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18" />
      <path d="M12 3a14 14 0 0 1 0 18 14 14 0 0 1 0-18z" />
    </>
  ),
  rupee: <path d="M7 4h10M7 8.5h10M15.5 4c0 4.4-3.4 6.5-8.5 6.5L18 20" />,
  check: <path d="m5 13 4.5 4.5L19 7" />,
  plus: <path d="M12 5v14M5 12h14" />,
  minus: <path d="M5 12h14" />,
  filter: <path d="M3 5h18M6.5 12h11M10 19h4" />,
  zap: <path d="M13 2.5 4.5 14H11l-1 7.5L19.5 10H13z" />,
  trendingUp: <path d="m3 17 6-6 4 4 8-8M15 7h6v6" />,
  send: <path d="M21.5 2.5 11 13M21.5 2.5 15 21.5l-4-8.5-8.5-4z" />,
  image: (
    <>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <circle cx="8.5" cy="9.5" r="1.6" />
      <path d="m4 17 5-4.5 3.5 3 3-2.5L20 17" />
    </>
  ),
  bug: (
    <>
      <path d="M9 5.5a3 3 0 0 1 6 0" />
      <rect x="6" y="6" width="12" height="12.5" rx="6" />
      <path d="M2 12.5h4M18 12.5h4M3.5 7.8l3 1.4M20.5 7.8l-3 1.4M3.5 17.2l3-1.4M20.5 17.2l-3-1.4" />
      <path d="M12 10v6" />
    </>
  ),
  help: (
    <>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="3.4" />
      <path d="m5.9 5.9 3.7 3.7M14.4 14.4l3.7 3.7M18.1 5.9l-3.7 3.7M9.6 14.4l-3.7 3.7" />
    </>
  ),
  plane: <path d="M10.5 12.5 3 10V8l7.5 1.5V4.5a1.5 1.5 0 0 1 3 0V9.5L21 8v2l-7.5 2.5v5l3 1.5V21l-4.5-1-4.5 1v-2l3-1.5v-5z" />,
};

/** Icons that read better solid than outlined. */
const SOLID = new Set(["star", "heart", "zap", "plane"]);

export default function Icon({
  name,
  size = 20,
  strokeWidth = 1.9,
  filled = false,
  className = "",
  ...rest
}) {
  const glyph = P[name];
  if (!glyph) return null;

  const solid = filled || SOLID.has(name);

  return (
    <svg
      className={`icon ${className}`.trim()}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={solid ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth={solid ? strokeWidth * 0.55 : strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      {glyph}
    </svg>
  );
}