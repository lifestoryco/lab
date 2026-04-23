"""Credential-gated stub adapters — registry discovery + health semantics."""
from __future__ import annotations

import pytest

from pokequant.sources.registry import SourceRegistry


EXPECTED_STUB_NAMES = {
    "bgs_pop",
    "cardmarket",
    "goldin",
    "limitless",
    "ebay_api",
    "tcgplayer_pro",
    "card_ladder",
}


@pytest.fixture
def fresh_registry():
    # Use the module-level singleton but ensure discover ran.
    from pokequant.sources import registry
    registry.discover()
    return registry


def test_all_stubs_register(fresh_registry):
    names = {a.name for a in fresh_registry.all_adapters()}
    missing = EXPECTED_STUB_NAMES - names
    assert not missing, f"stubs missing from registry: {missing}"


def test_stubs_are_disabled_by_default(fresh_registry):
    for name in EXPECTED_STUB_NAMES:
        a = fresh_registry.get_adapter(name)
        assert a is not None, name
        # bgs_pop / cardmarket / ebay_api / tcgplayer_pro / card_ladder / limitless / goldin
        # Limitless is enabled_by_default=False until meta_signal endpoint lands
        assert a.enabled_by_default is False, f"{name} should be disabled-by-default"


def test_stub_fetch_returns_empty(fresh_registry):
    a = fresh_registry.get_adapter("ebay_api")
    assert a is not None
    assert list(a.fetch("Charizard", days=30, grade="raw")) == []


def test_stub_health_surfaces_missing_creds(fresh_registry, monkeypatch):
    # Ensure no creds set
    for v in ("EBAY_APP_ID", "EBAY_CERT_ID"):
        monkeypatch.delenv(v, raising=False)
    a = fresh_registry.get_adapter("ebay_api")
    hc = a.health_check()
    assert hc["ok"] is False
    assert "EBAY_APP_ID" in hc["error"] or "EBAY_CERT_ID" in hc["error"]


def test_stub_is_configured_requires_all_creds(monkeypatch, fresh_registry):
    monkeypatch.setenv("HOLO_ADAPTER_CARDMARKET", "1")
    for v in ("CARDMARKET_APP_TOKEN", "CARDMARKET_APP_SECRET",
              "CARDMARKET_ACCESS_TOKEN", "CARDMARKET_ACCESS_TOKEN_SECRET"):
        monkeypatch.delenv(v, raising=False)
    a = fresh_registry.get_adapter("cardmarket")
    # Even with feature flag on, missing creds keeps is_configured False
    assert a.is_configured() is False
