# Multi-Source Price Intelligence — Architecture

Status as of 2026-04-23 (post H-1.10 + H-1.10a).

## Why this exists

The old `fetch_sales()` was a linear `if/elif` cascade of four scrapers
(PriceCharting → eBay HTML → TCGPlayer redirect → pokemontcg.io synth).
Each was fragile, each integration was ad hoc, there was no normalized
record schema, no cross-source reconciliation, and no per-source health
metric. April 2026's silent eBay DOM break (`s-item` → `s-card`) went
undetected because the handler returned `[]` and the UI just said "no
sales found."

The adapter framework replaces that cascade with a registry of uniform
adapters. Every adapter emits `NormalizedSale` records. A pure
reconciler merges / FX-normalizes / dedupes / outlier-flags. A health
endpoint surfaces per-source status. New data sources add zero
branching to the existing handlers — they drop a file in
`pokequant/sources/adapters/` and register at import.

## Package layout

```
pokequant/sources/
├── __init__.py              # public surface: registry, NormalizedSale, LAST_AUDIT
├── schema.py                # NormalizedSale dataclass + Currency/Grade/SourceType
├── base.py                  # SourceAdapter ABC
├── registry.py              # SourceRegistry (discovery + parallel fan-out + invariants)
├── reconciler.py            # Pure merge/FX/dedup/IQR-outlier
├── priority.py              # ADAPTER_PRIORITY tie-break table
├── fx.py                    # Static EUR/GBP/JPY -> USD
├── exceptions.py            # InvalidSaleRecord, AdapterTimeout, AdapterNotConfigured
└── adapters/
    ├── __init__.py          # package marker
    ├── _stub.py             # Shared base for credential-gated stubs
    ├── psa_pop.py           # [LIVE] PSA Pop Report scraper
    ├── onethreezero_point.py# [LIVE] 130point sale aggregator
    ├── bgs_pop.py           # [STUB] BGS Pop Report
    ├── cardmarket.py        # [STUB] Cardmarket OAuth 1.0 (EUR)
    ├── goldin.py            # [STUB] Goldin/PWCC auction comps (>$500)
    ├── limitless.py         # [STUB] Tournament meta signals
    ├── ebay_api.py          # [STUB] eBay Browse API (OAuth 2.0)
    ├── tcgplayer_pro.py     # [STUB] TCGPlayer Pro (partner)
    └── card_ladder.py       # [STUB] Card Ladder (paid $99/mo)
```

## Fetch path (HOLO_USE_REGISTRY=1)

```
request
  │
  ▼
api/index.py::_handle_history (or _handle_flip, etc.)
  │
  ▼
pokequant.scraper.fetch_sales(card, days, grade)         ← dispatcher
  │   clears LAST_AUDIT contextvar; reads HOLO_USE_REGISTRY
  │
  ├── HOLO_USE_REGISTRY=0 (default) ──► _fetch_sales_legacy(...)   ← PC + eBay + TCGPlayer cascade
  │
  └── HOLO_USE_REGISTRY=1 ──► _fetch_sales_via_registry(...)
          │
          ├── registry.discover()                         ← lazy, idempotent
          │
          ├── registry.fetch_all(...)                     ← ThreadPoolExecutor fan-out,
          │     │                                             12s per-adapter timeout
          │     │
          │     ├── PSAPopAdapter.fetch() ─────────┐
          │     ├── OneThirtyPointAdapter.fetch() ─┤
          │     ├── [stubs return []]              │
          │     │                                  ▼
          │     │                          Each adapter calls registry's
          │     │                          _validate(record) on ingress; invalid
          │     │                          records dropped with WARN log.
          │     │                          Valid records stamped with fetched_at.
          │     │
          │     └── Metrics emitted as JSON to stderr:
          │         {ts, event:"adapter.fetch", adapter, card, count, latency_ms, error}
          │
          ├── reconciler.reconcile(records, days=days)
          │     │   Pure function:
          │     │   1. Drop records outside [today - days, today]
          │     │   2. FX-normalize non-USD to USD (static rates)
          │     │   3. Dedupe on (round(price,2), date, grade) — highest priority wins
          │     │   4. IQR fence over sale records (>=5) — mark but don't drop
          │     │   Returns (records, ReconciliationAudit)
          │
          ├── LAST_AUDIT.set(audit)                        ← contextvar for handler
          │
          └── return [r.to_dict() for r in records]        ← same shape as legacy
                                                              fallback to legacy on empty
```

The legacy path stays intact at `_fetch_sales_legacy()` — a one-line
swap restores full service if the registry path proves unstable. Kill
switch is `HOLO_USE_REGISTRY=0`, no deploy required.

## `NormalizedSale` invariants

Enforced by `registry._validate()` on every record an adapter emits:

