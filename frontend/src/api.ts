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

const API_BASE = import.meta.env.VITE_API_BASE_URL
  ?? `${window.location.protocol}//${window.location.hostname}:8000`;

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

export type AssistantChatResponse = {
  headline: string;
  message: string;
  advantages: string[];
  risks: string[];
  recommended_action: string;
  assumptions: string[];
  tool_calls_used: string[];
  needs_more_information: boolean;
};

export function sendAssistantMessage(payload: AssistantChatRequest) {
  return post<AssistantChatResponse>("/api/v1/assistant/chat", payload);
}
