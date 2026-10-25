# Software Requirements Specification

## 1. Document control

| Field | Value |
|---|---|
| Product | Animal Rights AI Knowledge Assistant |
| Version | Repository implementation reviewed 2026-10-25 |
| Status | Current-state specification |
| Audience | Maintainers, contributors, and deployment operators |

This specification describes behavior supported by the repository at the stated review
date. Requirements marked **Implemented** are evidenced by the current application and
tests. **Inferred** requirements describe the intended operational behavior implied by
existing interfaces. Gaps and proposals are kept separate from implemented behavior.

## 2. Purpose and scope

The product is a browser-based educational assistant for exploring animal-rights and
animal-welfare material. The frontend communicates with a Python/FastAPI backend. The
backend can retrieve chunks from a curated corpus in Supabase/PostgreSQL, combine semantic
and keyword rankings, rerank evidence, generate a response, and map citations to retrieved
chunks.

The release includes a static HTML/CSS/JavaScript interface, backend API, document
ingestion, database migrations, and small evaluation utilities. It is not a legal advice
service, a comprehensive legal database, or an authenticated multi-user product.

The repository does not state a personal motivation. The supported rationale is that
source-linked retrieval can make a curated cross-topic collection easier to explore while
making evidence and coverage limits visible.

## 3. Terms

| Term | Meaning |
|---|---|
| RAG | Retrieval-Augmented Generation: retrieved source passages are supplied to a generator |
| Chunk | A segment of an ingested document stored and retrieved independently |
| Embedding | Numeric vector representation used for semantic similarity search |
| pgvector | PostgreSQL extension used to store and compare embedding vectors |
| RRF | Reciprocal Rank Fusion, used to combine ranked retrieval lists |
| FTS | PostgreSQL full-text search over chunk text |
| Evidence/citation | Retrieved chunk and its source metadata referenced by an answer |
| Demo mode | Non-production response behavior when required live services are missing or forced off |

## 4. Users and roles

1. **Visitor / question asker (Implemented):** uses chat, search, document browsing,
   analytics, and feedback controls. The system does not require a user account.
2. **Deployment operator (Inferred):** configures environment variables, Supabase
   migrations, embedding/LLM providers, CORS origins, and ingestion.
3. **Knowledge maintainer (Inferred):** curates source documents and
   `knowledge_base/sources.json`.

There are no authenticated roles, user profiles, or record-level conversation ownership
checks in the current release. The API must not be treated as private or secure for
multi-user conversation data in its current form.

## 5. Operating environment and dependencies

- Python 3.10+ backend using FastAPI, Uvicorn, Pydantic, and the Supabase Python client.
- Modern browser with JavaScript enabled; frontend is static and has no build pipeline.
- Supabase/PostgreSQL with pgvector and the SQL functions/policies in
  `supabase/migrations/`.
- Optional OpenAI-compatible chat and embedding services or Anthropic chat service.
- Optional Cohere reranking service.
- Local mode uses extractive answer formatting and deterministic placeholder embeddings;
  it does not provide a semantic model.

## 6. Assumptions and constraints

- `SUPABASE_SERVICE_ROLE_KEY` is required for current backend write workflows. It is
  server-only and bypasses row-level security.
- The database schema and vector-search function define 1536-dimensional embeddings by
  default. A different configured dimension requires a matching database migration.
- The current RLS policies allow public reads of knowledge documents/chunks but do not
  grant anonymous access to conversations, messages, message sources, feedback, or logs.
- Uploaded files are PDF, TXT, or Markdown, subject to `MAX_UPLOAD_MB`.
- PDF text extraction does not perform OCR.
- The knowledge base is curated and finite; external laws and source documents can change.
- CORS is browser-origin policy, not user authentication or API authorization.
- Provider credentials and network availability are deployment dependencies.

## 7. Functional requirements

### FR-001 — Service health

**Status:** Implemented. The API shall provide `GET /api/health` with demo/configuration
indicators for Supabase, embeddings, LLM, reranker, and database reachability.

**Acceptance:** The endpoint returns a schema-valid response when optional services are
missing; a missing write-capable Supabase configuration is not reported as configured.

### FR-002 — Browse the knowledge base

**Status:** Implemented. The API shall list documents with optional country, document-type,
topic, and animal-category filters, return document details, and use the local manifest
when Supabase is unavailable.

**Acceptance:** Manifest-backed reads return valid document records. Database rows map the
schema's `file_path` to the API's `local_file` field. Unknown identifiers return 404.

### FR-003 — Ask a question

**Status:** Implemented. `POST /api/chat` shall accept a non-empty message up to 4000
characters, optional conversation ID, country, debug flag, and jurisdiction-skip flag.

**Acceptance:** Empty or oversized messages are rejected by request validation. A valid
request returns an answer type, confidence, demo-mode indicator, and citations array; a
debug trace is included only when requested.

### FR-004 — Clarify legal jurisdiction

**Status:** Implemented. When query analysis identifies a legal question that needs a
jurisdiction, the system shall return a clarification instead of silently choosing one,
unless the request explicitly bypasses the clarification gate.

