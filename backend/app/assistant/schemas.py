"""Pydantic schemas for the Assistant chat API and structured response."""

from __future__ import annotations

from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


from app.rag.models import SourceCitation


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoanContext(APIModel):
    """Optional validated loan context provided by the active dashboard."""
    loan_amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2, description="Principal loan amount in INR")
    annual_interest_rate: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=3, description="Annual interest rate percentage")
    tenure_months: int | None = Field(default=None, gt=0, le=480, description="Loan tenure in months")
    processing_fee: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2, description="Processing fee in INR")
    other_charges: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2, description="Other one-time charges in INR")
    monthly_income: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2, description="Monthly income in INR")
    existing_emis: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2, description="Existing EMIs in INR")
    estimated_monthly_expenses: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2, description="Estimated monthly expenses in INR")


class AssistantChatRequest(APIModel):
    """Chat request payload for POST /api/v1/assistant/chat."""
    message: str = Field(..., min_length=1, max_length=4000, description="User's query or instruction")
    loan_context: LoanContext | None = Field(default=None, description="Optional active loan context from dashboard")


class BreakdownItem(APIModel):
    """A single row in a cost or calculation breakdown table."""
    label: str = Field(..., description="Human-readable label for this component")
    amount_low: str = Field(..., description="Lower bound of estimate (or point value if equal to amount_high)")
    amount_high: str = Field(..., description="Upper bound of estimate")
    is_estimate: bool = Field(default=False, description="True when this row uses assumed values")
    assumption: str | None = Field(default=None, description="Assumption used for this component")
    category: str | None = Field(default=None, description="Component category: emi, operating, annual_provision, optional")


class AssistantChatResponse(APIModel):
    """Structured response adhering strictly to financial decision support standards."""
    message: str = Field(..., description="Educational explanation and commentary for the user")
    headline: str = Field(..., description="Short summary headline")
    advantages: list[str] = Field(default_factory=list, description="Key advantages identified from calculations")
    risks: list[str] = Field(default_factory=list, description="Key risks, trade-offs, and cautionary factors")
    recommended_action: str = Field(..., description="Actionable educational next step for the user")
    assumptions: list[str] = Field(default_factory=list, description="Underlying assumptions, caveats, and disclaimers")
    tool_calls_used: list[str] = Field(default_factory=list, description="Allowlisted financial tools executed for this response")
    needs_more_information: bool = Field(default=False, description="True if required loan parameters are missing")
    sources: list[SourceCitation] = Field(default_factory=list, description="Curated source citations grounding the answer")
    breakdown: list[BreakdownItem] = Field(default_factory=list, description="Structured cost/calculation breakdown for display (empty when not applicable)")
    is_estimate: bool = Field(default=False, description="True when the response contains assumed values or ranges rather than verified calculations")
