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

### Card image CSP fix ✅ COMPLETE
**Modified:** `handoffpack-www/next.config.js` — added `images.pokemontcg.io` to `remotePatterns` + CSP `img-src`; switched `<img>` → `<Image>` in `CardHeader`
**Commits:** `64a2ccd` — fix(holo): unblock pokemon card images blocked by CSP

### Date range tabs fix ✅ COMPLETE
**Modified:** `pokequant/scraper.py` — cache key now includes `days` (`{source}_{grade}_{days}d`); `api/index.py` — hard cutoff filter in `_handle_history`
**Commits:** `24c0542` — fix(holo): chart range tabs now correctly change graph and price delta

### Session workflow commands ✅ COMPLETE
**New files:** `.claude/commands/sync.md`, `start-session.md`, `run-task.md`, `prompt-builder.md`, `end-session.md` — full development loop  
**New files:** `.claude/commands/alpha-squad.md` — 7-member advisory board  
**New files:** `.claude/commands/code-review.md` — 4-agent parallel code review  
**New files:** `scripts/start.sh`, `scripts/end.sh` — env health check + push validation  
**New files:** `docs/advisory-board/charter.md`, `meetings/README.md` — board infrastructure  
**New files:** `docs/state/project-state.md` — this file  
**Modified:** `CLAUDE.md` — documented all commands + task naming convention  
**Commits:** `fe5b7a5`, `caef365`, `58d14a1`

---

## Current Status (as of 2026-04-16)

### Phase
Post-MVP web launch. Pre-monetization. Actively iterating.

### What's Live
- Bloomberg-style 5-tab dashboard (Overview, Sales, Flip, Grade It?)
- Card image via pokemontcg.io (fixed CSP blocking issue 2026-04-16)
- Date range tabs: 7D / 30D / 90D / 1Y sparkline (fixed cache collision bug 2026-04-16)
- Grade selector: Raw / PSA 9 / PSA 10
- Hero price + delta chip + Hi/Lo/Open stats
- Trade signal (STRONG BUY → STRONG SELL) with RSI-14
- Grade comparison table with grading premium %
- Sales feed (30 most recent completed sales with source links)
- Flip P&L calculator (cost basis → net profit after fees + shipping)
- Grade It? ROI calculator (PSA/CGC grading EV with 6 service tiers)
- Watchlist (localStorage persistence)
- Source attribution links (PriceCharting, eBay, pokemontcg.io)
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
- ✅ Card images blocked by CSP (2026-04-16) — added pokemontcg.io to remotePatterns + img-src
- ✅ Date range tabs not updating chart (2026-04-16) — cache key now includes days; hard cutoff in _handle_history
- ✅ PriceCharting 2026 HTML redesign breaking scraper — fixed div.completed-auctions-used parsing
- ✅ pokemontcg.io meta returning empty for number variants — name-only search + number proximity ranking

---

## Active Blockers
- No monetization layer (fully free, no conversion path)
- No auth — can't build personalized features (saved cards sync'd across devices, alerts)
- Scraper fragility — PriceCharting HTML can change silently; no monitoring
- Low test coverage on scraper.py (~31% overall)
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
| `tests/` | pytest suite — 40 tests, ~79% coverage on core modules |
| `docs/state/session.md` | Detailed session history |
| `docs/signal-quality-research.md` | Signal enhancement research (RSI, meta, seasonality) |
| `docs/ux-recommendation.md` | UX research — recommends Telegram bot |
| `handoffpack-www/components/lab/holo/HoloPage.tsx` | Full frontend (~1000 lines) |
| `handoffpack-www/app/api/holo/route.ts` | Next.js proxy to Python API |
