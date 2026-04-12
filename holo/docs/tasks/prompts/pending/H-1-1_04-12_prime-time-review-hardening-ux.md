---
id: H-1.1
title: Prime-Time Review — Hardening, UX Overhaul & Signal Quality
created: 2026-04-12
status: pending
steps: 11
risk_gates: 4
complexity: High
layer: All
---

# H-1.1 — Prime-Time Review: Hardening, UX Overhaul & Signal Quality

> **Model:** Claude Opus 4.6 (`claude-opus-4-6`)
> **Context budget:** Load CLAUDE.md + the exact files named in each step. Skip everything else until that step.
> **Mandate:** You are authorized to search the web, research open-source repos, and propose architectural enhancements. This is not a maintenance pass — it is a full vision review. Fix what's broken, enhance what's weak, and elevate the system to genuinely world-class.
> **Operator:** A Pokémon TCG collector/trader using Holo as their daily price intelligence tool. Right now they can only use it through Claude Code CLI. That is not the final product.

---

## WHO YOU ARE BUILDING FOR

The Holo user is a Pokémon TCG trader — not an engineer. They flip singles, rip boxes, manage bulk, and want to know whether a card is worth buying, holding, or selling *right now*. What they need:

- **An instant answer**: "Should I buy this card?" — answered in seconds with real market data, not vibes.
- **A price source they trust**: comp weighted by recency, not some stale 90-day average.
- **A flip number they can act on**: exact profit after eBay fees and shipping, not a spreadsheet exercise.
- **Access beyond Claude Code**: a Telegram bot, a web link, or at minimum something they can share — right now the tool dies if they close their terminal.
- **An EV check before cracking a box**: one command that tells them "this box is -23% EV, hold sealed."

**Your mandate on UX:** After completing the bug fixes, conduct a full UX audit from the trader's perspective. Research and recommend the best hosting + display option (Telegram bot, FastAPI + HTML served locally, Streamlit Cloud, Discord bot, Vercel, or something else entirely). Implement or stub the winning approach. The Claude Code slash command interface is excellent for developers but is not the final product for a user who wants to check a price mid-trade-show.

---

## WHAT WAS BUILT (Full Context)

Holo is a production-grade Pokémon TCG trading assistant:

- **6 slash commands**: `/holo-setup`, `/holo-buy-sell`, `/holo-price-check`, `/holo-box-value`, `/holo-bulk-sell`, `/holo-flip`, `/holo`
- **5 analysis modules** in `pokequant/`:
  - `ingestion/normalizer.py` — IQR outlier filtering + data coercion
  - `signals/dip_detector.py` — SMA-7 / SMA-30 + volume surge signal engine
  - `ev/calculator.py` — sealed box expected value with pull rate math
  - `comps/generator.py` — exponential-decay weighted market comp (λ=0.3)
  - `bulk/optimizer.py` — bulk liquidation optimizer with USPS weight model
- **`pokequant/analyze.py`** — dispatcher for all 5 subcommands (signal / ev / bulk / comp / flip)
- **`pokequant/scraper.py`** — PriceCharting.com scraper + pokemontcg.io API with 24h SQLite cache
- **`config.py`** — all tunable thresholds
- **`data/db/history.db`** — local SQLite cache (auto-created)
- **0 tests** — no test files exist at all; `tests/` contains only `__init__.py`

---

## Step 0 — Load Context

Read in this exact order:
1. `CLAUDE.md` (already loaded — skip if present)
2. `config.py` (full file)
3. `pokequant/analyze.py` (full file)
4. `pokequant/scraper.py` (full file)

Confirm you have read all four before proceeding.

---

## Step 1 — CRITICAL: Build the Test Suite

**The codebase has zero test coverage. No test has ever run against any of these modules.**

### Read
- `pokequant/ingestion/normalizer.py`
- `pokequant/signals/dip_detector.py`
- `pokequant/ev/calculator.py`
- `pokequant/comps/generator.py`
- `pokequant/bulk/optimizer.py`

### Problem
`tests/__init__.py` is empty. There are no test files. Every change made so far has had no regression safety net. The most dangerous gaps:

- No test that `ingest_card()` rejects a missing `sale_id` or negative price
- No test that `latest_signal()` returns `SIGNAL_INSUFFICIENT_DATA` on a single-row input
- No test that `calculate_box_ev()` rejects a `packs_per_box` of 0
- No test that `generate_comp_from_list()` raises on an empty list
- No test that the IQR filter doesn't crash on a 2-row dataset
- No test that `analyze_bulk_lot()` returns `should_liquidate=False` when below the threshold

### Fix
Create the following test files. Use `pytest` with `pytest-cov` for coverage. Keep tests fast (no HTTP calls — mock the scraper).

