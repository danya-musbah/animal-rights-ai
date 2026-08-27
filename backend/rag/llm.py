"""
llm.py
------
Provider-agnostic answer generation.

Like embeddings.py, this module exposes one function -
`generate_answer()` - that the rest of the pipeline calls. Switching
LLM providers (OpenAI-compatible endpoint, Anthropic, a local model
server) only requires editing this file.
"""

from __future__ import annotations

import re

import httpx

from backend.config import get_settings
from backend.utils.logger import get_logger

log = get_logger("llm")


class LLMError(RuntimeError):
    pass


def generate_answer(system_prompt: str, user_prompt: str, max_tokens: int = 900) -> str:
    settings = get_settings()

    if not settings.llm_configured:
        raise LLMError("No LLM provider is configured.")

    if settings.llm_provider == "local":
        return _local_extractive_answer(user_prompt)
    if settings.llm_provider == "openai":
        return _openai_compatible_chat(system_prompt, user_prompt, max_tokens)
    if settings.llm_provider == "anthropic":
        return _anthropic_chat(system_prompt, user_prompt, max_tokens)

    raise LLMError(f"Unsupported LLM provider: {settings.llm_provider}")


def _local_extractive_answer(user_prompt: str) -> str:
    """Build a citation-preserving answer without calling a remote LLM."""
    question_match = re.search(r"USER QUESTION:\s*(.+?)\s*\n\s*RETRIEVED EVIDENCE:", user_prompt, re.DOTALL)
    question = question_match.group(1).strip() if question_match else ""
    question_terms = {
        term.lower()
        for term in re.findall(r"[A-Za-z][A-Za-z-]{3,}", question)
        if term.lower() not in {"what", "which", "does", "this", "that", "with", "from", "into"}
    }

    blocks = re.findall(
        r"\[(\d+)\] SOURCE:.*?\n\s*EXCERPT:\s*(.*?)(?=\n\n\[\d+\] SOURCE:|\n\nAnswer\n|\Z)",
        user_prompt,
        re.DOTALL,
    )
    selected: list[str] = []
    for index, excerpt in blocks:
        normalized_excerpt = re.sub(r"\s+", " ", excerpt).strip()
        sentences = re.split(r"(?<=[.!?])\s+", normalized_excerpt)
        ranked = sorted(
            (sentence.strip() for sentence in sentences if len(sentence.strip()) >= 45),
            key=lambda sentence: sum(term in sentence.lower() for term in question_terms),
            reverse=True,
        )
        if ranked:
            selected.append(f"{ranked[0]} [{index}]")
        if len(selected) == 3:
            break

    if not selected:
        return "The retrieved sources contain text relevant to the question, but no concise extractive answer could be formed."
    return "Based on the retrieved evidence:\n\n" + "\n".join(f"- {item}" for item in selected)


def _openai_compatible_chat(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    settings = get_settings()
    url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    try:
        with httpx.Client(timeout=90.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]
    except httpx.HTTPError as exc:
        log.error("LLM request failed: %s", exc)
        raise LLMError(str(exc)) from exc


def _anthropic_chat(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    settings = get_settings()
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": settings.llm_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": settings.llm_model,
        "system": system_prompt,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    try:
        with httpx.Client(timeout=90.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return "".join(block.get("text", "") for block in data.get("content", []))
    except httpx.HTTPError as exc:
        log.error("LLM request failed: %s", exc)
        raise LLMError(str(exc)) from exc
