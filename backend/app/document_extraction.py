"""Conservative KFS/offer PDF extraction. Missing data is never guessed."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedField:
    value: str | None
    confidence: str


_FIELD_PATTERNS = {
    "loan_amount": r"(?:loan amount|amount financed)\s*[:\-]?\s*(₹|rs\.?\s*)?([\d,]+(?:\.\d{1,2})?)",
    "interest_rate": r"(?:interest rate|rate of interest)\s*[:\-]?\s*([\d.]+\s*%?)",
    "tenure": r"(?:tenure|loan term)\s*[:\-]?\s*(\d+\s*(?:months?|years?))",
    "emi": r"(?:emi|monthly instal(?:l)?ment)\s*[:\-]?\s*(₹|rs\.?\s*)?([\d,]+(?:\.\d{1,2})?)",
    "processing_fee": r"(?:processing fee)\s*[:\-]?\s*(₹|rs\.?\s*)?([\d,]+(?:\.\d{1,2})?\s*%?)",
    "apr": r"(?:apr|annual percentage rate)\s*[:\-]?\s*([\d.]+\s*%?)",
}


def extract_known_fields(text: str) -> dict[str, ExtractedField]:
    fields: dict[str, ExtractedField] = {}
    for name, pattern in _FIELD_PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE)
        fields[name] = ExtractedField(
            value="".join(group for group in match.groups() if group).strip() if match else None,
            confidence="high" if match else "not_found",
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
    return fields


def extract_pdf_fields(pdf_bytes: bytes) -> dict[str, ExtractedField]:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:  # pragma: no cover - depends on deployment extras
        raise RuntimeError("PDF processing is unavailable; install PyMuPDF.") from exc
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        text = "\n".join(page.get_text() for page in document)
    finally:
        document.close()
    return extract_known_fields(text)
