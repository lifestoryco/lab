"""Confirm the legacy fetch_sales path supplements with 130point records."""
from __future__ import annotations

from datetime import date
from unittest.mock import patch

from pokequant.sources.schema import NormalizedSale


def _fake_130_record(price: float, days_ago: int = 1, sale_id: str = "abc") -> NormalizedSale:
    return NormalizedSale(
        sale_id=sale_id,
        adapter="130point",
        source_type="sale",
        price=price,
        currency="USD",
        date=date.fromordinal(date.today().toordinal() - days_ago),
        condition="NM",
        grade="raw",
        source_url="https://130point/x",
        confidence=0.9,
    )


def test_130point_supplements_legacy_for_raw_grade(monkeypatch):
    """fetch_sales raw-grade call supplements PC+eBay with 130point records."""
    monkeypatch.delenv("HOLO_USE_REGISTRY", raising=False)  # force legacy path

    from pokequant.scraper import fetch_sales

    pc_sales = [
        {"sale_id": "pc-1", "price": 100.0, "date": "2026-04-01",
         "condition": "NM", "source": "pricecharting"},
    ]

    fake_130 = [
        _fake_130_record(price=105.0, sale_id="o1"),
        _fake_130_record(price=110.0, sale_id="o2"),
    ]

    with patch("pokequant.scraper._scrape_pricecharting", return_value=pc_sales), \
         patch("pokequant.scraper._scrape_ebay", return_value=[]), \
         patch("pokequant.sources.registry.SourceRegistry.discover"), \
         patch("pokequant.sources.registry.SourceRegistry.get_adapter") as mock_get:
        # Configure the adapter mock to look enabled and return 130point records
        mock_adapter = mock_get.return_value
        mock_adapter.is_configured.return_value = True
        mock_adapter.fetch.return_value = fake_130

        result = fetch_sales("test card", days=30, grade="raw", use_cache=False)

    assert isinstance(result, list)
    sources = {s.get("source") for s in result}
    assert "130point" in sources, f"expected 130point in sources, got {sources}"
    prices = sorted(float(s["price"]) for s in result)
    assert 105.0 in prices and 110.0 in prices


def test_130point_not_called_for_graded_request(monkeypatch):
    """Graded queries skip 130point — its site returns mixed grades."""
    monkeypatch.delenv("HOLO_USE_REGISTRY", raising=False)

    from pokequant.scraper import fetch_sales

    pc_sales = [
        {"sale_id": "pc-1", "price": 200.0, "date": "2026-04-01",
         "condition": "PSA 10", "source": "pricecharting"},
    ]

    with patch("pokequant.scraper._scrape_pricecharting", return_value=pc_sales), \
         patch("pokequant.sources.registry.SourceRegistry.get_adapter") as mock_get:
        result = fetch_sales("test card", days=30, grade="psa10", use_cache=False)

    # get_adapter should not have been called at all for graded paths
    mock_get.assert_not_called()
    assert isinstance(result, list)


def test_130point_supplement_dedupes_on_price_and_date(monkeypatch):
    """130point records matching PC on (price, date) are dropped as dupes."""
    monkeypatch.delenv("HOLO_USE_REGISTRY", raising=False)

    from pokequant.scraper import fetch_sales

    today = date.today().isoformat()
    pc_sales = [
        {"sale_id": "pc-1", "price": 50.0, "date": today,
         "condition": "NM", "source": "pricecharting"},
    ]

    fake_130 = [
        _fake_130_record(price=50.0, days_ago=0, sale_id="dup"),     # same price+date → drop
        _fake_130_record(price=55.0, days_ago=0, sale_id="keep"),    # different → keep
    ]

    with patch("pokequant.scraper._scrape_pricecharting", return_value=pc_sales), \
         patch("pokequant.scraper._scrape_ebay", return_value=[]), \
         patch("pokequant.sources.registry.SourceRegistry.discover"), \
         patch("pokequant.sources.registry.SourceRegistry.get_adapter") as mock_get:
        mock_adapter = mock_get.return_value
        mock_adapter.is_configured.return_value = True
        mock_adapter.fetch.return_value = fake_130

        result = fetch_sales("test card", days=30, grade="raw", use_cache=False)

    sources = {s.get("source") for s in result}
    assert "130point" in sources
    # We expect 2 total: 1 PC + 1 non-duplicate 130point (the $50 dupe was dropped)
    assert len(result) == 2
    prices = sorted(float(s["price"]) for s in result)
    assert prices == [50.0, 55.0]


def test_130point_adapter_failure_does_not_break_legacy(monkeypatch):
    """130point raising an exception must not affect PC+eBay results."""
    monkeypatch.delenv("HOLO_USE_REGISTRY", raising=False)

    from pokequant.scraper import fetch_sales

    pc_sales = [
        {"sale_id": "pc-1", "price": 100.0, "date": "2026-04-01",
         "condition": "NM", "source": "pricecharting"},
    ]

    with patch("pokequant.scraper._scrape_pricecharting", return_value=pc_sales), \
         patch("pokequant.scraper._scrape_ebay", return_value=[]), \
         patch("pokequant.sources.registry.SourceRegistry.discover"), \
         patch("pokequant.sources.registry.SourceRegistry.get_adapter") as mock_get:
        mock_adapter = mock_get.return_value
        mock_adapter.is_configured.return_value = True
        mock_adapter.fetch.side_effect = RuntimeError("403 Forbidden")

        result = fetch_sales("test card", days=30, grade="raw", use_cache=False)

    # PC sale still present; no crash
    assert isinstance(result, list)
    assert len(result) >= 1
    assert result[0]["source"] == "pricecharting"
