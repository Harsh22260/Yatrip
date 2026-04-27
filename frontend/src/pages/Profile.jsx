import { useState, useEffect } from "react";
import { getUserProfile, getOwnerProfile, logout } from "../services/authService";
import "bootstrap/dist/css/bootstrap.min.css";
import "../styles/auth.css";

export default function Profile() {
  const [user, setUser] = useState(null);
  const [owner, setOwner] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const u = await getUserProfile();
        setUser(u);
        if (u.is_owner) {
          try {
            const o = await getOwnerProfile();
            setOwner(o);
          } catch (_) {}
        }
      } catch (e) {
        setError("Failed to load profile. Please login again.");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) return (
    <div className="auth-root">
      <div className="blob blob-1" /><div className="blob blob-2" />
      <div className="profile-loader">
        <span className="spin-icon">✈</span>
        <p>Loading your profile...</p>
      </div>
    </div>
  );

  if (error) return (
    <div className="auth-root">
      <div className="auth-card">
        <div className="auth-error"><span>⚠</span> {error}</div>
        <a href="/login" className="auth-btn" style={{ textDecoration: "none", display: "block", textAlign: "center", marginTop: 16 }}>
          Go to Login
        </a>
      </div>
    </div>
  );

  return (
    <div className="auth-root profile-root">
      <div className="blob blob-1" /><div className="blob blob-2" /><div className="blob blob-3" />

      <div className="profile-card">
        {/* Header */}
        <div className="profile-header">
          <div className="profile-avatar">
            {user.username?.[0]?.toUpperCase() || "U"}
          </div>
          <div className="profile-header-info">
            <h2 className="profile-name">{user.username}</h2>
            <p className="profile-email">{user.email}</p>
            <div className="badge-row">
              {user.is_verified && (
                <span className="badge badge-verified">✓ Verified</span>
              )}
              {user.is_owner && (
                <span className="badge badge-owner">🏢 Business Owner</span>
              )}
              {!user.is_owner && (
                <span className="badge badge-traveler">✈ Traveler</span>
              )}
            </div>
          </div>
          <button className="logout-btn" onClick={logout} title="Logout">
            🚪 Logout
          </button>
        </div>

        {/* Info grid */}
        <div className="profile-section">
          <h3 className="section-title">Account Information</h3>
          <div className="info-grid">
            <div className="info-item">
              <span className="info-icon">✉</span>
              <div>
                <p className="info-label">Email</p>
                <p className="info-value">{user.email}</p>
              </div>
            </div>
            <div className="info-item">
              <span className="info-icon">👤</span>
              <div>
                <p className="info-label">Username</p>
                <p className="info-value">{user.username}</p>
              </div>
            </div>
            <div className="info-item">
              <span className="info-icon">📱</span>
              <div>
                <p className="info-label">Phone</p>
                <p className="info-value">{user.phone || "Not added"}</p>
              </div>
            </div>
            <div className="info-item">
              <span className="info-icon">🛡</span>
              <div>
                <p className="info-label">Account Status</p>
                <p className="info-value">
                  {user.is_verified ? "Verified ✓" : "Not Verified"}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Owner section */}
        {user.is_owner && owner && (
          <div className="profile-section owner-section">
            <h3 className="section-title">Business Profile</h3>
            <div className={`approval-banner ${owner.is_approved ? "approved" : "pending"}`}>
              {owner.is_approved
                ? "✅ Business Approved — You can list your services"
                : "⏳ Approval Pending — Our team will review your business soon"}
            </div>
            <div className="info-grid">
              <div className="info-item">
                <span className="info-icon">🏢</span>
                <div>
                  <p className="info-label">Business Name</p>
                  <p className="info-value">{owner.business_name}</p>
                </div>
              </div>
              <div className="info-item">
                <span className="info-icon">🏷</span>
                <div>
                  <p className="info-label">Business Type</p>
                  <p className="info-value" style={{ textTransform: "capitalize" }}>
                    {owner.business_type}
                  </p>
                </div>
              </div>
              <div className="info-item">
                <span className="info-icon">📞</span>
                <div>
                  <p className="info-label">Contact</p>
                  <p className="info-value">{owner.contact_number}</p>
                </div>
              </div>
              <div className="info-item">
                <span className="info-icon">📍</span>
                <div>
                  <p className="info-label">Address</p>
                  <p className="info-value">{owner.address}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Quick actions */}
        <div className="profile-section">
          <h3 className="section-title">Quick Actions</h3>
          <div className="quick-actions">
            <a href="/bookings" className="action-card">
              <span className="action-icon">🏨</span>
              <span>My Bookings</span>
            </a>
            <a href="/attractions" className="action-card">
              <span className="action-icon">🗺</span>
              <span>Explore</span>
            </a>
            <a href="/reviews" className="action-card">
              <span className="action-icon">⭐</span>
              <span>My Reviews</span>
            </a>
            {user.is_owner && (
              <a href="/dashboard" className="action-card action-card-owner">
                <span className="action-icon">📊</span>
                <span>Dashboard</span>
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
