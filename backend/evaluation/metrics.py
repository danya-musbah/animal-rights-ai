"""
metrics.py
----------
Modular evaluation metrics for both the retrieval stage and the
generation stage of the RAG pipeline. Designed to be run against the
evaluation/questions.json dataset (see backend/evaluation/dataset.py)
and to compare different retrieval configurations (vector-only,
keyword-only, hybrid, hybrid+rerank) as described in the README's
"RAG Experiments" section.

Retrieval metrics
-----------------
hit_rate_at_k        : fraction of queries where >=1 relevant doc is in top K
recall_at_k          : fraction of relevant docs retrieved in top K
precision_at_k       : fraction of top K results that are relevant
mean_reciprocal_rank : average of 1/rank of the first relevant result

Generation metrics (heuristic, LLM-free so they run without extra cost)
-------------------------------------------------------------------
citation_coverage    : fraction of answer sentences that carry a citation marker
citation_correctness : fraction of citation markers that map to a real retrieved chunk
context_relevance    : average reranker/fusion score of the chunks actually used
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.rag.citations import extract_cited_indices
from backend.rag.retrieval import RetrievedChunk

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass
class RetrievalMetrics:
    hit_rate_at_k: float
    recall_at_k: float
    precision_at_k: float
    mrr: float
    num_queries: int


def _is_relevant(retrieved_doc_id: str, expected_sources: list[str]) -> bool:
    if not expected_sources:
        return False
    return retrieved_doc_id in expected_sources


def evaluate_retrieval(
    results_per_query: list[tuple[list[RetrievedChunk], list[str]]],
    k: int = 6,
) -> RetrievalMetrics:
    """
    `results_per_query` is a list of (retrieved_chunks, expected_source_document_ids)
    tuples, one per evaluation question.
    """
    hits = 0
    recalls = []
    precisions = []
    reciprocal_ranks = []

    for retrieved, expected in results_per_query:
        if not expected:
            continue  # skip questions with no ground-truth sources (e.g. "not in KB" questions)

        top_k = retrieved[:k]
        relevant_ids = {r.document_id for r in top_k if _is_relevant(r.document_id, expected)}

        hit = len(relevant_ids) > 0
        hits += int(hit)

        recall = len(relevant_ids) / len(set(expected))
        precision = len(relevant_ids) / max(1, len(top_k))
        recalls.append(recall)
        precisions.append(precision)

        rr = 0.0
        for rank, chunk in enumerate(top_k, start=1):
            if _is_relevant(chunk.document_id, expected):
                rr = 1.0 / rank
                break
        reciprocal_ranks.append(rr)

    n = len(recalls) or 1
    return RetrievalMetrics(
        hit_rate_at_k=hits / n,
        recall_at_k=sum(recalls) / n,
        precision_at_k=sum(precisions) / n,
        mrr=sum(reciprocal_ranks) / n,
        num_queries=n,
    )


@dataclass
class GenerationMetrics:
    citation_coverage: float
    citation_correctness: float
    context_relevance: float


def evaluate_generation(answer_text: str, used_chunks: list[RetrievedChunk]) -> GenerationMetrics:
    sentences = [s for s in SENTENCE_SPLIT.split(answer_text) if len(s.strip()) > 15]
    cited_sentences = sum(1 for s in sentences if re.search(r"\[\d{1,2}\]", s))
    citation_coverage = cited_sentences / max(1, len(sentences))

    cited_indices = extract_cited_indices(answer_text)
    valid = sum(1 for i in cited_indices if 1 <= i <= len(used_chunks))
    citation_correctness = valid / max(1, len(cited_indices)) if cited_indices else 1.0

    scores = [c.rerank_score or c.fused_score for c in used_chunks]
    context_relevance = sum(scores) / max(1, len(scores))

    return GenerationMetrics(
        citation_coverage=round(citation_coverage, 3),
        citation_correctness=round(citation_correctness, 3),
        context_relevance=round(context_relevance, 3),
    )
