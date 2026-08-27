"""
embeddings.py
-------------
Provider-agnostic embedding generation.

The rest of the codebase only ever calls `generate_embedding(text)` or
`generate_embeddings(texts)`. Swapping providers (OpenAI-compatible
API, Cohere, a local sentence-transformers model, etc.) means editing
only this file - nothing else in the RAG pipeline needs to change.
"""

from __future__ import annotations

import hashlib
import math
from functools import lru_cache

import httpx

from backend.config import get_settings
from backend.utils.logger import get_logger

log = get_logger("embeddings")


class EmbeddingError(RuntimeError):
    pass


def _deterministic_fallback_embedding(text: str, dimensions: int) -> list[float]:
    """
    Used only when no embedding provider is configured (demo mode) so
    that the rest of the pipeline (chunk storage, similarity math,
    frontend rendering) can still be exercised end-to-end without a
    real API key. This is NOT semantically meaningful and must never
    be used to answer a real question - `is_demo_mode` gates that.
    """
    seed = hashlib.sha256(text.encode("utf-8")).digest()
    vec = []
    for i in range(dimensions):
        byte = seed[i % len(seed)]
        vec.append(math.sin(byte * (i + 1)))
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def generate_embedding(text: str) -> list[float]:
    return generate_embeddings([text])[0]


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    settings = get_settings()

    if settings.embedding_provider == "local" or not settings.embeddings_configured:
        log.warning("Embedding provider not configured - using deterministic fallback vectors (demo mode only).")
        return [_deterministic_fallback_embedding(t, settings.embedding_dimensions) for t in texts]

    if settings.embedding_provider == "openai":
        return _openai_compatible_embeddings(texts)

    raise EmbeddingError(f"Unsupported embedding provider: {settings.embedding_provider}")


def _openai_compatible_embeddings(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    url = f"{settings.embedding_base_url.rstrip('/')}/embeddings"
    headers = {"Authorization": f"Bearer {settings.embedding_api_key}", "Content-Type": "application/json"}
    payload = {"model": settings.embedding_model, "input": texts}

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return [item["embedding"] for item in data["data"]]
    except httpx.HTTPError as exc:
        log.error("Embedding request failed: %s", exc)
        raise EmbeddingError(str(exc)) from exc
