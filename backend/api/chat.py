"""
api/chat.py
-----------
POST /api/chat

The core RAG entry point. Accepts a question (optionally within an
existing conversation), runs the full retrieval-augmented generation
pipeline, persists the conversation/messages/sources to Supabase when
available, and returns the grounded answer with citations, evidence,
and (optionally) a full retrieval debug trace.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.rag.pipeline import run_pipeline
from backend.utils.logger import get_logger
from backend.utils.supabase_client import get_supabase

log = get_logger("api.chat")
router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[str] = None
    country: Optional[str] = None
    debug: bool = False
    force_jurisdiction_skip: bool = False


class CitationOut(BaseModel):
    citation_index: int
    document_title: str
    document_type: str
    jurisdiction: str
    country: str
    section: Optional[str]
    page: Optional[int]
    source_url: str
    relevance_score: float
    excerpt: str


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer: str
    answer_type: str
    confidence: str
    demo_mode: bool
    clarification_needed: Optional[str] = None
    citations: list[CitationOut]
    debug_trace: Optional[dict[str, Any]] = None


def _load_conversation_history(supabase, conversation_id: str) -> list[dict]:
    if supabase is None:
        return []
    try:
        resp = (
            supabase.table("messages")
            .select("role, content")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=False)
            .limit(20)
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        log.warning("Could not load conversation history: %s", exc)
        return []


def _persist_turn(supabase, conversation_id: str, question: str, result, request: ChatRequest) -> str:
    """Persists the user message, assistant message, and message_sources. Returns the assistant message id."""
    if supabase is None:
        return str(uuid.uuid4())

    try:
        supabase.table("messages").insert(
            {"conversation_id": conversation_id, "role": "user", "content": question}
        ).execute()

        assistant_msg = (
            supabase.table("messages")
            .insert(
                {
                    "conversation_id": conversation_id,
                    "role": "assistant",
                    "content": result.answer,
                    "answer_type": result.answer_type,
                    "confidence": result.confidence,
                }
            )
            .execute()
        )
        message_id = assistant_msg.data[0]["id"]

        for citation in result.citations:
            supabase.table("message_sources").insert(
                {
                    "message_id": message_id,
                    "chunk_id": citation.chunk_id,
                    "relevance_score": citation.relevance_score,
                    "citation_index": citation.citation_index,
                }
            ).execute()

        return str(message_id)
    except Exception as exc:
        log.warning("Could not persist conversation turn (continuing without persistence): %s", exc)
        return str(uuid.uuid4())


def _ensure_conversation(supabase, conversation_id: Optional[str], first_message: str) -> str:
    if conversation_id:
        return conversation_id
    new_id = str(uuid.uuid4())
    if supabase is not None:
        try:
            title = (first_message[:60] + "...") if len(first_message) > 60 else first_message
            supabase.table("conversations").insert({"id": new_id, "title": title}).execute()
        except Exception as exc:
            log.warning("Could not create conversation record: %s", exc)
    return new_id


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    supabase = get_supabase()
    conversation_id = _ensure_conversation(supabase, request.conversation_id, request.message)
    history = _load_conversation_history(supabase, conversation_id)

    filters = {"country": request.country} if request.country else None

    result = run_pipeline(
        question=request.message,
        conversation_history=history,
        filters=filters,
        force_jurisdiction_skip=request.force_jurisdiction_skip,
    )

    message_id = _persist_turn(supabase, conversation_id, request.message, result, request)

    citations_out = [
        CitationOut(
            citation_index=c.citation_index,
            document_title=c.document_title,
            document_type=c.document_type,
            jurisdiction=c.jurisdiction,
            country=c.country,
            section=c.section,
            page=c.page,
            source_url=c.source_url,
            relevance_score=c.relevance_score,
            excerpt=c.excerpt,
        )
        for c in result.citations
    ]

    return ChatResponse(
        conversation_id=conversation_id,
        message_id=message_id,
        answer=result.answer,
        answer_type=result.answer_type,
        confidence=result.confidence,
        demo_mode=result.demo_mode,
        clarification_needed=result.clarification_needed,
        citations=citations_out,
        debug_trace=result.debug_trace if request.debug else None,
    )