**`tests/conftest.py`**
Shared fixtures:
- `minimal_sales_df` — a 10-row sales DataFrame with all required columns
- `sample_box_data` — a valid `box_data` dict for `calculate_box_ev()`
- `sample_inventory` — `{"Common": 500, "Uncommon": 200, "Reverse Holo": 50}`
- `sample_sales_list` — a list of 12 sale dicts in the scraper output format

**`tests/test_normalizer.py`**
- `test_extract_raw_dataframe_valid` — happy path
- `test_extract_raw_dataframe_missing_card_id` — raises `KeyError`
- `test_extract_raw_dataframe_missing_sales_key` — raises `KeyError`
- `test_apply_iqr_filter_removes_outliers` — injects a $999 record; verify it is removed
- `test_apply_iqr_filter_skips_iqr_on_small_dataset` — 3 rows → skips IQR step, returns all 3
- `test_apply_iqr_filter_raises_on_empty` — all prices outside hard bounds → `ValueError`
- `test_normalize_sorts_ascending_and_dedupes` — out-of-order dates → sorted; duplicate `sale_id` → deduped

**`tests/test_signals.py`**
- `test_generate_signals_returns_annotated_df` — output has `sma_7`, `sma_30`, `signal` columns
- `test_generate_signals_raises_on_empty_df` — `ValueError`
- `test_latest_signal_strong_buy` — inject data where current price is 20% below SMA-30 + volume surge → `SIGNAL_STRONG_BUY`
- `test_latest_signal_strong_sell` — inject data where price is 35% above SMA-30 → `SIGNAL_STRONG_SELL`
- `test_latest_signal_hold` — price within ±10% of SMA-30 → `SIGNAL_HOLD`
- `test_latest_signal_insufficient_data` — 1-row input → `SIGNAL_INSUFFICIENT_DATA` or raises `ValueError`
- `test_classify_row_uses_config_thresholds` — verify that `DIP_THRESHOLD` and `VOLUME_SURGE_FACTOR` from `config.py` are actually used, not hardcoded overrides

**`tests/test_ev_calculator.py`**
- `test_calculate_box_ev_positive_ev` — manually crafted high-value box → `REC_RIP`
- `test_calculate_box_ev_negative_ev` — low-value box → `REC_HOLD`
- `test_calculate_box_ev_missing_key_raises` — missing `packs_per_box` → `KeyError`
- `test_calculate_box_ev_zero_packs_raises` — `packs_per_box=0` → `ValueError`
- `test_parse_pull_rate_fraction` — `"1/36"` → `0.02778` (±0.0001)
- `test_parse_pull_rate_float_string` — `"0.05"` → `0.05`
- `test_parse_pull_rate_invalid_raises` — `"not/a/rate"` → `ValueError`
- `test_compute_tier_ev_empty_cards_returns_zero` — tier with empty card list → `tier_ev == 0.0`

**`tests/test_comp_generator.py`**
- `test_generate_comp_from_list_happy_path` — 12 sales → `cmc`, `confidence`, `volatility_score` are all populated
- `test_generate_comp_from_list_empty_raises` — empty list → `ValueError`
- `test_generate_comp_from_list_missing_key_raises` — sale missing `price` → `KeyError`
- `test_generate_comp_single_sale_volatility_unknown` — 1 sale → `volatility_score == "UNKNOWN"`, `confidence == "LOW"`
- `test_assign_decay_weights_newest_highest` — weight at index 0 > weight at index 1 (always)
- `test_assess_confidence_high` — 8 sales, spread 7 days → `"HIGH"`
- `test_assess_confidence_low` — 2 sales, spread 45 days → `"LOW"`

**`tests/test_bulk_optimizer.py`**
- `test_analyze_bulk_lot_liquidate` — large inventory above threshold → `should_liquidate=True`
- `test_analyze_bulk_lot_hold` — tiny inventory → `should_liquidate=False`
- `test_analyze_bulk_lot_empty_inventory` — all zeroes → `should_liquidate=False`, `recommendation` mentions "empty"
- `test_analyze_bulk_lot_negative_count_raises` — `{"Common": -1}` → `ValueError`
- `test_analyze_bulk_lot_unknown_card_type_treated_as_zero` — `{"Holo GX": 50}` → no crash, warns, $0 subtotal
- `test_compute_shipping_cost_rounds_to_cents` — verify `shipping_cost` is a multiple of $0.01

> ✅ **Verify:**
> ```bash
> python3 -m pytest tests/ -v --tb=short
> ```
> All new tests must pass. Target: ≥ 70% line coverage on `pokequant/`.
> ```bash
> python3 -m pytest tests/ --cov=pokequant --cov-report=term-missing -q
> ```

> ⚠️ **Risk gate:** Do not add `try/except` blocks inside tests to make them "pass" — the tests must actually validate behavior. A test that never fails is worse than no test.

---

## Step 2 — Fix Hardcoded Constants (Config Consolidation)

