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
BULK_WEIGHT_LBS_PER_CARD: float = 0.006   # ~6 grams per sleeved card
SHIPPING_RATE_PER_LB: float = 0.50        # USPS Media Mail estimate
BULK_LIQUIDATE_THRESHOLD: float = 50.00   # Net profit floor to recommend sale

# ---------------------------------------------------------------------------
# Module 5 — Comp Generator
# ---------------------------------------------------------------------------
COMP_SALES_LIMIT: int = 10           # How many recent sales to fetch
DECAY_LAMBDA: float = 0.3            # Exponential decay rate (higher = recency-biased)
