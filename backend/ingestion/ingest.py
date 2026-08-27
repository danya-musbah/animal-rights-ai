"""
ingest.py
---------
End-to-end knowledge base ingestion command.

Usage:
    python -m backend.ingestion.ingest
    python -m backend.ingestion.ingest --force     # re-ingest even if unchanged
    python -m backend.ingestion.ingest --file knowledge_base/legislation/x.pdf

Pipeline per document:
    manifest entry -> load file -> clean text -> chunk -> embed -> upsert into Supabase

Idempotency: each document's `file_hash` (SHA-256 of the file bytes) is
stored alongside it. If a document with the same id and file_hash
already exists, ingestion skips it (unless --force is passed), so
running the command repeatedly does not create duplicate chunks.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from backend.config import KNOWLEDGE_BASE_DIR, get_settings
from backend.ingestion.loader import load_document
from backend.ingestion.metadata import DocumentMetadata, load_manifest
from backend.ingestion.text_cleaner import clean_text, looks_like_extraction_failure
from backend.rag.chunking import chunk_document
from backend.rag.embeddings import generate_embeddings
from backend.utils.logger import get_logger
from backend.utils.supabase_client import get_supabase

log = get_logger("ingest")


def _existing_document_hash(supabase, doc_id: str) -> str | None:
    try:
        resp = supabase.table("documents").select("file_hash").eq("id", doc_id).limit(1).execute()
        rows = resp.data or []
        return rows[0]["file_hash"] if rows else None
    except Exception as exc:
        log.warning("Could not check existing document %s: %s", doc_id, exc)
        return None


def _upsert_document(supabase, meta: DocumentMetadata, file_hash: str, file_path: str) -> None:
    supabase.table("documents").upsert(
        {
            "id": meta.id,
            "title": meta.title,
            "description": meta.description,
            "author": meta.author,
            "organization": meta.organization,
            "document_type": meta.document_type,
            "jurisdiction": meta.jurisdiction,
            "country": meta.country,
            "language": meta.language,
            "publication_date": meta.publication_date,
            "source_url": meta.source_url,
            "file_path": file_path,
            "file_hash": file_hash,
            "is_synthetic": meta.is_synthetic,
            "topics": meta.topics,
            "animal_categories": meta.animal_categories,
        }
    ).execute()


def _delete_existing_chunks(supabase, doc_id: str) -> None:
    supabase.table("document_chunks").delete().eq("document_id", doc_id).execute()


def _insert_chunks(supabase, meta: DocumentMetadata, chunks, embeddings) -> int:
    rows = []
    for chunk, embedding in zip(chunks, embeddings):
        chunk_metadata = {
            "title": meta.title,
            "document_type": meta.document_type,
            "jurisdiction": meta.jurisdiction,
            "country": meta.country,
            "topics": meta.topics,
            "animal_categories": meta.animal_categories,
            "section": chunk.section,
            "page": chunk.page,
            "source_url": meta.source_url,
            "is_synthetic": meta.is_synthetic,
        }
        rows.append(
            {
                "document_id": meta.id,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "section": chunk.section,
                "page": chunk.page,
                "metadata": chunk_metadata,
                "embedding": embedding,
            }
        )
    if rows:
        supabase.table("document_chunks").insert(rows).execute()
    return len(rows)


def ingest_document(meta: DocumentMetadata, force: bool = False) -> str:
    settings = get_settings()
    supabase = get_supabase()
    full_path = KNOWLEDGE_BASE_DIR / meta.local_file

    if not full_path.exists():
        log.error("File not found for %s: %s", meta.id, full_path)
        return "missing_file"

    loaded = load_document(full_path)

    if not force and supabase is not None:
        existing_hash = _existing_document_hash(supabase, meta.id)
        if existing_hash == loaded.file_hash:
            return "skipped_unchanged"

    if not loaded.extraction_ok:
        log.warning("Extraction problem for %s: %s", meta.id, loaded.warning)

    cleaned = clean_text(loaded.raw_text)
    if looks_like_extraction_failure(cleaned):
        log.error(
            "Document %s produced too little usable text after cleaning - skipping "
            "ingestion of this document. It may need OCR or manual review.",
            meta.id,
        )
        return "extraction_failed"

    chunks = chunk_document(cleaned, target_tokens=settings.chunk_size_tokens, overlap_tokens=settings.chunk_overlap_tokens)
    if not chunks:
        log.error("No chunks produced for %s", meta.id)
        return "no_chunks"

    embeddings = generate_embeddings([c.content for c in chunks])

    if supabase is None:
        log.warning(
            "Supabase not configured - dry run only. Would insert %d chunks for '%s'.",
            len(chunks),
            meta.title,
        )
        return "dry_run"

    _upsert_document(supabase, meta, loaded.file_hash, str(meta.local_file))
    _delete_existing_chunks(supabase, meta.id)
    inserted = _insert_chunks(supabase, meta, chunks, embeddings)
    log.info("Ingested '%s': %d chunks.", meta.title, inserted)
    return "ingested"


def run(force: bool = False, only_file: str | None = None) -> None:
    manifest = load_manifest()
    if only_file:
        manifest = [m for m in manifest if m.local_file == only_file]

    print(f"Discovering documents...\nFound {len(manifest)} documents in manifest.\n")

    stats = {"ingested": 0, "skipped_unchanged": 0, "missing_file": 0, "extraction_failed": 0, "dry_run": 0, "no_chunks": 0}

    for i, meta in enumerate(manifest, start=1):
        print(f"[{i}/{len(manifest)}] {meta.local_file} ...", end=" ")
        try:
            status = ingest_document(meta, force=force)
        except Exception as exc:
            log.error("Unexpected error ingesting %s: %s", meta.id, exc)
            status = "error"
        stats[status] = stats.get(status, 0) + 1
        print(status)

    print("\nIngestion summary:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print("\nIngestion completed.")


def main():
    parser = argparse.ArgumentParser(description="Ingest the Animal Rights AI knowledge base into Supabase.")
    parser.add_argument("--force", action="store_true", help="Re-ingest documents even if unchanged.")
    parser.add_argument("--file", type=str, default=None, help="Only ingest a single manifest local_file path.")
    args = parser.parse_args()

    run(force=args.force, only_file=args.file)


if __name__ == "__main__":
    main()
