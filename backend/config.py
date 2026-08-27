"""
config.py
---------
Centralised application configuration.

All secrets and environment-specific values are read from environment
variables (see .env.example). Nothing here is hard-coded. This module
is the single source of truth for configuration across the backend.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Load .env if present (no-op in production where real env vars are injected)
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"


def _get_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    val = os.getenv(name)
    try:
        return int(val) if val is not None else default
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    val = os.getenv(name)
    try:
        return float(val) if val is not None else default
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    # --- Supabase ---
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    supabase_service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    # --- LLM provider (OpenAI-compatible) ---
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai")  # openai | anthropic | local

    # --- Embeddings provider ---
    embedding_api_key: str = os.getenv("EMBEDDING_API_KEY", "")
    embedding_base_url: str = os.getenv("EMBEDDING_BASE_URL", "https://api.openai.com/v1")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    embedding_dimensions: int = _get_int("EMBEDDING_DIMENSIONS", 1536)
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "openai")

    # --- Optional dedicated reranker ---
    reranker_provider: str = os.getenv("RERANKER_PROVIDER", "none")  # none | cohere | api
    reranker_api_key: str = os.getenv("RERANKER_API_KEY", "")
    reranker_model: str = os.getenv("RERANKER_MODEL", "")

    # --- Retrieval tuning ---
    semantic_top_k: int = _get_int("SEMANTIC_TOP_K", 20)
    keyword_top_k: int = _get_int("KEYWORD_TOP_K", 20)
    final_top_k: int = _get_int("FINAL_TOP_K", 6)
    min_relevance_score: float = _get_float("MIN_RELEVANCE_SCORE", 0.15)
    chunk_size_tokens: int = _get_int("CHUNK_SIZE_TOKENS", 320)
    chunk_overlap_tokens: int = _get_int("CHUNK_OVERLAP_TOKENS", 60)

    # --- App ---
    app_env: str = os.getenv("APP_ENV", "development")
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")
    max_upload_mb: int = _get_int("MAX_UPLOAD_MB", 20)
    demo_mode_forced: bool = _get_bool("FORCE_DEMO_MODE", False)

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and (self.supabase_service_role_key or self.supabase_anon_key))

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key) or self.llm_provider == "local"

    @property
    def embeddings_configured(self) -> bool:
        return bool(self.embedding_api_key) or self.embedding_provider == "local"

    @property
    def is_demo_mode(self) -> bool:
        """
        Demo mode is active whenever the system is missing the pieces it
        needs to run a genuine RAG pipeline (Supabase and/or an LLM).
        The frontend clearly communicates this rather than faking answers.
        """
        return self.demo_mode_forced or not (self.supabase_configured and self.llm_configured)


@lru_cache
def get_settings() -> Settings:
    return Settings()
