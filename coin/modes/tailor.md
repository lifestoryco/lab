# Mode: tailor

Generate a lane-tailored resume and cover letter hook for a specific role. This is the highest-value mode — the output is what Sean actually submits. The output JSON MUST pass `modes/audit.md`'s 9 checks before it can be rendered to PDF.

## Input

- `--id <role_id>` (required)
- `--lane <archetype_id>` (optional; defaults to the role's current lane)

## Step 1 — Load the role, the base profile, and the North Star

Run these three reads (they're cheap):

```bash
.venv/bin/python scripts/print_role.py --id <role_id>
.venv/bin/python -c "import yaml; import json; print(json.dumps(yaml.safe_load(open('config/profile.yml')), indent=2))"
.venv/bin/python -c "import sys; sys.path.insert(0,'.'); from data.resumes.base import PROFILE; import json; print(json.dumps(PROFILE, indent=2))"
```

Then load `modes/_shared.md` and the truthfulness anchors (these are non-skippable per Operating Principle #3):
- `.claude/skills/coin/references/priority-hierarchy.md`
- `.claude/skills/coin/SKILL.md` "Sean's canonical facts" block

## Step 2 — Validate readiness

- Role must have `jd_raw` populated. If not, route to `score` mode first.
- Role's `lane` must match one of the **4 archetypes** (current as of 2026-04-25):
  - `mid-market-tpm`
  - `enterprise-sales-engineer`
  - `iot-solutions-architect`
  - `revenue-ops-operator`
- Reject `out_of_band` (pedigree-filtered) unless Sean passed `--force` (see _shared.md).
- If lane is empty or unknown, ask Sean which archetype to target — never silently pick.
- Fit score should be ≥ 50. If lower, confirm with Sean before tailoring.

## Step 3 — Select emphasis stories

From `PROFILE.positions[*].bullets`, draw the proof points whose `id` (from the legacy `PROFILE.stories` map) appears in the archetype's `proof_points` list (from profile.yml). You may add one more position bullet if the JD explicitly names a domain Sean has (e.g., aerospace, RF, 5G, BLE, Z-Wave) — borrow that proof too.

## Step 4 — Determine `target_role` (REQUIRED)

This is non-optional. Audit Check 7 will FAIL any tailored JSON missing `target_role`. Pick from this table:

| Lane | `target_role` (use this exact value or a close variant matching the JD title) |
|---|---|
| `mid-market-tpm` | "Senior Technical Program Manager" (or "Director of Program Management" for Director-titled JDs) |
| `enterprise-sales-engineer` | "Enterprise Sales Engineer / Solutions Architect" (or just "Sales Engineer" for IC roles) |
| `iot-solutions-architect` | "IoT / Wireless Solutions Architect" |
| `revenue-ops-operator` | "Director of Revenue Operations" (or match JD title — "Head of Operations", etc.) |

If the JD's actual title differs (e.g., JD says "Staff Sales Engineer"), prefer the JD's title verbatim — recruiters scan for the title they posted.

## Step 5 — Write the tailored resume as JSON

Required shape:

```json
{
  "role_id": <id>,
  "lane": "<lane>",
  "company": "<company>",
  "title": "<title>",
  "url": "<url>",
  "target_role": "<value from Step 4 table>",
  "generated_at": "<ISO8601>",
  "resume": {
    "executive_summary": "3-4 sentences. MUST open with the archetype's North Star rephrased for this specific company + role. MUST include at least two quantified outcomes from Sean's real positions/bullets. No generic 'senior leader' language.",
    "top_bullets": [
      "5 bullets, ranked by relevance to this JD's top_3_must_haves. Each bullet starts with a verb, includes a metric (numeric, spelled-out, or collective-noun) traceable to PROFILE.positions[*].bullets, and names a real company/program from Sean's profile.",
      "...", "...", "...", "..."
    ],
    "skills_matched": ["verbatim skills from JD that appear (or clearly map) in PROFILE.skills"],
    "skills_gap": ["required skills Sean genuinely lacks — be honest; this is for Sean's prep AND for audit Check 8"],
    "cover_letter_hook": "1 paragraph, 3-5 sentences. Names the company, names the specific role challenge (inferred from JD), connects it to ONE of Sean's proof points with a metric, ends with a forward-looking claim. No 'I am writing to express my interest in...' openers."
  }
}
```

### Voice rules

- First-person implied (no "I am" / "Sean is" — just claims and metrics)
- Active verbs: drove, shipped, scaled, orchestrated, led
- Never: "passionate about", "synergy", "dynamic", "results-driven"
- Every bullet has a number OR a concrete program/company name
- Prefer specific ($27M Series A) over vague (significant funding)

### Audit-aware writing rules (READ BEFORE FIRST BULLET)

These rules track audit.md's 9 checks. If you violate them, audit will catch it and you'll waste an iteration.

1. **Cox / TitanX / Safeguard bullets MUST contain "as Hydrant's <role>" or "while at Hydrant" or "fractional COO"** in the same bullet (audit Check 3).
2. **No vague-flex qualifiers without a verifiable named account.** Ban-list: "Fortune 500", "Fortune 100", "seven-figure", "world-class", "industry-leading", "cutting-edge", "premier", "top-tier", "blue-chip", "high-growth", "hypergrowth", "mission-critical", "transformational", "strategic", "global" (when not naming countries) (audit Check 4 — CRITICAL, escalated 2026-04-25).
3. **Every quantitative claim must trace to PROFILE** — numeric, spelled-out ("twelve months ahead"), AND collective-noun ("dozens of") all count (audit Check 5).
4. **Hedge causation for outcomes Sean didn't solely produce.** Soften "enabled $27M Series A" to "during the period the company raised $27M Series A" (audit Check 6).
5. **Set `target_role` per Step 4 table** (audit Check 7).
6. **List required JD skills Sean lacks in `skills_gap`** — never hide a gap (audit Check 8).
7. **Avoid claims of <2-year-tenure domains as deep expertise.** "Aerospace adjacent (CA Engineering)" is fine; "Aerospace & Defense" is not (audit Check 9).

## Step 6 — Save via the helper script

Write your JSON to a temp file, then:

```bash
cat > /tmp/resume.json <<'EOF'
{ ... your JSON ... }
EOF
.venv/bin/python scripts/save_resume.py --role-id <role_id> --lane <lane> --input /tmp/resume.json
```

The script validates required keys (including `target_role` after the 2026-04-25 audit alignment), writes `data/resumes/generated/<id:04d>_<lane>_<date>.json`, and transitions the role to `resume_generated`.

If `save_resume.py` does not yet enforce `target_role`, your JSON might still be saved without it — but audit will then fail Check 7. Always include it.

## Step 7 — Self-audit before render

Before printing the preview, mentally run audit Check 3, 4, 5, 7 on your output. If any would fire, fix and rewrite before showing Sean. This saves a round-trip.

## Step 8 — Render a preview for Sean

Print the executive summary, the 5 bullets, and the cover letter hook as a formatted block. Include the file path of the saved JSON.

## Step 9 — Recommend next step

End with:
> "Tailored JSON saved at `<path>`. Recommended next:
> 1. `/coin audit <id>` — verify against the 9 truthfulness checks (auto-pipeline calls this automatically)
> 2. `/coin pdf <id> --recruiter` — render the submission PDF (only after audit is CLEAN)
> 3. `/coin apply <id>` — open the ATS form and pre-fill (browser-assisted)"

## Failure modes

- **Ambiguous archetype** → ask Sean which of the **4** to use; don't pick silently.
- **Missing JD** → route to `score` first.
- **Skills gap is large (>50% of required)** → flag the role as a stretch; still tailor but make the gap explicit to Sean AND list every gap in `skills_gap`.
- **Lane is `out_of_band`** → refuse unless `--force`. The role is pedigree-filtered (FAANG-tier requiring CS degree or ex-FAANG-TPM pattern). Override is wasteful.

## Anti-patterns (reject if Sean asks for them)

- Writing multiple lanes in one resume — every output is one-lane.
- Claiming metrics not in PROFILE — if the JD asks about something Sean didn't do, put it in `skills_gap`, not `top_bullets`.
- Adding a "Fortune 500" or "seven-figure" qualifier to make a bullet sound bigger — audit will catch it.
- Skipping `target_role` to avoid the typing — audit Check 7 will FAIL the JSON and block the PDF.
- Editing the PDF directly to add claims that aren't in the JSON — the JSON is source of truth.
