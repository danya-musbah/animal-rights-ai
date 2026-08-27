"""
pdf_loader.py
-------------
PDF text and metadata extraction using pypdf.

Page boundaries are preserved with [[PAGE:n]] markers so downstream
chunking can attach an accurate page number to every chunk. Documents
where extraction clearly failed (e.g. scanned, image-only PDFs with
no text layer) are flagged rather than silently ingested as empty.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.utils.logger import get_logger

log = get_logger("pdf_loader")


@dataclass
class PDFLoadResult:
    text: str
    page_count: int
    title: str | None
    author: str | None
    extraction_ok: bool
    warning: str | None = None


def load_pdf(path: Path) -> PDFLoadResult:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("pypdf is required for PDF ingestion. Install it via requirements.txt.") from exc

    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        log.error("Failed to open PDF %s: %s", path, exc)
        return PDFLoadResult(text="", page_count=0, title=None, author=None, extraction_ok=False, warning=str(exc))

    pages_text = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
        except Exception as exc:  # pragma: no cover
            log.warning("Failed to extract text from page %d of %s: %s", i, path, exc)
            page_text = ""
        pages_text.append(f"[[PAGE:{i}]]\n{page_text}")

    full_text = "\n\n".join(pages_text)

    meta = reader.metadata or {}
    title = getattr(meta, "title", None) or (meta.get("/Title") if isinstance(meta, dict) else None)
    author = getattr(meta, "author", None) or (meta.get("/Author") if isinstance(meta, dict) else None)

    extraction_ok = True
    warning = None
    stripped_len = len(full_text.replace("\n", "").strip())
    if stripped_len < 200:
        extraction_ok = False
        warning = (
            f"Extracted only {stripped_len} characters from {len(reader.pages)} page(s). "
            "This PDF may be scanned/image-only and require OCR."
        )
        log.warning("Poor PDF extraction for %s: %s", path, warning)

    return PDFLoadResult(
        text=full_text,
        page_count=len(reader.pages),
        title=title,
        author=author,
        extraction_ok=extraction_ok,
        warning=warning,
    )
