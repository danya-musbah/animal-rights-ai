"""
api/analytics.py
------------------
GET /api/analytics

Lightweight, privacy-respecting aggregate statistics about knowledge
base size, usage, and feedback - no individual user data is exposed.
"""

from __future__ import annotations

from collections import Counter

from fastapi import APIRouter
from pydantic import BaseModel

from backend.ingestion.metadata import load_manifest
from backend.utils.logger import get_logger
from backend.utils.supabase_client import get_supabase

log = get_logger("api.analytics")
router = APIRouter()


class AnalyticsOut(BaseModel):
    total_documents: int
    total_chunks: int
    total_conversations: int
    total_messages: int
    positive_feedback: int
    negative_feedback: int
    top_topics: list[dict]
    top_countries: list[dict]
    source: str


@router.get("/analytics", response_model=AnalyticsOut)
def analytics() -> AnalyticsOut:
    supabase = get_supabase()

    if supabase is not None:
        try:
            docs = supabase.table("documents").select("id, topics, country").execute().data or []
            chunks_count = supabase.table("document_chunks").select("id", count="exact").execute().count or 0
            convos_count = supabase.table("conversations").select("id", count="exact").execute().count or 0
            messages_count = supabase.table("messages").select("id", count="exact").execute().count or 0
            feedback_rows = supabase.table("feedback").select("rating").execute().data or []

            topic_counter: Counter = Counter()
            country_counter: Counter = Counter()
            for d in docs:
                for t in (d.get("topics") or []):
                    topic_counter[t] += 1
                if d.get("country"):
                    country_counter[d["country"]] += 1

            return AnalyticsOut(
                total_documents=len(docs),
                total_chunks=chunks_count,
                total_conversations=convos_count,
                total_messages=messages_count,
                positive_feedback=sum(1 for f in feedback_rows if f.get("rating", 0) > 0),
                negative_feedback=sum(1 for f in feedback_rows if f.get("rating", 0) < 0),
                top_topics=[{"topic": t, "count": c} for t, c in topic_counter.most_common(8)],
                top_countries=[{"country": c, "count": n} for c, n in country_counter.most_common(8)],
                source="supabase",
            )
        except Exception as exc:
            log.warning("Falling back to manifest-based analytics: %s", exc)

    manifest = load_manifest()
    topic_counter = Counter()
    country_counter = Counter()
    for m in manifest:
        for t in m.topics:
            topic_counter[t] += 1
        if m.country:
            country_counter[m.country] += 1

    return AnalyticsOut(
        total_documents=len(manifest),
        total_chunks=0,
        total_conversations=0,
        total_messages=0,
        positive_feedback=0,
        negative_feedback=0,
        top_topics=[{"topic": t, "count": c} for t, c in topic_counter.most_common(8)],
        top_countries=[{"country": c, "count": n} for c, n in country_counter.most_common(8)],
        source="manifest (demo mode)",
    )
