# Mode: audit

Truthfulness check on a tailored resume JSON before it becomes a PDF that gets submitted. This mode is the safety gate between `tailor` and `pdf` in auto-pipeline.

## Input

- `--id <role_id>` (required) — the role whose tailored JSON to audit
- `--auto-fix` (optional) — after reporting, prompt to apply suggested fixes in-place

## Why this mode exists

The 2026-04-24 code review caught 3 CRITICAL truthfulness issues in the Filevine SE tailored resume that would have triggered a background-check rescind: claiming Cox pre-sales leadership Sean didn't have, "Fortune 500" / "seven-figure" qualifiers without verifiable accounts, and a header/summary positioning conflict. Audit catches these before submission.

Lying on a resume is the single fastest way to lose an offer after acceptance. Background checks call references; references contradict; offer rescinded; sometimes after Sean has quit his current job. This mode is non-negotiable.

## Step 1 — Read the inputs (strict order)

Load these files into context in this exact order. Each one anchors a different category of check:

1. `.claude/skills/coin/references/priority-hierarchy.md` — accuracy is rule #1; everything below ladders up to it
2. `.claude/skills/coin/SKILL.md` — extract the **"Sean's canonical facts"** block (education, real role at past clients, pedigree constraint)
3. `data/resumes/base.py` — extract `PROFILE.positions`, `PROFILE.education`, `PROFILE.certifications`, `PROFILE.skills_grid`, `PROFILE.skills`
4. `config/profile.yml` — extract `identity` block + each archetype's `north_star` and `keyword_emphasis`
5. The latest tailored JSON for this role:
   ```bash
   ls -t data/resumes/generated/<id:04d>_*.json | head -1
   ```
6. The role's JD from the DB (both `jd_raw` and `jd_parsed` fields):
   ```python
   .venv/bin/python -c "
   import sqlite3, json, sys
   c = sqlite3.connect('data/db/pipeline.db').cursor()
   r = c.execute('SELECT company, title, jd_raw, jd_parsed FROM roles WHERE id=?', (<id>,)).fetchone()
   print(json.dumps({'company': r[0], 'title': r[1], 'jd_raw': r[2][:5000], 'jd_parsed': r[3]}, indent=2))
   "
   ```

If the tailored JSON does not exist, STOP and tell Sean: *"No tailored JSON for role <id>. Run `/coin tailor <id>` first."*

## Step 2 — Run the 14 audit checks (in order)

> Checks 1-9 are prose-level truthfulness checks (judgment-based on the rendered text).
> Checks 10-14 are **structural** — they call into Python helpers and produce deterministic verdicts. Run them after the prose checks pass.

Each check returns one of: **PASS**, **FAIL** (CRITICAL), **WARN** (HIGH), **PASS-WITH-NOTE** (MEDIUM).
For every non-PASS, capture (a) the offending quote verbatim, (b) why it fails, (c) a concrete fix.

### Check 1 — Education truthfulness (CRITICAL)
Scan `executive_summary` and every `top_bullets[*]` for claims of CS, Computer Science, Engineering (BS/BE), EE, or "ex-FAANG-engineer" framing.
- **FAIL if found.** Sean's degree is BA History (U of Utah) + MBA (WGU). A claimed CS/engineering degree is a background-check landmine.
- **Fix template:** Reword to "MBA + 15 years operator experience" or drop the credential mention entirely.

### Check 2 — Pedigree non-claim (CRITICAL)
Scan for any bullet claiming employment AT a FAANG/big-tech/unicorn company (Netflix, Meta, Google, Apple, Amazon, Microsoft, Stripe, OpenAI, Anthropic, Nvidia, Tesla, LinkedIn, Salesforce, Uber, Airbnb, Palantir, Snowflake, Databricks).
- **FAIL** unless that company appears in `PROFILE.positions[*].company`.
- **Fix template:** Reframe as "for <company> as <Sean's actual employer>'s <Sean's actual role>" (e.g. "for Cox Communications as Hydrant's TPM").

### Check 3 — Cox / TitanX / Safeguard attribution (CRITICAL)
Scan for bullets that attribute outcomes from Cox True Local Labs, TitanX, or Safeguard Global to Sean's personal action without correctly framing him as Hydrant's PM/COO/lead.

**Positive-test rule (PRIMARY):** Any bullet containing the substring "Cox" OR "TitanX" OR "Safeguard" MUST also contain ONE of these framings within the same bullet:
- "as Hydrant's"
- "while at Hydrant"
- "Hydrant's TPM"
- "Hydrant's account lead"
- "fractional COO"
- "as fractional COO"

If the bullet names Cox/TitanX/Safeguard without ANY of those framings → **FAIL** regardless of verb.

