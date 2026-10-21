"""Pydantic schemas for allowlisted assistant financial tools."""

from __future__ import annotations

from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.financial.types import LoanType, RateType, RecommendationObjective


class ToolArgsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- calculate_emi ---
class CalculateEMIArgs(ToolArgsModel):
    loan_amount: Decimal = Field(..., gt=0, max_digits=14, decimal_places=2, description="Principal loan amount in INR")
    annual_interest_rate: Decimal = Field(..., ge=0, le=100, max_digits=5, decimal_places=3, description="Annual interest rate percentage (e.g. 9.5)")
    tenure_months: int = Field(..., gt=0, le=480, description="Loan tenure in months (e.g. 60)")
    processing_fee: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2, description="Upfront processing fee in INR")
    other_charges: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2, description="Other charges in INR")


class CalculateEMIResult(BaseModel):
    emi: Decimal
    total_interest: Decimal
    total_repayment: Decimal
    processing_fee: Decimal
    other_charges: Decimal
    total_borrowing_cost: Decimal


# --- calculate_affordability ---
class CalculateAffordabilityArgs(ToolArgsModel):
    monthly_income: Decimal = Field(..., gt=0, max_digits=14, decimal_places=2, description="Net monthly income in INR")
    existing_emis: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2, description="Existing monthly EMI obligations in INR")
    proposed_emi: Decimal = Field(..., gt=0, max_digits=14, decimal_places=2, description="Proposed new monthly EMI in INR")
    estimated_monthly_expenses: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2, description="Estimated non-EMI monthly living expenses in INR")


class CalculateAffordabilityResult(BaseModel):
    score: int
    classification: str
    current_emi_burden_percent: Decimal
    projected_emi_burden_percent: Decimal
    remaining_income_after_emis: Decimal
    reasons: list[str]
    risks: list[str]
    assumptions: list[str]


# --- compare_loans ---
class LoanOfferArg(ToolArgsModel):
    lender: str = Field(..., min_length=1, max_length=100, description="Lender or bank name")
    loan_amount: Decimal = Field(..., gt=0, max_digits=14, decimal_places=2, description="Principal loan amount in INR")
    annual_interest_rate: Decimal = Field(..., ge=0, le=100, max_digits=5, decimal_places=3, description="Annual interest rate percentage")
    tenure_months: int = Field(..., gt=0, le=480, description="Loan tenure in months")
    processing_fee: Decimal = Field(default=Decimal("0"), ge=0, description="Processing fee in INR")
    other_charges: Decimal = Field(default=Decimal("0"), ge=0, description="Other charges in INR")
    loan_type: LoanType = Field(default=LoanType.CAR, description="Loan type: car or home")
    rate_type: RateType = Field(default=RateType.FIXED, description="Rate type: fixed or floating")
    prepayment_terms: str | None = Field(default=None, max_length=1000, description="Prepayment terms if known")
    foreclosure_terms: str | None = Field(default=None, max_length=1000, description="Foreclosure terms if known")
    source_url: str | None = Field(default=None, max_length=2048, description="Source URL if verified")
    retrieved_at: str | None = None
    verified_at: str | None = None
    is_demo: bool = False


class CompareLoansArgs(ToolArgsModel):
    offers: list[LoanOfferArg] = Field(..., min_length=1, max_length=10, description="List of loan offers to compare (1 to 10 offers)")
    objective: RecommendationObjective = Field(
        default=RecommendationObjective.LOWEST_TOTAL_COST,
        description="Comparison objective: lowest_emi, lowest_total_cost, faster_repayment, maximum_flexibility",
    )


class CompareLoansResult(BaseModel):
    lender: str
    score: int
    reasons: list[str]
    risks: list[str]
    assumptions: list[str]


# --- simulate_prepayment ---
class SimulatePrepaymentArgs(ToolArgsModel):
    loan_amount: Decimal = Field(..., gt=0, max_digits=14, decimal_places=2, description="Principal loan amount in INR")
    annual_interest_rate: Decimal = Field(..., ge=0, le=100, max_digits=5, decimal_places=3, description="Annual interest rate percentage")
    tenure_months: int = Field(..., gt=0, le=480, description="Loan tenure in months")
    prepayment_amount: Decimal = Field(..., gt=0, max_digits=14, decimal_places=2, description="One-time prepayment lump sum amount in INR")
    prepayment_month: int = Field(..., gt=0, description="Month in which prepayment is made (e.g. 12)")
    processing_fee: Decimal = Field(default=Decimal("0"), ge=0, description="Processing fee in INR")
    other_charges: Decimal = Field(default=Decimal("0"), ge=0, description="Other charges in INR")


class SimulatePrepaymentResult(BaseModel):
    new_total_repayment: Decimal
    new_total_interest: Decimal
    interest_saved: Decimal
    months_saved: int
    assumptions: list[str]


