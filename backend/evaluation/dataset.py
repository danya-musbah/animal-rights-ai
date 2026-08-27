"""
dataset.py
----------
Loads the evaluation question set from evaluation/questions.json.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from backend.config import BASE_DIR

QUESTIONS_PATH = BASE_DIR / "evaluation" / "questions.json"


@dataclass
class EvalQuestion:
    question: str
    expected_topics: list[str]
    expected_sources: list[str]
    jurisdiction: str | None
    answer_type: str
    answerable: bool
    notes: str = ""


def load_questions() -> list[EvalQuestion]:
    with open(QUESTIONS_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    return [
        EvalQuestion(
            question=q["question"],
            expected_topics=q.get("expected_topics", []),
            expected_sources=q.get("expected_sources", []),
            jurisdiction=q.get("jurisdiction"),
            answer_type=q.get("answer_type", "general"),
            answerable=q.get("answerable", True),
            notes=q.get("notes", ""),
        )
        for q in raw
    ]
