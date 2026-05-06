import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useHotels } from "../../hooks/useHotels";
import HotelCard from "../../components/hotels/HotelCard";
import "./HotelsListPage.css";

const HotelsListPage = () => {
  const { hotels, loading, error, refetch } = useHotels();
  const [search, setSearch] = useState('');
  const navigate = useNavigate();

  const token = localStorage.getItem('access_token');
  const userStr = localStorage.getItem('user');
  const user = userStr ? JSON.parse(userStr) : null;
  const isBusiness = user?.is_business || user?.user_type === 'business';

  const filtered = Array.isArray(hotels) ? hotels.filter((h) =>
    h.name.toLowerCase().includes(search.toLowerCase()) ||
    h.address.toLowerCase().includes(search.toLowerCase())
  ) : [];

  return (
    <div className="hlp-page">
      <header className="hlp-header">
        <h1 className="hlp-title">Find Your Stay</h1>
        <p className="hlp-sub">Handpicked hotels, verified & ready</p>
        <div className="hlp-search-wrap">
          <input
            className="hlp-search"
            type="text"
            placeholder="Search by name or city..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <span className="hlp-search-icon">🔍</span>
        </div>
      </header>

      {/* Business Banner */}
      {token && (
        <div className="hlp-business-bar">
          <div className="hlp-business-info">
            <span>🏢 {isBusiness ? 'Business Account' : 'Partner with Yatrip'}</span>
            <p>{isBusiness ? 'Manage your properties' : 'Want to list your hotel? Start here'}</p>
          </div>
          <div className="hlp-business-actions">
            {isBusiness && (
              <button className="hlp-biz-btn" onClick={() => navigate('/my-hotels')}>
                My Hotels
              </button>
            )}
            <button className="hlp-biz-btn primary" onClick={() => navigate('/register-hotel')}>
              {isBusiness ? '+ Register Hotel' : 'List Your Hotel'}
            </button>
          </div>
        </div>
      )}

      {/* Login prompt agar login nahi kiya */}
      {!token && (
        <div className="hlp-login-bar">
          <span>🔐 Login to book hotels or register your property</span>
          <button className="hlp-login-btn" onClick={() => navigate('/login')}>Login</button>
        </div>
      )}

      <main className="hlp-main">
        {loading && (
          <div className="hlp-loading">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="hlp-skeleton" />
            ))}
          </div>
        )}

        {error && (
          <div className="hlp-error">
            <p>⚠ {error}</p>
            <button onClick={refetch}>Retry</button>
          </div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div className="hlp-empty">
            <p>No hotels found{search ? ` for "${search}"` : ''}.</p>
          </div>
        )}

        {!loading && !error && (
          <div className="hlp-grid">
            {filtered.map((hotel) => (
              <HotelCard
                key={hotel.id}
                hotel={hotel}
                onSelect={(h) => navigate(`/hotels/${h.id}`)}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default HotelsListPage;