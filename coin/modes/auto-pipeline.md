# Mode: auto-pipeline

The killer mode. Sean pastes a JD or URL with no other directive — Coin runs ingest → score → audit → tailor → render → track → report end-to-end. Stops only at the `applied` gate.

This collapses what was a 5-command chain into one paste.

## Trigger conditions (when SKILL.md routes here)

Route to `auto-pipeline` if user input matches ANY:

1. URL starting with `http://` or `https://` AND no other sub-command keyword in the input
2. Multi-line text (3+ newlines) containing 2+ of these phrases (case-insensitive):
   - "responsibilities"
   - "requirements"
   - "qualifications"
   - "about the role"
   - "what you'll do"
   - "we're looking for"
   - "must have"
   - "preferred qualifications"
3. Any input ≥ 800 characters that reads as JD prose (not a command)

**Do NOT trigger if** input starts with a known sub-command (`tailor`, `audit`, `track`, `status`, `pdf`, `apply`, `score`, `discover`, `liveness`, `setup`, `help`, `interview-prep`, `followup`, `patterns`).

## Step 1 — INGEST

**If URL:**

First, validate it's a JOB POSTING URL, not a search/listing URL. Reject early:

| URL pattern | Action |
|---|---|
| `linkedin.com/jobs/view/...` | Single posting → proceed |
| `linkedin.com/jobs/search...` or `?keywords=...` | Listings page → STOP, tell Sean: *"That looks like a search URL, not a single posting. Use `/coin discover` for searches, or click into one posting and paste that URL."* |
| `greenhouse.io/<company>/jobs/<id>` or `boards.greenhouse.io/...` | Single posting → proceed |
| `jobs.lever.co/<company>/<uuid>` | Single posting → proceed |
| `*.myworkdayjobs.com/.../job/...` | Single posting → proceed |
| Anything else | Open Sean: *"I don't recognize this ATS. I'll try fetching but if it fails I'll need the JD text pasted."* |

```bash
# Insert a stub row, capture the new id
.venv/bin/python -c "
import sys; sys.path.insert(0,'.')
from careerops.pipeline import upsert_role
print(upsert_role({'url': '<URL>', 'source': 'auto-pipeline', 'status': 'discovered'}))
"
# Then fetch the JD
.venv/bin/python scripts/fetch_jd.py --id <new_id>
```

The `fetch_jd.py` script populates `jd_raw`, `jd_parsed`, `company`, `title`, `location`, `comp_min`, `comp_max` if extractable. Verify these are non-null after fetch — if `company` is still null, the URL likely points to a page that doesn't expose the structured posting; ask Sean to paste the JD text instead.

**If JD text pasted:**
1. Extract `company` and `title` from the first 200 chars (look for "Job: <title> at <company>" or "<title> | <company>" patterns; fall back to asking Sean if ambiguous)
2. Insert via `upsert_role`:
   ```python
   role_id = upsert_role({
       'url': None,
       'company': '<extracted>',
       'title': '<extracted>',
       'location': '<extracted or "Unknown">',
       'source': 'manual-paste',
       'status': 'discovered',
   })
   update_jd_raw(role_id, '<full pasted text>')
   ```
3. Run JD parsing inline (extract required_skills, preferred_skills, comp_min, comp_max, seniority, red_flags, culture_signals from the text — see modes/score.md for the rubric)
4. Save with `update_jd_parsed(role_id, parsed_dict)`

**Lane assignment** (both branches):
After ingest, score title against all 4 lanes:
```python
# Source of truth: modes/_shared.md "The 4 archetypes" + config.LANES.
# If _shared.md changes the canonical lane set, update both here AND
# config.LANES — they must stay in sync.
from careerops.score import score_title
from config import LANES
scores = {lane: score_title(role['title'], lane) for lane in LANES.keys()}
best = max(scores, key=scores.get)
```
If `scores[best] >= 55`, set lane to `best`. If tied between two lanes, ask Sean. If all 4 score below 55, assign `mid-market-tpm` (default) and warn that lane fit is weak.

Update lane via the helper:
```bash
.venv/bin/python -c "
from careerops.pipeline import update_lane
update_lane(<id>, '<lane>')
"
```

## Step 2 — SCORE

