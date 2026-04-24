---
description: Search job boards for high-compensation roles matching a target lane. Filters by comp minimum ($180K base) and surfaces top matches ranked by fit score.
---

# /coin-search [lane] [--limit N]

**Usage:**
- `/coin-search tpm-high` — search for High-Tier TPM roles
- `/coin-search sales-ent --limit 20` — top 20 Enterprise Sales roles
- `/coin-search pm-ai` — AI Product Manager roles

**Lane IDs:** `tpm-high` | `pm-ai` | `sales-ent`

---

## Steps

1. Load lane config from `config.py` — keywords, title patterns, comp minimum
2. Run the scraper:
   ```bash
   .venv/bin/python -c "
   from careerops.scraper import search
   from careerops.compensation import filter_by_comp
   import json, sys
   results = search(lane='$LANE', limit=$LIMIT)
   filtered = filter_by_comp(results, min_base=180000)
   print(json.dumps(filtered, indent=2))
   " 2>&1 | head -200
   ```
3. For each result, run the JD analyzer:
   ```bash
   .venv/bin/python -c "
   from careerops.analyzer import score_fit
   # scores each result against Sean's baseline
   "
   ```
4. Rank by composite score: comp_band × fit_score
5. Save results to pipeline DB:
   ```bash
   .venv/bin/python -c "from careerops.pipeline import upsert_roles; ..."
   ```

---

## Output format

```
═══════════════════════════════════════════════
  Coin Search — {lane} | {date}
  Found: {n} roles above $180K base
═══════════════════════════════════════════════

#1 ██████████ 94/100
   {Title} — {Company}
   {Location} | {Remote/Hybrid/Onsite}
   Base: ${min}K–${max}K | RSU: {band or "unverified"}
   Fit: TPM ██████░░░ | Sales ████████░░ | PM ███░░░░░░
   → {job_url}

#2 ████████░░ 87/100
   ...

─────────────────────────────────────────────
Run /coin-apply {role_id} to generate tailored resume
Run /coin-track to view full pipeline
```

## Rules
- Never surface roles below $180K base unless `--override-comp` flag is passed
- Always show comp band source: `[explicit]`, `[glassdoor]`, `[estimated]`
- Cache results in pipeline.db — don't re-scrape the same URL within 24 hours
