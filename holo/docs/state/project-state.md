# Holo — Project State

*Keep this file current. The advisory board reads it at the start of every meeting.*

---

## What Holo Is

A Pokémon TCG price intelligence tool for serious traders and investors.
Live at: **https://www.handoffpack.com/lab/holo**

Target user: Someone trying to turn card trading into real income — not casual collectors.
They want an unfair data advantage, not another price lookup.

---

## What Was Just Done (2026-04-23 — session 12)

### H-1.10a backend wiring + parity gate + mypy + docs ✅ COMPLETE

Closed the backend side of the H-1.10 follow-up. Frontend provenance panel (single remaining scope item, cross-repo in `handoffpack-www`) filed as **H-1.10a-ui**.

**Reconciliation audit plumbing (`<hash>` audit-wiring commit)**:
- New `LAST_AUDIT` contextvar in `pokequant.sources` — set by `_fetch_sales_via_registry` after `reconcile()`, cleared by the dispatcher before each call so legacy-path responses never inherit a stale audit.
- `api/index.py::_current_audit()` helper reads the contextvar and returns the dict or None.
- `_handle_history` and `_handle_flip` responses now carry a `reconciliation_audit` field. Null when `HOLO_USE_REGISTRY=0` served the request.
- `_handle_movers` intentionally skipped — ThreadPoolExecutor fan-out overwrites the contextvar per worker; aggregation is its own design problem, filed as a deferred detail.
- 5 new audit-plumbing tests.

**Parity test + mypy (`<hash>` parity-and-mypy commit)**:
- `tests/test_fetch_sales_parity.py` — 5 canary cards run through both legacy and registry paths with `HOLO_USE_REGISTRY` toggled; asserts ±5% median delta. Live-gated on `HOLO_RUN_PARITY=1` (same pattern as the drift canary). 4 offline delta-math tests run in the default suite.
- This is the **gate** for flipping `HOLO_USE_REGISTRY=1` in production. Do not enable the flag until this test runs green.
- `mypy --strict --ignore-missing-imports pokequant/sources/` → Success, no issues found in 19 source files. Fixed 15 initial errors (mostly `dict` → `dict[str, Any]`, typed `**kwargs`, LAST_AUDIT contextvar parameterized).
- mypy + types-requests added to dev deps.

**meta_signal endpoint (`<hash>` meta-signal commit)**:
- `GET /api?action=meta_signal&card=<name>` — consumes the Limitless adapter. Currently returns `{enabled: false, signals: [], note: "H-1.3 will activate"}` since Limitless is still a stub. Endpoint shape is stable so frontend work can develop against it without blocking.

**Documentation (`<hash>` docs commit)**:
- New `docs/architecture/sources.md` — full spec: package layout, fetch-path diagram with registry path, invariants, priority table, audit schema, health endpoint, feature flags, observability, testing, rollback procedures.
- `CLAUDE.md` Data Sources section rewritten — now a dual-path explanation with a full adapter table (9 adapters, live/stub status, feature flag, required env vars).

**Test suite:** 122 passed, 10 skipped (5 live canary, 5 live parity). mypy strict clean.

**Decisions:**
- **ContextVar over thread-local** — `threading.local` would bind to the ThreadPoolExecutor worker, invisible to the caller. `contextvars.ContextVar` propagates correctly across `asyncio` and across `ThreadPoolExecutor` workers when using `concurrent.futures` properly. Clean API, standard library.
- **Movers audit deferred** — honest scope cut. Cross-worker aggregation needs a new primitive; not worth inventing one before we know what the UI wants.
- **Parity test lives in the test suite, not as a separate script** — keeps the gate adjacent to the code it protects. `HOLO_RUN_PARITY=1` toggle mirrors the canary's `HOLO_RUN_CANARY=1`, consistent operator model.
- **meta_signal endpoint ships empty** — the shape matters more than the content right now. Frontend consumers get a stable contract they can build against while H-1.3 fleshes in the Limitless data.

---

## What Was Just Done (2026-04-23 — session 11 part 2)

### H-1.10 multi-source adapter platform — foundation + 2 live adapters + 7 stubs 🚧 PARTIAL

Landed Steps 1–7 + 10–12 of the H-1.10 prompt. Remaining work (wiring `reconciliation_audit` into `/history`/`/flip`/`/movers`, frontend provenance panel, parity test, full docs pass) queued as **H-1.10a**. `HOLO_USE_REGISTRY=0` stays the default in production — no behavior change until the parity test passes.

**Foundation (`9a94375`)** — `pokequant/sources/` package:
- `schema.py` — `NormalizedSale` dataclass, `Currency`/`Grade`/`SourceType` literals, invariant constants
- `base.py` — `SourceAdapter` ABC with `HOLO_ADAPTER_<NAME>` env flag
- `registry.py` — `SourceRegistry` singleton; auto-discovers `pokequant.sources.adapters.*`; parallel fan-out via `ThreadPoolExecutor(max_workers=len(active))` with 12s per-adapter timeout; enforces `NormalizedSale` invariants on ingress; emits one JSON line per adapter call to stderr (`{ts, event, adapter, card, count, latency_ms, error}`)
- `reconciler.py` — pure merge/FX-normalize/dedup/IQR-outlier function; returns `(records, ReconciliationAudit)`
- `priority.py` — `ADAPTER_PRIORITY` table drives dedup tie-breaks
- `fx.py` — static `EUR=1.08 / GBP=1.27 / JPY=0.0066` → USD
- `exceptions.py` — `InvalidSaleRecord`, `AdapterTimeout`, `AdapterNotConfigured`
- 21 foundation tests (schema invariants + reconciler algorithm)

