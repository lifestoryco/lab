# Holo — Session State

## Last Session: H-1.1 (2026-04-15)

### What Was Just Done

#### H-1.1: Prime-Time Hardening + UX Research + Signal Enhancement

CRITICAL:
- Built full test suite from zero — 40 tests across 6 test files, 5 modules covered (normalizer 61%, signals 79%, ev 79%, comps 81%, bulk 82%)

HIGH fixes:
- Moved all hardcoded constants to config.py (6 magic numbers consolidated: PLATFORM_FEE_RATE, SHIPPING_COST_BMWT, SHIPPING_COST_PWE, FLIP_THIN_MARGIN_THRESHOLD_PCT, STRONG_SELL_THRESHOLD, BULK_PACKAGING_OVERHEAD_USD)
- Fixed HTTP error handling in scraper._get() — handles 403, 5xx, Timeout with exponential backoff (3 retries, doubling wait)
- Fixed timezone-naive date parsing — UTC-enforced throughout ingestion (pd.to_datetime utc=True) + signal pipeline (pd.date_range tz="UTC")

MEDIUM fixes:
- Added CompResult.insufficient_data_warning for 1-2 sale comps (displayed in price-check and flip command outputs)
- Removed placeholder https://github.com/ URL from bulk sources output
- Verified all except blocks in analyze.py log at WARNING or higher
- Added warning log when scraper returns error dict in cmd_flip

ENTRY POINT:
- scraper._init_cache_db() wrapped in try/except with JSON error to stdout on failure
- analyze.py no-args invocation prints JSON error instead of raw traceback

UX:
- docs/ux-recommendation.md written with Telegram Bot as winning deployment approach for TCG trader (1490 words)
- docs/signal-quality-research.md written with evidence-based signal enhancements (1817 words)

Enhancement:
- RSI (Relative Strength Index) implemented in pokequant/signals/dip_detector.py
  - _compute_rsi() uses Wilder smoothing (14-period default)
  - RSI oversold (<30) confirms STRONG BUY alongside volume surge
  - RSI overbought (>70) escalates elevated-price SELL to STRONG SELL
  - RSI exposed in cmd_signal() output and SignalResult dataclass
  - Config: RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT in config.py

Tests: 40/40 passing

## What's Next

1. H-1.2 — Implement winning UX interface (Telegram Bot per ux-recommendation.md)
2. H-1.3 — Implement top 2 remaining signal enhancements from signal-quality-research.md (Format Rotation Decay, New-Set Release Penalty)
3. H-1.4 — Pull rate database: build a maintained pull rate table for modern sets
4. H-1.5 — Backtesting harness: validate signal accuracy on historical PriceCharting data
5. H-1.6 — Monte Carlo EV simulation: add variance/risk range to box EV output
