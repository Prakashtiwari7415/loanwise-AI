from decimal import Decimal

import pytest

from app.financial.emi import calculate_emi, calculate_summary
from app.financial.amortization import generate_amortization_schedule
from app.financial.types import LoanInputs


def test_calculates_standard_monthly_emi() -> None:
    emi = calculate_emi(Decimal("1000000"), Decimal("10"), 60)
    assert emi == Decimal("21247.04")


def test_zero_interest_is_principal_divided_by_months() -> None:
    assert calculate_emi(Decimal("120000"), Decimal("0"), 12) == Decimal("10000.00")


@pytest.mark.parametrize(
    ("principal", "rate", "months"),
    [(Decimal("0"), Decimal("8"), 12), (Decimal("1000"), Decimal("-1"), 12), (Decimal("1000"), Decimal("8"), 0)],
)
def test_invalid_loan_input_is_rejected(principal: Decimal, rate: Decimal, months: int) -> None:
    with pytest.raises(ValueError):
        calculate_emi(principal, rate, months)


def test_summary_includes_fees_in_total_borrowing_cost() -> None:
    summary = calculate_summary(LoanInputs(Decimal("100000"), Decimal("10"), 12, Decimal("999"), Decimal("250")))
    assert summary.total_borrowing_cost == summary.total_repayment + Decimal("1249.00")


@pytest.mark.parametrize(
    "loan",
    [
        LoanInputs(Decimal("1000000"), Decimal("10"), 60),
        LoanInputs(Decimal("123456.78"), Decimal("7.35"), 37),
        LoanInputs(Decimal("1.00"), Decimal("0"), 3),
    ],
)
def test_summary_reconciles_with_the_canonical_amortization_schedule(loan: LoanInputs) -> None:
    summary = calculate_summary(loan)
    schedule = generate_amortization_schedule(loan)

    assert summary.total_repayment == sum(entry.emi for entry in schedule)
    assert summary.total_interest == sum(entry.interest for entry in schedule)
