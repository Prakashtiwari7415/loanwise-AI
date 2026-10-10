"""Document chunking and metadata preservation pipeline."""

from __future__ import annotations

from datetime import date, datetime
import re

from app.rag.models import SourceChunk, SourceDocument

# Stale threshold for lender disclosures in days (lender rates change frequently)
LENDER_STALE_THRESHOLD_DAYS = 90

DOMAIN_KEYWORD_PATTERNS = [
    r"\bkfs\b",
    r"\bkey fact statement\b",
    r"\bapr\b",
    r"\bannual percentage rate\b",
    r"\bforeclosure\b",
    r"\bprepayment\b",
    r"\bpre-payment\b",
    r"\bpenalty\b",
    r"\bpenal charges\b",
    r"\bpenal interest\b",
    r"\bfloating\b",
    r"\bfixed\b",
    r"\bflat rate\b",
    r"\breducing balance\b",
    r"\bdiminishing balance\b",
    r"\bmclr\b",
    r"\beblr\b",
    r"\bcooling-off\b",
    r"\blook-up\b",
    r"\bprocessing fee\b",
    r"\bvalidity\b",
    r"\bamortization\b",
    r"\btenure\b",
    r"\brbi\b",
    r"\bsbi\b",
]


def _extract_keywords(text: str) -> list[str]:
    """Extract domain keywords present in text."""
    lower = text.lower()
    matches: list[str] = []
    for pat in DOMAIN_KEYWORD_PATTERNS:
        found = re.findall(pat, lower)
        if found:
            matches.extend(set(found))
    return sorted(set(matches))


def _compute_is_stale(doc: SourceDocument, reference_date: date | None = None) -> bool:
    """Determine if a document is potentially stale (especially lender rate disclosures)."""
    if doc.source_type != "lender_disclosure":
        return False

    if not doc.last_verified_date:
        return True

    try:
        verified = datetime.strptime(doc.last_verified_date, "%Y-%m-%d").date()
        ref_date = reference_date or date.today()
        delta_days = (ref_date - verified).days
        return delta_days >= LENDER_STALE_THRESHOLD_DAYS
    except ValueError:
        return True


def chunk_document(doc: SourceDocument) -> list[SourceChunk]:
    """Split a SourceDocument into searchable chunks preserving complete traceable metadata."""
    raw_content = doc.content.strip()
    # Split on numbered sections or double newlines
    raw_paragraphs = re.split(r"\n\s*\n|\n(?=\d+\.\s+)", raw_content)

    paragraphs = [p.strip() for p in raw_paragraphs if p.strip()]
    if not paragraphs:
        paragraphs = [raw_content]

    is_stale = _compute_is_stale(doc)
    chunks: list[SourceChunk] = []

    for idx, para in enumerate(paragraphs):
        chunk_id = f"{doc.id}#{idx}"
        keywords = _extract_keywords(f"{doc.title} {para}")

        chunk = SourceChunk(
            id=chunk_id,
            document_id=doc.id,
            chunk_index=idx,
            title=doc.title,
            url=doc.url,
            publisher=doc.publisher,
            source_type=doc.source_type,
            publication_date=doc.publication_date,
            retrieval_date=doc.retrieval_date,
            last_verified_date=doc.last_verified_date,
            document_version=doc.document_version,
            text=para,
            keywords=keywords,
            is_potentially_stale=is_stale,
        )
        chunks.append(chunk)

    return chunks
