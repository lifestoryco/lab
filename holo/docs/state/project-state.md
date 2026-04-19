# Holo — Project State

*Keep this file current. The advisory board reads it at the start of every meeting.*

---

## What Holo Is

A Pokémon TCG price intelligence tool for serious traders and investors.
Live at: **https://www.handoffpack.com/lab/holo**

Target user: Someone trying to turn card trading into real income — not casual collectors.
They want an unfair data advantage, not another price lookup.

---

## What Was Just Done (2026-04-19 — session 6)

### Top Movers scroll with images + Recently Viewed row ✅ COMPLETE

**Modified:** `handoffpack-www/components/lab/holo/HoloPage.tsx` — added `useRecentlyViewed` hook, `RecentlyViewed` component, `RecentItem` interface, `onMetaReady` callback in `CardDetail`

**Commits:** `db396fb` feat(lab/holo): Top Movers scroll with images + Recently Viewed row

**What was built:**
- `useRecentlyViewed()` hook — localStorage persistence under `holo.recently_viewed`, stores up to 10 `{ card, name, image_small }` items newest-first, dedupes on re-visit
- `RecentlyViewed` component — drag-scrollable horizontal row at the bottom of the home screen (below TopMovers). Violet accent (`border-violet-400`, `shadow-[0_0_28px_rgba(167,139,250,0.5)]`) to visually distinguish from TopMovers' gold. Hidden when list is empty.
- `onMetaReady` prop on `CardDetail` — fires via `useEffect` when `history?.meta` loads. Root `HoloPage` captures it and calls `recentlyViewed.add({ card, name, image_small })`. Images are always real card art.
- TopMovers card images were already present (from session 4); this session confirmed the scroll + image UX is intact.

**Decisions:**
- **Violet accent for Recently Viewed** — gold is taken by TopMovers/brand. Violet reads as "history/memory" vs. gold "active signal" — clear visual hierarchy.
- **Capture via `onMetaReady` not on `setCardName`** — wait for meta so we always store the real `image_small`, never a blank placeholder. The ref-stable pattern (`onMetaReadyRef.current`) avoids stale closure issues across range changes.
- **Max 10, dedupes on re-visit** — visiting the same card twice just promotes it to the top, not a duplicate entry.

---

## What Was Just Done (2026-04-19 — session 7)

### Supabase L2 cache fully activated in production ✅ COMPLETE

Finished the activation that was pending from session 5. All three steps applied via Chrome automation:

1. **Service role key** — grabbed from Supabase Dashboard → Settings → API (Legacy tab).
2. **Vercel env vars** added to the **holo** project (not handoffpack-www):
   - `SUPABASE_URL = https://ufilszeczpxxggxqaedd.supabase.co` — Production + Preview
   - `SUPABASE_SERVICE_ROLE_KEY` — Production + Preview, marked **Sensitive** so Vercel masks the value in the dashboard post-save
3. **Redeployed** the holo Vercel project. Deployment ready in 25s.

**Verification:**
- `curl https://holo-lac-three.vercel.app/api?action=history&card=Mew%20VMAX%20114&grade=raw&days=30` returned 86 sales (first hit 5.65s cold scrape; second hit 191ms)
- Queried `holo.sales_cache` in Supabase SQL editor — 5 Mew VMAX ebay rows visible with real prices ($15.00, $22.50, $13.99, $10.81, $8.99), all keyed under `card_slug = mew-vmax-114`. Write-through from production confirmed.

**End-to-end pipeline is live:**
```
request → L1 /tmp sqlite → L2 Supabase holo.sales_cache → live PC/eBay scrape
          (warm instances)  (cross-instance shared)      (cold-only fallback)
write-through populates L1 + L2 on every live scrape
```

**Commits:** None (no code change — this session was pure activation).

**Decisions:**
- **Marked SUPABASE_SERVICE_ROLE_KEY as Sensitive** — Vercel masks the value in the dashboard after save. Slightly less convenient for debugging but the correct default for a bypass-RLS secret.
- **Scoped to Production + Preview only** — skipped Development so local `vercel dev` testing doesn't pollute production cache.
- **Legacy anon/service_role API keys** chosen over the new `sb_secret_*` format — `supabase_cache.py` was designed and docs reference the legacy key format, and both paths authenticate the same way against PostgREST. Switching to new-format keys is a future migration (separate rotation story).

