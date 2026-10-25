"""
api/documents.py
-----------------
GET  /api/documents            - list knowledge base documents (with filters)
GET  /api/documents/{id}       - a single document's full metadata
POST /api/documents/ingest     - upload a new document (pdf/txt/md) and run it through ingestion

Documents are always sourced from Supabase when configured; if
Supabase is unavailable, the endpoint falls back to reading directly
from the local knowledge_base/sources.json manifest so the Knowledge
Base explorer still works in demo mode.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.config import KNOWLEDGE_BASE_DIR, get_settings
from backend.ingestion.ingest import ingest_document
from backend.ingestion.metadata import DocumentMetadata, load_manifest
from backend.utils.logger import get_logger
from backend.utils.supabase_client import get_supabase

log = get_logger("api.documents")
router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}


class DocumentOut(BaseModel):
    id: str
    title: str
    description: str
    author: str
    organization: str
    document_type: str
    jurisdiction: str
    country: str
    language: str
    publication_date: Optional[str]
    source_url: str
    local_file: str
    topics: list[str]
    animal_categories: list[str]
    is_synthetic: bool


def _manifest_to_out(m: DocumentMetadata) -> DocumentOut:
    return DocumentOut(
        id=m.id, title=m.title, description=m.description, author=m.author,
        organization=m.organization, document_type=m.document_type, jurisdiction=m.jurisdiction,
        country=m.country, language=m.language, publication_date=m.publication_date,
        source_url=m.source_url, local_file=m.local_file, topics=m.topics,
        animal_categories=m.animal_categories, is_synthetic=m.is_synthetic,
    )


def _database_row_to_out(row: dict) -> DocumentOut:
    data = dict(row)
    data["local_file"] = data.get("local_file") or data.get("file_path", "")
    return DocumentOut(**data)


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(
    country: Optional[str] = None,
    document_type: Optional[str] = None,
    topic: Optional[str] = None,
    animal_category: Optional[str] = None,
) -> list[DocumentOut]:
    supabase = get_supabase()
    docs: list[DocumentOut]

    if supabase is not None:
        try:
            query = supabase.table("documents").select("*")
            if country:
                query = query.eq("country", country)
            if document_type:
                query = query.eq("document_type", document_type)
            resp = query.execute()
            docs = [_database_row_to_out(row) for row in (resp.data or [])]
        except Exception as exc:
            log.warning("Falling back to manifest for documents list: %s", exc)
            docs = [_manifest_to_out(m) for m in load_manifest()]
    else:
        docs = [_manifest_to_out(m) for m in load_manifest()]
        if country:
            docs = [d for d in docs if d.country == country]
        if document_type:
            docs = [d for d in docs if d.document_type == document_type]

    if topic:
        docs = [d for d in docs if topic in d.topics]
    if animal_category:
        docs = [d for d in docs if animal_category in d.animal_categories]

    return docs


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(document_id: str) -> DocumentOut:
    supabase = get_supabase()
    if supabase is not None:
        try:
            resp = supabase.table("documents").select("*").eq("id", document_id).limit(1).execute()
            if resp.data:
                return _database_row_to_out(resp.data[0])
        except Exception as exc:
            log.warning("Supabase lookup failed, falling back to manifest: %s", exc)

    for m in load_manifest():
        if m.id == document_id:
            return _manifest_to_out(m)

    raise HTTPException(status_code=404, detail="Document not found")


@router.post("/documents/ingest")
async def ingest_uploaded_document(file: UploadFile = File(...)):
    settings = get_settings()
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}")

    if get_supabase() is None:
        raise HTTPException(status_code=503, detail="Document ingestion requires a configured Supabase database.")
    if not settings.embeddings_configured:
        raise HTTPException(status_code=503, detail="Document ingestion requires a configured embedding provider.")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    contents = await file.read(max_bytes + 1)
    if len(contents) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds the {settings.max_upload_mb}MB upload limit.")
    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    doc_id = f"upload_{uuid.uuid4().hex[:10]}"
    relative_path = f"uploaded/{doc_id}{ext}"
    dest_path = KNOWLEDGE_BASE_DIR / relative_path
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(contents)

    meta = DocumentMetadata(
        id=doc_id,
        title=Path(filename).stem,
        description="User-uploaded document.",
        author="",
        organization="",
        document_type="other",
        jurisdiction="",
        country="",
        language="English",
        publication_date=None,
        source_url="",
        local_file=relative_path,
        topics=[],
        animal_categories=[],
        is_synthetic=False,
    )

    try:
        status = ingest_document(meta, force=True)
    except Exception as exc:
        log.exception("Uploaded document ingestion failed for %s", doc_id)
        raise HTTPException(
            status_code=500,
            detail="Document ingestion failed; check the backend logs for details.",
        ) from exc

    if status != "ingested":
        dest_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=422,
            detail=f"Document could not be ingested (status: {status}).",
        )
    return {"document_id": doc_id, "status": status}
