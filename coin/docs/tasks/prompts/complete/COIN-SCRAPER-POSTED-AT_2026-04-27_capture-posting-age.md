---
task: COIN-SCRAPER-POSTED-AT
title: Capture posting age (`posted_at`) from LinkedIn cards, score freshness, surface in dashboard
phase: Scraper Fidelity
size: M
depends_on: COIN-AUTOPIPELINE
created: 2026-04-27
---

# COIN-SCRAPER-POSTED-AT: Capture and surface job posting age

## Context

Today's `/coin discover --utah` returned 40 roles, all stamped
`discovered_at = 2026-04-27` — that's when **Coin** saw them, not when
LinkedIn published them. Sean flagged role #11 (Filevine) as a posting
that has actually been live for ~a month. A month-old SE posting is a
very different prospect than a 3-day-old one:

- The recruiter screen window is usually 5–14 days; month-old roles are
  often "still up" because the req hasn't been closed in the ATS, not
  because there's actual hiring momentum.
- Tailoring effort spent on stale roles is wasted effort. Coin's whole
  thesis is throughput per unit of Sean's attention.

The `roles` table has no `posted_at` column. LinkedIn's guest job cards
DO expose this — usually inside a `<time>` element with both a
human-readable string ("Posted 3 days ago") and a machine-readable
`datetime="2026-04-23"` attribute. We need to capture it, persist it,
score on it, and show it.

## Goal

After this task ships:

1. Every newly scraped role has a `posted_at` ISO date when LinkedIn
   exposed one.
2. Fit scoring includes a `freshness` dimension that penalizes stale
   roles.
3. `discover.py --max-age-days N` filters out roles older than N days
   before scoring (saves Claude tokens on stale postings).
4. The Rich dashboard shows an "Age" column so Sean can eyeball
   freshness at a glance.

## Pre-conditions

- [ ] Migrations m003 (`connections_outreach`) and m004
  (`outreach_role_tag`) are already applied to `data/db/pipeline.db`
- [ ] `careerops/scraper.py::_parse_linkedin_cards` exists (currently
  around lines 83–119 of that file — confirm with Read before editing)
- [ ] `FIT_SCORE_WEIGHTS` dict exists in `config.py` and currently sums
  to 1.0 — verify before reweighting
- [ ] `careerops/score.py::score_breakdown` is currently around lines
  176–251 (confirm before editing)
- [ ] `pytest tests/ -q` is GREEN at 228 tests as of 2026-04-27 (this is
  the regression baseline)

## Steps

### Step 1 — Author migration `m005_posted_at.py`

Create `coin/scripts/migrations/m005_posted_at.py`. Mirror the pattern
of the existing `m004_outreach_role_tag.py` exactly:

- Self-bootstraps prior migrations (m001 → m004) when run on a fresh DB
- `PRAGMA table_info(roles)` check before `ALTER TABLE roles ADD COLUMN
  posted_at TEXT` — must be idempotent (running twice is a no-op)
- Writes a row into `schema_migrations` table with id `m005_posted_at`
  on success
- Supports `--rollback` flag:
  - SQLite ≥3.35 supports `ALTER TABLE roles DROP COLUMN posted_at`;
    detect via `sqlite3.sqlite_version_info >= (3, 35, 0)` and use it
    if available
  - Otherwise: rebuild the table — `CREATE TABLE roles_new ...` (copy
    the current schema MINUS posted_at), `INSERT INTO roles_new SELECT
    <all columns except posted_at> FROM roles`, drop old, rename new.
    Then delete the `m005_posted_at` row from `schema_migrations`.

CLI:
```bash
.venv/bin/python scripts/migrations/m005_posted_at.py            # apply
.venv/bin/python scripts/migrations/m005_posted_at.py --rollback # revert
```

### Step 2 — Extract `posted_at` in the scraper

Edit `coin/careerops/scraper.py::_parse_linkedin_cards` (currently
~lines 83–119). For each card BeautifulSoup element, try selectors in
this order and stop at the first hit:

1. `time.job-search-card__listdate`
2. `time.job-search-card__listdate--new`
3. `time[datetime]`
4. `.job-search-card__listdate` (fallback for non-`time` tags)

When an element is found:

- **Prefer the `datetime` attribute** if present and ISO-parseable
  (`datetime.date.fromisoformat`). LinkedIn emits `YYYY-MM-DD`.
