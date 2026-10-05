import { useState } from "react";
import { registerUser } from "../services/authService";
import "bootstrap/dist/css/bootstrap.min.css";
import "../styles/auth.css";

const STEPS = ["Account", "Details", "Done"];

export default function Register() {
  const [step, setStep] = useState(0);
  const [form, setForm] = useState({
    email: "",
    username: "",
    password: "",
    confirmPassword: "",
    phone: "",
    is_owner: false,
    // owner fields - `business_address` is the name the API expects,
    // not `address`, so a mismatch here silently dropped the value.
    business_name: "",
    business_type: "hotel",
    business_address: "",
    contact_number: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPass, setShowPass] = useState(false);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm({ ...form, [name]: type === "checkbox" ? checked : value });
  };

  const validateStep0 = () => {
    if (!form.email || !form.username || !form.password || !form.confirmPassword)
      return "Please fill all required fields.";
    if (form.password !== form.confirmPassword)
      return "Passwords do not match.";
    // Keep in step with the backend: min_length=8 on the serializer plus
    // Django's AUTH_PASSWORD_VALIDATORS. The old "at least 6 characters"
    // message let people fill the form and then fail server-side.
    if (form.password.length < 8)
      return "Password must be at least 8 characters.";
    return null;
  };

  const validateStep1 = () => {
    if (!form.phone.trim()) return "Please enter your phone number.";
    if (form.is_owner) {
      if (!form.business_name.trim()) return "Business name is required.";
      if (!form.business_address.trim()) return "Business address is required.";
      if (!form.contact_number.trim()) return "Contact number is required.";
    }
    return null;
  };

  const nextStep = () => {
    if (step === 0) {
      const err = validateStep0();
      if (err) { setError(err); return; }
    }
    if (step === 1) {
      const err = validateStep1();
      if (err) { setError(err); return; }
    }
    setError("");
    setStep((s) => s + 1);
  };

  const handleSubmit = async () => {
    const stepError = validateStep1();
    if (stepError) { setError(stepError); return; }

    setError("");
    setLoading(true);
    try {
      const payload = {
        email: form.email.trim(),
        username: form.username.trim(),
        password: form.password,
        phone: form.phone.trim(),
        is_owner: form.is_owner,
      };
      // The owner fields were collected by the form but never sent, so the
      // backend created a user with no OwnerProfile and the owner page 500'd.
      if (form.is_owner) {
        payload.business_name = form.business_name.trim();
        payload.business_type = form.business_type;
        payload.business_address = form.business_address.trim();
        payload.contact_number = form.contact_number.trim();
      }
      await registerUser(payload);
      setStep(2); // Done step
    } catch (err) {
      // api.js throws an Error carrying a readable message built from the
      // DRF body; the old Object.values(err) walk printed raw JSON.
      setError(err?.message || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-root">
      <div className="blob blob-1" />
      <div className="blob blob-2" />
      <div className="blob blob-3" />

      <div className="auth-card register-card">
        {/* Brand */}
        <div className="auth-brand">
          <span className="brand-icon">✈</span>
          <span className="brand-name">Yatrip</span>
        </div>

        {/* Stepper */}
        <div className="stepper">
          {STEPS.map((label, i) => (
            <div key={i} className={`step ${i <= step ? "step-active" : ""}`}>
              <div className="step-dot">{i < step ? "✓" : i + 1}</div>
              <span className="step-label">{label}</span>
              {i < STEPS.length - 1 && <div className="step-line" />}
            </div>
          ))}
        </div>

        {error && (
          <div className="auth-error">
            <span>⚠</span> {error}
          </div>
        )}

        {/* Step 0 — Account */}
        {step === 0 && (
          <div className="auth-form">
            <h2 className="auth-title">Create Account</h2>
            <p className="auth-subtitle">Start your journey with Yatrip</p>

            <div className="field-group">
              <label className="field-label">Email address *</label>
              <div className="field-wrap">
                <span className="field-icon">✉</span>
                <input type="email" name="email" value={form.email}
                  onChange={handleChange} placeholder="you@example.com"
                  required className="field-input" />
              </div>
            </div>

            <div className="field-group">
              <label className="field-label">Username *</label>
              <div className="field-wrap">
                <span className="field-icon">👤</span>
                <input type="text" name="username" value={form.username}
                  onChange={handleChange} placeholder="Choose a username"
                  required className="field-input" />
              </div>
            </div>

            <div className="field-group">
              <label className="field-label">Password *</label>
              <div className="field-wrap">
                <span className="field-icon">🔒</span>
                <input type={showPass ? "text" : "password"} name="password"
                  value={form.password} onChange={handleChange}
                  placeholder="Min 8 characters" required className="field-input" />
                <button type="button" className="eye-btn"
                  onClick={() => setShowPass(!showPass)}>
                  {showPass ? "🙈" : "👁"}
                </button>
              </div>
            </div>

            <div className="field-group">
              <label className="field-label">Confirm Password *</label>
              <div className="field-wrap">
                <span className="field-icon">🔒</span>
                <input type={showPass ? "text" : "password"} name="confirmPassword"
                  value={form.confirmPassword} onChange={handleChange}
                  placeholder="Re-enter password" required className="field-input" />
              </div>
            </div>

            {/* Owner toggle */}
            <div className="owner-toggle">
              <label className="toggle-label">
                <input type="checkbox" name="is_owner" checked={form.is_owner}
                  onChange={handleChange} className="toggle-input" />
                <span className="toggle-track">
                  <span className="toggle-thumb" />
                </span>
                <span className="toggle-text">
                  Register as Business Owner
                </span>
              </label>
              {form.is_owner && (
                <p className="toggle-hint">
                  🏢 You can list hotels, food places & rentals
                </p>
              )}
            </div>

            <button type="button" className="auth-btn" onClick={nextStep}>
              Continue <span className="btn-arrow">→</span>
            </button>
          </div>
        )}

        {/* Step 1 — Details */}
        {step === 1 && (
          <div className="auth-form">
            <h2 className="auth-title">Personal Details</h2>
            <p className="auth-subtitle">A little more about you</p>

            <div className="field-group">
              <label className="field-label">Phone number</label>
              <div className="field-wrap">
                <span className="field-icon">📱</span>
                <input type="tel" name="phone" value={form.phone}
                  onChange={handleChange} placeholder="+91 XXXXX XXXXX"
                  className="field-input" />
              </div>
            </div>

            {form.is_owner && (
              <>
                <div className="owner-section-label">Business Details</div>

                <div className="field-group">
                  <label className="field-label">Business Name *</label>
                  <div className="field-wrap">
                    <span className="field-icon">🏢</span>
                    <input type="text" name="business_name" value={form.business_name}
                      onChange={handleChange} placeholder="Your business name"
                      className="field-input" />
                  </div>
                </div>

                <div className="field-group">
                  <label className="field-label">Business Type *</label>
                  <div className="field-wrap">
                    <span className="field-icon">🏷</span>
                    <select name="business_type" value={form.business_type}
                      onChange={handleChange} className="field-input field-select">
                      <option value="hotel">Hotel</option>
                      <option value="food">Food / Restaurant</option>
                      <option value="rental">Rental</option>
                    </select>
                  </div>
                </div>

                <div className="field-group">
                  <label className="field-label">Address *</label>
                  <div className="field-wrap">
                    <span className="field-icon">📍</span>
                    <textarea name="business_address" value={form.business_address}
                      onChange={handleChange} placeholder="Business address"
                      className="field-input field-textarea" rows={2} />
                  </div>
                </div>

                <div className="field-group">
                  <label className="field-label">Contact Number *</label>
                  <div className="field-wrap">
                    <span className="field-icon">📞</span>
                    <input type="tel" name="contact_number" value={form.contact_number}
                      onChange={handleChange} placeholder="Business contact"
                      className="field-input" />
                  </div>
                </div>
              </>
            )}

            <div className="btn-row">
              <button type="button" className="auth-btn-outline"
                onClick={() => setStep(0)}>
                ← Back
              </button>
              <button type="button" className="auth-btn" onClick={handleSubmit}
                disabled={loading}>
                {loading ? <span className="btn-loader" /> : <>Register <span className="btn-arrow">→</span></>}
              </button>
            </div>
          </div>
        )}

        {/* Step 2 — Done */}
        {step === 2 && (
          <div className="auth-form success-screen">
            <div className="success-icon">🎉</div>
            <h2 className="auth-title">You're in!</h2>
            <p className="auth-subtitle">
              Account created successfully.{" "}
              {form.is_owner && "Your business account is pending approval."}
            </p>
            <a href="/login" className="auth-btn" style={{ textDecoration: "none", display: "block", textAlign: "center" }}>
              Go to Login <span className="btn-arrow">→</span>
            </a>
          </div>
        )}

        {step < 2 && (
          <p className="auth-switch">
            Already have an account?{" "}
            <a href="/login" className="auth-link">Sign in</a>
          </p>
        )}
      </div>
    </div>
  );
}
