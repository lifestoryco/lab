-- COIN Career Ops — initial Postgres schema, multi-user from day one.
--
-- Design decisions:
--   1. Every row of user data carries user_id uuid → auth.users(id). RLS on
--      every table restricts access to owner. Adding a second user later costs
--      zero migration work.
--   2. roles uniqueness is (user_id, url) — two users can independently track
--      the same posting without one stomping the other's status.
--   3. role_events is an append-only audit log. Every state transition,
--      dismissal-with-reason, applied, offer, rejected lands here. The weekly
--      improvement loop ("compare model to what worked") becomes a single SQL
--      query joining roles.fit_score against role_events.event_type.
--   4. dismissal_reasons is a small controlled vocabulary so the "Not a Fit"
--      UI is data-driven and we can analyze rejection patterns over time.
--      Seeded with the canonical five; extensible by user.
--   5. levels_seed is shared reference data (read-only by app, write by service
--      role only). Sourced from Levels.fyi quarterly via /coin levels-refresh.
--   6. stories (STAR proof points) and offers/connections/outreach all carry
--      user_id so a future second user has their own corpus.

-- ─── extensions ───────────────────────────────────────────────────────────
create extension if not exists "uuid-ossp";

-- ─── helpers ──────────────────────────────────────────────────────────────
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

-- ─── profiles (1:1 with auth.users) ───────────────────────────────────────
create table public.profiles (
  id              uuid primary key references auth.users(id) on delete cascade,
  display_name    text,
  comp_floor_min  integer,                -- override per-user; null → use config default
  comp_floor_max  integer,
  preferred_archetypes text[],            -- subset of ('mid-market-tpm','enterprise-sales-engineer',…)
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create trigger profiles_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

alter table public.profiles enable row level security;

create policy "profiles_self_select" on public.profiles
  for select using (auth.uid() = id);
create policy "profiles_self_upsert" on public.profiles
  for insert with check (auth.uid() = id);
create policy "profiles_self_update" on public.profiles
  for update using (auth.uid() = id);

-- Auto-create a profile row when a new auth user signs up.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data->>'display_name', split_part(new.email, '@', 1)));
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ─── roles ────────────────────────────────────────────────────────────────
-- Mirrors SQLite roles table from coin/careerops/pipeline.py with these changes:
--   - id is bigserial (was integer autoincrement)
--   - timestamps are timestamptz (were ISO TEXT)
--   - user_id added; (user_id, url) is unique
--   - status enforced via check constraint matching STATUSES in pipeline.py

create type public.role_status as enum (
  'discovered','scored','resume_generated','applied','responded',
  'contact','interviewing','offer','rejected','withdrawn','no_apply','closed'
);

create table public.roles (
  id              bigserial primary key,
  user_id         uuid not null references auth.users(id) on delete cascade,
  url             text not null,
  title           text,
  company         text,
  location        text,
  remote          boolean default false,
  lane            text,
  comp_min        integer,
  comp_max        integer,
  comp_source     text,
  comp_currency   text default 'USD',
  comp_confidence real,
  fit_score       real,
  score_stage1    real,
  score_stage2    real,
  score_stage     smallint default 1,
  jd_parsed_at    timestamptz,
  status          public.role_status not null default 'discovered',
  source          text,
  jd_raw          text,
  jd_parsed       jsonb,                  -- jsonb instead of TEXT — queryable
  notes           text,
  posted_at       date,
  discovered_at   timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (user_id, url)
);

create index idx_roles_user_status on public.roles (user_id, status);
create index idx_roles_user_lane   on public.roles (user_id, lane);
create index idx_roles_user_fit    on public.roles (user_id, fit_score desc nulls last);
create index idx_roles_user_stage1 on public.roles (user_id, score_stage1 desc nulls last);

create trigger roles_updated_at
  before update on public.roles
  for each row execute function public.set_updated_at();

alter table public.roles enable row level security;

create policy "roles_owner_all" on public.roles
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ─── role_events (append-only audit log) ──────────────────────────────────
-- Every status change, dismissal reason, applied, offer, rejected, note appended
-- lands here. This is the corpus the weekly improvement loop reads.