- `0 < price < 1_000_000`
- `currency ∈ {USD, EUR, GBP, JPY}`
- `grade ∈ {raw, psa10, psa9, psa8, bgs10, bgs9.5, cgc10, cgc9}`
- `source_type ∈ {sale, market_estimate, pop_report, meta_signal}`
- `source_type=="sale"` forbids `condition="mixed"`
- `condition=="mixed"` is only allowed on `source_type=="market_estimate"`
- `lot_size>1` requires `source_type=="sale"`

Violation → `InvalidSaleRecord`, record dropped, WARN log carrying the
adapter name.

## Adapter priority (dedup tie-break)

Higher wins when two adapters produce records with matching
(price, date, grade). Thresholds:

| Tier | Priority | Adapters |
|------|----------|----------|
| Authoritative sales | ≥70 | `ebay_api`(100), `pricecharting`(90), `130point`(85), `ebay_html`(80), `goldin`(75), `cardmarket`(70) |
| Market estimates | 30–69 | `tcgplayer_pro`(60), `tcgplayer_redirect`(50), `pricecharting_static`(40), `pokemontcg_synth`(30) |
| Meta signals | ≤29 | `card_ladder`(20), `limitless`(10), `psa_pop`(5), `bgs_pop`(5) |

Market-estimate records never enter the sale median (session-10 rule).

## Reconciliation audit

Every registry-path call populates `LAST_AUDIT` — a contextvar carrying
the `ReconciliationAudit` for the most recent `fetch_sales()`. API
handlers surface it via `_current_audit()`:

```json
{
  "reconciliation_audit": {
    "reconciled_count": 47,
    "by_adapter": {"pricecharting": 28, "130point": 15, "psa_pop": 1, "ebay_html": 3},
    "dropped_outliers": 2,
    "fx_normalized": 0,
    "warnings": []
  }
}
```

Visible on `/api?action=history` and `/api?action=flip`. `_handle_movers`
is intentionally unwired — fan-out workers overwrite the contextvar per
card; meaningful aggregation is future work.

## Health endpoint

`GET /api?action=health` → iterates the registry, calls each adapter's
`health_check()`, returns:

```json
{
  "adapters": [
    {"name": "psa_pop", "priority": 5, "configured": true,
     "enabled_by_default": true, "ok": true, "latency_ms": 123.4, "error": null},
    {"name": "ebay_api", "priority": 100, "configured": false,
     "enabled_by_default": false, "ok": false, "latency_ms": 0.0,
     "error": "eBay Developer production scope + OAuth 2.0 approval required: missing EBAY_APP_ID, EBAY_CERT_ID"}
  ],
  "summary": {"total": 9, "configured": 2, "healthy": 2}
}
```

Cache-Control: `s-maxage=30`. Stubs report their exact missing
credential so the setup gap is visible without reading source.

## Feature flags

Per-adapter: `HOLO_ADAPTER_<NAME>=0` disables, `=1` forces on. Default
is the adapter's `enabled_by_default`. Stubs ignore the flag when
credentials are missing.

Global: `HOLO_USE_REGISTRY=1` routes `fetch_sales()` through the
registry path. Default `0` preserves legacy behavior. Flip only after
the parity test passes: `HOLO_RUN_PARITY=1 pytest
tests/test_fetch_sales_parity.py`.

## Observability

Every adapter call emits one JSON line to stderr:

```
{"ts": 1713831123.4, "event": "adapter.fetch", "adapter": "pricecharting",
 "card": "charizard-vmax-20", "count": 23, "latency_ms": 1847, "error": null}
```

Grep the Vercel function logs for `"event": "adapter.fetch"` to see
real-time per-adapter volume and latency. The `error` field is `null`
on success or a 200-char-truncated error message on failure.

## Testing

- `tests/test_sources_schema.py` — 10 invariant-enforcement tests
- `tests/test_sources_reconciler.py` — 11 reconciler-algorithm tests
- `tests/test_sources_psa_pop.py` — 8 PSA Pop parser + mock tests
- `tests/test_sources_130point.py` — 8 130point parser tests
- `tests/test_sources_stubs.py` — 5 stub registration + health tests
- `tests/test_audit_plumbing.py` — 5 LAST_AUDIT contextvar tests
- `tests/test_fetch_sales_parity.py` — 4 offline + 5 live-gated parity tests

Full suite: 122 passed, 10 skipped (live canary + live parity).

`mypy --strict --ignore-missing-imports pokequant/sources/` → 0 issues.

## Rollback

**Instant (no deploy):**
```
vercel env add HOLO_USE_REGISTRY 0 production
vercel redeploy
```

**Per-adapter:**
```
vercel env add HOLO_ADAPTER_130POINT 0 production
```

**Code-level (if imports are broken):**
```
git revert <commit>   # _fetch_sales_legacy is still wired, no data loss
```