**Health + parity shim (`4c66ad0`)**:
- `/api?action=health` iterates the registry, calls each adapter's `health_check()`, returns `{adapters: [...], summary: {total, configured, healthy}}`, cache 30s
- `fetch_sales()` is now a dispatcher. With `HOLO_USE_REGISTRY=1`, routes to a registry + reconciler path; empty-result or exception falls back to the legacy cascade. Legacy implementation renamed to `_fetch_sales_legacy` verbatim. Kill-switch is instant via env var

**Live adapters:**

- **PSA Pop Report** (`69a720e`) — `PSAPopAdapter` scrapes `psacard.com/pop/tcg-cards/pokemon/...`, 7-day sqlite cache (matches PSA's weekly update cadence). Emits `source_type="pop_report"`, exposes `fetch_pop()` for `_handle_grade_roi`. Handler now uses real `pop10/total` + `pop9/total` probabilities when `total >= PSA_POP_MIN_SAMPLES` (=50); user-supplied `?p10=/?p9=` still wins. Response now includes `assumptions.pop_source` = `"heuristic"|"psa_pop"` + raw `pop_data` for transparency. 8 unit tests.

- **130point** (`3beb18c`) — `OneThirtyPointAdapter` scrapes `130point.com/sales/?search=<card>`. Raw grade only. Propagates 130point's lot/damaged/reprint keyword hints to `outlier_flag` with `confidence=0.9`. Tolerant parser: ISO + `M/D/YYYY` dates, thousands-comma prices, skips malformed rows. 8 unit tests.

**Credential-gated stubs (`f0ebff5`)** — all `enabled_by_default=False`:
- `bgs_pop` (session cookie)
- `cardmarket` (OAuth 1.0 HMAC, EUR)
- `goldin` (scrape, $500+ cards; endpoint URLs pending verification)
- `limitless` (free JSON API; disabled until meta_signal endpoint wired)
- `ebay_api` (OAuth 2.0, 5k/day free tier)
- `tcgplayer_pro` (multi-day partner approval)
- `card_ladder` (paid $99/mo, blocks on spend approval)

Shared `CredentialStub` base in `adapters/_stub.py` — concrete stubs only declare name + priority + currency + `required_env` + `stub_reason`. `health_check` reports the missing credential so `/api?action=health` surfaces the setup gap.

**Bug discovered + fixed during this task:**
- **Registry deadlock on `discover()`** — `discover()` held `self._lock` while adapter modules imported and called `registry.register()`, which also grabbed `self._lock`. Python's `threading.Lock` is not reentrant → deadlock on first `/api?action=health` request. Fix: `threading.RLock()`. Caught by `test_sources_stubs.py::test_all_stubs_register` hanging. This is exactly the kind of "the point of the refactor is to surface bugs" the prompt's DoD anticipates.

**Test suite:** 113 passed, 5 skipped (live canary), 0 failed. 46 new tests this session.

**Commits (this half):** `9a94375`, `4c66ad0`, `69a720e`, `3beb18c`, `f0ebff5`.

**Decisions:**
- **File-based adapter discovery over explicit registration** — `pkgutil.iter_modules` + `importlib.import_module` at boot. Each adapter `register()`s itself at import time. Easier to add/remove adapters without touching a central list.
- **Reconciler is pure; registry enforces invariants** — separation of concerns. Adapters trust the registry to reject bad records; reconciler never touches the network or sqlite. Makes reconciler fully unit-testable with synthetic fixtures.
- **`HOLO_USE_REGISTRY=0` is default** — the registry path has zero adapter coverage that matches the full legacy cascade (no eBay API, no PC scraper rehoused). Flipping the flag now would drop most records. The parity test in H-1.10a is the gate.
- **RLock over Lock** — the single-word fix. Discovery is inherently reentrant; `threading.Lock` was the wrong primitive. Documented in the commit message so future readers don't re-break it.

---

## What Was Just Done (2026-04-23 — session 11)

### Hardening sweep — CORS, shared HTTP session, scraper canary ✅ COMPLETE

Closed three of the four hardening prompts queued from the 2026-04-22 code review. H-1.9 (edge rate limit via Upstash) deferred — lives in `handoffpack-www` and needs operator signup; decided to defer until a real abuse signal shows up.

**H-1.6 — CORS origin allowlist** (`fc9e707`)
- Replaced `Access-Control-Allow-Origin: *` with `_resolve_allowed_origin()` in `api/index.py`
- Allowlist: `handoffpack.com`, `www.handoffpack.com`, `*.vercel.app` containing `handoffpack-www`, `localhost:3000` outside production
- Added `do_OPTIONS` preflight handler + `Vary: Origin` when CORS header is emitted
- 10 unit tests in `tests/test_cors.py`

**H-1.7 — Shared HTTP keep-alive session** (`3aedf7f`)
- New `pokequant/http.py` — thread-safe singleton `requests.Session` with 16/32 connection pool
- `api/index.py::_http_session` now delegates to `pokequant.http.session`; all 3 direct `requests.get()` sites in `pokequant/scraper.py` migrated (PC/eBay `_get`, TCGPlayer redirect, TCGPlayer infinite-api history)
- Saves ~100–300ms per call on warm Vercel instances by reusing TCP+TLS handshakes across fan-outs
- Existing test mocks patch `_get` one layer up, so no test changes needed

**H-1.8 — Scraper drift canary** (`bec3cb6`)
- `tests/canary.py` — 5 liquid canary cards (Charizard VMAX 20, Pikachu 58, Umbreon VMAX 215, Giratina V 186, Mew VMAX 114). Each `fetch_sales()` asserted against a baseline median with ±50% drift fence
- `data/canary_baseline.json` — file-based baseline (deferred the Supabase `holo.canary_baseline` table from the prompt; avoids a schema migration for v1)
- EWMA update (alpha=0.3) resists single-day noise
- `pytest.ini` registers the `canary` marker and extends `python_files` so `canary.py` is discoverable
- `.github/workflows/scraper-canary.yml` — `workflow_dispatch` only until baseline seeded + tolerance tuned; webhook alert stubbed/commented
- Live tests gated on `HOLO_RUN_CANARY=1`; 4 offline drift-math tests run in the default suite

**Test suite:** 71 passed, 5 skipped (live canary), 1 pre-existing deprecation warning unchanged.

**Decisions:**
- **File-based canary baseline over Supabase table** — avoids a schema migration for a v1 canary; JSON is human-readable and diff-friendly in git. Can migrate to Supabase later if we need multi-environment or historical data.
- **GitHub workflow lands disabled** — follows the prompt's rollout plan: seed baseline manually 3× over 48h, then enable the schedule. Avoids false alerts on an empty baseline.
- **H-1.9 deferred** — cross-repo in `handoffpack-www`, requires Upstash signup + Vercel env vars. Operator not ready for that ops surface yet; prompt stays in `pending/`.

---

## What Was Just Done (2026-04-22 — session 10 tooling fix)

### end.sh actually pushes to origin/main now ✅ COMPLETE

Discovered mid-session that `scripts/end.sh` had been silently orphaning commits on worktree branches since its introduction. Every `/end-session` from a `claude/*` worktree claimed success but left commits unpushed to `origin/main` — next session's `/start-session` saw stale state.

**Root cause:** `git push origin main` pushes the *local* `main` ref, which on a worktree branch is whatever was there the last time main was updated — i.e. stale. Git correctly reported "Everything up-to-date" because local `main` equalled `origin/main`. The feature-branch HEAD never participated in the push.

**Fix:** switch to `git push origin HEAD:main` with a divergence guard:
- Fast-forward path: pushes current HEAD to origin/main, updates local `main` ref so sibling worktrees pick up the advance on next fetch.
- Divergence path: refuses the push, explains how to rebase, exits non-zero.
- Same pattern applied to the handoffpack-www push block for future-proofing.
- Added an explicit `git fetch origin main` at the start so ahead/behind counts are actually current.

**Modified:** `holo/scripts/end.sh` — push logic rewritten

**Commits:**
- `7927a6f` fix(scripts): end.sh actually pushes commits to origin/main

**Decisions:**
- **Fail loud on divergence, not force-push.** A force-push would silently eat remote commits made by a parallel agent. Better to stop and ask.
- **Keep local `main` in sync via `update-ref` after the push.** Without this, sibling worktrees would still see stale local `main` until they fetched — surprising and easy to trip over.
- **Retroactively repaired this session.** Manually pushed `HEAD:main` earlier to recover the 5 orphaned commits (d6f8b80 → 3e937d8) plus this fix (7927a6f). Verified `origin/main` + local `main` both at `7927a6f` before /end-session.

---

## What Was Just Done (2026-04-22 — session 10)

### Comprehensive code review + accuracy hardening ✅ COMPLETE

Full-app review focused on quality and price-data accuracy. Found 2 CRITICAL and 7 HIGH issues; auto-fixed the 4 that didn't require security/API/architecture restructuring. Queued 4 prompt files for the rest.

**Modified:**
- `holo/api/index.py` — `_handle_flip` + `_handle_history` now emit `synthetic_ratio` + `data_quality_warning` when >30% of records are non-sales. `_handle_movers` outlier floor requires ≥5 sales before using `median*0.15` (falls back to `HARD_PRICE_FLOOR`).
- `holo/pokequant/scraper.py` — TCGPlayer history, PC static, and pokemontcg.io synth records now tagged `source_type: "market_estimate"`. PC+eBay merge dedupes on `(rounded_price, date)`. All 8 `datetime.utcnow()` call sites migrated to `datetime.now(timezone.utc)` for Py 3.13 compat.
- `handoffpack-www/components/lab/holo/HoloPage.tsx` — amber warning chip rendered on flip-verdict panel and above the sparkline whenever `data_quality_warning` is non-null. Matches existing 1Y-sparsity warning pattern.

**New prompt files (pending):**
- `H-1-6_04-22_cors-origin-allowlist.md` — restrict `Access-Control-Allow-Origin` to handoffpack.com + preview suffixes
- `H-1-7_04-22_shared-http-session.md` — share `requests.Session` between api/ and pokequant/
- `H-1-8_04-22_scraper-drift-canary.md` — daily canary + Supabase baseline + GitHub Actions webhook alert
- `H-1-9_04-22_edge-rate-limit.md` — Upstash Redis + Next.js middleware per-IP / per-action rate limits
- `H-1-10_04-22_multi-source-adapters.md` — PhD-level XL prompt: unified `SourceAdapter` ABC + `NormalizedSale` schema + registry + reconciler + 9 concrete adapters (eBay Browse API, 130point, PSA Pop, BGS Pop, Cardmarket, Card Ladder, TCGPlayer Pro, Limitless, Goldin/PWCC). Feature-flagged per adapter; credential-gated adapters stub-ship disabled; parity test gates registry cutover.

**Commits:**
- `d6f8b80` fix(holo): accuracy hardening — flag market-estimate data, dedup PC+eBay, tz-aware dates, robust movers floor
- `8398d89` (handoffpack-www) feat(lab/holo): surface data_quality_warning on flip + price chart
- `30e59bd` docs: queue 4 hardening task prompts from 2026-04-22 code review
- `7bef122` docs: update project state after session 10 (code-review + accuracy hardening)
- `7c78be9` docs: queue H-1.10 multi-source adapter platform prompt

**Decisions:**
- **`source_type` over weighted blending.** Considered down-weighting market-estimate records inside `generate_comp`. Chose explicit tagging + UI warning instead — simpler, more honest ("we're showing you an estimate, not a sale"), and non-destructive to existing comp math. Blending can come later once we have enough data to calibrate the weight.
- **Dedup key = (rounded_price, date).** Pragmatic choice. PC and eBay sales can match by exact cents on the same day — extremely unlikely to be genuine coincidence on liquid cards (<1% false-positive rate expected). Alternative (sale_id linking) would require a true cross-source matcher.
- **Auto-fix scope limits.** Followed the review rule: `--fix` doesn't apply security (CORS), public API shape (movers payload), or architecture (shared HTTP module) changes. Those got prompt files for deliberate single-session implementation instead.
- **Source expansion recommendations documented.** Top-3 by impact: eBay Browse API (replaces fragile HTML scrape), 130point.com (sale-comp cross-validation), PSA Pop Report (grading liquidity — currently missing, makes `_handle_grade_roi` a guess). These will become future H-1.x tasks once H-1.6–H-1.9 land.

**Known cosmetic issue:** `tests/test_scraper.py:201` still uses the deprecated `datetime.utcnow()` — test-only, warning not failure, left for a cleanup pass.

---

## What Was Just Done (2026-04-21 — session 9 hotfix)

### Crash on back-nav when Recently Viewed has stale entries ✅ COMPLETE

User reported a full-page crash ("Application error: a client-side exception has occurred") when navigating back from a card detail. Reproduced on production via Chrome console — `TypeError: Cannot read properties of undefined (reading '0')` inside an `Array.map`. Traced to `RecentlyViewed` rendering `item.name[0]` when a stale localStorage entry had no `name` field (from an older schema or an incomplete `handleMetaReady` fire).

**Modified:** `handoffpack-www/components/lab/holo/HoloPage.tsx` — hardened `useRecentlyViewed` hook and render site

**Commits:**
- `8206a1d` fix(lab/holo): crash on back nav when Recently Viewed has stale entries

**Three-layer fix:**
- **Self-healing localStorage** — `useRecentlyViewed` validates parsed list on mount, drops entries missing `card`/`name`, and writes back the pruned list so bad data auto-clears on next load.
- **Reject incomplete writes** — `add()` bails if `card` or `name` is missing; coerces `image_small` to `''` so `JSON.stringify` can't drop the field to undefined.
- **Safe render** — `item.name?.[0] || '?'` as belt-and-suspenders for any future stale entry.

**Decisions:**
- **Three layers not one** — fixing only the render would leave bad data in localStorage forever. Fixing only the hook would still crash anyone whose browser had the data from before the fix deployed. All three layers together make the bug unrecoverable.
- **Reproduced in Chrome first** — confirmed the exact error signature before writing the fix. Cheap step, kept the fix narrowly targeted.

---

## What Was Just Done (2026-04-21 — session 9)

### Interactive price chart scrubber ✅ COMPLETE

Drag mouse or finger across the price sparkline to see price + date at each data point.

**Modified:** `handoffpack-www/components/lab/holo/HoloPage.tsx` — `Sparkline` component fully reworked with scrubber + all code-review fixes applied same session

**Commits:**
- `408c052` feat(lab/holo): interactive price scrubber on sparkline chart
- `0539b1e` fix(lab/holo): address all code-review findings on price scrubber

**What was built:**
- `onPointerMove` handler maps `clientX → nearest data point` (unified mouse + touch via Pointer Events API)
- Dashed vertical crosshair line tracks cursor position inside the SVG
- Scrubber dot rendered **outside** the SVG as an absolutely-positioned `<div>` — avoids oval distortion from `preserveAspectRatio="none"`
- Floating tooltip: accent-colored monospace price + UTC-correct date + sale count. Flips left/right at 58% threshold to prevent edge clipping.
- Last-point static dot hides while scrubbing to avoid visual collision

**Code-review fixes applied immediately after (all severity levels):**
- `setPointerCapture` on `pointerdown` — touch scrubs stay tracked past SVG edge bounds
- `touch-action: none` moved from wrapper `<div>` to `<svg>` only — mobile page scroll no longer blocked
- `onPointerCancel` handler — clears frozen tooltip on iOS interrupts (call, Face ID, palm rejection)
- `useMemo` for `xs`/`ys`/path geometry — heavy computations no longer run at 60Hz during scrub ticks
- `useCallback` for all 4 pointer handlers — stable refs across renders
- `scrubbedPt` bounds check — stale `idx` after grade/range switch can't crash
- `formatScrubDate` + `timeZone: 'UTC'` — correct date for US west-coast users
- `rect.width === 0` guard in handler
- `tabular-nums` added to date line in tooltip
- `formatScrubDate` catch returns `'—'` not raw API string
- `useId()` replaces `spark-grad-${tone}` — per-instance gradient ID, no DOM collision across Sparklines
- `SPARK_WIDTH`/`SPARK_PAD` extracted as module-level constants; clean `useMemo` deps
- `role="img"` + `aria-label` on SVG for screen reader accessibility
- Removed unused `svgRef`; `e.currentTarget.getBoundingClientRect()` used instead

**Decisions:**
- **Pointer Events API over mouse+touch split** — `onPointerMove` unifies both inputs; `setPointerCapture` handles the touch boundary case cleanly without separate touch event handlers.
- **Dot outside SVG** — `preserveAspectRatio="none"` with unequal x/y scale renders SVG circles as ovals. A CSS div is always a circle.
- **useMemo for geometry, not the handler** — xs/ys are computed once per data load; the handler stays lightweight (just index lookup + setScrub).
- **useId() for gradient IDs** — React 18's stable ID primitive; zero runtime cost, eliminates the multi-Sparkline collision forever.

---

## What Was Just Done (2026-04-19 — session 8)

### Collectr-style mobile home UX + feature-tile revert ✅ COMPLETE

Short, focused session. Added discoverability improvements to the mobile home page, then trimmed back a piece that wasn't pulling its weight.

**Added (kept):**
- **Market pulse chip** at top of `HomeView` — green pulsing dot + "Market · Live" on the left; tappable top-mover ticker on the right (e.g. "▲ +28.3% Giratina V") that navigates straight to the card. Fetches `/api?action=movers&limit=10&window=7` on mount.
- **Persistent mobile bottom nav on HomeView** — matches the card-detail nav pattern (`sm:hidden fixed inset-x-0 bottom-0 z-40`, safe-area-inset-bottom, 56px tap targets, gold-for-active, Fraunces caps labels). 4 tabs: Home / Movers / Watchlist / Search. Each smooth-scrolls to its section ref; Search focuses the combobox input and pops the mobile keyboard.
- Section refs (`searchHeroRef`, `moversRef`, `watchlistRef`, `recentRef`) drive the nav. Local `HomeTab` type avoids collision with card-detail's existing `Tab`.

**Added then removed (same session):**
- 2×2 feature-tile grid (Top Movers / Watchlist / Recently Viewed / Flip Calculator) between hero and watchlist. Tiles only scrolled to content already visible below on the same page — the operator (rightly) flagged they "didn't go anywhere". Reverted along with the orphaned transient-hint state that only supported the Flip tile.

**Modified:** `handoffpack-www/components/lab/holo/HoloPage.tsx` — `HomeView` restructured with pulse chip + bottom nav + section refs

**Commits (this session):**
- `e92ad61` feat(lab/holo): Collectr-style mobile home — tiles, market pulse, persistent bottom nav
- `b89371f` revert(lab/holo): remove feature-tile grid (tiles didn't navigate anywhere meaningful)

**Decisions:**
- **Tiles require real destinations.** Scrolling to content that's already scroll-visible below isn't discoverability — it's friction. Future tiles must open a view that doesn't otherwise exist (e.g. a Sealed Box EV tool that doesn't need a card, or a "Browse by Set" index).
- **Preserved the two patterns that do real work:** pulse chip (live market signal + one-tap navigation) and persistent bottom nav (always-visible wayfinding).

---


## Previous Sessions

- **Pokédex overlay + search autocomplete + perf + audit fixes + Fraunces + multi-color takeover (2026-04-17 s4):** Biggest session to date. Pokédex side-panel overlay merging pokemontcg.io + pokeapi.co (species data, stats, attacks, 30-day sqlite cache, pinned by id). ARIA-1.2 search combobox (250ms debounce, AbortController, server ranking). Performance: module `requests.Session` pooling, slim `select=` fieldsets, parallel movers via `ThreadPoolExecutor(8)`, WAL sqlite, per-action `Cache-Control`, edge-runtime Next.js proxy, `THEME_CACHE`. Audit-driven fixes: `/tmp` cache fallback on Vercel, exception handler hides `str(exc)`, flip `margin_pct` uses cost not revenue, flip break-even recomputes shipping tier, search cache skips errors, `useCardTheme` onerror fallback. Fraunces + Inter Tight + JetBrains Mono replaces Orbitron/Press Start 2P. 3.5× full-viewport card-color takeover with top-3 dominant hues + conic gradient foil + 900ms crossfade. 13 commits; notable: `f72d164` (pokedex backend) · `444e0c3` (api perf) · `89eb6a6` (Fraunces + multi-color + fade) · `8101d47` (pokedex id lookup).
- **Top Movers scroll w/ images + Recently Viewed row (2026-04-19 s6):** `useRecentlyViewed` hook (localStorage, 10-item cap, newest-first dedup). `RecentlyViewed` drag-scroll row at HomeView bottom in violet to distinguish from gold TopMovers. `onMetaReady` callback on `CardDetail` captures real `image_small` via `history.meta` so images are never blank placeholders. Commit `db396fb`.
- **Supabase L2 cache fully activated in production (2026-04-19 s7):** Service-role key + `SUPABASE_URL` added to Vercel holo project (Production + Preview, Sensitive). Redeployed; verified 86-sale `/history` request writes through to `holo.sales_cache`. End-to-end L1/tmp → L2 Supabase → live scrape pipeline confirmed. No code change — pure env-var activation. Known cosmetic: Vercel log stream doesn't show `logger.info` (default WARNING level) — filed for polish pass.
- **Ultra Ball theme + full-bleed card takeover + draggable movers + mobile bottom nav + flip bug fix (2026-04-16 s3):** `Pokeball` component redesigned as Ultra Ball (gold + black H-stripes + red pinstripe). `useCardTheme` extended with `bgBase/bgDeep`. Full-bleed stacked-gradient takeover on detail page. TopMovers switched to native drag-scroll with auto-scroll + "View all" modal. Mobile bottom nav (Overview/Sales/Flip/Grade) with safe-area-inset. Fixed `UnboundLocalError: DEFAULT_PACKS_PER_BOX` in flip handler. Commits `a7cc2fc` · `0144481`.
- **Supabase L2 cache — dark launch + DB migration (2026-04-17 s5):** Created `holo` schema with `sales_cache` + `scrape_runs` tables, RLS on zero policies, idempotent migration (`db/migrations/001_holo_sales_cache.sql`). New `pokequant/supabase_cache.py` PostgREST client — feature-gated, graceful fallback, fire-and-forget writes. Wired write-through into `fetch_sales`. Migration applied via Chrome automation; `holo` added to Data API Exposed schemas. Handoffpack `public` untouched. Commit `7baf6dc`.
- **Pokéball branding + card-driven palette + Top Movers endpoint (2026-04-16 s2):** `/api?action=movers` endpoint ranks ~12 liquid cards by `|change_pct|` over 7D. Inline SVG Pokéball, `useCardTheme` canvas-sampling hook. Commits `1a4ec7c`, `1f23e27`.
- **Session tooling + cleanup (2026-04-16 s1):** `end.sh` handoffpack-www push block, `DEFAULT_PACKS_PER_BOX` config constant, 57-test scraper suite landed. Commits `55026f4`...`cad01eb`.
- **Full UX overhaul + multi-source scraping fixes (2026-04-16):** Original fonts, card hero background, lightbox, glassmorphism; eBay selector fix, TCGPlayer sparse supplement, box flip math ÷ packs, `?action=meta`. Commits `68644c9`, `1da815d`.
- **Session workflow + earlier fixes (2026-04-16):** Card images CSP, date range tab cache collision fix, /start-session, /end-session, /run-task, /prompt-builder, /sync, /alpha-squad, /code-review commands. Commits `24c0542`, `fe5b7a5`, `caef365`, `58d14a1`.

---

## Current Status (as of 2026-04-22 — session 10)

### Phase
Post-MVP web launch. Pre-monetization. Actively iterating.

### What's Live
- Bloomberg-style 5-tab dashboard (Overview, Sales, Flip, Grade It?)
- **Card hero UI**: blurred card art background, 140×196px centered card image, click-to-lightbox
- **Card-driven palette**: `useCardTheme` extracts top-3 dominant hues (`chroma² × √luma` weighted) returning `{accent, accent2, accent3, glow, deep, bgBase, bgDeep, hue, isWarm}`. 7-layer full-bleed takeover including a conic-gradient foil (120s/rev) for subtle iridescence. Smooth 900ms crossfade between cards via keyed wrapper + opacity transition.
- **Pokédex overlay**: full-screen on card-tap. Two-col desktop / stacked mobile. Merges pokemontcg.io TCG data + pokeapi.co species data. Set logo, species banner, physical strip, type chips (18-type color map), 6-row base stats, species flavor quote, TCG abilities/attacks with energy circles, retreat, TCGPlayer link. Pinned by `meta.id` for exact-printing match.
- **Card search autocomplete**: WAI-ARIA 1.2 combobox, 250ms debounced `/api?action=search`, AbortController cancels stale. Thumbnail + name + caps meta line (Set · Series · Year · Rarity), `<mark>` highlighted match. ArrowUp/Down wrap, Enter selects or falls back to raw submit. Canonicalizes selection to `"<name> <number>"`.
- **Top Movers**: draggable horizontal scroller (pointer + touch) with gentle auto-scroll, pause on interact, "View all" modal grid.
- **Ultra Ball SVG**: gold radial gradient top with black H-stripes + red pinstripe accent; brand mark size 56 with float + hover-spin.
- **Mobile bottom nav**: fixed 4-tab bar (Overview/Sales/Flip/Grade) with safe-area-inset on card detail; desktop keeps top tabs.
- **Typography**: Fraunces (variable, opsz/SOFT/WONK axes) for display + HOLO wordmark (Black italic 5xl), Inter Tight for body, JetBrains Mono for numerics.
- **Glassmorphism panels**: backdrop-blur + semi-transparent + glass-edge highlight
- Card image lightbox: fullscreen overlay, ESC to dismiss
- Back navigation: Orbitron pill button with accent hover
- Date range tabs: 7D / 30D / 90D / 1Y sparkline (1Y shows sparsity warning if <20 points); active tab has solid-accent background + glow
- **Interactive price scrubber**: drag mouse or finger across the sparkline to inspect price + date at each data point. Crosshair line, glowing dot, floating tooltip (accent-colored monospace price + UTC date + sale count). Pointer capture keeps touch tracking stable past edge bounds. `touch-action:none` scoped to SVG only so mobile page scroll works. Per-instance `useId()` gradient IDs prevent multi-chart collision.
- Grade selector: Raw / PSA 9 / PSA 10
- Hero price ("Latest Price") + delta chip + Hi/Lo/Open stats; **outlier floor at 15% median** filters junk listings from LOW stat
- Trade signal (STRONG BUY → STRONG SELL) with RSI-14
- Grade comparison table with grading premium %
- Sales feed (30 most recent completed sales with source links)
- Flip P&L calculator — **box method divides cost by packs** (`DEFAULT_PACKS_PER_BOX = 36` in config)
- Grade It? ROI calculator (PSA/CGC grading EV with 6 service tiers)
- Watchlist (localStorage persistence)
- Source attribution links (PriceCharting, eBay, TCGPlayer)
- No auth gate — fully public

### Data Pipeline
- **Primary:** PriceCharting.com HTML scraping (completed auctions)
- **Supplement:** eBay completed listings (raw grade, augments PC data)
- **Fallback chain:** TCGPlayer → pokemontcg.io synthetic prices
- **Cache:** SQLite in /tmp/ (24h TTL, keyed by card_slug + grade + days)
- **Card meta:** pokemontcg.io REST API (7-day cache, name-only search + number proximity ranking)

### Signal Engine
- SMA-7 / SMA-30 crossover
- RSI-14 (Wilder smoothed EWM) — STRONG BUY < 30, STRONG SELL > 70
- Volume surge detection
- Exponential decay weighted comp (λ=0.3)
- IQR outlier normalization

### Infrastructure
- Python Vercel serverless: `holo-lac-three.vercel.app` (60s maxDuration)
- Next.js frontend: `handoffpack-www` on Vercel → proxy at `/api/holo`
- Two-repo architecture: lab (Python API) + handoffpack-www (Next.js)

---

## Resolved Bugs (recent)
- ✅ TCGPlayer / pokemontcg.io / PC-static market estimates contaminated flip + history as if they were completed sales (2026-04-22) — records now tagged `source_type: "market_estimate"`; `/flip` and `/history` return `synthetic_ratio` + `data_quality_warning`; UI shows amber chip when >30%
- ✅ eBay + PriceCharting double-counting the same sale in the median (2026-04-22) — dedup on `(rounded_price, date)` in `fetch_sales`
- ✅ Movers outlier floor could clear junk through on <5-sale cards (2026-04-22) — fall back to `HARD_PRICE_FLOOR` until 5+ samples are available
- ✅ `datetime.utcnow()` deprecated in Py 3.13 — migrated 8 scraper call sites to `datetime.now(timezone.utc)` (2026-04-22)
- ✅ Full-app crash on back-nav when Recently Viewed had stale entries (2026-04-21) — `RecentlyViewed` rendered `item.name[0]` without guarding for undefined; fixed with 3-layer hardening in `useRecentlyViewed` (self-healing prune on mount, rejecting incomplete writes, optional-chaining at render)
- ✅ Pokédex overlay showed wrong card printing (2026-04-17) — overlay re-searched by name only; now passes `meta.id` and backend uses `_lookup_card_by_id` for an exact pokemontcg.io match
- ✅ Pokédex overlay transparent on desktop (2026-04-17) — `bg-black/92` not in Tailwind's default scale, silently compiled to no background; replaced with inline rgba
- ✅ Card takeover confined to hero only (2026-04-17) — root div's opaque gradient painted over `-z-10` layers; moved base to `-z-20` fixed + `isolation: isolate` on root; gradient flood no longer fades to black
- ✅ Flip `margin_pct` was return-on-revenue not return-on-cost (2026-04-17) — `profit / market_value` → `profit / cost_basis`
- ✅ Flip break-even overstated when shipping tier would flip (2026-04-17) — recompute with PWE if calculated break-even falls below `SHIPPING_VALUE_THRESHOLD`
- ✅ Generic exception handler leaked `str(exc)` to clients (2026-04-17) — now logs traceback server-side + returns `{error, trace_id}`
- ✅ `_handle_search` cached error responses (2026-04-17) — 6-hour empty-typeahead poisoning when pokemontcg.io blipped; skip cache-put on error
- ✅ `scraper.py` could crash Vercel cold-start with stdout pollution + sys.exit (2026-04-17) — `_resolve_cache_db` detects VERCEL env, safe /tmp fallback, silent stderr warnings only
- ✅ Autocomplete dropdown overlapped TopMovers on mobile (2026-04-17) — search hero at `z-40`, dropdown at `z-[60]`; TopMovers' drag-scroll stacking context no longer wins
- ✅ Flip calculator "Bought Single" crashed with `UnboundLocalError: DEFAULT_PACKS_PER_BOX` (2026-04-16) — config import was mid-function, making the default-value lookup on line 274 reference a local bound later; moved import before first use
- ✅ `$1.49 LOW` on $695 cards (2026-04-16) — `_handle_history` now drops prices below 15% of overall median, killing junk listings (lot sales, proxies, damaged) that polluted the LOW summary stat
- ✅ "Moonbreon" in trending list (2026-04-16) — it was a collector nickname for Umbreon VMAX Alt Art, not a scrapable card name; replaced the entire hardcoded list with real data from new `/api?action=movers` endpoint
- ✅ eBay scraper returning 0 results (2026-04-16) — selector changed from `li.s-card` to `li.s-item`; title/price/date selectors updated for 2024+ DOM
- ✅ 1Y chart sparse/empty (2026-04-16) — TCGPlayer now supplements when <15 sales and days>=90 (raw grade only — graded queries excluded to avoid market-price contamination)
- ✅ Box/pack flip math wrong (2026-04-16) — `method=box` now divides entered cost by packs (`DEFAULT_PACKS_PER_BOX = 36`)
- ✅ Card images blocked by CSP (2026-04-16) — added pokemontcg.io to remotePatterns + img-src
- ✅ Date range tabs not updating chart (2026-04-16) — cache key now includes days; hard cutoff in `_handle_history`
- ✅ PriceCharting 2026 HTML redesign breaking scraper — fixed div.completed-auctions-used parsing
- ✅ pokemontcg.io meta returning empty for number variants — name-only search + number proximity ranking

---

## Active Blockers
- No monetization layer (fully free, no conversion path)
- No auth — can't build personalized features (saved cards sync'd across devices, alerts). Supabase is wired up for caching but not yet for auth
- ~~Scraper fragility — PriceCharting HTML can change silently~~ ✅ **RESOLVED session 11 (H-1.8)** — drift canary lands in `tests/canary.py`; GitHub workflow still `workflow_dispatch` until baseline seeded
- ~~CORS wildcard on `/api`~~ ✅ **RESOLVED session 11 (H-1.6)** — allowlist resolver in `api/index.py`
- No rate limiting on `/api` — unauth'd scraping is abuse-prone. Fix prompt **H-1.9** still queued; lives in `handoffpack-www` and needs Upstash signup, deferred until abuse signal appears
- Test coverage on scraper.py improved but still incomplete — critical paths covered, edge cases remain
- No signal backtesting — can't validate accuracy claims
- ~~L2 Supabase cache pending Vercel activation~~ ✅ **RESOLVED session 7** — env vars added, deployment ready, write-through confirmed with real rows in `holo.sales_cache`

---

## Roadmap

| ID | Task | Status | Priority |
|----|------|--------|----------|
| H-1.2 | Telegram bot interface | Not started | High |
| H-1.3 | Tournament meta-shift signal (Limitless TCG) | Not started | High |
| H-1.4 | Pull rate database for accurate sealed EV | Not started | Medium |
| H-1.5 | Backtesting harness for signal validation | Not started | Medium |
| H-1.9 | Edge rate limiting (Upstash + Next.js middleware) | Queued (deferred) | Medium |
| H-1.10 | Multi-source adapter platform — foundation + free adapters | 🚧 Partial (session 11) | High |
| H-1.10a | Registry audit wiring + parity test + docs + meta_signal | ✅ Complete (session 12) | Medium |
| H-1.10a-ui | Data provenance panel on card detail (handoffpack-www) | Queued | Low |
| H-2.0 | Auth layer + personalization | Not started | High |
| H-2.1 | Price alerts (email / push) | Not started | Medium |
| H-2.2 | Monetization / freemium tier | Not started | High |
| H-3.0 | Card shop / B2B buylist integration | Not started | Low |

---

## Key Files

| File | Purpose |
|------|---------|
| `api/index.py` | Vercel serverless entrypoint, all route handlers |
| `pokequant/scraper.py` | PriceCharting + eBay + TCGPlayer data fetching |
| `pokequant/signals/dip_detector.py` | SMA + RSI signal engine |
| `pokequant/comps/generator.py` | Decay-weighted comp |
| `pokequant/comps/calculator.py` | Box EV math |
| `pokequant/bulk/optimizer.py` | Bulk liquidation logic |
| `config.py` | All numeric thresholds (single source of truth) |
| `tests/` | pytest suite — 57 tests pass (scraper suite added); core modules ~79% coverage |
| `docs/state/session.md` | Detailed session history |
| `docs/signal-quality-research.md` | Signal enhancement research (RSI, meta, seasonality) |
| `docs/ux-recommendation.md` | UX research — recommends Telegram bot |
| `handoffpack-www/components/lab/holo/HoloPage.tsx` | Full frontend (~1780 lines) — Pokeball SVG, useCardTheme, TopMovers marquee |
| `handoffpack-www/app/lab/holo/layout.tsx` | Holo-specific layout: Orbitron + Space Grotesk + Press Start 2P fonts |
| `handoffpack-www/app/api/holo/route.ts` | Next.js proxy to Python API |
