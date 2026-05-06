import { useState } from "react";
import { useNavigate } from "react-router-dom";
import useAttractions from "../../hooks/useAttractions";
import AttractionCard from "../../components/attractions/AttractionCard";
import CategoryFilter from "../../components/attractions/CategoryFilter";
import { SORT_OPTIONS, RATING_OPTIONS, FEE_OPTIONS } from "../../utils/attractionHelpers";
import "./AttractionsListPage.css";

export default function AttractionsListPage() {
  const {
    attractions, total, totalPages, loading, error,
    filters, userLocation, locationStatus,
    requestLocation, clearLocation,
    setFilter, setDebouncedFilter, resetFilters,
    setPage, setCategory, retry,
  } = useAttractions();

  const [viewMode, setViewMode] = useState("grid"); // grid | list
  const [showFilters, setShowFilters] = useState(false);

  const token = localStorage.getItem('access_token');
  const userStr = localStorage.getItem('user');
  const user = userStr ? JSON.parse(userStr) : null;
  const isBusiness = user?.is_business || user?.user_type === 'business' || user?.is_owner;
  const navigate = useNavigate();

  // Category counts from data (approximate)
  const categoryCounts = {};

  return (
    <div className="alp">
      {/* ══ HERO HEADER ══ */}
      <div className="alp__header">
        <div className="alp__header-inner">
          <div className="alp__header-text">
            <h1>🗺️ Explore Attractions</h1>
            <p>Discover monuments, temples, parks & more across India</p>
          </div>

          {/* Location Button */}
          <button
            className={`alp__loc-btn alp__loc-btn--${locationStatus}`}
            onClick={locationStatus === "granted" ? clearLocation : requestLocation}
            disabled={locationStatus === "requesting"}
          >
            {locationStatus === "requesting" && <span className="alp__loc-spinner" />}
            {locationStatus === "idle" && "📍 Use My Location"}
            {locationStatus === "requesting" && "Getting location..."}
            {locationStatus === "granted" && "📍 Location On · Turn Off"}
            {locationStatus === "denied" && "🚫 Location Denied"}
          </button>
        </div>

        {/* Business Banner */}
        {token && (
          <div className="alp__business-bar">
            <div className="alp__business-info">
              <span>🏛️ {isBusiness ? 'Business Account' : 'Partner with Yatrip'}</span>
              <p>{isBusiness ? 'Manage your attractions' : 'Found a great place? Add it to Yatrip'}</p>
            </div>
            <div className="alp__business-actions">
              {isBusiness && (
                <button className="alp__biz-btn" onClick={() => navigate('/my-attractions')}>
                  My Places
                </button>
              )}
              <button className="alp__biz-btn primary" onClick={() => navigate('/register-attraction')}>
                {isBusiness ? '+ Register Attraction' : 'Add Attraction'}
              </button>
            </div>
          </div>
        )}

        {/* ══ SEARCH BAR ══ */}
        <div className="alp__search-row">
          <label className="alp__search-wrap">
            <span className="alp__search-icon">🔍</span>
            <input
              type="text"
              placeholder="Search attractions by name..."
              className="alp__search-input"
              defaultValue={filters.search}
              onChange={(e) => setDebouncedFilter("search", e.target.value)}
            />
          </label>
          <label className="alp__search-wrap">
            <span className="alp__search-icon">📌</span>
            <input
              type="text"
              placeholder="Search by city or place..."
              className="alp__search-input"
              defaultValue={filters.locationSearch}
              onChange={(e) => setDebouncedFilter("locationSearch", e.target.value)}
            />
          </label>
          <button
            className={`alp__filter-btn ${showFilters ? "active" : ""}`}
            onClick={() => setShowFilters((s) => !s)}
          >
            🎛️ Filters {showFilters ? "▲" : "▼"}
          </button>
        </div>

        {/* ══ ADVANCED FILTERS ══ */}
        {showFilters && (
          <div className="alp__filters-panel">
            <div className="alp__filter-group">
              <label>Sort By</label>
              <select value={filters.sortBy} onChange={(e) => setFilter("sortBy", e.target.value)}>
                {SORT_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div className="alp__filter-group">
              <label>Min Rating</label>
              <select value={filters.minRating} onChange={(e) => setFilter("minRating", e.target.value)}>
                {RATING_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div className="alp__filter-group">
              <label>Entry Type</label>
              <select value={filters.isFree} onChange={(e) => setFilter("isFree", e.target.value)}>
                {FEE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <button className="alp__clear-btn" onClick={resetFilters}>
              ✕ Clear All
            </button>
          </div>
        )}

        {/* ══ CATEGORY PILLS ══ */}
        <CategoryFilter
          activeCategory={filters.category}
          onChange={setCategory}
          categoryCounts={categoryCounts}
        />
      </div>

      {/* ══ TOOLBAR ══ */}
      <div className="alp__toolbar">
        <span className="alp__count">
          {loading ? "Loading..." : `${total.toLocaleString()} attraction${total !== 1 ? "s" : ""} found`}
          {userLocation && !loading && " · sorted by distance"}
        </span>
        <div className="alp__view-btns">
          <button
            className={`alp__view-btn ${viewMode === "grid" ? "active" : ""}`}
            onClick={() => setViewMode("grid")}
            title="Grid view"
          >⊞</button>
          <button
            className={`alp__view-btn ${viewMode === "list" ? "active" : ""}`}
            onClick={() => setViewMode("list")}
            title="List view"
          >☰</button>
        </div>
      </div>

      {/* ══ ERROR ══ */}
      {error && (
        <div className="alp__error">
          <span>⚠️ {error}</span>
          <button onClick={retry}>Retry</button>
        </div>
      )}

      {/* ══ GRID / LIST ══ */}
      {!loading && !error && attractions.length === 0 ? (
        <div className="alp__empty">
          <div className="alp__empty-icon">🏔️</div>
          <h3>No attractions found</h3>
          <p>Try a different search, category, or location</p>
          <button className="alp__empty-reset" onClick={resetFilters}>Reset Filters</button>
        </div>
      ) : (
        <div className={`alp__grid alp__grid--${viewMode}`}>
          {loading
            ? Array.from({ length: 12 }).map((_, i) => (
              <div key={i} className="attraction-card-skeleton" />
            ))
            : attractions.map((a) => (
              <AttractionCard key={a.id} attraction={a} variant={viewMode} />
            ))
          }
        </div>
      )}

      {/* ══ PAGINATION ══ */}
      {!loading && totalPages > 1 && (
        <div className="alp__pagination">
          <button
            className="alp__page-btn"
            disabled={filters.page <= 1}
            onClick={() => setPage(filters.page - 1)}
          >
            ← Prev
          </button>
          <div className="alp__page-numbers">
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              const pageNum = Math.max(1, filters.page - 2) + i;
              if (pageNum > totalPages) return null;
              return (
                <button
                  key={pageNum}
                  className={`alp__page-num ${filters.page === pageNum ? "active" : ""}`}
                  onClick={() => setPage(pageNum)}
                >
                  {pageNum}
                </button>
              );
            })}
          </div>
          <button
            className="alp__page-btn"
            disabled={filters.page >= totalPages}
            onClick={() => setPage(filters.page + 1)}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}