"""
api/health.py
-------------
GET /api/health

Reports the operational status of each subsystem (Supabase, LLM,
embeddings) so the frontend can clearly show demo mode instead of
silently failing or faking responses.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.config import get_settings
from backend.utils.supabase_client import get_supabase

router = APIRouter()


class HealthStatus(BaseModel):
    status: str
    demo_mode: bool
    supabase_configured: bool
    supabase_reachable: bool
    llm_configured: bool
    embeddings_configured: bool
    reranker: str


@router.get("/health", response_model=HealthStatus)
def health_check() -> HealthStatus:
    settings = get_settings()
    supabase = get_supabase()
    supabase_reachable = False
    if supabase is not None:
        try:
            supabase.table("documents").select("id").limit(1).execute()
            supabase_reachable = True
        except Exception:
            supabase_reachable = False

    return HealthStatus(
        status="ok",
        demo_mode=settings.is_demo_mode,
        supabase_configured=settings.supabase_configured,
        supabase_reachable=supabase_reachable,
        llm_configured=settings.llm_configured,
        embeddings_configured=settings.embeddings_configured,
        reranker=settings.reranker_provider,
    )
