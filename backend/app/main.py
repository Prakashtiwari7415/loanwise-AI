from __future__ import annotations

import os
from collections.abc import Callable
from contextlib import asynccontextmanager

from sqlalchemy import text
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .assistant.router import router as assistant_router
from .document_extraction import extract_pdf_fields
from .core.config import get_settings
from .db.session import get_engine
from .financial.affordability import analyse_affordability
from .financial.amortization import generate_amortization_schedule
from .financial.emi import calculate_summary
from .financial.payment import simulate_one_time_prepayment
from .financial.scenarios import recommend_offer, simulate_rate_scenarios
from .financial.types import LoanInputs, LoanOffer
from .services.calculation_persistence import persist_calculation_if_configured
from .schemas import (
    AffordabilityRequest,
    AffordabilityResponse,
    AmortizationEntryResponse,
    CompareRequest,
    DocumentAnalysisResponse,
    DocumentFieldResponse,
    LoanCalculationRequest,
    LoanSummaryResponse,
    PrepaymentRequest,
    PrepaymentResponse,
    RecommendationResponse,
    RateScenarioResponse,
    ScenarioRequest,
)

@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    if settings.is_production:
        if settings.database_url is None:
            raise RuntimeError("DATABASE_URL must be configured in production")
        if "*" in settings.cors_origins:
            raise RuntimeError("Wildcard CORS origin '*' is strictly prohibited in production")
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    yield


app = FastAPI(
    title="LoanWise AI",
    description="AI-powered loan decision support platform",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

MAX_DOCUMENT_BYTES = 8 * 1024 * 1024


def _loan_inputs(request: LoanCalculationRequest) -> LoanInputs:
    return LoanInputs(
        principal=request.loan_amount,
        annual_interest_rate=request.annual_interest_rate,
        tenure_months=request.tenure_months,
        processing_fee=request.processing_fee,
        other_charges=request.other_charges,
    )


def _handle_domain_error(operation: Callable[[], object]) -> object:
    try:
        return operation()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/")
async def root():
    return {
        "message": "LoanWise AI API is running",
        "version": "0.1.0",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy"
    }


@app.post("/api/v1/loans/calculate", response_model=LoanSummaryResponse, tags=["loans"])
async def calculate_loan(request: LoanCalculationRequest) -> object:
    summary = _handle_domain_error(lambda: calculate_summary(_loan_inputs(request)))
    persist_calculation_if_configured(
        calculation_type="loan_summary",
        inputs=request.model_dump(mode="json"),
        outputs=summary.__dict__,
    )
    return summary


@app.post("/api/v1/loans/amortization", response_model=list[AmortizationEntryResponse], tags=["loans"])
async def calculate_amortization(request: LoanCalculationRequest) -> object:
    return _handle_domain_error(lambda: generate_amortization_schedule(_loan_inputs(request)))


@app.post("/api/v1/loans/affordability", response_model=AffordabilityResponse, tags=["loans"])
async def calculate_affordability(request: AffordabilityRequest) -> object:
    return _handle_domain_error(
        lambda: analyse_affordability(
            request.monthly_income,
            request.existing_emis,
            request.proposed_emi,
            request.estimated_monthly_expenses,
        )
    )


@app.post("/api/v1/loans/prepayment", response_model=PrepaymentResponse, tags=["loans"])
async def calculate_prepayment(request: PrepaymentRequest) -> object:
    result = _handle_domain_error(
        lambda: simulate_one_time_prepayment(
            _loan_inputs(request),
            prepayment_amount=request.prepayment_amount,
            prepayment_month=request.prepayment_month,
        )
    )
    return {
        **result.__dict__,
        "assumptions": ["Prepayment penalties are not included unless lender terms are provided."],
    }


@app.post(
    "/api/v1/loans/scenario",
    response_model=list[RateScenarioResponse],
    tags=["loans"],
)
async def calculate_rate_scenario(request: ScenarioRequest) -> object:
    return _handle_domain_error(lambda: simulate_rate_scenarios(_loan_inputs(request), tuple(request.rate_changes)))


@app.post("/api/v1/loans/compare", response_model=RecommendationResponse, tags=["loans"])
async def compare_loans(request: CompareRequest) -> object:
    def operation() -> object:
        offers = tuple(
            LoanOffer(
                lender=item.lender,
                loan_type=item.loan_type,
                principal=item.loan_amount,
                annual_interest_rate=item.annual_interest_rate,
                tenure_months=item.tenure_months,
                processing_fee=item.processing_fee,
                other_charges=item.other_charges,
                rate_type=item.rate_type,
                prepayment_terms=item.prepayment_terms,
                foreclosure_terms=item.foreclosure_terms,
                source_url=item.source_url,
                retrieved_at=item.retrieved_at,
                verified_at=item.verified_at,
                is_demo=item.is_demo,
            )
            for item in request.offers
        )
        return recommend_offer(offers, request.objective)
    return _handle_domain_error(operation)


@app.post("/api/v1/documents/analyze", response_model=DocumentAnalysisResponse, tags=["documents"])
async def analyse_document(file: UploadFile = File(...)) -> object:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="Only PDF loan/KFS documents are accepted.")
    content = await file.read(MAX_DOCUMENT_BYTES + 1)
    if len(content) > MAX_DOCUMENT_BYTES:
        raise HTTPException(status_code=413, detail="Document exceeds the 8 MB limit.")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="Uploaded content is not a valid PDF.")
    try:
        fields = extract_pdf_fields(content)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Document analysis is temporarily unavailable.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Document could not be parsed.") from exc

    return {
        "filename": file.filename or "document.pdf",
        "extracted_fields": {name: DocumentFieldResponse(**value.__dict__) for name, value in fields.items()},
        "warnings": ["Missing fields are shown as not found and are never inferred."],
        "disclaimer": "Extracted values should be checked against the original lender document.",
    }


app.include_router(assistant_router)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
