# Signal Quality Research — Holo TCG Trading Assistant

Research date: 2026-04-15

## 1. Top 3 Highest-Evidence Signal Enhancements

### 1A. Add RSI (Relative Strength Index) to dip_detector.py

**What to change:** Add a 14-period RSI calculation alongside the existing SMA-7/SMA-30 signals in `pokequant/signals/dip_detector.py`. RSI measures the speed and magnitude of recent price changes on a 0-100 scale. When RSI drops below 30, the card is "oversold" (likely to rebound); above 70 it is "overbought" (likely to correct). This directly strengthens the existing DIP_THRESHOLD logic by adding momentum confirmation.

**Evidence:** RSI is the most widely backtested momentum oscillator in financial markets. QuantifiedStrategies.com reports a 91% win rate on mean-reversion RSI strategies when combined with trend filters (which Holo already has via SMA-30). The key advantage for TCG markets: RSI is manipulation-resistant compared to raw price levels because it normalizes velocity rather than absolute values. TCGPlayer's own "Market Price" metric already implicitly reflects momentum since it weights recent completed sales, so RSI computed on Market Price data would compound two manipulation-resistant signals. Academic research on MTG secondary markets from IU International University of Applied Sciences ([Exploring markets: Magic the Gathering](https://ideas.repec.org/p/zbw/iubhbm/32021.html)) confirms that TCG markets exhibit mean-reverting behavior at short horizons (7-14 days), which is exactly the regime where RSI excels.

**Implementation:** Add a `_compute_rsi()` helper to `dip_detector.py` using Wilder's smoothed moving average (approximately 20 lines). Feed RSI into `_classify_row()` as a confirmation signal: STRONG BUY requires RSI < 30 AND price below SMA-30 AND volume surge. This replaces the current two-condition composite with a three-condition composite, reducing false positives.

### 1B. Add Format Rotation Decay to generator.py

