# Signal Quality Research: Evidence-Based Enhancements for Holo

**Date:** 2026-04-12
**Scope:** TCG-specific price signals, data sources, EV model, open-source repos

---

## 1. Top 3 Highest-Evidence Signal Enhancements

### 1A. Add RSI-14 Momentum Oscillator to Signal Engine

**What to change:** Add a 14-period Relative Strength Index (RSI) calculation alongside the existing SMA-7/SMA-30 signals in `pokequant/signals/dip_detector.py`.

**Why:** Holo's current signal engine uses only SMA crossover and volume surge detection. RSI is the standard momentum oscillator for detecting overbought (>70) and oversold (<30) conditions. Backtested RSI strategies on financial time series show win rates of 73-91% when combined with trend confirmation (MACD or SMA), per QuantifiedStrategies.com analysis. The RSI complements Holo's existing SMA-based dip detection by quantifying *how fast* a price is moving, not just *where* it is relative to a moving average. For TCG cards, where price spikes from tournament results or YouTube openings are sharp and mean-reverting, RSI is particularly well-suited: a card spiking from $10 to $25 in 3 days will show RSI > 80, signaling the spike is likely to revert -- exactly the pattern Holo should flag as SELL before the inevitable correction.

**Implementation:** Add `_compute_rsi()` to `dip_detector.py` using the standard Wilder smoothing formula: `RSI = 100 - (100 / (1 + RS))` where `RS = avg_gain / avg_loss` over 14 periods. Integrate into `_classify_row()` as a confirmation signal: RSI < 30 + price below SMA-30 = STRONG BUY; RSI > 70 + price above SMA-30 = STRONG SELL.