**Known cosmetic issue (not a blocker):** Vercel log stream doesn't show the `logger.info("supabase L2 HIT …")` messages because Python's default logging level is WARNING. This is purely a visibility gap — the cache is working (verified via Supabase rows). If we want log visibility, a one-line `logging.basicConfig(level=logging.INFO)` at the top of `api/index.py` would surface them. Filed for a later polish pass.

---

## What Was Just Done (2026-04-17 — session 5)

### Supabase L2 cache for scraped sales (dark-launched + DB migration applied) ✅ SUPERSEDED BY SESSION 7

Built a persistent, cross-instance L2 cache for scraped TCG sales data in the handoffpack Supabase project. Code is shipped dark (feature-gated) and the database migration is applied + API-exposed; final activation pending the operator adding env vars to Vercel.

**Pipeline after activation:**
```
request → L1 /tmp sqlite (<1ms) → L2 Supabase (50-150ms) → live scrape
write-through populates both L1 and L2 after a live scrape
```

**New files:**
- `db/migrations/001_holo_sales_cache.sql` — idempotent DDL. Creates `holo` schema (never `public`), two tables (`sales_cache` + `scrape_runs`), indexes, RLS-on-with-zero-policies (service_role-only access), explicit revokes on anon/authenticated/public
- `pokequant/supabase_cache.py` — PostgREST client module. 3-4s timeouts, try/except around every call, fire-and-forget writes, deterministic sha1 sale_id for dedup. `is_enabled()` returns false when env vars unset → whole module no-ops
- `docs/supabase-setup.md` — 4-step activation guide + verification queries + revert procedure

**Modified:**
- `pokequant/scraper.py` — `fetch_sales` wired with L2 check between L1 miss and live scrape, plus write-through after live scrape completes. Graceful fallback on any Supabase failure

**Applied to Supabase (handoffpack2 project) via Chrome automation:**
- Ran `001_holo_sales_cache.sql` in SQL editor — "Success. No rows returned"
- Verified: `holo.sales_cache` and `holo.scrape_runs` exist with `rls_enabled = true`
- Added `holo` to Data API → Exposed schemas (alongside `public`, `graphql_public`)
- `public` schema untouched; handoffpack data fully isolated

**Commits:** `7baf6dc` feat: Supabase L2 cache for scraped sales (dark-launched, feature-gated)

**Decisions:**
- **Dedicated `holo` schema, not `public`:** full isolation from handoffpack data. A stray prefix typo can't collide with existing tables.
- **RLS enabled + zero policies:** defence in depth. Even if someone ever accidentally exposed a query via the anon key, there's literally no policy that grants read/write. Only service_role (bypasses RLS) can touch the cache.
- **Feature-gated on env vars:** code ships dark. No behaviour change until the operator adds `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` to Vercel. Zero risk to production.
- **Short timeouts + try/except everywhere:** a Supabase outage must NEVER kill a user request. Supabase being slow → fall through to live scrape, no 500s.
- **Fire-and-forget writes:** user request returns before L2 write lands. Write failures are logged at DEBUG only.
- **Idempotent sale_id (sha1 of source+url+price+date):** repeated scrapes of the same underlying sale dedupe cleanly via Postgres UNIQUE + `Prefer: resolution=ignore-duplicates`.

**To activate (operator doing tomorrow):**
1. Supabase Dashboard → Settings → API → copy `service_role` key
2. Vercel → **holo** project (not handoffpack-www) → env vars:
   - `SUPABASE_URL = https://ufilszeczpxxggxqaedd.supabase.co`
   - `SUPABASE_SERVICE_ROLE_KEY = <key>`
   - Scope: Production + Preview only
3. Redeploy

**Free-tier economics:** ~200 bytes/row; 1M sales ≈ 200 MB. Well under the 500 MB DB limit. No new bandwidth costs on Supabase free tier.

---

## What Was Just Done (2026-04-17 — session 4)

### Pokédex overlay, card search autocomplete, perf pass, bulletproof audit fixes, Fraunces typography, multi-color takeover ✅ COMPLETE

**The biggest session to date.** A long coordinated sprint: built the Pokédex overlay, added industry-standard search autocomplete, shipped a performance overhaul (parallel movers + HTTP session keep-alive + WAL sqlite + slim meta payloads + edge-runtime proxy + theme cache), audited the full product with 4 specialist reviews, retired the "vibe-coded" Orbitron/Press Start 2P typography in favour of Fraunces + Inter Tight + JetBrains Mono, and cranked the card-color takeover to full-viewport 3.5× with a multi-hue palette and smooth crossfade.

