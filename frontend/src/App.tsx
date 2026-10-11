import { FormEvent, useMemo, useState } from "react";
import {
  calculateAffordability,
  calculateLoan,
  calculateScenarios,
  type Affordability,
  type LoanContext,
  type LoanSummary,
  type RateScenario,
} from "./api";
import { AssistantPanel, type ExternalAssistantAction } from "./AssistantPanel";
import { HowToUseGuide } from "./HowToUseGuide";
import { KfsAnalysisSection } from "./KfsAnalysisSection";
import { LoanCategorySelector } from "./LoanCategorySelector";
import { OfferComparisonSection } from "./OfferComparisonSection";
import { LOAN_CATEGORIES, type LoanCategoryId } from "./types/loans";

type FormValues = {
  assetPrice: number;
  downPayment: number;
  income: number;
  existingEmis: number;
  expenses: number;
  interestRate: number;
  tenure: number;
  processingFee: number;
};

const inr = (value: string | number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Number(value));

function Field({
  label,
  value,
  onChange,
  prefix = "₹",
  min = 0,
  step = 1,
  helpText,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  prefix?: string;
  min?: number;
  step?: number;
  helpText?: string;
}) {
  return (
    <label className="field">
      <span className="field-label-text">
        {label}
        {helpText && <small className="field-hint" title={helpText}>ℹ</small>}
      </span>
      <div className="input-wrap">
        <b>{prefix}</b>
        <input
          aria-label={label}
          min={min}
          step={step}
          type="number"
          inputMode="decimal"
          value={value}
          onChange={(event) => onChange(Number(event.target.value))}
        />
      </div>
      {helpText && <small className="field-subtext">{helpText}</small>}
    </label>
  );
}