# --- simulate_rate_change ---
class SimulateRateChangeArgs(ToolArgsModel):
    loan_amount: Decimal = Field(..., gt=0, max_digits=14, decimal_places=2, description="Principal loan amount in INR")
    annual_interest_rate: Decimal = Field(..., ge=0, le=100, max_digits=5, decimal_places=3, description="Base annual interest rate percentage")
    tenure_months: int = Field(..., gt=0, le=480, description="Loan tenure in months")
    rate_changes: list[Decimal] = Field(
        default_factory=lambda: [Decimal("0.5"), Decimal("1.0"), Decimal("2.0")],
        min_length=1,
        max_length=8,
        description="List of percentage point changes to test (e.g. [0.5, 1.0, 2.0])",
    )
    processing_fee: Decimal = Field(default=Decimal("0"), ge=0, description="Processing fee in INR")
    other_charges: Decimal = Field(default=Decimal("0"), ge=0, description="Other charges in INR")

    @field_validator("rate_changes")
    @classmethod
    def validate_rate_changes(cls, rate_changes: list[Decimal]) -> list[Decimal]:
        if any(change < Decimal("-20") or change > Decimal("20") for change in rate_changes):
            raise ValueError("rate_changes must be between -20 and 20 percentage points")
        return rate_changes


class RateScenarioItem(BaseModel):
    annual_interest_rate: Decimal
    emi: Decimal
    total_interest: Decimal
    additional_monthly_cost: Decimal
    additional_total_interest: Decimal


class SimulateRateChangeResult(BaseModel):
    scenarios: list[RateScenarioItem]


# --- estimate_vehicle_ownership ---
class OtherExpenseItem(ToolArgsModel):
    label: str = Field(..., min_length=1, max_length=100, description="Human-readable label for this expense")
    amount: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2, description="Monthly amount in INR")


class EstimateVehicleOwnershipArgs(ToolArgsModel):
    """Arguments for the vehicle total-cost-of-ownership estimator.

    All monetary values are in INR. Missing optional inputs are handled with
    transparent range assumptions — they must NOT be defaulted to zero silently.
    """
    emi: Decimal | None = Field(
        default=None, gt=0, max_digits=14, decimal_places=2,
        description="Known monthly loan EMI in INR for this vehicle. Include only if the loan context is clear."
    )
    emi_is_assumed: bool = Field(
        default=False,
        description="Set true if the EMI is an assumption rather than a verified calculation."
    )
    emi_assumption_note: str | None = Field(
        default=None, max_length=300,
        description="Explanation of what was assumed for the EMI value."
    )
    monthly_distance_km: Decimal | None = Field(
        default=None, gt=0, max_digits=8, decimal_places=1,
        description="Average monthly driving distance in kilometres."
    )
    mileage_km_per_litre: Decimal | None = Field(
        default=None, gt=0, max_digits=6, decimal_places=2,
        description="Vehicle fuel efficiency in km per litre."
    )
    fuel_price_per_litre: Decimal | None = Field(
        default=None, gt=0, max_digits=7, decimal_places=2,
        description="Current fuel price in INR per litre."
    )
    annual_insurance_premium: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2,
        description="Annual comprehensive insurance premium in INR. Will be divided by 12 for monthly provision."
    )
    monthly_insurance_provision: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2,
        description="Pre-calculated monthly insurance provision in INR (use instead of annual_insurance_premium if already converted)."
    )
    monthly_maintenance: Decimal | None = Field(
        default=None, ge=0, max_digits=10, decimal_places=2,
        description="Monthly spend on routine maintenance and servicing in INR."
    )
    annual_maintenance: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2,
        description="Annual maintenance cost in INR. Will be divided by 12 for monthly provision."
    )
    monthly_parking: Decimal | None = Field(
        default=None, ge=0, max_digits=8, decimal_places=2,
        description="Monthly parking cost in INR (0 if not applicable)."
    )
    monthly_tolls: Decimal | None = Field(
        default=None, ge=0, max_digits=8, decimal_places=2,
        description="Monthly toll expenses in INR (FASTag / booth)."
    )
    other_monthly_expenses: list[OtherExpenseItem] = Field(
        default_factory=list, max_length=10,
        description="Additional recurring monthly expenses (e.g. car wash, accessories EMI)."
    )
    vehicle_purchase_price: Decimal | None = Field(
        default=None, gt=0, max_digits=14, decimal_places=2,
        description="Vehicle ex-showroom / on-road price in INR for depreciation estimation."
    )
    include_depreciation_note: bool = Field(
        default=True,
        description="Whether to include a depreciation note in the breakdown."
    )


class CostComponentResult(BaseModel):
    label: str
    amount_low: Decimal
    amount_high: Decimal
    is_estimate: bool
    assumption: str | None
    category: str


class VehicleOwnershipCostResult(BaseModel):
    components: list[CostComponentResult]
    total_low: Decimal
    total_high: Decimal
    emi_included: bool
    has_estimated_components: bool
    uncertainty_note: str
    exclusions: list[str]
    follow_up_suggestions: list[str]
