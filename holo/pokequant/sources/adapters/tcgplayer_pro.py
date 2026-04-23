"""TCGPlayer Pro API adapter — stub (multi-day partner approval).

Target: api.tcgplayer.com/catalog/ v1.39.0.

Operator setup:
  1. Apply at https://docs.tcgplayer.com/docs/welcome (multi-day
     approval — start this early if you want it)
  2. Set TCGPLAYER_PUBLIC_KEY, TCGPLAYER_PRIVATE_KEY
  3. Run the parity test (H-1.10 Step 3) against 10 liquid cards
  4. Flip HOLO_ADAPTER_TCGPLAYER_PRO=1 and decommission the
     tcgplayer_redirect hack in pokequant/scraper.py

Until approval lands, this stub reports "awaiting partner approval"
on /api?action=health so the setup gap is visible.
"""
from __future__ import annotations

from pokequant.sources.adapters._stub import CredentialStub
from pokequant.sources.priority import priority_for
from pokequant.sources.registry import registry as _registry


class TCGPlayerProAdapter(CredentialStub):
    name = "tcgplayer_pro"
    priority = priority_for("tcgplayer_pro")
    currency = "USD"
    required_env = ("TCGPLAYER_PUBLIC_KEY", "TCGPLAYER_PRIVATE_KEY")
    stub_reason = "TCGPlayer Pro partner program awaiting approval"


_registry.register(TCGPlayerProAdapter())
