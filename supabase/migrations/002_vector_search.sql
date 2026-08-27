-- 002_vector_search.sql
-- pgvector similarity search + PostgreSQL full-text keyword search functions
-- used by backend/rag/retrieval.py

-- ---------------------------------------------------------------------------
-- match_chunks: semantic (vector) search
-- ---------------------------------------------------------------------------
create or replace function match_chunks(
    query_embedding vector(1536),
    match_count integer default 20,
    filter_country text default null,
    filter_document_type text default null
)
returns table (
    id uuid,
    document_id text,
    content text,
    metadata jsonb,
    section text,
    page integer,
    document_title text,
    document_type text,
    jurisdiction text,
    country text,
    source_url text,
    similarity double precision
)
language sql stable
as $$
    select
        c.id,
        c.document_id,
        c.content,
        c.metadata,
        c.section,
        c.page,
        d.title as document_title,
        d.document_type,
        d.jurisdiction,
        d.country,
        d.source_url,
        1 - (c.embedding <=> query_embedding) as similarity
    from document_chunks c
    join documents d on d.id = c.document_id
    where c.embedding is not null
      and (filter_country is null or d.country = filter_country)
      and (filter_document_type is null or d.document_type = filter_document_type)
    order by c.embedding <=> query_embedding
    limit match_count;
$$;

-- ---------------------------------------------------------------------------
-- search_chunks_fts: keyword (full-text) search
-- ---------------------------------------------------------------------------
create or replace function search_chunks_fts(
    query_text text,
    match_count integer default 20,
    filter_country text default null,
    filter_document_type text default null
)
returns table (
    id uuid,
    document_id text,
    content text,
    metadata jsonb,
    section text,
    page integer,
    document_title text,
    document_type text,
    jurisdiction text,
    country text,
    source_url text,
    rank double precision
)
language sql stable
as $$
    select
        c.id,
        c.document_id,
        c.content,
        c.metadata,
        c.section,
        c.page,
        d.title as document_title,
        d.document_type,
        d.jurisdiction,
        d.country,
        d.source_url,
        ts_rank(c.content_tsv, plainto_tsquery('english', query_text)) as rank
    from document_chunks c
    join documents d on d.id = c.document_id
    where c.content_tsv @@ plainto_tsquery('english', query_text)
      and (filter_country is null or d.country = filter_country)
      and (filter_document_type is null or d.document_type = filter_document_type)
    order by rank desc
    limit match_count;
$$;

-- Recommended: an IVFFlat index for faster approximate vector search once
-- you have a meaningful number of chunks (a few thousand+). Skip this on a
-- fresh, small knowledge base - exact search is fine and this index needs
-- data present to train well.
--
-- create index if not exists idx_chunks_embedding_ivfflat
--   on document_chunks using ivfflat (embedding vector_cosine_ops)
--   with (lists = 100);
