import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import "./Home.css";

// ── Data ─────────────────────────────────────────────────────────
const CATEGORIES = [
  { icon: "🏨", label: "Hotels",      sub: "500+ properties",  path: "/hotels",      color: "#FF6B35" },
  { icon: "🗺️", label: "Attractions", sub: "200+ places",      path: "/attractions", color: "#4ECDC4" },
  { icon: "🍽️", label: "Food",        sub: "300+ restaurants", path: "/food",        color: "#FFE66D" },
  { icon: "🚌", label: "Transport",   sub: "Easy commute",     path: "/transport",   color: "#7C5CBF" },
  { icon: "🚗", label: "Rentals",     sub: "Cars & bikes",     path: "/rentals",     color: "#06D6A0" },
  { icon: "🤖", label: "AI Chatbot",  sub: "Plan your trip",   path: "/chatbot",     color: "#FF6B8A" },
];

const DESTINATIONS = [
  { name: "Rajasthan",  tag: "Royal Heritage",   emoji: "🏯", trips: "2.4k trips" },
  { name: "Kerala",     tag: "God's Own Country", emoji: "🌴", trips: "3.1k trips" },
  { name: "Goa",        tag: "Sun & Surf",        emoji: "🏖️", trips: "5.2k trips" },
  { name: "Himachal",   tag: "Mountain Escape",   emoji: "🏔️", trips: "1.8k trips" },
  { name: "Varanasi",   tag: "Spiritual Journey", emoji: "🪔", trips: "1.2k trips" },
  { name: "Ladakh",     tag: "Wild Frontier",     emoji: "🦅", trips: "900 trips"  },
];

const STEPS = [
  { icon: "🔍", title: "Search",  desc: "Find hotels, food spots, attractions & transport across India." },
  { icon: "📅", title: "Book",    desc: "Instant booking with secure payment & instant confirmation." },
  { icon: "✈️", title: "Travel",  desc: "Pack your bags & enjoy a seamless travel experience." },
  { icon: "⭐", title: "Review",  desc: "Share your experience & help other travelers discover gems." },
];

const REVIEWS = [
  { name: "Priya S.",   city: "Mumbai",    stars: 5, text: "Found an amazing heritage hotel in Jaipur through Yatrip. The booking was super smooth!" },
  { name: "Rahul M.",   city: "Delhi",     stars: 5, text: "The AI chatbot helped me plan my entire Kerala trip in minutes. Absolutely loved it." },
  { name: "Ananya K.",  city: "Bangalore", stars: 5, text: "Rented a bike through Yatrip and explored Goa on my own terms. 10/10 experience." },
  { name: "Vikram T.",  city: "Chennai",   stars: 5, text: "Best food recommendations in Varanasi. Found spots I would never have discovered alone." },
];

// ── Counter hook ─────────────────────────────────────────────────
function useCounter(target, duration = 1500, start = false) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!start) return;
    let startTime = null;
    const step = (timestamp) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      setCount(Math.floor(progress * target));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [start, target, duration]);
  return count;
}

