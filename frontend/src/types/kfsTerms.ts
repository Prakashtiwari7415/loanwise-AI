export interface TermExplanation {
  id: string;
  term: string;
  category: "understand" | "check" | "condition";
  whatItMeans: string;
  whyItMatters: string;
  whatToCheck: string;
}

export const KFS_TERMS_DICTIONARY: Record<string, TermExplanation> = {
  loan_amount: {
    id: "loan_amount",
    term: "Sanctioned Loan Amount (Principal)",
    category: "understand",
    whatItMeans:
      "The exact amount of money the lender approves and disburses to you or the seller.",
    whyItMatters:
      "Interest is charged on this remaining balance every single month. Any processing fee is often deducted upfront from this amount before disbursement.",
    whatToCheck:
      "Confirm whether the sanctioned amount matches your quotation or whether the lender deducted fees, credit insurance, or documentation charges from the disbursement.",
  },
  interest_rate: {
    id: "interest_rate",
    term: "Interest Rate & Calculation Type",
    category: "understand",
    whatItMeans:
      "The annual percentage fee charged on the borrowed money. It should be based on a reducing monthly balance.",
    whyItMatters:
      "A difference of just 0.5% in interest rate can cost you tens of thousands of rupees over a 5-year loan.",
    whatToCheck:
      "Verify whether the rate is fixed or floating, and confirm it is calculated on monthly reducing balance, not a deceptive 'flat' rate.",
  },
  rate_type: {
    id: "rate_type",
    term: "Fixed vs Floating Rate",
    category: "check",
    whatItMeans:
      "A fixed rate remains constant throughout the loan. A floating rate changes whenever the underlying benchmark (such as the RBI Repo Rate) moves.",
    whyItMatters:
      "If you choose a floating rate, an increase in central bank interest rates can either increase your monthly EMI or extend your repayment tenure.",
    whatToCheck:
      "Ask the lender which external benchmark the loan is tied to (e.g., Repo Linked Lending Rate / EBLR) and check the reset frequency (quarterly or monthly).",
  },
  apr: {
    id: "apr",
    term: "Annual Percentage Rate (APR)",
    category: "understand",
    whatItMeans:
      "The total annual cost of borrowing expressed as a single percentage, including the interest rate PLUS all mandatory fees, documentation, and processing charges.",
    whyItMatters:
      "APR is the single truest measure of a loan's cost. A loan with 8.5% interest rate + 2% processing fee may actually have a higher APR than an 8.75% loan with zero fees.",
    whatToCheck:
      "RBI mandates that every lender must clearly disclose the APR in the KFS. If APR is missing or higher than the interest rate, check what extra fees are included.",
  },
  emi: {
    id: "emi",
    term: "Equated Monthly Installment (EMI)",
    category: "understand",
    whatItMeans:
      "The fixed amount you must pay the lender on a specified date each month until the loan is fully repaid.",
    whyItMatters:
      "Each EMI contains both principal repayment and interest. Missing an EMI damages your credit score (CIBIL) and triggers penal charges.",
    whatToCheck:
      "Verify the EMI due date and make sure your monthly salary account has sufficient balance at least 2 days prior to the auto-debit (NACH/e-mandate).",
  },
  processing_fee: {
    id: "processing_fee",
    term: "Processing Fee & Upfront Charges",
    category: "check",
    whatItMeans:
      "A one-time non-refundable fee charged by the bank or NBFC to process and verify your loan application.",
    whyItMatters:
      "Processing fees can range from ₹1,000 to 2% of the loan amount plus 18% GST, directly reducing the net funds you receive.",
    whatToCheck:
      "Ask if the processing fee can be discounted or waived, especially during festive offers, and verify whether GST (18%) is included or extra.",
  },
  prepayment_foreclosure: {
    id: "prepayment_foreclosure",
    term: "Prepayment & Foreclosure Conditions",
    category: "check",
    whatItMeans:
      "Prepayment means paying extra money towards your loan before the due date. Foreclosure means closing the entire loan early in one lump sum.",
    whyItMatters:
      "Prepaying allows you to drastically cut down your total interest burden and exit the debt years ahead of schedule.",
    whatToCheck:
      "Under RBI regulations, individual borrowers with floating rate loans CANNOT be charged any foreclosure or prepayment penalties. If the document lists a fee, challenge it.",
  },
  penal_charges: {
    id: "penal_charges",
    term: "Penal Charges for Late Payment",
    category: "check",
    whatItMeans:
      "Charges imposed by the lender if you fail to pay your EMI on time.",
    whyItMatters:
      "Per recent RBI Fair Lending guidelines (2024), lenders can ONLY levy reasonable 'penal charges' and CANNOT compound them into interest.",
    whatToCheck:
      "Check the exact penal charge amount or percentage and confirm that the lender does not capitalize penal interest into your principal balance.",
  },
  tenure: {
    id: "tenure",
    term: "Loan Tenure (Duration)",
    category: "understand",
    whatItMeans:
      "The total period over which you agree to repay the loan, usually expressed in months or years.",
    whyItMatters:
      "A longer tenure reduces your monthly EMI but significantly increases the total interest you pay over the life of the loan.",
    whatToCheck:
      "Choose the shortest tenure whose monthly EMI you can comfortably afford (under 30-40% of your take-home pay) to minimize interest drain.",
  },
  cooling_off: {
    id: "cooling_off",
    term: "Cooling-Off / Look-Up Period",
    category: "check",
    whatItMeans:
      "A mandatory regulatory window (typically 1 to 3 days) during which you can cancel the loan without paying any exit penalty.",
    whyItMatters:
      "If you find a better offer or change your mind right after sanction, the cooling-off period lets you walk away by simply returning the principal and proportionate interest.",
    whatToCheck:
      "Look for the cooling-off period clause in the KFS and verify how many days you have and the exact process to cancel.",
  },
};
