import { LOAN_CATEGORIES, type LoanCategoryId } from "./types/loans";

interface LoanCategorySelectorProps {
  selectedId: LoanCategoryId;
  onSelect: (categoryId: LoanCategoryId) => void;
}

export function LoanCategorySelector({ selectedId, onSelect }: LoanCategorySelectorProps) {
  const selectedConfig = LOAN_CATEGORIES[selectedId];

  return (
    <section className="category-section" id="explore-loans" aria-label="Explore Loan Categories">
      <div className="section-heading">
        <p className="eyebrow">01 / CHOOSE YOUR LOAN TYPE</p>
        <h2>What type of loan are you exploring?</h2>
        <p className="section-subtext">
          LoanWise AI adapts labels, realistic market ranges, and regulatory rules to your chosen loan.
          Select a category below to get started.
        </p>
      </div>

      <div className="category-grid" role="radiogroup" aria-label="Loan categories">
        {(Object.keys(LOAN_CATEGORIES) as LoanCategoryId[]).map((catId) => {
          const cat = LOAN_CATEGORIES[catId];
          const isSelected = catId === selectedId;

          return (
            <div
              key={cat.id}
              className={`category-card ${isSelected ? "category-card-active" : ""}`}
              onClick={() => onSelect(cat.id)}
              role="radio"
              aria-checked={isSelected}
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelect(cat.id);
                }
              }}
            >
              <div className="category-card-header">
                <span className="category-icon" aria-hidden="true">
                  {cat.icon}
                </span>
                <span
                  className={`support-pill support-${cat.supportLevel}`}
                  title={cat.supportExplanation}
                >
                  {cat.supportBadge}
                </span>
              </div>

              <h3 className="category-name">{cat.name}</h3>
              <p className="category-tagline">{cat.tagline}</p>

              <button
                type="button"
                className={`category-select-btn ${isSelected ? "btn-selected" : ""}`}
                aria-label={`Select ${cat.name}`}
              >
                {isSelected ? "✓ Selected" : "Select this loan"}
              </button>
            </div>
          );
        })}
      </div>

      {/* Selected Category Feature Guidance & Honest Boundaries */}
      <div className="selected-category-banner" aria-live="polite">
        <div className="banner-left">
          <span className="banner-icon">{selectedConfig.icon}</span>
          <div>
            <div className="banner-title-row">
              <strong>Exploring: {selectedConfig.name}</strong>
              <span className={`support-pill support-${selectedConfig.supportLevel}`}>
                {selectedConfig.supportBadge}
              </span>
            </div>
            <p className="banner-desc">{selectedConfig.supportExplanation}</p>
          </div>
        </div>

        <div className="banner-engine-box">
          <small className="engine-badge-tag">ENGINE GUARANTEE</small>
          <p>{selectedConfig.whatTheEngineDoes}</p>
        </div>
      </div>
    </section>
  );
}
