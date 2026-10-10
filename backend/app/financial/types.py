"""Typed, deterministic domain models for LoanWise calculations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


Money = Decimal


class LoanType(StrEnum):
    CAR = "car"
    HOME = "home"


class RateType(StrEnum):
    FIXED = "fixed"
    FLOATING = "floating"


class RecommendationObjective(StrEnum):
    LOWEST_EMI = "lowest_emi"
    LOWEST_TOTAL_COST = "lowest_total_cost"
    FASTER_REPAYMENT = "faster_repayment"
    MAXIMUM_FLEXIBILITY = "maximum_flexibility"


@dataclass(frozen=True)
class LoanInputs:
    principal: Money
    annual_interest_rate: Decimal
    tenure_months: int
    processing_fee: Money = Decimal("0")
    other_charges: Money = Decimal("0")


@dataclass(frozen=True)
class LoanSummary:
    emi: Money
    total_interest: Money
    total_repayment: Money
    processing_fee: Money
    other_charges: Money
    total_borrowing_cost: Money


@dataclass(frozen=True)
class AmortizationEntry:
    month: int
    opening_balance: Money
    emi: Money
    interest: Money
    principal: Money
    closing_balance: Money


@dataclass(frozen=True)
class AffordabilityResult:
    score: int
    classification: str
    current_emi_burden_percent: Decimal
    projected_emi_burden_percent: Decimal
    remaining_income_after_emis: Money
    reasons: tuple[str, ...]
    risks: tuple[str, ...]
    assumptions: tuple[str, ...]


@dataclass(frozen=True)
class PrepaymentResult:
    revised_schedule: tuple[AmortizationEntry, ...]
    new_total_repayment: Money
    new_total_interest: Money
    interest_saved: Money
    months_saved: int


@dataclass(frozen=True)
class RateScenario:
    annual_interest_rate: Decimal
    emi: Money
    total_interest: Money
    additional_monthly_cost: Money
    additional_total_interest: Money


@dataclass(frozen=True)
class LoanOffer:
    lender: str
    loan_type: LoanType
    principal: Money
    annual_interest_rate: Decimal
    tenure_months: int
    processing_fee: Money = Decimal("0")
    other_charges: Money = Decimal("0")
    rate_type: RateType = RateType.FIXED
    prepayment_terms: str | None = None
    foreclosure_terms: str | None = None
    source_url: str | None = None
    retrieved_at: str | None = None
    verified_at: str | None = None
    is_demo: bool = False


@dataclass(frozen=True)
class Recommendation:
    lender: str
    score: int
    reasons: tuple[str, ...]
    risks: tuple[str, ...]
    assumptions: tuple[str, ...]
