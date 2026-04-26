-- ============================================================
-- 003_major_requirements.sql
-- Adds the major_requirements table for storing structured
-- IGETC, GE, and major prep requirements.
--
-- Run in Supabase SQL Editor → paste → Run
-- ============================================================

create table if not exists major_requirements (
  id               uuid primary key default gen_random_uuid(),
  school_id        uuid not null references schools (id) on delete cascade,
  major_name       text not null,
  requirement_type text not null check (
    requirement_type in (
      'major_prep',    -- major preparation course
      'igetc',         -- IGETC general education area
      'csu_ge',        -- CSU GE breadth area
      'lower_div',     -- lower division requirement
      'elective'       -- elective
    )
  ),
  area_code        text,        -- e.g. "1A", "2", "3B" for IGETC areas
  area_name        text,        -- e.g. "English Composition"
  units_required   numeric(4,2),
  course_constraint jsonb,      -- {"type": "any_of"|"all_of"|"series", "courses": [...]}
  notes            text,
  source_url       text,
  last_fetched_at  timestamptz not null default now()
);

create index on major_requirements (school_id);
create index on major_requirements (major_name);
create index on major_requirements (requirement_type);

alter table major_requirements enable row level security;

create policy "major_requirements: public read" on major_requirements
  for select using (true);
