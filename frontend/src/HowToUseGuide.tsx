import { useState } from "react";

interface GuideStep {
  stepNumber: number;
  title: string;
  subtitle: string;
  summary: string;
  bulletPoints: string[];
  exampleLabel: string;
  exampleData: {
    title: string;
    items: { label: string; value: string; note?: string }[];
  };
  tip: string;
  targetAnchor: string;
  actionText: string;
}

const GUIDE_STEPS: GuideStep[] = [
  {
    stepNumber: 1,
    title: "Step 1 — Choose your loan type",
    subtitle: "Car, Home, Personal, Education, or Two-Wheeler",
    summary:
      "Every loan serves a different need with its own rules, customary tenures, and interest dynamics. Start by choosing the type of loan you are planning to take.",
    bulletPoints: [
      "Select from 6 common categories: Personal, Home, Car, Education, Two-Wheeler, or General.",
      "LoanWise automatically adapts the default numbers, tenure limits, and guidance to match your choice.",
      "We honestly indicate which loan types are fully supported versus those needing specialized schedules (like education loan study moratoriums).",
    ],
    exampleLabel: "ILLUSTRATIVE EXAMPLE",
    exampleData: {
      title: "Category Selection",
      items: [
        { label: "Chosen Category", value: "Car Loan" },
        { label: "Typical Tenure", value: "3 to 7 years (36 to 84 months)" },
        { label: "Interest Structure", value: "Fixed or Floating reducing balance" },
      ],
    },
    tip: "You can change your selected loan category at any time without losing other information.",
    targetAnchor: "#explore-loans",
    actionText: "Try it: Select a loan category",
  },
  {
    stepNumber: 2,
    title: "Step 2 — Enter your details",
    subtitle: "Amount, down payment, interest rate, and tenure",
    summary:
      "Enter the loan terms you were offered or are planning for. If you don't know the exact interest rate yet, use the sensible market defaults provided.",
    bulletPoints: [
      "Asset Price & Down Payment: For car or home loans, the loan amount is the asset price minus your down payment.",
      "Annual Interest Rate: Always ensure this is the annual reducing balance rate, not a flat monthly rate.",
      "Tenure: The number of months you will take to pay off the loan.",
      "Monthly Income & EMIs: Used to calculate your Debt-to-Income / Affordability score safely.",
    ],
    exampleLabel: "ILLUSTRATIVE EXAMPLE",
    exampleData: {
      title: "Sample Input Terms",
      items: [
        { label: "Car on-road price", value: "₹12,00,000" },
        { label: "Down payment (25%)", value: "₹3,00,000" },
        { label: "Calculated Loan Amount", value: "₹9,00,000" },
        { label: "Annual Rate & Tenure", value: "9.25% for 60 months (5 yrs)" },
      ],
    },
    tip: "Look at your sanction letter, quote sheet, or Key Fact Statement (KFS) to find these exact numbers.",
    targetAnchor: "#calculator-section",
    actionText: "Try it: Enter your numbers",
  },
  {
    stepNumber: 3,
    title: "Step 3 — Understand the real borrowing cost",
    subtitle: "EMI, total interest, fees, and affordability",
    summary:
      "Never look only at the monthly EMI. The total cost of borrowing includes all the interest accumulated over the years plus upfront bank processing fees.",
    bulletPoints: [
      "Monthly EMI: What you will actually pay the bank every single month.",
      "Total Interest: The extra money the bank makes from lending to you over the full loan duration.",
      "Total Borrowing Cost: Principal + Total Interest + Disclosed Processing Fees.",
      "LoanWise Score: Evaluates whether the proposed EMI fits comfortably inside your monthly take-home income (FOIR < 40-50%).",
    ],
    exampleLabel: "ILLUSTRATIVE EXAMPLE",
    exampleData: {
      title: "Calculation Breakdown",
      items: [
        { label: "Monthly EMI", value: "₹18,806", note: "Deterministic calculation" },
        { label: "Total Interest Paid", value: "₹2,28,360", note: "Over 5 years" },
        { label: "Upfront Processing Fee", value: "₹4,999", note: "One-time bank fee" },
        { label: "Total Money Repaid", value: "₹11,33,359", note: "Principal + Interest + Fee" },
      ],
    },
    tip: "A lower EMI over a longer tenure usually costs thousands more in total interest. Always check total cost!",
    targetAnchor: "#decision-view",
    actionText: "Try it: See loan cost breakdown",
  },
  {
    stepNumber: 4,
    title: "Step 4 — Compare offers side-by-side",
    subtitle: "Why the lowest EMI does not always mean the cheapest loan",
    summary:
      "Lenders package loans differently. A lender offering a smaller monthly EMI might simply be stretching your tenure, which drastically increases the total interest you pay.",
    bulletPoints: [
      "Compare two offers with identical loan amounts to see the real winner.",
      "Compare processing fees: a loan with 0.25% lower interest might charge an exorbitant 2% upfront fee that negates the savings.",
      "Inspect fixed vs floating: floating rate loans may start lower but increase if RBI repo rates rise.",
    ],
    exampleLabel: "ILLUSTRATIVE EXAMPLE",
    exampleData: {
      title: "Comparison Sample",
      items: [
        { label: "Bank A (5 years @ 9.25%)", value: "EMI ₹18,806", note: "Total Cost: ₹11.33L" },
        { label: "Bank B (7 years @ 9.50%)", value: "EMI ₹14,710", note: "Total Cost: ₹12.40L" },
        { label: "Winner", value: "Bank A saves ₹1,07,000", note: "Despite higher monthly EMI!" },
      ],
    },
    tip: "Use the Offer Comparison tool below to test your actual bank quotations side-by-side.",
    targetAnchor: "#compare-section",
    actionText: "Try it: Compare loan offers",
  },
  {
    stepNumber: 5,
    title: "Step 5 — Upload your Key Fact Statement (KFS)",
    subtitle: "Let LoanWise verify and explain your bank document",
    summary:
      "RBI mandates that every bank and NBFC in India must provide a standardized 1-2 page Key Fact Statement (KFS) before you sign a loan agreement.",
    bulletPoints: [
      "Drop your PDF: LoanWise securely extracts sanctioned amount, interest rate, APR, tenure, and fees.",
      "Plain Language Translation: We translate every complex legal clause into everyday language.",
      "Confidence Badges: Every extracted field is tagged with HIGH, MEDIUM, or NEEDS REVIEW confidence.",
      "Missing Terms Detected: If the document is missing APR or cooling-off clauses, LoanWise highlights it.",
    ],
    exampleLabel: "ILLUSTRATIVE EXAMPLE",
    exampleData: {
      title: "Document Intelligence",
      items: [
        { label: "Extracted APR", value: "9.85%", note: "Verified against disclosed fees" },
        { label: "Foreclosure Clause", value: "Nil charges", note: "Complies with RBI floating rate rule" },
        { label: "Cooling-Off Period", value: "3 days", note: "Time to exit without penalty" },
      ],
    },
    tip: "Your uploaded document is processed in memory and never shared or added to any public corpus.",
    targetAnchor: "#kfs-section",
    actionText: "Try it: Upload a KFS PDF",
  },
  {
    stepNumber: 6,
    title: "Step 6 — Review risks and make an informed decision",
    subtitle: "Check rate rises, prepayment options, and penalties",
    summary:
      "Before signing the sanction letter, review what happens if things change down the road: interest rate hikes, job changes, or early repayment.",
    bulletPoints: [
      "Rate Sensitivity: See how much your monthly EMI would increase if the interest rate rises by +1% or +2%.",
      "Prepayment Simulator: Check how much interest you can save by paying an extra lump sum early.",
      "Prepare Questions for Lender: Use our 1-click generator to get critical questions to ask the loan manager before signing.",
      "AI Assistant Helper: Ask any doubt about regulatory rights, RBI circulars, or fee disclosures.",
    ],
    exampleLabel: "ILLUSTRATIVE EXAMPLE",
    exampleData: {
      title: "Risk Check",
      items: [
        { label: "If Rates Rise +1.5%", value: "+₹722/month", note: "Adds ₹43,300 over remaining tenure" },
        { label: "Lump Sum Prepayment of ₹1L", value: "Saves ₹34,200", note: "And cuts tenure by 7 months" },
        { label: "Cooling-off Rights", value: "Right to cancel", note: "Return principal with zero penalty" },
      ],
    },
    tip: "Take your time. Never sign a loan sanction letter under pressure or without an official KFS.",
    targetAnchor: "#assistant-panel-section",
    actionText: "Try it: Ask the AI Assistant",
  },
];