```python
from careerops.pipeline import get_role, update_fit_score
from careerops.score import score_breakdown
import json

role = get_role(role_id)
parsed = json.loads(role['jd_parsed']) if role.get('jd_parsed') else None
breakdown = score_breakdown(role, role['lane'], parsed_jd=parsed)
update_fit_score(role_id, breakdown['composite'])
```

**Stop conditions:**

| Condition | Action |
|---|---|
| `lane == "out_of_band"` | STOP. Print: *"Role <id> at <company> is pedigree-filtered (FAANG-tier requiring CS degree or ex-FAANG-TPM pattern). Tailoring would burn effort on a likely recruiter-screen reject. Override with `/coin tailor <id> --force`."* |
| `composite < 50` (D or F grade) | STOP and ASK: *"This role scored <X> (<grade>). Tailor anyway? Most D/F roles waste effort. (yes/no)"* |
| `composite >= 50` | Continue to Step 3 |

## Step 3 — TRUTHFULNESS PRE-LOAD

Before generating any tailored prose, re-read in this exact order:
1. `.claude/skills/coin/references/priority-hierarchy.md` — accuracy is rule #1
2. The "Sean's canonical facts" block in `.claude/skills/coin/SKILL.md`
3. The hard rules from the same SKILL.md (section "Hard rules — non-negotiable")

This reload protects against the Cox/TitanX/Fortune-500 inflation pattern caught in the 2026-04-24 code review. It is non-skippable. If you skip it, the audit in Step 5 will catch the slip — but a slip is wasted compute.

## Step 4 — TAILOR

Execute `modes/tailor.md` inline (load it; do not shell out). Output: a JSON file at:
```
data/resumes/generated/<id:04d>_<lane>_<YYYY-MM-DD>.json
```

The JSON shape is defined in `modes/tailor.md`. After write, set status:
```python
from careerops.pipeline import update_status
update_status(role_id, 'resume_generated')
```

## Step 5 — AUDIT

Execute `modes/audit.md` inline (load it). Capture the verdict and the issue list.

| Verdict | Action |
|---|---|
| **CLEAN** (0 CRITICAL, 0 HIGH) | Continue to Step 6 |
| **NEEDS REVISION** (0 CRITICAL, 1+ HIGH) | Continue to Step 6 BUT surface HIGH issues in the final report. Do not auto-fix. |
| **BLOCK** (1+ CRITICAL) | STOP. Show the audit report. Ask: *"Auto-fix the CRITICAL items? (yes/no)"* |

If Sean says yes to auto-fix:
1. Apply the audit's suggested fixes to the JSON in place (with diff confirmation gate per `modes/audit.md`)
2. Re-run audit. **Capture which checks fired before vs after.**
3. If now CLEAN or NEEDS REVISION: continue to Step 6
4. **Oscillation detection:** if iteration 2 reintroduces a check that iteration 1 fixed (or vice versa), STOP immediately and print:
   ```
   ⚠ AUTO-FIX OSCILLATION DETECTED
     Iteration 1 fixed: [check N, M]
     Iteration 1 introduced: [check P]
     Iteration 2 fixed: [check P]
     Iteration 2 reintroduced: [check N]
     Cycle: N ↔ P. Cannot resolve automatically.

     Manual edit required. The competing constraints are:
       Check N: <one-line rule>
       Check P: <one-line rule>
     Edit data/resumes/generated/<id:04d>_<lane>_<date>.json to satisfy both,
     then run /coin audit <id> to verify.
   ```
5. If still BLOCK after 2 iterations total without oscillation (different checks each time): STOP and tell Sean to manually edit, listing the still-firing checks.
6. **Never run a 3rd auto-fix iteration.** Two attempts is the cap; further automation makes things worse.

If Sean says no: STOP. Print: *"Manual revision required. Edit `<json path>` and run `/coin audit <id>` to verify."*

## Step 6 — RENDER

```bash
.venv/bin/python scripts/render_pdf.py --role-id <id> --recruiter
```

Verify the PDF was written (check `data/resumes/generated/<id:04d>_*_recruiter.pdf` exists with size > 30KB). If render fails, the most common cause is missing `pango` — surface to Sean: *"PDF render failed. Check: `brew list pango`."*

After the resume PDF lands, dispatch to `modes/cover-letter.md` for this same role to generate the standalone cover letter. The cover letter is **additive, not blocking**: if its truthfulness audit fails, log the failure to the report (Step 8) but do NOT stop the pipeline — the resume PDF still ships. Treat it the same way:

```bash
# Inside cover-letter mode dispatch — produces cover.json + cover.pdf
.venv/bin/python scripts/render_cover_letter.py --role-id <id>
```

If `cover_letter_audit_passes` is false, set `cover_status = "audit-failed"` for the report; if the render works, set `cover_status = "shipped"`; if no cover was attempted, `cover_status = "skipped"`.

## Step 7 — TRACK

Status was already set to `resume_generated` in Step 4. Now record the audit verdict in `notes`:

```python
from careerops.pipeline import update_role_notes
note = f"audit:{verdict}; high_issues:{len(high_issues)}; auto_pipeline:{date}"
update_role_notes(role_id, note, append=True)
```

## Step 8 — REPORT

Print this single-screen summary in the exact shape below. Sean reads only this — make every line count.

```
═══════════════════════════════════════════════════════════════
  Auto-Pipeline — Role <id>
  <company> — <title>
  Lane: <lane>  ·  Fit: <score> (<grade>)  ·  <location>
═══════════════════════════════════════════════════════════════

EXECUTIVE SUMMARY
  <first 2 sentences of resume.executive_summary>

TOP 3 BULLETS
  1. <top_bullets[0]>
  2. <top_bullets[1]>
  3. <top_bullets[2]>

GAPS TO PREP (skills_gap)
  · <skills_gap[0]>
  · <skills_gap[1]>

AUDIT VERDICT: <CLEAN | NEEDS REVISION | BLOCK>
<if HIGH issues, list up to 3 with quote + fix>

ARTIFACTS
  JSON:  data/resumes/generated/<id:04d>_<lane>_<date>.json
  PDF:   data/resumes/generated/<id:04d>_<lane>_<date>_recruiter.pdf
  COVER: <cover_status — shipped | audit-failed | skipped>
         (if shipped) data/resumes/generated/<id:04d>_<lane>_<date>_cover.pdf

NEXT STEP
  → Review the PDF (open it now)
  → If looks good: /coin track <id> applied  (after you actually submit)
  → If needs edits: edit JSON manually, then /coin audit <id>
  → To submit via ATS automation: /coin apply <id>
```

## Human gates (only two)

| Gate | When | Why |
|---|---|---|
| Audit BLOCK auto-fix | If Step 5 verdict = BLOCK | Never silently rewrite tailored content |
| `applied` transition | Always — separate command | Real-world commitment; auto-pipeline NEVER auto-submits |

## Performance target

End-to-end (URL paste → PDF + report) should complete in **under 90 seconds** on a typical role. If it takes longer, suspect:
- LinkedIn scraping rate limit (the `fetch_jd.py` step)
- PDF render font fallback (Helvetica Neue → DejaVu)
- Network round-trip for the Anthropic LLM call (skill execution)

## Failure modes & recovery

| Failure | Symptom | Recovery |
|---|---|---|
| URL fetch returns empty | `company` and `title` null after Step 1 | Ask Sean to paste JD text; redo Step 1 with manual extraction |
| Lane assignment ambiguous | Two lanes tied at score_title | Ask Sean which lane; do not auto-pick |
| Audit BLOCK can't be auto-fixed | 2 iterations didn't reach CLEAN | Stop; surface remaining issues; Sean edits manually |
| PDF render fails | weasyprint exception | Check pango install; fall back to brief mode (`--brief` not `--recruiter`) |
| DB write conflicts (race) | UNIQUE constraint on URL | upsert_role handles this — returns existing id; continue |

## Notes for the executor

- Do not parallelize steps. Order matters: ingest before score, score before tailor, tailor before audit.
- Do not cache the JD-to-tailoring transformation between roles. Each tailoring is fresh.
- The `score_breakdown` call is fast (no LLM); the tailoring is the slow part. Sean is paying attention — print "tailoring..." before Step 4 so the gap is visible.
- If `lane == "out_of_band"` is hit, do NOT auto-quarantine without telling Sean. The pedigree filter is opinionated; he may want to override.
- The `--force` flag mentioned in Step 2's stop message is not yet wired into `tailor` mode. Add it when COIN-TAILOR-FORCE is built. For now, manual override = directly invoke `modes/tailor.md` ignoring the auto-pipeline guard.
