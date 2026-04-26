-- ============================================================
-- 002_pgvector.sql
-- Enables the pgvector extension and adds an embedding column
-- to the courses table for semantic search.
--
-- Run this in the Supabase dashboard:
--   SQL Editor → paste this → Run
-- ============================================================

-- Enable pgvector (already available in Supabase, just needs enabling)
create extension if not exists vector;

-- Add a 384-dim embedding column to courses.
-- 384 matches the output of all-MiniLM-L6-v2, which we use locally
-- (no API key required). If you switch to text-embedding-3-small
-- (OpenAI) later, drop this column and re-add it with dimension 1536.
alter table courses
  add column if not exists embedding vector(384);

-- IVFFlat index for approximate nearest-neighbour search.
-- lists=100 is appropriate for tables up to ~1 million rows.
-- cosine distance is standard for sentence-transformer embeddings.
create index if not exists courses_embedding_ivfflat
  on courses
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- Helper function: semantic_search_courses
-- Called from Python as a single RPC — avoids sending the raw vector
-- over the REST API in every query.
--
-- Usage (Python):
--   supabase.rpc('semantic_search_courses', {
--     'query_embedding': [...384 floats...],
--     'school_uuid':     '00000000-0000-0000-0000-000000000001',
--     'match_count':     10,
--   }).execute()
create or replace function semantic_search_courses(
  query_embedding vector(384),
  school_uuid     uuid,
  match_count     int default 10
)
returns table (
  id          uuid,
  department  text,
  number      text,
  title       text,
  units       numeric,
  description text,
  catalog_url text,
  similarity  float
)
language sql stable
as $$
  select
    c.id,
    c.department,
    c.number,
    c.title,
    c.units,
    c.description,
    c.catalog_url,
    1 - (c.embedding <=> query_embedding) as similarity
  from courses c
  where
    c.school_id = school_uuid
    and c.embedding is not null
  order by c.embedding <=> query_embedding
  limit match_count;
$$;
