---
task: H-1.10
title: Multi-source price intelligence platform — unified SourceAdapter architecture + 9 concrete adapters
phase: Phase 1 — Core hardening & signal quality
size: XL (realistically 2–3 sessions; this prompt is structured for partial completion to be valuable at every checkpoint)
depends_on: H-1.6 (CORS), H-1.7 (shared HTTP session) — nice-to-have, not blockers
created: 2026-04-22
---

# H-1.10: Multi-Source Price Intelligence Platform

## Meta: How to read this prompt

This is a single orchestrated task covering **nine** data sources. It is explicitly
structured so that **any checkpoint is a shippable end state**. The work proceeds
in strict phases:

1. **Foundation** (required) — the SourceAdapter contract, NormalizedSale schema,
   registry, reconciliation engine, observability hooks. Without this, the
   per-source work has no home.
2. **Free adapters** (required, parallel-safe) — PSA Pop Report, BGS Pop Report,
   130point, Cardmarket, Goldin/PWCC, Limitless TCG. No credentials needed.
3. **Credential-gated adapters** (HUMAN GATE) — eBay Browse API, TCGPlayer Pro,
   Card Ladder. Each pauses until the operator has completed the OAuth/partner
   flow. Code ships disabled behind a feature flag; adapter smoke-tests ship.

**If you run out of turn budget:** commit the foundation + all finished adapters,
update project-state, and queue the remainder as individual follow-up prompts
(H-1.10a, H-1.10b, …). Partial completion is acceptable because every adapter is
independently useful once merged — the reconciliation engine weights by adapter
quality and ignores any that are disabled.

---

## Context

Today, holo's `pokequant/scraper.py::fetch_sales()` is a linear if/elif cascade
of four sources (PriceCharting → eBay HTML → TCGPlayer redirect → pokemontcg.io
synth). Each is fragile, each integration is ad hoc, there is no normalized
record schema, no reconciliation between sources, and no per-source health
metric. This design caused the April 2026 scraper break (eBay DOM change went
undetected for an unknown period) and the TCGPlayer market-estimate
contamination bug resolved in session 10 (`d6f8b80`).

Session 10's code review identified nine concrete source additions that would
meaningfully improve accuracy. Implementing nine sources in the current
architecture would multiply the fragility. **The right move is to refactor to
an adapter pattern first, then add sources against the new contract.**

This task is filed as **H-1.10**, chronologically after the hardening prompts
H-1.6–H-1.9 from session 10. It unblocks:
- **H-1.5** (backtesting harness) — needs Card Ladder historical index data
- **H-1.3** (tournament meta-shift) — needs Limitless TCG
- **Real PSA/CGC grading-ROI** — `_handle_grade_roi` currently hardcodes
  probabilities; PSA Pop Report replaces them with real liquidity data

## Goal

Ship a `pokequant/sources/` package with:

1. An abstract `SourceAdapter` ABC + a `NormalizedSale` dataclass
2. A `SourceRegistry` that discovers adapters by convention and routes fetches
3. A `SourceReconciler` that merges records across adapters with explicit
   outlier-vote logic
4. Concrete adapters for each source (subset acceptable — see Meta)
5. Migration of `fetch_sales()` to go through the registry
6. Migration of `_handle_grade_roi` to use PSA/BGS pop data
7. Per-source metrics emitted to stderr in a grep-able JSON format
8. Feature flags per adapter via env var (`HOLO_ADAPTER_<NAME>=0/1`)
9. Tests for each landed adapter + integration tests for the reconciler

**"Done"** = `fetch_sales("Charizard VMAX 20", days=30)` returns a merged,
deduped, outlier-rejected sale list drawn from ≥3 adapters, with source counts
visible in a new `/api?action=health` endpoint.

## Pre-conditions

