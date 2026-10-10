import httpx
import pytest

from app.main import app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_calculate_loan_endpoint_returns_structured_result() -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
        "/api/v1/loans/calculate",
        json={"loan_amount": 900000, "annual_interest_rate": 9.25, "tenure_months": 60, "processing_fee": 4999},
        )
    assert response.status_code == 200
    body = response.json()
    assert float(body["emi"]) > 0
    assert float(body["total_borrowing_cost"]) > float(body["total_repayment"])


@pytest.mark.anyio
async def test_invalid_loan_request_returns_validation_error() -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/loans/calculate", json={"loan_amount": 0, "annual_interest_rate": 9, "tenure_months": 60})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_compare_warns_when_offer_terms_are_missing() -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
        "/api/v1/loans/compare",
        json={
            "objective": "lowest_total_cost",
            "offers": [
                {"lender": "Illustrative offer", "loan_amount": 500000, "annual_interest_rate": 9, "tenure_months": 36, "is_demo": True}
            ],
        },
        )
    assert response.status_code == 200
    assert response.json()["risks"]


@pytest.mark.anyio
async def test_rate_scenarios_have_a_validated_response_contract() -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/loans/scenario",
            json={"loan_amount": 500000, "annual_interest_rate": 8, "tenure_months": 36},
        )
    assert response.status_code == 200
    assert response.json()[0]["additional_monthly_cost"] == "0.00"


@pytest.mark.anyio
async def test_rate_scenarios_reject_unbounded_rate_changes() -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/loans/scenario",
            json={
                "loan_amount": 500000,
                "annual_interest_rate": 8,
                "tenure_months": 36,
                "rate_changes": [1000],
            },
        )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_document_upload_rejects_a_forged_pdf_content_type() -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/documents/analyze",
            files={"file": ("offer.pdf", b"not a PDF", "application/pdf")},
        )
    assert response.status_code == 415
    assert response.json()["detail"] == "Uploaded content is not a valid PDF."
