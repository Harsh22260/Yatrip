import { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import Icon from "../components/Icon";
import "./Home.css";

/* ── Data ────────────────────────────────────────────────────────────────
   Kept as plain constants below, but note the `image` fields: these point at
   files in public/images, credited in public/images/CREDITS.md.            */

const CATEGORIES = [
  {
    key: "hotels", icon: "hotel", label: "Hotels", sub: "1,200+ properties",
    path: "/hotels", image: "/images/categories/hotels.jpg",
  },
  {
    key: "attractions", icon: "landmark", label: "Attractions", sub: "500+ places",
    path: "/attractions", image: "/images/categories/attractions.jpg",
  },
  {
    key: "food", icon: "utensils", label: "Food", sub: "300+ places to eat",
    path: "/food", image: "/images/categories/food.jpg",
  },
  {
    key: "transport", icon: "bus", label: "Transport", sub: "Routes & nearby stops",
    path: "/transport", image: "/images/categories/transport.jpg",
  },
  {
    key: "rentals", icon: "car", label: "Rentals", sub: "Cars, bikes & homestays",
    path: "/rentals", image: "/images/categories/rentals.jpg",
  },
  {
    // No photograph: this one is a product surface, not a place. A gradient
    // reads better than a stock image of a laptop.
    key: "chatbot", icon: "sparkles", label: "AI Planner", sub: "Build an itinerary",
    path: "/chatbot", accent: true,
  },
];

const DESTINATIONS = [
  { name: "Rajasthan", tag: "Royal Heritage",     image: "/images/destinations/rajasthan.jpg", alt: "Hawa Mahal, Jaipur", trips: "2.4k" },
  { name: "Kerala",    tag: "God's Own Country",  image: "/images/destinations/kerala.jpg",    alt: "Houseboats on the Alappuzha backwaters", trips: "3.1k" },
  { name: "Goa",       tag: "Sun & Surf",         image: "/images/destinations/goa.jpg",       alt: "Palolem Beach, South Goa", trips: "5.2k" },
  { name: "Himachal",  tag: "Mountain Escape",    image: "/images/destinations/himachal.jpg",  alt: "Kullu Valley near Manali", trips: "1.8k" },
  { name: "Varanasi",  tag: "Spiritual Journey",  image: "/images/destinations/varanasi.jpg",  alt: "Dashashwamedh Ghat on the Ganges", trips: "1.2k" },
  { name: "Ladakh",    tag: "Wild Frontier",      image: "/images/destinations/ladakh.jpg",    alt: "Hemis Monastery, Ladakh", trips: "900" },
];

/* Each tab sends the query to the page that can actually filter by it. */
const SEARCH_TABS = [
  { label: "Hotels",      placeholder: "Hotel, city or area…",            path: "/hotels" },
  { label: "Food",        placeholder: "Restaurant, cuisine or dish…",   path: "/food" },
  { label: "Attractions", placeholder: "Monument, museum or park…",      path: "/attractions" },
  { label: "Rentals",     placeholder: "City to pick up a car or bike…", path: "/rentals" },
];

const QUICK_CITIES = ["Jaipur", "Kerala", "Goa", "Manali", "Varanasi", "Leh"];

const STEPS = [
  { icon: "search", title: "Search",    desc: "Hotels, food spots, attractions and transport across India — all in one search." },
  { icon: "calendar", title: "Book",     desc: "Reserve a room in a couple of taps. Availability is locked in as soon as you confirm." },
  { icon: "plane", title: "Travel",    desc: "Get directions, find a ride and keep every booking in one place." },
  { icon: "star", title: "Review",    desc: "Rate where you stayed and help other travellers find the good ones." },
];

const REVIEWS = [
  { name: "Priya S.",  city: "Mumbai",    stars: 5, text: "Found an amazing heritage hotel in Jaipur through Yatrip. The booking was smooth and the room was exactly as pictured." },
  { name: "Rahul M.",  city: "Delhi",     stars: 5, text: "The AI planner built a whole Kerala itinerary in about a minute. It actually knew which towns to pair up." },
  { name: "Ananya K.", city: "Bengaluru", stars: 5, text: "Rented a bike through Yatrip and did Goa at my own pace. No agent, no counter, no queue." },
  { name: "Vikram T.", city: "Chennai",   stars: 4, text: "The food listings got me to two spots in Varanasi I would never have found on my own." },
];

const STATS = [
  { target: 500,   suffix: "+",  label: "Destinations" },
  { target: 10000, suffix: "+",  label: "Happy travellers" },
  { target: 1200,  suffix: "+",  label: "Hotels listed" },
  { target: 4.9,   suffix: "",   label: "Average rating", decimals: 1, star: true },
];

/* ── Counters ─────────────────────────────────────────────────────────────
   Driven by an IntersectionObserver so the numbers do not run while the
   stats bar is still below the fold.                                        */
function useCounter(target, duration = 1800, start = false, decimals = 0) {
  // Resolved once in a lazy initialiser rather than inside the effect: setting
  // state synchronously in an effect is a cascading render, and this value can
  // never change anyway.
  const [reducedMotion] = useState(
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!start || reducedMotion) return undefined;

    let raf = 0;
    let startedAt = null;

    const step = (t) => {
      if (startedAt === null) startedAt = t;
      const p = Math.min((t - startedAt) / duration, 1);
      // easeOutCubic, so the digits slow down as they land on the value
      // instead of snapping at the end the way linear does.
      const eased = 1 - (1 - p) ** 3;
      setValue(Number((target * eased).toFixed(decimals)));
      if (p < 1) raf = requestAnimationFrame(step);
    };

    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [start, target, duration, decimals, reducedMotion]);

  // Under reduced motion the final value is simply shown, unanimated.
  return reducedMotion ? target : value;
}

