"""Prepayment simulation using the same deterministic schedule engine."""

from decimal import Decimal

from .emi import calculate_summary, quantize_money, validate_loan_inputs
from .types import AmortizationEntry, LoanInputs, PrepaymentResult


def simulate_one_time_prepayment(
    inputs: LoanInputs, *, prepayment_amount: Decimal, prepayment_month: int
) -> PrepaymentResult:
    """Model a lump-sum prepayment while preserving the original EMI.

    Lender fees/penalties are deliberately excluded because they require lender terms.
    """
    validate_loan_inputs(inputs)
    if prepayment_amount <= 0:
        raise ValueError("prepayment_amount must be greater than zero")
    if not 1 <= prepayment_month < inputs.tenure_months:
        raise ValueError("prepayment_month must be before the original final month")

    monthly_rate = inputs.annual_interest_rate / Decimal("1200")
    original = calculate_summary(inputs)
    balance = quantize_money(inputs.principal)
    entries: list[AmortizationEntry] = []
    month = 0
    while balance > 0:
        month += 1
        opening = balance
        interest = quantize_money(opening * monthly_rate)
        principal = quantize_money(original.emi - interest)
        payment = original.emi
        if principal >= opening:
            principal = opening
            payment = quantize_money(principal + interest)
        balance = quantize_money(opening - principal)

        if month == prepayment_month and balance > 0:
            applied = min(quantize_money(prepayment_amount), balance)
            principal = quantize_money(principal + applied)
            payment = quantize_money(payment + applied)
            balance = quantize_money(balance - applied)
        entries.append(AmortizationEntry(month, opening, payment, interest, principal, balance))

    new_total = quantize_money(sum(entry.emi for entry in entries))
    new_interest = quantize_money(sum(entry.interest for entry in entries))
    return PrepaymentResult(
        revised_schedule=tuple(entries),
        new_total_repayment=new_total,
        new_total_interest=new_interest,
        interest_saved=quantize_money(max(Decimal("0"), original.total_interest - new_interest)),
        months_saved=inputs.tenure_months - len(entries),
    )
