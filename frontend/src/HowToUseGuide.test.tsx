import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { HowToUseGuide } from "./HowToUseGuide";

describe("HowToUseGuide", () => {
  it("renders Step 1 initially with total step count and illustrative badge", () => {
    render(<HowToUseGuide />);

    expect(screen.getByText("Step 1 of 6")).toBeDefined();
    expect(screen.getByText("Step 1 — Choose your loan type")).toBeDefined();
    expect(screen.getByText("ILLUSTRATIVE EXAMPLE")).toBeDefined();
    expect(screen.getByText(/Previous Step/i)).toHaveProperty("disabled", true);
  });

  it("progresses to next steps when Next button is clicked", () => {
    render(<HowToUseGuide />);

    const nextBtn = screen.getByRole("button", { name: /Next Step/i });
    fireEvent.click(nextBtn);

    expect(screen.getByText("Step 2 of 6")).toBeDefined();
    expect(screen.getByText("Step 2 — Enter your details")).toBeDefined();

    // Previous button should now be enabled
    const prevBtn = screen.getByRole("button", { name: /Previous Step/i });
    expect(prevBtn).toHaveProperty("disabled", false);
  });

  it("allows jumping directly to a step via the step indicator dots", () => {
    render(<HowToUseGuide />);

    // Click step 5 (KFS Upload)
    const step5Dot = screen.getByRole("tab", { name: /Step 5/i });
    fireEvent.click(step5Dot);

    expect(screen.getByText("Step 5 of 6")).toBeDefined();
    expect(screen.getByText(/Upload your Key Fact Statement/i)).toBeDefined();
    expect(screen.getByText(/Confidence Badges/i)).toBeDefined();
  });

  it("calls onNavigateToSection when 'Try it yourself' is clicked", () => {
    const navSpy = vi.fn();
    render(<HowToUseGuide onNavigateToSection={navSpy} />);

    const tryBtn = screen.getByRole("button", { name: /Try it: Select a loan category/i });
    fireEvent.click(tryBtn);

    expect(navSpy).toHaveBeenCalledWith("#explore-loans");
  });

  it("calls onClose when Close button is clicked", () => {
    const closeSpy = vi.fn();
    render(<HowToUseGuide onClose={closeSpy} />);

    const closeBtn = screen.getByRole("button", { name: /Close how to use guide/i });
    fireEvent.click(closeBtn);

    expect(closeSpy).toHaveBeenCalled();
  });
});
