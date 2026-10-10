"""Explainable affordability heuristics, not lender-approval predictions."""

from decimal import Decimal, ROUND_HALF_UP

from .emi import quantize_money
from .types import AffordabilityResult, Money


def _percentage(part: Money, whole: Money) -> Decimal:
    return (part / whole * Decimal("100")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def analyse_affordability(
    monthly_income: Money,
    existing_emis: Money,
    proposed_emi: Money,
    estimated_monthly_expenses: Money = Decimal("0"),
) -> AffordabilityResult:
    if monthly_income <= 0:
        raise ValueError("monthly_income must be greater than zero")
    if any(value < 0 for value in (existing_emis, proposed_emi, estimated_monthly_expenses)):
        raise ValueError("EMIs and expenses cannot be negative")

    current = _percentage(existing_emis, monthly_income)
    projected = _percentage(existing_emis + proposed_emi, monthly_income)
    remaining = quantize_money(monthly_income - existing_emis - proposed_emi - estimated_monthly_expenses)
    score = Decimal("100") - projected * Decimal("1.5")
    if remaining < 0:
        score -= Decimal("30")
    score = max(Decimal("0"), min(Decimal("100"), score))
    final_score = int(score.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    if final_score >= 80:
        classification = "GOOD FIT"
    elif final_score >= 60:
        classification = "MANAGEABLE"
    elif final_score >= 40:
        classification = "STRETCHED"
    else:
        classification = "HIGH STRAIN"

    reasons: list[str] = []
    risks: list[str] = []
    if projected <= Decimal("35"):
        reasons.append("Your projected EMI burden is modest under these assumptions.")
    elif projected <= Decimal("50"):
        reasons.append("Your projected EMI burden may be manageable, but leaves less room for changes.")
    else:
        risks.append("Your projected EMI burden is high relative to your monthly income.")
    if remaining >= monthly_income * Decimal("0.20"):
        reasons.append("You retain a meaningful monthly buffer after selected EMIs and expenses.")
    elif remaining < 0:
        risks.append("Selected EMIs and expenses exceed monthly income.")
    else:
        risks.append("Your remaining monthly buffer is limited.")

    return AffordabilityResult(
        score=final_score,
        classification=classification,
        current_emi_burden_percent=current,
        projected_emi_burden_percent=projected,
        remaining_income_after_emis=remaining,
        reasons=tuple(reasons),
        risks=tuple(risks),
        assumptions=(
            "This is an educational affordability estimate based on the inputs provided.",
            "It is not a lender approval decision or a universal lending rule.",
        ),
    )
