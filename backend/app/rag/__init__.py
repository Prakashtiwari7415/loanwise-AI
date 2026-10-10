"""Grounded Financial RAG module for LoanWise AI."""

from app.rag.chunker import chunk_document
from app.rag.corpus import CURATED_SOURCES
from app.rag.ingestion import ingest_sources
from app.rag.models import RetrievalResult, SourceCitation, SourceChunk, SourceDocument
from app.rag.retriever import KnowledgeRetriever, build_default_retriever, get_default_retriever, to_citation

__all__ = [
    "CURATED_SOURCES",
    "KnowledgeRetriever",
    "RetrievalResult",
    "SourceCitation",
    "SourceChunk",
    "SourceDocument",
    "build_default_retriever",
    "chunk_document",
    "get_default_retriever",
    "ingest_sources",
    "to_citation",
]
