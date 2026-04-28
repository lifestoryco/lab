---
task: COIN-MULTI-BOARD
title: Greenhouse / Lever / Ashby board scrapers — break LinkedIn comp blackout
phase: Discovery — Data Quality
size: L
depends_on: COIN-AUTOPIPELINE
created: 2026-04-27
---

# COIN-MULTI-BOARD: Greenhouse / Lever / Ashby Board Scrapers

## Context

Today's discovery run returned 40 roles, ALL from LinkedIn, ALL with
`comp_source='unverified'`. LinkedIn's guest job-cards API does not expose
salary on its public endpoint — even where the underlying employer disclosed a
range to comply with CO/WA/NY pay-transparency laws, LinkedIn strips it from
the guest payload.

That means Coin's comp floor (rule #3 in CLAUDE.md: $160K base / $200K total)
is being enforced against `imputed_levels` data only. Half the funnel is
flying blind. Every Utah role currently in the DB lacks a verified band.

The fix is to stop relying on LinkedIn as the only source. Greenhouse, Lever,
and Ashby all expose **public, unauthenticated** job-board APIs that DO carry
the comp ranges — especially Ashby, which has a first-class
`?includeCompensation=true` flag because Ashby ships pay-transparency
compliance as a product feature.

Most Utah-relevant in-league companies post on at least one of these:

| Board | Examples (verify slugs before adding) |
|---|---|
| Greenhouse | Filevine, Recursion, HashiCorp, dbt Labs, MasterControl |
| Lever | Lucid Software (some orgs), Datadog, Cloudflare |
| Ashby | Vercel, Linear, Notion-tier startups, RevenueCat |

Porting the API-detection switch and per-board parser pattern from
`santifer/career-ops`'s `scan.mjs` (MIT licensed — must cite in module
docstrings) gets us from 1 source × 0 verified comp → 4 sources × ~50%
verified comp in one task.

## Goal

Add a `coin/careerops/boards/` package with three board scrapers
(`GreenhouseBoard`, `LeverBoard`, `AshbyBoard`) plus a `TARGET_COMPANIES`
seed registry, wire them into `careerops/scraper.py` as a parallel discovery
source alongside LinkedIn, and surface them via new `--boards` and
`--companies` flags on `scripts/discover.py`.

Success looks like: a single `discover.py --boards greenhouse,lever,ashby
--location "Utah, United States"` run produces ≥10 non-LinkedIn roles, of
which ≥5 carry `comp_source IN ('explicit','parsed')` rather than
`unverified`.

## Pre-conditions

- [ ] `careerops.compensation.parse_comp_string` exists and handles
      "$120K-$180K", "$120,000 - $180,000", "120000-180000" formats
- [ ] `careerops.pipeline.upsert_role` exists and accepts the standard role
      dict (url, title, company, location, remote, comp_min, comp_max,
      comp_source, comp_currency, source, posted_at, jd_raw, lane)
- [ ] `httpx[http2]` and `bs4` already in `requirements.txt`
- [ ] `respx` may need to be added (test dependency only). If not installed,
      use the existing `monkeypatch`-on-`_get` pattern that
      `tests/test_scraper.py` already uses
- [ ] `careerops.score.score_title(title, lane) -> int` exists and returns
      0–100

## Steps

### Step 1 — Create the `boards/` package skeleton

Create `coin/careerops/boards/` with four files:

```
careerops/boards/
  __init__.py        # exports ALL_BOARDS = [GreenhouseBoard, LeverBoard, AshbyBoard]
  base.py            # BoardScraper ABC + shared helpers
  greenhouse.py      # GreenhouseBoard
  lever.py           # LeverBoard
  ashby.py           # AshbyBoard
```

Every module's top docstring must include:

```python
"""
<board name> public job-board scraper.

Pattern adapted from santifer/career-ops scan.mjs (MIT).
"""
```

### Step 2 — Author `boards/base.py`

