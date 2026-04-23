"""Goldin + PWCC auction-comp adapter — stub.

High-value only (cards with median > $500 per the task spec). Goldin
has a semi-documented JSON search endpoint; PWCC is HTML-scrape.

Emits source_type="sale", confidence=0.95 (auction with buyer's premium
disclosed in extra). Activation requires confirming current endpoint
URLs/selectors — site redesigns happen quarterly.
"""
from __future__ import annotations

from pokequant.sources.adapters._stub import CredentialStub
from pokequant.sources.priority import priority_for
from pokequant.sources.registry import registry as _registry


class GoldinAdapter(CredentialStub):
    name = "goldin"
    priority = priority_for("goldin")
    currency = "USD"
    required_env = ()  # No auth; disabled until endpoint URLs verified
    stub_reason = "endpoint URLs not yet verified; enable only for $500+ cards"


_registry.register(GoldinAdapter())
