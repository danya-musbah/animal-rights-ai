# 🐾 Animal Rights AI

**Animal Rights AI Knowledge Assistant**

Evidence-based AI knowledge assistant for animal rights, welfare, protection, and legislation.

> This application provides educational information based on the documents available in its
> knowledge base. It is not a substitute for professional legal advice. Laws and regulations
> may change, and users should verify current information with authoritative sources.

---

## Live Demo

[View Animal Rights AI](https://danya-musbah.github.io/animal-rights-ai/)

---

## Overview

Animal Rights AI is a full-stack, production-style **Retrieval-Augmented Generation (RAG)**
application specialised in animal rights, animal welfare, animal protection, and related
legislation and research. It is built to be:

- A **real RAG system** — genuine document ingestion, chunking, embedding, hybrid vector +
  keyword search, reranking, and citation-grounded generation — not a chatbot with documents
  pasted into a prompt.
- A **portfolio-quality software project** demonstrating Python, FastAPI, Supabase/Postgres,
  pgvector, hybrid search, reranking, LLM orchestration, and vanilla frontend engineering.
- **Honest about its own limits** — it answers only from its knowledge base, says so when
  evidence is insufficient, and never invents legislation, case law, or citations.

## Features

- **Hybrid retrieval**: semantic (pgvector) + keyword (PostgreSQL full-text search),
  fused with Reciprocal Rank Fusion.
- **Reranking**: pluggable dedicated reranker API, or a transparent heuristic fallback.
- **Query understanding**: intent, animal, topic, and jurisdiction extraction; asks for
  clarification instead of guessing a jurisdiction.
- **Real citations**: `[n]` markers map back to actual retrieved chunks — never fabricated.
- **Hallucination protection**: a configurable relevance threshold below which the system
  says "insufficient evidence" instead of generating an answer.
- **Knowledge Base explorer**, **Semantic Search page**, **RAG Pipeline visualization**,
  and **Analytics** — all as first-class pages, not afterthoughts.
- **Distinctive, non-childish animal-themed UI** built from a fixed 5-color palette,
  vanilla HTML/CSS/JS, fully responsive from 320px to 1920px+.
- **Retrieval Debug Mode** — see query analysis, retrieval scores, fusion, and reranking
  for any question, without ever exposing hidden model chain-of-thought.
- **Evaluation harness**: 36-question dataset, retrieval metrics (Hit Rate, Recall@K,
  Precision@K, MRR), and generation metrics (citation coverage/correctness).

## Architecture

```text
animal-rights-ai/
├── index.html                  ← frontend entry point
├── css/                        ← main, chat, knowledge, responsive
├── js/                         ← api, app, chat, evidence, knowledge, search, settings, utils
├── backend/
│   ├── main.py                 ← FastAPI app
│   ├── config.py                ← environment-driven settings
│   ├── api/                    ← chat, search, documents, conversations, feedback, analytics, health
│   ├── rag/                    ← pipeline, retrieval, hybrid_search, reranker, embeddings, llm,
│   │                              chunking, prompts, citations, query_analysis
│   ├── ingestion/               ← loader, pdf_loader, text_cleaner, metadata, ingest (CLI)
│   ├── evaluation/              ← dataset loader, metrics
│   └── utils/                   ← logger, supabase_client
├── knowledge_base/              ← source documents + sources.json manifest
├── evaluation/questions.json    ← 36 evaluation questions
├── supabase/migrations/         ← SQL schema, vector/FTS functions, RLS
├── tests/                       ← pytest suite
├── requirements.txt
├── .env.example
└── README.md (this file)
```

**Frontend**: HTML5, CSS3, vanilla JavaScript only — no frameworks, no build step. Open
`index.html` (served via a local static server — see below) and it talks to the FastAPI
backend via `js/api.js`.

**Backend**: Python + FastAPI. All RAG logic (ingestion, retrieval, reranking, generation,
citations, evaluation) lives here.

**Database**: Supabase (PostgreSQL + pgvector).

## The RAG Pipeline

```text
User Question
     ↓
Query Analysis / Understanding      (backend/rag/query_analysis.py)
     ↓
Jurisdiction Clarification Gate      — pauses for legal questions with no jurisdiction
     ↓
Hybrid Retrieval                    (backend/rag/hybrid_search.py)
 ├── Semantic Search (pgvector)      (backend/rag/retrieval.py::semantic_search)
 └── Keyword Search (Postgres FTS)   (backend/rag/retrieval.py::keyword_search)
     ↓
Reciprocal Rank Fusion + Dedup
     ↓
Reranking                           (backend/rag/reranker.py)
     ↓
Relevance Thresholding              — hallucination protection
     ↓
Context Construction                (backend/rag/prompts.py::build_context_block)
     ↓
Grounded LLM Generation             (backend/rag/llm.py)
     ↓
Citation Mapping                    (backend/rag/citations.py)
     ↓
Answer + Citations + Evidence
```

Every stage's output is captured in a `debug_trace`, visible in the frontend's **Retrieval
Debug Mode** (Settings → Retrieval Debug Mode, or try it directly on the **RAG Pipeline**
page) — without ever exposing the LLM's private chain-of-thought, only retrieval mechanics.

## Legal Disclaimer

This application provides educational information based on the documents available in its
knowledge base. It is not a substitute for professional legal advice. Laws and regulations
may change, and users should verify current information with authoritative sources.

## Limitations

- The included knowledge base is a **curated starting corpus** (15 real + 2 synthetic
  documents), not an exhaustive legal or scientific database. Many countries and topics are
  not yet covered — the assistant is designed to say so rather than guess.
- The default reranker is a **transparent heuristic**, not a trained cross-encoder; plugging
  in a dedicated reranker API (e.g. Cohere Rerank) will generally improve ranking quality.
- Query understanding is **rule-based** (keyword/pattern matching), not an LLM classifier —
  deterministic and free to run, but less flexible than an LLM-based approach.
- No end-user authentication is implemented; conversations are not tied to individual user
  accounts (see Future Improvements).
