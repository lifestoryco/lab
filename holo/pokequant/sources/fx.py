"""FX normalization — static exchange rates to USD.

These are intentionally static constants. Live FX lookups for per-request
conversion are overkill for comp math; we tolerate a few percent error in
exchange for zero external dependency.
"""
from __future__ import annotations

EXCHANGE_RATES_USD: dict[str, float] = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.27,
    "JPY": 0.0066,
}


def to_usd(amount: float, currency: str) -> float | None:
    """Convert amount to USD; return None for unknown currencies."""
    rate = EXCHANGE_RATES_USD.get(currency)
    if rate is None:
        return None
    return round(amount * rate, 2)
