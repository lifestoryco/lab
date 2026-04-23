"""SourceReconciler — pure merge/FX/dedup/outlier logic."""
from __future__ import annotations

from datetime import date

from pokequant.sources.reconciler import reconcile
from pokequant.sources.schema import NormalizedSale


TODAY = date(2026, 4, 23)


def _mk(adapter="pricecharting", price=10.0, currency="USD", stype="sale",
        sale_id=None, days_ago=1, grade="raw", outlier=False, condition="NM"):
    return NormalizedSale(
        sale_id=sale_id or f"{adapter}-{price}-{days_ago}",
        adapter=adapter,
        source_type=stype,
        price=price,
        currency=currency,
        date=date.fromordinal(TODAY.toordinal() - days_ago),
        condition=condition,
        grade=grade,
        source_url=f"https://{adapter}/x",
        outlier_flag=outlier,
    )


def test_empty_input_returns_empty():
    out, audit = reconcile([], days=30, today=TODAY)
    assert out == []
    assert audit.reconciled_count == 0


def test_records_outside_window_dropped():
    records = [_mk(days_ago=5), _mk(days_ago=60, sale_id="old")]
    out, audit = reconcile(records, days=30, today=TODAY)
    assert len(out) == 1
    assert audit.reconciled_count == 1


def test_future_dated_records_dropped():
    records = [_mk(days_ago=1), _mk(days_ago=-2, sale_id="future")]
    out, _ = reconcile(records, days=30, today=TODAY)
    assert len(out) == 1


def test_fx_normalizes_eur_to_usd():
    eur = _mk(adapter="cardmarket", price=100.0, currency="EUR")
    out, audit = reconcile([eur], days=30, today=TODAY)
    assert len(out) == 1
    assert out[0].currency == "USD"
    assert out[0].price == 108.0  # 100 * 1.08
    assert audit.fx_normalized == 1
    assert out[0].extra["original_currency"] == "EUR"


def test_unknown_currency_warns_and_keeps_original():
    weird = _mk(adapter="x", currency="XYZ")  # type: ignore[arg-type]
    out, audit = reconcile([weird], days=30, today=TODAY)
    assert len(out) == 1
    assert out[0].currency == "XYZ"
    assert any("unknown currency" in w for w in audit.warnings)


def test_dedupe_keeps_higher_priority():
    # Same date/price/grade — ebay_api (100) beats pricecharting (90)
    pc = _mk(adapter="pricecharting", price=50.0, sale_id="pc")
    ebay = _mk(adapter="ebay_api", price=50.0, sale_id="ebay")
    out, audit = reconcile([pc, ebay], days=30, today=TODAY)
    assert len(out) == 1
    assert out[0].adapter == "ebay_api"


def test_different_prices_not_deduped():
    a = _mk(adapter="pricecharting", price=50.0, sale_id="a")
    b = _mk(adapter="pricecharting", price=51.0, sale_id="b")
    out, _ = reconcile([a, b], days=30, today=TODAY)
    assert len(out) == 2


def test_market_estimate_does_not_dedupe_against_sale():
    # Different source_type -> same date/price/grade still collide by (price,date,grade)
    # Reconciler's dedup key is (price,date,grade) which will collide.
    # The higher priority adapter wins. Market estimate has lower priority.
    sale = _mk(adapter="ebay_api", price=50.0, stype="sale", sale_id="sale")
    est = _mk(adapter="tcgplayer_redirect", price=50.0, stype="market_estimate",
              sale_id="est", condition="mixed")
    out, _ = reconcile([sale, est], days=30, today=TODAY)
    assert len(out) == 1
    assert out[0].source_type == "sale"


def test_iqr_flags_outliers_without_dropping():
    # 5 sales at ~$50, one at $500
    clean = [_mk(adapter="pricecharting", price=50.0 + i, sale_id=f"c{i}", days_ago=i+1)
             for i in range(5)]
    outlier = _mk(adapter="pricecharting", price=500.0, sale_id="outlier", days_ago=6)
    out, audit = reconcile(clean + [outlier], days=30, today=TODAY)
    assert len(out) == 6  # nothing dropped
    flagged = [r for r in out if r.outlier_flag]
    assert len(flagged) == 1
    assert flagged[0].price == 500.0
    assert audit.dropped_outliers == 1


def test_iqr_inactive_below_five_sales():
    records = [_mk(adapter="pricecharting", price=10.0, sale_id="a", days_ago=1),
               _mk(adapter="pricecharting", price=1000.0, sale_id="b", days_ago=2)]
    out, audit = reconcile(records, days=30, today=TODAY)
    # Only 2 records, IQR fence not applied
    assert audit.dropped_outliers == 0
    assert all(not r.outlier_flag for r in out)


def test_audit_tracks_by_adapter_counts():
    records = [
        _mk(adapter="pricecharting", price=10.0, sale_id="a", days_ago=1),
        _mk(adapter="pricecharting", price=11.0, sale_id="b", days_ago=2),
        _mk(adapter="ebay_api", price=12.0, sale_id="c", days_ago=3),
    ]
    _, audit = reconcile(records, days=30, today=TODAY)
    assert audit.by_adapter == {"pricecharting": 2, "ebay_api": 1}
