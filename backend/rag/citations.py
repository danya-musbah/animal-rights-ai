"""
citations.py
------------
Maps the [n] style citation markers produced by the LLM back to the
actual retrieved chunks, and produces the structured citation/evidence
objects consumed by the frontend's evidence panel.

Citations are NEVER fabricated here: only chunks that were actually
part of the retrieved evidence set for this turn can be cited. If the
model outputs a citation number outside the retrieved range, it is
dropped rather than mapped to an arbitrary chunk.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.rag.retrieval import RetrievedChunk

CITATION_PATTERN = re.compile(r"\[(\d{1,2})\]")


@dataclass
class Citation:
    citation_index: int
    chunk_id: str
    document_id: str
    document_title: str
    document_type: str
    jurisdiction: str
    country: str
    section: str | None
    page: int | None
    source_url: str
    relevance_score: float
    excerpt: str


def extract_cited_indices(answer_text: str) -> list[int]:
    seen: list[int] = []
    for match in CITATION_PATTERN.finditer(answer_text):
        n = int(match.group(1))
        if n not in seen:
            seen.append(n)
    return seen


def build_citations(chunks: list[RetrievedChunk], answer_text: str) -> list[Citation]:
    """
    Builds citation objects for every chunk that was retrieved AND
    actually referenced by the model's answer. If the model cited
    nothing explicitly but evidence exists, all retrieved chunks are
    still returned as supporting evidence (marked with their natural
    order) so the evidence panel is never empty when evidence exists.
    """
    cited_indices = extract_cited_indices(answer_text)
    citations: list[Citation] = []

    indices_to_use = cited_indices if cited_indices else list(range(1, len(chunks) + 1))

    for idx in indices_to_use:
        if idx < 1 or idx > len(chunks):
            continue  # never map to a non-existent chunk
        chunk = chunks[idx - 1]
        citations.append(
            Citation(
                citation_index=idx,
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                document_title=chunk.document_title,
                document_type=chunk.document_type,
                jurisdiction=chunk.jurisdiction,
                country=chunk.country,
                section=chunk.section,
                page=chunk.page,
                source_url=chunk.source_url,
                relevance_score=round(chunk.rerank_score or chunk.fused_score, 4),
                excerpt=chunk.content[:400].strip(),
            )
        )
    return citations
