-- 001_initial_schema.sql
-- Animal Rights AI - core schema
-- Run this in the Supabase SQL editor, or via `supabase db push` / psql.

create extension if not exists "uuid-ossp";
create extension if not exists vector;   -- pgvector
create extension if not exists pg_trgm;  -- trigram support, useful for fuzzy keyword matching

-- ---------------------------------------------------------------------------
-- documents
-- ---------------------------------------------------------------------------
create table if not exists documents (
    id                 text primary key,           -- matches sources.json "id"
    title              text not null,
    description        text default '',
    author             text default '',
    organization       text default '',
    document_type      text not null default 'other',
    jurisdiction       text default '',
    country            text default '',
    language           text default 'English',
    publication_date   date,
    source_url         text default '',
    file_path          text not null,
    file_hash          text not null,
    is_synthetic       boolean not null default false,
    topics             text[] not null default '{}',
    animal_categories  text[] not null default '{}',
    created_at         timestamptz not null default now(),
    updated_at         timestamptz not null default now()
);

create index if not exists idx_documents_country on documents (country);
create index if not exists idx_documents_type on documents (document_type);
create index if not exists idx_documents_topics on documents using gin (topics);
create index if not exists idx_documents_animal_categories on documents using gin (animal_categories);

-- ---------------------------------------------------------------------------
-- document_chunks
-- ---------------------------------------------------------------------------
create table if not exists document_chunks (
    id             uuid primary key default uuid_generate_v4(),
    document_id    text not null references documents(id) on delete cascade,
    chunk_index    integer not null,
    content        text not null,
    section        text,
    page           integer,
    metadata       jsonb not null default '{}'::jsonb,
    embedding      vector(1536),           -- dimension must match EMBEDDING_DIMENSIONS
    content_tsv    tsvector generated always as (to_tsvector('english', content)) stored,
    created_at     timestamptz not null default now(),

    unique (document_id, chunk_index)
);

create index if not exists idx_chunks_document_id on document_chunks (document_id);
create index if not exists idx_chunks_content_tsv on document_chunks using gin (content_tsv);
create index if not exists idx_chunks_metadata on document_chunks using gin (metadata);

-- ---------------------------------------------------------------------------
-- conversations
-- ---------------------------------------------------------------------------
create table if not exists conversations (
    id          uuid primary key default uuid_generate_v4(),
    user_id     uuid,                     -- nullable: supports anonymous / demo usage
    title       text not null default 'New conversation',
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

create index if not exists idx_conversations_user on conversations (user_id);

-- ---------------------------------------------------------------------------
-- messages
-- ---------------------------------------------------------------------------
create table if not exists messages (
    id               uuid primary key default uuid_generate_v4(),
    conversation_id  uuid not null references conversations(id) on delete cascade,
    role             text not null check (role in ('user', 'assistant', 'system')),
    content          text not null,
    answer_type      text,                -- legal | scientific | ethical | educational | comparative | clarification
    confidence       text,                -- high | medium | low | none | n/a
    created_at       timestamptz not null default now()
);

create index if not exists idx_messages_conversation on messages (conversation_id, created_at);

-- ---------------------------------------------------------------------------
-- message_sources (citation -> chunk mapping)
-- ---------------------------------------------------------------------------
create table if not exists message_sources (
    id                uuid primary key default uuid_generate_v4(),
    message_id        uuid not null references messages(id) on delete cascade,
    chunk_id          uuid not null references document_chunks(id) on delete cascade,
    relevance_score   double precision not null default 0,
    citation_index    integer not null,
    created_at        timestamptz not null default now()
);

create index if not exists idx_message_sources_message on message_sources (message_id);

-- ---------------------------------------------------------------------------
-- feedback
-- ---------------------------------------------------------------------------
create table if not exists feedback (
    id          uuid primary key default uuid_generate_v4(),
    message_id  uuid not null references messages(id) on delete cascade,
    rating      integer not null check (rating in (-1, 1)),
    comment     text,
    created_at  timestamptz not null default now()
);

create index if not exists idx_feedback_message on feedback (message_id);

-- ---------------------------------------------------------------------------
-- retrieval_logs (optional, useful for debugging & evaluation over time)
-- ---------------------------------------------------------------------------
create table if not exists retrieval_logs (
    id                uuid primary key default uuid_generate_v4(),
    query             text not null,
    rewritten_query   text,
    filters           jsonb default '{}'::jsonb,
    num_semantic_hits integer default 0,
    num_keyword_hits  integer default 0,
    num_final_chunks  integer default 0,
    top_score         double precision,
    latency_ms        integer,
    created_at        timestamptz not null default now()
);

-- keep updated_at fresh
create or replace function set_updated_at() returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_documents_updated_at on documents;
create trigger trg_documents_updated_at before update on documents
    for each row execute procedure set_updated_at();

drop trigger if exists trg_conversations_updated_at on conversations;
create trigger trg_conversations_updated_at before update on conversations
    for each row execute procedure set_updated_at();
