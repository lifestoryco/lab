"""Card Ladder adapter — stub ($99/mo paid partner API).

Scope: signal-validation / backtesting only. Dormant until H-1.5
(backtesting harness) is scoped AND operator has approved the
subscription spend.

DO NOT subscribe without explicit approval-to-spend confirmation.
"""
from __future__ import annotations

from pokequant.sources.adapters._stub import CredentialStub
from pokequant.sources.priority import priority_for
from pokequant.sources.registry import registry as _registry


class CardLadderAdapter(CredentialStub):
    name = "card_ladder"
    priority = priority_for("card_ladder")
    currency = "USD"
    required_env = ("CARDLADDER_API_KEY",)
    stub_reason = "Card Ladder requires paid subscription ($99/mo) — awaiting approval"


_registry.register(CardLadderAdapter())
