"""
test_api.py
-----------
Smoke tests for the FastAPI application: it should start cleanly, expose
/api/health, and respond sensibly to /api/chat and /api/search even with
no Supabase/LLM configured (demo mode), instead of crashing.
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_root_endpoint_ok():
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Animal Rights AI API"


def test_health_endpoint_reports_demo_mode():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "demo_mode" in body
    assert body["demo_mode"] is True  # forced by conftest.py env vars


def test_chat_endpoint_handles_missing_supabase_gracefully():
    resp = client.post("/api/chat", json={"message": "What is the difference between animal rights and animal welfare?"})
    assert resp.status_code == 200
    body = resp.json()
    assert "answer" in body
    assert body["demo_mode"] is True


def test_chat_endpoint_validates_empty_message():
    resp = client.post("/api/chat", json={"message": ""})
    assert resp.status_code == 422  # Pydantic min_length validation


def test_search_endpoint_returns_empty_results_without_supabase():
    resp = client.post("/api/search", json={"query": "animal transport welfare"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["results"] == []  # no Supabase configured => no candidates


def test_documents_endpoint_falls_back_to_manifest():
    resp = client.get("/api/documents")
    assert resp.status_code == 200
    docs = resp.json()
    assert isinstance(docs, list)
    assert len(docs) >= 10  # the manifest ships with 15 documents


def test_documents_endpoint_404_for_unknown_id():
    resp = client.get("/api/documents/does-not-exist")
    assert resp.status_code == 404


def test_analytics_endpoint_ok():
    resp = client.get("/api/analytics")
    assert resp.status_code == 200
    body = resp.json()
    assert "total_documents" in body


def test_feedback_without_supabase_returns_503():
    resp = client.post("/api/feedback", json={"message_id": "abc", "rating": 1})
    assert resp.status_code == 503
