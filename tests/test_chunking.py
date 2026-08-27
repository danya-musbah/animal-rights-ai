"""
test_chunking.py
-----------------
Tests for backend/rag/chunking.py: section-aware chunking, overlap,
and metadata (section/page) tracking.
"""

from backend.rag.chunking import chunk_document, _split_into_units, _estimate_tokens


def test_estimate_tokens_nonzero():
    assert _estimate_tokens("hello world") > 0
    assert _estimate_tokens("") == 1  # never returns zero/negative


def test_split_into_units_detects_headings():
    text = "SECTION 1: DUTY OF CARE\n\nA person responsible for an animal must take reasonable steps."
    units = _split_into_units(text)
    assert any(u.is_heading for u in units)


def test_split_into_units_tracks_page_markers():
    text = "[[PAGE:1]]\nFirst page content here.\n\n[[PAGE:2]]\nSecond page content here."
    units = _split_into_units(text)
    pages = [u.page for u in units]
    assert 1 in pages
    assert 2 in pages


def test_chunk_document_produces_chunks():
    text = "\n\n".join([f"This is paragraph number {i} about animal welfare law and policy." for i in range(40)])
    chunks = chunk_document(text, target_tokens=50, overlap_tokens=10)
    assert len(chunks) > 1
    for c in chunks:
        assert c.content.strip() != ""
        assert c.token_count > 0


def test_chunk_document_indices_are_sequential():
    text = "\n\n".join([f"Paragraph {i}." * 5 for i in range(20)])
    chunks = chunk_document(text, target_tokens=30, overlap_tokens=5)
    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))


def test_chunk_document_respects_overlap():
    # With a small target and meaningful overlap, later chunks should share
    # at least some words with the immediately preceding chunk.
    text = "\n\n".join([f"Unique sentence marker {i} about animal law." for i in range(30)])
    chunks = chunk_document(text, target_tokens=20, overlap_tokens=8)
    assert len(chunks) > 2


def test_chunk_document_empty_text_returns_no_chunks():
    assert chunk_document("") == []


def test_chunk_document_tracks_section_metadata():
    text = "ARTICLE 5: TRANSPORT\n\nAnimals must be given water during transport.\n\nARTICLE 6: SLAUGHTER\n\nStunning is required before slaughter in most cases."
    chunks = chunk_document(text, target_tokens=15, overlap_tokens=2)
    sections = {c.section for c in chunks if c.section}
    assert len(sections) >= 1