**Citations:**
- RSI formula and standard 14-period parameterization: [Wilder, J.W. (1978). "New Concepts in Technical Trading Systems"](https://en.wikipedia.org/wiki/Relative_strength_index)
- RSI backtested win rates (91% with 2-period RSI on mean-reverting assets): [QuantifiedStrategies.com RSI Trading Strategy](https://www.quantifiedstrategies.com/rsi-trading-strategy/)
- Combined MACD+RSI 73% win rate in backtests: [QuantifiedStrategies.com MACD and RSI Strategy](https://www.quantifiedstrategies.com/macd-and-rsi-strategy/)

### 1B. Add Tournament Meta-Shift Signal (Limitless TCG Integration)

**What to change:** Add a new signal source in `pokequant/signals/` that queries the Limitless TCG API for tournament top-8 decklists and flags cards appearing in winning decks.

**Why:** Tournament results are the single strongest short-term price driver for playable Pokemon cards. Data from Card Chill's meta analysis shows: Regional Championship wins increase card prices 15-30% within 72 hours; format rotation shifts can drive 70-120% ROI on newly-viable cards; and deck archetype shifts (e.g., Mega ex rising from 15% to 55-60% of top cuts post-rotation) create sustained multi-week price movements. The Limitless TCG API is freely available without an API key for tournament placings and match data, making integration straightforward. A specific documented example: Mega Lucario ex SAR rose 16-21% on eBay after Birmingham Regional results in April 2026.

**Implementation:** Create `pokequant/signals/meta_detector.py` that polls `limitlesstcg.com/api/v2/tournaments` for recent results, extracts card names from top-8 decklists, and emits a META_SPIKE signal for any card in Holo's watchlist that appeared in 3+ winning decks in the last 14 days. This signal would feed into `_classify_row()` as an additional SELL confirmation (the price spike has likely already started by the time results are published).

**Citations:**
- Limitless TCG API (free, no key required for tournament data): [Limitless Developer Docs](https://docs.limitlesstcg.com/developer.html)
- Tournament price impact quantified (15-30% within 72h): [Card Chill Meta Shift Analysis](https://cardchill.com/article/pokemon-tcg-meta-shifts-post-rotation-deck-synergies-and-chase-card-demand-drivers)
- Post-rotation tier list with specific price movements: [Card Chill March 2026 Tier List](https://cardchill.com/article/data-analysis-post-rotation-meta-tier-list-top-10-decks-dominating-march-2026-tournaments)

### 1C. Add Holiday Seasonality Adjustment to Comp Generator

**What to change:** Add a seasonal multiplier in `pokequant/comps/generator.py` that adjusts the CMC (Current Market Comp) based on known annual price cycles.

**Why:** Pokemon card prices follow documented seasonal patterns: prices rise 30-40% during Black Friday through Christmas, then drop 10-15% in January as gift-recipients flood the secondary market. Summer events (Pokemon Worlds in August) create a secondary 15-25% spike. Holo's current comp generator treats all time periods equally -- a comp generated in December will overstate fair value because it is capturing holiday-inflated prices, leading to incorrect HOLD signals when a user should be selling into the seasonal peak. Conversely, January comps will understate value because they capture post-holiday liquidation prices.

**Implementation:** Add a `_seasonal_adjustment()` function that applies a multiplicative factor based on the current month: November-December = 0.85 (deflate comp to remove holiday premium, signaling that current high prices are temporary); January = 1.10 (inflate comp to account for temporary dip); June-August = 0.95 (slight deflation for Worlds hype). Store the seasonal factors in `config.py` as `SEASONAL_FACTORS: dict[int, float]`. Apply the adjustment after the exponential-decay weighted average is computed but before the recommendation is generated.

**Citations:**
- Holiday price increase of 30-40%, January dip of 10-15%: [Card Shops List Seasonal Guide](https://www.cardshopslist.com/blog/ultimate-guide-to-seasonal-card-market-cycles/)
- Summer event (Worlds) price bump of 15-25%: [MyDexTCG Price Trends](https://www.mydextcg.com/blog/pokemon-card-price-trends-what-affects-value)
- Holt-Winters seasonal decomposition methodology: [Forecasting: Principles and Practice, Ch 8.3](https://otexts.com/fpp3/holt-winters.html)

---

## 2. Data Source Recommendation

**Recommendation: Keep PriceCharting + pokemontcg.io, and add TCGdex price-history as a third source.**

### Current Sources Assessment

| Source | Strengths | Weaknesses |
|--------|-----------|------------|
| **PriceCharting** | 5+ years historical depth, sold listings (not asks), covers sealed products | Slow API (300ms), 60 req/hour free tier, scraping-dependent |
| **pokemontcg.io** | Unlimited free requests, excellent card metadata, images | No pricing data at all (metadata only) |

### Recommended Addition: TCGdex price-history

The [tcgdex/price-history](https://github.com/tcgdex/price-history) GitHub repository provides daily-updated pricing from multiple marketplaces (Cardmarket, TCGPlayer) with pre-calculated 1-day, 7-day, and 28-day moving averages plus trend indicators. It is MIT-licensed, updates daily via automated pipeline, and stores data as flat JSON files -- no API rate limits.

**Why not replace PriceCharting?** PriceCharting remains the best source for eBay completed-listing sold prices (actual transaction data, not listed prices). The eBay Marketplace Insights API is restricted to approved partners, so PriceCharting's scraping is effectively the only way independent developers access this data. TCGdex provides TCGPlayer/Cardmarket prices, which are complementary (different buyer populations, different price points).

**Why not PokemonPriceTracker API?** While it offers the fastest response time (48ms) and PSA data, its free tier is only 100 credits/day -- insufficient for a tool that needs to check multiple cards per session. The $9.99/month paid tier (20K req/day) is reasonable but adds a recurring cost dependency.

**Citations:**
- API comparison with response times and rate limits: [PokemonPriceTracker API Comparison 2025](https://www.pokemonpricetracker.com/blog/posts/pokemon-api-comparison-2025)
- TCGdex price-history repo (MIT, daily updates, pre-calculated averages): [GitHub tcgdex/price-history](https://github.com/tcgdex/price-history)
- PriceCharting API docs (60/hour free, 5+ year depth): [PriceCharting API Documentation](https://www.pricecharting.com/api-documentation)
- eBay sold listings restricted to partners: [eBay Community Thread on API Access](https://community.ebay.com/t5/eBay-APIs-Talk-to-your-fellow/Access-to-sold-completed-listing-data-what-options-do-non/m-p/35398955)

---

## 3. EV Model Recommendation: Add Pull Rate Variance / Risk Range

**Recommendation: Yes -- add Monte Carlo variance estimation to `pokequant/ev/calculator.py`.**

### Current Limitation

Holo's EV calculator computes a single point estimate: `EV = sum(expected_hits * avg_card_value)`. This is mathematically correct for the *mean* outcome but tells users nothing about the *range* of likely outcomes. Community data from Card Chill's pull rate analysis shows that across 50+ boxes, roughly 15% are "hot" (2x+ expected hits of Illustration Rares) and 15% are "cold" (<0.5x expected). At 500 packs, pull rate estimates can be off by 30-50% for rare tiers. This means a box showing "$160 EV vs $150 retail" could easily yield $80-$240 in practice.

### Recommended Implementation

Add a `simulate_box_ev()` function that runs N=1,000 Monte Carlo trials per box:

1. For each trial, simulate pack-by-pack pulls using binomial sampling with the given pull rates
2. When a pull hits a tier, randomly select a card from that tier's card list (uniform distribution)
3. Sum the market values of all pulled cards to get one trial's realized value
4. After N trials, report: **mean EV**, **10th percentile** (pessimistic), **90th percentile** (optimistic), and **P(profit)** (percentage of trials where realized value > retail price)

This converts the current `BoxEVResult` from a single number into a risk-aware range. The existing `calculate_box_ev()` function stays unchanged; `simulate_box_ev()` is an additive enhancement.

The [pokemonevcalculator.com](https://pokemonevcalculator.com/) site already uses 10,000 Monte Carlo simulations with community pull rate data from PokeData.io, validating that this approach is standard practice in the TCG EV space.

### Pull Rate Data Quality

Per Card Chill's statistical breakdown: minimum 1,000 packs are needed for general rarity estimates (plus/minus 15-25% accuracy); 3,000+ packs for flagship chase cards (plus/minus 5-10%). Holo should display a confidence indicator based on the source sample size of its pull rate data.

**Citations:**
- Monte Carlo EV approach with 10,000 simulations: [PokemonEVCalculator.com](https://pokemonevcalculator.com/)
- Pull rate variance (15% hot/cold boxes, 30-50% variance at 500 packs): [Card Chill Pull Rate Realities](https://cardchill.com/article/pokemon-cards-pull-rate-realities-statistical-breakdowns-across-recent-expansions)
- Community pull rate data source: [PokeData.io](https://www.pokedata.io/)
- The Expected Value site (ETB-specific EV with variance projections): [TheExpectedValue.com](https://theexpectedvalue.com/)

---

## 4. Top 3 Open-Source Repos to Study

### 4A. tcgdex/price-history

**URL:** [github.com/tcgdex/price-history](https://github.com/tcgdex/price-history)
**Stars:** 25 | **License:** MIT | **Language:** Automated pipeline (JSON output)

**Why study it:** This repo solves the exact data pipeline problem Holo faces -- daily multi-source price ingestion with pre-calculated moving averages (1, 7, 28 days) and trend indicators. The data is stored as flat JSON per card per language (English, French), making it trivially consumable. Holo could either use this as a supplementary data source directly or study its pipeline architecture for improving `pokequant/scraper.py`'s multi-source ingestion.

**Key takeaway:** Pre-calculating rolling averages at ingestion time (rather than at query time) significantly reduces latency for the signal engine.

### 4B. wjsutton/pokemon_tcg_stockmarket

**URL:** [github.com/wjsutton/pokemon_tcg_stockmarket](https://github.com/wjsutton/pokemon_tcg_stockmarket)
**Stars:** Notable | **License:** Open source | **Language:** Python

**Why study it:** This project treats Pokemon cards as financial instruments -- exactly Holo's thesis. It fetches daily prices from TCGPlayer via the pokemontcg.io API, stores them as timestamped CSVs separating vintage from modern cards, and exports to Tableau for stock-market-style visualization. The data pipeline architecture (pokemon_api.py for API calls with pagination, main.py for orchestration) is a clean reference for improving Holo's scraper. The vintage vs. modern card separation is relevant because price behavior differs substantially between these categories (vintage cards are more stable; modern cards are more volatile and tournament-meta-sensitive).

**Key takeaway:** Separating card cohorts (vintage/modern, playable/collectible) before applying signal analysis improves signal quality because the same SMA parameters perform differently across cohorts.

### 4C. n1ru4l/pokemon-tcg-deck-scraper-api

**URL:** [github.com/n1ru4l/pokemon-tcg-deck-scraper-api](https://github.com/n1ru4l/pokemon-tcg-deck-scraper-api)
**Stars:** Niche utility | **Language:** TypeScript

**Why study it:** This scraper extracts tournament decklists programmatically, which is the exact data needed for the meta-shift signal proposed in Enhancement 1B. Understanding how it parses deck composition into individual card references helps design the Limitless TCG integration. While Holo would use the official Limitless API rather than scraping, the data normalization patterns (mapping deck card names to canonical card IDs) are directly applicable.

**Key takeaway:** Tournament decklist data requires card-name normalization (e.g., "Charizard ex SV03" vs "Charizard ex 006/091") before it can be correlated with price data from PriceCharting.

---

## 5. One New Signal Idea: "Hype Decay Detector"

### Concept

A signal that detects post-hype price normalization by measuring the *rate of deceleration* in price momentum after a spike event. When a card spikes (new set release, tournament result, YouTuber opening), prices follow a predictable decay curve: sharp spike over 1-3 days, plateau for 3-7 days, then gradual decline over 2-4 weeks back toward a new (usually higher) baseline. The Hype Decay Detector identifies which phase the card is in and signals accordingly.

### TCG Market Evidence

Tournament results create 15-30% spikes within 72 hours that revert over 1-3 months unless sustained by continued meta relevance (Card Chill meta analysis). New set release chase cards spike at pre-release, then drop 20-30% within the first month as supply enters the market (PokemonPriceTracker historical data patterns). The 2025 market correction showed sealed products sitting on shelves after initial hype (PokéWallet market crash analysis), demonstrating that hype-driven spikes are a recurring, predictable pattern.

### Implementation (under 100 lines)

```python
# pokequant/signals/hype_decay.py

import numpy as np
import pandas as pd

SPIKE_THRESHOLD_PCT = 20.0    # Min % rise over 3 days to qualify as spike
PLATEAU_DAYS = 7              # Window to detect plateau after spike
DECAY_CONFIRM_DAYS = 5        # Days of declining prices to confirm decay

SIGNAL_HYPE_PEAK = "SELL (Hype Peak — Decay Expected)"
SIGNAL_HYPE_DECAY = "BUY (Post-Hype Dip — Stabilizing)"
SIGNAL_NO_HYPE = "NO HYPE EVENT DETECTED"


def detect_hype_phase(daily: pd.DataFrame) -> dict:
    """Detect if a card is in a post-hype decay pattern.

    Parameters
    ----------
    daily : pd.DataFrame
        Date-indexed with 'price_mean' column (from dip_detector._aggregate_daily).

    Returns
    -------
    dict with keys: signal, spike_date, spike_magnitude_pct, days_since_spike, phase
    """
    prices = daily["price_mean"].dropna()
    if len(prices) < 14:
        return {"signal": SIGNAL_NO_HYPE, "phase": "insufficient_data"}

    # Step 1: Find the most recent spike (rolling 3-day return > threshold)
    returns_3d = prices.pct_change(periods=3) * 100
    spike_mask = returns_3d > SPIKE_THRESHOLD_PCT
    if not spike_mask.any():
        return {"signal": SIGNAL_NO_HYPE, "phase": "no_spike"}

    spike_date = spike_mask[spike_mask].index[-1]
    spike_magnitude = float(returns_3d.loc[spike_date])
    days_since = (prices.index[-1] - spike_date).days

    # Step 2: Identify current phase
    post_spike = prices.loc[spike_date:]

    if len(post_spike) < 3:
        return {
            "signal": SIGNAL_HYPE_PEAK,
            "spike_date": spike_date,
            "spike_magnitude_pct": round(spike_magnitude, 1),
            "days_since_spike": days_since,
            "phase": "peak",
        }

    # Check if price has been declining for DECAY_CONFIRM_DAYS
    recent = post_spike.tail(DECAY_CONFIRM_DAYS)
    if len(recent) >= 3:
        declining_days = (recent.diff().dropna() < 0).sum()
        pct_declining = declining_days / len(recent.diff().dropna())
    else:
        pct_declining = 0.0

    if days_since <= PLATEAU_DAYS and pct_declining < 0.5:
        phase = "plateau"
        signal = SIGNAL_HYPE_PEAK
    elif pct_declining >= 0.6:
        phase = "decay"
        signal = SIGNAL_HYPE_DECAY
    else:
        phase = "stabilizing"
        signal = SIGNAL_NO_HYPE

    return {
        "signal": signal,
        "spike_date": spike_date,
        "spike_magnitude_pct": round(spike_magnitude, 1),
        "days_since_spike": days_since,
        "phase": phase,
        "decline_ratio": round(float(pct_declining), 2),
    }
```

This detector adds a new dimension to Holo's signal taxonomy: instead of only measuring where a price *is* relative to moving averages (the SMA approach), it measures the *trajectory and phase* of a price event. It would integrate into the existing `_classify_row()` in `dip_detector.py` as an additional signal that can override or confirm the SMA-based signal. For example, a card showing HOLD on SMA signals but SELL on hype-decay (it is in the plateau phase after a spike) would be upgraded to SELL.

**Grounding:** This pattern is well-documented in TCG markets. Card Chill's analysis shows tournament-driven spikes revert in 1-3 months; the 2025 Pokewallet market crash analysis documented sealed product hype cycles following this exact spike-plateau-decay pattern; and the seasonal analysis shows holiday spikes follow a predictable January correction.

---

## References (Consolidated)

1. [Limitless TCG Developer API](https://docs.limitlesstcg.com/developer.html) -- Free tournament data API
2. [tcgdex/price-history](https://github.com/tcgdex/price-history) -- Daily multi-source price data with averages
3. [wjsutton/pokemon_tcg_stockmarket](https://github.com/wjsutton/pokemon_tcg_stockmarket) -- TCGPlayer price pipeline
4. [n1ru4l/pokemon-tcg-deck-scraper-api](https://github.com/n1ru4l/pokemon-tcg-deck-scraper-api) -- Decklist scraping
5. [PokemonEVCalculator.com](https://pokemonevcalculator.com/) -- Monte Carlo EV with 10K simulations
6. [PokeData.io](https://www.pokedata.io/) -- Community pull rate data
7. [Card Chill Pull Rate Realities](https://cardchill.com/article/pokemon-cards-pull-rate-realities-statistical-breakdowns-across-recent-expansions)
8. [Card Chill Meta Shift Analysis](https://cardchill.com/article/pokemon-tcg-meta-shifts-post-rotation-deck-synergies-and-chase-card-demand-drivers)
9. [PokemonPriceTracker API Comparison](https://www.pokemonpricetracker.com/blog/posts/pokemon-api-comparison-2025)
10. [PriceCharting API Documentation](https://www.pricecharting.com/api-documentation)
11. [RSI Wikipedia (Wilder 1978)](https://en.wikipedia.org/wiki/Relative_strength_index)
12. [QuantifiedStrategies RSI Backtests](https://www.quantifiedstrategies.com/rsi-trading-strategy/)
13. [Hyndman & Athanasopoulos, Forecasting: Principles and Practice, Ch 8.3](https://otexts.com/fpp3/holt-winters.html)
14. [EWMA Optimal Decay Parameter (arXiv 2105.14382)](https://arxiv.org/pdf/2105.14382)
15. [PokéWallet Market Crash 2025 Analysis](https://www.pokewallet.io/blog/pokemon-tcg-market-crash-2025-analysis)
16. [Card Chill Sealed Product EV Comparison](https://cardchill.com/article/pokemon-tcg-sealed-products-ev-comparison-which-phantasmal-flames-item-delivers-the-best-bang-for-your-buck)
