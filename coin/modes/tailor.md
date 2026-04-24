# Mode: tailor

Generate a lane-tailored resume and cover letter hook for a specific role.
This is the highest-value mode — the output is what Sean actually submits.

## Input

- `--id <role_id>` (required)
- `--lane <archetype_id>` (optional; defaults to the role's current lane)

## Steps

1. **Load the role, the base profile, and the North Star.** Run these three
   reads (they're cheap):

   ```bash
   .venv/bin/python scripts/print_role.py --id <role_id>
   .venv/bin/python -c "import yaml; import json; print(json.dumps(yaml.safe_load(open('config/profile.yml')), indent=2))"
   .venv/bin/python -c "import sys; sys.path.insert(0,'.'); from data.resumes.base import PROFILE; import json; print(json.dumps(PROFILE, indent=2))"
   ```

2. **Validate readiness:**
   - Role must have `jd_raw` populated. If not, route to `score` mode first.
   - Role's `lane` must match one of the five archetypes. If empty or
     unknown, ask Sean which archetype to target.
   - Fit score should be ≥ 50. If lower, confirm with Sean before tailoring.

3. **Select emphasis stories** from PROFILE["stories"] whose `id` appears
   in the archetype's `proof_points` list (from profile.yml). You may
   add one more story if the JD explicitly names a domain Sean has
   (e.g., aerospace, RF, 5G) — borrow that story too.

4. **Write the tailored resume** as JSON. Required shape:

   ```json
   {
     "executive_summary": "3-4 sentences. MUST open with the archetype's North Star rephrased for this specific company + role. MUST include at least two quantified outcomes from Sean's real stories. No generic 'senior leader' language.",
     "top_bullets": [
       "5 bullets, ranked by relevance to this JD's top_3_must_haves. Each bullet starts with a verb, includes a metric, and names a real company/program from Sean's profile.",
       "...", "...", "...", "..."
     ],
     "skills_matched": ["verbatim skills from JD that appear (or clearly map) in Sean's profile"],
     "skills_gap": ["required skills Sean genuinely doesn't have — be honest; this is for Sean's prep, not submission"],
     "cover_letter_hook": "1 paragraph, 3-5 sentences. Names the company, names the specific role challenge (inferred from JD), connects it to ONE of Sean's proof points with a metric, ends with a forward-looking claim. No 'I am writing to express my interest in...' openers."
   }
   ```

   **Voice rules:**
   - First-person implied (no "I am" / "Sean is" — just claims and metrics)
   - Active verbs: drove, shipped, scaled, orchestrated, led
   - Never: "passionate about", "synergy", "dynamic", "results-driven"
   - Every bullet has a number OR a concrete program/company name
   - Prefer specific ($27M Series A) over vague (significant funding)

5. **Save via the helper script.** Write your JSON to a temp file, then:

   ```bash
   cat > /tmp/resume.json <<'EOF'
   { ... your JSON ... }
   EOF
   .venv/bin/python scripts/save_resume.py --role-id <role_id> --lane <lane> --input /tmp/resume.json
   ```

   The script validates required keys, writes `data/resumes/generated/<id>_<lane>_<date>.json`,
   and transitions the role to `resume_generated`.

6. **Render a preview** for Sean — print the executive summary, the 5
   bullets, and the cover letter hook as a formatted block. Include the
   file path of the saved JSON so he can copy it into his actual resume
   template.

7. **Ask about next step:** submit the application manually (Sean does
   this), mark `applied` via `/coin track`, or refine the output.

## Failure modes

- **Ambiguous archetype** → ask Sean which of the five to use; don't pick
  silently.
- **Missing JD** → route to `score` first.
- **Skills gap is large (>50% of required)** → flag the role as a stretch;
  still tailor but make the gap explicit to Sean.

## Anti-patterns (reject if Sean asks for them)

- Writing multiple lanes in one resume — every output is one-lane.
- Claiming metrics not in PROFILE — if the JD asks about something Sean
  didn't do, put it in `skills_gap`, not `top_bullets`.