- [ ] venv active: `source .venv/bin/activate` from repo root (this worktree
      uses the main repo's venv at `/Users/tealizard/Documents/lab/holo/.venv`)
- [ ] Working tree clean at task start; create branch
      `task/H-1-10-multi-source-adapters` from `main`
- [ ] Tests passing baseline: `.venv/bin/pytest tests/ -q` → 57 passing before
      any changes. Any regression from this baseline is a P0 stop.
- [ ] Read the four pending hardening prompts in
      `docs/tasks/prompts/pending/H-1-{6,7,8,9}*.md` — if any has landed, its
      output (shared HTTP session in particular) changes the import path in
      Step 2.

---

## Architectural Specification

### The `NormalizedSale` schema (the invariant)

Every adapter MUST emit records conforming to this dataclass:

```python
# pokequant/sources/schema.py
from dataclasses import dataclass, field
from datetime import date
from typing import Literal, Optional

SourceType = Literal["sale", "market_estimate", "pop_report", "meta_signal"]
Currency = Literal["USD", "EUR", "GBP", "JPY"]
Grade = Literal["raw", "psa10", "psa9", "psa8", "bgs10", "bgs9.5", "cgc10", "cgc9"]

@dataclass(frozen=True)
class NormalizedSale:
    # Identity
    sale_id: str              # stable hash; same input → same id across runs
    adapter: str              # "pricecharting", "ebay_api", "130point", ...
    source_type: SourceType   # see rules below

    # Transaction
    price: float              # in `currency`; adapters MUST NOT convert
    currency: Currency
    date: date                # UTC calendar date of the sale
    condition: str            # "NM" | "LP" | "MP" | "HP" | "DMG" | "mixed"
    grade: Grade

    # Attribution
    source_url: str           # link the user can click
    quantity: int = 1
    lot_size: int = 1         # > 1 means this was a multi-card lot

    # Provenance
    confidence: float = 1.0   # adapter-reported confidence in [0, 1]
    outlier_flag: bool = False  # adapter already flagged this as suspect
    fetched_at: Optional[float] = None  # unix timestamp; set by registry

    # Escape hatch for adapter-specific metadata
    extra: dict = field(default_factory=dict)
```

**Invariants checked by the registry on ingress:**

- `price > 0` and `price < 1_000_000` (hard bounds sanity)
- `source_type == "sale"` requires `condition` to be a specific grade, not "mixed"
- `source_type == "market_estimate"` is the ONLY value that may have
  `condition == "mixed"`
- `lot_size > 1` implies `source_type == "sale"` and forces `outlier_flag = True`
  (lot sales are always suspect for single-card comps)
- `currency != "USD"` implies the reconciler must FX-normalize before median

Violations raise `InvalidSaleRecord` and the record is dropped with a WARN log
carrying the adapter name. **The registry is the contract enforcement point —
adapters must not self-police, they must trust the registry to reject bad
records.** This keeps adapter code focused on extraction.

### The `SourceAdapter` contract

```python
# pokequant/sources/base.py
from abc import ABC, abstractmethod
from typing import Sequence

class SourceAdapter(ABC):
    """One adapter per data source. Stateless; all caching lives in the registry."""

    name: str                  # class attribute — stable identifier
    enabled_by_default: bool   # False for credential-gated adapters
    priority: int              # tie-break when two records match; higher wins
    currency: Currency         # native currency of the source

    @abstractmethod
    def supports_grade(self, grade: Grade) -> bool: ...

    @abstractmethod
    def fetch(self, card_name: str, *, days: int, grade: Grade) -> Sequence[NormalizedSale]: ...

    @abstractmethod
    def health_check(self) -> dict: ...
    # Returns {"ok": bool, "latency_ms": float, "error": str | None}
    # Called by /api?action=health. Must not raise.

    def is_configured(self) -> bool:
        """Env-var feature flag + credential presence. Default: check HOLO_ADAPTER_<NAME>."""
        import os
        if os.environ.get(f"HOLO_ADAPTER_{self.name.upper()}", "1") == "0":
            return False
        return True
```

### The `SourceRegistry`

```python
# pokequant/sources/registry.py
class SourceRegistry:
    def __init__(self) -> None:
        self._adapters: list[SourceAdapter] = []

    def register(self, adapter: SourceAdapter) -> None: ...

    def discover(self) -> None:
        """Auto-import every pokequant.sources.adapters.* module."""
        import importlib, pkgutil
        from pokequant.sources import adapters
        for _, modname, _ in pkgutil.iter_modules(adapters.__path__):
            importlib.import_module(f"pokequant.sources.adapters.{modname}")
        # Each module calls registry.register(X()) at import time.

    def active_adapters(self, grade: Grade) -> list[SourceAdapter]:
        return [a for a in self._adapters if a.is_configured() and a.supports_grade(grade)]

    def fetch_all(self, card_name: str, *, days: int, grade: Grade) -> list[NormalizedSale]:
        """Parallel fan-out across active adapters. Enforces NormalizedSale invariants.
        Emits per-adapter metrics to stderr as JSON."""
        # ThreadPoolExecutor(max_workers=len(active))
        # Per-adapter timeout wrapped in concurrent.futures.wait(timeout=12)
        # Metrics: {"adapter": name, "count": n, "latency_ms": ms, "error": str | None}
        ...
```

### The `SourceReconciler`

The reconciler is the **only place** where records from multiple adapters get
merged. Its algorithm:

```
1. Partition records by (calendar_date, grade). Records outside
   [today - days, today] are dropped.
2. Within each partition:
   a. FX-normalize non-USD to USD using static rate constants in config.py
      (EXCHANGE_RATES_USD = {"EUR": 1.08, "GBP": 1.27, "JPY": 0.0066}).
      Log a WARN if we see a currency not in the table.
   b. Dedupe on (round(price_usd, 2), adapter_priority_rank). Keep the
      highest-priority adapter's record when duplicates collide.
   c. Compute partition_median over sale-type records only (exclude
      market_estimate). If partition has ≥5 sale records, apply a 3-sigma
      IQR fence; mark outliers with outlier_flag=True but do NOT drop
      (the UI needs them for transparency).
   d. Market-estimate records pass through but never enter median
      computation (session-10 rule preserved).
3. Emit a reconciliation audit trail in the returned payload:
   {"reconciled_count": N, "by_adapter": {name: count}, "dropped_outliers": M,
    "fx_normalized": K, "warnings": [...]}
```

**Why this design:** the reconciler is pure — takes a flat list in, emits a
flat list + audit out. That means we can test it with synthetic records and
never touch the network.

### Adapter priority rubric (tie-break order, highest to lowest)

```python
# pokequant/sources/priority.py
ADAPTER_PRIORITY = {
    # Completed-sale records, authoritative
    "ebay_api": 100,          # official, stable, grade-filterable
    "pricecharting": 90,      # good coverage, fragile DOM
    "130point": 85,           # sale-comp aggregator with built-in outlier flags
    "ebay_html": 80,          # fallback when API quota exhausted
    "goldin": 75,             # auction comps, high-value only
    "cardmarket": 70,         # EU market, FX-normalized
    # Market estimates (never enter sale median)
    "tcgplayer_pro": 60,      # official market price, authenticated
    "tcgplayer_redirect": 50, # current scraping hack
    "pricecharting_static": 40,
    "pokemontcg_synth": 30,
    # Meta signals (not priced sales)
    "card_ladder": 20,        # index data for backtesting only
    "limitless": 10,          # tournament decklists, no price
    "psa_pop": 5,             # pop report, read by grade-ROI handler
    "bgs_pop": 5,             # same
}
```

---

## Steps

### Step 1 — Foundation scaffold

Create the package skeleton:

```
pokequant/sources/
├── __init__.py               # exposes registry singleton
├── schema.py                 # NormalizedSale + types
├── base.py                   # SourceAdapter ABC
├── registry.py               # SourceRegistry
├── reconciler.py             # SourceReconciler (pure)
├── priority.py               # priority table
├── exceptions.py             # InvalidSaleRecord, AdapterNotConfigured, etc.
├── fx.py                     # FX normalization helpers
└── adapters/
    └── __init__.py           # empty; package marker
```

Patterns to match from existing code:
- Type hints: Python 3.11 `X | Y` union syntax (see `pokequant/signals/dip_detector.py`)
- Logging: `logger = logging.getLogger(__name__)` at module top
- Thread-safety primitives: see `api/index.py::_http_session()` for the
  `threading.Lock + None + double-check` pattern
- Tests go in `tests/test_sources_*.py`, one file per major module

Write a companion `tests/test_sources_schema.py` covering every invariant with
negative tests (invalid price, wrong grade/source_type combo, etc.).

Write `tests/test_sources_reconciler.py` with ≥10 cases covering: simple
merge, FX conversion, duplicate dedup by priority, market-estimate exclusion
from median, IQR fence, outlier flagging without dropping.

**Verification gate:** `.venv/bin/pytest tests/test_sources_*.py -q` → green
before proceeding.

### Step 2 — Registry + observability

Implement `SourceRegistry.fetch_all` with a `ThreadPoolExecutor`. Timeout is
**per-adapter 12 seconds** (PriceCharting's p95). Total budget is capped at
`min(15s, days * 0.5s)` to leave room for the Vercel 60s envelope.

Observability: the registry writes one JSON line per adapter call to stderr:

```
{"ts": 1713831123.4, "event": "adapter.fetch", "adapter": "pricecharting",
 "card": "charizard-vmax-20", "count": 23, "latency_ms": 1847, "error": null}
```

In `api/index.py`, add a new `_handle_health(params)` action that iterates the
registry, calls `health_check()` on each, and returns a JSON envelope suitable
for the Next.js proxy's status page. Wire into `_HANDLERS`. Cache-Control:
`s-maxage=30`. **Keep pandas/numpy/bs4 out of module-level imports as usual.**

### Step 3 — Migrate `fetch_sales()` to the registry

This is the dangerous step — it changes the runtime behavior of every price
call. Protocol:

1. Keep the existing `fetch_sales()` body untouched; rename it to
   `_fetch_sales_legacy()`.
2. Write a new `fetch_sales()` that calls `registry.fetch_all()`, runs the
   result through `SourceReconciler`, and returns `[r.to_dict() for r in reconciled]`.
3. Add a feature flag `HOLO_USE_REGISTRY=0/1` (default `0`) so deployment can
   roll back instantly.
4. Add a delta test `tests/test_fetch_sales_parity.py` that runs 5 canary
   cards through both paths with identical adapters enabled and asserts the
   price distributions are within 5% of each other.

**HUMAN GATE:** Before flipping `HOLO_USE_REGISTRY=1` in production, paste the
parity test output here. Non-trivial distributional deltas mean the reconciler
has a bug; do not deploy until investigated.

### Step 4 — PSA Pop Report adapter (free, high-impact)

**Source:** `https://www.psacard.com/pop/tcg-cards/pokemon/{set_name}/{number}`

**Extract:** pop10 count, pop9 count, pop_total. Emit as records of
`source_type="pop_report"` (add to `SourceType` union). These records have
`price=0` — they're metadata, not sales.

**Frequency:** PSA updates weekly. Cache 7 days.

**Wire-up:** `api/index.py::_handle_grade_roi` currently uses static
`p10=0.15, p9=0.35` heuristics. Replace with:

```python
pop = registry.get_adapter("psa_pop").fetch_pop(card_name=card)
total_graded = pop.get("total", 0)
p10 = pop["pop10"] / total_graded if total_graded > 50 else 0.15  # fallback
p9  = pop["pop9"]  / total_graded if total_graded > 50 else 0.35
```

Document the 50-sample threshold in `config.py` as `PSA_POP_MIN_SAMPLES = 50`.

**Tests:** fixture HTML file in `tests/fixtures/psa_pop_charizard.html`
exercising the parser. Do not hit the live endpoint from tests.

### Step 5 — BGS Pop Report adapter (free, low-impact)

Same pattern as PSA. **Source:** `https://www.beckett.com/grading/pop-report/`
(session-authenticated; if the endpoint requires login, stub the adapter
behind HUMAN GATE and log that BGS is deferred). Low priority — ship
disabled-by-default.

### Step 6 — 130point adapter (free, scraping)

**Source:** `https://130point.com/sales/?search={card}`

**Why high value:** 130point already rejects lot sales and damaged-card
listings. Its records arrive pre-cleaned; cross-validates PriceCharting.

**Robots:** check `/robots.txt` — last known to allow `/sales/`. If it
disallows at task execution time, **stop** and file a HUMAN GATE.

**Rate:** conservative 1 req/sec per IP (self-imposed, no documented limit).

**Parsing:** 130point renders tables server-side. Use BeautifulSoup, same
patterns as `_scrape_ebay`. Their outlier column is a boolean flag —
propagate to `NormalizedSale.outlier_flag`.

**Tests:** fixture HTML in `tests/fixtures/130point_umbreon.html`.

### Step 7 — Cardmarket adapter (free API, MED effort)

**Source:** Cardmarket public API at `https://api.cardmarket.com/ws/v2.0/output.json/`

**Auth:** OAuth 1.0 HMAC-SHA1 (not OAuth 2). Requires free "Dedicated App"
registration at cardmarket.com. **Credential-gated — HUMAN GATE.**

**Human steps for the operator:**
1. Register app at https://www.cardmarket.com/en/Magic/Account/API
2. Get `APP_TOKEN`, `APP_SECRET`, `ACCESS_TOKEN`, `ACCESS_TOKEN_SECRET`
3. Set `CARDMARKET_APP_TOKEN`, etc. in Vercel env (Production + Preview,
   Sensitive)
4. Confirm in this chat that env vars are live

Ship the adapter skeleton with `enabled_by_default=False`. Write the
signed-request helper using `requests_oauthlib.OAuth1Session` (add to
`requirements.txt`).

**Currency:** records arrive in EUR. `NormalizedSale.currency="EUR"`. The
reconciler handles FX normalization in Step 2 — adapter stays currency-native.

**Tests:** mock the OAuth session; fixture JSON response body.

### Step 8 — Goldin / PWCC adapter (auction comps, MED effort)

**Source A (Goldin):** `https://goldin.co/collection/pokemon` + completed
auctions search. Goldin exposes a JSON endpoint when you inspect their search
page network traffic — URL and schema are not documented but stable.

**Source B (PWCC):** `https://www.pwccmarketplace.com/auctions/` — HTML scrape.

**Rationale:** only used for cards with `market_value > $500`. Add a gate in
`fetch_sales()`: if the initial `pricecharting` pass returns a median above
$500, spawn a Goldin/PWCC supplement.

**Output:** `source_type="sale"`, `confidence=0.95` (auction with buyer's
premium; premium is included in reported price — disclose in `extra`).

**Tests:** fixture JSON (Goldin) + fixture HTML (PWCC).

### Step 9 — Limitless TCG adapter (tournament meta signal)

**Source:** `https://play.limitlesstcg.com/api/` — official JSON API, no auth.

**Note:** this overlaps **H-1.3** on the existing roadmap. If H-1.3 has a
prompt already, **merge this step into that prompt instead of duplicating
work**. Check `docs/tasks/prompts/pending/H-1-3*` at task start.

**Output:** `source_type="meta_signal"`, `price=0`. Record contains
`extra = {"top8_count": N, "event_count": M, "deck_archetypes": [...]}`.

**Consumption:** exposed via a new `/api?action=meta_signal&card=X` endpoint.
Wiring into `/movers` ranking is **future work** — document as a follow-up but
don't implement here.

### Step 10 — eBay Browse API (credential-gated, HIGH impact)

**Source:** `https://api.ebay.com/buy/browse/v1/item_summary/search`

**Auth:** OAuth 2.0 client credentials grant. Sandbox free; production
requires approval.

**Human steps:**
1. Register at https://developer.ebay.com/my/keys (free tier)
2. Get `EBAY_APP_ID`, `EBAY_CERT_ID`, `EBAY_DEV_ID`
3. Request production scope for `buy.browse` (approval in ~1 business day)
4. Set Vercel env vars; confirm in chat

**Query shape:**
```
GET /buy/browse/v1/item_summary/search
?q=<card_name>+pokemon
&filter=soldItemsOnly:{true},price:[1..50000],priceCurrency:USD
&limit=200
```

**Rate limit:** 5000 calls/day free tier. Add daily-budget guard in adapter:
check a `holo.ebay_api_budget` Supabase counter; skip if exhausted; fall
through to `ebay_html`.

**Migrate:** once eBay API is live, set `priority["ebay_api"]=100` and
`priority["ebay_html"]=30`. The reconciler will naturally prefer the API
source while keeping HTML as emergency fallback.

**Tests:** mock `requests`; fixture JSON from a real sandbox call saved to
`tests/fixtures/ebay_browse_response.json`. Do not commit credentials.

### Step 11 — TCGPlayer Pro API (credential-gated, HIGH stability)

**Source:** `https://api.tcgplayer.com/catalog/` (v1.39.0).

**Auth:** Partner program application — **multi-day approval**. Operator must
apply at https://docs.tcgplayer.com/docs/welcome. Until approval lands, ship
the adapter **stub only** (implements `SourceAdapter` but `health_check`
returns `{ok: False, error: "awaiting partner approval"}`).

**When approval lands:** flip `HOLO_ADAPTER_TCGPLAYER_PRO=1`, migrate all the
callers that currently hit the `prices.pokemontcg.io` redirect hack to this
adapter, and decommission `tcgplayer_redirect`.

**HUMAN GATE:** Before decommissioning the redirect hack, run the parity test
from Step 3 against 10 liquid cards. Only cut over if the Pro API returns
non-empty sets for all 10.

### Step 12 — Card Ladder (paid partner API, signal-validation only)

**Source:** `https://www.cardladder.com/api/v2/`

**Auth:** partner key; **paid subscription** ($99/mo at time of writing).

**Scope for this task:** ship the adapter stub. Do not subscribe without
operator approval. The adapter is dormant until H-1.5 (backtesting harness)
is scoped.

**HUMAN GATE:** Do not proceed to paid signup without explicit
approval-to-spend in chat. If approval is given, the operator handles the
subscription + credential provisioning out-of-band.

### Step 13 — Wire the reconciler into /history, /flip, /movers

Now that adapters populate a richer dataset, the three consumers benefit from
the reconciler's audit trail. In each handler:

1. Call `fetch_sales(...)` as today (new registry path).
2. Add `reconciliation_audit` to the response payload (same shape as the
   reconciler emits).
3. The frontend (`HoloPage.tsx`) will display this in a collapsible "Data
   provenance" panel below the existing `data_quality_warning` chip. **This
   task does not require the frontend change — file as H-1.10-frontend
   follow-up.**

Keep `data_quality_warning` computation based on the reconciler's
`market_estimate / total_sales` ratio (same threshold, 30%).

### Step 14 — Observability sanity pass

After the registry is wired in:

- Deploy to a preview branch
- Hit `/api?action=health` — every configured adapter returns `ok: true`
- Run a 10-card smoke test through `/history` — inspect the
  `reconciliation_audit.by_adapter` map to confirm each adapter is actually
  contributing records
- Inspect Vercel function logs — verify each adapter emits exactly one JSON
  log line per call, with `latency_ms` populated and `error: null`
- Measure p50 and p95 `fetch_sales` latency against the legacy path — expect
  **no regression** because the ThreadPoolExecutor parallelizes what the old
  path did serially

**HUMAN GATE:** Paste the health endpoint output + one sample log line here
before closing the session.

### Step 15 — Documentation

Update in this order:

1. `docs/state/project-state.md` — new "What Was Just Done" block following
   the convention from session 10; add resolved bugs; update roadmap (H-1.10
   marked ✅ or 🚧 accordingly)
2. `CLAUDE.md` — add a new section "Data Sources" replacing the current
   "Data Sources (No API Keys Required)" subsection. List all 9 adapters
   with their feature-flag env var and credential status.
3. `docs/architecture/sources.md` (new file) — copy the Architectural
   Specification section from this prompt, plus the final priority table and
   one diagram of the fetch path
4. `docs/tasks/prompts/complete/H-1-10_{MM-DD}_multi-source-adapters.md` —
   move this file there with status `COMPLETE` or `PARTIAL` header noted

## Verification

```bash
# 1. Unit tests
.venv/bin/pytest tests/test_sources_*.py -q --tb=short

# 2. Existing tests (no regressions)
.venv/bin/pytest tests/ -q --tb=short

# 3. Parity test (Step 3 — requires network)
HOLO_USE_REGISTRY=1 .venv/bin/pytest tests/test_fetch_sales_parity.py -v

# 4. Type check
.venv/bin/mypy pokequant/sources/ --strict --ignore-missing-imports

# 5. Manual smoke — health endpoint (after deploy)
curl 'https://holo-lac-three.vercel.app/api?action=health' | jq

# 6. Manual smoke — /history with audit payload
curl 'https://holo-lac-three.vercel.app/api?action=history&card=Charizard+VMAX+20&days=30' | jq '.reconciliation_audit'
```

**Success criteria (all required for ✅ COMPLETE; partial completion means
🚧 IN PROGRESS with the incomplete adapters re-filed as their own H-1.10x
prompts):**

- [ ] Foundation (Steps 1–3) landed; `HOLO_USE_REGISTRY=1` stable in preview
- [ ] PSA Pop Report adapter live + `_handle_grade_roi` using real pop data
- [ ] 130point adapter live + visible in `reconciliation_audit`
- [ ] Cardmarket adapter shipped (may be disabled pending creds)
- [ ] Goldin/PWCC adapter shipped for >$500 cards
- [ ] Limitless adapter shipped with `/api?action=meta_signal` endpoint
- [ ] eBay Browse API adapter shipped (may be disabled pending OAuth approval)
- [ ] TCGPlayer Pro adapter stub shipped (disabled pending partner approval)
- [ ] Card Ladder adapter stub shipped (disabled pending paid signup)
- [ ] BGS Pop Report adapter shipped (may be disabled)
- [ ] All new code type-checks with `--strict` mypy
- [ ] All new code has tests with ≥80% coverage (measured via `pytest --cov`)
- [ ] `/api?action=health` returns healthy for every `enabled_by_default=True` adapter
- [ ] Docs updated (Step 15)

## Definition of Done

- [ ] Every checkbox above is ticked OR explicitly deferred with a follow-up
      prompt filed in `docs/tasks/prompts/pending/`
- [ ] `project-state.md` updated; commit pushed
- [ ] No regression in existing test suite (57+ passing)
- [ ] At least one non-trivial bug discovered via the new per-source metrics
      has been filed as a Resolved Bug entry (we know they exist; the point
      of this refactor is to surface them — be honest about what you find)

## Rollback

Full rollback (per-step rollbacks documented in each commit message):

```bash
# Flip the kill switch first — instant
vercel env add HOLO_USE_REGISTRY 0 production
vercel redeploy

# If the code itself is breaking imports or cold-start, revert
git revert <merge-commit-sha>
git push
```

Partial rollback — disable a single adapter:

```bash
vercel env add HOLO_ADAPTER_130POINT 0 production
vercel redeploy
```

If the new `pokequant/sources/` package itself is broken enough to prevent
the serverless function from booting, `git revert` the introduction commit;
because `fetch_sales()` was renamed (not replaced) in Step 3, the legacy
path is still intact at `_fetch_sales_legacy()` and a one-line swap restores
full service.

## Known risks + mitigations

| Risk | Mitigation |
|---|---|
| Vercel 60s timeout exceeded by 9-adapter fan-out | Per-adapter 12s timeout enforced by `concurrent.futures.wait(timeout=...)`; slow adapters get their partial result discarded, fast ones still return |
| SQLite /tmp cache contention under parallel adapter writes | WAL already enabled; registry writes are fire-and-forget via the existing `_cache_put` pattern; short-lived connections |
| OAuth credential leakage | Never commit `.env`; never log auth headers; use Vercel Sensitive flag; audit the commit before push |
| 130point / Goldin / Cardmarket TOS violation | Respect robots.txt; cap rate at 1 req/sec per source; cache aggressively (24h); do not redistribute raw data |
| Reconciler bug silently drops good sales | Parity test (Step 3) catches distributional deltas; audit payload makes per-adapter contribution visible in production |
| Partner API approvals block session completion | Each credential-gated adapter ships disabled-by-default — session completes cleanly, operator flips flags later |
| Cold-start regression from new package imports | Keep imports local to adapter methods, not module top; registry.discover() lazy-loads on first use; measure cold-start latency before merge |

## Commit cadence guidance

One commit per step minimum, with conventional-commits prefixes:

- `feat(sources): SourceAdapter ABC + NormalizedSale schema` (Step 1)
- `feat(sources): registry with parallel fan-out + structured logs` (Step 2)
- `refactor(scraper): migrate fetch_sales to registry with parity shim` (Step 3)
- `feat(sources): PSA Pop Report adapter + real grading-ROI probabilities` (Step 4)
- `feat(sources): 130point adapter` (Step 6)
- ... one per remaining adapter
- `feat(api): /health endpoint + reconciliation_audit in /history and /flip` (Step 13)
- `docs: multi-source architecture` (Step 15)

Never batch unrelated adapters into one commit — per-source rollback depends
on clean commit boundaries.
