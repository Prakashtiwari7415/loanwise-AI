export type LoanSummary = {
  emi: string;
  total_interest: string;
  total_repayment: string;
  processing_fee: string;
  other_charges: string;
  total_borrowing_cost: string;
};

export type Affordability = {
  score: number;
  classification: string;
  current_emi_burden_percent: string;
  projected_emi_burden_percent: string;
  remaining_income_after_emis: string;
  reasons: string[];
  risks: string[];
  assumptions: string[];
};

export type RateScenario = {
  annual_interest_rate: string;
  emi: string;
  total_interest: string;
  additional_monthly_cost: string;
  additional_total_interest: string;
};

const rawEnvUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim();
const defaultBase =
  typeof window !== "undefined" && window.location?.hostname
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : "http://localhost:8000";
const API_BASE = (rawEnvUrl && rawEnvUrl.length > 0 ? rawEnvUrl : defaultBase).replace(/\/+$/, "");

async function post<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? "Unable to calculate. Please check your inputs.");
  }
  return response.json() as Promise<T>;
}

export function calculateLoan(payload: Record<string, number>) {
  return post<LoanSummary>("/api/v1/loans/calculate", payload);
}

export function calculateAffordability(payload: Record<string, number>) {
  return post<Affordability>("/api/v1/loans/affordability", payload);
}

export function calculateScenarios(payload: Record<string, unknown>) {
  return post<RateScenario[]>("/api/v1/loans/scenario", payload);
}

export type LoanContext = {
  loan_amount?: number;
  annual_interest_rate?: number;
  tenure_months?: number;
  processing_fee?: number;
  other_charges?: number;
  monthly_income?: number;
  existing_emis?: number;
  estimated_monthly_expenses?: number;
};

export type AssistantChatRequest = {
  message: string;
  loan_context?: LoanContext;
};

export type SourceCitation = {
  title: string;
  url?: string | null;
  publisher: string;
  source_type: "regulatory" | "lender_disclosure" | "educational" | string;
  excerpt?: string | null;
  published_date?: string | null;
  verified_date?: string | null;
  is_potentially_stale?: boolean;
};

export type AssistantChatResponse = {
  headline: string;
  message: string;
  advantages: string[];
  risks: string[];
  recommended_action: string;
  assumptions: string[];
  tool_calls_used: string[];
  needs_more_information: boolean;
  sources?: SourceCitation[];
};

export function sendAssistantMessage(payload: AssistantChatRequest) {
  return post<AssistantChatResponse>("/api/v1/assistant/chat", payload);
}

export type DocumentField = {
  value: string | null;
  confidence: "high" | "medium" | "needs_review" | "not_found" | string;
  page_number?: number | null;
};

export type DocumentAnalysisResponse = {
  filename: string;
  extracted_fields: {
    lender?: DocumentField;
    loan_amount?: DocumentField;
    interest_rate?: DocumentField;
    tenure?: DocumentField;
    emi?: DocumentField;
    processing_fee?: DocumentField;
    other_charges?: DocumentField;
    apr?: DocumentField;
    rate_type?: DocumentField;
    prepayment_terms?: DocumentField;
    foreclosure_terms?: DocumentField;
    [key: string]: DocumentField | undefined;
  };
  warnings: string[];
  disclaimer: string;
};

export async function uploadAndAnalyzeDocument(file: File): Promise<DocumentAnalysisResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE}/api/v1/documents/analyze`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? "Failed to analyze document.");
  }
  return response.json() as Promise<DocumentAnalysisResponse>;
}

export type OfferToCompare = {
  lender: string;
  loan_amount: number;
  annual_interest_rate: number;
  tenure_months: number;
  processing_fee: number;
  other_charges: number;
  rate_type?: "fixed" | "floating";
};

export type CompareRecommendation = {
  lender: string;
  score: number;
  reasons: string[];
  risks: string[];
  assumptions: string[];
};

export function compareLoans(offers: OfferToCompare[], objective: string = "lowest_total_cost") {
  return post<CompareRecommendation>("/api/v1/loans/compare", {
    offers,
    objective,
  });
}
