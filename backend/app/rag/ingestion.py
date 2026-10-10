"""Repeatable ingestion pipeline for curated, verified sources."""

from __future__ import annotations

import argparse
from datetime import datetime
import logging
import sys
from typing import Sequence

from app.rag.chunker import chunk_document
from app.rag.corpus import CURATED_SOURCES
from app.rag.models import SourceChunk, SourceDocument
from app.rag.retriever import KnowledgeRetriever, build_default_retriever

logger = logging.getLogger(__name__)


def validate_source_document(doc: SourceDocument) -> None:
    """Validate metadata integrity of a source document prior to ingestion."""
    if not doc.id or not doc.title or not doc.publisher or not doc.content:
        raise ValueError(f"Document {doc.id or 'unknown'} is missing required title, publisher, or content.")

    if doc.source_type not in ("regulatory", "lender_disclosure", "educational"):
        raise ValueError(f"Document {doc.id} has invalid source_type: {doc.source_type}")

    # Validate ISO date strings if provided
    for date_field, val in [
        ("publication_date", doc.publication_date),
        ("retrieval_date", doc.retrieval_date),
        ("last_verified_date", doc.last_verified_date),
    ]:
        if val is not None:
            try:
                datetime.strptime(val, "%Y-%m-%d")
            except ValueError as exc:
                raise ValueError(
                    f"Document {doc.id} has invalid {date_field} '{val}'; must be YYYY-MM-DD."
                ) from exc

    # Security check: Ensure private borrower/customer files are never ingested into public knowledge base
    lower_content = doc.content.lower()
    lower_title = doc.title.lower()
    for suspicious_term in ("borrower pan", "aadhaar", "customer loan account number", "sanction letter to mr"):
        if suspicious_term in lower_content or suspicious_term in lower_title:
            raise ValueError(
                f"Security guardrail rejected document {doc.id}: contains private customer data pattern '{suspicious_term}'."
            )


def ingest_sources(
    documents: Sequence[SourceDocument] | None = None,
    retriever: KnowledgeRetriever | None = None,
) -> list[SourceChunk]:
    """Validate, chunk, and index curated source documents into the retriever."""
    docs = documents or CURATED_SOURCES
    all_chunks: list[SourceChunk] = []

    for doc in docs:
        validate_source_document(doc)
        chunks = chunk_document(doc)
        all_chunks.extend(chunks)

    if retriever is not None:
        retriever.clear()
        retriever.index_chunks(all_chunks)

    return all_chunks


def main() -> None:
    """CLI entrypoint for repeatable source ingestion and status reporting."""
    parser = argparse.ArgumentParser(description="LoanWise Grounded RAG Source Ingestion")
    parser.add_argument("--verify-only", action="store_true", help="Validate documents without modifying index")
    args = parser.parse_args()

    print("==================================================")
    print("LoanWise AI — Grounded Financial RAG Ingestion")
    print("==================================================")

    chunks = ingest_sources(CURATED_SOURCES)
    regulatory_count = sum(1 for c in chunks if c.source_type == "regulatory")
    lender_count = sum(1 for c in chunks if c.source_type == "lender_disclosure")
    edu_count = sum(1 for c in chunks if c.source_type == "educational")
    stale_count = sum(1 for c in chunks if c.is_potentially_stale)

    print(f"Total curated source documents: {len(CURATED_SOURCES)}")
    print(f"Total verified chunks generated: {len(chunks)}")
    print(f"  - Regulatory chunks:           {regulatory_count}")
    print(f"  - Lender disclosure chunks:    {lender_count}")
    print(f"  - Financial education chunks:  {edu_count}")
    print(f"  - Flagged potentially stale:   {stale_count}")
    print("All documents validated against source metadata and security guardrails successfully.")


if __name__ == "__main__":
    main()
