"""
api/feedback.py
----------------
POST /api/feedback

Stores a thumbs up/down (and optional comment) against a specific
assistant message, for later analysis and retrieval-quality
improvement. No sensitive user data is collected.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.utils.logger import get_logger
from backend.utils.supabase_client import get_supabase

log = get_logger("api.feedback")
router = APIRouter()


class FeedbackRequest(BaseModel):
    message_id: str
    rating: int = Field(..., ge=-1, le=1, description="-1 = thumbs down, 1 = thumbs up")
    comment: Optional[str] = Field(default=None, max_length=1000)


@router.post("/feedback")
def submit_feedback(request: FeedbackRequest):
    supabase = get_supabase()
    if supabase is None:
        raise HTTPException(status_code=503, detail="Supabase is not configured - feedback cannot be stored right now.")
    try:
        supabase.table("feedback").insert(
            {"message_id": request.message_id, "rating": request.rating, "comment": request.comment}
        ).execute()
        return {"status": "recorded"}
    except Exception as exc:
        log.error("Failed to store feedback: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to store feedback")
