"""Reconciliation audit plumbing — LAST_AUDIT contextvar + handler exposure."""
from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest

from pokequant.sources import LAST_AUDIT
from pokequant.sources.reconciler import reconcile
from pokequant.sources.schema import NormalizedSale


TODAY = date.today()


def _mk(adapter="pricecharting", price=10.0):
    return NormalizedSale(
        sale_id=f"{adapter}-{price}",
        adapter=adapter,
        source_type="sale",
        price=price,
        currency="USD",
        date=TODAY,
        condition="NM",
        grade="raw",
        source_url=f"https://{adapter}/x",
    )


def test_last_audit_starts_none():
    LAST_AUDIT.set(None)
    assert LAST_AUDIT.get() is None


def test_reconciler_output_carries_counts():
    records = [_mk(price=10.0), _mk(price=11.0), _mk(adapter="ebay_api", price=12.0)]
    _, audit = reconcile(records, days=30, today=TODAY)
    assert audit.reconciled_count == 3
    assert audit.by_adapter["pricecharting"] == 2
    assert audit.by_adapter["ebay_api"] == 1


def test_audit_to_dict_roundtrip():
    records = [_mk(price=10.0)]
    _, audit = reconcile(records, days=30, today=TODAY)
    d = audit.to_dict()
    assert set(d.keys()) == {"reconciled_count", "by_adapter", "dropped_outliers",
                             "fx_normalized", "warnings"}
    assert d["reconciled_count"] == 1


def test_fetch_sales_registry_path_sets_last_audit(monkeypatch):
    """When HOLO_USE_REGISTRY=1, the registry path populates LAST_AUDIT."""
    LAST_AUDIT.set(None)
    monkeypatch.setenv("HOLO_USE_REGISTRY", "1")

    from pokequant.scraper import fetch_sales

    fake_records = [_mk(price=10.0), _mk(price=11.0)]

    with patch("pokequant.sources.registry.SourceRegistry.fetch_all",
               return_value=fake_records), \
         patch("pokequant.sources.registry.SourceRegistry.discover"):
        result = fetch_sales("test-card", days=30, grade="raw", use_cache=False)

    # Registry path returned a list (not legacy fallback)
    assert isinstance(result, list)
    audit = LAST_AUDIT.get()
    assert audit is not None
    assert audit.reconciled_count >= 1


def test_fetch_sales_legacy_path_clears_stale_audit(monkeypatch):
    """Legacy path must NOT leak a prior registry audit into its response."""
    # Simulate a stale audit from an earlier call
    from pokequant.sources.reconciler import ReconciliationAudit
    stale = ReconciliationAudit(reconciled_count=99)
    LAST_AUDIT.set(stale)

    monkeypatch.delenv("HOLO_USE_REGISTRY", raising=False)

    from pokequant.scraper import fetch_sales

    # Mock legacy to return a canned list so the call completes
    with patch("pokequant.scraper._fetch_sales_legacy", return_value=[]):
        fetch_sales("x", days=30, grade="raw", use_cache=False)

    # Dispatcher cleared the contextvar before dispatching
    assert LAST_AUDIT.get() is None
