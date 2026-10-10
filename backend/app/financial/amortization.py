"""Reducing-balance amortization schedules."""

from decimal import Decimal

from .emi import calculate_emi, quantize_money, validate_loan_inputs
from .types import AmortizationEntry, LoanInputs


def generate_amortization_schedule(inputs: LoanInputs) -> tuple[AmortizationEntry, ...]:
    validate_loan_inputs(inputs)
    emi = calculate_emi(inputs.principal, inputs.annual_interest_rate, inputs.tenure_months)
    monthly_rate = inputs.annual_interest_rate / Decimal("1200")
    balance = quantize_money(inputs.principal)
    entries: list[AmortizationEntry] = []

    for month in range(1, inputs.tenure_months + 1):
        opening_balance = balance
        interest = quantize_money(opening_balance * monthly_rate)
        principal = quantize_money(emi - interest)
        if month == inputs.tenure_months or principal >= opening_balance:
            principal = opening_balance
            payment = quantize_money(interest + principal)
        else:
            payment = emi
        balance = quantize_money(opening_balance - principal)
        entries.append(
            AmortizationEntry(month, opening_balance, payment, interest, principal, balance)
        )
    return tuple(entries)
