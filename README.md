# Animal Rights AI

Animal Rights AI is an evidence-grounded knowledge assistant for animal rights, welfare,
protection, and related law. It retrieves passages from a curated document collection and,
when its external services are configured, uses them to produce answers with citations.

> Educational information only—not legal advice. Coverage is limited to the documents in
> this repository and any documents ingested into its database. Verify current law against
> authoritative sources.

## Why this project exists

The repository does not record a personal origin story, so none is claimed here. Its
documented purpose is to make a scattered, curated set of animal-welfare legislation,
standards, and research easier to explore without presenting unsupported answers as fact.
The implementation addresses that need with source-linked retrieval, a visible evidence
panel, and an insufficient-evidence response when retrieval does not meet its configured
threshold. The current corpus and rule-based query analysis are deliberately bounded; this
is a focused educational/engineering project, not a comprehensive legal database.

## What is implemented

- A chat interface with conversation history, jurisdiction clarification, answer type and
  confidence labels, citation markers, evidence excerpts, and optional retrieval diagnostics.
- Hybrid retrieval: pgvector semantic search and PostgreSQL full-text search, fused with
  Reciprocal Rank Fusion and followed by a heuristic reranker. An optional Cohere reranker
  is supported.
- Configurable LLM generation through OpenAI-compatible chat APIs or Anthropic; a local
  extractive mode is included for demonstration.
- A knowledge-base browser, filtered document search, document-detail/source links, a
  pipeline walkthrough, aggregate analytics, and feedback controls.
- PDF, TXT, and Markdown ingestion. Uploads require a writable Supabase connection and a
  configured real embedding provider; demo hash vectors are not stored as semantic vectors.
- A small evaluation question set and reusable retrieval/generation metric functions.
- A responsive, no-build HTML/CSS/JavaScript frontend with locally bundled Feather icons.

The checked-in knowledge base contains curated summaries and two explicitly synthetic
contradiction-test documents. It is a starter collection, not an exhaustive or continuously
updated source of law.

## Screenshots

<p align="center">
  <img src="images/Screenshot%202026-08-27%20064227.png" alt="Animal Rights AI chat interface" width="820">
</p>

## Architecture

```text
index.html / css/ / js/       Vanilla frontend and API client
backend/main.py               FastAPI application and HTTP routes
backend/rag/                  Query analysis, retrieval, reranking, prompting, citations
backend/ingestion/            Manifest loading, extraction, cleaning, chunking, ingestion
backend/evaluation/           Dataset and evaluation metrics
knowledge_base/               Curated source material and metadata manifest
supabase/migrations/          PostgreSQL, pgvector, search functions, and RLS policies
tests/                        Pytest coverage for APIs and core RAG helpers
vendor/                       Pinned Feather icon script and its license
```

The detailed current-state requirements, acceptance criteria, and known gaps are documented
in [SRS.md](./SRS.md).

The browser calls the FastAPI API through `js/api.js`; it never connects directly to
Supabase. Supabase stores document metadata, chunks/embeddings, conversations, messages,
message-source mappings, and feedback. Analytics use aggregate counts.

## Requirements

- Python 3.10 or later
- Supabase project with PostgreSQL, pgvector, and the checked-in migrations applied for
  database-backed retrieval and persistence
- An OpenAI-compatible embedding endpoint and an LLM provider for full RAG operation
- A browser with JavaScript enabled

The UI can be opened locally without a frontend build step. Without external services, the
manifest-backed knowledge browser and local demo behavior remain available; database-backed
search, persistence, ingestion, and full generation are unavailable.

## Setup

### 1. Install Python dependencies

From the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On macOS/Linux, activate with `source .venv/bin/activate` after creating the environment
with `python3 -m venv .venv`.

### 2. Configure services

Copy `.env.example` to `.env` and fill in values for the services you intend to use. Apply
the SQL files in `supabase/migrations/` to the Supabase project in numeric order. The
backend requires `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` for its current write
workflows. The service-role key bypasses RLS: keep it only in the backend environment and
never put it in browser code or a public deployment artifact.

For full semantic retrieval, set `EMBEDDING_PROVIDER=openai` and provide
`EMBEDDING_API_KEY`. The checked-in schema uses 1536-dimensional vectors; if changing
`EMBEDDING_DIMENSIONS`, update the database schema and search function consistently.

For generated answers, use `LLM_PROVIDER=openai` with `LLM_API_KEY`, or
`LLM_PROVIDER=anthropic` with an Anthropic API key. `LLM_PROVIDER=local` is a deterministic
extractive demonstration mode, not a remote language model. `EMBEDDING_PROVIDER=local`
produces deterministic placeholder vectors, not meaningful semantic embeddings; the
application reports that semantic embeddings are unconfigured and does not save those
vectors to Supabase.

Optional reranking uses `RERANKER_PROVIDER=cohere`, `RERANKER_API_KEY`, and optionally
`RERANKER_MODEL`. With `RERANKER_PROVIDER=none`, the built-in heuristic is used.

