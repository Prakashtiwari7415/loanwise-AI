from decimal import Decimal

from app.financial.payment import simulate_one_time_prepayment
from app.financial.scenarios import simulate_rate_scenarios
from app.financial.scenarios import recommend_offer
from app.financial.types import LoanInputs, LoanOffer, LoanType, RateType, RecommendationObjective


def test_rate_rise_increases_emi_and_interest() -> None:
    scenarios = simulate_rate_scenarios(LoanInputs(Decimal("800000"), Decimal("8"), 48))
    baseline, higher = scenarios[0], scenarios[-1]
    assert higher.emi > baseline.emi
    assert higher.total_interest > baseline.total_interest


def test_prepayment_reduces_interest_and_tenure() -> None:
    result = simulate_one_time_prepayment(
        LoanInputs(Decimal("800000"), Decimal("9"), 60),
        prepayment_amount=Decimal("100000"),
        prepayment_month=12,
    )
    assert result.interest_saved > 0
    assert result.months_saved > 0
    assert result.revised_schedule[-1].closing_balance == Decimal("0.00")


def test_comparison_keeps_each_offer_distinct_when_lender_names_repeat() -> None:
    recommendation = recommend_offer(
        (
            LoanOffer("Same lender", LoanType.CAR, Decimal("500000"), Decimal("15"), 36, rate_type=RateType.FLOATING),
            LoanOffer("Same lender", LoanType.CAR, Decimal("500000"), Decimal("8"), 36, rate_type=RateType.FIXED),
        ),
        RecommendationObjective.LOWEST_TOTAL_COST,
    )
    assert not any("floating" in risk.lower() for risk in recommendation.risks)
