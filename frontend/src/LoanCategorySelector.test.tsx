import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { LoanCategorySelector } from "./LoanCategorySelector";

describe("LoanCategorySelector", () => {
  it("renders all 6 loan category options with their support badges", () => {
    const handleSelect = vi.fn();
    render(<LoanCategorySelector selectedId="car" onSelect={handleSelect} />);

    expect(screen.getByText("What type of loan are you exploring?")).toBeDefined();

    // 6 categories
    expect(screen.getByText("Car Loan")).toBeDefined();
    expect(screen.getByText("Home Loan")).toBeDefined();
    expect(screen.getByText("Personal Loan")).toBeDefined();
    expect(screen.getByText("Two-Wheeler Loan")).toBeDefined();
    expect(screen.getByText("Education Loan")).toBeDefined();
    expect(screen.getByText("Other Loan / Not Sure Yet")).toBeDefined();

    // Support badges
    expect(screen.getAllByText("Fully Supported").length).toBeGreaterThan(3);
    expect(screen.getByText("Partially Supported")).toBeDefined();
    expect(screen.getByText("General Support")).toBeDefined();
  });

  it("calls onSelect when a category card is clicked", () => {
    const handleSelect = vi.fn();
    render(<LoanCategorySelector selectedId="car" onSelect={handleSelect} />);

    const homeCard = screen.getByText("Home Loan");
    fireEvent.click(homeCard);

    expect(handleSelect).toHaveBeenCalledWith("home");
  });

  it("calls onSelect on Enter or Space key press", () => {
    const handleSelect = vi.fn();
    render(<LoanCategorySelector selectedId="car" onSelect={handleSelect} />);

    const eduCard = screen.getByRole("radio", { name: /Education Loan/i });
    fireEvent.keyDown(eduCard, { key: "Enter" });

    expect(handleSelect).toHaveBeenCalledWith("education");
  });

  it("honestly explains calculation boundaries in the banner for education loan", () => {
    const handleSelect = vi.fn();
    render(<LoanCategorySelector selectedId="education" onSelect={handleSelect} />);

    expect(screen.getByText(/Exploring: Education Loan/i)).toBeDefined();
    expect(screen.getAllByText(/Partially Supported/i).length).toBe(2);
    expect(
      screen.getByText(/study-phase simple interest subsidies require specialized scheduling/i)
    ).toBeDefined();
  });
});
