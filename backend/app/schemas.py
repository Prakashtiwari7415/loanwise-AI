"""HTTP contracts. Financial computation remains in the domain package."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .financial.types import LoanType, RateType, RecommendationObjective


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoanCalculationRequest(APIModel):
    loan_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    annual_interest_rate: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=3)
    tenure_months: int = Field(gt=0, le=480)
    processing_fee: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    other_charges: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)


class LoanSummaryResponse(APIModel):
    emi: Decimal
    total_interest: Decimal
    total_repayment: Decimal
    processing_fee: Decimal
    other_charges: Decimal
    total_borrowing_cost: Decimal


class AmortizationEntryResponse(APIModel):
    month: int
    opening_balance: Decimal
    emi: Decimal
    interest: Decimal
    principal: Decimal
    closing_balance: Decimal


class AffordabilityRequest(APIModel):
    monthly_income: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    existing_emis: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    proposed_emi: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    estimated_monthly_expenses: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)


class AffordabilityResponse(APIModel):
    score: int
    classification: str
    current_emi_burden_percent: Decimal
    projected_emi_burden_percent: Decimal
    remaining_income_after_emis: Decimal
    reasons: list[str]
    risks: list[str]
    assumptions: list[str]


class PrepaymentRequest(LoanCalculationRequest):
    prepayment_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    prepayment_month: int = Field(gt=0)


class PrepaymentResponse(APIModel):
    new_total_repayment: Decimal
    new_total_interest: Decimal
    interest_saved: Decimal
    months_saved: int
    revised_schedule: list[AmortizationEntryResponse]
    assumptions: list[str]


class RateScenarioResponse(APIModel):
    annual_interest_rate: Decimal
    emi: Decimal
    total_interest: Decimal
    additional_monthly_cost: Decimal
    additional_total_interest: Decimal


class ScenarioRequest(LoanCalculationRequest):
    rate_changes: list[Decimal] = Field(
        default_factory=lambda: [Decimal("0"), Decimal("0.5"), Decimal("1"), Decimal("2")],
        min_length=1,
        max_length=8,
    )

    @field_validator("rate_changes")
    @classmethod
    def validate_rate_changes(cls, rate_changes: list[Decimal]) -> list[Decimal]:
        if any(change < Decimal("-20") or change > Decimal("20") for change in rate_changes):
            raise ValueError("rate_changes must be between -20 and 20 percentage points")
        return rate_changes


class OfferRequest(APIModel):
    lender: str = Field(min_length=1, max_length=100)
    loan_type: LoanType = LoanType.CAR
    loan_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    annual_interest_rate: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=3)
    tenure_months: int = Field(gt=0, le=480)
    processing_fee: Decimal = Field(default=Decimal("0"), ge=0)
    other_charges: Decimal = Field(default=Decimal("0"), ge=0)
    rate_type: RateType = RateType.FIXED
    prepayment_terms: str | None = Field(default=None, max_length=1000)
    foreclosure_terms: str | None = Field(default=None, max_length=1000)
    source_url: str | None = Field(default=None, max_length=2048)
    retrieved_at: str | None = None
    verified_at: str | None = None
    is_demo: bool = False


class CompareRequest(APIModel):
    offers: list[OfferRequest] = Field(min_length=1, max_length=10)
    objective: RecommendationObjective = RecommendationObjective.LOWEST_TOTAL_COST


class RecommendationResponse(APIModel):
    lender: str
    score: int
    reasons: list[str]
    risks: list[str]
    assumptions: list[str]


class DocumentFieldResponse(APIModel):
    value: str | None
    confidence: str


class DocumentAnalysisResponse(APIModel):
    filename: str
    extracted_fields: dict[str, DocumentFieldResponse]
    warnings: list[str]
    disclaimer: str
