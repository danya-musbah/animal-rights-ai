"""
hybrid_search.py
-----------------
Merges semantic (vector) and keyword (full-text) search results using
Reciprocal Rank Fusion (RRF), a simple and well-established technique
for combining ranked lists from heterogeneous retrieval methods
without needing to normalise incomparable raw scores.

    RRF_score(d) = sum over each ranking r that contains d of:
                       1 / (k + rank_r(d))

k=60 is the standard constant from the original RRF paper (Cormack
et al., 2009) and works well in practice without tuning.

Pipeline:
    Query
     ├── semantic_search()  -> ranked list A
     └── keyword_search()   -> ranked list B
              |
              v
        reciprocal rank fusion + de-duplication by chunk_id
              |
              v
        candidate pool passed to the reranker
"""

from __future__ import annotations

from backend.rag.retrieval import RetrievedChunk, keyword_search, semantic_search
from backend.utils.logger import get_logger

log = get_logger("hybrid_search")

RRF_K = 60


def hybrid_search(query: str, filters: dict | None = None) -> list[RetrievedChunk]:
    semantic_results = semantic_search(query, filters=filters)
    keyword_results = keyword_search(query, filters=filters)

    log.info(
        "hybrid_search: %d semantic candidates, %d keyword candidates",
        len(semantic_results),
        len(keyword_results),
    )

    merged: dict[str, RetrievedChunk] = {}
    rrf_scores: dict[str, float] = {}

    for rank, chunk in enumerate(semantic_results, start=1):
        merged[chunk.chunk_id] = chunk
        rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0.0) + 1.0 / (RRF_K + rank)

    for rank, chunk in enumerate(keyword_results, start=1):
        if chunk.chunk_id in merged:
            existing = merged[chunk.chunk_id]
            existing.keyword_score = chunk.keyword_score
        else:
            merged[chunk.chunk_id] = chunk
        rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0.0) + 1.0 / (RRF_K + rank)

    for chunk_id, chunk in merged.items():
        chunk.fused_score = rrf_scores[chunk_id]

    fused_list = sorted(merged.values(), key=lambda c: c.fused_score, reverse=True)
    return fused_list
