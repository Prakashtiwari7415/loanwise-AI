import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { KfsAnalysisSection } from "./KfsAnalysisSection";
import * as api from "./api";

describe("KfsAnalysisSection", () => {
  const dummyActivePlan = {
    loanAmount: 900000,
    interestRate: 9.25,
    tenure: 60,
    emi: "18806.00",
    total_interest: "228360.00",
    total_borrowing_cost: "1133359.00",
  };

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders upload dropzone and instructions", () => {
    render(<KfsAnalysisSection activePlan={dummyActivePlan} />);

    expect(screen.getByText("02 / KEY FACT STATEMENT (KFS) INTELLIGENCE")).toBeDefined();
    expect(screen.getByText(/Upload & verify loan document/i)).toBeDefined();
    expect(screen.getByText(/Click to upload/i)).toBeDefined();
    expect(screen.getByText(/Standard RBI-mandated KFS or sanction letter/i)).toBeDefined();
  });

  it("rejects non-PDF files client-side without calling API", async () => {
    const uploadSpy = vi.spyOn(api, "uploadAndAnalyzeDocument");

    render(<KfsAnalysisSection activePlan={dummyActivePlan} />);

    const input = screen.getByLabelText(/Upload KFS PDF document/i);
    const nonPdfFile = new File(["dummy content"], "invoice.txt", { type: "text/plain" });

    fireEvent.change(input, { target: { files: [nonPdfFile] } });

    await waitFor(() => {
      expect(screen.getByText(/Only PDF documents are supported/i)).toBeDefined();
    });
    expect(uploadSpy).not.toHaveBeenCalled();
  });

  it("rejects oversized PDF files (> 8 MB) client-side", async () => {
    const uploadSpy = vi.spyOn(api, "uploadAndAnalyzeDocument");

    render(<KfsAnalysisSection activePlan={dummyActivePlan} />);

    const input = screen.getByLabelText(/Upload KFS PDF document/i);
    // Create oversized file: 9 MB
    const oversizedFile = new File(["%PDF-1.4 "], "huge.pdf", { type: "application/pdf" });
    Object.defineProperty(oversizedFile, "size", { value: 9 * 1024 * 1024 });

    fireEvent.change(input, { target: { files: [oversizedFile] } });

    await waitFor(() => {
      expect(screen.getByText(/Document exceeds the 8 MB limit/i)).toBeDefined();
    });
    expect(uploadSpy).not.toHaveBeenCalled();
  });

  it("displays file info when valid PDF is selected, and allows removing it", async () => {
    render(<KfsAnalysisSection activePlan={dummyActivePlan} />);

    const input = screen.getByLabelText(/Upload KFS PDF document/i);
    const pdfFile = new File(["%PDF-1.4 mock content"], "sample_kfs.pdf", { type: "application/pdf" });

    fireEvent.change(input, { target: { files: [pdfFile] } });

    await waitFor(() => {
      expect(screen.getByText("sample_kfs.pdf")).toBeDefined();
      expect(screen.getByRole("button", { name: /Analyze KFS document/i })).toBeDefined();
      expect(screen.getByRole("button", { name: /Remove uploaded file/i })).toBeDefined();
    });

    // Click remove
    const removeBtn = screen.getByRole("button", { name: /Remove uploaded file/i });
    fireEvent.click(removeBtn);

    await waitFor(() => {
      expect(screen.queryByText("sample_kfs.pdf")).toBeNull();
      expect(screen.getByText(/Click to upload/i)).toBeDefined();
    });
  });

  it("uploads document and renders extracted loan terms with confidence badges", async () => {
    const mockExtraction: api.DocumentAnalysisResponse = {
      filename: "sbi_car_kfs.pdf",
      extracted_fields: {
        lender: { value: "State Bank of India", confidence: "high" },
        loan_amount: { value: "Rs. 10,00,000", confidence: "high" },
        interest_rate: { value: "8.75%", confidence: "high" },
        rate_type: { value: "floating", confidence: "medium" },
        tenure: { value: "60 months", confidence: "high" },
        emi: { value: "Rs. 20,638", confidence: "high" },
        processing_fee: { value: "Rs. 2,500", confidence: "high" },
        other_charges: { value: "Rs. 500", confidence: "high" },
        apr: { value: "9.10%", confidence: "high" },
        prepayment_terms: { value: "Needs review", confidence: "needs_review" },
        foreclosure_terms: { value: "Needs review", confidence: "needs_review" },
      },
      warnings: ["Missing fields are shown as not found and are never inferred."],
      disclaimer: "Extracted values should be checked against the original lender document.",
    };

    const mockCalcLoan: api.LoanSummary = {
      emi: "20638.00",
      total_interest: "238280.00",
      total_repayment: "1238280.00",
      processing_fee: "2500.00",
      other_charges: "500.00",
      total_borrowing_cost: "1241280.00",
    };

    const uploadSpy = vi.spyOn(api, "uploadAndAnalyzeDocument").mockResolvedValue(mockExtraction);
    const calcSpy = vi.spyOn(api, "calculateLoan").mockResolvedValue(mockCalcLoan);

    render(<KfsAnalysisSection activePlan={dummyActivePlan} />);

    const input = screen.getByLabelText(/Upload KFS PDF document/i);
    const pdfFile = new File(["%PDF-1.4 mock"], "sbi_car_kfs.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [pdfFile] } });

    const analyzeBtn = await screen.findByRole("button", { name: /Analyze KFS document/i });
    fireEvent.click(analyzeBtn);

    await waitFor(() => {
      expect(uploadSpy).toHaveBeenCalledWith(pdfFile);
    });

    // Check extracted terms
    await waitFor(() => {
      expect(screen.getByText("State Bank of India")).toBeDefined();
      expect(screen.getByText("Rs. 10,00,000")).toBeDefined();
      expect(screen.getByText("8.75%")).toBeDefined();
      expect(screen.getByText("60 months")).toBeDefined();
      expect(screen.getByText("Rs. 20,638")).toBeDefined();
      expect(screen.getByText("Rs. 2,500")).toBeDefined();
      expect(screen.getByText("floating")).toBeDefined();
      expect(screen.getAllByText("High confidence").length).toBeGreaterThan(3);
      expect(screen.getByText("Medium")).toBeDefined();
      expect(screen.getAllByText("Needs review").length).toBe(4);
    });

    // Check deterministic financial calculation triggered
    await waitFor(() => {
      expect(calcSpy).toHaveBeenCalled();
      expect(screen.getByText("LoanWise Deterministic Calculation")).toBeDefined();
      expect(screen.getByText("ESTIMATED EMI")).toBeDefined();
      expect(screen.getByText("TOTAL BORROWING COST")).toBeDefined();
    });

    // Check plan comparison
    await waitFor(() => {
      expect(screen.getByText("Comparison with Your Current Plan")).toBeDefined();
      expect(screen.getByText(/KFS Document Offer/i)).toBeDefined();
    });
  });

  it("displays 'Not found in document' and allows supplying missing terms", async () => {
    const mockExtraction: api.DocumentAnalysisResponse = {
      filename: "partial_kfs.pdf",
      extracted_fields: {
        lender: { value: "Bank of Baroda", confidence: "high" },
        loan_amount: { value: "Rs. 6,00,000", confidence: "high" },
        interest_rate: { value: null, confidence: "not_found" },
        rate_type: { value: null, confidence: "not_found" },
        tenure: { value: null, confidence: "not_found" },
        emi: { value: null, confidence: "not_found" },
        processing_fee: { value: null, confidence: "not_found" },
        other_charges: { value: null, confidence: "not_found" },
        apr: { value: null, confidence: "not_found" },
        prepayment_terms: { value: null, confidence: "not_found" },
        foreclosure_terms: { value: null, confidence: "not_found" },
      },
      warnings: ["Missing fields are shown as not found and are never inferred."],
      disclaimer: "Extracted values should be checked against the original lender document.",
    };

    vi.spyOn(api, "uploadAndAnalyzeDocument").mockResolvedValue(mockExtraction);
    const calcSpy = vi.spyOn(api, "calculateLoan").mockResolvedValue({
      emi: "12800.00",
      total_interest: "168000.00",
      total_repayment: "768000.00",
      processing_fee: "0.00",
      other_charges: "0.00",
      total_borrowing_cost: "768000.00",
    });

    render(<KfsAnalysisSection activePlan={dummyActivePlan} />);

    const input = screen.getByLabelText(/Upload KFS PDF document/i);
    fireEvent.change(input, {
      target: { files: [new File(["%PDF-1.4"], "partial.pdf", { type: "application/pdf" })] },
    });

    const analyzeBtn = await screen.findByRole("button", { name: /Analyze KFS document/i });
    fireEvent.click(analyzeBtn);

    await waitFor(() => {
      expect(screen.getByText("Supply Missing Terms")).toBeDefined();
      expect(screen.getAllByText("Not found in document").length).toBeGreaterThan(3);
    });

    // Provide missing interest rate and tenure
    const rateInput = screen.getByLabelText("Manual Interest Rate");
    const tenureInput = screen.getByLabelText("Manual Tenure Months");

    fireEvent.change(rateInput, { target: { value: "9.0" } });
    fireEvent.change(tenureInput, { target: { value: "48" } });

    await waitFor(() => {
      expect(calcSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          loan_amount: 600000,
          annual_interest_rate: 9,
          tenure_months: 48,
        })
      );
    });
  });

  it("invokes onAskAssistant when contextual prompt buttons are clicked", async () => {
    const mockExtraction: api.DocumentAnalysisResponse = {
      filename: "offer.pdf",
      extracted_fields: {
        lender: { value: "Axis Bank", confidence: "high" },
        loan_amount: { value: "Rs. 8,00,000", confidence: "high" },
        interest_rate: { value: "9.50%", confidence: "high" },
        rate_type: { value: "floating", confidence: "medium" },
        tenure: { value: "48 months", confidence: "high" },
        emi: { value: "Rs. 20,105", confidence: "high" },
        processing_fee: { value: "Rs. 4,000", confidence: "high" },
        other_charges: { value: "Rs. 800", confidence: "high" },
        apr: { value: null, confidence: "not_found" },
        prepayment_terms: { value: "Needs review", confidence: "needs_review" },
        foreclosure_terms: { value: "Needs review", confidence: "needs_review" },
      },
      warnings: [],
      disclaimer: "Extracted values should be checked.",
    };

    vi.spyOn(api, "uploadAndAnalyzeDocument").mockResolvedValue(mockExtraction);
    vi.spyOn(api, "calculateLoan").mockResolvedValue({
      emi: "20105.00",
      total_interest: "165040.00",
      total_repayment: "965040.00",
      processing_fee: "4000.00",
      other_charges: "800.00",
      total_borrowing_cost: "969840.00",
    });

    const askSpy = vi.fn();
    render(<KfsAnalysisSection activePlan={dummyActivePlan} onAskAssistant={askSpy} />);

    const fileInput = screen.getByLabelText(/Upload KFS PDF document/i);
    fireEvent.change(fileInput, {
      target: { files: [new File(["%PDF-1.4"], "offer.pdf", { type: "application/pdf" })] },
    });

    const analyzeBtn = await screen.findByRole("button", { name: /Analyze KFS document/i });
    fireEvent.click(analyzeBtn);

    const explainBtn = await screen.findByText(/Explain this KFS in simple language/i);
    fireEvent.click(explainBtn);

    expect(askSpy).toHaveBeenCalledWith(
      expect.stringContaining("Explain this Key Fact Statement (KFS) in simple language"),
      expect.objectContaining({
        loan_amount: 800000,
        annual_interest_rate: 9.5,
        tenure_months: 48,
      })
    );

    const chargesBtn = screen.getByText(/Explain these charges/i);
    fireEvent.click(chargesBtn);
    expect(askSpy).toHaveBeenCalledWith(
      expect.stringContaining("Explain the fee structure in this KFS document"),
      expect.anything()
    );

    const compareBtn = screen.getByText(/Compare this offer with my current loan/i);
    fireEvent.click(compareBtn);
    expect(askSpy).toHaveBeenCalledWith(
      expect.stringContaining("Compare this KFS offer"),
      expect.anything()
    );
  });
});
