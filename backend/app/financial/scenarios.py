"""Interest-rate scenarios and transparent offer recommendations."""

from decimal import Decimal

from .emi import calculate_summary
from .types import (
    LoanInputs,
    LoanOffer,
    RateScenario,
    Recommendation,
    RecommendationObjective,
    RateType,
)


def simulate_rate_scenarios(
    inputs: LoanInputs, rate_changes: tuple[Decimal, ...] = (Decimal("0"), Decimal("0.5"), Decimal("1"), Decimal("2")),
) -> tuple[RateScenario, ...]:
    baseline = calculate_summary(inputs)
    scenarios: list[RateScenario] = []
    for change in rate_changes:
        if inputs.annual_interest_rate + change < 0:
            raise ValueError("rate scenario cannot produce a negative rate")
        summary = calculate_summary(
            LoanInputs(
                principal=inputs.principal,
                annual_interest_rate=inputs.annual_interest_rate + change,
                tenure_months=inputs.tenure_months,
                processing_fee=inputs.processing_fee,
                other_charges=inputs.other_charges,
            )
        )
        scenarios.append(
            RateScenario(
                annual_interest_rate=inputs.annual_interest_rate + change,
                emi=summary.emi,
                total_interest=summary.total_interest,
                additional_monthly_cost=summary.emi - baseline.emi,
                additional_total_interest=summary.total_interest - baseline.total_interest,
            )
        )
    return tuple(scenarios)


def recommend_offer(
    offers: tuple[LoanOffer, ...], objective: RecommendationObjective
) -> Recommendation:
    if not offers:
        raise ValueError("at least one offer is required")
    calculated_offers = tuple(
        (
            offer,
            calculate_summary(
                LoanInputs(
                    offer.principal,
                    offer.annual_interest_rate,
                    offer.tenure_months,
                    offer.processing_fee,
                    offer.other_charges,
                )
            ),
        )
        for offer in offers
    )
    if objective == RecommendationObjective.LOWEST_EMI:
        chosen = min(calculated_offers, key=lambda item: item[1].emi)[0]
        reason = "It has the lowest estimated monthly EMI among the selected offers."
    elif objective == RecommendationObjective.FASTER_REPAYMENT:
        chosen = min(offers, key=lambda offer: offer.tenure_months)
        reason = "It has the shortest selected repayment period."
    elif objective == RecommendationObjective.MAXIMUM_FLEXIBILITY:
        chosen = max(
            offers,
            key=lambda offer: int(bool(offer.prepayment_terms)) + int(bool(offer.foreclosure_terms)),
        )
        reason = "It has the most documented flexibility information in the selected offers."
    else:
        chosen = min(calculated_offers, key=lambda item: item[1].total_borrowing_cost)[0]
        reason = "It has the lowest estimated repayment plus disclosed fees among the selected offers."

    risks: list[str] = []
    if chosen.rate_type == RateType.FLOATING:
        risks.append("A floating rate can change the EMI or tenure if rates move.")
    if not chosen.prepayment_terms:
        risks.append("Prepayment terms were not supplied; confirm charges directly with the lender.")
    if chosen.is_demo:
        risks.append("This is illustrative demo data, not a current lender offer.")
    return Recommendation(
        lender=chosen.lender,
        score=75 if not risks else 65,
        reasons=(reason,),
        risks=tuple(risks),
        assumptions=(
            "Based on the selected objective and provided offer details.",
            "This is not a universal best-loan claim or approval decision.",
        ),
    )