**New features:**
- **Pokédex side-panel overlay** (`/api?action=pokedex`) — full-screen on card-tap. Two-column desktop / stacked mobile. Set logo + species banner (genus, generation, legendary/mythical chips), HP/height/weight strip, 18-type color map with weakness/resistance pills, 6-row base-stats bar chart, species flavor text quote block, TCG abilities, attacks with colored energy-cost circles + accent damage, retreat row, TCGPlayer link. Merges pokemontcg.io (TCG card data) + pokeapi.co (species data), 30-day sqlite cache.
- **Card search autocomplete** (`/api?action=search`) — WAI-ARIA 1.2 combobox, 250ms debounce, AbortController cancels stale fetches. Dropdown with 40×56 thumbnail + name·number + caps meta line (Set · Series · Year · Rarity), `<mark>` on matched substring. ArrowUp/Down wrap, Enter selects or falls back to raw submit, Escape/Tab/click-outside close. Server ranks by exact-number > exact name > starts-with > contains > release date desc. 6-hour sqlite cache.
- **Top Movers drag + modal** — replaced the 40s CSS marquee with native drag-scroll + pointer handlers, gentle rAF auto-scroll that pauses on interaction, new "View all" button opens portal modal grid of all loaded movers.
- **Mobile bottom nav** — fixed 4-tab bar (Overview/Sales/Flip/Grade) with `safe-area-inset-bottom` padding, 56px tap targets.

**Performance:**
- Module-level `requests.Session()` with HTTPAdapter pooling — all pokemontcg.io / PokeAPI calls reuse keep-alive connections (~100–300ms per call saved).
- `_lookup_card_meta(rich=False)` slim `select=` fieldset for list/search callers; rich reserved for detail+pokedex. Separate cache rows per payload shape. pageSize cut from 25→10.
- `_handle_movers` parallelized via `ThreadPoolExecutor(max_workers=8)` + 10-min in-process memo. Cold ~12s → ~2s, warm <100ms.
- SQLite set to `journal_mode=WAL, synchronous=NORMAL, temp_store=MEMORY` at init.
- Per-action `Cache-Control` presets threaded through `do_GET` (movers/meta/pokedex cacheable at edge with long SWR).
- Next.js proxy (`app/api/holo/route.ts`) moved to edge runtime, streams upstream body instead of reparse+reserialize, passes `Cache-Control` through.
- Module-level `THEME_CACHE: Map<url, CardTheme>` — revisiting a card skips the canvas decode.

**Audit-driven bulletproofing:**
- **[CRITICAL]** `pokequant/scraper.py`: `_resolve_cache_db()` defaults to `/tmp` when `VERCEL` env is set; `_init_cache_db` no longer prints to stdout or `sys.exit` (was killing the serverless handler).
- **[HIGH]** `api/index.py` generic exception handler now logs traceback to stderr + returns `{error: "Internal error", trace_id}` instead of leaking `str(exc)`.
- **[HIGH]** Flip `margin_pct` fixed to `profit / cost_basis * 100` (return on cost, not revenue).
- **[HIGH]** Flip `break_even` now recomputes shipping tier when the calculated break-even falls below `SHIPPING_VALUE_THRESHOLD`.
- **[MEDIUM]** `_handle_search` stops caching error responses (was poisoning the 6-hour cache on transient upstream failures).
- **[MEDIUM]** `useCardTheme` now has an `onerror` handler that falls back to `DEFAULT_THEME` (prevents stale theme from a prior card).

**Pokédex / image-mismatch fix:**
- Users reported the Pokédex overlay showing a different Miraidon ex printing than the detail page. Root cause: the overlay re-searched by name only.
- New `_lookup_card_by_id()` hits `pokemontcg.io /v2/cards/{id}` for an exact lookup, bypasses name-match scoring.
- New `_shape_card_meta()` helper — shared by name-search and id-lookup paths so both produce identical wire payloads.
- `/api?action=pokedex` prefers `?id=` over `?card=`; frontend now passes `meta.id`.

