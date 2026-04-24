# Mode: discover

Find high-compensation roles across Sean's five archetypes, filter by comp
floor, compute fit scores, and present the top results.

## Inputs

- None (default: all five archetypes, limit 15 each)
- Or: `lane=<archetype_id>` and/or `limit=<N>` and/or `location="..."`

## Steps

1. **Load shared context:** `modes/_shared.md` rubric and archetype list.

2. **Run the discover script.** Invoke Python — it handles scraping,
   comp filtering, upsert, and heuristic fit scoring in one pass:

   ```bash
   .venv/bin/python scripts/discover.py [--lane LANE] [--limit N] [--location LOC]
   ```

   The script prints a JSON summary to stdout. Parse it.

3. **Inspect the JSON `top`** (top-10 by fit score).
   - If LinkedIn returned 0 results, surface the error and stop (network /
     endpoint issue — do not silently continue).
   - If Indeed returned 0, that's expected (Cloudflare); note but proceed.

4. **Apply rubric narration.** For each of the top 3–5 roles, compose a
   one-sentence qualitative take:
   - Which archetype this belongs to and why
   - The strongest proof point to leverage
   - One concrete red flag or risk (if any)

5. **Present Bloomberg-style cards** using Rich-like markdown:

   ```
   ┌─ #42 · cox-style-tpm · fit 82 ─────────────────────────
   │ Staff TPM @ Acme Robotics · Remote · comp unverified
   │ Lean on: True Local Labs (concept→$1M Y1, 12mo early)
   │ Watch: title says "platform" — confirm hardware exposure
   │ URL: https://www.linkedin.com/jobs/view/...
   └────────────────────────────────────────────────────────
   ```

6. **Ask Sean** which to tailor next. Accepted replies:
   - A number / ID → route to `tailor` mode for that role
   - "tailor top 3" → run `tailor` mode for IDs 1, 2, 3 in order
   - "status" / "dashboard" → route to `status` mode
   - "skip N" → `update_role.py --id N --status no_apply`
   - "get JD N" → route to `score` mode first (deeper JD parse)

## Output

- Rich cards for top roles
- A clear "what's next?" prompt
- Never auto-tailor without Sean's pick

## Failure modes

- **Scraper returns 0 LinkedIn results** → check httpx h2 installed; check
  if LinkedIn changed HTML structure. Surface raw status code and exit.
- **All scores < 50** → widen search. Suggest running with
  `--lane global-eng-orchestrator` or a broader location.
- **DB locked** → another discover is running; wait or rerun.
