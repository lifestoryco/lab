# Mode: score

Fetch and parse the full job description for a specific role, then write
the parsed structure back to the DB. This runs before `tailor` when the
role doesn't yet have parsed_jd populated.

## Input

- `--id <role_id>` (required)

## Steps

1. **Fetch JD text** to disk via Python (no LLM):

   ```bash
   .venv/bin/python scripts/fetch_jd.py --id <role_id>
   ```

   On success, the JD is stored in the `jd_raw` column. If this fails,
   abort and report the error — don't guess at skills without source.

2. **Read it back:**

   ```bash
   .venv/bin/python scripts/print_role.py --id <role_id> --fields id,title,company,location,jd_raw
   ```

3. **Parse the JD yourself** (this is the LLM work — it happens in this
   session, no API call). Extract this exact JSON shape:

   ```json
   {
     "required_skills": ["..."],
     "preferred_skills": ["..."],
     "comp_min": 180000,
     "comp_max": 240000,
     "comp_explicit": true,
     "remote": true,
     "seniority": "senior",
     "yoe_min": 10,
     "culture_signals": ["collaborative", "flat hierarchy", ...],
     "red_flags": ["rockstar language", "unlimited PTO without floor", ...],
     "top_3_must_haves": ["the three things a resume MUST answer"]
   }
   ```

   Rules:
   - `seniority`: one of `junior | mid | senior | staff | principal | director | vp`
   - `comp_*`: integers in USD, or null if not stated. Never invent.
   - `top_3_must_haves`: phrase them as things Sean's resume must *answer*,
     e.g. "Has shipped IoT hardware programs end-to-end" — not generic
     skills like "leadership".

4. **Write the parsed JD back** via a temp file:

   ```bash
   cat > /tmp/parsed.json <<'EOF'
   { ... your JSON ... }
   EOF
   .venv/bin/python scripts/update_role.py --id <role_id> --parsed-jd /tmp/parsed.json
   ```

5. **Recompute fit score** (optional but recommended — score.py will use
   the richer parsed skills now):

   ```bash
   .venv/bin/python -c "
   import sys; sys.path.insert(0,'.')
   from careerops.pipeline import get_role, update_fit_score
   from careerops.score import score_fit
   import json
   r = get_role(<role_id>)
   parsed = json.loads(r['jd_parsed']) if r.get('jd_parsed') else {}
   score = score_fit(r, r['lane'], parsed_jd=parsed)
   update_fit_score(<role_id>, score)
   print('new fit:', score)
   "
   ```

6. **Summarize to Sean** in 2–3 sentences: archetype fit, the top-3
   must-haves, any comp or culture red flags. Then ask whether to proceed
   to `tailor`.

## Guardrails

- If `comp_min` is below $180K and the JD states it explicitly, mark
  `no_apply` with reason "comp below floor" and do not tailor.
- If the JD is evidently not a real JD (landing page, 404), alert Sean
  and skip — don't parse garbage.