// ── Stats component ───────────────────────────────────────────────
function StatCounter({ target, suffix, label, started }) {
  const count = useCounter(target, 1800, started);
  return (
    <div className="stat-box">
      <span className="stat-big">{count}{suffix}</span>
      <span className="stat-lbl">{label}</span>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────
export default function Home() {
  const [query, setQuery]         = useState("");
  const [statsVisible, setStats]  = useState(false);
  const [activeTab, setActiveTab] = useState("Hotels");
  const statsRef = useRef(null);

  // Intersection Observer for stats
  useEffect(() => {
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setStats(true); },
      { threshold: 0.3 }
    );
    if (statsRef.current) obs.observe(statsRef.current);
    return () => obs.disconnect();
  }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    if (query.trim()) window.location.href = `/hotels?search=${query}`;
  };

  return (
    <div className="home">

      {/* ══ HERO ═══════════════════════════════════════════════ */}
      <section className="hero">
        {/* Animated BG */}
        <div className="hero-bg">
          <div className="hero-orb orb-1" />
          <div className="hero-orb orb-2" />
          <div className="hero-orb orb-3" />
          <div className="hero-grid" />
        </div>

        <div className="hero-content">
          <div className="hero-badge">
            <span className="badge-dot" />
            Trusted by 10,000+ travelers across India
          </div>

          <h1 className="hero-title">
            Explore India<br />
            <span className="hero-title-gradient">Your Way</span>
          </h1>

          <p className="hero-subtitle">
            Hotels, food, attractions, transport & rentals — everything you need
            for the perfect Indian adventure, in one place.
          </p>

          {/* Search bar */}
          <form className="hero-search" onSubmit={handleSearch}>
            <div className="search-tabs">
              {["Hotels", "Food", "Attractions"].map((t) => (
                <button
                  key={t}
                  type="button"
                  className={`search-tab ${activeTab === t ? "search-tab--active" : ""}`}
                  onClick={() => setActiveTab(t)}
                >
                  {t}
                </button>
              ))}
            </div>
            <div className="search-bar">
              <span className="search-icon">🔍</span>
              <input
                type="text"
                placeholder={`Search ${activeTab.toLowerCase()} in any city...`}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="search-input"
              />
              <button type="submit" className="search-btn">
                Search
              </button>
            </div>
          </form>

          {/* Quick tags */}
          <div className="hero-tags">
            {["🏯 Jaipur", "🌴 Kerala", "🏖️ Goa", "🏔️ Manali", "🪔 Varanasi"].map((t) => (
              <button key={t} className="hero-tag" onClick={() => setQuery(t.split(" ")[1])}>
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Scroll cue */}
        <div className="scroll-cue">
          <span>Scroll to explore</span>
          <div className="scroll-arrow" />
        </div>
      </section>

      {/* ══ STATS ══════════════════════════════════════════════ */}
      <section className="stats-section" ref={statsRef}>
        <div className="stats-inner">
          <StatCounter target={500}  suffix="+"  label="Destinations"     started={statsVisible} />
          <div className="stats-divider" />
          <StatCounter target={10000} suffix="+"  label="Happy Travelers"  started={statsVisible} />
          <div className="stats-divider" />
          <StatCounter target={1200}  suffix="+"  label="Hotels Listed"    started={statsVisible} />
          <div className="stats-divider" />
          <StatCounter target={4}     suffix=".9★" label="Average Rating"  started={statsVisible} />
        </div>
      </section>

      {/* ══ CATEGORIES ═════════════════════════════════════════ */}
      <section className="section categories-section">
        <div className="section-inner">
          <div className="section-header">
            <span className="section-tag">Everything in one place</span>
            <h2 className="section-title">What are you looking for?</h2>
            <p className="section-sub">From luxury hotels to street food — Yatrip has it all.</p>
          </div>
          <div className="categories-grid">
            {CATEGORIES.map((cat, i) => (
              <Link
                key={cat.label}
                to={cat.path}
                className="cat-card"
                style={{
                  borderColor: `${cat.color}30`,
                  animationDelay: `${i * 0.08}s`
                }}
                onMouseEnter={e => e.currentTarget.style.borderColor = cat.color}
                onMouseLeave={e => e.currentTarget.style.borderColor = `${cat.color}30`}
                >
                <div className="cat-icon-wrap" style={{ background: `${cat.color}18` }}>
                  <span className="cat-icon">{cat.icon}</span>
                </div>
                <h3 className="cat-label">{cat.label}</h3>
                <p className="cat-sub">{cat.sub}</p>
                <span className="cat-arrow" style={{ color: cat.color }}>→</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ══ DESTINATIONS ═══════════════════════════════════════ */}
      <section className="section destinations-section">
        <div className="section-inner">
          <div className="section-header">
            <span className="section-tag">Popular picks</span>
            <h2 className="section-title">Top Destinations</h2>
            <p className="section-sub">India's most loved travel spots, waiting to be explored.</p>
          </div>
          <div className="dest-grid">
            {DESTINATIONS.map((d, i) => (
              <Link
                key={d.name}
                to={`/hotels?city=${d.name}`}
                className={`dest-card dest-card--${i}`}
              >
                <div className="dest-emoji">{d.emoji}</div>
                <div className="dest-info">
                  <h3 className="dest-name">{d.name}</h3>
                  <p className="dest-tag">{d.tag}</p>
                  <p className="dest-trips">✈ {d.trips}</p>
                </div>
                <div className="dest-overlay" />
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ══ HOW IT WORKS ═══════════════════════════════════════ */}
      <section className="section how-section">
        <div className="section-inner">
          <div className="section-header">
            <span className="section-tag">Simple & fast</span>
            <h2 className="section-title">How Yatrip Works</h2>
          </div>
          <div className="steps-grid">
            {STEPS.map((s, i) => (
              <div key={s.title} className="step-card" style={{ animationDelay: `${i * 0.1}s` }}>
                <div className="step-num">{String(i + 1).padStart(2, "0")}</div>
                <div className="step-icon">{s.icon}</div>
                <h3 className="step-title">{s.title}</h3>
                <p className="step-desc">{s.desc}</p>
                {i < STEPS.length - 1 && <div className="step-connector" />}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══ AI CHATBOT CTA ══════════════════════════════════════ */}
      <section className="section chatbot-section">
        <div className="chatbot-card">
          <div className="chatbot-left">
            <span className="chatbot-badge">✨ AI Powered</span>
            <h2 className="chatbot-title">
              Plan Your Trip with<br />
              <span>AI Assistant</span>
            </h2>
            <p className="chatbot-desc">
              Tell our AI where you want to go and your budget — it'll build
              a complete itinerary with hotels, food spots & attractions instantly.
            </p>
            <Link to="/chatbot" className="chatbot-btn">
              Start Planning Free <span>→</span>
            </Link>
          </div>
          <div className="chatbot-right">
            <div className="chat-bubble chat-bubble--user">
              Hey! Plan a 3-day trip to Goa under ₹15,000 🌊
            </div>
            <div className="chat-bubble chat-bubble--bot">
              <span className="bot-badge">🤖 Yatrip AI</span>
              Sure! Here's your personalized Goa itinerary with budget hotels,
              beach shacks & hidden spots...
            </div>
            <div className="chat-bubble chat-bubble--user">
              This is perfect! Book Day 1 hotels 🏨
            </div>
          </div>
        </div>
      </section>

      {/* ══ REVIEWS ════════════════════════════════════════════ */}
      <section className="section reviews-section">
        <div className="section-inner">
          <div className="section-header">
            <span className="section-tag">Real experiences</span>
            <h2 className="section-title">What Travelers Say</h2>
          </div>
          <div className="reviews-grid">
            {REVIEWS.map((r, i) => (
              <div key={r.name} className="review-card" style={{ animationDelay: `${i * 0.1}s` }}>
                <div className="review-stars">{"★".repeat(r.stars)}</div>
                <p className="review-text">"{r.text}"</p>
                <div className="review-author">
                  <div className="review-avatar">{r.name[0]}</div>
                  <div>
                    <p className="review-name">{r.name}</p>
                    <p className="review-city">📍 {r.city}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══ FINAL CTA ══════════════════════════════════════════ */}
      <section className="section cta-section">
        <div className="cta-card">
          <div className="cta-orb cta-orb-1" />
          <div className="cta-orb cta-orb-2" />
          <h2 className="cta-title">Ready to Explore India?</h2>
          <p className="cta-sub">
            Join 10,000+ travelers who plan smarter with Yatrip.
          </p>
          <div className="cta-btns">
            <Link to="/register" className="cta-btn-primary">Get Started Free →</Link>
            <Link to="/hotels"   className="cta-btn-ghost">Browse Hotels</Link>
          </div>
        </div>
      </section>

    </div>
  );
}