```python
from abc import ABC, abstractmethod
from typing import Optional
import httpx
import time

from careerops.compensation import parse_comp_string

class BoardScraper(ABC):
    """Base class for public job-board API scrapers."""

    name: str = ""  # subclass overrides; must be one of: greenhouse, lever, ashby
    REQUEST_DELAY_SECONDS = 1.5

    def __init__(self, client: Optional[httpx.Client] = None):
        self._client = client or httpx.Client(http2=True, timeout=15.0,
                                              headers={"User-Agent": "coin-careerops/0.1"})
        self._last_request_at = 0.0

    @abstractmethod
    def fetch_listings(self, slug: str, lane: str) -> list[dict]:
        """Return a list of role dicts (see _to_role_dict for shape)."""

    @abstractmethod
    def fetch_detail(self, url: str) -> dict | None:
        """Return enriched detail dict for one role URL, or None on failure."""

    def _get(self, url: str, params: dict | None = None) -> httpx.Response | None:
        """GET with rate limit. Returns None on 404 or network error (logged)."""
        # honor REQUEST_DELAY_SECONDS since last call
        # try/except network errors; log + return None
        # return response only on 2xx

    def _parse_comp(self, text: str | None) -> tuple[int | None, int | None]:
        """Delegates to careerops.compensation.parse_comp_string."""
        if not text:
            return (None, None)
        return parse_comp_string(text)

    def _normalize_location(self, loc) -> str:
        """Accept dict, str, or list; return display string."""
        # Greenhouse: {"name": "Lehi, UT"}
        # Lever: {"location": "Remote — US", "additionalLocations": [...]}
        # Ashby: "Salt Lake City, UT" | "Remote (United States)"

    def _to_role_dict(self, *, url: str, title: str, company: str,
                      location: str, remote: bool, comp_min: int | None,
                      comp_max: int | None, comp_source: str,
                      comp_currency: str = "USD", posted_at: str | None,
                      jd_raw: str | None) -> dict:
        return {
            "url": url, "title": title, "company": company,
            "location": location, "remote": remote,
            "comp_min": comp_min, "comp_max": comp_max,
            "comp_source": comp_source, "comp_currency": comp_currency,
            "source": self.name, "posted_at": posted_at,
            "jd_raw": jd_raw, "lane": None,  # set by orchestrator
        }
```

`comp_source` values produced here are `"explicit"` (board returned a
structured comp field) or `"parsed"` (regex-extracted from JD prose).
Never produce `"unverified"` from a board scraper — that label is reserved
for LinkedIn-style sources with no comp signal.

### Step 3 — Author `boards/greenhouse.py`

**API endpoint:**
`https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true`

**Response shape (sample, redacted):**
```json
{
  "jobs": [
    {
      "id": 4567890,
      "title": "Senior Solutions Engineer",
      "absolute_url": "https://boards.greenhouse.io/filevine/jobs/4567890",
      "location": {"name": "Lehi, UT"},
      "updated_at": "2026-04-22T18:14:09-04:00",
      "content": "<p>Filevine is...</p><p>Compensation: $135,000 - $175,000 + equity</p>",
      "metadata": [
        {"name": "Salary range", "value": "$135,000 - $175,000"},
        {"name": "Department", "value": "Sales Engineering"}
      ]
    }
  ]
}
```

**Comp extraction priority:**
1. Iterate `metadata` for entries where `name` matches `/salary|comp|pay/i`.
   If `value` parses via `parse_comp_string` to a `(min,max)` tuple, use it
   with `comp_source='explicit'`.
2. Fallback: regex-search `content` (after HTML-stripping) for the same
   patterns. If found, `comp_source='parsed'`.
3. If neither, return the role with `(None, None)` and `comp_source='parsed'`
   (so the row still flows; comp imputation happens later via Levels.fyi).

**Remote heuristic:** `True` if `location.name` matches
`/remote|anywhere|distributed/i`.

**`fetch_detail`:** for Greenhouse, the listings endpoint with
`content=true` already returns full HTML; `fetch_detail` is a no-op that
returns the cached dict. Implement it for ABC compliance.

### Step 4 — Author `boards/lever.py`

**API endpoint:**
`https://api.lever.co/v0/postings/{slug}?mode=json`

**Response shape (sample):**
```json
[
  {
    "id": "abc-123",
    "text": "Staff Solutions Architect",
    "hostedUrl": "https://jobs.lever.co/lucidsoftware/abc-123",
    "categories": {
      "location": "South Jordan, UT",
      "team": "Solutions",
      "commitment": "Full-time"
    },
    "descriptionPlain": "About the role...\nBase salary range: $140,000-$190,000",
    "additional": "...",
    "salaryRange": {"min": 140000, "max": 190000, "currency": "USD"}
  }
]
```

