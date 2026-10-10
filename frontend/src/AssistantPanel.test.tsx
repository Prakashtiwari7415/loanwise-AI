import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AssistantPanel } from "./AssistantPanel";
import * as api from "./api";

// Mock scrollIntoView which is not implemented in jsdom
window.HTMLElement.prototype.scrollIntoView = vi.fn();

describe("AssistantPanel", () => {
  const dummyContext = {
    loan_amount: 900000,
    annual_interest_rate: 9.25,
    tenure_months: 60,
    processing_fee: 4999,
    other_charges: 0,
    monthly_income: 90000,
    existing_emis: 5000,
    estimated_monthly_expenses: 30000,
  };

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders assistant header, subtitle, and suggested questions", () => {
    render(<AssistantPanel loanContext={dummyContext} />);

    expect(screen.getByText("LoanWise AI Assistant")).toBeDefined();
    expect(screen.getByText("Understand your loan. Explore better decisions.")).toBeDefined();
    expect(screen.getByText("Explain my current EMI.")).toBeDefined();
    expect(screen.getByText("What happens if interest rates rise by 1%?")).toBeDefined();
    expect(screen.getByRole("textbox", { name: /Ask LoanWise AI Assistant/i })).toBeDefined();
  });

  it("submits a message when a suggested question is clicked and displays structured response", async () => {
    const mockResponse: api.AssistantChatResponse = {
      headline: "Monthly EMI is ₹18,806.00",
      message: "At 9.25% interest rate for 60 months, your calculated EMI is ₹18,806.00.",
      advantages: ["Predictable monthly reducing payments", "Manageable term"],
      risks: ["Floating rate adjustments if rates rise"],
      recommended_action: "Review potential prepayment options after year 1.",
      assumptions: ["Based on disclosed 9.25% annual rate."],
      tool_calls_used: ["calculate_emi"],
      needs_more_information: false,
    };

    const sendSpy = vi.spyOn(api, "sendAssistantMessage").mockResolvedValue(mockResponse);

    render(<AssistantPanel loanContext={dummyContext} />);

    // Click suggested question
    const suggestedBtn = screen.getByText("Explain my current EMI.");
    fireEvent.click(suggestedBtn);

    // Verify spy was called with current loan context
    await waitFor(() => {
      expect(sendSpy).toHaveBeenCalledWith({
        message: "Explain my current EMI.",
        loan_context: dummyContext,
      });
    });

    // Verify structured response elements are rendered
    await waitFor(() => {
      expect(screen.getByText("Monthly EMI is ₹18,806.00")).toBeDefined();
      expect(screen.getByText(/Used financial tool:/i)).toBeDefined();
      expect(screen.getByText(/EMI & Borrowing Cost Engine/i)).toBeDefined();
      expect(screen.getByText(/At 9.25% interest rate/i)).toBeDefined();
      expect(screen.getByText(/Predictable monthly reducing payments/i)).toBeDefined();
      expect(screen.getByText(/Floating rate adjustments if rates rise/i)).toBeDefined();
      expect(screen.getByText(/Review potential prepayment options/i)).toBeDefined();
      expect(screen.getByText(/Based on disclosed 9.25% annual rate/i)).toBeDefined();
    });
  });

  it("allows custom typing and submitting via Send button", async () => {
    const mockResponse: api.AssistantChatResponse = {
      headline: "Prepayment Analysis",
      message: "Prepaying ₹1,00,000 saves ₹24,000 in interest.",
      advantages: ["Interest savings"],
      risks: [],
      recommended_action: "Ensure no foreclosure penalties apply.",
      assumptions: ["Zero penalty assumed."],
      tool_calls_used: ["simulate_prepayment"],
      needs_more_information: false,
    };

    const sendSpy = vi.spyOn(api, "sendAssistantMessage").mockResolvedValue(mockResponse);

    render(<AssistantPanel loanContext={dummyContext} />);

    const textarea = screen.getByRole("textbox", { name: /Ask LoanWise AI Assistant/i });
    fireEvent.change(textarea, { target: { value: "Can I save by prepaying 1 lakh?" } });

    const sendButton = screen.getByRole("button", { name: /Send message/i });
    expect(sendButton).not.toHaveProperty("disabled", true);
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(sendSpy).toHaveBeenCalledWith({
        message: "Can I save by prepaying 1 lakh?",
        loan_context: dummyContext,
      });
    });

    await waitFor(() => {
      expect(screen.getByText("Prepayment Analysis")).toBeDefined();
      expect(screen.getByText(/Prepayment Schedule Simulation/i)).toBeDefined();
    });

  });

  it("displays friendly error message and allows retry when API fails", async () => {
    const sendSpy = vi.spyOn(api, "sendAssistantMessage")
      .mockRejectedValueOnce(new Error("503 Missing or invalid API key"));

    render(<AssistantPanel loanContext={dummyContext} />);

    const textarea = screen.getByRole("textbox", { name: /Ask LoanWise AI Assistant/i });
    fireEvent.change(textarea, { target: { value: "Will rates rise?" } });

    const sendButton = screen.getByRole("button", { name: /Send message/i });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(screen.getByText(/Gemini API key is not configured/i)).toBeDefined();
      expect(screen.getByText(/Retry Question/i)).toBeDefined();
    });

    // Mock success on retry
    const successResponse: api.AssistantChatResponse = {
      headline: "Rate Sensitivity Result",
      message: "A 1% hike increases EMI by ₹450/month.",
      advantages: [],
      risks: ["Higher monthly outgo"],
      recommended_action: "Consider a fixed rate if budget is tight.",
      assumptions: ["Illustrative scenario."],
      tool_calls_used: ["simulate_rate_change"],
      needs_more_information: false,
    };
    sendSpy.mockResolvedValueOnce(successResponse);

    const retryButton = screen.getByText(/Retry Question/i);
    fireEvent.click(retryButton);

    await waitFor(() => {
      expect(screen.getByText("Rate Sensitivity Result")).toBeDefined();
    });
  });

  it("renders grounded source citations with clickable links, publisher, and type badge", async () => {
    const mockResponseWithSources: api.AssistantChatResponse = {
      headline: "RBI KFS Disclosure Mandate",
      message: "According to RBI guidelines, all retail loan offers must include a Key Fact Statement.",
      advantages: ["Clear upfront APR disclosure"],
      risks: ["Verify all fees"],
      recommended_action: "Examine the KFS before signing the sanction letter.",
      assumptions: ["Based on RBI directions 2024."],
      tool_calls_used: [],
      needs_more_information: false,
      sources: [
        {
          title: "RBI Directions on Key Fact Statement (KFS) for Retail and MSME Term Loans",
          url: "https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12658&Mode=0",
          publisher: "Reserve Bank of India",
          source_type: "regulatory",
          excerpt: "All Regulated Entities must provide a standardized Key Fact Statement (KFS) to retail borrowers.",
          published_date: "2024-04-15",
          verified_date: "2024-10-01",
          is_potentially_stale: false,
        },
      ],
    };

    vi.spyOn(api, "sendAssistantMessage").mockResolvedValue(mockResponseWithSources);

    render(<AssistantPanel loanContext={dummyContext} />);

    const textarea = screen.getByRole("textbox", { name: /Ask LoanWise AI Assistant/i });
    fireEvent.change(textarea, { target: { value: "What does RBI mandate about KFS?" } });

    const sendBtn = screen.getByRole("button", { name: /Send message/i });
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(screen.getByText("RBI KFS Disclosure Mandate")).toBeDefined();
      expect(screen.getByText("Verified Regulatory & Research Sources")).toBeDefined();
      expect(screen.getByText("Regulatory Mandate")).toBeDefined();
      expect(screen.getByText("Reserve Bank of India")).toBeDefined();
      expect(screen.getByText("Verified: 2024-10-01")).toBeDefined();
      expect(screen.getByText(/All Regulated Entities must provide a standardized Key Fact Statement/i)).toBeDefined();
    });

    const link = screen.getByRole("link", { name: /RBI Directions on Key Fact Statement/i });
    expect(link.getAttribute("href")).toBe("https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12658&Mode=0");
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toContain("noopener");
  });

  it("displays warning banner when citation is flagged as potentially stale", async () => {
    const mockStaleResponse: api.AssistantChatResponse = {
      headline: "SBI Auto Loan Schedule",
      message: "SBI car loan processing fee is typically 0.25% to 0.75%.",
      advantages: [],
      risks: ["Lender fee waivers vary"],
      recommended_action: "Verify current fee waivers directly with SBI.",
      assumptions: [],
      tool_calls_used: [],
      needs_more_information: false,
      sources: [
        {
          title: "State Bank of India: Retail Auto Loan Schedule of Fees",
          url: "https://sbi.co.in/web/personal-banking/loans/auto-loans",
          publisher: "State Bank of India",
          source_type: "lender_disclosure",
          excerpt: "Standard processing fee is 0.25% to 0.75% of sanctioned loan amount.",
          published_date: "2024-01-01",
          verified_date: "2024-05-15",
          is_potentially_stale: true,
        },
      ],
    };

    vi.spyOn(api, "sendAssistantMessage").mockResolvedValue(mockStaleResponse);

    render(<AssistantPanel loanContext={dummyContext} />);

    const textarea = screen.getByRole("textbox", { name: /Ask LoanWise AI Assistant/i });
    fireEvent.change(textarea, { target: { value: "What are SBI processing fees?" } });

    const sendBtn = screen.getByRole("button", { name: /Send message/i });
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(screen.getByText("Lender Disclosure")).toBeDefined();
      expect(screen.getByText(/Notice:/i)).toBeDefined();
      expect(screen.getByText(/Verification date is older than 90 days/i)).toBeDefined();
    });
  });
});
