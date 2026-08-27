"""
main.py
-------
FastAPI application entry point for Animal Rights AI.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import analytics, chat, conversations, documents, feedback, health, search
from backend.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Animal Rights AI API",
    description=(
        "Evidence-grounded RAG API for the Animal Rights AI Knowledge Assistant. "
        "Combines hybrid (semantic + keyword) retrieval, reranking, and grounded "
        "LLM generation over a curated animal rights / welfare / legislation knowledge base."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

allowed_origins = ["*"] if settings.cors_origins.strip() == "*" else [o.strip() for o in settings.cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(conversations.router, prefix="/api", tags=["conversations"])
app.include_router(feedback.router, prefix="/api", tags=["feedback"])
app.include_router(analytics.router, prefix="/api", tags=["analytics"])


@app.get("/", tags=["health"])
def root():
    return {
        "name": "Animal Rights AI API",
        "status": "running",
        "docs": "/api/docs",
        "demo_mode": settings.is_demo_mode,
    }