function StatCounter({ target, suffix, label, decimals = 0, star, started }) {
  const count = useCounter(target, 1800, started, decimals);
  return (
    <div className="stat-box">
      <span className="stat-big">
        {count.toFixed(decimals)}
        {suffix}
        {star && <Icon name="star" size={20} filled className="stat-star" />}
      </span>
      <span className="stat-lbl">{label}</span>
    </div>
  );
}

/* ── Main ─────────────────────────────────────────────────────────────── */
export default function Home() {
  const [query, setQuery]         = useState("");
  const [statsVisible, setStats]  = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const statsRef = useRef(null);
  const navigate  = useNavigate();

  const tab = SEARCH_TABS[activeTab];

  useEffect(() => {
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setStats(true); },
      { threshold: 0.35 }
    );
    if (statsRef.current) obs.observe(statsRef.current);
    return () => obs.disconnect();
  }, []);

  // Was window.location.href, which threw away the whole SPA and re-ran every
  // module on the way to the hotels page.
  const go = (path, params) => {
    const qs = new URLSearchParams(params).toString();
    navigate(qs ? `${path}?${qs}` : path);
  };

  const handleSearch = (e) => {
    e.preventDefault();
    const q = query.trim();
    if (q) go(tab.path, { search: q });
    else go(tab.path);
  };

  return (
    <div className="home">
      {/* ══ HERO ═══════════════════════════════════════════════════════ */}
      <section className="hero">
        <div className="hero-bg" aria-hidden="true">
          <img
            className="hero-photo"
            src="/images/hero/india.jpg"
            alt=""
            fetchPriority="high"
            decoding="async"
          />
          <div className="hero-scrim" />
          <div className="hero-orb hero-orb--1" />
          <div className="hero-orb hero-orb--2" />
          <div className="hero-grid" />
        </div>

        <div className="hero-content">
          <div className="hero-badge">
            <span className="badge-dot" />
            Trusted by 10,000+ travellers across India
          </div>

          <h1 className="hero-title">
            Explore India
            <span className="hero-title-grad">Your Way</span>
          </h1>

          <p className="hero-subtitle">
            Hotels, food, attractions, transport and rentals — everything you need
            for the perfect Indian adventure, in one place.
          </p>

          <form className="hero-search" onSubmit={handleSearch}>
            <div className="search-tabs" role="tablist" aria-label="Search category">
              {SEARCH_TABS.map((t, i) => (
                <button
                  key={t.label}
                  type="button"
                  role="tab"
                  aria-selected={activeTab === i}
                  className={`search-tab ${activeTab === i ? "search-tab--active" : ""}`}
                  onClick={() => setActiveTab(i)}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <div className="search-bar">
              <Icon name="search" size={20} className="search-icon" />
              <input
                type="search"
                placeholder={tab.placeholder}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="search-input"
                aria-label={`Search ${tab.label.toLowerCase()}`}
              />
              <button type="submit" className="search-btn">
                Search
              </button>
            </div>
          </form>

          <div className="hero-tags">
            <span className="hero-tags-label">Popular</span>
            {QUICK_CITIES.map((c) => (
              <button key={c} type="button" className="hero-tag" onClick={() => go("/hotels", { city: c })}>
                {c}
              </button>
            ))}
          </div>

          <div className="hero-trust">
            <div className="hero-trust-item">
              <Icon name="shield" size={16} /> Secure payments
            </div>
            <div className="hero-trust-item">
              <Icon name="zap" size={16} /> Instant confirmation
            </div>
            <div className="hero-trust-item">
              <Icon name="badgeCheck" size={16} /> Verified listings
            </div>
          </div>
        </div>

        <div className="scroll-cue" aria-hidden="true">
          <span>Scroll to explore</span>
          <div className="scroll-arrow" />
        </div>
      </section>

      {/* ══ STATS ══════════════════════════════════════════════════════ */}
      <section className="stats-section" ref={statsRef}>
        <div className="stats-inner">
          {STATS.map((s, i) => (
            <div key={s.label} className="stats-cell">
              {i > 0 && <span className="stats-divider" aria-hidden="true" />}
              <StatCounter {...s} started={statsVisible} />
            </div>
          ))}
        </div>
      </section>

      {/* ══ CATEGORIES ═════════════════════════════════════════════════ */}
      <section className="section">
        <div className="section-inner">
          <header className="section-header">
            <span className="section-tag">Everything in one place</span>
            <h2 className="section-title">What are you looking for?</h2>
            <p className="section-sub">
              From heritage hotels to a plate of roadside dosas — six ways to plan a trip.
            </p>
          </header>

          <div className="categories-grid">
            {CATEGORIES.map((cat, i) => (
              <Link
                key={cat.key}
                to={cat.path}
                className={`cat-card ${cat.accent ? "cat-card--accent" : ""}`}
                style={{ animationDelay: `${i * 0.07}s` }}
              >
                <div className="cat-media">
                  {cat.image && (
                    <img src={cat.image} alt="" loading="lazy" decoding="async" className="cat-img" />
                  )}
                  <div className="cat-media-scrim" />
                  <span className="cat-icon-wrap">
                    <Icon name={cat.icon} size={24} className="cat-icon" />
                  </span>
                </div>

                <div className="cat-body">
                  <h3 className="cat-label">{cat.label}</h3>
                  <p className="cat-sub">{cat.sub}</p>
                </div>

                <span className="cat-arrow">
                  <Icon name="arrowRight" size={17} />
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ══ DESTINATIONS ═══════════════════════════════════════════════ */}
      <section className="section destinations-section">
        <div className="section-inner">
          <header className="section-header">
            <span className="section-tag">Popular picks</span>
            <h2 className="section-title">Top destinations</h2>
            <p className="section-sub">
              Where travellers are heading right now. Tap through to see stays in that city.
            </p>
          </header>

          <div className="dest-grid">
            {DESTINATIONS.map((d, i) => (
              <Link
                key={d.name}
                to={`/hotels?city=${encodeURIComponent(d.name)}`}
                className="dest-card"
                style={{ animationDelay: `${i * 0.07}s` }}
              >
                <img src={d.image} alt={d.alt} loading="lazy" decoding="async" className="dest-img" />
                <span className="dest-scrim" />

                <div className="dest-top">
                  <span className="dest-chip">
                    <Icon name="plane" size={12} /> {d.trips} trips
                  </span>
                </div>

                <div className="dest-info">
                  <h3 className="dest-name">{d.name}</h3>
                  <p className="dest-tag">
                    <Icon name="pin" size={13} /> {d.tag}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ══ HOW IT WORKS ═══════════════════════════════════════════════ */}
      <section className="section">
        <div className="section-inner">
          <header className="section-header">
            <span className="section-tag">Simple &amp; fast</span>
            <h2 className="section-title">How Yatrip works</h2>
            <p className="section-sub">Four steps from an idea to a booked trip.</p>
          </header>

          <div className="steps-grid">
            {STEPS.map((s, i) => (
              <div key={s.title} className="step-card" style={{ animationDelay: `${i * 0.1}s` }}>
                <span className="step-num">{String(i + 1).padStart(2, "0")}</span>
                <span className="step-icon">
                  <Icon name={s.icon} size={22} />
                </span>
                <h3 className="step-title">{s.title}</h3>
                <p className="step-desc">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══ AI PLANNER CTA ═════════════════════════════════════════════ */}
      <section className="section">
        <div className="section-inner">
          <div className="chatbot-card">
            <div className="chatbot-left">
              <span className="chatbot-badge">
                <Icon name="sparkles" size={14} /> AI powered
              </span>
              <h2 className="chatbot-title">
                Plan the whole trip
                <span>in one conversation</span>
              </h2>
              <p className="chatbot-desc">
                Give the assistant your destination, dates and budget. It searches real
                hotels, restaurants and attractions, then hands you a day-by-day plan you
                can act on.
              </p>

              <ul className="chatbot-points">
                <li><Icon name="check" size={15} /> Day-by-day itineraries</li>
                <li><Icon name="check" size={15} /> Budget-aware picks</li>
                <li><Icon name="check" size={15} /> Live availability</li>
              </ul>

              <Link to="/chatbot" className="chatbot-btn">
                Start planning free <Icon name="arrowRight" size={17} />
              </Link>
            </div>

            <div className="chatbot-right" aria-hidden="true">
              <div className="chat-bubble chat-bubble--user">
                Plan a 3-day trip to Goa under ₹15,000
              </div>
              <div className="chat-bubble chat-bubble--bot">
                <span className="bot-badge">
                  <Icon name="sparkles" size={12} /> Yatrip AI
                </span>
                Here is a plan that fits ₹15,000 for two:
                <strong>Day 1</strong> Palolem Beach + a beach shack dinner
                <strong>Day 2</strong> Old Goa churches, then Fontona Chapel
                <strong>Day 3</strong> Dudhsagar Falls, back to Panaji by evening
              </div>
              <div className="chat-bubble chat-bubble--user">
                Book the Day 1 hotel
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══ REVIEWS ════════════════════════════════════════════════════ */}
      <section className="section">
        <div className="section-inner">
          <header className="section-header">
            <span className="section-tag">Real experiences</span>
            <h2 className="section-title">What travellers say</h2>
            <p className="section-sub">
              <Icon name="star" size={14} filled /> 4.9 average across 10,000+ trips
            </p>
          </header>

          <div className="reviews-grid">
            {REVIEWS.map((r, i) => (
              <figure key={r.name} className="review-card" style={{ animationDelay: `${i * 0.09}s` }}>
                <div className="review-stars" aria-label={`${r.stars} out of 5`}>
                  {Array.from({ length: 5 }, (_, k) => (
                    <Icon
                      key={k}
                      name="star"
                      size={15}
                      filled={k < r.stars}
                      className={k < r.stars ? "star-on" : "star-off"}
                    />
                  ))}
                </div>

                <blockquote className="review-text">{r.text}</blockquote>

                <figcaption className="review-author">
                  <span className="review-avatar">{r.name[0]}</span>
                  <span>
                    <span className="review-name">{r.name}</span>
                    <span className="review-city">
                      <Icon name="pin" size={12} /> {r.city}
                    </span>
                  </span>
                </figcaption>
              </figure>
            ))}
          </div>
        </div>
      </section>

      {/* ══ FINAL CTA ══════════════════════════════════════════════════ */}
      <section className="section">
        <div className="section-inner">
          <div className="cta-card">
            <div className="cta-orb cta-orb--1" aria-hidden="true" />
            <div className="cta-orb cta-orb--2" aria-hidden="true" />

            <h2 className="cta-title">Ready to explore India?</h2>
            <p className="cta-sub">
              Join 10,000+ travellers who plan smarter with Yatrip. Free to sign up.
            </p>

            <div className="cta-btns">
              <Link to="/register" className="yt-btn yt-btn--primary yt-btn--lg">
                Get started free <Icon name="arrowRight" size={17} />
              </Link>
              <Link to="/hotels" className="yt-btn yt-btn--ghost yt-btn--lg">
                Browse hotels
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}