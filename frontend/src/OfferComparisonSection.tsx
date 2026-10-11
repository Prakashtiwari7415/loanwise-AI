import { useState, useMemo } from "react";
import { compareLoans, calculateLoan, type CompareRecommendation, type LoanSummary } from "./api";

const inr = (value: string | number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Number(value));

interface OfferData {
  lender: string;
  loanAmount: number;
  interestRate: number;
  tenure: number;
  processingFee: number;
}

interface OfferComparisonSectionProps {
  currentPlanLoanAmount?: number;
  currentPlanRate?: number;
  currentPlanTenure?: number;
  currentPlanFee?: number;
}

export function OfferComparisonSection({
  currentPlanLoanAmount = 900000,
  currentPlanRate = 9.25,
  currentPlanTenure = 60,
  currentPlanFee = 4999,
}: OfferComparisonSectionProps) {
  const [offerA, setOfferA] = useState<OfferData>({
    lender: "Bank A (Offer 1)",
    loanAmount: currentPlanLoanAmount,
    interestRate: currentPlanRate,
    tenure: currentPlanTenure,
    processingFee: currentPlanFee,
  });

  const [offerB, setOfferB] = useState<OfferData>({
    lender: "Bank B (Offer 2)",
    loanAmount: currentPlanLoanAmount,
    interestRate: 9.75,
    tenure: 84, // Longer tenure! Lower EMI, higher total cost
    processingFee: 2500,
  });

  const [summaryA, setSummaryA] = useState<LoanSummary | null>(null);
  const [summaryB, setSummaryB] = useState<LoanSummary | null>(null);
  const [recommendation, setRecommendation] = useState<CompareRecommendation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCompare() {
    setLoading(true);
    setError(null);
    try {
      const [resA, resB] = await Promise.all([
        calculateLoan({
          loan_amount: offerA.loanAmount,
          annual_interest_rate: offerA.interestRate,
          tenure_months: offerA.tenure,
          processing_fee: offerA.processingFee,
          other_charges: 0,
        }),
        calculateLoan({
          loan_amount: offerB.loanAmount,
          annual_interest_rate: offerB.interestRate,
          tenure_months: offerB.tenure,
          processing_fee: offerB.processingFee,
          other_charges: 0,
        }),
      ]);

      setSummaryA(resA);
      setSummaryB(resB);

      const rec = await compareLoans([
        {
          lender: offerA.lender,
          loan_amount: offerA.loanAmount,
          annual_interest_rate: offerA.interestRate,
          tenure_months: offerA.tenure,
          processing_fee: offerA.processingFee,
          other_charges: 0,
        },
        {
          lender: offerB.lender,
          loan_amount: offerB.loanAmount,
          annual_interest_rate: offerB.interestRate,
          tenure_months: offerB.tenure,
          processing_fee: offerB.processingFee,
          other_charges: 0,
        },
      ]);
      setRecommendation(rec);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to compare offers.");
    } finally {
      setLoading(false);
    }
  }

  // Cost comparison calculation
  const comparisonInsight = useMemo(() => {
    if (!summaryA || !summaryB) return null;
    const emiA = parseFloat(summaryA.emi);
    const emiB = parseFloat(summaryB.emi);
    const costA = parseFloat(summaryA.total_borrowing_cost);
    const costB = parseFloat(summaryB.total_borrowing_cost);

    const costDiff = costB - costA;
    const emiDiff = emiB - emiA;

    return {
      cheaperLender: costDiff > 0 ? offerA.lender : offerB.lender,
      totalSavings: Math.abs(costDiff),
      emiWinner: emiDiff < 0 ? offerB.lender : offerA.lender,
      emiSavings: Math.abs(emiDiff),
      hasTenureTrap:
        (emiA > emiB && costA < costB) || (emiB > emiA && costB < costA),
    };
  }, [summaryA, summaryB, offerA, offerB]);

  return (
    <section className="compare-section" id="compare-section" aria-label="Compare Loan Offers">
      <div className="section-heading">
        <p className="eyebrow">03 / COMPARE LOAN OFFERS</p>
        <h2>Compare two offers side-by-side</h2>
        <p className="section-subtext">
          Lenders often lure borrowers with a smaller monthly EMI by stretching tenure. Compare total borrowing
          costs under the same assumptions before deciding.
        </p>
      </div>

      <div className="compare-inputs-grid">
        {/* Offer A Form */}
        <div className="compare-card offer-card-a">
          <div className="offer-header">
            <span className="offer-badge badge-a">OFFER A</span>
            <input
              type="text"
              className="lender-input"
              value={offerA.lender}
              onChange={(e) => setOfferA({ ...offerA, lender: e.target.value })}
              aria-label="Offer A Lender Name"
            />
          </div>

          <div className="offer-fields">
            <label className="field">
              <span>Loan Amount (₹)</span>
              <div className="input-wrap">
                <b>₹</b>
                <input
                  type="number"
                  inputMode="decimal"
                  value={offerA.loanAmount}
                  onChange={(e) => setOfferA({ ...offerA, loanAmount: Number(e.target.value) })}
                  aria-label="Offer A Loan Amount"
                />
              </div>
            </label>

            <label className="field">
              <span>Interest Rate (%)</span>
              <div className="input-wrap">
                <b>%</b>
                <input
                  type="number"
                  inputMode="decimal"
                  step="0.05"
                  value={offerA.interestRate}
                  onChange={(e) => setOfferA({ ...offerA, interestRate: Number(e.target.value) })}
                  aria-label="Offer A Interest Rate"
                />
              </div>
            </label>

            <label className="field">
              <span>Tenure (Months)</span>
              <div className="input-wrap">
                <b>📅</b>
                <input
                  type="number"
                  inputMode="numeric"
                  step="12"
                  value={offerA.tenure}
                  onChange={(e) => setOfferA({ ...offerA, tenure: Number(e.target.value) })}
                  aria-label="Offer A Tenure Months"
                />
              </div>
            </label>

            <label className="field">
              <span>Processing Fee (₹)</span>
              <div className="input-wrap">
                <b>₹</b>
                <input
                  type="number"
                  inputMode="decimal"
                  value={offerA.processingFee}
                  onChange={(e) => setOfferA({ ...offerA, processingFee: Number(e.target.value) })}
                  aria-label="Offer A Processing Fee"
                />
              </div>
            </label>
          </div>
        </div>

        {/* Offer B Form */}
        <div className="compare-card offer-card-b">
          <div className="offer-header">
            <span className="offer-badge badge-b">OFFER B</span>
            <input
              type="text"
              className="lender-input"
              value={offerB.lender}
              onChange={(e) => setOfferB({ ...offerB, lender: e.target.value })}
              aria-label="Offer B Lender Name"
            />
          </div>

          <div className="offer-fields">
            <label className="field">
              <span>Loan Amount (₹)</span>
              <div className="input-wrap">
                <b>₹</b>
                <input
                  type="number"
                  inputMode="decimal"
                  value={offerB.loanAmount}
                  onChange={(e) => setOfferB({ ...offerB, loanAmount: Number(e.target.value) })}
                  aria-label="Offer B Loan Amount"
                />
              </div>
            </label>

            <label className="field">
              <span>Interest Rate (%)</span>
              <div className="input-wrap">
                <b>%</b>
                <input
                  type="number"
                  inputMode="decimal"
                  step="0.05"
                  value={offerB.interestRate}
                  onChange={(e) => setOfferB({ ...offerB, interestRate: Number(e.target.value) })}
                  aria-label="Offer B Interest Rate"
                />
              </div>
            </label>

            <label className="field">
              <span>Tenure (Months)</span>
              <div className="input-wrap">
                <b>📅</b>
                <input
                  type="number"
                  inputMode="numeric"
                  step="12"
                  value={offerB.tenure}
                  onChange={(e) => setOfferB({ ...offerB, tenure: Number(e.target.value) })}
                  aria-label="Offer B Tenure Months"
                />
              </div>
            </label>

            <label className="field">
              <span>Processing Fee (₹)</span>
              <div className="input-wrap">
                <b>₹</b>
                <input
                  type="number"
                  inputMode="decimal"
                  value={offerB.processingFee}
                  onChange={(e) => setOfferB({ ...offerB, processingFee: Number(e.target.value) })}
                  aria-label="Offer B Processing Fee"
                />
              </div>
            </label>
          </div>
        </div>
      </div>

      <div className="compare-action-bar">
        <button
          type="button"
          className="compare-submit-btn"
          onClick={handleCompare}
          disabled={loading}
          aria-label="Compare offers side by side"
        >
          {loading ? "Comparing offers through engine…" : "Compare Both Offers →"}
        </button>
      </div>

      {error && <p className="error" role="alert">{error}</p>}

      {/* Comparison Results */}
      {summaryA && summaryB && (
        <div className="comparison-results-card" aria-live="polite">
          <div className="card-header">
            <div>
              <span className="pill-tag pill-lime">DETERMINISTIC COMPARISON</span>
              <h3>Side-by-Side Financial Results</h3>
            </div>
          </div>

          <div className="results-table">
            <div className="results-row results-header-row">
              <span className="metric-name">METRIC</span>
              <span className="col-val col-a">{offerA.lender}</span>
              <span className="col-val col-b">{offerB.lender}</span>
              <span className="col-diff">DIFFERENCE</span>
            </div>

            <div className="results-row">
              <span className="metric-name">Monthly EMI</span>
              <span className="col-val col-a">
                <span className="mobile-lender-label">{offerA.lender}: </span>
                {inr(summaryA.emi)}
              </span>
              <span className="col-val col-b">
                <span className="mobile-lender-label">{offerB.lender}: </span>
                {inr(summaryB.emi)}
              </span>
              <span className="col-diff">
                <span className="mobile-lender-label">Diff: </span>
                {parseFloat(summaryA.emi) < parseFloat(summaryB.emi)
                  ? `${offerA.lender} is lower by ${inr(parseFloat(summaryB.emi) - parseFloat(summaryA.emi))}/mo`
                  : `${offerB.lender} is lower by ${inr(parseFloat(summaryA.emi) - parseFloat(summaryB.emi))}/mo`}
              </span>
            </div>

            <div className="results-row">
              <span className="metric-name">Total Interest</span>
              <span className="col-val col-a">
                <span className="mobile-lender-label">{offerA.lender}: </span>
                {inr(summaryA.total_interest)}
              </span>
              <span className="col-val col-b">
                <span className="mobile-lender-label">{offerB.lender}: </span>
                {inr(summaryB.total_interest)}
              </span>
              <span className="col-diff">
                <span className="mobile-lender-label">Diff: </span>
                {parseFloat(summaryA.total_interest) < parseFloat(summaryB.total_interest)
                  ? `${offerA.lender} saves ${inr(parseFloat(summaryB.total_interest) - parseFloat(summaryA.total_interest))}`
                  : `${offerB.lender} saves ${inr(parseFloat(summaryA.total_interest) - parseFloat(summaryB.total_interest))}`}
              </span>
            </div>

            <div className="results-row">
              <span className="metric-name">Processing Fee</span>
              <span className="col-val col-a">
                <span className="mobile-lender-label">{offerA.lender}: </span>
                {inr(offerA.processingFee)}
              </span>
              <span className="col-val col-b">
                <span className="mobile-lender-label">{offerB.lender}: </span>
                {inr(offerB.processingFee)}
              </span>
              <span className="col-diff">
                <span className="mobile-lender-label">Diff: </span>
                Diff: {inr(Math.abs(offerA.processingFee - offerB.processingFee))}
              </span>
            </div>

            <div className="results-row row-total-cost">
              <span className="metric-name">
                <strong>TOTAL BORROWING COST</strong>
                <small>(Principal + Interest + Fees)</small>
              </span>
              <span className="col-val col-a">
                <span className="mobile-lender-label">{offerA.lender}: </span>
                <strong>{inr(summaryA.total_borrowing_cost)}</strong>
              </span>
              <span className="col-val col-b">
                <span className="mobile-lender-label">{offerB.lender}: </span>
                <strong>{inr(summaryB.total_borrowing_cost)}</strong>
              </span>
              <span className="col-diff highlight-diff">
                {comparisonInsight && (
                  <strong>
                    {comparisonInsight.cheaperLender} saves {inr(comparisonInsight.totalSavings)} overall
                  </strong>
                )}
              </span>
            </div>
          </div>

          {/* Educational Tenurial Trap Insight */}
          {comparisonInsight?.hasTenureTrap && (
            <div className="tenure-trap-callout" role="note">
              <strong>⚠️ The "Lower EMI" Illusion:</strong>
              <p>
                Notice that while {comparisonInsight.emiWinner} appears more affordable every month (saving{" "}
                {inr(comparisonInsight.emiSavings)}/mo), {comparisonInsight.cheaperLender} actually saves{" "}
                {inr(comparisonInsight.totalSavings)} overall! Stretching loan tenure reduces monthly cash outflow
                at the expense of significantly higher cumulative interest.
              </p>
            </div>
          )}

          {/* Engine Recommendation */}
          {recommendation && (
            <div className="recommendation-callout">
              <div className="rec-header">
                <span className="rec-score">Engine Score: {recommendation.score}/100</span>
                <h4>Recommended: {recommendation.lender}</h4>
              </div>
              <ul className="rec-reasons">
                {recommendation.reasons.map((r, i) => (
                  <li key={i}>✓ {r}</li>
                ))}
              </ul>
              {recommendation.risks.length > 0 && (
                <ul className="rec-risks">
                  {recommendation.risks.map((rk, i) => (
                    <li key={i}>⚠️ {rk}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
