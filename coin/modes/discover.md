# Mode: discover

Find high-compensation roles across Sean's four archetypes, filter by comp
floor, compute fit scores, and present the top results.

**Two-stage discovery** (added COIN-SCORE-V2, 2026-04-28):

- **Stage 1 (fast):** scrape → cheap title + company-tier score → store.
  Always runs. Produces a first dashboard view in ~2 min for 40 roles.
  This stage was JD-blind, which caused roles #4, #13, #14 to appear at
  72.4 (B-) when the JDs contained clearance gates, MSFT stack requirements,
  and domain mismatches. Stage 2 corrects this.

- **Stage 2 (smart):** for top-N (default 15), fetch the full JD, parse it
  here in the host Claude Code session, run disqualifiers, and re-score.
  Adds ~3–5 min for top-15 (one HTTP fetch + one parse prompt per role).
  Per CLAUDE.md rule #6, ALL LLM reasoning runs here in this session —
  `discover.py` is pure Python I/O, it never calls any LLM or SDK.

## Inputs

- None (default: all four archetypes, limit 15 each, --deep-score 15)
- Or: `lane=<archetype_id>` and/or `limit=<N>` and/or `location="..."`
- Or: `--deep-score 0` to skip stage 2 and get a fast-only run

## Steps

### Step 1 — Load shared context

Load `modes/_shared.md` rubric and archetype list.

### Step 2 — Run the discover script (stage 1)

```bash
.venv/bin/python scripts/discover.py \
  [--lane LANE] [--limit N] [--location LOC] \
  [--boards linkedin,greenhouse,lever,ashby] \
  [--deep-score 15]
```

The script prints a JSON summary to stdout AND (when `--deep-score N > 0`)
a marker line:

```
### DEEP-SCORE-PENDING count=15 file=data/.deep_score_pending.json
```

Parse the JSON summary. If LinkedIn returned 0 results, surface the error
and stop (network / endpoint issue). If Indeed returned 0, that's expected
(Cloudflare); note but proceed.

### Step 3 — Inspect the JSON `top` (stage-1 results)

Review the top-10 by stage-1 fit score. Note any scores that look
suspicious (identical scores like 72.4 often signal JD-blind collapse —
those will be corrected in Step 4a).

### Step 4a — Deep-score loop (runs automatically when DEEP-SCORE-PENDING marker present)

**Only run this step when `discover.py` printed the `### DEEP-SCORE-PENDING` marker.**

> This is the fix for the #4 / #13 / #14 false-positive class: roles that
> scored 72.4 on title keywords alone but contained clearance gates, MSFT
> stack requirements, or narrow-domain cybersecurity specs that disqualify
> Sean. Stage 2 catches all of these.

1. Read `data/.deep_score_pending.json` for the list of `role_ids`.
2. Load `modes/_shared.md` PROFILE so the disqualifier scan has skills context.
3. For **each `role_id`** in the list:

   a. Read the role's `jd_raw` from the DB:
   ```python
   from careerops.pipeline import get_role
   role = get_role(role_id)
   jd_text = role.get("jd_raw") or ""
   ```

   b. If `jd_text` is empty, print `[deep-score] role {role_id} skipped (no JD)` and move on.

   c. **Parse the JD** — use THIS exact prompt block and output ONLY the JSON:

   ```
   Extract from this JD into a JSON object with exactly these keys:

   - required_skills: list[str]      # must-have skills explicitly listed in "Requirements" or "Must have"
   - preferred_skills: list[str]     # nice-to-have skills from "Preferred" or "Bonus"
   - seniority: str                  # one of: 'junior'|'mid'|'senior'|'staff'|'principal'|'director'|'vp'|''
   - comp_min: int|null              # parse $XXXk-$YYYk patterns, USD; null if not stated
   - comp_max: int|null              # null if not stated
   - comp_currency: str              # 'USD' default, 'CAD'|'EUR'|'GBP' if explicit
   - comp_explicit: bool             # true if comp band is in the JD; false if absent
   - red_flags: list[str]            # e.g. "10x engineer language", "unlimited PTO with no minimum",
                                     #      "wear many hats", "fast-paced startup environment",
                                     #      "ninja/rockstar/guru language"
   - culture_signals: list[str]      # e.g. "remote-first", "async", "no on-call", "4-day week",
                                     #      "core hours overlap", "documented onboarding"
   - team_size: int|null             # if mentioned ("team of 8")
   - reporting_to: str|null          # e.g. "VP of Engineering", "CTO", "Head of Product"
   - location_flexibility: str       # one of: 'remote'|'hybrid'|'onsite'|'remote-us'|'remote-global'|''

   Output ONLY the JSON object. No prose, no code fence, no commentary.
   ```

   d. Run the disqualifier scan:
   ```python
   from careerops.disqualifiers import scan_jd
   from data.resumes.base import PROFILE
   dq_result = scan_jd(jd_text, PROFILE)
   ```

   e. **If `dq_result['hard_dq']` is True:**
   ```python
   from careerops.pipeline import update_lane, update_status
   update_lane(role_id, 'out_of_band')
   reason = list(dq_result['hard_dq'])[0]
   update_status(role_id, 'no_apply', note=f"hard_dq: {reason}")
   ```
   Print: `[deep-score] role {role_id} HARD DQ → out_of_band ({reason})`. Move to next role.

   f. **Else — re-score with stage 2:**
   ```python
   from careerops.pipeline import get_role, update_score_stage2
   from careerops.score import score_stage2 as compute_stage2
   from datetime import datetime, timezone
   role = get_role(role_id)
   breakdown = compute_stage2(role, role['lane'], parsed_jd, dq_result)
   update_score_stage2(
       role_id,
       breakdown['composite'],
       parsed_jd,
       datetime.now(timezone.utc).isoformat(timespec='seconds'),
   )
   ```
   Print: `[deep-score] role {role_id} stage-2 score: {breakdown['composite']:.1f} ({breakdown['grade']})`

