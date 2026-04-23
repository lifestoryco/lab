# H-1.10a-ui — Data provenance panel on card detail

**Priority:** Low (polish)
**Effort:** LOW
**Follows:** H-1.10a (backend audit wiring landed session 12)
**Lives in:** `handoffpack-www` — cross-repo

## Context

Backend for `reconciliation_audit` is live on `/api?action=history` and
`/api?action=flip` (session 12, H-1.10a). The response shape is:

```json
{
  "reconciliation_audit": {
    "reconciled_count": 47,
    "by_adapter": {"pricecharting": 28, "130point": 15, "psa_pop": 1},
    "dropped_outliers": 2,
    "fx_normalized": 0,
    "warnings": []
  } | null
}
```

The field is `null` when `HOLO_USE_REGISTRY=0` (default) served the
request. The UI should render nothing in that case.

## Scope

In `handoffpack-www/components/lab/holo/HoloPage.tsx`:

1. Add a `ReconciliationAudit` TS interface matching the payload shape
   above.
2. Add an optional `reconciliationAudit: ReconciliationAudit | null`
   prop / state on the CardDetail view's existing response consumer.
3. Below the existing `data_quality_warning` chip (near the Sales feed
   header), add a collapsible `<details>` panel titled
   **"Data provenance"**.
4. Content (when expanded): a small table of `by_adapter` entries
   sorted by count desc, plus three one-line stats
   (`reconciled_count`, `dropped_outliers`, `fx_normalized`). Warnings
   list rendered as red bullets if non-empty.
5. Panel hidden when `reconciliationAudit` is `null` — no visual noise
   during legacy-path responses.

## Design hints

Match the existing panel aesthetic: Fraunces caps label, glass panel,
violet accent (different from TopMovers' gold and data_quality's red).
Keep it <120px tall when expanded.

## Out of scope

- Exposing adapter latency (belongs on an admin-only `/health` surface).
- Per-adapter drill-down (future work — H-1.10b if it matters).

## Verification

- `handoffpack-www` dev server: visit a card detail while
  `HOLO_USE_REGISTRY=1` on the backend → panel renders with real counts.
- With `HOLO_USE_REGISTRY=0` (production default today) → panel is
  absent, no regression in existing UI.

## Commits

Single commit: `feat(lab/holo): data provenance panel on card detail`
