from decimal import Decimal

from app.financial.amortization import generate_amortization_schedule
from app.financial.types import LoanInputs


def test_schedule_reconciles_principal_and_closes_balance() -> None:
    loan = LoanInputs(Decimal("500000"), Decimal("9.5"), 36)
    schedule = generate_amortization_schedule(loan)

    assert len(schedule) == 36
    assert schedule[-1].closing_balance == Decimal("0.00")
    assert sum(row.principal for row in schedule) == loan.principal
    assert all(row.closing_balance >= 0 for row in schedule)
    assert all(row.emi == row.interest + row.principal for row in schedule)


def test_zero_rate_schedule_has_no_interest() -> None:
    schedule = generate_amortization_schedule(LoanInputs(Decimal("1200"), Decimal("0"), 12))
    assert sum(row.interest for row in schedule) == Decimal("0.00")
