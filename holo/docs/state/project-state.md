# Holo — Project State

*Keep this file current. The advisory board reads it at the start of every meeting.*

---

## What Holo Is

A Pokémon TCG price intelligence tool for serious traders and investors.
Live at: **https://www.handoffpack.com/lab/holo**

Target user: Someone trying to turn card trading into real income — not casual collectors.
They want an unfair data advantage, not another price lookup.

---

## What Was Just Done (2026-04-16)

### Pokéball branding + card-driven palette + Top Movers endpoint ✅ COMPLETE

**Modified:** `api/index.py` — new `_handle_movers` (`/api?action=movers`) ranks a curated universe of ~12 liquid cards by `|change_pct|` over 7D; `_handle_history` now applies an outlier floor at 15% of overall median to drop junk listings (lot sales/proxies/damaged) that were polluting LOW stats  
**Modified:** `handoffpack-www/app/lab/holo/layout.tsx` — Press Start 2P font loaded as `--font-press-start`  
**Modified:** `handoffpack-www/components/lab/holo/HoloPage.tsx` — new `<Pokeball>` inline SVG component (currentColor + optional spin); `useCardTheme` replaces `useCardAccent`, returning full palette `{accent, glow, deep, hue, ready}` biased toward the most-saturated pixel (Pikachu→yellow, Charizard→orange, Umbreon→purple); ambient card-driven top-of-viewport glow; Press Start 2P wordmark + pokeball mark in brand header; red-glow lookup screen with decorative pokeball; `TopMovers` component replaces hardcoded `TrendingCarousel` — fetches `/api?action=movers`, auto-scrolling 40s marquee with pause on hover/touch, emerald/red ▲▼ chips, fade masks on both sides; range tabs now solid accent background when active; hero price renamed "Latest Price" (semantically accurate — value IS always the latest sale)  
**Commits:** `1a4ec7c` — feat(holo): add /api?action=movers endpoint + history outlier filter | `1f23e27` (handoffpack-www) — feat(lab/holo): Press Start 2P + pokeball mark + card-driven palette + auto-scroll top movers  
**Decisions:** Inline SVG pokeball instead of PNG asset — scales crisp at any size, tintable via `currentColor`, no file dependency. Movers endpoint reuses existing `fetch_sales` cache per-card, so each card is a cache hit on subsequent calls (no N+1 cold-fetch problem). "Moonbreon" removed from the trending list — it's a collector nickname for Umbreon VMAX Alt Art, not a scrapable card name.

---

## What Was Just Done (2026-04-16)

### Session tooling + cleanup ✅ COMPLETE

**Modified:** `scripts/end.sh` — added handoffpack-www push block; `HANDOFFPACK_DIR` variable at top for easy path changes  
**Modified:** `config.py` — added `DEFAULT_PACKS_PER_BOX = 36` constant  
**Modified:** `api/index.py` — replaced hardcoded `"36"` with `DEFAULT_PACKS_PER_BOX` in both flip and EV handlers  
**Modified:** `pokequant/scraper.py` — restrict TCGPlayer supplement to `grade == "raw"` (graded queries were getting contaminated market prices)  
**New files:** `tests/test_scraper.py` — 57-test scraper suite (was untracked from previous session)  
**Commits:** `55026f4` · `be4c914` · `91f5788` · `d98ec47` · `cad01eb`  
**Decisions:** `end.sh` uses `git -C $DIR` pattern so it never changes working directory — safe even if holo push fails mid-way.

---

## Previous Sessions

- **Full UX overhaul + multi-source scraping fixes (2026-04-16):** Orbitron/Space Grotesk fonts, card hero background, lightbox, glassmorphism panels, dynamic card accent via canvas sampling (`68644c9`); eBay selector fix (`s-card`→`s-item`), TCGPlayer sparse supplement, box flip math ÷ packs, `?action=meta` endpoint (`1da815d`).
- **Session workflow + earlier fixes (2026-04-16):** Card images CSP fix (`64a2ccd`), date range tab cache collision fix (`24c0542`), /start-session, /end-session, /run-task, /prompt-builder, /sync, /alpha-squad, /code-review commands built (`fe5b7a5`, `caef365`, `58d14a1`).

---

## Current Status (as of 2026-04-16 — session 2)

### Phase
Post-MVP web launch. Pre-monetization. Actively iterating.

### What's Live
- Bloomberg-style 5-tab dashboard (Overview, Sales, Flip, Grade It?)
- **Card hero UI**: blurred card art background, 140×196px centered card image, click-to-lightbox
- **Card-driven palette**: `useCardTheme` extracts full `{accent, glow, deep}` from card art (biased toward most-saturated pixel); ambient top-of-viewport glow + tinted card halo + tinted panel borders
- **Top Movers marquee**: auto-scrolling 40s loop, pause on hover/touch, ▲▼% chips; data from `/api?action=movers`
- **Inline SVG Pokéball**: reusable component tinted via `currentColor`, used in brand mark + lookup screen decoration
- **Orbitron + Press Start 2P + Space Grotesk** trio via next/font/google (Press Start 2P reserved for wordmark + small retro labels)
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
- No auth — can't build personalized features (saved cards sync'd across devices, alerts)
- Scraper fragility — PriceCharting HTML can change silently; no monitoring
- Test coverage on scraper.py improved but still incomplete — critical paths covered, edge cases remain
- No signal backtesting — can't validate accuracy claims

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
