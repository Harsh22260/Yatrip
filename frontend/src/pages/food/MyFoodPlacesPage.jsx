import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import PlaceImage from '../../components/PlaceImage';
import {
  fetchMyFoodPlaces,
  updateFoodPlace,
  deleteFoodPlace,
  createMenuItem,
  deleteMenuItem,
} from '../../services/foodService';
import { getCategoryInfo } from '../../utils/foodHelpers';
import { categoryFallback, fallbackCredit } from '../../utils/foodFallbackImages';
import './MyFoodPlacesPage.css';

const emptyDraft = { name: '', description: '', price: '', is_veg: true };

const MyFoodPlacesPage = () => {
  const navigate = useNavigate();
  const [places, setPlaces] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState(null);
  const [editing, setEditing] = useState(null);
  const [openMenu, setOpenMenu] = useState(null);
  const [draft, setDraft] = useState(emptyDraft);
  const [menuError, setMenuError] = useState('');

  const load = useCallback(async (signal) => {
    setError('');
    try {
      const data = await fetchMyFoodPlaces();
      if (!signal?.aborted) setPlaces(data);
    } catch (err) {
      if (signal?.aborted) return;
      setError(err.message || 'Could not load your outlets.');
      setPlaces([]);
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    // Reading the owner's own rows from the API on mount, not derived state.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const remove = async (place) => {
    if (!window.confirm(`Delete “${place.name}”? This cannot be undone.`)) return;
    setBusyId(place.id);
    setError('');
    try {
      await deleteFoodPlace(place.id);
      setPlaces((list) => list.filter((p) => p.id !== place.id));
    } catch (err) {
      setError(err.message || 'Could not delete that outlet.');
    } finally {
      setBusyId(null);
    }
  };

  const saveEdits = async (place, patch) => {
    setBusyId(place.id);
    setError('');
    try {
      const updated = await updateFoodPlace(place.id, patch);
      setPlaces((list) => list.map((p) => (p.id === place.id ? { ...p, ...updated } : p)));
      setEditing(null);
    } catch (err) {
      setError(err.message || 'Could not save those changes.');
    } finally {
      setBusyId(null);
    }
  };

  const addDish = async (place, event) => {
    event.preventDefault();
    setMenuError('');
    if (!draft.name.trim()) return setMenuError('Dish name is required.');
    if (draft.price !== '' && Number(draft.price) < 0) {
      return setMenuError('Price cannot be negative.');
    }

    setBusyId(place.id);
    try {
      const item = await createMenuItem(place.id, {
        name: draft.name.trim(),
        description: '',
        price: draft.price === '' ? null : Number(draft.price),
        is_veg: draft.is_veg,
        is_available: true,
      });
      setPlaces((list) =>
        list.map((p) =>
          p.id === place.id ? { ...p, menu_items: [...(p.menu_items || []), item] } : p
        )
      );
      setDraft(emptyDraft);
    } catch (err) {
      setMenuError(err.message || 'Could not add that dish.');
    } finally {
      setBusyId(null);
    }
  };

  const removeDish = async (place, item) => {
    setMenuError('');
    setBusyId(place.id);
    try {
      await deleteMenuItem(place.id, item.id);
      setPlaces((list) =>
        list.map((p) =>
          p.id === place.id
            ? { ...p, menu_items: (p.menu_items || []).filter((i) => i.id !== item.id) }
            : p
        )
      );
    } catch (err) {
      setMenuError(err.message || 'Could not remove that dish.');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="mfp-page">
      <div className="mfp-container">
        <header className="mfp-header">
          <div>
            <h1>My Food Outlets</h1>
            <p>Keep your listings and menus up to date</p>
          </div>
          <div className="mfp-header-actions">
            <button className="mfp-btn" onClick={() => navigate('/food')}>← Back to Food</button>
            <button className="mfp-btn primary" onClick={() => navigate('/register-food')}>
              + Register Outlet
            </button>
          </div>
        </header>

        {error && <div className="mfp-error" role="alert">⚠️ {error}</div>}

        {loading ? (
          <div className="mfp-grid">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="fc-skeleton" />
            ))}
          </div>
        ) : places.length === 0 ? (
          <div className="mfp-empty">
            <span>🍽️</span>
            <h3>No outlets yet</h3>
            <p>Register your first outlet and it will show up here.</p>
            <button className="mfp-btn primary" onClick={() => navigate('/register-food')}>
              Register an outlet
            </button>
          </div>
        ) : (
          <div className="mfp-grid">
            {places.map((place) => {
              const cat = getCategoryInfo(place.category);
              const items = place.menu_items || [];

              return (
                <article key={place.id} className="mfp-card">
                  <PlaceImage
                    src={place.image_url}
                    fallbackSrc={categoryFallback(place.category).src}
                    fallbackCredit={fallbackCredit(place.category)}
                    alt={place.name}
                    category={place.category}
                    name={place.name}
                    className="mfp-card__img"
                  />

                  <div className="mfp-card__body">
                    <div className="mfp-card__title">
                      <h3>{place.name}</h3>
                      {place.is_verified ? (
                        <span className="mfp-chip verified">✓ Verified</span>
                      ) : (
                        <span className="mfp-chip pending">Pending review</span>
                      )}
                    </div>
                    <p className="mfp-card__meta">
                      {cat.icon} {cat.label} · {[place.city, place.state].filter(Boolean).join(', ') || '—'}
                    </p>
                    {place.description && (
                      <p className="mfp-card__desc">{place.description}</p>
                    )}

                    <div className="mfp-card__actions">
                      <Link className="mfp-btn" to={`/food/${place.id}`}>View</Link>
                      <button
                        className="mfp-btn"
                        onClick={() => setEditing(editing === place.id ? null : place.id)}
                      >
                        {editing === place.id ? 'Close' : 'Edit'}
                      </button>
                      <button
                        className="mfp-btn"
                        onClick={() => setOpenMenu(openMenu === place.id ? null : place.id)}
                      >
                        Menu ({items.length})
                      </button>
                      <button
                        className="mfp-btn danger"
                        disabled={busyId === place.id}
                        onClick={() => remove(place)}
                      >
                        Delete
                      </button>
                    </div>

                    {editing === place.id && (
                      <EditForm
                        place={place}
                        busy={busyId === place.id}
                        onCancel={() => setEditing(null)}
                        onSave={(patch) => saveEdits(place, patch)}
                      />
                    )}

                    {openMenu === place.id && (
                      <div className="mfp-menu">
                        {menuError && <div className="mfp-error">⚠️ {menuError}</div>}

                        {items.length === 0 ? (
                          <p className="mfp-menu__empty">No dishes yet.</p>
                        ) : (
                          <ul className="mfp-menu__list">
                            {items.map((item) => (
                              <li key={item.id}>
                                <span className={`mfp-dot ${item.is_veg ? 'veg' : 'nonveg'}`} />
                                <span className="mfp-menu__name">{item.name}</span>
                                <span className="mfp-menu__price">
                                  {item.price != null ? `₹${item.price}` : '—'}
                                </span>
                                <button
                                  className="mfp-menu__remove"
                                  aria-label={`Remove ${item.name}`}
                                  onClick={() => removeDish(place, item)}
                                >
                                  ✕
                                </button>
                              </li>
                            ))}
                          </ul>
                        )}

                        <form className="mfp-menu__add" onSubmit={(e) => addDish(place, e)}>
                          <input
                            name="name"
                            value={draft.name}
                            placeholder="Dish name"
                            onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
                          />
                          <input
                            name="price"
                            type="number"
                            min="0"
                            value={draft.price}
                            placeholder="Price"
                            onChange={(e) => setDraft((d) => ({ ...d, price: e.target.value }))}
                          />
                          <label className="mfp-menu__veg">
                            <input
                              type="checkbox"
                              checked={draft.is_veg}
                              onChange={(e) => setDraft((d) => ({ ...d, is_veg: e.target.checked }))}
                            />
                            Veg
                          </label>
                          <button className="mfp-btn primary" disabled={busyId === place.id}>
                            Add
                          </button>
                        </form>
                      </div>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

const EditForm = ({ place, busy, onCancel, onSave }) => {
  const [form, setForm] = useState({
    name: place.name || '',
    description: place.description || '',
    address: place.address || '',
    city: place.city || '',
    phone: place.phone || '',
    website: place.website || '',
    image_url: place.image_url || '',
  });

  const change = (e) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
  };

  const submit = (e) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    onSave({
      ...form,
      image_url: form.image_url.trim() || null,
      website: form.website.trim() || null,
      phone: form.phone.trim() || null,
    });
  };

  return (
    <form className="mfp-edit" onSubmit={submit}>
      <div className="mfp-edit__row">
        <label htmlFor={`mfp-name-${place.id}`}>Name</label>
        <input id={`mfp-name-${place.id}`} name="name" value={form.name} onChange={change} />
      </div>
      <div className="mfp-edit__row">
        <label htmlFor={`mfp-city-${place.id}`}>City</label>
        <input id={`mfp-city-${place.id}`} name="city" value={form.city} onChange={change} />
      </div>
      <div className="mfp-edit__row">
        <label htmlFor={`mfp-image-${place.id}`}>Photo URL</label>
        <input id={`mfp-image-${place.id}`} name="image_url" value={form.image_url} onChange={change} />
      </div>
      <div className="mfp-edit__row">
        <label htmlFor={`mfp-address-${place.id}`}>Address</label>
        <input id={`mfp-address-${place.id}`} name="address" value={form.address} onChange={change} />
      </div>
      <div className="mfp-edit__row">
        <label htmlFor={`mfp-phone-${place.id}`}>Phone</label>
        <input id={`mfp-phone-${place.id}`} name="phone" value={form.phone} onChange={change} />
      </div>
      <div className="mfp-edit__row full">
        <label htmlFor={`mfp-desc-${place.id}`}>Description</label>
        <textarea id={`mfp-desc-${place.id}`} name="description" rows="2" value={form.description} onChange={change} />
      </div>
      <div className="mfp-edit__actions">
        <button className="mfp-btn" type="button" onClick={onCancel}>Cancel</button>
        <button className="mfp-btn primary" disabled={busy}>Save changes</button>
      </div>
    </form>
  );
};

export default MyFoodPlacesPage;