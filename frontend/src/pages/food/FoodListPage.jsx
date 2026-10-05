import { useState } from "react";
import { useNavigate } from "react-router-dom";
import useFood from "../../hooks/useFood";
import FoodCard from "../../components/food/FoodCard";
import useCurrentUser from "../../hooks/useCurrentUser";
import { FOOD_CATEGORIES, SORT_OPTIONS, PRICE_OPTIONS } from "../../utils/foodHelpers";
import "./FoodListPage.css";

export default function FoodListPage() {
  const {
    foods, total, totalPages, loading, error,
    filters, userLocation, locationStatus,
    sparse, importing, importMessage, runImport,
    requestLocation, clearLocation,
    setFilter, setDebouncedFilter, resetFilters,
    setPage, setCategory, retry,
  } = useFood();

  const [viewMode, setViewMode] = useState("grid");
  const [showFilters, setShowFilters] = useState(false);

  // The session lives in an HttpOnly cookie and the cached profile in
  // `authService`. Reading a localStorage 'access_token' here always returned
  // null, which hid the partner banner from everyone actually signed in.
  const { user, isOwner } = useCurrentUser();
  const isSignedIn = Boolean(user);
  const navigate = useNavigate();

  return (
    <div className="flp">
      {/* ══ HEADER ══ */}
      <div className="flp__header">
        <div className="flp__header-top">
          <div>
            <h1>🍴 Food & Restaurants</h1>
            <p>Street food, dhabas, cafés & more across India</p>
          </div>
          <button
            className={`flp__loc-btn flp__loc-btn--${locationStatus}`}
            onClick={locationStatus === "granted" ? clearLocation : requestLocation}
            disabled={locationStatus === "requesting"}
          >
            {locationStatus === "requesting" && <span className="flp__spinner" />}
            {locationStatus === "idle" && "📍 Use My Location"}
            {locationStatus === "requesting" && "Getting location..."}
            {locationStatus === "granted" && "📍 Location On · Off"}
            {locationStatus === "denied" && "🚫 Location Denied"}
          </button>
        </div>

        {/* Business Banner */}
        {isSignedIn && (
          <div className="flp__business-bar">
            <div className="flp__business-info">
              <span>🏢 {isOwner ? 'Business Account' : 'Partner with Yatrip'}</span>
              <p>{isOwner ? 'Manage your food outlets' : 'Want to list your restaurant? Join us'}</p>
            </div>
            <div className="flp__business-actions">
              {isOwner && (
                <button className="flp__biz-btn" onClick={() => navigate('/my-food-places')}>
                  My Outlets
                </button>
              )}
              <button className="flp__biz-btn primary" onClick={() => navigate('/register-food')}>
                {isOwner ? '+ Register Outlet' : 'List Your Restaurant'}
              </button>
            </div>
          </div>
        )}

        {/* ══ SEARCH ══ */}
        <div className="flp__search-row">
          <label className="flp__search-wrap">
            <span>🔍</span>
            <input
              type="text" placeholder="Search by name or cuisine..."
              defaultValue={filters.search}
              onChange={e => setDebouncedFilter("search", e.target.value)}
            />
          </label>
          <label className="flp__search-wrap">
            <span>📌</span>
            <input
              type="text" placeholder="Search by city or area..."
              defaultValue={filters.locationSearch}
              onChange={e => setDebouncedFilter("locationSearch", e.target.value)}
            />
          </label>
          <button
            className={`flp__filter-btn ${showFilters ? "active" : ""}`}
            onClick={() => setShowFilters(s => !s)}
          >
            🎛️ Filters {showFilters ? "▲" : "▼"}
          </button>
        </div>

        {/* ══ FILTER PANEL ══ */}
        {showFilters && (
          <div className="flp__filters">
            <div className="flp__fg">
              <label>Sort By</label>
              <select value={filters.sortBy} onChange={e => setFilter("sortBy", e.target.value)}>
                {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div className="flp__fg">
              <label>Price Range</label>
              <select value={filters.priceLevel} onChange={e => setFilter("priceLevel", e.target.value)}>
                {PRICE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div className="flp__fg">
              <label>Diet</label>
              <select value={filters.isVeg} onChange={e => setFilter("isVeg", e.target.value)}>
                <option value="">Any</option>
                <option value="true">🟢 Veg Only</option>
                <option value="false">🔴 Non-Veg</option>
              </select>
            </div>
            <div className="flp__fg">
              <label>Min Rating</label>
              <select value={filters.minRating} onChange={e => setFilter("minRating", e.target.value)}>
                <option value="">Any</option>
                <option value="3">3+ ⭐</option>
                <option value="4">4+ ⭐</option>
                <option value="4.5">4.5+ ⭐</option>
              </select>
            </div>
            <div className="flp__fg">
              <label>Delivery</label>
              <select value={filters.delivery} onChange={e => setFilter("delivery", e.target.value)}>
                <option value="">Any</option>
                <option value="true">🛵 Delivery Only</option>
              </select>
            </div>
            <button className="flp__clear-btn" onClick={resetFilters}>✕ Clear All</button>
          </div>
        )}

        {/* ══ CATEGORY PILLS ══ */}
        <div className="flp__cats">
          {FOOD_CATEGORIES.map(cat => (
            <button
              key={cat.key}
              className={`flp__cat-pill ${filters.category === cat.key ? "active" : ""}`}
              onClick={() => setCategory(cat.key)}
            >
              <span>{cat.icon}</span>
              <span>{cat.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* ══ TOOLBAR ══ */}
      <div className="flp__toolbar">
        <span className="flp__count">
          {loading ? "Loading..." : `${total.toLocaleString()} place${total !== 1 ? "s" : ""} found`}
          {userLocation && !loading && " · sorted by distance"}
        </span>
        <div className="flp__views">
          <button className={`flp__view-btn ${viewMode === "grid" ? "active" : ""}`} onClick={() => setViewMode("grid")}>⊞</button>
          <button className={`flp__view-btn ${viewMode === "list" ? "active" : ""}`} onClick={() => setViewMode("list")}>☰</button>
        </div>
      </div>

      {/* ══ ERROR ══ */}
      {error && (
        <div className="flp__error">
          ⚠️ {error}
          <button onClick={retry}>Retry</button>
        </div>
      )}

      {/* ══ COVERAGE / IMPORT ══
          A thin area used to trigger a blocking Overpass fetch on every browse
          request. Importing is now explicit and rate limited. */}
      {!loading && !error && sparse && (
        <div className="flp__coverage">
          <div>
            <strong>Not much here yet</strong>
            <p>
              {filters.locationSearch
                ? `We have little coverage for “${filters.locationSearch}”.`
                : "We have little coverage for this area."}{" "}
              Pull the latest places from OpenStreetMap?
            </p>
            {importMessage && <span className="flp__coverage-msg">{importMessage}</span>}
          </div>
          <div className="flp__coverage-actions">
            <button onClick={runImport} disabled={importing}>
              {importing ? "Importing…" : "Import this area"}
            </button>
            <button className="ghost" onClick={resetFilters}>Reset filters</button>
          </div>
        </div>
      )}

      {/* ══ GRID/LIST ══ */}
      {!loading && !error && foods.length === 0 ? (
        <div className="flp__empty">
          <span>🍽️</span>
          <h3>No food places found</h3>
          <p>
            {filters.locationSearch
              ? `Nothing matches “${filters.locationSearch}” yet. Try importing the area.`
              : "Try a different search, category, or location"}
          </p>
          <div className="flp__empty-actions">
            <button onClick={runImport} disabled={importing}>
              {importing ? "Importing…" : "Import this area"}
            </button>
            <button className="ghost" onClick={resetFilters}>Reset Filters</button>
          </div>
        </div>
      ) : (
        <div className={`flp__grid flp__grid--${viewMode}`}>
          {loading
            ? Array.from({ length: 12 }).map((_, i) => <div key={i} className="fc-skeleton" />)
            : foods.map(f => <FoodCard key={f.id} place={f} variant={viewMode} />)
          }
        </div>
      )}

      {/* ══ PAGINATION ══ */}
      {!loading && totalPages > 1 && (
        <div className="flp__pagination">
          <button disabled={filters.page <= 1} onClick={() => setPage(filters.page - 1)}>← Prev</button>
          <div className="flp__page-nums">
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              const n = Math.max(1, filters.page - 2) + i;
              if (n > totalPages) return null;
              return (
                <button key={n} className={filters.page === n ? "active" : ""} onClick={() => setPage(n)}>{n}</button>
              );
            })}
          </div>
          <button disabled={filters.page >= totalPages} onClick={() => setPage(filters.page + 1)}>Next →</button>
        </div>
      )}
    </div>
  );
}