**Acceptance:** A clarification response identifies the missing jurisdiction and includes
no fabricated citations.

### FR-005 — Retrieve and rank evidence

**Status:** Implemented. With configured services, the backend shall combine pgvector
semantic retrieval and PostgreSQL full-text retrieval using RRF, then apply the configured
reranker or heuristic fallback.

**Acceptance:** Results are deduplicated by chunk ID and limited to configured top-K values.
When a real embedding provider is not configured, semantic search shall not use
deterministic placeholder vectors.

### FR-006 — Generate or decline to generate an answer

**Status:** Implemented. The backend shall use retrieved chunks to construct an evidence
context. It shall return an insufficient-evidence response when no chunk meets
`MIN_RELEVANCE_SCORE`. When required service configuration is absent or forced demo mode is
active, it shall identify that condition instead of implying that a live model generated
the answer.

**Acceptance:** No answer is generated from below-threshold evidence; demo responses are
marked `demo_mode=true`.

### FR-007 — Map citations to evidence

**Status:** Implemented. Citation markers shall correspond to chunks in the retrieved set
and expose their source title, type, jurisdiction, country, section/page where present,
source URL, relevance score, and excerpt.

**Acceptance:** Citation indices returned by chat resolve to returned evidence records;
unknown citations are not synthesized.

### FR-008 — Search

**Status:** Implemented. `POST /api/search` shall accept a query of 1–500 characters,
optional country/document-type filters, and `top_k` from 1 through 30, returning ranked
chunk results and excerpts.

**Acceptance:** Invalid query length or top-K values are rejected; a valid query returns a
`results` array, which may be empty if the database has no matches.

### FR-009 — Persist and manage conversations

**Status:** Implemented when Supabase is configured. The API shall support listing,
creating, reading, renaming, and deleting conversations and their associated messages.

**Acceptance:** Message history is returned in creation order; deleting a conversation
cascades according to the database foreign keys. **Security limitation:** endpoints
currently lack authentication and ownership checks.

### FR-010 — Upload and ingest documents

**Status:** Implemented. The API shall accept `.pdf`, `.txt`, and `.md` files, enforce
`MAX_UPLOAD_MB`, reject empty or unsupported files, and run accepted files through
extraction, cleaning, chunking, embedding, and database insertion.

**Acceptance:** Upload fails with an explicit service-unavailable response if writable
Supabase or a configured embedding provider is missing; files larger than the configured
limit are rejected before ingestion; dry-run or extraction-failure statuses are not
reported as successfully ingested.

### FR-011 — Record feedback

**Status:** Implemented when Supabase is configured. The API shall accept a message ID,
rating of -1 or 1, and an optional comment up to 1000 characters.

**Acceptance:** Out-of-range ratings or overlong comments are rejected; unavailable
Supabase returns an explicit service error.

### FR-012 — Display aggregate analytics

**Status:** Implemented. `GET /api/analytics` shall return document/chunk/conversation/
message counts, positive and negative feedback counts, common topics/countries, and the
data source. If database analytics are unavailable, corpus counts may come from the local
manifest and usage counts shall be zero.

**Acceptance:** Response fields conform to `AnalyticsOut`; it does not expose individual
message content.

### FR-013 — Configure frontend behavior

**Status:** Implemented. The interface shall allow changing the API base URL, toggling
retrieval debug mode, browsing the pipeline walkthrough, and accessing the mobile evidence
drawer.

**Acceptance:** Settings persist in browser local storage. API/network failures are shown as
errors, not as successful empty results where an action failed.

## 8. Non-functional requirements and quality attributes

### NFR-001 — Evidence honesty

The system shall distinguish insufficient evidence and demo behavior from a successful
live generated answer. Placeholder vectors shall not be persisted as semantic embeddings.

### NFR-002 — Secret handling

Service-role and provider keys shall be read from backend environment configuration and
shall not be embedded in frontend assets or committed `.env` files. `.env.example` may
contain empty placeholders.

### NFR-003 — Privacy and access control

**Current gap:** The release has no end-user authentication, conversation ownership
enforcement, or API rate limiting. Conversation IDs are not authorization. Before public
multi-user deployment, access control and abuse safeguards are required. No sensitive
personal data should be entered into an unauthenticated deployment.

### NFR-004 — Error visibility

Validation and unavailable-service conditions shall return explicit HTTP errors or visible
UI messages. Operational failures shall be logged by the backend and shall not be
presented as successful ingestion.

### NFR-005 — Maintainability

Backend configuration is environment-driven; routes, RAG stages, ingestion, and frontend
API requests are separated into modules. Automated tests cover core API and RAG behavior.

### NFR-006 — Usability and accessibility

The frontend shall remain responsive across its existing desktop/tablet/mobile layouts,
provide labels for icon-only controls, and support keyboard focus for interactive controls.
The icon set is locally bundled to avoid a runtime CDN dependency.

### NFR-007 — Performance

No service-level latency, throughput, or availability target is specified by the
repository. Search and generation depend on database/provider response time; query and
upload limits are configured separately.

## 9. External interfaces

### 9.1 User interface

