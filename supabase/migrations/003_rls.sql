-- 003_rls.sql
-- Row Level Security policies.
--
-- Design:
--   - The FastAPI backend is the ONLY writer, always using the Supabase
--     SERVICE ROLE key, which bypasses RLS entirely. This is safe because
--     the service role key is never sent to the frontend (see backend/
--     utils/supabase_client.py and README "Security").
--   - Public knowledge-base data (documents, chunks) is readable by the
--     anon key so a purely read-only frontend integration (or future
--     direct Supabase usage) cannot see private conversation data.
--   - Conversations, messages, message_sources, and feedback are NOT
--     exposed to the anon key at all in this default configuration,
--     since this project does not implement end-user authentication.
--     If you add Supabase Auth, replace the policies below with
--     `user_id = auth.uid()` style ownership checks.

alter table documents enable row level security;
alter table document_chunks enable row level security;
alter table conversations enable row level security;
alter table messages enable row level security;
alter table message_sources enable row level security;
alter table feedback enable row level security;
alter table retrieval_logs enable row level security;

-- Public, read-only knowledge base content
drop policy if exists "public read documents" on documents;
create policy "public read documents"
    on documents for select
    to anon, authenticated
    using (true);

drop policy if exists "public read chunks" on document_chunks;
create policy "public read chunks"
    on document_chunks for select
    to anon, authenticated
    using (true);

-- Everything else: no anon/authenticated access by default.
-- (No policy = default deny once RLS is enabled.) The backend service
-- role key bypasses RLS, so /api/chat, /api/conversations, /api/feedback
-- continue to work normally through the API.

-- ---------------------------------------------------------------------------
-- OPTIONAL: if you add Supabase Auth and want end users to read their own
-- conversations directly from the client (bypassing the API), uncomment
-- and adapt policies like these:
-- ---------------------------------------------------------------------------
-- drop policy if exists "own conversations" on conversations;
-- create policy "own conversations"
--     on conversations for select
--     to authenticated
--     using (user_id = auth.uid());
--
-- drop policy if exists "own messages" on messages;
-- create policy "own messages"
--     on messages for select
--     to authenticated
--     using (
--       conversation_id in (select id from conversations where user_id = auth.uid())
--     );
