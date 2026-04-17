"""
config.py
---------
Global constants and tunable parameters for PokeQuant.
All threshold values live here so callers never hardcode magic numbers.
"""

import os

# ---------------------------------------------------------------------------
# Filesystem paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
DB_PATH = os.path.join(DATA_DIR, "db", "pokequant.db")

# ---------------------------------------------------------------------------
# Module 1 — Ingestion / IQR Outlier Filtering
# ---------------------------------------------------------------------------
IQR_MULTIPLIER: float = 1.5          # Standard Tukey fence multiplier
HARD_PRICE_FLOOR: float = 0.01       # Reject anything priced below $0.01
HARD_PRICE_CEILING: float = 50_000   # Reject obvious data-entry errors

# ---------------------------------------------------------------------------
# Module 2 — Signal Engine (SMA + Volume Liquidity)
# ---------------------------------------------------------------------------
SMA_SHORT_WINDOW: int = 7            # Days for the short moving average
SMA_LONG_WINDOW: int = 30            # Days for the long moving average

# A price this far below the 30-day SMA triggers the buy-side check
DIP_THRESHOLD: float = 0.15          # 15% below SMA-30

# Volume over the last N days must be this much higher than its rolling mean
VOLUME_LOOKBACK_DAYS: int = 3
VOLUME_SURGE_FACTOR: float = 1.20    # 20% above rolling-average volume
STRONG_SELL_THRESHOLD: float = 0.30  # 30% above SMA-30 → STRONG SELL

# ---------------------------------------------------------------------------
# Module 3 — Sealed Product EV
# ---------------------------------------------------------------------------
# Fraction of retail price above/below which we recommend action
EV_POSITIVE_MARGIN: float = 0.00     # EV > retail → "Rip for Singles"
EV_BREAKEVEN_MARGIN: float = -0.05  # EV within -5% of retail → "Borderline"

# ---------------------------------------------------------------------------
# Module 4 — Bulk Optimizer
# ---------------------------------------------------------------------------
# Default payout rates per card type (USD per card)
DEFAULT_BULK_RATES: dict = {
    "Common": 0.01,
    "Uncommon": 0.02,
    "Reverse Holo": 0.05,
    "Holo Rare": 0.10,
    "Ultra Rare": 0.50,
}
BULK_WEIGHT_LBS_PER_CARD: float = 0.013   # ~6g card + ~6g penny sleeve ≈ 12g per sleeved card (0.026 lbs double-sleeved, 0.013 lbs single-sleeved)
SHIPPING_RATE_PER_LB: float = 0.50        # USPS Media Mail estimate
BULK_LIQUIDATE_THRESHOLD: float = 50.00   # Net profit floor to recommend sale
BULK_PACKAGING_OVERHEAD_USD: float = 2.00  # Fixed packaging cost (envelope + label)

# Shipping tier cutoff: cards below this value go PWE, above go BMWT
SHIPPING_VALUE_THRESHOLD: float = 20.00   # eBay/TCGPlayer best practice for claim protection

# ---------------------------------------------------------------------------
# Module 5 — Comp Generator
# ---------------------------------------------------------------------------
COMP_SALES_LIMIT: int = 10           # How many recent sales to fetch
DECAY_LAMBDA: float = 0.3            # Exponential decay rate (higher = recency-biased)

# ---------------------------------------------------------------------------
# Module 6 — Flip Calculator (analyze.py cmd_flip)
# ---------------------------------------------------------------------------
PLATFORM_FEE_RATE: float = 0.13           # Combined eBay + TCGPlayer seller fee
SHIPPING_COST_BMWT: float = 4.00          # Bubble Mailer with Tracking (≥ $20 cards)
SHIPPING_COST_PWE: float = 1.00           # Plain White Envelope (< $20 cards)
FLIP_THIN_MARGIN_THRESHOLD_PCT: float = 20.0  # Below this margin % → "HOLD" verdict

# ---------------------------------------------------------------------------
# Module 7 — Sealed Product / Box Defaults
# ---------------------------------------------------------------------------
DEFAULT_PACKS_PER_BOX: int = 36          # Standard booster box pack count (used for box flip math)