interface HowToUseGuideProps {
  onClose?: () => void;
  onNavigateToSection?: (selector: string) => void;
}

export function HowToUseGuide({ onClose, onNavigateToSection }: HowToUseGuideProps) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  const step = GUIDE_STEPS[currentStepIndex];
  const totalSteps = GUIDE_STEPS.length;
  const isFirst = currentStepIndex === 0;
  const isLast = currentStepIndex === totalSteps - 1;

  function handleNavigate(targetAnchor: string) {
    if (onNavigateToSection) {
      onNavigateToSection(targetAnchor);
    } else {
      const el = document.querySelector(targetAnchor);
      if (el) {
        el.scrollIntoView({ behavior: "smooth" });
      }
    }
    onClose?.();
  }

  return (
    <section className="guide-modal-card" id="how-to-use-guide" aria-label="How to use LoanWise Guide">
      <div className="guide-header">
        <div>
          <div className="guide-step-tag">
            <span>BEGINNER'S GUIDE</span>
            <b>
              Step {step.stepNumber} of {totalSteps}
            </b>
          </div>
          <h2 className="guide-title">{step.title}</h2>
          <p className="guide-subtitle">{step.subtitle}</p>
        </div>

        {onClose && (
          <button
            type="button"
            className="guide-close-btn"
            onClick={onClose}
            aria-label="Close how to use guide"
          >
            ✕ Close Guide
          </button>
        )}
      </div>

      {/* Progress Bar */}
      <div className="guide-progress-bar" role="progressbar" aria-valuenow={step.stepNumber} aria-valuemin={1} aria-valuemax={totalSteps}>
        <div
          className="guide-progress-fill"
          style={{ width: `${(step.stepNumber / totalSteps) * 100}%` }}
        />
      </div>

      {/* Step Indicators */}
      <div className="guide-step-dots" role="tablist" aria-label="Guide Steps">
        {GUIDE_STEPS.map((s, idx) => (
          <button
            key={s.stepNumber}
            type="button"
            className={`step-dot-btn ${idx === currentStepIndex ? "dot-active" : ""} ${
              idx < currentStepIndex ? "dot-completed" : ""
            }`}
            onClick={() => setCurrentStepIndex(idx)}
            aria-label={`Jump to ${s.title}`}
            role="tab"
            aria-selected={idx === currentStepIndex}
          >
            <span>{s.stepNumber}</span>
          </button>
        ))}
      </div>

      {/* Main Content Layout */}
      <div className="guide-body-grid">
        <div className="guide-text-col">
          <p className="guide-summary">{step.summary}</p>

          <ul className="guide-bullets">
            {step.bulletPoints.map((bp, i) => (
              <li key={i}>{bp}</li>
            ))}
          </ul>

          <div className="guide-tip-box">
            <strong>💡 Helpful Tip:</strong>
            <p>{step.tip}</p>
          </div>
        </div>

        {/* Visual Example Card */}
        <div className="guide-visual-col">
          <div className="guide-example-card">
            <div className="example-card-header">
              <span className="example-badge">{step.exampleLabel}</span>
              <h4>{step.exampleData.title}</h4>
            </div>

            <div className="example-items-list">
              {step.exampleData.items.map((item, i) => (
                <div key={i} className="example-item-row">
                  <span className="item-label">{item.label}</span>
                  <div className="item-right">
                    <strong className="item-val">{item.value}</strong>
                    {item.note && <small className="item-note">{item.note}</small>}
                  </div>
                </div>
              ))}
            </div>

            <div className="example-card-footer">
              <button
                type="button"
                className="guide-try-btn"
                onClick={() => handleNavigate(step.targetAnchor)}
              >
                {step.actionText} ↗
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Navigation Controls */}
      <div className="guide-footer-controls">
        <div className="guide-left-actions">
          <button
            type="button"
            className="guide-nav-btn btn-prev"
            disabled={isFirst}
            onClick={() => setCurrentStepIndex((prev) => Math.max(0, prev - 1))}
          >
            ← Previous Step
          </button>

          {!isLast && (
            <button
              type="button"
              className="guide-skip-btn"
              onClick={() => handleNavigate("#explore-loans")}
            >
              Skip guide
            </button>
          )}
        </div>

        <div className="guide-right-actions">
          {!isLast ? (
            <button
              type="button"
              className="guide-nav-btn btn-next"
              onClick={() => setCurrentStepIndex((prev) => Math.min(totalSteps - 1, prev + 1))}
            >
              Next Step: {GUIDE_STEPS[currentStepIndex + 1]?.title.split("—")[1]?.trim() ?? "Next"} →
            </button>
          ) : (
            <button
              type="button"
              className="guide-nav-btn btn-finish"
              onClick={() => handleNavigate("#explore-loans")}
            >
              Start exploring LoanWise AI →
            </button>
          )}
        </div>
      </div>
    </section>
  );
}
