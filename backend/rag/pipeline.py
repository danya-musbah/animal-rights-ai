"""
pipeline.py
-----------
Orchestrates the full RAG pipeline end to end:

    User question
        -> query analysis / query understanding
        -> (optional) query rewriting using conversation history
        -> hybrid retrieval (semantic + keyword)
        -> reranking
        -> relevance thresholding (hallucination protection)
        -> context construction
        -> grounded LLM generation
        -> citation mapping
        -> structured PipelineResult (answer + citations + evidence + debug trace)

Every stage's output is retained in a `debug_trace` so the frontend's
Retrieval Debug Mode can show exactly what happened, without ever
exposing the model's private chain-of-thought.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from backend.config import get_settings
from backend.rag.citations import Citation, build_citations
from backend.rag.hybrid_search import hybrid_search
from backend.rag.llm import LLMError, generate_answer
from backend.rag.prompts import NO_EVIDENCE_FALLBACK, SYSTEM_PROMPT, build_context_block, build_user_turn
from backend.rag.query_analysis import QueryAnalysis, analyze_query, needs_clarification
from backend.rag.reranker import rerank
from backend.rag.retrieval import RetrievedChunk
from backend.utils.logger import get_logger

log = get_logger("pipeline")


@dataclass
class PipelineResult:
    answer: str
    answer_type: str
    citations: list[Citation]
    clarification_needed: str | None
    confidence: str
    debug_trace: dict[str, Any] = field(default_factory=dict)
    demo_mode: bool = False


def _rewrite_query_with_context(question: str, conversation_history: list[dict]) -> str:
    """
    Lightweight, deterministic query rewriting for follow-up questions.
    If the current question is short and conversation history exists,
    the previous user question's topical keywords are appended so
    retrieval has enough signal (e.g. "What about in the UK?" ->
    "What about in the UK? (context: animal cruelty definition)").

    This intentionally avoids an extra LLM call for cost/latency, but
    the function signature makes it trivial to swap in LLM-based
    rewriting later without touching the rest of the pipeline.
    """
    if not conversation_history or len(question.split()) > 8:
        return question

    last_user_turns = [m["content"] for m in conversation_history if m.get("role") == "user"]
    if not last_user_turns:
        return question

    previous = last_user_turns[-1]
    return f"{question} (follow-up in context of: {previous})"


def _answer_type_from_intent(intent: str) -> str:
    return {
        "legal_question": "legal",
        "scientific_question": "scientific",
        "ethical_discussion": "ethical",
        "comparison": "comparative",
        "definition": "educational",
    }.get(intent, "educational")


def _confidence_from_scores(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "none"
    top_score = max((c.rerank_score or c.fused_score) for c in chunks)
    if top_score >= 0.55:
        return "high"
    if top_score >= 0.25:
        return "medium"
    return "low"


def run_pipeline(
    question: str,
    conversation_history: list[dict] | None = None,
    filters: dict | None = None,
    force_jurisdiction_skip: bool = False,
) -> PipelineResult:
    settings = get_settings()
    conversation_history = conversation_history or []
    debug: dict[str, Any] = {"stages": []}
    t0 = time.time()

    def log_stage(name: str, payload: Any):
        debug["stages"].append({"stage": name, "data": payload})

    # 1. Query rewriting (only used internally for retrieval, not shown unless debug mode)
    known_country = (filters or {}).get("country")
    rewritten_query = _rewrite_query_with_context(question, conversation_history)
    log_stage("query_rewriting", {"original": question, "rewritten": rewritten_query})

    # 2. Query analysis / understanding
    analysis: QueryAnalysis = analyze_query(rewritten_query, known_country=known_country)
    log_stage("query_analysis", analysis.__dict__)

    # 3. Jurisdiction clarification gate
    clarification = None if force_jurisdiction_skip else needs_clarification(analysis)
    if clarification:
        return PipelineResult(
            answer=clarification,
            answer_type="clarification",
            citations=[],
            clarification_needed=clarification,
            confidence="n/a",
            debug_trace=debug,
            demo_mode=settings.is_demo_mode,
        )

    # 4. Hybrid retrieval
    search_filters = dict(filters or {})
    if analysis.country and "country" not in search_filters:
        search_filters["country"] = analysis.country
    if analysis.document_type_hint and "document_type" not in search_filters:
        search_filters["document_type"] = analysis.document_type_hint

    fused_candidates = hybrid_search(rewritten_query, filters=search_filters)
    log_stage(
        "hybrid_retrieval",
        [
            {
                "chunk_id": c.chunk_id,
                "title": c.document_title,
                "semantic_score": round(c.semantic_score, 4),
                "keyword_score": round(c.keyword_score, 4),
                "fused_score": round(c.fused_score, 4),
            }
            for c in fused_candidates[:20]
        ],
    )

    # 5. Reranking
    top_chunks = rerank(rewritten_query, fused_candidates, top_k=settings.final_top_k)
    log_stage(
        "reranking",
        [
            {"chunk_id": c.chunk_id, "title": c.document_title, "rerank_score": round(c.rerank_score or 0, 4)}
            for c in top_chunks
        ],
    )

    confidence = _confidence_from_scores(top_chunks)

    # 6. Hallucination protection: relevance thresholding
    usable_chunks = [
        c for c in top_chunks if (c.rerank_score or c.fused_score) >= settings.min_relevance_score
    ]
    log_stage("relevance_threshold", {"threshold": settings.min_relevance_score, "kept": len(usable_chunks)})

    if not usable_chunks:
        return PipelineResult(
            answer=NO_EVIDENCE_FALLBACK,
            answer_type="educational",
            citations=[],
            clarification_needed=None,
            confidence="none",
            debug_trace=debug,
            demo_mode=settings.is_demo_mode,
        )

    # 7. Context construction
    context_block = build_context_block(usable_chunks)
    user_turn = build_user_turn(question, context_block)
    log_stage("context_construction", {"num_chunks": len(usable_chunks), "context_preview": context_block[:800]})

    # 8. Grounded generation
    if settings.is_demo_mode:
        answer_text = (
            "Demo mode is active (Supabase and/or an LLM provider are not fully configured), so a "
            "grounded answer cannot be generated right now. The retrieval stages above still ran "
            "against the configured knowledge base to demonstrate the pipeline end to end. Configure "
            "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY and LLM_API_KEY in your .env file to enable "
            "full generation.\n\n" + (context_block[:300] if context_block else "")
        )
    else:
        try:
            answer_text = generate_answer(SYSTEM_PROMPT, user_turn)
        except LLMError as exc:
            log.error("Generation failed: %s", exc)
            answer_text = (
                "The knowledge base returned relevant evidence, but the language model could not be "
                "reached to generate a grounded answer right now. Please try again shortly."
            )

    # 9. Citation mapping
    citations = build_citations(usable_chunks, answer_text)
    log_stage("citations", [c.__dict__ for c in citations])

    debug["latency_ms"] = int((time.time() - t0) * 1000)

    return PipelineResult(
        answer=answer_text,
        answer_type=_answer_type_from_intent(analysis.intent),
        citations=citations,
        clarification_needed=None,
        confidence=confidence,
        debug_trace=debug,
        demo_mode=settings.is_demo_mode,
    )
