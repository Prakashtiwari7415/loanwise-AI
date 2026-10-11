import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { KfsAnalysisSection } from "./KfsAnalysisSection";
import * as api from "./api";

describe("KfsAnalysisSection — Plain Language, Terms & Findings (Feature 2)", () => {
  const dummyActivePlan = {
    loanAmount: 800000,
    interestRate: 9.5,
    tenure: 60,
    emi: "16800.00",
    total_interest: "208000.00",
    total_borrowing_cost: "1012999.00",
  };

  const sampleKfsResponse: api.DocumentAnalysisResponse = {
    filename: "hdfc_car_kfs.pdf",
    extracted_fields: {
      lender: { value: "HDFC Bank Ltd", confidence: "high", page_number: 1 },
      loan_amount: { value: "Rs. 7,50,000", confidence: "high", page_number: 1 },
      interest_rate: { value: "9.25%", confidence: "high", page_number: 1 },
      rate_type: { value: "Floating (Repo-linked)", confidence: "high", page_number: 1 },
      tenure: { value: "60 months", confidence: "high", page_number: 1 },
      emi: { value: "Rs. 15,660", confidence: "high", page_number: 1 },
      processing_fee: { value: "Rs. 3,500", confidence: "high", page_number: 1 },
      other_charges: { value: "Rs. 500 (Doc Fee)", confidence: "medium", page_number: 2 },
      apr: { value: "9.60%", confidence: "high", page_number: 1 },
      prepayment_terms: { value: "Zero prepayment penalty after 6 months", confidence: "high", page_number: 2 },
      foreclosure_terms: { value: "Nil foreclosure charges as per RBI rules", confidence: "high", page_number: 2 },
    },
    warnings: ["Disclosed processing fee excludes GST."],
    disclaimer: "Extracted for analysis only. Verify terms with physical copy.",
  };

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders plain-language overview distinguishing extracted values from calculated estimates", async () => {
    vi.spyOn(api, "uploadAndAnalyzeDocument").mockResolvedValue(sampleKfsResponse);
    vi.spyOn(api, "calculateLoan").mockResolvedValue({
      emi: "15660.00",
      total_interest: "189600.00",
      total_repayment: "939600.00",
      processing_fee: "3500.00",
      other_charges: "500.00",
      total_borrowing_cost: "943600.00",
    });

    render(<KfsAnalysisSection activePlan={dummyActivePlan} />);

    const input = screen.getByLabelText(/Upload KFS PDF document/i);
    const pdfFile = new File(["%PDF-1.4 mock"], "hdfc_car_kfs.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [pdfFile] } });

    const analyzeBtn = await screen.findByRole("button", { name: /Analyze KFS document/i });
    fireEvent.click(analyzeBtn);

    // Verify Plain-Language Overview Card
    await waitFor(() => {
      expect(screen.getByText("PLAIN-LANGUAGE OVERVIEW")).toBeDefined();
      expect(screen.getByText("What this document means for you")).toBeDefined();
    });

    // Verify distinct badges for extracted vs calculated
    expect(screen.getAllByText("EXTRACTED VALUE").length).toBeGreaterThan(1);
    expect(screen.getAllByText("CALCULATED ESTIMATE").length).toBeGreaterThan(1);

    // Verify overview sections
    expect(screen.getByText("Amount you are borrowing")).toBeDefined();
    expect(screen.getByText(/Principal: Rs. 7,50,000/i)).toBeDefined();
    expect(screen.getByText("Estimated monthly EMI")).toBeDefined();
    expect(screen.getByText("Total repayment")).toBeDefined();
    expect(screen.getByText("Additional charges disclosed")).toBeDefined();
    expect(screen.getByText("Important things to check")).toBeDefined();
  });

  it("explains terms using 3 pillars (What it means, Why it matters, What to check)", async () => {
    vi.spyOn(api, "uploadAndAnalyzeDocument").mockResolvedValue(sampleKfsResponse);

    render(<KfsAnalysisSection activePlan={dummyActivePlan} />);

    const input = screen.getByLabelText(/Upload KFS PDF document/i);
    const pdfFile = new File(["%PDF-1.4 mock"], "hdfc_car_kfs.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [pdfFile] } });

    const analyzeBtn = await screen.findByRole("button", { name: /Analyze KFS document/i });
    fireEvent.click(analyzeBtn);

    await waitFor(() => {
      expect(screen.getByText("BEGINNER'S GLOSSARY")).toBeDefined();
    });

    // Click on APR term chip
    const aprChip = screen.getByRole("button", { name: /Annual Percentage Rate \(APR\)/i });
    fireEvent.click(aprChip);

    // Check 3 pillars rendered
    expect(screen.getByText("1. WHAT IT MEANS")).toBeDefined();
    expect(screen.getByText("2. WHY IT MATTERS")).toBeDefined();
    expect(screen.getByText("3. WHAT TO CHECK / ASK")).toBeDefined();
    expect(screen.getByText(/APR is the single truest measure of a loan's cost/i)).toBeDefined();
  });

  it("displays findings with category tabs and generates 5 critical lender questions", async () => {
    vi.spyOn(api, "uploadAndAnalyzeDocument").mockResolvedValue(sampleKfsResponse);

    render(<KfsAnalysisSection activePlan={dummyActivePlan} />);

    const input = screen.getByLabelText(/Upload KFS PDF document/i);
    const pdfFile = new File(["%PDF-1.4 mock"], "hdfc_car_kfs.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [pdfFile] } });

    const analyzeBtn = await screen.findByRole("button", { name: /Analyze KFS document/i });
    fireEvent.click(analyzeBtn);

    await waitFor(() => {
      expect(screen.getByText("Document Findings & Checkpoints")).toBeDefined();
    });

    // Check ethical disclaimer
    expect(
      screen.getByText(/We do not declare lenders or loans as fraudulent or bad based on document extraction/i)
    ).toBeDefined();

    // Click "Help me prepare questions for the lender"
    const prepareQBtn = screen.getByRole("button", {
      name: /Help me prepare questions for the lender/i,
    });
    fireEvent.click(prepareQBtn);

    // Verify 5 questions checklist
    expect(
      screen.getByText("5 Critical Questions to Ask Your Loan Officer Before Signing")
    ).toBeDefined();
    expect(screen.getByText(/Rate Type & Calculation:/i)).toBeDefined();
    expect(screen.getByText(/Benchmark & Reset:/i)).toBeDefined();
    expect(screen.getByText(/Prepayment & Foreclosure Charges:/i)).toBeDefined();
    expect(screen.getByText(/Upfront Deductions:/i)).toBeDefined();
    expect(screen.getByText(/Cooling-off Period:/i)).toBeDefined();
  });
});
