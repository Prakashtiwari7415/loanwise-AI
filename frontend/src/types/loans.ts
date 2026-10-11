export type LoanCategoryId =
  | "car"
  | "home"
  | "personal"
  | "education"
  | "two_wheeler"
  | "other";

export type SupportLevel = "full" | "partial" | "general";

export interface LoanCategoryConfig {
  id: LoanCategoryId;
  name: string;
  tagline: string;
  icon: string;
  supportLevel: SupportLevel;
  supportBadge: string;
  supportExplanation: string;
  whatTheEngineDoes: string;
  defaultValues: {
    assetPrice: number;
    downPayment: number;
    income: number;
    existingEmis: number;
    expenses: number;
    interestRate: number;
    tenure: number;
    processingFee: number;
  };
  fieldLabels: {
    assetPrice: string;
    assetPriceHelp: string;
    downPayment: string;
    downPaymentHelp: string;
    interestRateHelp: string;
    tenureHelp: string;
    tenureMinMonths: number;
    tenureMaxMonths: number;
    tenureStepMonths: number;
    hasDownPayment: boolean;
  };
  educationalTips: string[];
}

export const LOAN_CATEGORIES: Record<LoanCategoryId, LoanCategoryConfig> = {
  car: {
    id: "car",
    name: "Car Loan",
    tagline: "For new or pre-owned four-wheelers",
    icon: "🚗",
    supportLevel: "full",
    supportBadge: "Fully Supported",
    supportExplanation:
      "Full calculation of reducing balance EMI, processing fees, down payments, rate-rise sensitivity, and prepayment savings.",
    whatTheEngineDoes:
      "Calculates monthly EMI, total interest, and total cost of borrowing using standard monthly reducing balance. Simulates RBI foreclosure rules for floating rate car loans.",
    defaultValues: {
      assetPrice: 1200000,
      downPayment: 300000,
      income: 90000,
      existingEmis: 5000,
      expenses: 30000,
      interestRate: 9.25,
      tenure: 60,
      processingFee: 4999,
    },
    fieldLabels: {
      assetPrice: "Car on-road price",
      assetPriceHelp: "Total on-road price including registration, road tax, and insurance.",
      downPayment: "Down payment (margin)",
      downPaymentHelp: "Upfront amount paid from your savings (typically 15% to 25%).",
      interestRateHelp: "Annual interest rate charged by the bank or NBFC.",
      tenureHelp: "Loan repayment duration, typically between 1 and 7 years (12 to 84 months).",
      tenureMinMonths: 12,
      tenureMaxMonths: 84,
      tenureStepMonths: 12,
      hasDownPayment: true,
    },
    educationalTips: [
      "Check whether your interest quote is flat or reducing balance; a 9% flat rate can equate to nearly 16% reducing balance APR.",
      "Under RBI directions, banks cannot charge foreclosure penalties on floating-rate individual car loans.",
      "Aim for a down payment of at least 20% to avoid being underwater due to vehicle depreciation.",
    ],
  },
  home: {
    id: "home",
    name: "Home Loan",
    tagline: "For apartments, houses, construction & plots",
    icon: "🏠",
    supportLevel: "full",
    supportBadge: "Fully Supported",
    supportExplanation:
      "Supports long-tenure calculations up to 30 years (360 months), floating rate sensitivity, prepayment tenure reduction, and fee disclosures.",
    whatTheEngineDoes:
      "Simulates long-tenure reducing balance amortization. Shows how small prepayment amounts save lakhs in interest over 15 to 30 years.",
    defaultValues: {
      assetPrice: 4500000,
      downPayment: 900000,
      income: 120000,
      existingEmis: 8000,
      expenses: 40000,
      interestRate: 8.5,
      tenure: 240,
      processingFee: 10000,
    },
    fieldLabels: {
      assetPrice: "Property value",
      assetPriceHelp: "Total property agreement value plus stamp duty and registration.",
      downPayment: "Own contribution / Down payment",
      downPaymentHelp: "RBI mandates minimum 20% down payment for loans up to ₹75 lakhs (10-15% for smaller loans).",
      interestRateHelp: "Home loan rates are usually linked to an external benchmark like the RBI Repo Rate (EBLR).",
      tenureHelp: "Home loan tenure can range from 5 to 30 years (60 to 360 months).",
      tenureMinMonths: 60,
      tenureMaxMonths: 360,
      tenureStepMonths: 12,
      hasDownPayment: true,
    },
    educationalTips: [
      "Most Indian home loans are floating rate (EBLR/Repo-linked). When RBI raises repo rates, banks usually increase tenure or EMI.",
      "RBI rules strictly prohibit prepayment and foreclosure charges for individual borrowers on floating-rate home loans.",
      "Even a single extra EMI per year can reduce a 20-year home loan by 3 to 4 years.",
    ],
  },
  personal: {
    id: "personal",
    name: "Personal Loan",
    tagline: "Unsecured loan for medical, travel or personal needs",
    icon: "💼",
    supportLevel: "full",
    supportBadge: "Fully Supported",
    supportExplanation:
      "Calculates unsecured monthly reducing EMI, processing fees, affordability ratio, and total borrowing cost.",
    whatTheEngineDoes:
      "Computes total borrowing cost with upfront processing fees and verifies whether proposed EMI fits within safe income thresholds (35-45% FOIR).",
    defaultValues: {
      assetPrice: 300000,
      downPayment: 0,
      income: 70000,
      existingEmis: 3000,
      expenses: 25000,
      interestRate: 12.5,
      tenure: 36,
      processingFee: 2500,
    },
    fieldLabels: {
      assetPrice: "Loan amount required",
      assetPriceHelp: "The exact amount you need disbursed into your bank account.",
      downPayment: "Down payment (Not applicable)",
      downPaymentHelp: "Personal loans do not require down payments.",
      interestRateHelp: "Personal loan rates typically range from 10.5% to 22% based on credit score.",
      tenureHelp: "Personal loan tenure usually ranges from 12 to 60 months (1 to 5 years).",
      tenureMinMonths: 12,
      tenureMaxMonths: 60,
      tenureStepMonths: 12,
      hasDownPayment: false,
    },
    educationalTips: [
      "Personal loans are unsecured, meaning lenders charge higher interest rates than for home or car loans.",
      "Check the processing fee carefully—it is typically deducted upfront from your sanctioned loan amount.",
      "Prepayment lock-in periods of 6 to 12 months often apply to personal loans, and fixed-rate loans may have prepayment charges.",
    ],
  },
  two_wheeler: {
    id: "two_wheeler",
    name: "Two-Wheeler Loan",
    tagline: "For motorcycles, scooters & electric two-wheelers",
    icon: "🛵",
    supportLevel: "full",
    supportBadge: "Fully Supported",
    supportExplanation:
      "Supports shorter 12 to 36 month tenures, standard reducing calculations, and upfront documentation charges.",
    whatTheEngineDoes:
      "Provides clear monthly installment calculations and separates doc fees from principal so you know the genuine APR.",
    defaultValues: {
      assetPrice: 110000,
      downPayment: 25000,
      income: 45000,
      existingEmis: 0,
      expenses: 18000,
      interestRate: 11.5,
      tenure: 24,
      processingFee: 1500,
    },
    fieldLabels: {
      assetPrice: "Two-wheeler on-road price",
      assetPriceHelp: "Total showroom price plus RTO registration and insurance.",
      downPayment: "Down payment",
      downPaymentHelp: "Initial cash paid to dealership (usually 15% to 30% of on-road price).",
      interestRateHelp: "Beware of flat interest rates quoted by dealers; always ask for the reducing balance rate or APR.",
      tenureHelp: "Two-wheeler loan tenure typically ranges from 12 to 36 months (1 to 3 years).",
      tenureMinMonths: 12,
      tenureMaxMonths: 48,
      tenureStepMonths: 6,
      hasDownPayment: true,
    },
    educationalTips: [
      "Dealers often quote 'flat rates' like 6% per annum, which is equivalent to approximately 11.5% reducing rate.",
      "Ensure electric two-wheeler subsidy (such as PM E-DRIVE) is deducted before loan amount calculation.",
      "Keep the tenure as short as possible (under 3 years) to avoid paying excessive interest on a depreciating vehicle.",
    ],
  },
  education: {
    id: "education",
    name: "Education Loan",
    tagline: "For higher studies in India or abroad",
    icon: "🎓",
    supportLevel: "partial",
    supportBadge: "Partially Supported",
    supportExplanation:
      "Calculates the post-moratorium monthly repayment phase. Note: Course moratorium periods and study-phase simple interest subsidies require specialized scheduling.",
    whatTheEngineDoes:
      "Calculates the monthly EMI and interest for the active repayment period. Clearly marks that study-period grace/moratorium interest accumulation must be verified with the bank.",
    defaultValues: {
      assetPrice: 1500000,
      downPayment: 300000,
      income: 80000,
      existingEmis: 0,
      expenses: 25000,
      interestRate: 10.0,
      tenure: 84,
      processingFee: 5000,
    },
    fieldLabels: {
      assetPrice: "Total tuition & living costs",
      assetPriceHelp: "Total course fees, hostel accommodation, travel, and books.",
      downPayment: "Margin money / Family contribution",
      downPaymentHelp: "RBI guidelines typically require 0% margin for loans up to ₹4 lakhs, 5% for domestic studies, and 15% for abroad.",
      interestRateHelp: "Concessions (typically 0.5%) are often available for female students and premier institutions.",
      tenureHelp: "Repayment tenure after course completion and moratorium (typically 5 to 15 years).",
      tenureMinMonths: 24,
      tenureMaxMonths: 180,
      tenureStepMonths: 12,
      hasDownPayment: true,
    },
    educationalTips: [
      "Education loans offer a moratorium period (course duration + 6 to 12 months) before full EMI repayment starts.",
      "If you service simple interest during the moratorium period, the bank does not capitalize interest into the principal, saving you money.",
      "Interest paid on education loans is deductible under Section 80E of the Income Tax Act with no upper limit for up to 8 years.",
    ],
  },
  other: {
    id: "other",
    name: "Other Loan / Not Sure Yet",
    tagline: "Customizable parameters for any standard term loan",
    icon: "📊",
    supportLevel: "general",
    supportBadge: "General Support",
    supportExplanation:
      "Applies standard deterministic monthly reducing balance formulas. Suitable for gold loans, consumer durable loans, or general borrowing.",
    whatTheEngineDoes:
      "Provides transparent EMI, total interest, and total cost of borrowing for any custom amount, tenure, and interest rate.",
    defaultValues: {
      assetPrice: 500000,
      downPayment: 0,
      income: 75000,
      existingEmis: 5000,
      expenses: 25000,
      interestRate: 10.5,
      tenure: 48,
      processingFee: 3000,
    },
    fieldLabels: {
      assetPrice: "Estimated borrowing amount",
      assetPriceHelp: "Total funds you plan to borrow.",
      downPayment: "Down payment (if any)",
      downPaymentHelp: "Any upfront payment you are making towards the asset or goal.",
      interestRateHelp: "Expected annual interest rate.",
      tenureHelp: "Repayment duration in months.",
      tenureMinMonths: 12,
      tenureMaxMonths: 120,
      tenureStepMonths: 6,
      hasDownPayment: false,
    },
    educationalTips: [
      "Always request a Key Fact Statement (KFS) from the lender before signing any loan agreement.",
      "Compare the Annual Percentage Rate (APR), which accounts for processing fees and documentation charges, not just the nominal rate.",
      "Ensure the monthly EMI does not exceed 40% of your net monthly take-home pay.",
    ],
  },
};