### Read
- `pokequant/analyze.py` (already loaded) — lines 492–499
- `pokequant/signals/dip_detector.py` (already loaded) — line 68
- `pokequant/bulk/optimizer.py` — line 47
- `config.py` (already loaded)

### Problems
There are 6 magic numbers scattered outside `config.py`. This means tuning the system requires editing logic files, and there's no single source of truth for operational parameters.

**In `pokequant/analyze.py` lines 492–499:**
```python
_PLATFORM_FEE_RATE: float = 0.13          # Not in config
_SHIPPING_BMWT: float = 4.00              # Not in config
_SHIPPING_PWE: float = 1.00               # Not in config
_THIN_MARGIN_THRESHOLD_PCT: float = 20.0  # Not in config
```

**In `pokequant/signals/dip_detector.py` line 68:**
```python
_STRONG_SELL_THRESHOLD = 0.30  # Hardcoded — should mirror DIP_THRESHOLD pattern in config
```

**In `pokequant/bulk/optimizer.py` line 47:**
```python
_PACKAGING_OVERHEAD_USD: float = 2.00  # Not in config
```

### Fix
Add the following to `config.py` under a new `# Module 6 — Flip Calculator` section:
```python
# ---------------------------------------------------------------------------
# Module 6 — Flip Calculator (analyze.py cmd_flip)
# ---------------------------------------------------------------------------
PLATFORM_FEE_RATE: float = 0.13           # Combined eBay + TCGPlayer seller fee
SHIPPING_COST_BMWT: float = 4.00          # Bubble Mailer with Tracking (≥ $20 cards)
SHIPPING_COST_PWE: float = 1.00           # Plain White Envelope (< $20 cards)
FLIP_THIN_MARGIN_THRESHOLD_PCT: float = 20.0  # Below this margin % → "HOLD" verdict
```

Add to the `# Module 2 — Signal Engine` section in `config.py`:
```python
STRONG_SELL_THRESHOLD: float = 0.30       # 30% above SMA-30 → STRONG SELL
```

Add to the `# Module 4 — Bulk Optimizer` section in `config.py`:
```python
BULK_PACKAGING_OVERHEAD_USD: float = 2.00  # Fixed packaging cost (envelope + label)
```

Then update all three files to import from `config` and remove the module-level constants.

In `analyze.py`, change the flip math section to use:
```python
from config import (
    PLATFORM_FEE_RATE,
    SHIPPING_COST_BMWT,
    SHIPPING_COST_PWE,
    FLIP_THIN_MARGIN_THRESHOLD_PCT,
    SHIPPING_VALUE_THRESHOLD,
)
```

In `dip_detector.py`, add `STRONG_SELL_THRESHOLD` to the existing config import and remove the `_STRONG_SELL_THRESHOLD` local constant.

In `bulk/optimizer.py`, add `BULK_PACKAGING_OVERHEAD_USD` to the config import and update `_PACKAGING_OVERHEAD_USD` to reference it (or remove the alias entirely).

> ✅ **Verify:**
> ```bash
> python3 -m py_compile pokequant/analyze.py pokequant/signals/dip_detector.py pokequant/bulk/optimizer.py config.py
> python3 -m pytest tests/ -q
> ```

---

## Step 3 — Fix HTTP Error Handling in Scraper

### Read
- `pokequant/scraper.py` (already loaded) — specifically `_get()` at line ~207

### Problem
`_get()` handles only HTTP 429 (rate limit) with a single 5-second retry. All other failure modes are unhandled:

- **HTTP 403 (Forbidden):** PriceCharting or TCGPlayer may WAF-block the scraper. Currently raises a generic `requests.exceptions.HTTPError` with no user-facing guidance.
- **HTTP 5xx (Server Error):** A transient server error propagates as an unhandled exception to the caller, which then returns `[]` with no explanation.
- **Connection timeout:** The default 10s timeout triggers `requests.exceptions.Timeout` which propagates uncaught through `fetch_sales()` to the command file, resulting in a raw Python traceback in the Claude output.
- **Single retry only:** One retry after a 429 with no exponential backoff. If PriceCharting is briefly rate-limiting heavily, the second attempt fails immediately.

### Fix
Rewrite `_get()` to handle all failure cases explicitly:

