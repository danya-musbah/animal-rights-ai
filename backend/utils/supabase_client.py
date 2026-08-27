"""
supabase_client.py
-------------------
Thin wrapper around the Supabase Python client.

The SERVICE ROLE key is only ever used server-side (here, in the
FastAPI backend process). It is never sent to the frontend. The
frontend only ever talks to our FastAPI API, never directly to
Supabase, so no Supabase key of any kind is exposed to the browser.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from backend.config import get_settings
from backend.utils.logger import get_logger

log = get_logger("supabase_client")

try:
    from supabase import Client, create_client
except ImportError:  # pragma: no cover - supabase-py may not be installed in demo mode
    Client = None  # type: ignore
    create_client = None  # type: ignore


@lru_cache
def get_supabase() -> Optional["Client"]:
    """
    Returns a configured Supabase client using the service role key
    (needed for server-side writes such as ingestion), or None if
    Supabase is not configured (the app falls back to demo mode).
    """
    settings = get_settings()
    if not settings.supabase_configured or create_client is None:
        log.warning("Supabase is not configured - running without a database connection.")
        return None

    key = settings.supabase_service_role_key or settings.supabase_anon_key
    try:
        return create_client(settings.supabase_url, key)
    except Exception as exc:  # pragma: no cover
        log.error("Failed to create Supabase client: %s", exc)
        return None
