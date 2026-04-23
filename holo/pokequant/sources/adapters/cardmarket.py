"""Cardmarket adapter — stub (OAuth 1.0 HMAC-SHA1).

When credentials land, adapter returns EUR-denominated NormalizedSale
records. The reconciler handles EUR→USD FX normalization; adapter stays
currency-native.

Operator setup:
  1. Register at https://www.cardmarket.com/en/Magic/Account/API
  2. Set CARDMARKET_APP_TOKEN, CARDMARKET_APP_SECRET,
     CARDMARKET_ACCESS_TOKEN, CARDMARKET_ACCESS_TOKEN_SECRET in Vercel
     (Production + Preview, Sensitive)
  3. Flip HOLO_ADAPTER_CARDMARKET=1
"""
from __future__ import annotations

from pokequant.sources.adapters._stub import CredentialStub
from pokequant.sources.priority import priority_for
from pokequant.sources.registry import registry as _registry


class CardmarketAdapter(CredentialStub):
    name = "cardmarket"
    priority = priority_for("cardmarket")
    currency = "EUR"
    required_env = (
        "CARDMARKET_APP_TOKEN",
        "CARDMARKET_APP_SECRET",
        "CARDMARKET_ACCESS_TOKEN",
        "CARDMARKET_ACCESS_TOKEN_SECRET",
    )
    stub_reason = "Cardmarket OAuth 1.0 app registration required"


_registry.register(CardmarketAdapter())