**Comp extraction priority:**
1. If top-level `salaryRange` present with `min` and `max`, use directly with
   `comp_source='explicit'`.
2. Fallback: regex on `descriptionPlain` + `additional`. If found,
   `comp_source='parsed'`.

**Remote heuristic:** `True` if `categories.location` or
`categories.workplaceType` matches remote patterns.

### Step 5 — Author `boards/ashby.py`

**API endpoint:**
`https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true`

**Response shape (sample):**
```json
{
  "jobs": [
    {
      "id": "abc-789",
      "title": "Engineering Program Manager",
      "jobUrl": "https://jobs.ashbyhq.com/vercel/abc-789",
      "location": "Remote (United States)",
      "publishedAt": "2026-04-19T12:00:00Z",
      "descriptionPlain": "Vercel is hiring...",
      "compensation": {
        "compensationTierSummary": "$170K - $220K",
        "compensationTier": {
          "minValue": 170000,
          "maxValue": 220000,
          "currencyCode": "USD"
        }
      }
    }
  ]
}
```

**Comp extraction priority (this is the highest-value source — get it right):**
1. If `compensation.compensationTier.minValue` and `maxValue` both present,
   use directly with `comp_source='explicit'`.
2. If only `compensationTierSummary` present, parse via
   `parse_comp_string`; on success, `comp_source='explicit'`.
3. Fallback: regex on `descriptionPlain`; `comp_source='parsed'`.

**Remote heuristic:** `True` if `location` matches
`/remote|anywhere|distributed/i`.

### Step 6 — Author `boards/__init__.py`

```python
from careerops.boards.greenhouse import GreenhouseBoard
from careerops.boards.lever import LeverBoard
from careerops.boards.ashby import AshbyBoard

ALL_BOARDS = [GreenhouseBoard, LeverBoard, AshbyBoard]

__all__ = ["GreenhouseBoard", "LeverBoard", "AshbyBoard", "ALL_BOARDS"]
```

### Step 7 — Add `TARGET_COMPANIES` seed in `coin/config.py`

Append (do not overwrite the file):

```python
# Public job-board slugs per company.
# Verify each slug by curl-ing the API endpoint before adding.
# Wrong slugs = 404s logged but no crash.
# Some companies post on multiple boards (e.g. Lucid uses both Greenhouse
# and Lever for different orgs); that's fine — dedup handles it.
TARGET_COMPANIES: dict[str, dict[str, str | None]] = {
    # Utah core
    "Filevine":       {"greenhouse": "filevine",        "lever": None,           "ashby": None},
    "Awardco":        {"greenhouse": None,              "lever": None,           "ashby": None},  # TODO verify
    "Weave":          {"greenhouse": None,              "lever": None,           "ashby": None},  # TODO verify
    "MasterControl":  {"greenhouse": None,              "lever": None,           "ashby": None},  # TODO verify
    "Pluralsight":    {"greenhouse": None,              "lever": None,           "ashby": None},  # TODO verify
    "Lucid Software": {"greenhouse": None,              "lever": "lucidsoftware","ashby": None},  # TODO verify
    "Podium":         {"greenhouse": None,              "lever": None,           "ashby": None},  # TODO verify
    "Recursion":      {"greenhouse": "recursion",       "lever": None,           "ashby": None},
    "Domo":           {"greenhouse": None,              "lever": None,           "ashby": None},  # TODO verify
    "Vivint":         {"greenhouse": None,              "lever": None,           "ashby": None},  # TODO verify
    "Qualtrics":      {"greenhouse": None,              "lever": None,           "ashby": None},  # TODO verify
    "Workfront":      {"greenhouse": None,              "lever": None,           "ashby": None},  # TODO verify
    "Spiff":          {"greenhouse": None,              "lever": None,           "ashby": None},  # TODO verify
    # In-league outside Utah (remote-friendly)
    "RevenueCat":     {"greenhouse": None,              "lever": None,           "ashby": None},  # TODO verify
    "Linear":         {"greenhouse": None,              "lever": None,           "ashby": None},  # TODO verify
    "Notion":         {"greenhouse": None,              "lever": None,           "ashby": None},  # TODO verify
    "Vercel":         {"greenhouse": None,              "lever": None,           "ashby": "vercel"},
    "Datadog":        {"greenhouse": None,              "lever": "datadog",      "ashby": None},
    "HashiCorp":      {"greenhouse": "hashicorp",       "lever": None,           "ashby": None},
    "Block":          {"greenhouse": None,              "lever": None,           "ashby": None},  # TODO verify
    "Snowflake":      {"greenhouse": None,              "lever": None,           "ashby": None},  # TODO verify
    "Cloudflare":     {"greenhouse": None,              "lever": "cloudflare",   "ashby": None},
    "MongoDB":        {"greenhouse": None,              "lever": None,           "ashby": None},  # TODO verify
    "Confluent":      {"greenhouse": None,              "lever": None,           "ashby": None},  # TODO verify
    "Hightouch":      {"greenhouse": None,              "lever": None,           "ashby": None},  # TODO verify
    "Census":         {"greenhouse": None,              "lever": None,           "ashby": None},  # TODO verify
    "Retool":         {"greenhouse": None,              "lever": None,           "ashby": None},  # TODO verify
    "Airbyte":        {"greenhouse": None,              "lever": None,           "ashby": None},  # TODO verify
    "Fivetran":       {"greenhouse": None,              "lever": None,           "ashby": None},  # TODO verify
    "dbt Labs":       {"greenhouse": "dbtlabs",         "lever": None,           "ashby": None},
    # NOTE: Adobe, Stripe, Google, Meta, Apple intentionally omitted —
    # FAANG-tier per the cox-style-tpm → out_of_band pedigree filter.
}
```

