import "./CategoryFilter.css";
import { CATEGORIES } from "../../utils/attractionHelpers";

export default function CategoryFilter({ activeCategory, onChange, categoryCounts = {} }) {
  return (
    <div className="category-filter">
      <div className="category-scroll">
        {CATEGORIES.map((cat) => {
          const count = cat.key === "all"
            ? Object.values(categoryCounts).reduce((a, b) => a + b, 0)
            : categoryCounts[cat.key];

          return (
            <button
              key={cat.key}
              className={`cat-pill ${activeCategory === cat.key ? "active" : ""}`}
              onClick={() => onChange(cat.key)}
              aria-pressed={activeCategory === cat.key}
            >
              <span className="cat-pill__icon">{cat.icon}</span>
              <span className="cat-pill__label">{cat.label}</span>
              {count != null && count > 0 && (
                <span className="cat-pill__count">{count > 999 ? "999+" : count}</span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}