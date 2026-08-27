"""
text_cleaner.py
----------------
Normalises raw extracted text before chunking:

  - collapses excessive whitespace while preserving paragraph breaks
  - fixes common PDF extraction artefacts (hyphenated line-wraps,
    stray control characters, repeated headers/footers)
  - normalises unicode punctuation (smart quotes, en/em dashes)
  - preserves [[PAGE:n]] markers inserted by the PDF loader
"""

from __future__ import annotations

import re
import unicodedata

PAGE_MARKER = re.compile(r"\[\[PAGE:\d+\]\]")
HYPHEN_LINEBREAK = re.compile(r"(\w)-\n(\w)")
MULTI_BLANK = re.compile(r"\n{3,}")
MULTI_SPACE = re.compile(r"[ \t]{2,}")
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def clean_text(raw_text: str) -> str:
    if not raw_text:
        return ""

    text = unicodedata.normalize("NFKC", raw_text)
    text = CONTROL_CHARS.sub("", text)

    # Re-join words split across a line break by a hyphen (common PDF artefact)
    text = HYPHEN_LINEBREAK.sub(r"\1\2", text)

    # Normalise smart punctuation to plain ASCII equivalents
    replacements = {
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u00a0": " ",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)

    text = MULTI_SPACE.sub(" ", text)
    text = MULTI_BLANK.sub("\n\n", text)

    # Strip trailing whitespace per line while preserving page markers
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines).strip()

    return text


def looks_like_extraction_failure(text: str, min_chars: int = 200, min_alpha_ratio: float = 0.4) -> bool:
    """
    Heuristic used to detect PDFs where text extraction produced
    little or no usable content (e.g. scanned image-only PDFs with
    no OCR layer). Callers should log these clearly rather than
    silently ingesting near-empty documents.
    """
    stripped = PAGE_MARKER.sub("", text).strip()
    if len(stripped) < min_chars:
        return True
    alpha_chars = sum(1 for ch in stripped if ch.isalpha())
    return (alpha_chars / max(1, len(stripped))) < min_alpha_ratio