create type public.role_event_type as enum (
  'status_change','dismissed','applied','offer_received','rejected',
  'withdrew','note_added','tailor_queued','resume_generated'
);

create table public.role_events (
  id          bigserial primary key,
  role_id     bigint not null references public.roles(id) on delete cascade,
  user_id     uuid not null references auth.users(id) on delete cascade,
  event_type  public.role_event_type not null,
  -- Free-form per-event payload. For status_change: {from, to}. For
  -- dismissed: {reason_code, reason_text, custom_text}. For applied:
  -- {channel}. For note_added: {text}. Schema is intentionally loose so the
  -- UI can evolve without migrations.
  payload     jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now()
);

create index idx_role_events_role on public.role_events (role_id, created_at desc);
create index idx_role_events_user_type_time
  on public.role_events (user_id, event_type, created_at desc);

alter table public.role_events enable row level security;

-- Append-only: users can read their own events, insert their own, but never
-- update or delete. The audit log must be tamper-resistant so the weekly
-- learning corpus is trustworthy.
create policy "role_events_owner_select" on public.role_events
  for select using (auth.uid() = user_id);
create policy "role_events_owner_insert" on public.role_events
  for insert with check (auth.uid() = user_id);

-- ─── dismissal_reasons (controlled vocab for "Not a Fit") ─────────────────
create table public.dismissal_reasons (
  code        text primary key,           -- short stable id, e.g. 'comp_too_low'
  label       text not null,              -- UI label
  description text,                       -- tooltip
  -- Per-user custom additions live in user_dismissal_reasons (later); seeded
  -- vocab is global. user_id null → global; user_id set → custom for one user.
  user_id     uuid references auth.users(id) on delete cascade,
  sort_order  smallint not null default 100,
  created_at  timestamptz not null default now()
);

alter table public.dismissal_reasons enable row level security;

create policy "dismissal_reasons_read_own_or_global" on public.dismissal_reasons
  for select using (user_id is null or auth.uid() = user_id);
create policy "dismissal_reasons_owner_write" on public.dismissal_reasons
  for insert with check (auth.uid() = user_id);
create policy "dismissal_reasons_owner_update" on public.dismissal_reasons
  for update using (auth.uid() = user_id);
create policy "dismissal_reasons_owner_delete" on public.dismissal_reasons
  for delete using (auth.uid() = user_id);

-- Seed the canonical five (global; user_id null).
insert into public.dismissal_reasons (code, label, description, sort_order) values
  ('comp_too_low',          'Comp too low',           'Below the comp floor or implied total comp is unattractive',                10),
  ('wrong_archetype',       'Wrong archetype',        'Title/scope mismatch with current target lanes',                              20),
  ('location_constraint',   'Location constraint',    'Onsite/hybrid in a city I won''t relocate to, or no remote',                  30),
  ('company_signal_negative','Negative company signal','Layoffs, declining ARR, founder drama, regulatory risk',                     40),
  ('seniority_mismatch',    'Seniority mismatch',     'Junior IC framing, or the role is two rungs above realistic landing',         50);

