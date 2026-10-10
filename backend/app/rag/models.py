"""Domain models and schemas for Grounded Financial RAG."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

SourceType = Literal["regulatory", "lender_disclosure", "educational"]


class SourceCitation(BaseModel):
    """Traceable citation returned with assistant responses."""
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., description="Title of the cited source document")
    url: str | None = Field(default=None, description="Official verifiable URL of the source")
    publisher: str = Field(..., description="Publishing authority or institution (e.g. Reserve Bank of India)")
    source_type: SourceType = Field(..., description="Classification: regulatory, lender_disclosure, or educational")
    excerpt: str | None = Field(default=None, description="Verbatim or concise supporting passage from source")
    published_date: str | None = Field(default=None, description="Official publication date (YYYY-MM-DD) if known")
    verified_date: str | None = Field(default=None, description="Date source was last verified (YYYY-MM-DD)")
    is_potentially_stale: bool = Field(default=False, description="True if source terms may be outdated")


class SourceDocument(BaseModel):
    """Curated knowledge document with verified metadata."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique slug or identifier for document")
    title: str = Field(..., description="Official document title")
    url: str | None = Field(default=None, description="Official source URL")
    publisher: str = Field(..., description="Authoritative publisher name")
    source_type: SourceType = Field(..., description="Classification: regulatory, lender_disclosure, or educational")
    publication_date: str | None = Field(default=None, description="Publication date (YYYY-MM-DD)")
    retrieval_date: str = Field(..., description="Date document was retrieved into LoanWise (YYYY-MM-DD)")
    last_verified_date: str | None = Field(default=None, description="Date terms were last verified (YYYY-MM-DD)")
    document_version: str | None = Field(default=None, description="Circular or version identifier")
    content: str = Field(..., description="Full text content of document")


class SourceChunk(BaseModel):
    """Searchable chunk linked traceably to a parent SourceDocument."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique chunk ID format: doc_id#chunk_idx")
    document_id: str = Field(..., description="ID of the parent SourceDocument")
    chunk_index: int = Field(..., description="Index of this chunk within parent document")
    title: str = Field(..., description="Title of the source document")
    url: str | None = Field(default=None, description="Official source URL")
    publisher: str = Field(..., description="Publisher name")
    source_type: SourceType = Field(..., description="regulatory | lender_disclosure | educational")
    publication_date: str | None = Field(default=None)
    retrieval_date: str = Field(...)
    last_verified_date: str | None = Field(default=None)
    document_version: str | None = Field(default=None)
    text: str = Field(..., description="Chunk content text")
    keywords: list[str] = Field(default_factory=list, description="Extracted domain keywords for indexing")
    is_potentially_stale: bool = Field(default=False, description="Whether lender terms require re-verification")


class RetrievalResult(BaseModel):
    """Retrieval search match with relevance scoring."""
    model_config = ConfigDict(extra="forbid")

    chunk: SourceChunk
    score: float = Field(..., description="Computed BM25/hybrid relevance score")
