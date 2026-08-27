"""
loader.py
---------
Dispatches document loading by file extension (.pdf, .txt, .md) and
returns a unified LoadedDocument regardless of source format.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from backend.ingestion.pdf_loader import load_pdf
from backend.utils.logger import get_logger

log = get_logger("loader")

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


@dataclass
class LoadedDocument:
    path: Path
    raw_text: str
    file_hash: str
    extraction_ok: bool
    warning: str | None
    page_count: int = 0
    extracted_title: str | None = None
    extracted_author: str | None = None


def compute_file_hash(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            hasher.update(block)
    return hasher.hexdigest()


def load_document(path: Path) -> LoadedDocument:
    ext = path.suffix.lower()
    file_hash = compute_file_hash(path)

    if ext == ".pdf":
        result = load_pdf(path)
        return LoadedDocument(
            path=path,
            raw_text=result.text,
            file_hash=file_hash,
            extraction_ok=result.extraction_ok,
            warning=result.warning,
            page_count=result.page_count,
            extracted_title=result.title,
            extracted_author=result.author,
        )

    if ext in {".txt", ".md"}:
        text = path.read_text(encoding="utf-8", errors="replace")
        return LoadedDocument(
            path=path,
            raw_text=text,
            file_hash=file_hash,
            extraction_ok=len(text.strip()) > 0,
            warning=None if text.strip() else "File appears to be empty.",
        )

    raise ValueError(f"Unsupported file extension: {ext} ({path})")
