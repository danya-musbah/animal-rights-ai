"""
api/search.py
-------------
POST /api/search

A dedicated semantic/hybrid search endpoint (distinct from /api/chat)
that returns ranked document/chunk matches with relevance scores and
excerpts, for the standalone Search page and the Knowledge Base
explorer's search box.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.rag.hybrid_search import hybrid_search
from backend.rag.reranker import rerank

router = APIRouter()


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    country: Optional[str] = None
    document_type: Optional[str] = None
    top_k: int = Field(default=10, ge=1, le=30)


class SearchResultItem(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    document_type: str
    jurisdiction: str
    country: str
    source_url: str
    section: Optional[str]
    page: Optional[int]
    excerpt: str
    similarity: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]


@router.post("/search", response_model=SearchResponse)
def search(request: SearchRequest) -> SearchResponse:
    filters = {}
    if request.country:
        filters["country"] = request.country
    if request.document_type:
        filters["document_type"] = request.document_type

    fused = hybrid_search(request.query, filters=filters or None)
    ranked = rerank(request.query, fused, top_k=request.top_k)

    results = [
        SearchResultItem(
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            document_title=c.document_title,
            document_type=c.document_type,
            jurisdiction=c.jurisdiction,
            country=c.country,
            source_url=c.source_url,
            section=c.section,
            page=c.page,
            excerpt=c.content[:400],
            similarity=round(c.rerank_score or c.fused_score, 4),
        )
        for c in ranked
    ]
    return SearchResponse(query=request.query, results=results)