**Pokédex overlay transparency fix (desktop):**
- Scrim was `bg-black/92`, which isn't in Tailwind's default opacity scale and silently compiled to no background. Replaced with inline `rgba(6,6,8,0.92)`. Mobile unchanged.

**Typography overhaul — retire Orbitron + Press Start 2P:**
- **Fraunces** (variable, opsz + SOFT + WONK axes) → display + labels + HOLO wordmark (Black italic, 5xl, tight tracking, gold gradient preserved)
- **Inter Tight** (variable) → body/stats/tabs
- **JetBrains Mono** (variable) → prices + numerics
- Semantic aliases in `layout.tsx` keep the 51 existing inline font-var refs working without touching HoloPage.tsx

**Card-color takeover — 3.5× + multi-hue + smooth crossfade:**
- `useCardTheme` extracts top 3 dominant hues (primary + secondary + tertiary) with angular separation; weighting by `chroma² × √luma` so bright saturated pixels (Miraidon's yellow) beat high-coverage-but-duller pixels (Miraidon's cyan body). Boosted saturation (accent 92%, bgDeep 88%) with warm-band luma bumps so yellow reads as yellow, not olive.
- 7 takeover layers weave all three hues: primary top, secondary bottom, tertiary bottom-right corner, plus a slow-rotating **conic gradient (120s/rev)** for subtle foil iridescence. Layer 1 flood holds `bgDeep` for 45% of viewport — no fade to black — so colour is visible at every scroll position. Global purity wash at 60% alpha. Respects `prefers-reduced-motion`.
- Whole takeover set lives in one keyed wrapper div with `opacity 0→1` transitioning 900ms cubic-bezier — card switches crossfade instead of flipping.

**Ultra Ball theme (session 3 work preserved and polished):** SVG pokeball redesigned as Ultra Ball (gold + black H-stripes + red pinstripe accent); brand wordmark floats + hover-spin.

**Files modified:**
- `api/index.py` (+700 lines net) — pokedex/search/movers endpoints, session pooling, WAL, shared meta shaper, id lookup
- `pokequant/scraper.py` — safe /tmp fallback, no sys.exit from init
- `handoffpack-www/components/lab/holo/HoloPage.tsx` (~1000 lines net) — Lightbox→Pokedex, autocomplete combobox, multi-hue theme, takeover layers, font refs
- `handoffpack-www/app/lab/holo/layout.tsx` — new font stack + semantic aliases
- `handoffpack-www/app/api/holo/route.ts` — edge runtime, pass-through streaming

**Commits (13 this session):** `a7cc2fc` (flip unbound-local) · `0144481` (ultra-ball theme) · `dc6672d` (state) · `5be7f22` (takeover covers full page) · `f72d164` (pokedex backend) · `ec3c512` (pokedex frontend) · `4e979f6` (search backend) · `95f8189` (search combobox) · `444e0c3` (api perf) · `7435afd` (frontend perf + theme cache) · `cbfcbb7` (3.5× takeover + z-index + onerror) · `b74744e` (takeover no-fade + translucent panels) · `8101d47` (pokedex id lookup) · `89eb6a6` (Fraunces + multi-color + smooth fade + overlay scrim) · `3634367` (scraper /tmp fallback)

**Decisions:**
- **Pokedex data sourcing:** merge pokemontcg.io + pokeapi.co rather than pick one. pokemontcg.io has the TCG-specific fields (attacks, abilities, energy costs, artist, rarity); pokeapi.co has the species data (genus, flavor text, base stats, dimensions). Both cached in `/tmp` sqlite with long TTLs so cold-start isn't punished.
- **Pin pokedex by id:** the name-based scorer is fine for initial lookups but unreliable when a card has 5–10 printings. Once we have an id in hand (from history), passing it through eliminates the problem class entirely.
- **Retire retro pixel font:** Press Start 2P was fun but read as amateur for a trader tool. Fraunces with opsz=144 + SOFT + WONK is distinctive enough to own the brand without being cutesy.
- **Crossfade via key + opacity transition:** animating gradients directly doesn't interpolate in any browser. Keying the wrapper on `theme.hue` re-mounts the layers with fresh opacity, and a 900ms opacity transition gives a soft crossfade for free. Simpler than `@property`-registered custom properties.
- **Parallel movers with ThreadPoolExecutor:** Vercel Python supports threads fine; the big worry was concurrent sqlite writes. WAL + short per-task connections handle that.

---

