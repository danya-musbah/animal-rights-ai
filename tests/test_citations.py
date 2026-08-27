"""
test_citations.py
-------------------
Tests for backend/rag/citations.py: citation extraction and mapping from
[n] markers back to retrieved chunks, ensuring no fabricated citations.
"""

from backend.rag.citations import build_citations, extract_cited_indices
from backend.rag.retrieval import RetrievedChunk


def make_chunk(i: int) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=f"chunk-{i}",
        document_id=f"doc-{i}",
        content=f"Content of chunk {i}.",
        document_title=f"Document {i}",
        rerank_score=0.9 - (i * 0.1),
    )


def test_extract_cited_indices_basic():
    text = "Animals have protections [1] under this law [2]. See also [1]."
    indices = extract_cited_indices(text)
    assert indices == [1, 2]  # de-duplicated, in first-seen order


def test_extract_cited_indices_no_citations():
    assert extract_cited_indices("No citations here.") == []


def test_build_citations_maps_only_cited_chunks():
    chunks = [make_chunk(1), make_chunk(2), make_chunk(3)]
    answer = "This is protected [1] and also discussed [3]."
    citations = build_citations(chunks, answer)
    cited_docs = {c.document_id for c in citations}
    assert cited_docs == {"doc-1", "doc-3"}


def test_build_citations_ignores_out_of_range_indices():
    chunks = [make_chunk(1)]
    answer = "This references a citation that does not exist [5]."
    citations = build_citations(chunks, answer)
    assert citations == []  # [5] must never map to chunk 1


def test_build_citations_falls_back_to_all_chunks_when_none_cited():
    chunks = [make_chunk(1), make_chunk(2)]
    answer = "This answer has no bracket citations at all."
    citations = build_citations(chunks, answer)
    assert len(citations) == 2


def test_citations_never_exceed_retrieved_chunk_count():
    chunks = [make_chunk(1), make_chunk(2)]
    answer = "[1] [2] [3] [4]"
    citations = build_citations(chunks, answer)
    assert all(c.citation_index <= len(chunks) for c in citations)
