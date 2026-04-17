# Supabase L2 Cache — Setup & Safety

## What this is

A persistent, cross-instance cache for scraped TCG sales data, backed by
your existing Supabase (handoffpack) Postgres. Layered below the /tmp
sqlite L1 cache:

```
request
  ↓
L1 /tmp sqlite       ← warm Vercel instance, <1ms hit, ephemeral
  ↓ miss
L2 Supabase          ← shared across all Vercel instances, ~50-150ms, persistent
  ↓ stale (>24h)
LIVE scrape          ← PriceCharting + eBay + TCGPlayer, 200-800ms
  ↓
write-through → L1 + L2
```

Popular cards stay hot in Supabase indefinitely. Cold-start pain for
"Charizard" / "Umbreon VMAX Alt Art" / other daily lookups goes away
after the first scrape ever.

## Safety guarantees (read this)

- **Schema isolated.** All Holo tables live in a dedicated `holo` schema,
  never `public`. Cannot collide with handoffpack tables.
- **RLS enabled, zero policies.** `anon` and `authenticated` roles cannot
  read or write a single row. Only the `service_role` key (backend-only)
  has access.
- **Feature-gated.** The Python module is a total no-op when
  `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` env vars are unset — the
  code ships to production dark until you activate it.
- **Graceful degradation.** Every Supabase call has a 3-4s timeout and is
  wrapped in try/except. A Supabase outage falls through to live scrape
  automatically. Holo never 500s because Supabase is slow.
- **Free-tier compatible.** One small schema, two tables, two indexes.
  A row is ~200 bytes; 1M sales ≈ 200 MB, well under the 500 MB free-tier
  database limit. No new bandwidth costs.

## Activation — 4 steps

### 1. Run the migration

Open Supabase Dashboard → SQL Editor → New query. Paste the contents of:

```
db/migrations/001_holo_sales_cache.sql
```

Run it. The file is idempotent — safe to re-run later if anything changes.

Verify by running:

```sql
select table_schema, table_name, row_security_active
from information_schema.tables
where table_schema = 'holo';
```

You should see `sales_cache` and `scrape_runs` both with
`row_security_active = true`.

### 2. Expose the `holo` schema to the Data API

Dashboard → **Project Settings** → **API** → **Data API Settings** →
**Exposed schemas** → add `holo` → Save.

(Required because PostgREST only serves exposed schemas. RLS still
protects the tables — this only tells PostgREST they exist.)

### 3. Copy the service role key

Dashboard → **Project Settings** → **API** → **Project API Keys** →
**service_role** → copy the key.

> ⚠️ This key **bypasses RLS**. Treat it like a database password:
> • Never commit to git.
> • Never prefix with `NEXT_PUBLIC_`.
> • Never expose to the browser or any frontend code.
> • Only use in server-side environments.

### 4. Add Vercel env vars

In the Vercel dashboard for the **holo** project (the Python API, not
handoffpack-www):

```
SUPABASE_URL             = https://ufilszeczpxxggxqaedd.supabase.co
SUPABASE_SERVICE_ROLE_KEY = <service_role key from step 3>
```

Scope: **Production** and **Preview** (not Development — keep local dev
L1-only so you don't pollute production data during testing).

Redeploy. First scrape populates L2; subsequent calls serve from L2 until
the 24h freshness window expires.

## Verification

After first production traffic, run this in the SQL editor:

```sql
-- How many unique sales have we accumulated?
select count(*) from holo.sales_cache;

-- What cards have been scraped?
select card_slug, grade, sales_count, last_fetched_at
from holo.scrape_runs
order by last_fetched_at desc
limit 20;
```

In Vercel function logs, look for:

```
supabase L2 HIT for charizard-151 (raw, 30d) — 42 sales.
```

That's a 200-800ms scrape avoided.

## Reverting / disabling

Instant off: remove `SUPABASE_URL` from Vercel env and redeploy. The code
reverts to L1-only immediately.

Full cleanup (if you ever want to drop the cache entirely):

```sql
drop schema holo cascade;
```

Only touches the Holo schema. Handoffpack data in `public` is unaffected.
