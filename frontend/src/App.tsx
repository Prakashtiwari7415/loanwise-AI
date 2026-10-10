import { FormEvent, useMemo, useState } from "react";
import { calculateAffordability, calculateLoan, calculateScenarios, type Affordability, type LoanSummary, type RateScenario } from "./api";

type FormValues = {
  carPrice: number;
  downPayment: number;
  income: number;
  existingEmis: number;
  expenses: number;
  interestRate: number;
  tenure: number;
  processingFee: number;
};

const initialValues: FormValues = {
  carPrice: 1200000,
  downPayment: 300000,
  income: 90000,
  existingEmis: 5000,
  expenses: 30000,
  interestRate: 9.25,
  tenure: 60,
  processingFee: 4999,
};

const inr = (value: string | number) => new Intl.NumberFormat("en-IN", {
  style: "currency", currency: "INR", maximumFractionDigits: 0,
}).format(Number(value));

function Field({ label, value, onChange, prefix = "₹", min = 0, step = 1 }: {
  label: string; value: number; onChange: (value: number) => void; prefix?: string; min?: number; step?: number;
}) {
  return <label className="field"><span>{label}</span><div className="input-wrap"><b>{prefix}</b><input aria-label={label} min={min} step={step} type="number" value={value} onChange={(event) => onChange(Number(event.target.value))} /></div></label>;
}

