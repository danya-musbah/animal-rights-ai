"""
test_retrieval.py
-------------------
Tests for backend/rag/hybrid_search.py (Reciprocal Rank Fusion) and
backend/rag/reranker.py (heuristic fallback reranking), using monkeypatched
retrieval functions so no real Supabase connection is required.
"""

import backend.rag.hybrid_search as hybrid_search_module
from backend.rag.reranker import rerank
from backend.rag.retrieval import RetrievedChunk


def make_chunk(chunk_id, content="animal welfare transport"):
    return RetrievedChunk(chunk_id=chunk_id, document_id=f"doc-{chunk_id}", content=content)


def test_hybrid_search_merges_and_deduplicates(monkeypatch):
    semantic_results = [make_chunk("a"), make_chunk("b"), make_chunk("c")]
    keyword_results = [make_chunk("b"), make_chunk("d")]  # "b" overlaps

    monkeypatch.setattr(hybrid_search_module, "semantic_search", lambda q, filters=None: semantic_results)
    monkeypatch.setattr(hybrid_search_module, "keyword_search", lambda q, filters=None: keyword_results)

    fused = hybrid_search_module.hybrid_search("test query")
    ids = [c.chunk_id for c in fused]

    assert len(ids) == len(set(ids))  # no duplicates
    assert set(ids) == {"a", "b", "c", "d"}


def test_hybrid_search_ranks_overlapping_chunk_higher(monkeypatch):
    # "b" appears in both semantic and keyword results, so it should fuse
    # to a higher combined RRF score than chunks appearing in only one list.
    semantic_results = [make_chunk("a"), make_chunk("b")]
    keyword_results = [make_chunk("b"), make_chunk("c")]

    monkeypatch.setattr(hybrid_search_module, "semantic_search", lambda q, filters=None: semantic_results)
    monkeypatch.setattr(hybrid_search_module, "keyword_search", lambda q, filters=None: keyword_results)

    fused = hybrid_search_module.hybrid_search("test query")
    top_id = fused[0].chunk_id
    assert top_id == "b"


def test_heuristic_reranker_prefers_lexical_overlap():
    chunks = [
        make_chunk("relevant", content="animal transport welfare requirements journey time"),
        make_chunk("irrelevant", content="unrelated topic about something else entirely"),
    ]
    for c in chunks:
        c.fused_score = 0.01  # equal fused score so overlap should decide order

    ranked = rerank("animal transport welfare requirements", chunks, top_k=2)
    assert ranked[0].chunk_id == "relevant"


def test_rerank_respects_top_k():
    chunks = [make_chunk(str(i)) for i in range(10)]
    ranked = rerank("animal welfare", chunks, top_k=3)
    assert len(ranked) == 3


def test_rerank_empty_input_returns_empty():
    assert rerank("anything", [], top_k=5) == []
