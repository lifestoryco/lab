"""eBay Browse API adapter — stub (OAuth 2.0 client credentials).

Target: api.ebay.com/buy/browse/v1/item_summary/search — official,
grade-filterable, 5000 calls/day free tier.

Operator setup:
  1. Register at https://developer.ebay.com/my/keys (free tier OK)
  2. Get EBAY_APP_ID, EBAY_CERT_ID, EBAY_DEV_ID
  3. Request production scope for buy.browse (1-day approval)
  4. Set Vercel env vars; flip HOLO_ADAPTER_EBAY_API=1

Migration: once live, move ebay_html to priority 30 so the reconciler
naturally prefers the API. A daily budget guard keyed on a Supabase
counter is part of the activation work, not this stub.
"""
from __future__ import annotations

from pokequant.sources.adapters._stub import CredentialStub
from pokequant.sources.priority import priority_for
from pokequant.sources.registry import registry as _registry


class EbayAPIAdapter(CredentialStub):
    name = "ebay_api"
    priority = priority_for("ebay_api")
    currency = "USD"
    required_env = ("EBAY_APP_ID", "EBAY_CERT_ID")
    stub_reason = "eBay Developer production scope + OAuth 2.0 approval required"


_registry.register(EbayAPIAdapter())
