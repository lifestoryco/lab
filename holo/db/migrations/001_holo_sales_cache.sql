-- ============================================================================
-- Holo sales cache — persistent L2 cache for scraped TCG sales data.
--
-- Design goals
-- ------------
-- 1. FULL ISOLATION from handoffpack data. Everything lives in a dedicated
--    `holo` schema. This migration NEVER touches `public` or any other
--    existing schema. Re-running this file is safe: every statement is
--    idempotent (`if not exists` / `or replace` / parameterised grants).
--
-- 2. ZERO ANON EXPOSURE. Row Level Security is enabled on both tables with
--    NO policies defined — which means `anon` and `authenticated` roles
--    cannot read or write a single row. Only the `service_role` key
--    (used server-side only, never shipped to the client) can access data,
--    because service_role bypasses RLS by design.
--
-- 3. NO NEW RECURRING COSTS. Free-tier compatible: a few KB of schema, two
--    small indexes, tables grow linearly with unique sales (~200 bytes/row).
--    1M sales ≈ 200 MB, well under the 500 MB free-tier DB limit.
--
-- Manual activation steps (see docs/supabase-setup.md)
-- ----------------------------------------------------
-- 1. Paste this file into Supabase Dashboard → SQL Editor → New query → Run.
-- 2. Settings → API → "Data API Settings" → add `holo` to Exposed schemas.
-- 3. Add SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY to Vercel env (Python
--    function scope only; NEVER prefix with NEXT_PUBLIC_).
-- 4. Redeploy. The Python scraper will autodetect the env vars and start
--    using L2 transparently. No code change needed post-deploy.
-- ============================================================================

create schema if not exists holo;

-- ─── Table: sales_cache ────────────────────────────────────────────────────
-- One row per unique scraped sale. Deduped via deterministic sale_id
-- (hash of source + source_url + price_cents + sale_date) so repeated
-- scrapes of the same underlying sale are no-ops.
create table if not exists holo.sales_cache (
    sale_id         text primary key,
    card_slug       text not null,
    grade           text not null default 'raw',
    source          text not null,
    source_url      text,
    sale_date       date not null,
    price_cents     integer not null check (price_cents >= 0),
    title           text,
    inserted_at     timestamptz not null default now()
);

-- Hot read path: "give me last N days of sales for this card + grade",
-- sorted newest-first. Covering index for the expected filter set.
create index if not exists sales_cache_card_grade_date_idx
    on holo.sales_cache (card_slug, grade, sale_date desc);

-- Secondary: occasional maintenance queries ("old rows we could archive").
create index if not exists sales_cache_inserted_at_idx
    on holo.sales_cache (inserted_at);

comment on table holo.sales_cache is
    'Persistent cache of scraped TCG card sales. One row per unique sale. '
    'Populated by the Python scraper via write-through from scraper.fetch_sales().';


-- ─── Table: scrape_runs ────────────────────────────────────────────────────
-- Records when we last did a live scrape for a (card, grade, days) tuple.
-- Freshness check: if last_fetched_at is within the L2 trust window (24h),
-- we serve sales_cache directly without hitting PriceCharting. If stale,
-- we re-scrape and write-through to both tables.
create table if not exists holo.scrape_runs (
    card_slug       text not null,
    grade           text not null default 'raw',
    days            integer not null,
    last_fetched_at timestamptz not null default now(),
    sales_count     integer not null default 0,
    primary key (card_slug, grade, days)
);

create index if not exists scrape_runs_last_fetched_idx
    on holo.scrape_runs (last_fetched_at);

comment on table holo.scrape_runs is
    'Freshness ledger for the holo L2 cache. Used to decide when a live '
    're-scrape is needed despite L2 hits existing.';


-- ─── Row Level Security: lock everything down ──────────────────────────────
-- RLS on + zero policies = anon/authenticated cannot touch these tables.
-- Only service_role (used only by the Python backend) has access.
alter table holo.sales_cache enable row level security;
alter table holo.scrape_runs enable row level security;


-- ─── Explicit grants (defence in depth) ────────────────────────────────────
-- service_role bypasses RLS anyway, but we grant usage on the schema
-- explicitly so PostgREST can serve the tables when `holo` is added to
-- the exposed-schemas list in dashboard → API settings.
grant usage on schema holo to service_role;
grant all on holo.sales_cache to service_role;
grant all on holo.scrape_runs to service_role;

-- Revoke ANY default privileges that may have been granted to public roles
-- by a stray policy. (No-ops if nothing was ever granted.)
revoke all on schema holo from public;
revoke all on holo.sales_cache from anon, authenticated, public;
revoke all on holo.scrape_runs from anon, authenticated, public;
