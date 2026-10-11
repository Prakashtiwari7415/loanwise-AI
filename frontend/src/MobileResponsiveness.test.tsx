import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import App from "./App";

// Mock scrollIntoView for jsdom
window.HTMLElement.prototype.scrollIntoView = vi.fn();

describe("MobileResponsiveness", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders mobile navigation bar with all 5 quick-access links", () => {
    render(<App />);

    const mobileNav = screen.getByRole("navigation", { name: "Mobile Navigation" });
    expect(mobileNav).toBeDefined();

    const loansLink = screen.getByRole("link", { name: "Loan Categories" });
    expect(loansLink.getAttribute("href")).toBe("#explore-loans");

    const calcLink = screen.getByRole("link", { name: "Loan Calculator" });
    expect(calcLink.getAttribute("href")).toBe("#calculator-section");

    const compareLink = screen.getByRole("link", { name: "Compare Offers" });
    expect(compareLink.getAttribute("href")).toBe("#compare-section");

    const kfsLink = screen.getByRole("link", { name: "KFS Document Analysis" });
    expect(kfsLink.getAttribute("href")).toBe("#kfs-section");

    const assistantLink = screen.getByRole("link", { name: "AI Assistant" });
    expect(assistantLink.getAttribute("href")).toBe("#assistant-panel-section");
  });

  it("renders top mobile guide button and opens guide modal on click", () => {
    render(<App />);

    const guideButtons = screen.getAllByRole("button", { name: /Open how to use guide/i });
    expect(guideButtons.length).toBeGreaterThanOrEqual(1);

    // Open guide modal via first guide button
    fireEvent.click(guideButtons[0]);

    // Modal should appear
    expect(screen.getByText("Step 1 — Choose your loan type")).toBeDefined();
    expect(screen.getByText("Step 1 of 6")).toBeDefined();

    // Close guide
    const closeBtn = screen.getByRole("button", { name: /Close how to use guide/i });
    fireEvent.click(closeBtn);

    expect(screen.queryByText("Step 1 of 6")).toBeNull();
  });

  it("ensures calculator inputs provide inputMode='decimal' for mobile touch keyboards", () => {
    render(<App />);

    const priceInput = screen.getByLabelText(/Car on-road price/i);
    expect(priceInput.getAttribute("inputmode")).toBe("decimal");

    const incomeInput = screen.getByLabelText("Monthly take-home income");
    expect(incomeInput.getAttribute("inputmode")).toBe("decimal");

    const emisInput = screen.getByLabelText("Existing monthly EMIs");
    expect(emisInput.getAttribute("inputmode")).toBe("decimal");

    const feeInput = screen.getByLabelText("Processing fee");
    expect(feeInput.getAttribute("inputmode")).toBe("decimal");
  });

  it("ensures comparison inputs provide appropriate inputMode for touch keyboards", () => {
    render(<App />);

    const offerAAmount = screen.getByLabelText("Offer A Loan Amount");
    expect(offerAAmount.getAttribute("inputmode")).toBe("decimal");

    const offerARate = screen.getByLabelText("Offer A Interest Rate");
    expect(offerARate.getAttribute("inputmode")).toBe("decimal");

    const offerATenure = screen.getByLabelText("Offer A Tenure Months");
    expect(offerATenure.getAttribute("inputmode")).toBe("numeric");

    const offerAFee = screen.getByLabelText("Offer A Processing Fee");
    expect(offerAFee.getAttribute("inputmode")).toBe("decimal");
  });

  const VIEWPORT_WIDTHS = [320, 375, 390, 430, 768, 1024, 1440];

  VIEWPORT_WIDTHS.forEach((width) => {
    it(`renders complete application cleanly at ${width}px viewport width`, () => {
      // Simulate viewport width
      window.innerWidth = width;
      window.dispatchEvent(new Event("resize"));

      const { container } = render(<App />);

      // Ensure main content, hero, calculator, comparison, KFS, and assistant render without error
      expect(container.querySelector("main")).toBeDefined();
      expect(screen.getByRole("heading", { level: 1 })).toBeDefined();
      expect(screen.getByText("UNIVERSAL LOAN DECISION PLATFORM")).toBeDefined();
      expect(screen.getByText("01 / CHOOSE YOUR LOAN TYPE")).toBeDefined();
      expect(screen.getByText("02 / YOUR PLAN")).toBeDefined();
      expect(screen.getByText("03 / COMPARE LOAN OFFERS")).toBeDefined();
      expect(screen.getByText("02 / KEY FACT STATEMENT (KFS) INTELLIGENCE")).toBeDefined();
      expect(screen.getByText("LoanWise AI Assistant")).toBeDefined();
    });
  });
});
