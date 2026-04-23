"""BGS Pop Report adapter — stub.

Beckett's pop-report endpoint requires session auth and has lower
industry coverage than PSA. Disabled by default; fill in the parser +
auth when BGS data demand surfaces.
"""
from __future__ import annotations

from pokequant.sources.adapters._stub import CredentialStub
from pokequant.sources.priority import priority_for
from pokequant.sources.registry import registry as _registry


class BGSPopAdapter(CredentialStub):
    name = "bgs_pop"
    priority = priority_for("bgs_pop")
    currency = "USD"
    required_env = ("BECKETT_SESSION_COOKIE",)
    stub_reason = "BGS pop report requires logged-in session cookie"


_registry.register(BGSPopAdapter())
