"""
test_api.py
-----------
Smoke tests for the FastAPI application: it should start cleanly, expose
/api/health, and respond sensibly to /api/chat and /api/search even with
no Supabase/LLM configured (demo mode), instead of crashing.
"""

from types import SimpleNamespace

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


def test_supabase_requires_service_role_key_for_write_api():
    from backend.config import Settings

    settings = Settings(supabase_url="https://example.supabase.co")

    assert settings.supabase_configured is False


def test_local_placeholder_embeddings_are_not_reported_as_configured():
    from backend.config import Settings

    settings = Settings(embedding_provider="local", embedding_api_key="")

    assert settings.embeddings_configured is False


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


def test_documents_endpoint_maps_database_file_path_to_api_local_file(monkeypatch):
    from backend.api import documents

    row = {
        "id": "db_doc",
        "title": "Database document",
        "description": "",
        "author": "",
        "organization": "",
        "document_type": "other",
        "jurisdiction": "",
        "country": "",
        "language": "English",
        "publication_date": None,
        "source_url": "",
        "file_path": "uploaded/db_doc.txt",
        "topics": [],
        "animal_categories": [],
        "is_synthetic": False,
    }

    class Query:
        def select(self, *args, **kwargs):
            return self

        def eq(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def execute(self):
            return SimpleNamespace(data=[row])

    class FakeSupabase:
        def table(self, _name):
            return Query()

    monkeypatch.setattr(documents, "get_supabase", lambda: FakeSupabase())

    response = client.get("/api/documents")
    detail = client.get("/api/documents/db_doc")

    assert response.status_code == 200
    assert response.json()[0]["local_file"] == "uploaded/db_doc.txt"
    assert detail.status_code == 200
    assert detail.json()["local_file"] == "uploaded/db_doc.txt"


def test_documents_endpoint_404_for_unknown_id():
    resp = client.get("/api/documents/does-not-exist")
    assert resp.status_code == 404


def test_upload_requires_supabase_before_writing_document(monkeypatch, tmp_path):
    from backend.api import documents

    monkeypatch.setattr(documents, "get_supabase", lambda: None)
    monkeypatch.setattr(documents, "KNOWLEDGE_BASE_DIR", tmp_path)

    resp = client.post(
        "/api/documents/ingest",
        files={"file": ("guide.txt", b"Animal welfare guidance")},
    )

    assert resp.status_code == 503
    assert not (tmp_path / "uploaded").exists()


def test_upload_rejects_oversized_file_before_ingestion(monkeypatch, tmp_path):
    from backend.api import documents

    monkeypatch.setattr(documents, "get_supabase", lambda: object())
    monkeypatch.setattr(
        documents,
        "get_settings",
        lambda: SimpleNamespace(max_upload_mb=1, embeddings_configured=True),
    )
    monkeypatch.setattr(documents, "KNOWLEDGE_BASE_DIR", tmp_path)
    monkeypatch.setattr(
        documents,
        "ingest_document",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Ingestion should not run")),
    )

    resp = client.post(
        "/api/documents/ingest",
        files={"file": ("large.txt", b"x" * (1024 * 1024 + 1))},
    )

    assert resp.status_code == 413
    assert not (tmp_path / "uploaded").exists()


def test_upload_does_not_report_dry_run_as_ingested(monkeypatch, tmp_path):
    from backend.api import documents

    monkeypatch.setattr(documents, "get_supabase", lambda: object())
    monkeypatch.setattr(
        documents,
        "get_settings",
        lambda: SimpleNamespace(max_upload_mb=1, embeddings_configured=True),
    )
    monkeypatch.setattr(documents, "KNOWLEDGE_BASE_DIR", tmp_path)
    monkeypatch.setattr(documents, "ingest_document", lambda *args, **kwargs: "dry_run")

    resp = client.post(
        "/api/documents/ingest",
        files={"file": ("guide.txt", b"Animal welfare guidance")},
    )

    assert resp.status_code == 422
    assert not list((tmp_path / "uploaded").glob("*"))


def test_analytics_endpoint_ok():
    resp = client.get("/api/analytics")
    assert resp.status_code == 200
    body = resp.json()
    assert "total_documents" in body


def test_feedback_without_supabase_returns_503():
    resp = client.post("/api/feedback", json={"message_id": "abc", "rating": 1})
    assert resp.status_code == 503


def test_create_conversation_without_supabase_returns_503(monkeypatch):
    from backend.api import conversations

    monkeypatch.setattr(conversations, "get_supabase", lambda: None)

    resp = client.post("/api/conversations", json={"title": "Test"})

    assert resp.status_code == 503