-- ─── stories (STAR proof points) ──────────────────────────────────────────
create table public.stories (
  id              text primary key,           -- e.g. 'cox_true_local_labs'
  user_id         uuid not null references auth.users(id) on delete cascade,
  lane            text not null,              -- archetype id
  headline        text not null,
  context         text not null,
  metric          text not null,
  source_of_truth text not null,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create index idx_stories_user_lane on public.stories (user_id, lane);
create trigger stories_updated_at
  before update on public.stories
  for each row execute function public.set_updated_at();

alter table public.stories enable row level security;
create policy "stories_owner_all" on public.stories
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ─── connections ──────────────────────────────────────────────────────────
create table public.connections (
  id                  bigserial primary key,
  user_id             uuid not null references auth.users(id) on delete cascade,
  first_name          text,
  last_name           text,
  full_name           text,
  linkedin_url        text,
  email               text,
  company             text,
  company_normalized  text,
  position            text,
  connected_on        date,
  seniority           text,
  last_seen           date,
  notes               text,
  created_at          timestamptz not null default now(),
  unique (user_id, linkedin_url)
);

create index idx_connections_user_company on public.connections (user_id, company_normalized);
create index idx_connections_user_seniority on public.connections (user_id, seniority);

alter table public.connections enable row level security;
create policy "connections_owner_all" on public.connections
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ─── outreach ─────────────────────────────────────────────────────────────
create table public.outreach (
  id              bigserial primary key,
  user_id         uuid not null references auth.users(id) on delete cascade,
  role_id         bigint references public.roles(id) on delete set null,
  connection_id   bigint references public.connections(id) on delete set null,
  drafted_at      timestamptz not null default now(),
  sent_at         timestamptz,
  replied_at      timestamptz,
  warmth_score    real,
  draft_message   text,
  contact_role    text,
  target_role_id  bigint references public.roles(id) on delete set null,
  notes           text
);

create index idx_outreach_user_role on public.outreach (user_id, role_id);
create index idx_outreach_user_connection on public.outreach (user_id, connection_id);

alter table public.outreach enable row level security;
create policy "outreach_owner_all" on public.outreach
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ─── offers ───────────────────────────────────────────────────────────────
create table public.offers (
  id                       bigserial primary key,
  user_id                  uuid not null references auth.users(id) on delete cascade,
  role_id                  bigint references public.roles(id) on delete set null,
  company                  text not null,
  title                    text not null,
  received_at              date not null,
  expires_at               date,
  base_salary              integer not null,
  signing_bonus            integer default 0,
  annual_bonus_target_pct  real default 0,
  annual_bonus_paid_history text,
  rsu_total_value          integer default 0,
  rsu_vesting_schedule     text,
  rsu_vest_years           integer default 4,
  rsu_cliff_months         integer default 12,
  equity_refresh_expected  boolean default false,
  benefits_delta           integer default 0,
  pto_days                 integer,
  remote_pct               integer,
  state_tax                text,
  growth_signal            text,
  notes                    text,
  status                   text default 'active',
  created_at               timestamptz not null default now()
);

create index idx_offers_user_role on public.offers (user_id, role_id);
create index idx_offers_user_status on public.offers (user_id, status);

alter table public.offers enable row level security;
create policy "offers_owner_all" on public.offers
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ─── levels_seed (shared reference data, read-only to app) ────────────────
create table public.levels_seed (
  company         text primary key,
  default_level   text,                       -- L4/L5/L6 etc
  unknown         boolean not null default false,
  source_url      text,
  -- Component breakdown by level: { "L5": { "base_p50": …, "rsu_4yr_p50": …, "bonus": … } }
  levels          jsonb not null default '{}'::jsonb,
  updated_at      timestamptz not null default now(),
  notes           text
);

create trigger levels_seed_updated_at
  before update on public.levels_seed
  for each row execute function public.set_updated_at();

alter table public.levels_seed enable row level security;
-- Anyone authenticated can read; only service_role writes (no policy = denied
-- for non-service-role sessions).
create policy "levels_seed_read_authenticated" on public.levels_seed
  for select to authenticated using (true);

-- ─── helpful views for the dashboard ──────────────────────────────────────

-- pipeline_counts: status histogram per user. Cheap to query, good for the
-- header chip and the kanban column counts.
create or replace view public.pipeline_counts as
  select user_id, status, count(*)::int as n
  from public.roles
  group by user_id, status;

-- Views inherit the underlying tables' RLS, but be explicit:
alter view public.pipeline_counts set (security_invoker = on);

-- weekly_improvement_corpus: convenience view for the learning loop. Joins
-- each terminal-state event with the role's fit_score at the time of the
-- event so you can compare model prediction against actual outcome.
create or replace view public.weekly_improvement_corpus as
  select
    e.id              as event_id,
    e.user_id,
    e.event_type,
    e.payload,
    e.created_at      as event_at,
    r.id              as role_id,
    r.company,
    r.title,
    r.lane,
    r.fit_score,
    r.score_stage1,
    r.score_stage2,
    r.comp_min,
    r.comp_max,
    r.comp_source
  from public.role_events e
  join public.roles r on r.id = e.role_id
  where e.event_type in ('dismissed','applied','offer_received','rejected','withdrew');

alter view public.weekly_improvement_corpus set (security_invoker = on);