4. After the full loop, delete `data/.deep_score_pending.json`.
5. Print summary: `Deep-scored N roles. M hard-DQ'd, K re-scored.`

**Stage 2 does NOT auto-tailor.** Tailoring still requires explicit `/coin tailor N`.
This separation is intentional — re-scoring 15 roles is cheap; tailoring 15 resumes
is expensive in both tokens and review time.

### Step 4b — Bloomberg-style cards

Render Rich-style cards for the top 3–5 roles. After stage 2 runs, use
the updated scores. Each card shows the stage badge (S1 or S2) to indicate
which signal is authoritative.

**Stage badge legend:**
- `[S2]` (cyan) — JD-aware score after full parse + disqualifier scan. Trust this.
- `[S1]` (gray) — title-keyword score only. Treat as a first approximation.

Card format:
```
┌─ #42 [S2] · mid-market-tpm · fit 82 (B) ──────────────────────
│ Staff TPM @ Acme Robotics · Remote · $180K–$220K verified
│ Lean on: True Local Labs (concept→$1M Y1, 12mo early)
│ Watch: title says "platform" — confirm hardware exposure
│ URL: https://www.linkedin.com/jobs/view/...
└──────────────────────────────────────────────────────────────
```

For roles still at [S1] (stage 2 didn't run for them), note: "score is
title-only; run /coin score {id} for a JD-aware re-score."

### Step 5 — Sean's pick

Recommend one role from the top-3, citing the parsed JD's specific signals
(stage-2 roles have parsed_jd available; use it). Ask Sean which to tailor
next.

Accepted replies:
- A number / ID → route to `tailor` mode for that role
- "tailor top 3" → run `tailor` mode for IDs 1, 2, 3 in order
- "status" / "dashboard" → route to `status` mode
- "skip N" → `update_role.py --id N --status no_apply`
- "get JD N" → route to `score` mode first (deeper single-role parse)

## Output

- Bloomberg-style cards for top roles with S1/S2 badges
- Deep-score summary line (e.g. "Deep-scored 15 roles. 2 hard-DQ'd, 13 re-scored.")
- A clear "what's next?" prompt
- Never auto-tailor without Sean's pick

## Failure modes

- **Scraper returns 0 LinkedIn results** → check httpx h2 installed; check
  if LinkedIn changed HTML structure. Surface raw status code and exit.
- **All scores < 50** → widen search. Suggest running with
  `--lane iot-solutions-architect` or a broader location.
- **DB locked** → another discover is running; wait or rerun.
- **Stage 2 JD parse returns malformed JSON** → log the role ID, skip it,
  continue. Do NOT halt the entire deep-score loop on one bad parse.
- **Stage 2 taking too long** → each JD fetch is ~1–2s HTTP + ~5s parse.
  15 roles = ~3–5 min total. If you need a faster result, rerun with
  `--deep-score 5` or `--deep-score 0`.