The single-page interface contains Landing, Chat, Knowledge Base, Search, RAG Pipeline,
Analytics, and Settings views. It provides citations/evidence, conversation controls,
filters, upload controls, and a retrieval-debug mode. The frontend uses static local assets
and browser `fetch()` calls to the configured API.

### 9.2 HTTP API

The JSON API is served under `/api`; OpenAPI docs are available at `/api/docs` and
`/api/openapi.json`. Document uploads use multipart form data. Request/response validation
uses Pydantic models.

### 9.3 External services

- Supabase/PostgreSQL: vector and full-text retrieval, document ingestion, conversation and
  feedback persistence, and analytics.
- OpenAI-compatible chat and embedding endpoints: optional generation and real embeddings.
- Anthropic Messages API: optional answer generation.
- Cohere Rerank API: optional second-stage reranking.

## 10. Data requirements

The migrations define:

- `documents`: source metadata and file provenance/hash.
- `document_chunks`: chunk content, section/page metadata, vector embedding, and FTS vector.
- `conversations` and `messages`: conversation metadata and message content.
- `message_sources`: message-to-chunk citation mapping.
- `feedback`: message rating and optional comment.
- `retrieval_logs`: optional retrieval instrumentation table.

Document IDs are text identifiers; chunk, conversation, message, feedback, and source IDs
are UUIDs. Foreign keys cascade on document/conversation/message deletion as defined in
`001_initial_schema.sql`. The vector dimension is 1536 by default. RLS policies in
`003_rls.sql` expose knowledge-base rows for public reads and deny anonymous access to
other tables; server-side service-role operations bypass those policies.

## 11. Business rules and error handling

1. User messages must contain 1–4000 characters; search queries 1–500 characters.
2. Search `top_k` must be 1–30.
3. Feedback ratings must be -1 or 1; comments are limited to 1000 characters.
4. Upload extensions are limited to PDF, TXT, and Markdown; uploaded documents must be
   non-empty and within the configured size limit.
5. Database ingestion requires configured Supabase write access and real embeddings.
6. If a legal question needs a jurisdiction, clarification is preferred over guessing.
7. Chunks below the configured relevance threshold are excluded from generation.
8. Unavailable Supabase/provider operations return errors or demo responses as appropriate;
   a dry run is not a successful database ingestion.

## 12. Use cases and exceptional flows

### UC-01: Ask a question

1. Visitor enters a question and optional jurisdiction.
2. Frontend sends `POST /api/chat`.
3. Backend analyzes intent and jurisdiction, retrieves/reranks evidence when available, and
   either requests clarification, reports insufficient evidence/demo mode, or generates a
   response with source mappings.
4. Frontend displays the answer and evidence panel.

**Exceptions:** invalid message → 422; missing service configuration → demo response or
unavailable status; provider error → explicit generation/retrieval error behavior.

### UC-02: Search documents

1. Visitor enters a query and optional document filters.
2. Backend returns ranked chunk excerpts.
3. Visitor opens a source or asks about a document.

**Exceptions:** invalid query/top-K → 422; no candidates → empty results; database/provider
unavailable → visible search error or no semantic candidates.

### UC-03: Upload a source document

1. Visitor selects a supported file.
2. Backend checks service configuration, extension, non-empty content, and size.
3. Backend saves and processes the file, then stores metadata/chunks/embeddings.

**Exceptions:** missing database or embedding service → 503; unsupported/empty file → 400;
oversized file → 413; extraction/ingestion failure → explicit failure, not a success toast.

### UC-04: Manage a conversation

When Supabase is available, the visitor can list, open, rename, and delete stored
conversations. The current implementation does not verify that the caller owns a
conversation; this flow is unsafe for private use on a public deployment.

## 13. Verification and traceability

| Requirement area | Verification |
|---|---|
| API startup, validation, demo responses, health, documents, analytics, feedback | `tests/test_api.py` |
| Chunking behavior | `tests/test_chunking.py` |
| Citation mapping | `tests/test_citations.py` |
| Query analysis and jurisdiction clarification | `tests/test_query_analysis.py` |
| Retrieval fusion, reranking, and unconfigured embedding behavior | `tests/test_retrieval.py` |
| Complete automated suite | `python -m pytest -q` |

Live Supabase migrations, remote provider calls, browser rendering across devices, and
end-to-end ingestion against a provisioned database require external/manual verification.
The repository includes an evaluation dataset and metric functions but no turnkey live
evaluation command.

## 14. Known gaps

- No authentication, conversation ownership, authorization, or rate limiting.
- No OCR for scanned PDFs.
- The included knowledge corpus is limited and may be out of date.
- Query understanding is rule-based and local embeddings are placeholders.
- The evaluation metrics have no checked-in live orchestration command or reported
  benchmark baseline.
- Performance and availability service levels are unspecified.

## 15. Future requirements (not part of current behavior)

- Add authentication, enforce per-user ownership for conversations/messages/feedback, and
  protect write endpoints before multi-user public use.
- Add abuse/rate controls and deployment-specific security headers.
- Add OCR and ingestion status/retry management for larger document workflows.
- Add a repeatable evaluation runner with versioned datasets and recorded baseline results.
- Define measurable latency, availability, and retention targets with project-owner input.
