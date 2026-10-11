import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { OfferComparisonSection } from "./OfferComparisonSection";
import * as api from "./api";

describe("OfferComparisonSection", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders side-by-side inputs for Offer A and Offer B", () => {
    render(<OfferComparisonSection />);

    expect(screen.getByText("03 / COMPARE LOAN OFFERS")).toBeDefined();
    expect(screen.getByText("Compare two offers side-by-side")).toBeDefined();
    expect(screen.getByText("OFFER A")).toBeDefined();
    expect(screen.getByText("OFFER B")).toBeDefined();
    expect(screen.getByRole("button", { name: /Compare offers side by side/i })).toBeDefined();
  });

  it("computes deterministic comparison and exposes tenure trap when lower EMI costs more overall", async () => {
    const calcLoanSpy = vi.spyOn(api, "calculateLoan")
      .mockResolvedValueOnce({
        emi: "18806.00",
        total_interest: "228360.00",
        total_repayment: "1128360.00",
        processing_fee: "4999.00",
        other_charges: "0.00",
        total_borrowing_cost: "1133359.00",
      })
      .mockResolvedValueOnce({
        emi: "14800.00", // Lower EMI!
        total_interest: "343200.00", // Much higher interest!
        total_repayment: "1243200.00",
        processing_fee: "2500.00",
        other_charges: "0.00",
        total_borrowing_cost: "1245700.00", // Higher total cost!
      });

    const compareSpy = vi.spyOn(api, "compareLoans").mockResolvedValue({
      lender: "Bank A (Offer 1)",
      score: 88,
      reasons: ["Significantly lower total borrowing cost"],
      risks: ["Higher monthly EMI"],
      assumptions: ["Standard reducing balance amortization"],
    });

    render(<OfferComparisonSection />);

    const compareBtn = screen.getByRole("button", { name: /Compare offers side by side/i });
    fireEvent.click(compareBtn);

    await waitFor(() => {
      expect(calcLoanSpy).toHaveBeenCalledTimes(2);
      expect(compareSpy).toHaveBeenCalled();
      expect(screen.getByText("Side-by-Side Financial Results")).toBeDefined();
    });

    // Check tenure trap callout appears
    expect(screen.getByText(/The "Lower EMI" Illusion/i)).toBeDefined();
    expect(screen.getAllByText(/saves ₹1,12,341 overall/i).length).toBe(2);

    // Check recommendation
    expect(screen.getByText("Recommended: Bank A (Offer 1)")).toBeDefined();
    expect(screen.getByText("✓ Significantly lower total borrowing cost")).toBeDefined();
  });
});