**What to change:** In `pokequant/comps/generator.py`, add a rotation-awareness multiplier that increases the decay lambda for cards approaching Standard format rotation. Currently Holo uses a static lambda=0.3 for all cards. Cards rotating out of Standard lose 10-30% within weeks of rotation ([2026 Rotation Analysis, CardChill](https://cardchill.com/article/2026-pokemon-tcg-rotation-in-depth-analysis-of-card-value-impacts-and-investment-strategies); [TCGPlayer 2026 Rotation Guide](https://www.tcgplayer.com/content/article/2026-Pok%C3%A9mon-Standard-Rotation-Guide/cd81088d-d38c-481c-b680-1248a23bd62d/)). Pre-rotation comps are systematically misleading because they reflect a price regime that is about to end.

**Evidence:** The 2026 Standard rotation (effective March 26 digitally, April 10 in-person) removed all G-regulation-mark cards. TCGPlayer data shows H/I/J singles climb ~20% post-announcement while rotating staples drop 10-30%. Academic EWMA research ([Araneda, 2021, arXiv:2105.14382](https://arxiv.org/abs/2105.14382)) demonstrates that the optimal lambda is time-varying and should be adjusted based on forecasting horizon. For TCG cards approaching rotation, the effective "horizon" compresses dramatically, justifying lambda increases to 0.5-0.7 in the 60 days before rotation date.

**Implementation:** Add an optional `rotation_date` parameter to `generate_comp()`. When present and within 60 days, compute `adjusted_lambda = base_lambda + 0.3 * (1 - days_remaining / 60)`. This smoothly ramps decay from 0.3 to 0.6 as rotation approaches. Approximately 15 lines of new code.

### 1C. Add New-Set Release Price Decay Curve to dip_detector.py

**What to change:** Add a "release week penalty" flag in `pokequant/signals/dip_detector.py` that suppresses BUY signals during the first 14 days after a set's release date. New-set singles are systematically overpriced at launch due to scarcity and FOMO, then crash as supply normalizes.

**Evidence:** Wargamer reported that Phantasmal Flames chase cards crashed "way faster than normal" ([Wargamer, 2026](https://www.wargamer.com/pokemon-trading-card-game/phantasmal-flames-fall-price-dropping)). PokemonPriceTracker's Q1 2026 market report documents that "release-week FOMO pricing is no longer sustainable" as a market pattern. Obsidian Flames Charizard dropped from $126 to $79 post-release; Prismatic Evolutions Umbreon SIR fell 50% from peak ($1,600 to $832). A dip detector that fires BUY on a card that dropped 20% from its artificially inflated release price is producing a false positive. The card is not dipping; it is normalizing.

**Implementation:** Add a `set_release_date` optional field to the signal pipeline. When `(today - release_date).days < 14`, override any BUY/STRONG BUY signal with HOLD and append a metadata note: "Release-week pricing detected: wait for price stabilization." Approximately 10 lines in `_classify_row()`.


## 2. Data Source Recommendation

**Keep PriceCharting + pokemontcg.io, and add one supplemental source.**

PriceCharting remains the best free source for historical sold-listing data, and pokemontcg.io provides the card metadata and TCGPlayer market prices needed for EV calculations. However, the research uncovered two gaps worth filling:

- **eBay sold-listing data** is missing from Holo's pipeline. PriceCharting aggregates eBay data but with a delay and without granular condition breakdowns. The [TCG Price Lookup API (tcgfast.com)](https://tcgfast.com/) provides a free tier (200 requests/day) with eBay sold listings updated daily, per-condition values, and price history endpoints. This is the strongest candidate for a supplemental data source because it adds genuine transaction data (not asking prices) from a different marketplace, enabling cross-platform price validation.

- **TCGPlayer Market Price** should be preferred over Mid/Low when available. TCGPlayer's own documentation confirms that Market Price is a rolling weighted average of actual completed sales, while Mid/Low reflect listing prices that can be manipulated via buyouts ([TCGPlayer Help](https://help.tcgplayer.com/hc/en-us/articles/213588017-TCGplayer-Market-Price)). Holo's scraper should prioritize Market Price and treat Mid as a fallback.

- **PokemonPriceTracker API** ([pokemonpricetracker.com/api](https://www.pokemonpricetracker.com/api)) aggregates TCGPlayer, eBay, and CardMarket with a free tier and 48ms average response time. Worth evaluating if tcgfast.com proves insufficient.

**Not recommended:** Direct eBay API access. eBay's Finding API rate-limits findCompletedItems aggressively and Marketplace Insights is restricted to approved partners. Third-party aggregators are more practical.


## 3. EV Model Recommendation — Add Pull Rate Variance / Risk Range

**Yes, add a Monte Carlo risk range to `pokequant/ev/calculator.py`.**

The current EV calculator computes a single point estimate: `expected_hits_per_box * avg_card_value`. This is mathematically correct as a mean but tells the user nothing about variance. A box with EV of $160 could mean "you will almost certainly get $140-$180" (low variance, many common hits) or "you have a 5% chance of $400 and a 95% chance of $80" (high variance, chase-card-dependent).

**Evidence:** PokemonEVCalculator.com and PorgDepot's EV tools both use 10,000-iteration Monte Carlo simulations to produce 25th/50th/75th percentile outcomes rather than a single mean. The community has adopted this as the standard because it matches the lived experience of opening boxes. The TCGPlayer "Perfect Order Pull Rates" article ([TCGPlayer, 2025](https://www.tcgplayer.com/content/article/Pok%C3%A9mon-TCG-Perfect-Order-Pull-Rates/73148119-ebcb-40b7-84b6-52b3a6d0c631/)) documents that pull rates vary significantly between sets, and that individual box variance can be extreme, especially for Special Illustration Rares with rates like 1/36.

**Specific change:** Add a `simulate_box_ev()` function to `calculator.py` that runs N=5000 Monte Carlo trials per box. For each trial, simulate each pack independently: for each rarity tier, draw a Bernoulli trial at the tier's pull rate, and if hit, select a random card from that tier's card list. Sum the total box value. Return P25, P50 (median), P75, and P95 alongside the analytical mean EV. Display as: "EV: $160 (likely range: $95-$210, 50th percentile: $145)".

This is approximately 40-50 lines of new code using only `numpy.random` (already a dependency).


## 4. Top 3 Open-Source Repos Holo Should Study

### 4A. tcgdex/price-history
- **URL:** [github.com/tcgdex/price-history](https://github.com/tcgdex/price-history)
- **Why:** Automatic daily price history collection for Pokemon TCG cards from multiple sources, with pre-calculated averages (1, 7, 28 day) and trend data. MIT licensed. This is the closest open-source analog to Holo's data pipeline and could serve as a reference for multi-source price aggregation, daily scheduling, and trend computation. The pre-calculated moving averages mirror Holo's SMA approach and could be used as a validation dataset.

### 4B. wjsutton/pokemon_tcg_stockmarket
- **URL:** [github.com/wjsutton/pokemon_tcg_stockmarket](https://github.com/wjsutton/pokemon_tcg_stockmarket)
- **Why:** A data visualization and analysis project that fetches live market prices from TCGPlayer via their API and generates daily CSV snapshots of Pokemon card prices across vintage and modern sets. The project applies stock-market-style analysis methods to TCG data, which directly parallels Holo's SMA and signal approach. The CSV data format and daily snapshot architecture could inform Holo's history.db schema improvements.

### 4C. zsd7200/packrip
- **URL:** [github.com/zsd7200/packrip](https://github.com/zsd7200/packrip)
- **Why:** A Pokemon TCG booster pack simulator that uses the Pokemon TCG API for card/set data combined with pull rate data from various community sources, aiming for set-specific accuracy. This is directly relevant to improving Holo's EV calculator. The project's pull rate data sourcing approach (aggregating community-reported rates per set) could replace Holo's current static JSON pull rate input with a more dynamic, community-validated data feed. Study its rate data format for the Monte Carlo simulation recommended in Section 3.


## 5. New Signal Idea: Tournament Meta Spike Detector

**Signal name:** META_SPIKE
**Target file:** `pokequant/signals/dip_detector.py` (new function, or new file `pokequant/signals/meta_detector.py`)

**What it does:** Detect cards experiencing price spikes driven by tournament results, and classify them as either sustainable (format staple) or transient (single-event tech).

**TCG market evidence:** Tournament results are the single strongest short-term price driver for playable Pokemon cards. Regional Championship wins increase card prices 30-50% within 24-48 hours, World Championship results can double prices, and even Top 8 appearances boost prices 15-25% ([MyDexTCG](https://www.mydextcg.com/blog/pokemon-card-price-trends-what-affects-value); [PokemonPriceTracker](https://www.pokemonpricetracker.com/blog/posts/pokemon-card-game-value)). However, these spikes only sustain if the card maintains meta relevance across multiple events over 1-3 months. Single-event tech cards revert to baseline within 2-4 weeks.

**Algorithm (implementable in approximately 60-80 lines):**

```
1. Compute 7-day price velocity:  velocity = (price_today - price_7d_ago) / price_7d_ago
2. If velocity > 0.25 (25% gain in 7 days):
     a. Check if volume also surged > 2x baseline (confirms real demand, not thin-market noise)
     b. If yes: flag as META_SPIKE_DETECTED
3. Classify sustainability:
     a. If the card's 30-day price trend was already positive before the spike: "SUSTAINABLE — format staple gaining meta share"
     b. If the card was flat or declining before the spike: "TRANSIENT — likely single-event tech, consider selling into the spike"
4. Emit advisory:
     - SUSTAINABLE → HOLD (do not sell into strength if card is a staple)
     - TRANSIENT  → SELL (capture the spike premium before reversion)
```

This signal fills a gap in Holo's current system: the dip detector finds cards that have fallen, but nothing detects cards that have spiked and helps the user decide whether to hold or sell into the spike. The velocity + pre-spike-trend heuristic is simple, requires no external tournament data API, and relies entirely on price/volume data Holo already collects.

**Data needed:** Only the daily price and volume series already produced by `_aggregate_daily()` in `dip_detector.py`. No new data sources required.


## Sources

- [QuantifiedStrategies.com — RSI Trading Strategy Backtest](https://www.quantifiedstrategies.com/rsi-trading-strategy/)
- [IU International University — Exploring markets: Magic the Gathering](https://ideas.repec.org/p/zbw/iubhbm/32021.html)
- [ResearchGate — MTG Economic Analysis of Collectible Card Game Market](https://www.researchgate.net/publication/325049318_Magic_the_Gathering_economic_analysis_of_the_market_of_a_collectible_card_game)
- [Araneda (2021) — Optimal Decay Parameter in the EWMA Model (arXiv:2105.14382)](https://arxiv.org/abs/2105.14382)
- [CardChill — 2026 Pokemon TCG Rotation Value Impact Analysis](https://cardchill.com/article/2026-pokemon-tcg-rotation-in-depth-analysis-of-card-value-impacts-and-investment-strategies)
- [TCGPlayer — 2026 Pokemon Standard Rotation Guide](https://www.tcgplayer.com/content/article/2026-Pok%C3%A9mon-Standard-Rotation-Guide/cd81088d-d38c-481c-b680-1248a23bd62d/)
- [TCGPlayer — Market Price Documentation](https://help.tcgplayer.com/hc/en-us/articles/213588017-TCGplayer-Market-Price)
- [TCGPlayer — Perfect Order Pull Rates](https://www.tcgplayer.com/content/article/Pok%C3%A9mon-TCG-Perfect-Order-Pull-Rates/73148119-ebcb-40b7-84b6-52b3a6d0c631/)
- [Wargamer — Phantasmal Flames Price Crash](https://www.wargamer.com/pokemon-trading-card-game/phantasmal-flames-fall-price-dropping)
- [PokemonPriceTracker — Q1 2026 Market Trends Report](https://www.pokemonpricetracker.com/blog/posts/pokemon-card-market-trends-q1-2026-complete-data-report)
- [MyDexTCG — Pokemon Card Price Trends: What Affects Value](https://www.mydextcg.com/blog/pokemon-card-price-trends-what-affects-value)
- [PokemonPriceTracker — Card Game Value: Playability vs Collectability](https://www.pokemonpricetracker.com/blog/posts/pokemon-card-game-value)
- [Pancake Analytics — Trading Card Holt-Winters Forecasting](https://pancakebreakfaststats.com/trading-card-resources/)
- [CAIA — Collectibles: Trading Cards and the Price of Perfection](https://caia.org/blog/2021/12/02/collectibles-trading-cards-and-price-perfection)
- [TCG Price Lookup API (tcgfast.com)](https://tcgfast.com/)
- [PokemonPriceTracker API](https://www.pokemonpricetracker.com/api)
- [JustTCG API](https://justtcg.com/)
- [tcgdex/price-history (GitHub)](https://github.com/tcgdex/price-history)
- [wjsutton/pokemon_tcg_stockmarket (GitHub)](https://github.com/wjsutton/pokemon_tcg_stockmarket)
- [zsd7200/packrip (GitHub)](https://github.com/zsd7200/packrip)
- [PokemonTCG/pokemon-tcg-data (GitHub)](https://github.com/PokemonTCG/pokemon-tcg-data)
- [tooniez/pokemoncards_tcg (GitHub)](https://github.com/tooniez/pokemoncards_tcg)
- [Quiet Speculation — Spread Analysis on TCGPlayer](https://www.quietspeculation.com/2019/12/spread-analysis-on-tcgplayer-part-1/)
- [GemRate — PSA Population Report and Grading Data](https://www.gemrate.com/)
- [PokemonEVCalculator.com](https://pokemonevcalculator.com/)
- [PorgDepot — Box Expected Value Calculator](https://porgdepot.com/expected-value-calculator/)
