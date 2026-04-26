# Mode: tailor (v2, schema-driven)

Generate a lane-tailored resume + cover letter hook for a specific role. This is the highest-value mode — the output is what Sean actually submits.

**Source of truth:** the experience DB (m005 schema). `data/resumes/base.py` is seed-input only; do not read PROFILE at runtime.

The output JSON MUST pass `modes/audit.md`'s 14 checks (Checks 1-9 prose-level, 10-14 structural). Multi-variant rendering happens at Step 6 — every render emits both ATS-strict and designed variants.

## Input

- `--id <role_id>` (required)
- `--lane <archetype_id>` (optional; defaults to the role's current lane)
- `--variants {1,2,4}` (optional; defaults to 4 if `fit_score >= 80`, else 2)

## Step 1 — Load the role + experience DB + North Star

```bash
# Run migrations + seed (idempotent — safe every run)
.venv/bin/python scripts/migrations/m005_experience_db.py
.venv/bin/python scripts/migrations/m006_seed_lightcast.py
.venv/bin/python scripts/seed_from_base_py.py

# Read the role
.venv/bin/python scripts/print_role.py --id <role_id>

# Read profile.yml (lanes + per-lane themes)
.venv/bin/python -c "import yaml; import json; print(json.dumps(yaml.safe_load(open('config/profile.yml')), indent=2))"

# Read the lane's accomplishment payload (fact-only — no rendered bullets yet)
.venv/bin/python -c "
from careerops import experience as exp
import json
print(json.dumps(exp.assemble_for_lane('<lane_slug>', min_relevance=60), default=str, indent=2))
"
```

Then load `modes/_shared.md` and the truthfulness anchors (non-skippable per Operating Principle #3):
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

## Step 2.5 — Run the structured-output ranker (Claude as ranker)

This step replaces the old "pick stories by hand" flow with a deterministic Claude prompt. Per locked decision #2 (hybrid bullet selector): Claude ranks (temp 0, structured output), then Claude paraphrases the top-K winners.

```python
from careerops.ranker import build_ranker_prompt, validate_ranker_response, RankerPromptInputs
from careerops import experience as exp

payload = exp.assemble_for_lane(lane_slug, min_relevance=60)
expected_ids = {entry["accomplishment"]["id"] for entry in payload}

prompt = build_ranker_prompt(RankerPromptInputs(
    lane_slug=lane_slug,
    payload=payload,
    jd_text=role["jd_raw"],
    jd_role_id=role["id"],
    k=6,
    seniority_constraint=None,  # set when JD explicitly demands a level
))
```

Emit JSON conforming to `careerops.ranker.RANKER_SCHEMA` (temp 0). Then validate:

```python
result = validate_ranker_response(your_json, expected_accomplishment_ids=expected_ids, k=6)
assert result.valid, result.errors
top_ids = result.top_k  # [accomplishment_id, ...]
```

The top-K accomplishment_ids are the inputs for Step 5 paraphrase.

## Step 3 — Select emphasis stories (Lightcast tags + ranker score)

For each top-K id from Step 2.5:
1. Load the full accomplishment + outcomes + evidence + skill tags via `experience.get_accomplishment / list_outcomes / list_evidence / list_skills_for_accomplishment`.
2. The ranker rationale tells you WHICH JD keywords each story matches.
3. Drop any story whose `seniority_ceiling` is below what the JD demands (Eightfold-style title-ladder check).

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

## Step 8 — Render multi-variant + score panel

Per locked decision #3, every render emits BOTH ATS-strict and designed variants. For high-fit roles (`fit_score >= 80`), render 4 variants (3 designed themes + 1 ATS-strict).

```bash
.venv/bin/python scripts/render_resume.py <role_id>
```

This calls `careerops.score_panel.score_artifact` on every output, persisting one row per variant to `render_artifact`. The reported metrics:

```
[ats     ] engineeringresumes       0004_<lane>.engineeringresumes.ats.pdf
         ATS=92  KW=72%  density=2.1%  truth=✅  pages=1  → SHIP-READY
[designed] harvard                  0004_<lane>.harvard.designed.pdf
         ATS=88  KW=72%  density=2.1%  truth=✅  pages=1  → SHIP-READY
```

If the truth gate fails (`truth=❌`), the bullet text contains a metric not in any linked outcome row. Fix by:
1. Identifying the offending metric (`careerops.score_panel.truthfulness_gate` reports the failure).
2. Either add an `outcome` row + `evidence` row via `/coin add-evidence`, OR rewrite the bullet to drop the unbacked claim.

Per the locked truth gate (#4), no SHIP-READY render advances if truth fails.

## Step 9 — Show Sean the score panel + recommend variants

Print the score panel header for every variant. Highlight the SHIP-READY one. Then:

> "Tailored. Renders at `data/resumes/generated/<id:04d>_*.pdf`:
> - Recommended for ATS submission: `<basename>.ats.pdf` — single-column, plain glyphs.
> - Recommended for warm intro / hiring-manager-direct: `<basename>.<theme>.designed.pdf` (highest ATS + KW score).
>
> Next:
> 1. `/coin audit <id>` — verify against the 14 truthfulness checks (auto-pipeline calls this).
> 2. `/coin recruiter-eye <id>` — 30-sec human-screener pass.
> 3. `/coin apply <id>` — open the ATS form and pre-fill the right variant."

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
