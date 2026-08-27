"""
retrieval.py
------------
Low-level retrieval primitives:

  - semantic_search(): vector similarity search over document_chunks
    using pgvector, via a Postgres function `match_chunks` (see
    supabase/migrations/002_vector_search.sql).
  - keyword_search(): PostgreSQL full-text search (tsvector/ts_rank)
    over the same table, via a Postgres function `search_chunks_fts`.

Both return a normalised list of RetrievedChunk objects so that the
hybrid fusion stage (hybrid_search.py) can merge them regardless of
which retrieval method produced them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from backend.config import get_settings
from backend.rag.embeddings import generate_embedding
from backend.utils.logger import get_logger
from backend.utils.supabase_client import get_supabase

log = get_logger("retrieval")


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    semantic_score: float = 0.0
    keyword_score: float = 0.0
    fused_score: float = 0.0
    rerank_score: Optional[float] = None
    document_title: str = ""
    document_type: str = ""
    jurisdiction: str = ""
    country: str = ""
    source_url: str = ""
    page: Optional[int] = None
    section: Optional[str] = None


def semantic_search(query: str, top_k: int | None = None, filters: dict | None = None) -> list[RetrievedChunk]:
    """
    Embeds the query and calls the `match_chunks` Postgres RPC
    function, which performs cosine-distance vector search over
    `document_chunks.embedding` (pgvector).
    """
    settings = get_settings()
    top_k = top_k or settings.semantic_top_k
    supabase = get_supabase()
    if supabase is None:
        log.warning("Supabase unavailable - semantic_search returning no results.")
        return []

    query_embedding = generate_embedding(query)

    try:
        response = supabase.rpc(
            "match_chunks",
            {
                "query_embedding": query_embedding,
                "match_count": top_k,
                "filter_country": (filters or {}).get("country"),
                "filter_document_type": (filters or {}).get("document_type"),
            },
        ).execute()
        rows = response.data or []
    except Exception as exc:
        log.error("semantic_search RPC failed: %s", exc)
        return []

    results = []
    for row in rows:
        results.append(_row_to_chunk(row, semantic_score=row.get("similarity", 0.0)))
    return results


def keyword_search(query: str, top_k: int | None = None, filters: dict | None = None) -> list[RetrievedChunk]:
    """
    Calls the `search_chunks_fts` Postgres RPC function, which runs a
    PostgreSQL full-text search (ts_rank over a tsvector column) for
    keyword/lexical matches - important for exact legal terms,
    section numbers, and proper nouns that embeddings can miss.
    """
    settings = get_settings()
    top_k = top_k or settings.keyword_top_k
    supabase = get_supabase()
    if supabase is None:
        log.warning("Supabase unavailable - keyword_search returning no results.")
        return []

    try:
        response = supabase.rpc(
            "search_chunks_fts",
            {
                "query_text": query,
                "match_count": top_k,
                "filter_country": (filters or {}).get("country"),
                "filter_document_type": (filters or {}).get("document_type"),
            },
        ).execute()
        rows = response.data or []
    except Exception as exc:
        log.error("keyword_search RPC failed: %s", exc)
        return []

    results = []
    for row in rows:
        results.append(_row_to_chunk(row, keyword_score=row.get("rank", 0.0)))
    return results


def _row_to_chunk(row: dict, semantic_score: float = 0.0, keyword_score: float = 0.0) -> RetrievedChunk:
    metadata = row.get("metadata") or {}
    return RetrievedChunk(
        chunk_id=str(row.get("id")),
        document_id=str(row.get("document_id")),
        content=row.get("content", ""),
        metadata=metadata,
        semantic_score=float(semantic_score or 0.0),
        keyword_score=float(keyword_score or 0.0),
        document_title=row.get("document_title") or metadata.get("title", ""),
        document_type=row.get("document_type") or metadata.get("document_type", ""),
        jurisdiction=row.get("jurisdiction") or metadata.get("jurisdiction", ""),
        country=row.get("country") or metadata.get("country", ""),
        source_url=row.get("source_url") or metadata.get("source_url", ""),
        page=row.get("page") or metadata.get("page"),
        section=row.get("section") or metadata.get("section"),
    )
