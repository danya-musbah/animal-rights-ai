"""
metadata.py
-----------
Loads and resolves document metadata from knowledge_base/sources.json,
the single manifest describing every document in the knowledge base:
its title, type, jurisdiction, country, language, publication date,
source URL, and local file path.

Ingestion always prefers the manifest's curated metadata over
whatever (often unreliable) metadata a PDF's internal properties
contain, since the manifest is the human-verified source of truth
about where each document actually came from.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from backend.config import KNOWLEDGE_BASE_DIR
from backend.utils.logger import get_logger

log = get_logger("metadata")

SOURCES_MANIFEST_PATH = KNOWLEDGE_BASE_DIR / "sources.json"


@dataclass
class DocumentMetadata:
    id: str
    title: str
    description: str
    author: str
    organization: str
    document_type: str
    jurisdiction: str
    country: str
    language: str
    publication_date: str | None
    source_url: str
    local_file: str
    topics: list[str]
    animal_categories: list[str]
    is_synthetic: bool = False


def load_manifest() -> list[DocumentMetadata]:
    if not SOURCES_MANIFEST_PATH.exists():
        log.warning("sources.json manifest not found at %s", SOURCES_MANIFEST_PATH)
        return []

    with open(SOURCES_MANIFEST_PATH, encoding="utf-8") as f:
        raw = json.load(f)

    docs = []
    for entry in raw:
        docs.append(
            DocumentMetadata(
                id=entry["id"],
                title=entry["title"],
                description=entry.get("description", ""),
                author=entry.get("author", ""),
                organization=entry.get("organization", ""),
                document_type=entry.get("document_type", "other"),
                jurisdiction=entry.get("jurisdiction", ""),
                country=entry.get("country", ""),
                language=entry.get("language", "English"),
                publication_date=entry.get("publication_date"),
                source_url=entry.get("source_url", ""),
                local_file=entry["local_file"],
                topics=entry.get("topics", []),
                animal_categories=entry.get("animal_categories", []),
                is_synthetic=entry.get("is_synthetic", False),
            )
        )
    return docs


def get_metadata_for_file(relative_path: str) -> DocumentMetadata | None:
    for doc in load_manifest():
        if doc.local_file == relative_path:
            return doc
    return None