**Verb trigger (SECONDARY, catches subtle slips):** FAIL if a bullet about Cox/TitanX/Safeguard uses any of these verbs without proper framing:
- led, drove, ran, headed, headed up, spearheaded, orchestrated, architected, built, launched, shipped, owned, managed, delivered, scaled, took, designed, grew, transformed, operated, championed, ran point on, owned the relationship, drove pre-sales, personally led

- **Fix template:** "Led program execution for <Client>'s <project> as Hydrant's TPM, partnering with <Client> stakeholders through delivery to <verifiable outcome>."

**Trumps:** If both Check 2 and Check 3 fire on the same bullet, report only Check 3 (more specific). If Check 6 also fires (causation), report only Check 3 (attribution is the deeper failure).

### Check 4 — Vague-flex qualifiers (CRITICAL — escalated 2026-04-25)
Scan for unsupported puffery strings. Each match without a verifiable named account in the same bullet → **FAIL**.

**Trigger list (case-insensitive, expand cautiously):**
- Money/scale: "Fortune 500", "Fortune 100", "seven-figure", "eight-figure", "nine-figure", "multi-million", "multi-billion", "NASDAQ:", "NYSE:" (when used as flex, not factual)
- Quality flex: "world-class", "industry-leading", "best-in-class", "cutting-edge", "premier", "top-tier", "blue-chip", "category-leading", "market-leading", "household-name", "elite", "premium"
- Stage flex: "high-growth", "hypergrowth", "mission-critical", "transformational", "strategic", "enterprise-grade"
- Vague scope: "global", "international", "worldwide" (when used without naming the actual countries/regions Sean delivered in)

- **Allowed when verifiable:** "$27M Boston Omaha (NASDAQ: BOMN) acquisition" is fine — NASDAQ is factual context for a real exit. "Fortune 500 energy company" is NOT fine — no named account.
- **Fix template:** Either name the actual account (with permission) or drop the qualifier entirely. Replace "Fortune 500 energy clients" → "energy-sector enterprise clients". Replace "world-class delivery" → drop entirely; the metric speaks for itself.

**Trumps:** If Check 4 and Check 6 both fire on the same bullet (vague flex + causation), report only Check 4 (the puffery is the more obvious recruiter signal).

### Check 5 — Metric provenance (CRITICAL)
For every quantitative claim in `top_bullets` and `executive_summary` (numeric, spelled-out, OR collective-noun), verify it traces back to:
- A `PROFILE.positions[*].bullets` entry, OR
- A `PROFILE.positions[*].summary` entry (start/end dates, location), OR
- A direct quote from the JD (skill counts, "for our 10K-customer base")

**What counts as a quantitative claim:**
- **Numeric:** $1M, 12 months, 40%, 187 countries, $6M→$13M
- **Spelled-out numbers:** "twelve months ahead", "five years", "two dozen products", "three continents"
- **Collective nouns / vague counts:** "dozens of", "several", "multiple", "many", "numerous", "a handful of", "scores of"
- **Team-shape claims:** "five-team standup", "12-person org", "N-pod", "N-squad", "global engineering team across N continents"
- **Tenure / duration claims:** "X years at Y", "in under N years"

**FAIL** if any quantitative claim (in any of the above forms) has no source in PROFILE or JD.

- **Known-good metrics (verified 2026-04-25):** $1M Y1 (Cox), $27M Series A (TitanX), $6M→$13M ARR (Utah Broadband), $27M acquisition (Boston Omaha), 187 countries / 7 localizations / 1000+ pages (Safeguard — confirmed with Sean), 15+ network expansion deployments (Utah Broadband), 100+ internal stakeholders (LINX), 40%+ first-call resolution (LINX — flag for re-confirmation).
- **Fix template:** Drop the unverifiable claim. Replace with a qualitative version ("delivered ahead of schedule" instead of "six weeks ahead"; "across multiple time zones" instead of "across three continents").

**Trumps:** None — Check 5 is the deepest of the integrity checks. If Check 5 and Check 4 both fire (invented metric + vague flex), report both.

### Check 6 — Causation hedging (HIGH)
Scan for strong-causation verbs applied to outcomes Sean didn't solely produce:
- "enabled $X raise", "drove acquisition", "caused growth from $X to $Y"
- **WARN if found** for TitanX Series A, Utah Broadband acquisition, Cox revenue ramp.
- **Fix template:** Soften to "during the period the company raised $X", "served as <role> on the technical side of <outcome>", "owned my book during the $X→$Y ARR phase that culminated in <outcome>".

### Check 7 — Header / summary congruence (CRITICAL)
Read the tailored JSON's `target_role` field. **FAIL** if missing — the recruiter PDF header falls back to `PROFILE.title` ("Senior Technical Program Manager") which conflicts with summary positioning for any lane other than mid-market-tpm AND drifts even for that lane if PROFILE.title later changes.

