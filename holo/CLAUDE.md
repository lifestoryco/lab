# Holo — Claude Code Context

## What is this?

Holo is a Pokémon TCG trading assistant. It fetches real market data and
runs quantitative analysis to answer questions like:
- Should I buy this card right now?
- Is this sealed box worth ripping?
- What is this card actually worth?
- Should I flip this card I pulled?
- Should I ship my bulk yet?

## First-Time Setup

If this is a fresh clone, run `/holo-setup` first. That command will:
1. Check Python 3.11+
2. Create a virtual environment at `.venv/`
3. Install all dependencies
4. Verify live data is reachable
5. Confirm everything is ready

## Analysis Commands

| Command | Usage | What it does |
|---------|-------|--------------|
| `/holo-setup` | `/holo-setup` | First-time installer. Run once. |
| `/holo-buy-sell` | `/holo-buy-sell Charizard V` | Buy/Sell/Hold signal based on 30-day price trend and volume |
| `/holo-price-check` | `/holo-price-check Umbreon VMAX` | Decay-weighted market comp + volatility score |
| `/holo-box-value` | `/holo-box-value Obsidian Flames 149.99` | Sealed box EV vs. what you paid |
| `/holo-bulk-sell` | `/holo-bulk-sell` | Should you ship your bulk cards yet? |
| `/holo-flip` | `/holo-flip "Charizard V" 4.50 pack` | Exact profit after fees and shipping |
| `/holo` | `/holo should I buy Charizard V?` | Ask anything in plain English |

## Session Workflow Commands

| Command | Usage | What it does |
|---------|-------|--------------|
| `/start-session` | `/start-session` | Health check + brief on last session and what's next |
| `/sync` | `/sync` | Rebase onto origin/main before starting work |
| `/prompt-builder` | `/prompt-builder H-1.2` | Research + generate a self-contained task prompt |
| `/run-task` | `/run-task H-1.2` | Execute a pending task prompt step-by-step |
| `/end-session` | `/end-session` | Verify, commit, update state, push |
| `/docs-update` | `/docs-update H-1.2` | Mark tasks done, move prompts to complete/, update roadmap |
| `/code-review` | `/code-review [--fix]` | 4-agent parallel code review (Security, Logic, Arch, UX) |
| `/alpha-squad` | `/alpha-squad [topic]` | Convene the 7-member advisory board for strategic decisions |

## Task Naming Convention

Tasks follow the `H-X.Y` format:
- `H-1.x` — Phase 1: Core hardening and signal quality
- `H-2.x` — Phase 2: Auth, personalization, monetization
- `H-3.x` — Phase 3: B2B and integrations

Prompt files: `docs/tasks/prompts/pending/H-X-Y_{MM-DD}_{slug}.md`
Completed:    `docs/tasks/prompts/complete/H-X-Y_{MM-DD}_{slug}.md`

## How the System Works

```
User runs a /holo-* command
        │
        ▼
Claude reads .claude/commands/holo-*.md
        │
        ├── pokequant/scraper.py     ← Fetches live data (PriceCharting / pokemontcg.io)
        │   └── data/db/history.db  ← SQLite cache (24h TTL, auto-created)
        │
        ├── pokequant/analyze.py     ← Runs math (signal/ev/bulk/comp/flip)
        │   └── pokequant/           ← Pure-function modules (IQR, SMA, EV, comp)
        │
        └── Claude renders output    ← Bloomberg-style terminal card + plain English verdict
```

## Key Files

| File | Purpose |
|------|---------|
| `config.py` | All tunable thresholds (SMA windows, fee rates, shipping tiers) |
| `pokequant/scraper.py` | Live data fetcher with SQLite cache + anti-blocking |
| `pokequant/analyze.py` | Analysis dispatcher — outputs compact JSON |
| `pokequant/signals/dip_detector.py` | SMA + volume + RSI-14 signal engine |
| `pokequant/ev/calculator.py` | Sealed box EV math |
| `pokequant/comps/generator.py` | Exponential-decay weighted comp |
| `pokequant/bulk/optimizer.py` | Bulk liquidation calculator |
| `.claude/commands/` | Claude Code slash command definitions |

## Data Sources

Two code paths exist in parallel:

### Legacy cascade (default — `HOLO_USE_REGISTRY=0`)

Linear if/elif in `pokequant/scraper.py::_fetch_sales_legacy`. Data sources:

- **PriceCharting.com** — historical sold listings (primary for signals + comps)
- **eBay HTML** — supplements raw-grade with recent completed auctions
- **TCGPlayer** — redirect hack + infinite-api for market estimates
- **pokemontcg.io** — card meta + final-fallback synthetic prices

### Multi-source registry (opt-in — `HOLO_USE_REGISTRY=1`)

Unified adapter framework in `pokequant/sources/`. Spec:
[docs/architecture/sources.md](docs/architecture/sources.md). Adapters:

| Adapter | Feature flag | Credentials | Status |
|---|---|---|---|
| `psa_pop` | `HOLO_ADAPTER_PSA_POP` | none | **LIVE** — powers `_handle_grade_roi` pop-based probabilities |
| `130point` | `HOLO_ADAPTER_130POINT` | none | **LIVE** — sale-comp cross-validator |
| `limitless` | `HOLO_ADAPTER_LIMITLESS` | none | Stub — activate with H-1.3 |
| `goldin` | `HOLO_ADAPTER_GOLDIN` | none | Stub — endpoint URLs pending verification |
| `bgs_pop` | `HOLO_ADAPTER_BGS_POP` | `BECKETT_SESSION_COOKIE` | Stub — session-auth required |
| `cardmarket` | `HOLO_ADAPTER_CARDMARKET` | `CARDMARKET_APP_TOKEN` + 3 more | Stub — OAuth 1.0 (EUR) |
| `ebay_api` | `HOLO_ADAPTER_EBAY_API` | `EBAY_APP_ID`, `EBAY_CERT_ID` | Stub — OAuth 2.0 approval |
| `tcgplayer_pro` | `HOLO_ADAPTER_TCGPLAYER_PRO` | `TCGPLAYER_PUBLIC_KEY`, `_PRIVATE_KEY` | Stub — partner approval |
| `card_ladder` | `HOLO_ADAPTER_CARD_LADDER` | `CARDLADDER_API_KEY` | Stub — paid ($99/mo), blocks on spend approval |

Health surface: `GET /api?action=health`. Parity test (gate for flipping
the registry flag on in production):
`HOLO_RUN_PARITY=1 pytest tests/test_fetch_sales_parity.py -v`.

## Requirements

Python 3.11+ · pandas · numpy · requests · beautifulsoup4 · python-dateutil

Install: `pip install -r requirements.txt` (or let `/holo-setup` handle it)