```python
def _get(url: str, timeout: int = 10, retries: int = 3) -> requests.Response:
    """HTTP GET with UA rotation, exponential backoff, and explicit error classification."""
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            headers = {
                "User-Agent": random.choice(_USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "DNT": "1",
            }
            resp = requests.get(url, headers=headers, timeout=timeout)

            if resp.status_code == 429:
                wait = 5 * (2 ** attempt)  # 5s, 10s, 20s
                logger.warning("Rate limited by %s — backing off %ds (attempt %d/%d).",
                               url, wait, attempt + 1, retries)
                time.sleep(wait)
                last_exc = None
                continue

            if resp.status_code == 403:
                raise ValueError(
                    f"Access denied by {url} (HTTP 403). "
                    "The site may be blocking automated requests. "
                    "Try again in a few minutes or check your User-Agent."
                )

            if resp.status_code >= 500:
                logger.warning("Server error %d from %s — retrying (attempt %d/%d).",
                               resp.status_code, url, attempt + 1, retries)
                time.sleep(3 * (attempt + 1))
                last_exc = ValueError(f"Server error {resp.status_code} from {url}")
                continue

            resp.raise_for_status()
            return resp

        except requests.exceptions.Timeout:
            logger.warning("Timeout after %ds fetching %s (attempt %d/%d).",
                           timeout, url, attempt + 1, retries)
            last_exc = ValueError(
                f"Request to {url} timed out after {timeout}s. "
                "The site may be slow. Try again shortly."
            )
            time.sleep(2 * (attempt + 1))

        except requests.exceptions.ConnectionError as exc:
            logger.warning("Connection error fetching %s: %s (attempt %d/%d).",
                           url, exc, attempt + 1, retries)
            last_exc = ValueError(
                f"Could not connect to {url}. Check your internet connection."
            )
            time.sleep(2 * (attempt + 1))

    raise last_exc or ValueError(f"Failed to fetch {url} after {retries} attempts.")
```

> ✅ **Verify:**
> ```bash
> python3 -m py_compile pokequant/scraper.py
> python3 -m pytest tests/ -q
> ```

> ⚠️ **Risk gate:** The `_get()` function is the single HTTP entry point for all PriceCharting and TCGPlayer scraping. Any change here affects every data fetch. Confirm `fetch_sales()` and `fetch_tcgplayer_sales()` still handle `ValueError` from `_get()` — they should catch and log it, then return `[]` rather than letting it propagate to the command file as a raw traceback.

---

## Step 4 — Fix Timezone-Naive Date Handling

### Read
- `pokequant/ingestion/normalizer.py` — line ~180 (`pd.to_datetime(sale["date"])`)
- `pokequant/signals/dip_detector.py` (already loaded) — `_aggregate_daily()` line ~165 and `pd.date_range()` line ~179

### Problem
Date handling is timezone-naive throughout the ingestion and signal pipeline. Two specific issues:

**4A: `normalizer.py` — naive `pd.to_datetime()`**
Line ~180: `date = pd.to_datetime(sale["date"])` produces a tz-naive timestamp. If a sale record from PriceCharting says `"2024-04-12"` and another from TCGPlayer says `"2024-04-12T23:00:00-07:00"`, they will be compared as naive timestamps. The TCGPlayer record would be placed at `2024-04-12 23:00` while the date `2024-04-13 06:00 UTC` for the same sale would land in the wrong SMA window.

**4B: `dip_detector.py` — `pd.date_range()` produces tz-naive index**
Line ~179: `pd.date_range(start=..., end=..., freq="D")` produces a tz-naive DatetimeIndex. If the `daily.index` is tz-aware but the reindex range is tz-naive (or vice versa), pandas raises `TypeError: Cannot compare tz-naive and tz-aware` at runtime when reindexing.

### Fix
**4A:** In `normalizer.py`, change the date coercion line to:
```python
date = pd.to_datetime(sale["date"], utc=True)
```
This normalizes all incoming dates to UTC regardless of the source timezone. A naive date string like `"2024-04-12"` is treated as UTC; a tz-aware string like `"2024-04-12T23:00:00-07:00"` is converted to UTC.

**4B:** In `dip_detector.py:_aggregate_daily()`, the groupby normalizer already uses `.dt.normalize()` which truncates to midnight. Ensure the reindex range matches timezone:
```python
full_range = pd.date_range(
    start=daily.index.min(), end=daily.index.max(), freq="D", tz="UTC"
)
```

> ✅ **Verify:**
> ```bash
> python3 -m py_compile pokequant/ingestion/normalizer.py pokequant/signals/dip_detector.py
> python3 -m pytest tests/test_normalizer.py tests/test_signals.py -q
> ```
> Existing tests for date handling must pass after this change. Add a test `test_extract_raw_dataframe_mixed_tz_dates` in `test_normalizer.py` that provides one UTC date string and one offset-aware date string and verifies they both parse without error.

---

## Step 5 — Fix Comp Edge Cases: Single-Sale Confidence

### Read
- `pokequant/comps/generator.py` (already loaded) — `_assess_confidence()`, `_assess_volatility()`, `generate_comp()`

### Problems

**5A: Single-sale comp shows "LOW" confidence but no explicit warning**
When only 1 sale exists, `_assess_confidence()` correctly returns `"LOW"`. However `_assess_volatility()` returns `("UNKNOWN", 0.0)` — and the `CompResult.cmc` is still computed and returned as a valid number with no flag that it's based on a single data point.