**MANDATORY:** before merging, the executor must verify each slug they
plan to mark non-`None` by hitting the actual API:

```bash
curl -s "https://boards-api.greenhouse.io/v1/boards/<slug>/jobs?content=true" | head -c 500
curl -s "https://api.lever.co/v0/postings/<slug>?mode=json" | head -c 500
curl -s "https://api.ashbyhq.com/posting-api/job-board/<slug>?includeCompensation=true" | head -c 500
```

A 404 or HTML error page = wrong slug. Leave the entry as `None` rather than
guessing. Better to ship 8 verified slugs than 30 guessed ones.

### Step 8 — Wire `careerops/scraper.py` orchestrator

Add to `careerops/scraper.py`:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from careerops.boards import ALL_BOARDS
from careerops.score import score_title
from coin.config import TARGET_COMPANIES  # adjust import path to actual layout

LANE_SCORE_FLOOR = 55  # only keep board roles whose title scores >= this for the lane

def search_boards(self, lane: str, location: str | None = None,
                  boards: list[str] | None = None,
                  companies: list[str] | None = None) -> list[dict]:
    """Iterate TARGET_COMPANIES, fetch from each enabled board, filter by lane."""
    enabled = set(boards or ["greenhouse", "lever", "ashby"])
    target_companies = (
        {k: v for k, v in TARGET_COMPANIES.items() if k in companies}
        if companies else TARGET_COMPANIES
    )
    results: list[dict] = []
    board_instances = {cls.name: cls() for cls in ALL_BOARDS if cls.name in enabled}

    tasks = []
    for company, slugs in target_companies.items():
        for board_name, slug in slugs.items():
            if slug and board_name in board_instances:
                tasks.append((company, board_instances[board_name], slug))

    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {
            ex.submit(board.fetch_listings, slug, lane): (company, board.name)
            for company, board, slug in tasks
        }
        for fut in as_completed(futures):
            company, board_name = futures[fut]
            try:
                roles = fut.result() or []
            except Exception as e:
                # log and continue — never let one board take down the run
                print(f"[boards] {company}/{board_name} failed: {e}")
                continue
            for r in roles:
                r["company"] = company  # canonical company name from registry
                r["lane"] = lane
                if score_title(r["title"], lane) >= LANE_SCORE_FLOOR:
                    if location is None or self._matches_location(r["location"], location):
                        results.append(r)
    return results