function App() {
  const [selectedCategory, setSelectedCategory] = useState<LoanCategoryId>("car");
  const categoryConfig = LOAN_CATEGORIES[selectedCategory];

  const [values, setValues] = useState<FormValues>({
    assetPrice: categoryConfig.defaultValues.assetPrice,
    downPayment: categoryConfig.defaultValues.downPayment,
    income: categoryConfig.defaultValues.income,
    existingEmis: categoryConfig.defaultValues.existingEmis,
    expenses: categoryConfig.defaultValues.expenses,
    interestRate: categoryConfig.defaultValues.interestRate,
    tenure: categoryConfig.defaultValues.tenure,
    processingFee: categoryConfig.defaultValues.processingFee,
  });

  const [loan, setLoan] = useState<LoanSummary | null>(null);
  const [affordability, setAffordability] = useState<Affordability | null>(null);
  const [scenarios, setScenarios] = useState<RateScenario[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showDetails, setShowDetails] = useState(false);
  const [showGuideModal, setShowGuideModal] = useState(false);
  const [externalAction, setExternalAction] = useState<ExternalAssistantAction | null>(null);

  // Switch category and adapt defaults
  function handleCategorySelect(newCatId: LoanCategoryId) {
    setSelectedCategory(newCatId);
    const newConfig = LOAN_CATEGORIES[newCatId];
    setValues((prev) => ({
      ...prev,
      assetPrice: newConfig.defaultValues.assetPrice,
      downPayment: newConfig.defaultValues.downPayment,
      interestRate: newConfig.defaultValues.interestRate,
      tenure: newConfig.defaultValues.tenure,
      processingFee: newConfig.defaultValues.processingFee,
    }));
    setLoan(null);
    setAffordability(null);
    setScenarios([]);
    setError("");
  }

  const loanAmount = useMemo(() => {
    if (!categoryConfig.fieldLabels.hasDownPayment) {
      return Math.max(0, values.assetPrice);
    }
    return Math.max(0, values.assetPrice - values.downPayment);
  }, [categoryConfig, values.assetPrice, values.downPayment]);

  const activeLoanContext: LoanContext = useMemo(
    () => ({
      loan_amount: loanAmount > 0 ? loanAmount : undefined,
      annual_interest_rate: values.interestRate > 0 ? values.interestRate : undefined,
      tenure_months: values.tenure > 0 ? values.tenure : undefined,
      processing_fee: values.processingFee >= 0 ? values.processingFee : undefined,
      other_charges: 0,
      monthly_income: values.income > 0 ? values.income : undefined,
      existing_emis: values.existingEmis >= 0 ? values.existingEmis : undefined,
      estimated_monthly_expenses: values.expenses >= 0 ? values.expenses : undefined,
    }),
    [loanAmount, values]
  );

  const activePlanSummary = useMemo(() => {
    if (!loan) return null;
    return {
      loanAmount,
      interestRate: values.interestRate,
      tenure: values.tenure,
      emi: loan.emi,
      total_interest: loan.total_interest,
      total_borrowing_cost: loan.total_borrowing_cost,
    };
  }, [loan, loanAmount, values]);

  const highestScenarioEmi = useMemo(
    () => Math.max(...scenarios.map((scenario) => Number(scenario.emi)), 1),
    [scenarios]
  );

  const change = (key: keyof FormValues) => (next: number) =>
    setValues((current) => ({ ...current, [key]: next }));

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (loanAmount <= 0) {
      setError(
        categoryConfig.fieldLabels.hasDownPayment
          ? "Down payment must be lower than the asset price."
          : "Please enter a loan amount greater than ₹0."
      );
      return;
    }
    setLoading(true);
    setError("");
    const base = {
      loan_amount: loanAmount,
      annual_interest_rate: values.interestRate,
      tenure_months: values.tenure,
      processing_fee: values.processingFee,
      other_charges: 0,
    };
    try {
      const nextLoan = await calculateLoan(base);
      const [nextAffordability, nextScenarios] = await Promise.all([
        calculateAffordability({
          monthly_income: values.income,
          existing_emis: values.existingEmis,
          proposed_emi: Number(nextLoan.emi),
          estimated_monthly_expenses: values.expenses,
        }),
        calculateScenarios(base),
      ]);
      setLoan(nextLoan);
      setAffordability(nextAffordability);
      setScenarios(nextScenarios);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to calculate. Please check your inputs.");
    } finally {
      setLoading(false);
    }
  }

  const scoreTone = affordability && affordability.score < 60 ? "warning" : "good";

  return (
    <main>
      {/* Universal Navigation */}
      <nav className="main-nav" aria-label="Main Navigation">
        <a className="brand" href="#top" aria-label="LoanWise home">
          <i>↗</i> LoanWise <em>AI</em>
        </a>

        {/* Active Loan Category Pill in Header */}
        <div className="nav-category-badge" title="Active loan category">
          <span className="badge-cat-icon">{categoryConfig.icon}</span>
          <span className="badge-cat-name">{categoryConfig.name}</span>
          <a href="#explore-loans" className="change-cat-link">
            Change
          </a>
        </div>

        <button
          type="button"
          className="mobile-guide-trigger-btn"
          onClick={() => setShowGuideModal(true)}
          aria-label="Open how to use guide"
        >
          📖 Guide
        </button>

        <div className="nav-links">
          <button
            type="button"
            className="guide-trigger-btn"
            onClick={() => setShowGuideModal(true)}
            aria-label="Open how to use guide"
          >
            📖 How to use LoanWise
          </button>
          <a href="#explore-loans">01 / Loans</a>
          <a href="#calculator-section">02 / Plan & Cost</a>
          <a href="#compare-section">03 / Compare</a>
          <a href="#kfs-section">04 / KFS Document</a>
          <a href="#assistant-panel-section">05 / Assistant</a>
        </div>
      </nav>

      {/* Guide Modal / Embedded View */}
      {showGuideModal && (
        <div className="guide-modal-overlay">
          <HowToUseGuide onClose={() => setShowGuideModal(false)} />
        </div>
      )}

      {/* Hero Section */}
      <section className="hero" id="top">
        <div>
          <p className="eyebrow">UNIVERSAL LOAN DECISION PLATFORM</p>
          <h1>
            Understand your loan.
            <br />
            <strong>Know the real cost.</strong>
          </h1>
          <p className="lede">
            A simple, visual-first loan platform for first-time borrowers, families, and salaried
            individuals. Compare offers, verify KFS terms, and make informed financial decisions.
          </p>
        </div>

        <div className="hero-chip">
          <span>Product Promise</span>
          <b>Understand before you borrow</b>
          <small>Decision support • Not loan approvals</small>
        </div>
      </section>

      {/* Educational Trust Banner */}
      <aside className="trust-disclaimer-banner" role="note">
        <span className="trust-icon">🛡️</span>
        <div className="trust-text">
          <strong>Decision Support & Financial Education:</strong> LoanWise AI helps you evaluate borrowing
          costs and verify loan documents through deterministic calculations and verified RBI guidance. It
          does not approve loans, solicit borrower applications, or guarantee lender eligibility.
        </div>
      </aside>

      {/* STAGE 1: LOAN CATEGORY EXPLORATION */}
      <LoanCategorySelector selectedId={selectedCategory} onSelect={handleCategorySelect} />

      {/* STAGE 2: CALCULATOR & WORKSPACE */}
      <section className="workspace" id="calculator-section">
        <form className="calculator" onSubmit={submit}>
          <div className="section-heading">
            <p className="eyebrow">02 / YOUR PLAN</p>
            <h2>Calculate {categoryConfig.name} Terms</h2>
            <p className="section-subtext">
              Enter your terms below. All calculations use deterministic reducing balance math.
            </p>
          </div>

          <div className="fields">
            <Field
              label={categoryConfig.fieldLabels.assetPrice}
              value={values.assetPrice}
              onChange={change("assetPrice")}
              min={1}
              helpText={categoryConfig.fieldLabels.assetPriceHelp}
            />

            {categoryConfig.fieldLabels.hasDownPayment ? (
              <Field
                label={categoryConfig.fieldLabels.downPayment}
                value={values.downPayment}
                onChange={change("downPayment")}
                helpText={categoryConfig.fieldLabels.downPaymentHelp}
              />
            ) : (
              <div className="field-placeholder">
                <span className="field-label-text">Down Payment</span>
                <p className="field-disabled-note">Not applicable for {categoryConfig.name}</p>
              </div>
            )}

            <output className="loan-amount">
              <span>Estimated loan amount to borrow</span>
              <strong>{inr(loanAmount)}</strong>
            </output>

            <Field
              label="Monthly take-home income"
              value={values.income}
              onChange={change("income")}
              min={1}
              helpText="Net monthly salary or business income credited to your account."
            />

            <Field
              label="Existing monthly EMIs"
              value={values.existingEmis}
              onChange={change("existingEmis")}
              helpText="Current loan or credit card EMIs you are actively paying."
            />

            <Field
              label="Monthly expenses (optional)"
              value={values.expenses}
              onChange={change("expenses")}
              helpText="Estimated rent, groceries, utilities, and school fees."
            />
          </div>

          <div className="sliders">
            <label>
              <span>
                Interest rate (annual reducing) <b>{values.interestRate}%</b>
              </span>
              <input
                aria-label="Interest rate"
                type="range"
                min="0"
                max="25"
                step="0.05"
                value={values.interestRate}
                onChange={(e) => change("interestRate")(Number(e.target.value))}
              />
              <small className="slider-hint">{categoryConfig.fieldLabels.interestRateHelp}</small>
            </label>

            <label>
              <span>
                Tenure <b>{(values.tenure / 12).toFixed(1)} years ({values.tenure} months)</b>
              </span>
              <input
                aria-label="Tenure"
                type="range"
                min={categoryConfig.fieldLabels.tenureMinMonths}
                max={categoryConfig.fieldLabels.tenureMaxMonths}
                step={categoryConfig.fieldLabels.tenureStepMonths}
                value={values.tenure}
                onChange={(e) => change("tenure")(Number(e.target.value))}
              />
              <small className="slider-hint">{categoryConfig.fieldLabels.tenureHelp}</small>
            </label>
          </div>

          <Field
            label="Processing fee"
            value={values.processingFee}
            onChange={change("processingFee")}
            helpText="One-time fee charged upfront by lender. Included in total borrowing cost."
          />

          <button type="submit" disabled={loading}>
            {loading ? "Calculating your loan…" : `See ${categoryConfig.name} Analysis →`}
          </button>

          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
        </form>

        <section className="result" id="decision-view" aria-live="polite">
          {!loan || !affordability ? (
            <div className="empty">
              <div className="empty-mark">⌁</div>
              <h2>Your decision view</h2>
              <p>
                Enter your details to get an explainable estimate of your EMI, borrowing cost, and
                affordability score.
              </p>
              <small>No lender approvals or hidden fees are assumed.</small>

              {categoryConfig.educationalTips.length > 0 && (
                <div className="category-tips-box">
                  <strong>💡 Tips for {categoryConfig.name}:</strong>
                  <ul>
                    {categoryConfig.educationalTips.map((tip, idx) => (
                      <li key={idx}>{tip}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <>
              <div className="score-row">
                <div className={`score ${scoreTone}`}>
                  <small>LOANWISE SCORE</small>
                  <b>
                    {affordability.score}
                    <i>/ 100</i>
                  </b>
                  <span>{affordability.classification}</span>
                </div>
                <p>
                  Based on your income, existing EMIs, and expenses—not confidential lender credit scoring.
                </p>
              </div>

              <div className="metrics">
                <article>
                  <span>MONTHLY EMI</span>
                  <b>{inr(loan.emi)}</b>
                </article>
                <article>
                  <span>TOTAL INTEREST</span>
                  <b>{inr(loan.total_interest)}</b>
                </article>
                <article>
                  <span>TOTAL BORROWING COST</span>
                  <b>{inr(loan.total_borrowing_cost)}</b>
                </article>
              </div>

              <div className="insights">
                <div>
                  <h3>Working for you</h3>
                  {affordability.reasons.map((reason) => (
                    <p key={reason}>● {reason}</p>
                  ))}
                </div>
                <div>
                  <h3>Watch out</h3>
                  {affordability.risks.length ? (
                    affordability.risks.map((risk) => <p key={risk}>● {risk}</p>)
                  ) : (
                    <p>● Keep an emergency fund buffer before taking on new debt.</p>
                  )}
                </div>
              </div>

              <button
                className="text-button"
                type="button"
                onClick={() => setShowDetails(!showDetails)}
              >
                {showDetails ? "Hide calculation details" : "Why this result?"}
              </button>

              {showDetails && (
                <div className="details">
                  <p>
                    Projected EMI burden: <b>{affordability.projected_emi_burden_percent}%</b> of monthly income.
                  </p>
                  <p>
                    Income remaining after EMIs and selected expenses:{" "}
                    <b>{inr(affordability.remaining_income_after_emis)}</b>.
                  </p>
                  <p>
                    Includes disclosed processing fee of {inr(values.processingFee)}. Calculations assume
                    standard monthly reducing balance amortization.
                  </p>
                </div>
              )}
            </>
          )}
        </section>
      </section>

      {/* Floating Rate Sensitivity Scenario */}
      {scenarios.length > 0 && (
        <section className="scenario">
          <div>
            <p className="eyebrow">WHAT IF INTEREST RATES RISE?</p>
            <h2>Your rate sensitivity analysis</h2>
            <p>
              For a floating-rate loan, lenders adjust your EMI or tenure whenever external benchmarks move.
              This illustration shows the potential monthly impact.
            </p>
          </div>
          <div className="scenario-bars">
            {scenarios.map((scenario, index) => (
              <article key={scenario.annual_interest_rate}>
                <span>{scenario.annual_interest_rate}%</span>
                <div className="bar">
                  <i
                    style={{
                      width: `${Math.max(
                        12,
                        (Number(scenario.emi) / highestScenarioEmi) * 100
                      )}%`,
                    }}
                  />
                </div>
                <b>
                  {inr(scenario.emi)}
                  <small>
                    {index ? ` +${inr(scenario.additional_monthly_cost)}/mo` : " current"}
                  </small>
                </b>
              </article>
            ))}
          </div>
        </section>
      )}

      {/* STAGE 3: OFFER COMPARISON SECTION */}
      <OfferComparisonSection
        currentPlanLoanAmount={loanAmount > 0 ? loanAmount : 900000}
        currentPlanRate={values.interestRate > 0 ? values.interestRate : 9.25}
        currentPlanTenure={values.tenure > 0 ? values.tenure : 60}
        currentPlanFee={values.processingFee >= 0 ? values.processingFee : 4999}
      />

      {/* STAGE 4: KEY FACT STATEMENT (KFS) DOCUMENT INTELLIGENCE */}
      <div id="kfs-section">
        <KfsAnalysisSection
          activePlan={activePlanSummary}
          onAskAssistant={(prompt, ctx) =>
            setExternalAction({
              prompt,
              context: ctx ?? activeLoanContext,
              timestamp: Date.now(),
            })
          }
        />
      </div>

      {/* STAGE 5: AI ASSISTANT CONTEXTUAL HELPER */}
      <AssistantPanel
        loanContext={activeLoanContext}
        externalAction={externalAction}
        onClearExternalAction={() => setExternalAction(null)}
      />

      {/* Comprehensive Educational Disclaimer Footer */}
      <footer id="disclaimer">
        <div>
          <b>LoanWise AI Platform</b>
          <p>
            Understand your loan. Know the real cost. Make a more informed decision.
          </p>
        </div>
        <p>
          LoanWise AI is an educational decision-support platform designed for Indian borrowers. It does not
          issue loans, guarantee approvals, or act as an intermediary for lenders. All calculations are
          deterministic and based on disclosed inputs and official Reserve Bank of India (RBI) regulations.
        </p>
      </footer>

      {/* Mobile Bottom Navigation Bar */}
      <nav className="mobile-bottom-nav" aria-label="Mobile Navigation">
        <a href="#explore-loans" className="mobile-nav-item" aria-label="Loan Categories">
          <span className="mobile-nav-icon" aria-hidden="true">🏷️</span>
          <span className="mobile-nav-label">Loans</span>
        </a>
        <a href="#calculator-section" className="mobile-nav-item" aria-label="Loan Calculator">
          <span className="mobile-nav-icon" aria-hidden="true">🧮</span>
          <span className="mobile-nav-label">Calculator</span>
        </a>
        <a href="#compare-section" className="mobile-nav-item" aria-label="Compare Offers">
          <span className="mobile-nav-icon" aria-hidden="true">⚖️</span>
          <span className="mobile-nav-label">Compare</span>
        </a>
        <a href="#kfs-section" className="mobile-nav-item" aria-label="KFS Document Analysis">
          <span className="mobile-nav-icon" aria-hidden="true">📄</span>
          <span className="mobile-nav-label">KFS Doc</span>
        </a>
        <a href="#assistant-panel-section" className="mobile-nav-item" aria-label="AI Assistant">
          <span className="mobile-nav-icon" aria-hidden="true">💬</span>
          <span className="mobile-nav-label">Assistant</span>
        </a>
      </nav>
    </main>
  );
}

export default App;
