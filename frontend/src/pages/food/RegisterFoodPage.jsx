import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createFoodPlace } from '../../services/foodService';
import useCurrentUser from '../../hooks/useCurrentUser';
import './RegisterFoodPage.css';

const CATEGORIES = [
  ['restaurant', 'Restaurant'],
  ['cafe', 'Café'],
  ['dhaba', 'Dhaba'],
  ['street_food', 'Street Food'],
  ['bakery', 'Bakery'],
  ['sweet_shop', 'Sweet Shop'],
  ['juice_bar', 'Juice Bar'],
  ['fast_food', 'Fast Food'],
];

const CUISINES = [
  ['north_indian', 'North Indian'],
  ['south_indian', 'South Indian'],
  ['chinese', 'Chinese'],
  ['mughlai', 'Mughlai'],
  ['italian', 'Italian'],
  ['continental', 'Continental'],
  ['fast_food', 'Fast Food'],
  ['multi', 'Multi-Cuisine'],
];

// Places get their coordinates from the address, so the form only asks for a
// place name and lets the backend geocode it.
const emptyForm = {
  name: '',
  category: 'restaurant',
  cuisine: 'multi',
  description: '',
  address: '',
  city: '',
  state: '',
  phone: '',
  website: '',
  image_url: '',
  price_level: 2,
  avg_cost_for_two: '',
  is_veg: true,
  home_delivery: false,
  takeaway: false,
  outdoor_seating: false,
};

