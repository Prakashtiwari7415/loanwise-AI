"""Search indexing and grounded retrieval using SQLite FTS5 BM25."""

from __future__ import annotations

import logging
import re
import sqlite3
from typing import Sequence

from app.rag.chunker import chunk_document
from app.rag.corpus import CURATED_SOURCES
from app.rag.models import RetrievalResult, SourceCitation, SourceChunk, SourceDocument

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "a", "about", "an", "and", "are", "as", "at", "be", "by", "can",
    "do", "does", "for", "from", "how", "i", "in", "is", "it", "me",
    "my", "no", "not", "of", "on", "or", "so", "tell", "the", "their",
    "this", "to", "was", "what", "when", "where", "which", "who", "why",
    "will", "with", "you", "your",
}

# Minimum BM25 score to consider a result relevant (SQLite FTS5 bm25 is negative; positive score = -bm25)
MIN_RELEVANCE_SCORE = 1.0


class KnowledgeRetriever:
    """In-memory SQLite FTS5 search index with BM25 ranking and confidence thresholding."""

    def __init__(
        self,
        chunks: Sequence[SourceChunk] | None = None,
        min_score: float = MIN_RELEVANCE_SCORE,
    ) -> None:
        self.min_score = min_score
        self._chunks_by_id: dict[str, SourceChunk] = {}
        self._con = sqlite3.connect(":memory:", check_same_thread=False)
        self._con.execute(
            "CREATE VIRTUAL TABLE chunk_index USING fts5(chunk_id, title, text, keywords);"
        )
        if chunks:
            self.index_chunks(chunks)

    def index_chunks(self, chunks: Sequence[SourceChunk]) -> None:
        """Add chunks to the in-memory search index."""
        for chunk in chunks:
            self._chunks_by_id[chunk.id] = chunk
            self._con.execute(
                "INSERT INTO chunk_index(chunk_id, title, text, keywords) VALUES (?, ?, ?, ?)",
                (
                    chunk.id,
                    chunk.title,
                    chunk.text,
                    " ".join(chunk.keywords),
                ),
            )
        self._con.commit()

    def clear(self) -> None:
        """Clear all indexed chunks."""
        self._chunks_by_id.clear()
        self._con.execute("DELETE FROM chunk_index;")
        self._con.commit()

    def _sanitize_query(self, query: str) -> list[str]:
        """Extract meaningful alphanumeric query tokens, filtering stop words and FTS syntax."""
        cleaned = re.sub(r"[^\w\s-]", " ", query)
        raw_tokens = cleaned.split()
        tokens = [
            t.lower() for t in raw_tokens
            if len(t) >= 2 and t.lower() not in STOP_WORDS
        ]
        return tokens

    def retrieve(self, query: str, top_k: int = 3) -> list[RetrievalResult]:
        """Retrieve most relevant chunks for a query or return empty list if relevance is inadequate."""
        tokens = self._sanitize_query(query)
        if not tokens:
            return []

        # Construct safe FTS match expression: term prefix matching
        # e.g., 'foreclosure*' OR 'prepayment*'
        safe_terms = [f'"{t}"*' for t in tokens if re.match(r"^[a-zA-Z0-9_-]+$", t)]
        if not safe_terms:
            return []

        match_expr = " OR ".join(safe_terms)

        try:
            cursor = self._con.execute(
                "SELECT chunk_id, bm25(chunk_index) as rank FROM chunk_index "
                "WHERE chunk_index MATCH ? ORDER BY rank ASC LIMIT ?",
                (match_expr, top_k * 2),
            )
            rows = cursor.fetchall()
        except sqlite3.OperationalError as exc:
            logger.warning("FTS query failed for expression %r: %s", match_expr, exc)
            return []

        if not rows:
            return []

        results: list[RetrievalResult] = []
        for chunk_id, rank in rows:
            chunk = self._chunks_by_id.get(chunk_id)
            if not chunk:
                continue

            # SQLite FTS5 bm25 returns negative values where lower is better
            score = -float(rank)

            # Bonus for exact keyword matches in title or chunk keywords
            q_lower = query.lower()
            keyword_overlap = sum(1 for kw in chunk.keywords if kw in q_lower)
            adjusted_score = score + (keyword_overlap * 0.5)

            if adjusted_score >= self.min_score:
                results.append(RetrievalResult(chunk=chunk, score=adjusted_score))

        # Sort descending by adjusted score
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]


def build_default_retriever(documents: Sequence[SourceDocument] | None = None) -> KnowledgeRetriever:
    """Build a KnowledgeRetriever pre-populated with curated source documents."""
    docs = documents or CURATED_SOURCES
    all_chunks: list[SourceChunk] = []
    for doc in docs:
        all_chunks.extend(chunk_document(doc))
    return KnowledgeRetriever(chunks=all_chunks)


_DEFAULT_RETRIEVER: KnowledgeRetriever | None = None


def get_default_retriever() -> KnowledgeRetriever:
    """Singleton getter for default pre-populated knowledge retriever."""
    global _DEFAULT_RETRIEVER
    if _DEFAULT_RETRIEVER is None:
        _DEFAULT_RETRIEVER = build_default_retriever()
    return _DEFAULT_RETRIEVER


def to_citation(result: RetrievalResult) -> SourceCitation:
    """Convert a retrieval search result to a SourceCitation for API response."""
    chunk = result.chunk
    excerpt = chunk.text.strip()
    if len(excerpt) > 300:
        excerpt = excerpt[:297].rstrip() + "..."

    return SourceCitation(
        title=chunk.title,
        url=chunk.url,
        publisher=chunk.publisher,
        source_type=chunk.source_type,
        excerpt=excerpt,
        published_date=chunk.publication_date,
        verified_date=chunk.last_verified_date,
        is_potentially_stale=chunk.is_potentially_stale,
    )