The command files (`holo-price-check.md`, `holo-flip.md`) render confidence without special-casing `sales_used == 1`. A user sees "Confidence: LOW · 1 sale" and may think LOW means "slightly uncertain" when it actually means "single observation — statistically meaningless comp."

**5B: `cmc_vs_mean_pct` is always `0.0` for a single sale**
With 1 sale, `cmc == simple_mean`, so the delta is exactly 0%. The comp output shows `→ Stable` as the trend even though there's no trend to detect. This is misleading.

### Fix

**5A:** Add an `insufficient_data_warning` field to `CompResult`:
```python
@dataclass
class CompResult:
    # ... existing fields ...
    insufficient_data_warning: str = ""  # Non-empty when sales_used < 3
```

In `generate_comp()`, after computing `sales_used`:
```python
insufficient_data_warning = ""
if len(sale_points) == 1:
    insufficient_data_warning = (
        "Only 1 sale found — this comp is a single data point, not a market average. "
        "Treat with caution."
    )
elif len(sale_points) == 2:
    insufficient_data_warning = (
        "Only 2 sales found — comp is directionally useful but not statistically reliable."
    )
```

Include `insufficient_data_warning` in the returned `CompResult`.

**5B:** In `cmd_comp()` and `cmd_flip()` in `analyze.py`, add `insufficient_data_warning` to the output JSON:
```python
"insufficient_data_warning": result.insufficient_data_warning,
```

Update the command files (`.claude/commands/holo-price-check.md` and `.claude/commands/holo-flip.md`) to display this warning prominently if it is non-empty — place it directly below the confidence line, formatted as:
```
⚠  [insufficient_data_warning]
```

> ✅ **Verify:**
> ```bash
> python3 -m pytest tests/test_comp_generator.py -q
> ```
> The test `test_generate_comp_single_sale_volatility_unknown` from Step 1 must pass and additionally assert that `insufficient_data_warning != ""`.

---

## Step 6 — Fix Observability and Silent Output Issues

### Read
- `pokequant/analyze.py` (already loaded) — `cmd_bulk()` lines ~400–421
- `pokequant/scraper.py` (already loaded) — `fetch_sales()` error return path

### Fix all of these:

**6A: Placeholder GitHub URL in bulk output (`analyze.py` line ~413)**
```python
"sources": [
    {
        "label": "Holo bulk rates",
        "url": "https://github.com/",   # ← This is a stub, not a real URL
        ...
    }
]
```
The `url` field points to `https://github.com/` — a useless placeholder. Either:
- Remove the `url` field from the bulk sources dict entirely (preferred — bulk rates are internal config, not a web source), or
- Point it to the actual TCGPlayer / CFB bulk buylist page if one exists

Fix: Remove the `url` field. The `note` field already explains the rates. Source attribution for internal config-driven rates does not need a URL.

**6B: `fetch_sales()` returns `{}` with "error" key but callers silently swallow it**
In `scraper.py`, when the scraper finds no results after all fallback strategies, it returns a dict like `{"error": "No listings found", "card": card_name, "count": 0}`. The command files check for `"error"` in the JSON and stop — that's correct. But `cmd_flip()` in `analyze.py` handles this at step 1, then proceeds to step 2 (comp generation) using the same `sales_result`. Verify that `cmd_flip()` actually exits when `sales_result` is an error dict — it does (line ~529), but add a log statement at `logger.warning` level so failed fetches are visible in the log, not just silent exits.

**6C: P&L / debug errors logged at `DEBUG` instead of `WARNING`**
Throughout `analyze.py`, any exception caught in the `except Exception as exc:` blocks at the bottom of each `cmd_*` function logs at `logger.error` — which is correct. But the individual inner `try/except` blocks in `cmd_signal()` log failures at `logger.error` with `exc_info=True` — verify this is consistent and no failure path uses `logger.debug` for an error condition. Audit every `except` block in `analyze.py` and confirm all exception paths log at `WARNING` or higher.

> ✅ **Verify:**
> ```bash
> python3 -m py_compile pokequant/analyze.py pokequant/scraper.py
> python3 -m pytest tests/ -q
> ```

---

## Step 7 — UX Audit: Hosting & Display Beyond Claude Code CLI

### Context
The current interface is exclusively Claude Code slash commands. The user types `/holo-buy-sell Charizard V` in a terminal. This is excellent for power users, but:
- It requires Claude Code to be running
- It produces output only in the Claude Code conversation
- It cannot be accessed from a phone mid-trade-show
- It cannot be shared with another collector ("check this link")
- There is no persistent history of past queries

### Research mandate — search the web
Use web search to investigate the following options. For each, find real examples, open-source implementations, and cost/complexity tradeoffs:

1. **Telegram Bot** — Python `python-telegram-bot` library, inline commands
   - Search: "python telegram bot price alert trading" GitHub
   - Search: "python-telegram-bot polling webhook example 2024"
   - Could `/holo-buy-sell Charizard V` become a Telegram command `/buy Charizard V`?
   - What does the output card look like in Telegram Markdown?

2. **FastAPI + single HTML file** — minimal web server served from the same process
   - Search: "fastapi sqlite json api minimal example python"
   - AlphaBot already exposes JSON from `analyze.py` — could a thin FastAPI layer serve this?
   - A single `dashboard.html` with `fetch("/api/signal?card=Charizard+V")` could work from any browser
   - Cost: $0 (local) or ~$5/mo on a VPS

3. **Streamlit** — Python-native, deployable to Streamlit Cloud free tier
   - Search: "streamlit pokemon tcg price dashboard sqlite" GitHub
   - Streamlit can read from `data/db/history.db` directly (SQLite)
   - Zero infrastructure — `streamlit run app.py` just works
   - Free tier on Streamlit Community Cloud for public repos

4. **Discord Bot** — slash commands in Discord
   - Search: "discord.py slash commands trading bot 2024"
   - TCG community lives on Discord — a `/price charizard-v` command in a Discord server would be immediately useful
   - Can share comps with other collectors in the same channel

5. **Vercel + Next.js or static HTML**
   - Search: "vercel static site pokemon card price dashboard"
   - AlphaBot's JSON API could be deployed serverless; analyze.py logic could become a Vercel function
   - Cost: $0 on Hobby tier

### Deliverable for this step
Write `docs/ux-recommendation.md` containing:

1. **Recommended approach for a TCG trader** — one clear winner with justification (consider: mobile-first, zero setup, TCG community fit, free tier availability)
2. **Runner-up** — in case the winner has a deployment blocker
3. **What Holo needs to expose** — which `analyze.py` subcommands need a web/bot interface, what input/output format changes are needed, what AlphaBot's `data/db/history.db` can provide for a history view
4. **Implementation sketch** — 20–50 lines of actual Python showing how to wire the winning approach to the existing `analyze.py` dispatcher
5. **Cost** — free tier vs paid at "one active user" and "10 active users" scale

Base your recommendation on the user profile: TCG trader, phone-first when at events, wants to share comps with friends, no interest in running a server.

> ⚠️ **Do not implement the full interface yet** — that is H-1.2 or later. The goal here is a researched recommendation document with enough detail that a future session can implement it without re-researching.

---

## Step 8 — Signal Quality Research

### Mandate
You are authorized to search the web and academic sources for evidence-based enhancements to Holo's signal quality. Every suggestion must be grounded in published research, open-source implementation, or quantified historical performance on TCG or collectibles markets — not equity market analogues applied blindly.

Search and synthesize findings on the following:

**8A: TCG-specific price signals**

Search:
- "pokemon tcg card price prediction machine learning github"
- "TCG price signal RSI collectibles market momentum"
- "pokemon card price spike detection tournament meta impact"
- "collectibles price seasonality pattern analysis"
- GitHub: `pkmn-prices`, `pokedata`, `pokemon-prices-analysis`, `tcg-market-analysis`
- "card game secondary market price dynamics academic research"

For each of Holo's 5 analysis modules, assess:
- Is there a published improvement to the core signal logic for TCG markets specifically?
- Is there a feature or indicator that addresses TCG-specific dynamics (tournament meta, set rotation, reprint risk)?
- What is the typical alpha decay rate for TCG price signals vs equity signals?

**8B: Data source improvements**

Search:
- "PriceCharting API alternatives pokemon card prices"
- "TCGPlayer API python scraping free tier 2024"
- "eBay completed listings pokemon card price API python"
- "pokemon card price history database open source"

Questions to answer:
- Is there a better data source than PriceCharting for raw card price history?
- Does the TCGPlayer API provide volume data that PriceCharting doesn't?
- Can eBay completed listings (not just active listings) be reliably scraped for a better sold-price signal?
- Should Holo add a Reddit r/pkmntcg sentiment signal as an early warning for price movements?

**8C: EV and comp model improvements**

Search:
- "box EV calculator pokemon accuracy backtested"
- "exponential decay pricing model collectibles recency bias"
- "sealed product arbitrage pokemon tcg evidence"
- "pull rate variance pokemon set simulation"

Questions to answer:
- Is the exponential decay lambda of 0.3 optimal for TCG prices, or does evidence suggest a different value?
- Is the current pull rate table in `analyze.py` accurate for modern sets (2023–2025)?
- Should the EV calculator model pull rate *variance* (not just expected value) to give a risk range?

**8D: Open-source repos to study**

Find and summarize the most valuable open-source projects for:
- TCG-specific price signal generation
- Collectibles market backtesting infrastructure
- Pull rate / EV calculation implementations
- Community-maintained pull rate databases