## What Was Just Done (2026-04-16 — session 3)

### Ultra Ball theme + full-bleed card takeover + draggable movers + mobile bottom nav + flip bug fix ✅ COMPLETE

**Modified:** `api/index.py` — fixed `UnboundLocalError` on `DEFAULT_PACKS_PER_BOX` in `_handle_flip`. The config import happened mid-function, so Python treated the name as a local throughout, crashing the default value expression on line 274 whenever `?packs=` wasn't explicitly passed. This broke the web-UI "Bought Single" flip flow. Moved the import before first use; removed duplicate from later import line.
**Modified (handoffpack-www):** `components/lab/holo/HoloPage.tsx` — large coordinated redesign (+394/-116):
  - `Pokeball` component redesigned as Ultra Ball (gold radial gradient top, black H-stripes flaring from button, red pinstripe accent on equator, premium highlight streak, scoped gradient IDs via `React.useId()`)
  - Brand header: bigger (size 56) ball with `holo-float` animation + `holo-spin-once` on hover, gold wordmark gradient, warmer black radial page background
  - `useCardTheme` extended with `bgBase` / `bgDeep` for detail-page takeover
  - Card detail view: full-bleed stacked gradient layers driven by card palette — the ENTIRE page background pulls from the card, not just the top glow. Frosted glass panels upgraded to blur 22–24px + saturate 1.4–1.5 with stronger edge highlights and accent-tinted shadow rings
  - `TopMovers`: replaced 40s CSS marquee with native `overflow-x-auto` scroller + pointer-drag handlers + gentle rAF auto-scroll that pauses on interaction. New "View all" button opens `MoversModal` (portal, Escape to close, responsive grid of all loaded movers with image/name/price/delta)
  - Mobile bottom nav: fixed 4-icon tab bar (Overview/Sales/Flip/Grade) with `safe-area-inset-bottom` padding and 56px tap targets; top tabs hidden on mobile (`hidden sm:flex`), replaced by a small current-tab pill
  - Readability pass: `zinc-500/600` → `zinc-300/400` body text, min-h-44px tap targets, stronger panel borders  
**Commits:** `a7cc2fc` fix(api): flip DEFAULT_PACKS_PER_BOX unbound-local | `0144481` (handoffpack-www) feat(lab/holo): ultra-ball theme + full-bleed takeover + draggable movers + mobile bottom nav  
**Decisions:** Native scroll + pointer events for the movers carousel instead of a drag library — less bundle weight, respects browser fling momentum. Ultra Ball chosen over classic red: yellow/black/white palette gives a premium "serious trader" vibe that the classic red pokeball didn't, while the red pinstripe preserves a nod to the original. Full-bleed takeover only on detail page — lookup screen stays on the base dark theme so it feels like a distinct "portal" into the card.

---

## Previous Sessions

- **Pokéball branding + card-driven palette + Top Movers endpoint (2026-04-16 s2):** `/api?action=movers` endpoint ranks ~12 liquid cards by `|change_pct|` over 7D with history outlier floor at 15% of median. Inline SVG Pokéball component, `useCardTheme` canvas-sampling hook, ambient top glow, auto-scroll marquee. Commits `1a4ec7c`, `1f23e27`.
- **Session tooling + cleanup (2026-04-16 s1):** `end.sh` handoffpack-www push block, `DEFAULT_PACKS_PER_BOX` config constant, TCGPlayer supplement restricted to raw grade, 57-test scraper suite landed. Commits `55026f4` · `be4c914` · `91f5788` · `d98ec47` · `cad01eb`.
- **Full UX overhaul + multi-source scraping fixes (2026-04-16):** Orbitron/Space Grotesk fonts (later replaced), card hero background, lightbox (later rebuilt as Pokédex overlay), glassmorphism panels, canvas card accent (`68644c9`); eBay selector fix, TCGPlayer sparse supplement, box flip math ÷ packs, `?action=meta` (`1da815d`).
- **Session workflow + earlier fixes (2026-04-16):** Card images CSP, date range tab cache collision fix (`24c0542`), /start-session, /end-session, /run-task, /prompt-builder, /sync, /alpha-squad, /code-review commands (`fe5b7a5`, `caef365`, `58d14a1`).

---

## Current Status (as of 2026-04-17 — session 5)

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
- Scraper fragility — PriceCharting HTML can change silently; no monitoring
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
