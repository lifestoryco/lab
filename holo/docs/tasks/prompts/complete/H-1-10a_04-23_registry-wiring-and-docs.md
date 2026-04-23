# H-1.10a — Multi-source registry: production wiring + frontend provenance + docs

**Priority:** Medium (completes the refactor)
**Effort:** MED
**Follows:** H-1.10 (foundation + free adapters + stubs) landed session 11

## Context

H-1.10 session 11 shipped:
- `pokequant/sources/` foundation (schema, registry, reconciler, FX, priority, exceptions)
- `fetch_sales()` parity shim behind `HOLO_USE_REGISTRY=0` (default off)
- PSA Pop Report + 130point free adapters
- 7 credential-gated stubs (cardmarket, goldin, limitless, ebay_api, tcgplayer_pro, card_ladder, bgs_pop)
- `/api?action=health` endpoint
- 46 new tests, 113 total passing

What H-1.10 deliberately deferred to this follow-up:

## Scope

### 1. Wire reconciliation_audit into /history, /flip, /movers

When `HOLO_USE_REGISTRY=1`, expose the reconciler's audit payload in:
- `_handle_history` → add `reconciliation_audit` field to response
- `_handle_flip`   → same
- `_handle_movers` → per-card audit in the movers payload

Keep `data_quality_warning` derived from `market_estimate / total_sales` ratio
at the 30% threshold (session-10 rule preserved).

### 2. Frontend "Data provenance" panel

In `handoffpack-www/components/lab/holo/HoloPage.tsx`: a collapsible
panel under the existing `data_quality_warning` chip. Displays the
`by_adapter` map with per-source counts. Defaults collapsed.

### 3. Parity test (Step 3 validation gate)

`tests/test_fetch_sales_parity.py` — 5 canary cards run through both
legacy and registry paths with identical adapters enabled (PC + eBay
simulated via PSA Pop + 130point). Assert price distributions within
5% of each other. Required **before** flipping `HOLO_USE_REGISTRY=1`
in production.

### 4. mypy --strict on pokequant/sources/

Add a strict mypy pass to CI or a pre-commit step. All new foundation
code should type-check clean.

### 5. Full Step 15 docs pass

- New `docs/architecture/sources.md` with the spec + priority table +
  fetch-path diagram (copy from H-1.10 prompt, update per what actually
  shipped)
- Update `CLAUDE.md` "Data Sources" section — list all 11 adapters
  (2 live, 7 stubs, 2 legacy) with feature flag + credential status

### 6. Meta-signal endpoint

`/api?action=meta_signal&card=X` — consumes the Limitless adapter when
it gets fleshed out. Overlaps roadmap item H-1.3 (tournament meta-shift
signal). If H-1.3 gets scoped first, fold this into that work.

## Out of scope

- Activating credential-gated adapters — each needs its own operator
  signup flow (eBay Developer, TCGPlayer partner, Cardmarket OAuth,
  Card Ladder paid). File separate H-1.10b/c/... prompts when creds are
  provisioned.
- Flipping `HOLO_USE_REGISTRY=1` in production — depends on parity test
  (scope item 3) passing. That test is the gate.

## Verification

```bash
.venv/bin/pytest tests/ -q                # no regression
.venv/bin/pytest tests/test_fetch_sales_parity.py -v  # parity gate
curl '.../api?action=health' | jq         # all enabled adapters ok
curl '.../api?action=history&card=...' | jq '.reconciliation_audit'
```

## Success criteria

- [ ] Audit payload visible in /history, /flip, /movers responses
- [ ] Frontend panel rendering; collapsed by default
- [ ] Parity test passes with <5% delta on all 5 canary cards
- [ ] mypy --strict green on pokequant/sources/
- [ ] docs/architecture/sources.md committed; CLAUDE.md updated
- [ ] `HOLO_USE_REGISTRY=1` flipped in Vercel production after parity
      gate; kill-switch documented

## Commits expected

1. `feat(api): wire reconciliation_audit into /history, /flip, /movers`
2. `feat(lab/holo): Data provenance panel on card detail`
3. `test(sources): fetch_sales parity test — legacy vs registry`
4. `docs: multi-source architecture + CLAUDE.md data-sources section`
5. `ops: flip HOLO_USE_REGISTRY=1 in production` (after parity gate)