### Deliverable
Write `docs/signal-quality-research.md` containing:
1. **Top 3 highest-evidence signal enhancements** — what to change, in which file, with citations or links
2. **Data source recommendation** — keep PriceCharting + pokemontcg.io, or add/replace a source?
3. **EV model recommendation** — add pull rate variance / risk range display?
4. **Top 3 open-source repos** Holo's future development should study
5. **One new signal idea** not currently in Holo — grounded in TCG market evidence, with enough detail for a future prompt to implement it in ≤ 100 lines

---

## Step 9 — Implement the Top Enhancement from Step 8

Based on your research in Step 8, select the **single highest-impact, evidence-backed enhancement** that:
- Can be implemented in ≤ 100 lines of Python
- Operates on data Holo already fetches (no new scraping targets)
- Has clear, measurable impact on signal quality or comp accuracy
- Does not break any existing command's output format (additions are fine; removals are not)

Implement it. Write tests. If it is a new signal component, add it to `generate_signals()` output and expose it in the relevant `cmd_*()` output JSON. Document it in `CLAUDE.md`'s Key Files section if it creates a new file.

> ✅ **Verify:**
> ```bash
> python3 -m py_compile $(find . -name "*.py" -not -path "./.venv/*" -not -path "./__pycache__/*")
> python3 -m pytest tests/ -q
> ```
> All tests must pass. New tests for the enhancement must be included.

> ⚠️ **Risk gate:** If the enhancement touches the signal pipeline, confirm:
> - `cmd_signal()` in `analyze.py` still outputs a valid JSON object with at minimum `signal`, `price`, `sma7`, `sma30`, `sources`
> - The buy-sell command files (`.claude/commands/holo-buy-sell.md`) still work with the new output
> - The new field is clearly named and its value is always present (never `undefined` / missing key)

---

## Step 10 — Improve Entry Point Error UX

### Read
- `.claude/commands/holo-buy-sell.md`
- `.claude/commands/holo-price-check.md`
- `.claude/commands/holo-flip.md`

### Problem
When `pokequant/analyze.py` is run with a bad argument (e.g., missing `--data` on the `signal` subcommand), argparse prints a raw usage message to stderr and exits with code 2. The Claude Code command files capture stdout but not stderr — so the user sees nothing, or an empty result, with no explanation.

Additionally, `pokequant/scraper.py` called from a command file with a bad card name returns `{"error": "..."}` in stdout — the command files check for this and show a user-friendly message. But if the scraper's SQLite cache database is corrupted or the `data/db/` directory doesn't exist, the import-time `_init_cache_db()` call raises an exception before any output is produced, and the command fails silently.

### Fix
**10A: Cache init defensive guard**
In `scraper.py:_init_cache_db()`, wrap the entire body in a try/except:
```python
def _init_cache_db() -> None:
    global _CACHE_READY
    if _CACHE_READY:
        return
    try:
        _CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(_CACHE_DB) as conn:
            # ... existing CREATE TABLE statements ...
        _CACHE_READY = True
    except Exception as exc:
        # Log to stderr — stdout must stay clean for JSON protocol
        print(
            json.dumps({"error": f"Cache database init failed: {exc}. "
                                 f"Try deleting {_CACHE_DB} and re-running."}),
            file=sys.stdout,  # Intentional — command files read stdout
        )
        sys.exit(1)
```

**10B: Startup banner for `analyze.py` when run as `__main__`**
Replace the bare `args.func(args)` call at the bottom of `analyze.py` with:
```python
if __name__ == "__main__":
    parser = build_parser()
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        print(json.dumps({"error": "No subcommand provided. Use: signal, ev, bulk, comp, or flip."}))
        sys.exit(1)
    args = parser.parse_args()
    log_level = logging.DEBUG if getattr(args, "verbose", False) else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    args.func(args)
```

> ✅ **Verify:**
> ```bash
> python3 -m py_compile pokequant/scraper.py pokequant/analyze.py
> python3 pokequant/analyze.py 2>/dev/null; echo "Exit: $?"
> # Should print JSON error to stdout and exit 1, not a raw Python traceback
> ```

---

## Step 11 — Final Verification Checklist & Documentation Update

### Run the full test suite
```bash
python3 -m pytest tests/ -v --tb=short 2>&1 | tee /tmp/holo_test_results.txt
```

All tests must pass. If any fail, fix them before continuing.

### Compile check
```bash
python3 -m py_compile $(find . -name "*.py" -not -path "./.venv/*" -not -path "./__pycache__/*")
```

### Manual integrity checklist — confirm each item:

