"""summary.average — mean of in-window sales above outlier floor.

Replaces the misleading `summary.current` (last day's daily-median) as the
primary "what does this card sell for" number on the card detail page.
"""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch


def _build_sales(today: date, prices_by_offset: dict[int, list[float]]) -> list[dict]:
    """Build a sales list with prices keyed by days-ago."""
    out = []
    for offset, prices in prices_by_offset.items():
        d = (today - timedelta(days=offset)).isoformat()
        for i, p in enumerate(prices):
            out.append({
                "sale_id": f"s-{offset}-{i}",
                "price": p,
                "date": d,
                "condition": "NM",
                "source": "pricecharting",
                "quantity": 1,
            })
    return out


def test_average_is_mean_of_all_in_window_sales(monkeypatch):
    monkeypatch.delenv("HOLO_USE_REGISTRY", raising=False)
    today = date.today()
    sales = _build_sales(today, {
        0: [20.0],          # one outlier-ish sale today
        1: [10.0, 11.0],
        5: [12.0, 13.0],
        10: [10.0, 11.0],
    })

    with patch("pokequant.scraper.fetch_sales", return_value=sales), \
         patch("api.index._lookup_card_meta", return_value={}), \
         patch("api.index._extract_sources", return_value=[]):
        from api.index import _handle_history
        result = _handle_history({"card": ["Test"], "days": ["30"]})

    expected = round((20 + 10 + 11 + 12 + 13 + 10 + 11) / 7, 2)
    assert result["summary"]["average"] == expected
    # current still present for backward compat, but should NOT equal average here
    assert "current" in result["summary"]
    assert result["summary"]["in_window_count"] == 7


def test_average_drops_low_outliers_below_15pct_floor(monkeypatch):
    """A junk $1 listing on a $50 card must not pull the average down."""
    monkeypatch.delenv("HOLO_USE_REGISTRY", raising=False)
    today = date.today()
    sales = _build_sales(today, {
        1: [50.0, 52.0, 48.0, 51.0, 49.0],
        2: [1.0],   # junk listing — 2% of median, must be dropped
    })

    with patch("pokequant.scraper.fetch_sales", return_value=sales), \
         patch("api.index._lookup_card_meta", return_value={}), \
         patch("api.index._extract_sources", return_value=[]):
        from api.index import _handle_history
        result = _handle_history({"card": ["Test"], "days": ["30"]})

    # 5 legitimate sales averaged; the $1 is below 15% of $50 median
    expected = round((50 + 52 + 48 + 51 + 49) / 5, 2)
    assert result["summary"]["average"] == expected
    assert result["summary"]["in_window_count"] == 5


def test_average_excludes_sales_outside_window(monkeypatch):
    """Sales older than `days` must not affect the average."""
    monkeypatch.delenv("HOLO_USE_REGISTRY", raising=False)
    today = date.today()
    sales = _build_sales(today, {
        2: [100.0, 100.0],   # in-window (30D)
        45: [200.0],         # out of window — must be dropped from average
    })

    with patch("pokequant.scraper.fetch_sales", return_value=sales), \
         patch("api.index._lookup_card_meta", return_value={}), \
         patch("api.index._extract_sources", return_value=[]):
        from api.index import _handle_history
        result = _handle_history({"card": ["Test"], "days": ["30"]})

    assert result["summary"]["average"] == 100.0
    assert result["summary"]["in_window_count"] == 2


def test_average_differs_from_current_when_last_day_is_skewed(monkeypatch):
    """The whole point: a single recent outlier no longer becomes 'the price'."""
    monkeypatch.delenv("HOLO_USE_REGISTRY", raising=False)
    today = date.today()
    sales = _build_sales(today, {
        0: [25.0],                           # one sale today at $25 — was driving 'current'
        1: [12.0, 13.0, 11.0, 12.0, 13.0],
        3: [12.0, 13.0, 11.0],
        5: [12.0, 11.0, 13.0],
    })

    with patch("pokequant.scraper.fetch_sales", return_value=sales), \
         patch("api.index._lookup_card_meta", return_value={}), \
         patch("api.index._extract_sources", return_value=[]):
        from api.index import _handle_history
        result = _handle_history({"card": ["Test"], "days": ["30"]})

    # current = today's median = $25 (the misleading number)
    assert result["summary"]["current"] == 25.0
    # average = real mean across all 12 sales — much closer to typical
    assert 12.0 <= result["summary"]["average"] <= 14.0
    assert result["summary"]["average"] != result["summary"]["current"]
