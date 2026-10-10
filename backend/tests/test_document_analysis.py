import fitz
import httpx
import pytest

from app.document_extraction import extract_known_fields, extract_pdf_fields
from app.main import MAX_DOCUMENT_BYTES, app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _create_sample_pdf(text: str, encrypt: bool = False) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text)
    if encrypt:
        return doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="pass", user_pw="pass")
    return doc.tobytes()


@pytest.mark.anyio
async def test_document_upload_success_extracts_all_fields() -> None:
    pdf_text = (
        "Lender: State Bank of India\n"
        "Loan Amount: Rs. 10,00,000\n"
        "Interest Rate: 8.50%\n"
        "Tenure: 60 months\n"
        "EMI: Rs. 20,517\n"
        "Processing Fee: Rs. 2,500\n"
        "Other Charges: Rs. 1,000\n"
        "APR: 8.85%\n"
        "Floating rate personal loan. Prepayment and foreclosure allowed subject to guidelines."
    )
    pdf_bytes = _create_sample_pdf(pdf_text)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/documents/analyze",
            files={"file": ("sbi_kfs.pdf", pdf_bytes, "application/pdf")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "sbi_kfs.pdf"
    assert len(body["warnings"]) > 0
    assert "disclaimer" in body

    fields = body["extracted_fields"]
    assert fields["lender"]["value"] == "State Bank of India"
    assert fields["lender"]["confidence"] == "high"
    assert "10,00,000" in fields["loan_amount"]["value"]
    assert fields["loan_amount"]["confidence"] == "high"
    assert "8.50" in fields["interest_rate"]["value"]
    assert fields["interest_rate"]["confidence"] == "high"
    assert "60" in fields["tenure"]["value"]
    assert fields["tenure"]["confidence"] == "high"
    assert "20,517" in fields["emi"]["value"]
    assert fields["emi"]["confidence"] == "high"
    assert "2,500" in fields["processing_fee"]["value"]
    assert fields["processing_fee"]["confidence"] == "high"
    assert "1,000" in fields["other_charges"]["value"]
    assert fields["other_charges"]["confidence"] == "high"
    assert "8.85" in fields["apr"]["value"]
    assert fields["apr"]["confidence"] == "high"
    assert fields["rate_type"]["value"] == "floating"
    assert fields["rate_type"]["confidence"] == "medium"
    assert fields["prepayment_terms"]["confidence"] == "needs_review"
    assert fields["foreclosure_terms"]["confidence"] == "needs_review"


@pytest.mark.anyio
async def test_document_upload_partial_fields_shows_not_found() -> None:
    pdf_text = "Sanctioned Amount: Rs. 500,000\nAnnual Interest Rate: 10.5%"
    pdf_bytes = _create_sample_pdf(pdf_text)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/documents/analyze",
            files={"file": ("partial.pdf", pdf_bytes, "application/pdf")},
        )

    assert response.status_code == 200
    fields = response.json()["extracted_fields"]
    assert "500,000" in fields["loan_amount"]["value"]
    assert fields["loan_amount"]["confidence"] == "high"
    assert fields["interest_rate"]["value"] == "10.5%"
    assert fields["interest_rate"]["confidence"] == "high"
    assert fields["tenure"]["confidence"] == "not_found"
    assert fields["tenure"]["value"] is None
    assert fields["emi"]["confidence"] == "not_found"
    assert fields["processing_fee"]["confidence"] == "not_found"
    assert fields["other_charges"]["confidence"] == "not_found"
    assert fields["apr"]["confidence"] == "not_found"
    assert fields["rate_type"]["confidence"] == "not_found"


@pytest.mark.anyio
async def test_document_upload_rejects_non_pdf_content_type() -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/documents/analyze",
            files={"file": ("photo.jpg", b"%PDF-1.4 mock", "image/jpeg")},
        )
    assert response.status_code == 415
    assert "Only PDF" in response.json()["detail"]


@pytest.mark.anyio
async def test_document_upload_rejects_forged_pdf_header() -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/documents/analyze",
            files={"file": ("offer.pdf", b"fake binary content", "application/pdf")},
        )
    assert response.status_code == 415
    assert "not a valid PDF" in response.json()["detail"]


@pytest.mark.anyio
async def test_document_upload_rejects_oversized_pdf() -> None:
    oversized_bytes = b"%PDF-" + b"0" * (MAX_DOCUMENT_BYTES + 10)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/documents/analyze",
            files={"file": ("large.pdf", oversized_bytes, "application/pdf")},
        )
    assert response.status_code == 413
    assert "8 MB limit" in response.json()["detail"]


@pytest.mark.anyio
async def test_document_upload_rejects_malformed_pdf() -> None:
    malformed_bytes = b"%PDF-1.4\ncorrupt body data\n%%EOF"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/documents/analyze",
            files={"file": ("corrupt.pdf", malformed_bytes, "application/pdf")},
        )
    assert response.status_code == 422
    assert "Malformed or unreadable PDF" in response.json()["detail"]


@pytest.mark.anyio
async def test_document_upload_rejects_encrypted_pdf() -> None:
    encrypted_bytes = _create_sample_pdf("Secret Loan Terms", encrypt=True)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/documents/analyze",
            files={"file": ("locked.pdf", encrypted_bytes, "application/pdf")},
        )
    assert response.status_code == 422
    assert "encrypted or password-protected" in response.json()["detail"]


def test_extract_known_fields_fixed_rate() -> None:
    res = extract_known_fields("This offer provides a fixed rate across all terms.")
    assert res["rate_type"].value == "fixed"
    assert res["rate_type"].confidence == "medium"