- [ ] **Config single source of truth:** `grep -r "_PLATFORM_FEE_RATE\|_SHIPPING_BMWT\|_STRONG_SELL_THRESHOLD\|_PACKAGING_OVERHEAD" pokequant/` returns no results (all moved to config.py).
- [ ] **No hardcoded numbers in flip logic:** `pokequant/analyze.py` imports `PLATFORM_FEE_RATE`, `SHIPPING_COST_BMWT`, `SHIPPING_COST_PWE`, `FLIP_THIN_MARGIN_THRESHOLD_PCT` from config.
- [ ] **HTTP errors are classified:** `pokequant/scraper.py:_get()` handles 403, 5xx, and Timeout explicitly — no bare `raise_for_status()` without a wrapper.
- [ ] **Dates are UTC-aware:** `pokequant/ingestion/normalizer.py` uses `pd.to_datetime(..., utc=True)`. `dip_detector.py:pd.date_range()` includes `tz="UTC"`.
- [ ] **Single-sale warning present:** `CompResult.insufficient_data_warning` is non-empty when `sales_used == 1` or `2`. The `cmd_comp()` and `cmd_flip()` outputs include this field.
- [ ] **Bulk placeholder URL removed:** `analyze.py:cmd_bulk()` sources dict has no `"url": "https://github.com/"` entry.
- [ ] **Tests pass:** `python3 -m pytest tests/ -q` exits 0. Coverage ≥ 70% on `pokequant/`.
- [ ] **Docs written:** `docs/ux-recommendation.md` and `docs/signal-quality-research.md` exist and are non-trivial (each ≥ 400 words with actual research findings).

### Create session state file
Create `docs/state/session.md` (this is the first one — establish the format for future sessions):

```markdown
# Holo — Session State

## Last Session: H-1.1 (2026-04-12)

### What Was Just Done

#### H-1.1: Prime-Time Hardening + UX Research ✅ DONE

CRITICAL:
- Built full test suite from zero — [N] tests across 5 modules, [N]% coverage

HIGH fixes:
- Moved all hardcoded constants to config.py (6 magic numbers consolidated)
- Fixed HTTP error handling in scraper._get() — handles 403, 5xx, Timeout with retry backoff
- Fixed timezone-naive date parsing — UTC-enforced throughout ingestion + signal pipeline

MEDIUM fixes:
- Added CompResult.insufficient_data_warning for 1–2 sale comps
- Removed placeholder https://github.com/ URL from bulk sources output
- Verified all except blocks in analyze.py log at WARNING or higher

ENTRY POINT:
- scraper._init_cache_db() wrapped in try/except with JSON error to stdout
- analyze.py no-args invocation prints JSON error instead of raw traceback

UX:
- docs/ux-recommendation.md written with winning deployment approach for TCG trader
- docs/signal-quality-research.md written with evidence-based signal enhancements

Enhancement:
- [Name of Step 9 enhancement] implemented in [file]

Tests: [N]/[N] passing · Coverage: [N]%

## What's Next

1. H-1.2 — Implement winning UX interface (per ux-recommendation.md)
2. H-1.3 — Implement top 2 remaining signal enhancements from signal-quality-research.md
3. H-1.4 — Pull rate database: build a maintained pull rate table for modern sets
4. H-1.5 — Backtesting harness: validate signal accuracy on historical PriceCharting data
```

### Commit

```bash
git add -A
git commit -m "$(cat <<'EOF'
fix: prime-time hardening — tests, config consolidation, HTTP robustness, UTC dates

- Build full test suite from zero (6 test files, N tests, N% coverage)
- Move 6 hardcoded constants to config.py (fees, thresholds, overrides)
- Fix scraper._get() to handle 403, 5xx, Timeout with exponential backoff
- Fix timezone-naive date parsing (pd.to_datetime utc=True throughout)
- Add CompResult.insufficient_data_warning for single-sale edge cases
- Remove placeholder github.com URL from bulk sources output
- Add scraper cache init guard (JSON error to stdout on failure)
- Add docs/ux-recommendation.md for post-CLI deployment approach
- Add docs/signal-quality-research.md with evidence-based enhancements
- Implement [Step 9 enhancement name] in [file]
- Create docs/state/session.md (first session state file)

 Authored by: tealizard @ HandoffPack
EOF
)"
```

---

## Rules for Execution

1. **Execute steps in order.** Each step must pass its verification before the next begins.
2. **Never skip a risk gate.** If a risk gate check fails, fix it before continuing.
3. **Commit after Step 11 only.** Do not commit partial work mid-session.
4. **Web searches are mandatory in Steps 7 and 8.** Do not skip them or summarize from memory — Holo's signal quality depends on real evidence about TCG market dynamics.
5. **Do not invent APIs.** Every function you call or import must exist in the codebase or be explicitly imported from a verified library.
6. **The UX document is as important as the bug fixes.** The tool is useless to a card trader who can't reach it from their phone at a trade show.
7. **Tests must actually test behavior.** A test that wraps everything in `try/except: pass` is worse than no test. Every test must be capable of failing.
8. **Config is the single source of truth.** If a number appears in two places, one of them is wrong. All tunable parameters live in `config.py`.
