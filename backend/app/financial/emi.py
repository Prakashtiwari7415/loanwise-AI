"""EMI and total borrowing cost calculations."""

from decimal import Decimal, ROUND_HALF_UP, localcontext

from .types import LoanInputs, LoanSummary, Money

MONEY_PLACES = Decimal("0.01")


def quantize_money(value: Decimal) -> Money:
    return value.quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def validate_loan_inputs(inputs: LoanInputs) -> None:
    if inputs.principal <= 0:
        raise ValueError("principal must be greater than zero")
    if inputs.annual_interest_rate < 0:
        raise ValueError("annual_interest_rate cannot be negative")
    if inputs.tenure_months <= 0:
        raise ValueError("tenure_months must be greater than zero")
    if inputs.processing_fee < 0 or inputs.other_charges < 0:
        raise ValueError("fees and charges cannot be negative")


def calculate_emi(principal: Money, annual_interest_rate: Decimal, tenure_months: int) -> Money:
    """Calculate a monthly reducing-balance instalment, rounded to paise."""
    validate_loan_inputs(LoanInputs(principal, annual_interest_rate, tenure_months))
    if annual_interest_rate == 0:
        return quantize_money(principal / Decimal(tenure_months))
    with localcontext() as context:
        context.prec = 40
        rate = annual_interest_rate / Decimal("1200")
        factor = (Decimal("1") + rate) ** tenure_months
        return quantize_money(principal * rate * factor / (factor - Decimal("1")))


def calculate_summary(inputs: LoanInputs) -> LoanSummary:
    """Return loan totals excluding any unknown lender-specific penalties."""
    validate_loan_inputs(inputs)
    # The final scheduled payment can differ from the rounded regular EMI by a
    # few paise. Reuse the canonical schedule rather than multiplying a rounded
    # EMI so headline totals always reconcile with the payment breakdown.
    from .amortization import generate_amortization_schedule

    schedule = generate_amortization_schedule(inputs)
    emi = calculate_emi(inputs.principal, inputs.annual_interest_rate, inputs.tenure_months)
    total_repayment = quantize_money(sum(entry.emi for entry in schedule))
    total_interest = quantize_money(sum(entry.interest for entry in schedule))
    total_borrowing_cost = quantize_money(total_repayment + inputs.processing_fee + inputs.other_charges)
    return LoanSummary(
        emi=emi,
        total_interest=total_interest,
        total_repayment=total_repayment,
        processing_fee=quantize_money(inputs.processing_fee),
        other_charges=quantize_money(inputs.other_charges),
        total_borrowing_cost=total_borrowing_cost,
    )