- **Fallback:** parse the human string (`element.get_text(strip=True)`)
  with this regex pattern:
  ```python
  RELATIVE_AGE_RE = re.compile(
      r"(\d+)\s+(minute|hour|day|week|month|year)s?\s+ago",
      re.IGNORECASE,
  )
  ```
  Multiply the integer by `{minute: 0, hour: 0, day: 1, week: 7,
  month: 30, year: 365}` to get a day-delta, then subtract from
  `datetime.date.today()` (use `datetime.date.today()` not `datetime.now()`
  so it's stable in tests via monkeypatch). Minutes/hours collapse to
  "today" (delta = 0).
- If no element found OR string unparseable → set `posted_at = None`.

Emit `posted_at` (ISO string `YYYY-MM-DD` or `None`) as a new key in
the role dict each card produces.

### Step 3 — Persist `posted_at` in the pipeline

Edit `coin/careerops/pipeline.py`:

- **`init_db` schema string** — add `posted_at TEXT` to the `roles`
  CREATE TABLE so fresh installs get the column. Place it after
  `discovered_at` for readability. (Idempotent because m005 also runs
  on existing DBs.)
- **`upsert_role`** — accept `posted_at` kwarg (default `None`). On
  INSERT, write whatever was passed. On UPDATE conflict, use
  `COALESCE(excluded.posted_at, roles.posted_at)` semantics so we
  NEVER clobber a known posted_at with `NULL` — once captured, it
  stays captured even if a future scrape misses the element.

### Step 4 — Add `score_freshness` dimension

Add to `coin/careerops/score.py`:

```python
def score_freshness(posted_at: str | None) -> int:
    """Score role freshness. Stale postings rarely convert.

    Returns 100 if ≤7d, 80 if ≤14d, 60 if ≤30d, 30 if ≤90d, 10 if
    >90d, 50 if unknown (don't penalize too hard for missing data).
    """
    if posted_at is None:
        return 50
    try:
        posted = datetime.date.fromisoformat(posted_at)
    except (ValueError, TypeError):
        return 50
    age_days = (datetime.date.today() - posted).days
    if age_days <= 7:
        return 100
    if age_days <= 14:
        return 80
    if age_days <= 30:
        return 60
    if age_days <= 90:
        return 30
    return 10
```

**Rebalance `FIT_SCORE_WEIGHTS` in `config.py`** so total stays 1.0:

| Dimension | Old weight | New weight |
|---|---|---|
| `freshness` | (new) | 0.04 |
| `application_effort` | 0.04 | 0.02 |
| `culture_fit` | 0.03 | 0.01 |
| (everything else) | unchanged | unchanged |

Net change: `+0.04 − 0.02 − 0.02 = 0.00`. Still sums to 1.0.

Wire `freshness` into `score_breakdown` (around lines 176–251 of
`score.py`). The return shape stays a dict; just add a `"freshness"`
key alongside the others. Update the docstring at the top of
`score.py` (around lines 1–40) to list the new dimension and new
weights.

### Step 5 — Add `--max-age-days` to discover.py

Edit `coin/scripts/discover.py`:

- Add `--max-age-days N` (type=int, default=None) argparse flag.
- After scraping but BEFORE scoring/upserting, when the flag is set:
  filter the role list — drop any role whose `posted_at` parses to a
  date older than `N` days from `datetime.date.today()`. Roles with
  `posted_at = None` PASS the filter (don't punish missing data here;
  the `freshness` score already handles that softly).
- Print a one-line summary: `"--max-age-days {N}: dropped {X} of {Y}
  roles older than cutoff"`.

### Step 6 — Add "Age" column to dashboard

Edit `coin/scripts/dashboard.py` AND any Rich-table render in
`coin/careerops/pipeline.py`:

Helper function (place in `pipeline.py` near other formatters):

```python
def format_age(posted_at: str | None) -> str:
    if not posted_at:
        return "?"
    try:
        days = (datetime.date.today() - datetime.date.fromisoformat(posted_at)).days
    except (ValueError, TypeError):
        return "?"
    if days < 7:
        return f"{days}d"
    if days < 30:
        return f"{days // 7}w"
    if days < 365:
        return f"{days // 30}mo"
    return "1y+"
```

Add an "Age" column to the roles table. Position: **between Lane and
Company**. Width: 5 chars. Right-aligned looks cleanest.

### Step 7 — Tests

#### 7a. Extend `coin/tests/test_scraper.py`

Add four tests covering `_parse_linkedin_cards` posting-age extraction:

- `test_parse_linkedin_card_extracts_posted_at_from_datetime_attr` —
  fixture HTML with `<time datetime="2026-04-20">2 weeks ago</time>` →
  `posted_at == "2026-04-20"`
- `test_parse_linkedin_card_extracts_posted_at_from_relative_string` —
  fixture HTML with `<time>Posted 3 days ago</time>` (no datetime
  attr); monkeypatch `datetime.date.today` to return
  `2026-04-27` → `posted_at == "2026-04-24"`
- `test_parse_linkedin_card_posted_at_none_when_no_time_element` —
  card with no `<time>` → `posted_at is None`
- `test_parse_linkedin_card_posted_at_none_when_unparseable` — card
  with `<time>brand new!</time>` (no datetime, no regex match) →
  `posted_at is None`

#### 7b. New file `coin/tests/test_score_freshness.py`

Six tests across the buckets (use freezegun OR
`monkeypatch.setattr(datetime.date, "today", ...)` — match whatever
pattern existing tests use):

- `test_score_freshness_fresh` (3d → 100)
- `test_score_freshness_recent` (10d → 80)
- `test_score_freshness_aging` (20d → 60)
- `test_score_freshness_stale` (60d → 30)
- `test_score_freshness_ancient` (200d → 10)
- `test_score_freshness_unknown_returns_neutral` (None → 50)
- bonus: `test_score_freshness_unparseable_returns_neutral` ("not a
  date" → 50)

#### 7c. New file `coin/tests/test_migrations_m005.py`

Three tests against an in-memory or tmp_path SQLite:

- `test_m005_adds_posted_at_column` — apply, then `PRAGMA
  table_info(roles)` includes `posted_at`
- `test_m005_idempotent` — apply twice; no error, column still present
  exactly once
- `test_m005_writes_schema_migrations_row` — after apply, row with
  `id = 'm005_posted_at'` exists in `schema_migrations`

#### 7d. Bonus regression in existing `test_score.py`

`test_score_breakdown_includes_freshness` — call `score_breakdown(...)`
on a stock role and assert `"freshness"` is a key in the returned dict
AND that the composite score still falls in [0, 100].

## Verification

```bash
cd /Users/tealizard/Documents/lab/coin
.venv/bin/python scripts/migrations/m005_posted_at.py
.venv/bin/pytest tests/ -q --tb=short
# Expect: 228 + ~11 new = 239+ passing, 0 regressions
```

Manual smoke:

```bash
.venv/bin/python scripts/discover.py \
  --location "Utah, United States" --utah-remote --max-age-days 14
# Expect: ≤14d roles only; "--max-age-days 14: dropped X of Y" line printed

.venv/bin/python scripts/dashboard.py
# Expect: "Age" column populated for newly scraped roles ("3d", "1w");
# "?" for roles scraped before the migration
```

- [ ] m005 applied cleanly, idempotent on second run
- [ ] All new tests pass
- [ ] No regressions in the 228-test baseline
- [ ] `--max-age-days 14` actually filters; reports dropped count
- [ ] Dashboard "Age" column renders between Lane and Company
- [ ] `FIT_SCORE_WEIGHTS` in config.py sums to exactly 1.0 (assert this
  in a test if not already covered)

## Definition of Done

- [ ] `scripts/migrations/m005_posted_at.py` exists with `--rollback`
- [ ] `careerops/scraper.py::_parse_linkedin_cards` extracts
  `posted_at`
- [ ] `careerops/pipeline.py::upsert_role` persists with
  COALESCE-preserve semantics
- [ ] `careerops/score.py::score_freshness` exists and is wired into
  `score_breakdown`
- [ ] `config.py::FIT_SCORE_WEIGHTS` includes `freshness: 0.04`,
  rebalanced, sums to 1.0
- [ ] `scripts/discover.py --max-age-days N` filters by age
- [ ] `scripts/dashboard.py` (and pipeline Rich table) shows Age column
- [ ] All tests in 7a–7d pass
- [ ] `docs/state/project-state.md` updated with note about the new
  freshness signal and the role #11 Filevine motivating example
- [ ] No regressions

## Rollback

```bash
cd /Users/tealizard/Documents/lab/coin
.venv/bin/python scripts/migrations/m005_posted_at.py --rollback
git checkout careerops/scraper.py careerops/pipeline.py careerops/score.py \
             config.py scripts/discover.py scripts/dashboard.py
rm tests/test_score_freshness.py tests/test_migrations_m005.py
# Revert test_scraper.py and test_score.py additions
git checkout tests/test_scraper.py tests/test_score.py
```

The migration's `--rollback` path drops the `posted_at` column (or
rebuilds the table on SQLite <3.35) and removes the
`schema_migrations` row — leaving the DB exactly as it was before
m005.
