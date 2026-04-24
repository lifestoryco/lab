---
description: Generate a lane-tailored resume and cover letter for a specific role. Rewrites Sean's baseline to match the JD's skill requirements and comp tier.
---

# /coin-apply [role_id or URL] [--lane LANE]

**Usage:**
- `/coin-apply 42` — apply to pipeline role #42 (auto-detects lane)
- `/coin-apply https://linkedin.com/jobs/view/... --lane tpm-high`
- `/coin-apply 42 --format pdf` — output as PDF (requires weasyprint)

---

## Steps

1. Load the role — from pipeline DB by ID, or fetch URL fresh:
   ```bash
   .venv/bin/python -c "from careerops.pipeline import get_role; import json; print(json.dumps(get_role($ROLE_ID), indent=2))"
   ```

2. Parse the JD with the analyzer:
   ```bash
   .venv/bin/python -c "
   from careerops.analyzer import parse_jd
   jd_data = parse_jd(role_id=$ROLE_ID)
   # Returns: required_skills, preferred_skills, comp_signals, culture_signals
   "
   ```

3. Run the resume transformer for the target lane:
   ```bash
   .venv/bin/python -c "
   from careerops.transformer import transform
   result = transform(lane='$LANE', role_id=$ROLE_ID)
   print(result['executive_summary'])
   "
   ```

4. Save output to `data/resumes/generated/{role_id}_{lane}_{date}.md`

5. Update pipeline status:
   ```bash
   .venv/bin/python -c "from careerops.pipeline import update_status; update_status($ROLE_ID, 'resume_generated')"
   ```

---

## Output format

```
═══════════════════════════════════════════════
  Coin Apply — {Company} | {Title}
  Lane: {lane} | Fit Score: {n}/100
═══════════════════════════════════════════════

EXECUTIVE SUMMARY (rewritten for {lane})
──────────────────────────────────────────
{transformed summary — 3-4 sentences}

KEY BULLETS REWEIGHTED
──────────────────────────────────────────
▶ {highest-weight bullet for this lane}
▶ {second bullet}
▶ {third bullet}
▶ {fourth bullet}

SKILLS MATCH
──────────────────────────────────────────
Required:  {matched} / {total required}  {████████░░}
Preferred: {matched} / {total preferred} {██████░░░░}
Gap:       {skills in JD not in base.json — flag for user}

COVER LETTER HOOK
──────────────────────────────────────────
{1 paragraph — specific to this role and company}

─────────────────────────────────────────────
Saved: data/resumes/generated/{filename}
Run /coin-track to update pipeline status
```

## Rules
- Never fabricate metrics — only use data from `data/resumes/base.json`
- If a required skill has no match in Sean's baseline, surface it as a gap — don't invent coverage
- Executive summary must reference the specific company/role, not be generic
- Prompt caching MUST be used for the base.json → transformer call (input exceeds 1024 tokens)
