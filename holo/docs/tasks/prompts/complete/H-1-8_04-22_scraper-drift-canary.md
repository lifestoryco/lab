# H-1.8 — Scraper drift canary + DOM-change alert

**Priority:** High (data integrity)
**Effort:** MED
**Surfaces the code-review H6 finding from 2026-04-22.**

## Problem

The PriceCharting 2026 redesign broke our scraper silently for an
unknown period in April. The fix landed retroactively
(`_extract_pricecharting_price_data` refactor). The current scraper
also has no tripwire for:
- eBay DOM class renames (already bit us once: `s-item` → `s-card`)
- pokemontcg.io API shape changes
- TCGPlayer infinite-api schema drift

When a selector stops matching, we emit a warn log and return `[]` —
the user just sees "No sales found" and assumes the card is obscure.

## Goal

Daily automated canary that hits every scraper path against a known-
good card and fails loudly if the parsed record count or price range
drifts beyond an acceptable band.

## Design

### 1. Canary targets (in `tests/canary.py`)

Five well-known, liquid cards with predictable data:
- `"Charizard VMAX 20"` (Darkness Ablaze) — always has recent sales
- `"Pikachu 58"` (Obsidian Flames) — common promo, high volume
- `"Umbreon VMAX 215"` (Evolving Skies) — alt art, $500+ range
- `"Giratina V 186"` (Lost Origin) — raw volume
- `"Mew VMAX 114"` (Fusion Strike) — we already have this in
  production Supabase so can compare

### 2. Per-card assertions

For each target, run `fetch_sales(card, days=30, grade="raw")` with
`use_cache=False` and check:
- `len(sales) >= 5` (empty result = scraper broken)
- `any(s["source"] == "pricecharting" for s in sales)` — PC working
- `any(s["source"] == "ebay" for s in sales)` — eBay working
- Median sale price within ±50% of the last-known median stored in
  `holo.canary_baseline` Supabase table (catches unit-scale bugs
  like price-text containing thousands separators)

### 3. Storage: `holo.canary_baseline`

New Supabase table:
```sql
CREATE TABLE holo.canary_baseline (
    card_slug TEXT PRIMARY KEY,
    grade TEXT NOT NULL,
    last_median NUMERIC(10, 2) NOT NULL,
    last_count INT NOT NULL,
    last_run_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_status TEXT NOT NULL  -- 'ok' | 'drift' | 'broken'
);
```

After each successful run, update the baseline (exponentially
weighted — don't just overwrite; `new = 0.7 * old + 0.3 * observed`
so a single noisy day doesn't move the fence).

### 4. Scheduler

Two options:
- **Vercel Cron** — add to `vercel.json` under `crons`:
  ```json
  { "path": "/api/canary", "schedule": "0 13 * * *" }
  ```
  Add `_handle_canary` in `api/index.py`.

- **GitHub Actions** (preferred for alerting):
  `.github/workflows/scraper-canary.yml` runs daily at 13:00 UTC,
  executes `pytest tests/canary.py -v`, and on failure posts to a
  webhook.

Use GitHub Actions — logs are free to keep, easy to inspect, and the
workflow file makes the contract visible in-repo.

### 5. Alerting

Webhook target configurable via env. For v1, post a formatted
message to a Slack/Discord webhook URL stored in a GitHub secret:

```yaml
- name: Notify on failure
  if: failure()
  run: |
    curl -X POST "${{ secrets.CANARY_WEBHOOK }}" \
      -H 'Content-Type: application/json' \
      -d '{"text":"🚨 Holo scraper canary failed — check recent deploys + upstream DOM changes"}'
```

### 6. Tests

The canary itself _is_ the test, so the bar is: does it exit non-
zero when a scraper path is broken, and zero otherwise.

Unit-test the median-drift check with synthetic data:
```python
def test_canary_fails_on_50pct_drift():
    baseline = 100.0
    observed = 40.0  # 60% drift
    assert _detect_drift(baseline, observed, tolerance=0.5) is True
```

## Rollout

1. Land canary code + GitHub workflow (disabled initially).
2. Run manually three times over 48h to populate `canary_baseline`.
3. Enable scheduled run + webhook.
4. Tune tolerance after one week of baseline noise.

## Out of scope

- Automatic fallback when a scraper breaks — that's a circuit
  breaker (H-1.10, future task).
- Alerting beyond webhook (PagerDuty, etc) — follow-on.

## Commits

Two commits expected:
1. `feat(holo): scraper drift canary + Supabase baseline table`
2. `ci(holo): daily scraper canary workflow + webhook alert`
