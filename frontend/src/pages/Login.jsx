import { useState } from "react";
import { loginUser } from "../services/authService";
import "bootstrap/dist/css/bootstrap.min.css";
import "../styles/auth.css";

export default function Login() {
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPass, setShowPass] = useState(false);

  const handleChange = (e) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await loginUser(form.email, form.password);
      window.location.href = "/";
    } catch (err) {
      setError(err?.detail || "Invalid email or password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-root">
      {/* Background blobs */}
      <div className="blob blob-1" />
      <div className="blob blob-2" />
      <div className="blob blob-3" />

      <div className="auth-card">
        {/* Logo / Brand */}
        <div className="auth-brand">
          <span className="brand-icon">✈</span>
          <span className="brand-name">Yatrip</span>
        </div>

        <h2 className="auth-title">Welcome back!</h2>
        <p className="auth-subtitle">Sign in to continue your journey</p>

        {error && (
          <div className="auth-error">
            <span>⚠</span> {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          {/* Email */}
          <div className="field-group">
            <label className="field-label">Email address</label>
            <div className="field-wrap">
              <span className="field-icon">✉</span>
              <input
                type="email"
                name="email"
                value={form.email}
                onChange={handleChange}
                placeholder="you@example.com"
                required
                className="field-input"
              />
            </div>
          </div>

          {/* Password */}
          <div className="field-group">
            <label className="field-label">Password</label>
            <div className="field-wrap">
              <span className="field-icon">🔒</span>
              <input
                type={showPass ? "text" : "password"}
                name="password"
                value={form.password}
                onChange={handleChange}
                placeholder="Enter your password"
                required
                className="field-input"
              />
              <button
                type="button"
                className="eye-btn"
                onClick={() => setShowPass(!showPass)}
              >
                {showPass ? "🙈" : "👁"}
              </button>
            </div>
          </div>

          <div className="forgot-row">
            <a href="/forgot-password" className="forgot-link">
              Forgot password?
            </a>
          </div>

          <button type="submit" className="auth-btn" disabled={loading}>
            {loading ? (
              <span className="btn-loader" />
            ) : (
              <>Sign In <span className="btn-arrow">→</span></>
            )}
          </button>
        </form>

        <p className="auth-switch">
          New to Yatrip?{" "}
          <a href="/register" className="auth-link">
            Create account
          </a>
        </p>
      </div>
    </div>
  );
}