### 3. Run the API and frontend

In one terminal, from the repository root:

```powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal, also from the repository root:

```powershell
python -m http.server 5500
```

Open <http://localhost:5500/>. The frontend detects a local host and defaults to
`http://localhost:8000/api`. To use a separately hosted backend, enter its public API base
URL (including `/api`) in **Settings**. API documentation is available at
`http://localhost:8000/api/docs`.

### 4. Ingest the checked-in corpus

After configuring Supabase and a real embedding provider:

```powershell
python -m backend.ingestion.ingest
```

Use `--force` to re-process all manifest documents or `--file
knowledge_base/legislation/example.md` to process one manifest path. With no database, the
ingestion command is a dry run and does not populate search data.

## Configuration reference

| Variable | Purpose |
|---|---|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend-only database key required by current write workflows |
| `LLM_PROVIDER` | `openai`, `anthropic`, or local extractive demonstration mode |
| `LLM_API_KEY` | Key for the selected remote LLM provider |
| `LLM_BASE_URL`, `LLM_MODEL` | OpenAI-compatible chat endpoint and model |
| `EMBEDDING_PROVIDER` | `openai` or local placeholder mode |
| `EMBEDDING_API_KEY` | Key for the embedding endpoint |
| `EMBEDDING_BASE_URL`, `EMBEDDING_MODEL` | Embedding endpoint and model |
| `EMBEDDING_DIMENSIONS` | Vector size; must match the Supabase schema (1536 by default) |
| `RERANKER_PROVIDER` | `none` or `cohere` |
| `RERANKER_API_KEY`, `RERANKER_MODEL` | Optional Cohere reranker settings |
| `SEMANTIC_TOP_K`, `KEYWORD_TOP_K`, `FINAL_TOP_K` | Retrieval candidate/result counts |
| `MIN_RELEVANCE_SCORE` | Minimum score for using retrieved chunks in answer generation |
| `CHUNK_SIZE_TOKENS`, `CHUNK_OVERLAP_TOKENS` | Ingestion chunking configuration |
| `APP_ENV` | Environment label |
| `CORS_ORIGINS` | Comma-separated allowed browser origins, or `*` for local/demo use |
| `MAX_UPLOAD_MB` | Maximum uploaded document size in MiB (minimum 1) |
| `FORCE_DEMO_MODE` | Force non-production/demo answer behavior |

The backend reads `.env` through `python-dotenv`; real secrets should instead be supplied
through the deployment's secret manager in hosted environments.

## API overview

- `GET /api/health` — configuration and database reachability indicators
- `POST /api/chat` — answer a question and return citations/evidence metadata
- `POST /api/search` — return ranked search results
- `GET /api/documents` and `GET /api/documents/{id}` — list/filter documents and inspect one
- `POST /api/documents/ingest` — ingest a PDF, TXT, or Markdown upload
- `/api/conversations` — list, create, read, rename, and delete conversations
- `POST /api/feedback` — store a message rating and optional comment
- `GET /api/analytics` — aggregate corpus, usage, and feedback statistics

See the generated OpenAPI UI at `/api/docs` for request and response schemas.

## Tests and evaluation

Run the current automated suite from the repository root:

```powershell
python -m pytest -q
```

The evaluation dataset is `evaluation/questions.json`; reusable metric calculations are in
`backend/evaluation/metrics.py`. There is no checked-in command that runs the entire
retrieval/generation evaluation against a live database and provider, so those metrics are
not represented as benchmark results here.

## Security, privacy, and known limitations

- The application has **no end-user authentication or conversation ownership checks**.
  Conversation and feedback endpoints are not safe for private or sensitive user data on a
  public deployment. A conversation identifier is not an authorization mechanism. Add
  authentication, ownership enforcement, and appropriate abuse controls before treating a
  public instance as a multi-user service.
- The service-role key is required by current write workflows and bypasses Supabase RLS.
  The key must remain server-side; CORS is not authentication.
- The legal/scientific corpus is limited and may become outdated. No legal advice or
  exhaustive coverage is provided.
- Query understanding is rule-based. The default reranker is a transparent heuristic, and
  local embedding vectors are demonstration placeholders rather than semantic vectors.
- File ingestion extracts text from PDFs but does not provide OCR for scanned documents.
- A configured external LLM or embedding provider may receive queries or document text.
  Review its data-handling terms before use.
- The backend API has no built-in authentication or rate limiting.

## Contributing

Open an issue with a reproducible description before making substantial changes. Keep
knowledge-base additions attributable: update `knowledge_base/sources.json`, preserve
source URLs and relevant provenance, and clearly label synthetic test material. Run
`python -m pytest -q` before submitting a change.

## License

This project is licensed under the MIT License. See [LICENSE](./LICENSE). The bundled
Feather Icons library is separately distributed under the license in
[`vendor/FEATHER_LICENSE`](./vendor/FEATHER_LICENSE).
