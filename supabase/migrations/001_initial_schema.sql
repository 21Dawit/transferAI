-- ============================================================
-- 001_initial_schema.sql
-- ============================================================

-- ============================================================
-- TABLES
-- ============================================================

-- -------------------------
-- schools
-- (referenced by users and courses, so defined first)
-- -------------------------
create table schools (
  id            uuid primary key default gen_random_uuid(),
  name          text not null,
  type          text not null check (type in ('CCC', 'UC', 'CSU', 'PRIVATE')),
  canonical_url text
);

-- -------------------------
-- users
-- -------------------------
create table users (
  id              uuid primary key default gen_random_uuid(),
  email           text not null unique,
  created_at      timestamptz not null default now(),
  current_ccc_id  uuid references schools (id) on delete set null
);

-- -------------------------
-- profiles
-- -------------------------
create table profiles (
  user_id                uuid primary key references users (id) on delete cascade,
  intended_major         text,
  gpa                    numeric(4, 3) check (gpa >= 0 and gpa <= 4),
  unit_load_preference   int,
  work_hours_per_week    int,
  summer_available       boolean not null default false,
  winter_available       boolean not null default false,
  transfer_year          int
);

-- -------------------------
-- courses
-- -------------------------
create table courses (
  id           uuid primary key default gen_random_uuid(),
  school_id    uuid not null references schools (id) on delete cascade,
  department   text not null,
  number       text not null,
  title        text not null,
  units        numeric(4, 2),
  description  text,
  catalog_url  text,
  last_seen_at timestamptz not null default now()
);

-- -------------------------
-- completed_courses
-- -------------------------
create table completed_courses (
  user_id    uuid not null references users (id) on delete cascade,
  course_id  uuid not null references courses (id) on delete cascade,
  grade      text,
  term_taken text,
  primary key (user_id, course_id)
);

-- -------------------------
-- target_schools
-- -------------------------
create table target_schools (
  user_id   uuid not null references users (id) on delete cascade,
  school_id uuid not null references schools (id) on delete cascade,
  priority  int not null default 0,
  primary key (user_id, school_id)
);

-- -------------------------
-- articulation_agreements
-- -------------------------
create table articulation_agreements (
  id              uuid primary key default gen_random_uuid(),
  from_ccc_id     uuid not null references schools (id) on delete cascade,
  to_school_id    uuid not null references schools (id) on delete cascade,
  major_name      text not null,
  effective_year  int,
  source_url      text,
  last_fetched_at timestamptz
);

-- -------------------------
-- articulation_rows
-- -------------------------
create table articulation_rows (
  agreement_id    uuid not null references articulation_agreements (id) on delete cascade,
  from_course_id  uuid references courses (id) on delete set null,
  to_course_id    uuid references courses (id) on delete set null,
  relationship    text,
  notes           text,
  raw_payload     jsonb,
  primary key (agreement_id, from_course_id, to_course_id)
);

-- -------------------------
-- plans
-- -------------------------
create table plans (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references users (id) on delete cascade,
  created_at timestamptz not null default now(),
  name       text not null,
  status     text not null default 'draft' check (status in ('draft', 'active', 'archived'))
);

-- -------------------------
-- plan_terms
-- -------------------------
create table plan_terms (
  id           uuid primary key default gen_random_uuid(),
  plan_id      uuid not null references plans (id) on delete cascade,
  term_label   text not null,
  term_order   int not null,
  target_units numeric(4, 2)
);

-- -------------------------
-- plan_courses
-- -------------------------
create table plan_courses (
  plan_term_id uuid not null references plan_terms (id) on delete cascade,
  course_id    uuid not null references courses (id) on delete cascade,
  rationale    text,
  citations    jsonb,
  primary key (plan_term_id, course_id)
);

-- -------------------------
-- conversations
-- -------------------------
create table conversations (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references users (id) on delete cascade,
  created_at timestamptz not null default now(),
  title      text
);

-- -------------------------
-- messages
-- -------------------------
create table messages (
  id              uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references conversations (id) on delete cascade,
  role            text not null check (role in ('user', 'assistant', 'tool')),
  content         text,
  tool_calls      jsonb,
  citations       jsonb,
  created_at      timestamptz not null default now()
);


-- ============================================================
-- INDEXES ON FOREIGN KEYS
-- ============================================================

create index on users (current_ccc_id);

create index on courses (school_id);

create index on completed_courses (user_id);
create index on completed_courses (course_id);

create index on target_schools (user_id);
create index on target_schools (school_id);

create index on articulation_agreements (from_ccc_id);
create index on articulation_agreements (to_school_id);

create index on articulation_rows (agreement_id);
create index on articulation_rows (from_course_id);
create index on articulation_rows (to_course_id);

create index on plans (user_id);

create index on plan_terms (plan_id);

create index on plan_courses (plan_term_id);
create index on plan_courses (course_id);

create index on conversations (user_id);

create index on messages (conversation_id);
create index on messages (created_at);


-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

alter table users                   enable row level security;
alter table profiles                enable row level security;
alter table schools                 enable row level security;
alter table courses                 enable row level security;
alter table completed_courses       enable row level security;
alter table target_schools          enable row level security;
alter table articulation_agreements enable row level security;
alter table articulation_rows       enable row level security;
alter table plans                   enable row level security;
alter table plan_terms              enable row level security;
alter table plan_courses            enable row level security;
alter table conversations           enable row level security;
alter table messages                enable row level security;


-- ============================================================
-- RLS POLICIES
-- ============================================================

create policy "users: own row" on users
  for all using (auth.uid() = id);

create policy "profiles: own row" on profiles
  for all using (auth.uid() = user_id);

create policy "schools: public read" on schools
  for select using (true);

create policy "courses: public read" on courses
  for select using (true);

create policy "completed_courses: own rows" on completed_courses
  for all using (auth.uid() = user_id);

create policy "target_schools: own rows" on target_schools
  for all using (auth.uid() = user_id);

create policy "articulation_agreements: public read" on articulation_agreements
  for select using (true);

create policy "articulation_rows: public read" on articulation_rows
  for select using (true);

create policy "plans: own rows" on plans
  for all using (auth.uid() = user_id);

create policy "plan_terms: via plan ownership" on plan_terms
  for all using (
    exists (
      select 1 from plans
      where plans.id = plan_terms.plan_id
        and plans.user_id = auth.uid()
    )
  );

create policy "plan_courses: via plan ownership" on plan_courses
  for all using (
    exists (
      select 1 from plan_terms
      join plans on plans.id = plan_terms.plan_id
      where plan_terms.id = plan_courses.plan_term_id
        and plans.user_id = auth.uid()
    )
  );

create policy "conversations: own rows" on conversations
  for all using (auth.uid() = user_id);

create policy "messages: via conversation ownership" on messages
  for all using (
    exists (
      select 1 from conversations
      where conversations.id = messages.conversation_id
        and conversations.user_id = auth.uid()
    )
  );
