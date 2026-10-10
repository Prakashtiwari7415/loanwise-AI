"""Conservative KFS/offer PDF extraction. Missing data is never guessed."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedField:
    value: str | None
    confidence: str


_FIELD_PATTERNS = {
    "lender": r"(?:lender(?:'s)? name|lender|bank name|financier|institution)\s*[:\-]?\s*([A-Za-z0-9\s&.,'-]+?)(?:\n|\r|\t|,|;|$)",
    "loan_amount": r"(?:loan amount|amount financed|principal amount|sanctioned amount)\s*[:\-]?\s*(₹|rs\.?\s*)?([\d,]+(?:\.\d{1,2})?)",
    "interest_rate": r"(?:interest rate|rate of interest|roi)\s*[:\-]?\s*([\d.]+\s*%?)",
    "tenure": r"(?:tenure|loan term|loan duration)\s*[:\-]?\s*(\d+\s*(?:months?|years?|yrs?|m))",
    "emi": r"(?:emi|monthly instal(?:l)?ment|monthly payment)\s*[:\-]?\s*(₹|rs\.?\s*)?([\d,]+(?:\.\d{1,2})?)",
    "processing_fee": r"(?:processing fee(?:s)?|upfront fee(?:s)?)\s*[:\-]?\s*(₹|rs\.?\s*)?([\d,]+(?:\.\d{1,2})?\s*%?)",
    "other_charges": r"(?:other charges|documentation charges|stamp duty|administrative fee)\s*[:\-]?\s*(₹|rs\.?\s*)?([\d,]+(?:\.\d{1,2})?)",
    "apr": r"(?:apr|annual percentage rate)\s*[:\-]?\s*([\d.]+\s*%?)",
}


def extract_known_fields(text: str) -> dict[str, ExtractedField]:
    fields: dict[str, ExtractedField] = {}
    for name, pattern in _FIELD_PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE)
        val = "".join(group for group in match.groups() if group).strip() if match else None
        fields[name] = ExtractedField(
            value=val if val else None,
            confidence="high" if (match and val) else "not_found",
        )
    lower_text = text.lower()
    fields["rate_type"] = ExtractedField(
        value="floating" if "floating" in lower_text else "fixed" if "fixed" in lower_text else None,
        confidence="medium" if ("floating" in lower_text or "fixed" in lower_text) else "not_found",
    )
    fields["prepayment_terms"] = ExtractedField(
        value="Needs review" if "prepayment" in lower_text else None,
        confidence="needs_review" if "prepayment" in lower_text else "not_found",
    )
    fields["foreclosure_terms"] = ExtractedField(
        value="Needs review" if "foreclosure" in lower_text else None,
        confidence="needs_review" if "foreclosure" in lower_text else "not_found",
    )
    return fields


def extract_pdf_fields(pdf_bytes: bytes) -> dict[str, ExtractedField]:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:  # pragma: no cover - depends on deployment extras
        raise RuntimeError("PDF processing is unavailable; install PyMuPDF.") from exc
    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Malformed or unreadable PDF: {exc}") from exc

    try:
        if document.is_encrypted:
            raise ValueError("Document is encrypted or password-protected.")
        if document.page_count == 0:
            raise ValueError("Document contains no pages.")
        text = "\n".join(page.get_text() for page in document)
    finally:
        document.close()
    return extract_known_fields(text)