**Required for every lane (no exemption):**

| Lane | Required `target_role` value |
|---|---|
| `mid-market-tpm` | "Senior Technical Program Manager" (or "Director of Program Management" for Director-titled JDs) |
| `enterprise-sales-engineer` | "Enterprise Sales Engineer / Solutions Architect" |
| `iot-solutions-architect` | "IoT / Wireless Solutions Architect" |
| `revenue-ops-operator` | "Director of Revenue Operations" (or match the JD's exact title) |

- **FAIL** if `target_role` is missing OR doesn't match the lane's required value family.
- **Fix template:** Add `"target_role": "<value from table above>"` to the JSON.

**Trumps:** None. Check 7 is independent.

### Check 8 — JD ↔ skills_gap honesty (HIGH)
For every skill listed as REQUIRED in `jd_parsed.required_skills` (or visibly required in `jd_raw`), verify it appears in EITHER:
- `PROFILE.skills` (Sean genuinely has it), OR
- The tailored JSON's `skills_gap` array (honest gap flagged for prep)

- **WARN** if a known-required JD skill appears in NEITHER place — that's hidden gap territory.
- **Fix template:** Add the missing skill to `skills_gap`. Hidden gaps blow up in technical interviews.

### Check 9 — Domain overreach (HIGH)
Scan `PROFILE.skills_grid["Technical Domain Experience"]` and the tailored JSON for claims of domains where Sean's tenure is < 2 years:
- "Aerospace & Defense" — only via CA Engineering (since Jan 2025, < 16 months)
- "Defense" alone — zero direct delivery in Sean's history
- Any other domain Sean hasn't shipped (verify against PROFILE.positions tenure dates)

- **WARN** for "Aerospace & Defense" with a recommendation to reframe as "Aerospace adjacent (CA Engineering)".
- **FAIL** for "Defense" appearing alone — no support in history.
- **Fix template:** Drop unsupported domains; soften with a tenure qualifier where adjacency is real.

### Check 10 — Metric ↔ outcome row (CRITICAL — structural; locked decision #4)

This is the schema-level truthfulness gate. EVERY numeric token in EVERY rendered bullet must trace to an `outcome` row attached to the bullet's source accomplishment.

Implementation: `careerops.score_panel.truthfulness_gate(generated_json)` walks the bullets, calls `careerops.linter.lint_bullet(text, outcome_rows=...)`, and reports unverified metrics. The numeric normalizer handles `$27M` ↔ `$27 million` ↔ `27,000,000` so equivalent forms compare equal.

- **FAIL** when any metric token does not match any linked outcome row.
- **Fix template:** Either (a) add an `outcome` row + `evidence` row via `/coin add-evidence <accomplishment_id>`, or (b) rewrite the bullet to drop the unbacked claim.
- **Refusal to soften:** the renderer in `scripts/render_resume.py` also enforces this gate; truth=❌ blocks SHIP-READY verdict.

### Check 11 — Buzzword density + kill-words (HIGH)

`careerops.linter.lint_resume(bullets)` runs against the joined corpus.

- **FAIL** if any kill-word from `data/linter/buzzwords.json` appears (52 kill-words including "responsible for", "helped with", "team player", "world-class", "thought leader", etc.).
- **FAIL** if buzzword density > 6.0% across the resume (12 strong-verb flags / 100 tokens).
- **WARN** if soft-kill words appear without `accomplishment.linter_override`.
- **Fix template:** Replace kill-words with action verbs from audit.md Check 3 list (drove, headed, spearheaded, architected, championed). Tone down density by varying verbs.

### Check 12 — Recruiter-eye 30-sec audit (HIGH)

Re-parse the rendered PDF via `careerops.parser.parse_resume_pdf` and run the 8 visual checks documented in `modes/recruiter-eye.md`:
- Name presence + ≥14pt size
- Contact in body, not header/footer
- Date format consistency
- Canonical sections present (experience + education minimum)
- Bullet density per role (3-5 newest, no 8+ ever)
- No Unicode glyphs outside `–•·*`
- Page count discipline (1 for ATS-strict; ≤2 for designed)
- Mono-column layout (ATS-strict only)

- **FAIL** for any FAIL-level recruiter-eye finding.
- **WARN** acceptable for non-blocking visual issues.

### Check 13 — ATS parseability self-check (HIGH; structural)

`careerops.parser.parse_resume_pdf(pdf_path).ats_score()` re-parses our own rendered PDF. The score is the percentage of canonical signals (name, email, phone, sections, dates, monocolumn, glyph-clean, page-count) successfully extracted.

- **FAIL** if `ats_score < 70` on the ATS-strict variant (`*.ats.pdf`).
- **WARN** if `ats_score < 85` on any designed variant.
- **Fix template:** address the missing signal directly — a low score means a real ATS will likely also fail. The parser report itself shows which signal is missing.

### Check 14 — Lightcast keyword overlap (HIGH)

`careerops.score_panel.keyword_overlap_pct(generated_json, role_id=role_id)` computes the percent of role's `must_have` JD keywords that appear in the rendered text. The JD-keyword extraction comes from `careerops.jd_parser` (Lightcast subset + must-have/nice-to-have classification).

- **FAIL** if `keyword_overlap_pct < 40` on the must-have set.
- **WARN** if `keyword_overlap_pct > 90` (stuffing risk).
- **Target band: 60-85%.**
- **Fix template:** Surface missing must-have terms in `skills_matched` if they're genuinely supported in PROFILE; otherwise add to `skills_gap` and reflect in the cover letter hook.

## Step 3 — Output format

Print the audit report in this exact shape:

```
═══════════════════════════════════════════════
  AUDIT — Role <id>: <company> — <title>
  JSON: <path/to/json>
  Lane: <lane>  ·  Verdict: <CLEAN | NEEDS REVISION | BLOCK>
═══════════════════════════════════════════════

CRITICAL (block submission):
  ✗ Check 3 — Cox attribution
    Quote: "Personally led pre-sales discovery and stakeholder demos for Cox"
    Why:   Sean was Hydrant's TPM on the Cox account, not Cox's SE.
           Reference call to Cox would expose this immediately.
    Fix:   "Led program execution for Cox Communications' True Local Labs as
           Hydrant's TPM, partnering with Cox stakeholders through delivery to
           $1M Year 1 revenue."

HIGH (resolve before submission):
  ⚠ Check 4 — Vague-flex qualifier
    Quote: "...for Fortune 500 clients"
    Why:   No named account verifies "Fortune 500" framing.
    Fix:   Drop the qualifier or name the actual accounts (with permission).

PASSED (n of 9 checks):
  ✓ Check 1 (education)         ✓ Check 2 (pedigree)
  ✓ Check 5 (metric provenance) ✓ Check 6 (causation hedging)
  ✓ Check 7 (header congruence) ✓ Check 8 (gap honesty)
  ✓ Check 9 (domain overreach)

Verdict: BLOCK — fix the CRITICAL items before /coin pdf <id> --recruiter.
```

### Verdict rules
- **CLEAN** = 0 CRITICAL, 0 HIGH
- **NEEDS REVISION** = 0 CRITICAL, 1+ HIGH
- **BLOCK** = 1+ CRITICAL

## Step 4 — Auto-fix flow (only when `--auto-fix`)

If verdict is non-CLEAN AND `--auto-fix` was passed, prompt:

> "Apply the suggested fixes to <path/to/json> now? Show me the diff first. (yes/no)"

**HUMAN GATE — never silently rewrite a tailored artifact.** If Sean says yes:

1. Show the unified diff between current JSON and proposed fixes
2. Wait for explicit "yes" to apply
3. Apply fixes in place (overwrite the JSON)
4. Re-run the 9 checks
5. If verdict is now CLEAN: print "✅ Audit clean after fix. Run `/coin pdf <id> --recruiter`."
6. If still non-CLEAN: stop and tell Sean which checks still fail; he edits manually

Never iterate auto-fix more than 2 times — if 2 passes can't get to CLEAN, the issues need human judgment.

## Step 5 — Recommend next step

After the report:

| Verdict | Recommend |
|---|---|
| CLEAN | `/coin pdf <id> --recruiter` |
| NEEDS REVISION | "Review HIGH issues. They won't block submission but may hurt at interview. Continue: `/coin pdf <id> --recruiter`. Fix later: edit JSON + `/coin audit <id>`." |
| BLOCK | "DO NOT submit. Fix CRITICAL items: edit JSON manually OR run `/coin audit <id> --auto-fix`." |

## Step 6 — Notes for the executor

- Audit is read-only by default. Only `--auto-fix` can write — and even then only with two human confirmations (yes to fix, yes to apply diff).
- The 9 checks are not heuristics — they encode lessons from real failure modes (the 2026-04-24 code review). Don't soften them.
- If you find a new failure mode not covered by the 9 checks, surface it to Sean AND open a follow-up to extend this mode. Don't silently bake undocumented checks in.
- This mode is called by `auto-pipeline` between tailor and pdf. Keep it fast — under 30 seconds per audit on a typical role.
- Never claim a JSON is CLEAN if you skipped any check. If the JD's `jd_parsed` is missing (Check 8 needs it), report Check 8 as INDETERMINATE and recommend running `/coin score <id>` first.