function App() {
  const [values, setValues] = useState(initialValues);
  const [loan, setLoan] = useState<LoanSummary | null>(null);
  const [affordability, setAffordability] = useState<Affordability | null>(null);
  const [scenarios, setScenarios] = useState<RateScenario[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showDetails, setShowDetails] = useState(false);

  const loanAmount = useMemo(() => Math.max(0, values.carPrice - values.downPayment), [values]);
  const highestScenarioEmi = useMemo(
    () => Math.max(...scenarios.map((scenario) => Number(scenario.emi)), 1),
    [scenarios],
  );
  const change = (key: keyof FormValues) => (next: number) => setValues((current) => ({ ...current, [key]: next }));

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (loanAmount <= 0) { setError("Down payment must be lower than the car price."); return; }
    setLoading(true); setError("");
    const base = { loan_amount: loanAmount, annual_interest_rate: values.interestRate, tenure_months: values.tenure, processing_fee: values.processingFee, other_charges: 0 };
    try {
      const nextLoan = await calculateLoan(base);
      const [nextAffordability, nextScenarios] = await Promise.all([
        calculateAffordability({ monthly_income: values.income, existing_emis: values.existingEmis, proposed_emi: Number(nextLoan.emi), estimated_monthly_expenses: values.expenses }),
        calculateScenarios(base),
      ]);
      setLoan(nextLoan); setAffordability(nextAffordability); setScenarios(nextScenarios);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to calculate. Please check your inputs.");
    } finally { setLoading(false); }
  }

  const scoreTone = affordability && affordability.score < 60 ? "warning" : "good";
  return <main>
    <nav><a className="brand" href="#top" aria-label="LoanWise home"><i>↗</i> LoanWise <em>AI</em></a><span>Car loan planner</span><a href="#disclaimer">How it works</a></nav>
    <section className="hero" id="top"><div><p className="eyebrow">CAR LOAN DECISION SUPPORT</p><h1>Understand your loan<br /><strong>in 60 seconds.</strong></h1><p className="lede">See the real monthly cost, affordability and rate-risk before you commit.</p></div><div className="hero-chip"><span>Built for decisions</span><b>Not loan approvals</b></div></section>
    <section className="workspace">
      <form className="calculator" onSubmit={submit}>
        <div className="section-heading"><p className="eyebrow">01 / YOUR PLAN</p><h2>Set your car loan</h2></div>
        <div className="fields">
          <Field label="Car price" value={values.carPrice} onChange={change("carPrice")} min={1} />
          <Field label="Down payment" value={values.downPayment} onChange={change("downPayment")} />
          <output className="loan-amount"><span>Estimated loan amount</span><strong>{inr(loanAmount)}</strong></output>
          <Field label="Monthly income" value={values.income} onChange={change("income")} min={1} />
          <Field label="Existing monthly EMIs" value={values.existingEmis} onChange={change("existingEmis")} />
          <Field label="Monthly expenses (optional)" value={values.expenses} onChange={change("expenses")} />
        </div>
        <div className="sliders">
          <label><span>Interest rate <b>{values.interestRate}%</b></span><input aria-label="Interest rate" type="range" min="0" max="20" step="0.05" value={values.interestRate} onChange={(e) => change("interestRate")(Number(e.target.value))} /></label>
          <label><span>Tenure <b>{values.tenure / 12} years</b></span><input aria-label="Tenure" type="range" min="12" max="84" step="12" value={values.tenure} onChange={(e) => change("tenure")(Number(e.target.value))} /></label>
        </div>
        <Field label="Processing fee" value={values.processingFee} onChange={change("processingFee")} />
        <button type="submit" disabled={loading}>{loading ? "Calculating your loan…" : "See my loan analysis →"}</button>
        {error && <p role="alert" className="error">{error}</p>}
      </form>
      <section className="result" aria-live="polite">
        {!loan || !affordability ? <div className="empty"><div className="empty-mark">⌁</div><h2>Your decision view</h2><p>Enter your details to get an explainable estimate of your EMI, borrowing cost and affordability.</p><small>No lender rates, approvals or penalties are assumed.</small></div> : <>
          <div className="score-row"><div className={`score ${scoreTone}`}><small>LOANWISE SCORE</small><b>{affordability.score}<i>/ 100</i></b><span>{affordability.classification}</span></div><p>Based on the income, EMIs and expenses you selected—not lender eligibility rules.</p></div>
          <div className="metrics"><article><span>MONTHLY EMI</span><b>{inr(loan.emi)}</b></article><article><span>TOTAL INTEREST</span><b>{inr(loan.total_interest)}</b></article><article><span>TOTAL COST</span><b>{inr(loan.total_borrowing_cost)}</b></article></div>
          <div className="insights"><div><h3>Working for you</h3>{affordability.reasons.map((reason) => <p key={reason}>● {reason}</p>)}</div><div><h3>Watch out</h3>{affordability.risks.length ? affordability.risks.map((risk) => <p key={risk}>● {risk}</p>) : <p>● Keep an emergency buffer before committing.</p>}</div></div>
          <button className="text-button" type="button" onClick={() => setShowDetails(!showDetails)}>{showDetails ? "Hide calculation details" : "Why this result?"}</button>
          {showDetails && <div className="details"><p>Projected EMI burden: <b>{affordability.projected_emi_burden_percent}%</b> of monthly income.</p><p>Estimated income remaining after EMIs and selected expenses: <b>{inr(affordability.remaining_income_after_emis)}</b>.</p><p>Calculation includes the disclosed processing fee, but no unknown lender-specific penalties.</p></div>}
        </>}
      </section>
    </section>
    {scenarios.length > 0 && <section className="scenario"><div><p className="eyebrow">WHAT IF RATES RISE?</p><h2>Your rate sensitivity</h2><p>For a floating-rate loan, the lender may adjust EMI, tenure or both. This is a cost illustration, not a forecast.</p></div><div className="scenario-bars">{scenarios.map((scenario, index) => <article key={scenario.annual_interest_rate}><span>{scenario.annual_interest_rate}%</span><div className="bar"><i style={{ width: `${Math.max(12, Number(scenario.emi) / highestScenarioEmi * 100)}%` }} /></div><b>{inr(scenario.emi)}<small>{index ? ` +${inr(scenario.additional_monthly_cost)}/mo` : " current"}</small></b></article>)}</div></section>}
    <footer id="disclaimer"><b>LoanWise AI</b><p>This tool provides educational and decision-support analysis. It does not guarantee loan approval and does not replace professional financial advice.</p></footer>
  </main>;
}

export default App;
