"""
reranker.py
-----------
Second-stage reranking of the fused hybrid-search candidate pool.

Two strategies, chosen based on configuration:

  1. API reranker (RERANKER_PROVIDER != "none"): calls a dedicated
     cross-encoder style reranking API (e.g. Cohere Rerank) that
     scores (query, chunk) pairs directly - generally the highest
     quality option.

  2. Heuristic fallback (default, no extra API key required): a
     transparent weighted-score reranker that combines the fused
     RRF score with lexical term-overlap between the query and the
     chunk content. This keeps the architecture fully modular - the
     rest of the pipeline does not need to know which strategy ran.

Either way, the reranker narrows a pool of ~20-40 fused candidates
down to the top `final_top_k` chunks that are actually sent to the
LLM, which is essential both for answer quality and for cost/latency.
"""

from __future__ import annotations

import re

import httpx

from backend.config import get_settings
from backend.rag.retrieval import RetrievedChunk
from backend.utils.logger import get_logger

log = get_logger("reranker")

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def _heuristic_rerank(query: str, candidates: list[RetrievedChunk]) -> list[RetrievedChunk]:
    query_terms = _tokenize(query)
    if not query_terms:
        for c in candidates:
            c.rerank_score = c.fused_score
        return sorted(candidates, key=lambda c: c.rerank_score, reverse=True)

    for chunk in candidates:
        chunk_terms = _tokenize(chunk.content)
        overlap = len(query_terms & chunk_terms) / len(query_terms)
        # Blend fused rank score (already reflects both retrieval methods)
        # with direct lexical overlap against this specific chunk.
        chunk.rerank_score = (0.65 * chunk.fused_score * 10) + (0.35 * overlap)

    return sorted(candidates, key=lambda c: c.rerank_score, reverse=True)


def _api_rerank(query: str, candidates: list[RetrievedChunk]) -> list[RetrievedChunk]:
    settings = get_settings()
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                "https://api.cohere.ai/v1/rerank",
                headers={"Authorization": f"Bearer {settings.reranker_api_key}"},
                json={
                    "model": settings.reranker_model or "rerank-english-v3.0",
                    "query": query,
                    "documents": [c.content for c in candidates],
                    "top_n": len(candidates),
                },
            )
            resp.raise_for_status()
            data = resp.json()
        for result in data.get("results", []):
            idx = result["index"]
            candidates[idx].rerank_score = result["relevance_score"]
        return sorted(candidates, key=lambda c: (c.rerank_score or 0.0), reverse=True)
    except Exception as exc:
        log.warning("API reranker failed (%s) - falling back to heuristic reranking.", exc)
        return _heuristic_rerank(query, candidates)


def rerank(query: str, candidates: list[RetrievedChunk], top_k: int | None = None) -> list[RetrievedChunk]:
    settings = get_settings()
    top_k = top_k or settings.final_top_k

    if not candidates:
        return []

    if settings.reranker_provider == "cohere" and settings.reranker_api_key:
        ranked = _api_rerank(query, candidates)
    else:
        ranked = _heuristic_rerank(query, candidates)

    return ranked[:top_k]
