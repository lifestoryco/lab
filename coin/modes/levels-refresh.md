# Mode — `/coin levels-refresh`

Quarterly walk-through to refresh `data/levels_seed.yml`. Levels.fyi is
NOT auto-scraped — this mode is human-in-the-loop, surfaced when Sean
runs the command directly.

## When this fires

- User invocation: `/coin levels-refresh`

That is the only trigger. It is never invoked by another mode.

## Workflow

### Step 1 — Find stale entries

```bash
.venv/bin/python -c "from careerops.levels import flag_stale; \
    print('\n'.join(flag_stale(90)) or 'NONE')"
```

If the output is `NONE`, print:

```
Seed is fresh — every entry < 90 days old.
Next refresh due: <oldest entry's last_refreshed + 90 days>
```

…and exit. Do nothing else.

### Step 2 — Walk each stale company

For each company in the stale list, in order, do this:

1. **Print the current seed entry** so Sean sees what he's about to
   replace. Read it from `data/levels_seed.yml` directly.
2. **Surface the source URL.** It's stored as `source_url` on the
   entry. Tell Sean the URL — do not click it for him. He opens it in
   a browser, reads the current numbers, and pastes them back.
3. **Ask for the bands per level.** For each level the company's
   ladder publishes, run an `AskUserQuestion` block with one entry per
   band field:

   - `base_p25 (USD)`
   - `base_p50 (USD)`
   - `base_p75 (USD)`
   - `rsu_4yr_p50 (USD, total grant — Levels.fyi shows annualized;
     multiply by 4)`
   - `bonus_p50 (USD)`

   If Levels.fyi only exposes the median for a level, set
   `base_p25 = base_p50 = base_p75` (point estimate, no spread). The
   YAML header documents this convention.
4. **Atomic update.** After Sean confirms the bands, update the YAML
   in-place. Set `last_refreshed: <today's ISO date>`. Preserve the
   ordering of other companies — only edit this one entry.
5. **If Sean answers "skip"** for a level (or for the whole entry),
   do NOT mark `last_refreshed`. The next refresh run will surface it
   again.
6. **If Sean answers "company has no Levels.fyi data"**, set
   `unknown: true` on the entry (drop any existing `levels` key) and
   bump `last_refreshed`. The lookup function honors `unknown: true`
   by returning None, so this is the honest "checked, no data" state.

### Step 3 — Summary

After the loop completes, print:

```
Refreshed: <N>
Skipped: <M>
Marked unknown: <K>

Next refresh due: <today + 90 days>
```

…and exit.

## Non-goals

- **Does NOT scrape Levels.fyi.** That's a TOS gray area and brittle
  to UI churn. Sean reads the page; the agent transcribes his answers.
- **Does NOT modify scoring weights.** The confidence haircut formula
  in `careerops/score.py::score_comp` is a deliberate honesty discount.
  Don't touch it from this mode.
- **Does NOT touch role rows.** New imputations only fire on the next
  `/coin discover` pass via the `pipeline.upsert_role` hook.

## v2.1 notes

The current implementation is fully manual: agent reads the YAML,
asks Sean for numbers, edits the file. A future iteration may add
`scripts/levels_refresh.py` for batch operation (e.g. "refresh
everything older than 180 days non-interactively from a CSV"). That
isn't necessary until the seed has 50+ entries and quarterly attention
becomes painful.

## Self-checks

After updating the YAML, validate it:

```bash
.venv/bin/python -c "import yaml; \
    yaml.safe_load(open('data/levels_seed.yml')); print('YAML OK')"
.venv/bin/python -c "from careerops.levels import _reset_cache, lookup_company; \
    _reset_cache(); print(lookup_company('<company>') is not None)"
```

If either fails, restore from `git diff` before exiting — leave the
seed in a parseable state.