```

Update `search_all_lanes` to combine LinkedIn + boards results, deduped by
canonical URL form (strip query params and trailing slashes).

**Politeness:** `REQUEST_DELAY_SECONDS = 1.5` enforced inside `BoardScraper._get`
already throttles per-instance. ThreadPool max 4 keeps total concurrent
in-flight reasonable.

### Step 9 — Update `scripts/discover.py`

Add two new flags (preserve all existing ones):

```python
parser.add_argument(
    "--boards",
    type=str,
    default="linkedin,greenhouse,lever,ashby",
    help="CSV of sources to query. Default: all four."
)
parser.add_argument(
    "--companies",
    type=str,
    default=None,
    help="CSV of company names from TARGET_COMPANIES to limit board scrapes to. "
         "Ignored for LinkedIn."
)
```

Parse, pass to scraper. If `linkedin` is omitted, skip the LinkedIn pass.

### Step 10 — Extend `careerops/pipeline.py` `comp_source` enum

Locate the schema definition and `upsert_role`. The `comp_source` column
must accept these four string values:

| value | meaning |
|---|---|
| `explicit` | Board returned a structured comp field (Ashby tier, Lever salaryRange, Greenhouse metadata) |
| `parsed` | Regex-extracted from JD prose |
| `imputed_levels` | (Future) Levels.fyi cross-reference fallback |
| `unverified` | LinkedIn / Indeed with no comp signal |

If a CHECK constraint or enum exists in the schema, update it. Add a
migration shim (idempotent) that ALTERs the constraint or no-ops if already
correct. `upsert_role` must accept the new keys (`source`, `posted_at`,
`jd_raw`, `comp_currency`) without crashing if the table already has them.

### Step 11 — Tests

Add five test files under `coin/tests/`. Match the existing test style
(pytest, no class wrappers, `monkeypatch`-on-`_get` if `respx` not present).

Create fixture files first:
```
coin/tests/fixtures/boards/
  greenhouse_filevine.json    # ~3 jobs, real shape, redacted
  lever_lucidsoftware.json    # ~3 postings
  ashby_vercel.json           # ~3 jobs, varied compensation shapes
```

Pull real shapes via `curl` against the live API once and trim. Do not
fabricate fields that the real API doesn't emit.

**`tests/test_boards_greenhouse.py`** — 8 tests:
1. `test_parses_basic_listing` — title, url, location all extracted
2. `test_comp_from_metadata_explicit` — metadata "Salary range" → `explicit`
3. `test_comp_from_content_html_parsed` — no metadata, regex hits content → `parsed`
4. `test_comp_missing_returns_none` — neither source → `(None, None, 'parsed')`
5. `test_location_remote_flagged` — "Remote" → `remote=True`
6. `test_posted_at_iso_extracted` — `updated_at` → ISO string
7. `test_404_returns_empty_list` — bad slug → `[]`, no crash
8. `test_empty_jobs_array` — `{"jobs": []}` → `[]`

**`tests/test_boards_lever.py`** — 8 tests, parallel structure:
1. `test_parses_basic_posting`
2. `test_comp_from_salaryRange_explicit`
3. `test_comp_from_descriptionPlain_parsed`
4. `test_comp_missing`
5. `test_location_remote_flagged`
6. `test_hostedUrl_used_as_canonical`
7. `test_404_returns_empty_list`
8. `test_empty_array`

**`tests/test_boards_ashby.py`** — 8 tests, parallel structure with extra
focus on the comp tier (this source carries the most signal):
1. `test_parses_basic_job`
2. `test_comp_from_compensationTier_explicit` — minValue/maxValue
3. `test_comp_from_compensationTierSummary_explicit` — string parsed
4. `test_comp_from_descriptionPlain_parsed` — fallback
5. `test_comp_missing`
6. `test_location_remote_flagged`
7. `test_includeCompensation_param_sent` — assert URL includes the flag
8. `test_404_returns_empty_list`

**`tests/test_boards_orchestrator.py`** — 4 tests:
1. `test_search_boards_filters_by_lane_score` — title scoring < 55 dropped
2. `test_search_boards_dedupes_against_linkedin` — same canonical URL appears once
3. `test_board_failure_does_not_kill_run` — one board raises → others still return
4. `test_companies_flag_limits_scope` — `--companies "Vercel,Filevine"` only hits those two

### Step 12 — Manual live-API smoke (Acceptance only — not in pytest)

Document in the task report:

```bash
# Smoke #1: Ashby returns real Vercel jobs with comp
.venv/bin/python -c "
from careerops.boards.ashby import AshbyBoard
b = AshbyBoard()
for r in b.fetch_listings('vercel', 'mid-market-tpm')[:3]:
    print(r['title'], '|', r['comp_min'], '-', r['comp_max'], '|', r['comp_source'])