const RegisterFoodPage = () => {
  const navigate = useNavigate();
  const { user, isOwner } = useCurrentUser();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [form, setForm] = useState(emptyForm);

  // A business account is what makes this page reachable, so send anyone else to
  // sign in rather than showing a form that would 403 on submit.
  useEffect(() => {
    if (user && !isOwner) navigate('/my-food-places', { replace: true });
  }, [user, isOwner, navigate]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((f) => ({ ...f, [name]: type === 'checkbox' ? checked : value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Validate before spending a network round trip; the server also enforces it.
    if (!form.name.trim()) return setError('Outlet name is required.');
    if (!form.address.trim()) return setError('Address is required.');
    if (!form.city.trim()) return setError('City is required.');
    if (form.avg_cost_for_two && Number(form.avg_cost_for_two) < 0) {
      return setError('Average cost cannot be negative.');
    }

    setLoading(true);
    try {
      const place = await createFoodPlace({
        ...form,
        avg_cost_for_two: form.avg_cost_for_two === '' ? null : Number(form.avg_cost_for_two),
        price_level: Number(form.price_level),
        image_url: form.image_url.trim() || null,
        website: form.website.trim() || null,
        phone: form.phone.trim() || null,
        description: form.description.trim(),
      });
      setSuccess(true);
      setTimeout(() => navigate(`/food/${place.id}`), 1800);
    } catch (err) {
      setError(err.message || 'Could not register your outlet. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="rfp-page success">
        <div className="rfp-card">
          <div className="rfp-success-icon">🥘</div>
          <h2>Restaurant Registered!</h2>
          <p>Your food place is now live on Yatrip Food.</p>
          <button className="rfp-submit-btn" onClick={() => navigate('/my-food-places')}>
            Manage my outlets
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="rfp-page">
      <div className="rfp-container">
        <header className="rfp-header">
          <button type="button" className="rfp-back" onClick={() => navigate('/food')}>← Back</button>
          <h1>Register Your Food Business</h1>
          <p>Join Yatrip Food and reach hungry travelers nearby</p>
        </header>

        <form className="rfp-card" onSubmit={handleSubmit} noValidate>
          <div className="rfp-section">
            <h3>🍽 Basic Details</h3>
            <div className="rfp-field">
              <label htmlFor="rfp-name">Outlet Name *</label>
              <input id="rfp-name" name="name" value={form.name} onChange={handleChange}
                placeholder="e.g. Royal Punjabi Dhaba" required />
            </div>

            <div className="rfp-row">
              <div className="rfp-field">
                <label htmlFor="rfp-category">Category</label>
                <select id="rfp-category" name="category" value={form.category} onChange={handleChange}>
                  {CATEGORIES.map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>
              <div className="rfp-field">
                <label htmlFor="rfp-cuisine">Cuisine Type</label>
                <select id="rfp-cuisine" name="cuisine" value={form.cuisine} onChange={handleChange}>
                  {CUISINES.map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="rfp-field">
              <label htmlFor="rfp-image">Photo URL</label>
              <input id="rfp-image" type="url" name="image_url" value={form.image_url}
                onChange={handleChange} placeholder="https://… (optional)" />
            </div>
          </div>

          <div className="rfp-section">
            <h3>📍 Location & Pricing</h3>
            <div className="rfp-field">
              <label htmlFor="rfp-address">Full Address *</label>
              <input id="rfp-address" name="address" value={form.address} onChange={handleChange}
                placeholder="Shop no, Building, Street..." required />
            </div>
            <div className="rfp-row">
              <div className="rfp-field">
                <label htmlFor="rfp-city">City *</label>
                <input id="rfp-city" name="city" value={form.city} onChange={handleChange}
                  placeholder="e.g. Jaipur" required />
              </div>
              <div className="rfp-field">
                <label htmlFor="rfp-state">State</label>
                <input id="rfp-state" name="state" value={form.state || ''} onChange={handleChange}
                  placeholder="e.g. Rajasthan" />
              </div>
            </div>

            <div className="rfp-row">
              <div className="rfp-field">
                <label htmlFor="rfp-price">Price Level</label>
                <select id="rfp-price" name="price_level" value={form.price_level} onChange={handleChange}>
                  <option value="1">₹ Budget</option>
                  <option value="2">₹₹ Moderate</option>
                  <option value="3">₹₹₹ Premium</option>
                  <option value="4">₹₹₹₹ Fine Dining</option>
                </select>
              </div>
              <div className="rfp-field">
                <label htmlFor="rfp-cost">Avg. Cost for Two (₹)</label>
                <input id="rfp-cost" type="number" min="0" name="avg_cost_for_two"
                  value={form.avg_cost_for_two} onChange={handleChange} placeholder="500" />
              </div>
            </div>
          </div>

          <div className="rfp-section">
            <h3>☎ Contact & Services</h3>
            <div className="rfp-row">
              <div className="rfp-field">
                <label htmlFor="rfp-phone">Phone</label>
                <input id="rfp-phone" type="tel" name="phone" value={form.phone}
                  onChange={handleChange} placeholder="+91 …" />
              </div>
              <div className="rfp-field">
                <label htmlFor="rfp-website">Website</label>
                <input id="rfp-website" type="url" name="website" value={form.website}
                  onChange={handleChange} placeholder="https://…" />
              </div>
            </div>

            <div className="rfp-row">
              <div className="rfp-field">
                <label htmlFor="rfp-veg">Vegetarian Only?</label>
                <div className="rfp-toggle">
                  <input id="rfp-veg" type="checkbox" name="is_veg" checked={form.is_veg}
                    onChange={handleChange} />
                  <span>{form.is_veg ? 'Yes (Pure Veg)' : 'No (Non-Veg available)'}</span>
                </div>
              </div>
              <div className="rfp-field">
                <label htmlFor="rfp-takeaway">Takeaway</label>
                <div className="rfp-toggle">
                  <input id="rfp-takeaway" type="checkbox" name="takeaway" checked={form.takeaway}
                    onChange={handleChange} />
                  <span>{form.takeaway ? 'Available' : 'Not available'}</span>
                </div>
              </div>
            </div>

            <div className="rfp-row">
              <div className="rfp-field">
                <label htmlFor="rfp-delivery">Home Delivery</label>
                <div className="rfp-toggle">
                  <input id="rfp-delivery" type="checkbox" name="home_delivery"
                    checked={form.home_delivery} onChange={handleChange} />
                  <span>{form.home_delivery ? 'Available' : 'Not available'}</span>
                </div>
              </div>
              <div className="rfp-field">
                <label htmlFor="rfp-outdoor">Outdoor Seating</label>
                <div className="rfp-toggle">
                  <input id="rfp-outdoor" type="checkbox" name="outdoor_seating"
                    checked={form.outdoor_seating} onChange={handleChange} />
                  <span>{form.outdoor_seating ? 'Yes' : 'No'}</span>
                </div>
              </div>
            </div>

            <div className="rfp-field">
              <label htmlFor="rfp-desc">About</label>
              <textarea id="rfp-desc" name="description" rows="3" value={form.description}
                onChange={handleChange} placeholder="A short description of your outlet" />
            </div>
          </div>

          {error && <div className="rfp-error" role="alert">⚠️ {error}</div>}

          <button type="submit" className="rfp-submit-btn" disabled={loading}>
            {loading ? 'Registering…' : 'Register My Outlet'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default RegisterFoodPage;