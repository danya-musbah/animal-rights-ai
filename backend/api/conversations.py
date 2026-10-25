"""
api/conversations.py
---------------------
GET    /api/conversations           - list conversations
POST   /api/conversations           - create a new (empty) conversation
GET    /api/conversations/{id}      - a conversation with its messages
PATCH  /api/conversations/{id}      - rename a conversation
DELETE /api/conversations/{id}      - delete a conversation and its messages
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.utils.logger import get_logger
from backend.utils.supabase_client import get_supabase

log = get_logger("api.conversations")
router = APIRouter()


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    answer_type: Optional[str] = None
    confidence: Optional[str] = None
    created_at: Optional[str] = None


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = []


class CreateConversationRequest(BaseModel):
    title: str = "New conversation"


class RenameRequest(BaseModel):
    title: str


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations():
    supabase = get_supabase()
    if supabase is None:
        return []
    try:
        resp = supabase.table("conversations").select("*").order("updated_at", desc=True).execute()
        return resp.data or []
    except Exception as exc:
        log.error("Could not list conversations: %s", exc)
        raise HTTPException(status_code=503, detail="Could not load conversations.") from exc


@router.post("/conversations", response_model=ConversationOut)
def create_conversation(request: CreateConversationRequest):
    supabase = get_supabase()
    if supabase is None:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")

    new_id = str(uuid.uuid4())
    try:
        supabase.table("conversations").insert({"id": new_id, "title": request.title}).execute()
    except Exception as exc:
        log.error("Could not persist new conversation: %s", exc)
        raise HTTPException(status_code=503, detail="Could not create a conversation.") from exc

    return ConversationOut(id=new_id, title=request.title)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str):
    supabase = get_supabase()
    if supabase is None:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")
    try:
        conv_resp = supabase.table("conversations").select("*").eq("id", conversation_id).limit(1).execute()
        if not conv_resp.data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conv = conv_resp.data[0]
        msg_resp = (
            supabase.table("messages")
            .select("*")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=False)
            .execute()
        )
        conv["messages"] = msg_resp.data or []
        return conv
    except HTTPException:
        raise
    except Exception as exc:
        log.error("Failed to load conversation %s: %s", conversation_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load conversation")


@router.patch("/conversations/{conversation_id}", response_model=ConversationOut)
def rename_conversation(conversation_id: str, request: RenameRequest):
    supabase = get_supabase()
    if supabase is None:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")
    try:
        supabase.table("conversations").update({"title": request.title}).eq("id", conversation_id).execute()
    except Exception as exc:
        log.error("Could not rename conversation %s: %s", conversation_id, exc)
        raise HTTPException(status_code=503, detail="Could not rename conversation.") from exc
    return ConversationOut(id=conversation_id, title=request.title)


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    supabase = get_supabase()
    if supabase is None:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")
    try:
        supabase.table("conversations").delete().eq("id", conversation_id).execute()
    except Exception as exc:
        log.error("Could not delete conversation %s: %s", conversation_id, exc)
        raise HTTPException(status_code=503, detail="Could not delete conversation.") from exc
    return {"status": "deleted", "id": conversation_id}
