"""
chunking.py
-----------
Intelligent, structure-aware text chunking.

Rather than naively slicing every document into fixed-size character
blocks, this module:

  1. Splits text into structural units (headings, paragraphs, list
     items) using simple but effective heuristics that work well for
     legislation, reports, and academic text.
  2. Groups those units into chunks close to a target token budget.
  3. Carries a token-level overlap between consecutive chunks so that
     context is not lost at chunk boundaries.
  4. Tracks the current "section" (nearest preceding heading) and,
     when available, the page number, and attaches both to every
     resulting chunk as metadata.

"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

HEADING_PATTERN = re.compile(
    r"^\s{0,3}("
    r"(?i:Article|Section|Chapter|Part|Regulation|Rule|Annex|Schedule)\s+[\dIVXLC]+[.:]?.*"
    r"|\d{1,3}(\.\d{1,3}){0,3}\s+[A-Z].{0,120}"
    r"|[A-Z][A-Z0-9 \-/&:,.]{5,90}"
    r")\s*$"
)

PAGE_BREAK_PATTERN = re.compile(r"\[\[PAGE:(\d+)\]\]")


def _estimate_tokens(text: str) -> int:
    """Cheap token estimate (~0.75 words/token average for English)."""
    words = text.split()
    return max(1, int(len(words) / 0.75))


@dataclass
class RawUnit:
    text: str
    is_heading: bool
    page: Optional[int] = None


@dataclass
class Chunk:
    chunk_index: int
    content: str
    section: Optional[str]
    page: Optional[int]
    token_count: int
    metadata: dict = field(default_factory=dict)


def _split_into_units(text: str) -> list[RawUnit]:
    """
    Splits cleaned document text into paragraph/heading units.
    Page markers (inserted by the PDF loader as [[PAGE:n]]) are
    tracked but stripped from the visible content.
    """
    units: list[RawUnit] = []
    current_page: Optional[int] = None

    # Normalise line endings and split on blank lines (paragraphs)
    text = text.replace("\r\n", "\n")
    blocks = re.split(r"\n\s*\n", text)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        for line in block.split("\n"):
            m = PAGE_BREAK_PATTERN.search(line)
            if m:
                current_page = int(m.group(1))
                line = PAGE_BREAK_PATTERN.sub("", line).strip()
                if not line:
                    continue
            first_line = block.split("\n")[0].strip()
            break
        else:
            first_line = block

        cleaned_block = PAGE_BREAK_PATTERN.sub("", block).strip()
        if not cleaned_block:
            continue

        is_heading = bool(HEADING_PATTERN.match(first_line)) and len(cleaned_block) < 160
        units.append(RawUnit(text=cleaned_block, is_heading=is_heading, page=current_page))

    return units


def chunk_document(
    text: str,
    target_tokens: int = 320,
    overlap_tokens: int = 60,
) -> list[Chunk]:
    """
    Produces a list of overlapping, section-aware chunks from raw
    document text.
    """
    units = _split_into_units(text)

    chunks: list[Chunk] = []
    current_texts: list[str] = []
    current_tokens = 0
    current_section: Optional[str] = None
    current_page: Optional[int] = None
    chunk_index = 0

    def flush():
        nonlocal chunks, current_texts, current_tokens, chunk_index
        if not current_texts:
            return
        content = "\n\n".join(current_texts).strip()
        if content:
            chunks.append(
                Chunk(
                    chunk_index=chunk_index,
                    content=content,
                    section=current_section,
                    page=current_page,
                    token_count=_estimate_tokens(content),
                )
            )
            chunk_index += 1

    for unit in units:
        if unit.is_heading:
            current_section = unit.text
            # Headings alone rarely make useful stand-alone chunks;
            # still flush existing content once the heading changes.
            if current_tokens >= target_tokens * 0.4:
                flush()
                # Overlap: carry the tail of previous content forward
                tail_words = " ".join(current_texts).split()[-overlap_tokens:]
                current_texts = [" ".join(tail_words)] if tail_words else []
                current_tokens = _estimate_tokens(" ".join(current_texts))
            continue

        unit_tokens = _estimate_tokens(unit.text)
        if current_page is None:
            current_page = unit.page
        elif unit.page is not None:
            current_page = unit.page

        if current_tokens + unit_tokens > target_tokens and current_texts:
            flush()
            tail_words = " ".join(current_texts).split()[-overlap_tokens:]
            current_texts = [" ".join(tail_words)] if tail_words else []
            current_tokens = _estimate_tokens(" ".join(current_texts))

        current_texts.append(unit.text)
        current_tokens += unit_tokens

    flush()
    return chunks