"

# Smoke #2: Greenhouse returns Filevine jobs
.venv/bin/python -c "
from careerops.boards.greenhouse import GreenhouseBoard
b = GreenhouseBoard()
for r in b.fetch_listings('filevine', 'enterprise-sales-engineer')[:3]:
    print(r['title'], '|', r['comp_min'], '-', r['comp_max'], '|', r['comp_source'])
"

# Smoke #3: Full orchestrator run with comp verified
.venv/bin/python scripts/discover.py \
    --boards greenhouse,lever,ashby \
    --location "Utah, United States"
```

Capture the output in the PR / handoff notes.

## Verification

```bash
cd /Users/tealizard/Documents/lab/coin
.venv/bin/python -m pytest tests/ -q --tb=short

# Expect: 228 + ~28 new = 256+ tests passing, 0 regressions

.venv/bin/python -c "from careerops.boards import GreenhouseBoard, LeverBoard, AshbyBoard, ALL_BOARDS; print(len(ALL_BOARDS), 'boards loaded')"
.venv/bin/python -c "from coin.config import TARGET_COMPANIES; print(len(TARGET_COMPANIES), 'companies in registry')"

# Live smoke (network required):
.venv/bin/python scripts/discover.py --boards greenhouse,lever,ashby --location "Utah, United States"
```

- [ ] `careerops/boards/{base,greenhouse,lever,ashby,__init__}.py` all exist
- [ ] Each board module cites santifer/career-ops scan.mjs (MIT) in its docstring
- [ ] `TARGET_COMPANIES` registry exists in `coin/config.py` with verified slugs
- [ ] Every non-`None` slug in `TARGET_COMPANIES` was curl-verified before merge
- [ ] `scripts/discover.py` accepts `--boards` and `--companies`
- [ ] `comp_source` accepts `explicit | parsed | imputed_levels | unverified`
- [ ] All 28 new tests pass; existing 228 still pass; 0 regressions
- [ ] Live discover run returns ≥10 non-LinkedIn roles, ≥5 with verified comp
- [ ] Combined LinkedIn + boards run produces ≥50 unique roles
- [ ] A role on both LinkedIn and Greenhouse appears once after dedup

## Definition of Done

- [ ] `careerops/boards/` package landed with all four modules
- [ ] `TARGET_COMPANIES` registry seeded with verified slugs only
- [ ] `careerops/scraper.py` orchestrates LinkedIn + 3 boards in parallel
- [ ] `scripts/discover.py` flags wired and documented in `--help`
- [ ] `careerops/pipeline.py` schema accepts the four `comp_source` values
- [ ] 28 new tests pass; full suite green
- [ ] Manual smoke output captured in handoff notes
- [ ] `docs/state/project-state.md` updated to reflect new discovery sources
- [ ] Commit message uses the canonical Coin format (`feat(coin): ...`)

## Style notes

- **Cite the source** in every board module docstring:
  `# Pattern adapted from santifer/career-ops scan.mjs (MIT)`
- **Slug verification is mandatory** — wrong slugs return HTML 404 pages
  that look like JSON to a careless parser, then silently produce zero
  rows. Verify before adding.
- **Multiple boards per company is fine** — Lucid Software has both
  Greenhouse and Lever orgs. Dedup by canonical URL handles overlap.
- **Never produce `comp_source='unverified'` from a board** — that label
  is reserved for LinkedIn-style sources. Boards always know whether they
  found structured comp (`explicit`), regex-parsed it from prose
  (`parsed`), or genuinely have nothing (still `parsed` with `(None, None)`).
- **Politeness:** keep `REQUEST_DELAY_SECONDS = 1.5` per board instance
  and `max_workers=4` in the orchestrator. These boards are public but
  operated by real companies — don't get Coin's IP banned.

## Rollback

```bash
rm -rf careerops/boards/
rm tests/test_boards_greenhouse.py tests/test_boards_lever.py \
      tests/test_boards_ashby.py tests/test_boards_orchestrator.py
rm -rf tests/fixtures/boards/
git checkout careerops/scraper.py careerops/pipeline.py \
             scripts/discover.py coin/config.py \
             docs/state/project-state.md
```

LinkedIn-only discovery (the pre-task baseline) remains functional.
