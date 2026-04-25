---
task: COIN-COVER-LETTER
title: Author modes/cover-letter.md — separate cover letter generation (proficiently pattern)
phase: Modes Build-Out
size: M
depends_on: COIN-AUDIT
created: 2026-04-25
---

# COIN-COVER-LETTER: Author `modes/cover-letter.md`

## Context

Cover-letter generation is currently folded into `modes/tailor.md` as a one-line "hook" inside the resume JSON. Two problems:

1. **Output mismatch.** Most ATS systems ask for a separate cover-letter file (PDF or text paste). The hook-inside-JSON path produces nothing droppable.
2. **Voice mismatch.** A resume bullet is past-tense, metric-led, terse. A cover letter is present-tense, narrative, slightly less formal. Trying to share a generation pass produces flat output in both.

The `proficiently` skill collection separates these — its cover-letter pattern reads the JD + tailored resume + PROFILE narrative, produces a 3-paragraph letter (hook → proof → fit), and renders it as a standalone PDF in the same `data/resumes/generated/` directory.

This mode adds that capability without disturbing `tailor.md`. The two stay separate; auto-pipeline calls both in sequence.

## Goal

Create `modes/cover-letter.md` so that `/coin cover-letter <id>` reads the role's tailored resume JSON + parsed JD + PROFILE, generates a structured 3-paragraph letter (hook, proof, fit) in Sean's voice, persists it as JSON, and renders a print-ready PDF at `data/resumes/generated/<id:04d>_<lane>_<date>_cover.pdf`.

## Pre-conditions

- [ ] Role has status ≥ `resume_generated` (we need the tailored JSON to anchor the letter to the resume's chosen stories)
- [ ] Tailored JSON exists at `data/resumes/generated/<id:04d>_*.json`
- [ ] Parsed JD exists in DB (`roles.jd_parsed` is non-null)
- [ ] PDF rendering deps work (`weasyprint` + `jinja2` + `brew install pango`)

## Steps

### Step 1 — HTML template

Add `data/cover_letter_template.html` — a single-page Jinja2 template:

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    @page { size: Letter; margin: 1in; }
    body { font-family: Georgia, serif; font-size: 11pt; line-height: 1.45; color: #222; }
    .header { margin-bottom: 1.2em; }
    .header .name { font-size: 14pt; font-weight: bold; }
    .header .contact { color: #555; font-size: 10pt; }
    .date { margin: 1.2em 0 0.6em; color: #555; }
    .recipient { margin-bottom: 1.2em; }
    p { margin: 0 0 0.9em; }
    .signoff { margin-top: 1.5em; }
  </style>
</head>
<body>
  <div class="header">
    <div class="name">{{ profile.name }}</div>
    <div class="contact">{{ profile.email }} · {{ profile.phone }} · {{ profile.city }}, {{ profile.state }} · {{ profile.linkedin }}</div>
  </div>
  <div class="date">{{ today }}</div>
  <div class="recipient">
    {% if recipient_name %}{{ recipient_name }}<br>{% endif %}
    Hiring Team — {{ company }}<br>
    Re: {{ title }}
  </div>
  <p>{{ paragraphs.hook }}</p>
  <p>{{ paragraphs.proof }}</p>
  <p>{{ paragraphs.fit }}</p>
  <div class="signoff">
    Best,<br>
    {{ profile.name }}
  </div>
</body>
</html>
```

Use `Environment(autoescape=select_autoescape(['html']))` per the existing render_pdf.py pattern (security parity).

### Step 2 — Renderer script

Add `scripts/render_cover_letter.py` modeled exactly on `scripts/render_pdf.py`:

- Args: `--role-id N` (required), `--out PATH` (optional override)
- Reads role row from DB, locates tailored JSON
- Reads cover-letter JSON at `data/resumes/generated/<id:04d>_*_cover.json`
- Renders via Jinja2 → WeasyPrint with `base_url` scoped to `data/` (NOT cwd)
- Writes PDF to `data/resumes/generated/<id:04d>_<lane>_<date>_cover.pdf`
- Idempotent — overwrites existing cover PDF for the same role/date

Add `COVER_TEMPLATE_PATH` to `config.py` alongside the existing `RECRUITER_TEMPLATE_PATH`.

### Step 3 — Author `modes/cover-letter.md`

The mode must instruct the agent to:

**3.1 — Load context.**
- Tailored resume JSON (the chosen North Star + chosen 3 lead stories)
- Parsed JD (company name, role title, top 5 keywords, hiring-manager name if present)
- `config/profile.yml` for the archetype's voice / North Star pitch
- Sean's PROFILE for letter header (name, email, phone, city, linkedin)

**3.2 — Truthfulness gate.** Re-read the gates from `modes/_shared.md` Operating Principle #3 BEFORE drafting. Specifically:
- Cox / TitanX / Safeguard outcomes are Hydrant engagements, not Sean-as-employee
- No "Fortune 500" / "seven-figure" / "world-class" without a verifiable named account
- No CS / engineering degree
- No invented metrics — every number must trace to PROFILE.positions

**3.3 — Generate the 3 paragraphs.**

**Hook (≤ 80 words)** — Lead with the North Star pitch from `profile.yml` for the role's archetype, immediately tied to the company's stated need (pulled from the JD's first-paragraph language). NOT a generic "I am writing to apply for...". Example shape:
*"<Company> is scaling <stated initiative>. That's the problem I solved at Hydrant — <one specific Hydrant outcome with metric>. I'm a TPM by trade, MBA by training, PMP by certification — and I'd rather build <archetype-relevant thing> than manage status decks."*

**Proof (≤ 130 words)** — Pick the SAME 2 lead stories already chosen in the tailored resume JSON. Re-narrate them in present-tense, narrative voice (not bullet voice). Each story must:
- Open with the named engagement (Cox True Local Labs / Utah Broadband / TitanX) AND Sean's actual role on it (Hydrant PM / Enterprise AM / fractional COO)
- Land on the metric (already in PROFILE)
- Bridge to the JD's stated requirement explicitly (cite a JD keyword by name)

**Fit (≤ 70 words)** — Two parts:
1. One sentence on Utah / remote / locations match (drawn from JD's location field + `config/profile.yml` target_locations)
2. One sentence acknowledging the strongest gap honestly + how Sean closes it (e.g., "no formal CS training; I close that with PMP rigor and 15 years of wireless / IoT delivery"). Honesty is differentiating.

Final paragraph length budget: ≤ 280 words total. Do not pad.

**3.4 — Persist as JSON.** Write to `data/resumes/generated/<id:04d>_<lane>_<date>_cover.json`:

```json
{
  "role_id": 137,
  "company": "Filevine",
  "title": "Senior Solutions Engineer",
  "lane": "enterprise-sales-engineer",
  "recipient_name": null,
  "today": "2026-04-25",
  "paragraphs": {
    "hook": "...",
    "proof": "...",
    "fit": "..."
  },
  "stories_used": ["utah_broadband_acquisition", "cox_true_local_labs"],
  "jd_keywords_cited": ["enterprise SaaS", "IoT integration", "pre-sales"],
  "audit_passes": true,
  "generated_at": "2026-04-25T..."
}
```

`stories_used` MUST be a subset of the resume JSON's chosen stories (parity check).
`jd_keywords_cited` MUST be substrings of the JD parsed-keywords list (parity check).

**3.5 — Render PDF.** Invoke `scripts/render_cover_letter.py --role-id <id>`. Confirm the file size > 4KB (sanity check — PDF generation succeeded with content).

**3.6 — Audit hand-off.** Run a stripped-down audit pass on the cover letter JSON (re-use `modes/audit.md` checks 1, 2, 3, 4, 5 — the truthfulness ones; skip orthogonality/lane checks which are resume-specific). If any check fails, STOP — print the failures, do NOT render PDF, await Sean's fix.

**3.7 — Output summary.**

```
═══════════════════════════════════════════════
  Cover Letter — Role <id>
  <company> · <title>
═══════════════════════════════════════════════

Stories used (parity with resume): cox_true_local_labs, utah_broadband_acquisition
JD keywords cited: enterprise SaaS, IoT integration, pre-sales
Audit: ✅ 5/5 truthfulness checks pass
Length: 247 words / 280 max

Files:
  → data/resumes/generated/0137_enterprise-sales-engineer_2026-04-25_cover.json
  → data/resumes/generated/0137_enterprise-sales-engineer_2026-04-25_cover.pdf

NEXT
  → Review the PDF
  → Edit the JSON if needed → re-render: /coin cover-letter <id> --rerender
  → Then: /coin apply <id>   (cover letter will auto-attach)
```

### Step 4 — Auto-pipeline integration

In `modes/auto-pipeline.md` Step 6 (Render):
- Currently renders `--brief` and `--recruiter` PDFs
- Add: also call `cover-letter <id>` mode after audit passes, before reporting
- If cover-letter audit fails, the auto-pipeline reports BOTH PDFs (resume) AND the cover-letter failure, then surfaces a fix path — does not block the resume

### Step 5 — Apply mode integration

In `modes/apply.md`:
- Greenhouse field 5 (Cover Letter file upload): use the cover PDF if it exists at the conventional path; previously this was "skip if not generated"
- Lever field 7 (Additional Information textarea): paste the `paragraphs.hook` value from the cover JSON (NOT the whole letter — the textarea is a hook field)

### Step 6 — Add safety guards

The mode must explicitly REFUSE:

| Refusal | Why |
|---|---|
| Generating a cover letter without a tailored resume JSON in place | Stories must match resume — sequence enforced |
| Citing a metric not in PROFILE.positions | Truthfulness gate |
| Claiming Cox/TitanX/Safeguard outcomes as Sean's direct employment | Truthfulness gate |
| Adding "I am writing to apply for..." style filler | Burns the first sentence of attention |
| Exceeding 280 words | ATS reviewers skim — long letters hurt |
| Auto-attaching to an apply session without `audit_passes: true` in JSON | Hard gate |

### Step 7 — Test

Add `tests/test_cover_letter_mode.py`:
1. Read `modes/cover-letter.md`
2. Assert each step (3.1–3.7) is present
3. Assert the 3-paragraph structure (hook/proof/fit) is documented with word budgets
4. Assert all 6 refusals from Step 6 are present
5. Assert truthfulness gate references `modes/_shared.md` Operating Principle #3
6. Assert `stories_used` parity check is documented
7. Assert `jd_keywords_cited` parity check is documented

Add `tests/test_render_cover_letter.py`:
1. Build a fixture cover JSON
2. Render to a temp file
3. Assert PDF created and > 4KB
4. Assert PDF text (extract via pdfplumber if available; else just byte-grep) contains the company name, role title, and Sean's name

### Step 8 — SKILL.md + _shared.md routing

`SKILL.md` — Mode Routing:
```
| `cover-letter <id>` or `cover <id>` | `modes/cover-letter.md` (separate cover letter generation) |
```

`SKILL.md` — Discovery menu:
```
  /coin cover-letter <id>     Generate standalone cover letter PDF
```

`modes/_shared.md` — mode catalog:
```
| `cover-letter` | Generate 3-para cover letter (hook/proof/fit) + PDF | `modes/cover-letter.md` |
```

## Verification

```bash
cd /Users/tealizard/Documents/lab/coin
.venv/bin/pytest tests/test_cover_letter_mode.py tests/test_render_cover_letter.py -v --tb=short

# Manual smoke (need a real role with status >= resume_generated)
# /coin cover-letter 4   (Netflix — should generate matching the existing resume's stories)
ls -la data/resumes/generated/0004_*_cover.{json,pdf}
```

- [ ] `modes/cover-letter.md` exists, follows the step shape
- [ ] `scripts/render_cover_letter.py` produces a valid PDF
- [ ] Letter respects 280-word total budget
- [ ] All 6 Step 6 refusals are explicit
- [ ] `stories_used` and `jd_keywords_cited` parity checks are enforced
- [ ] Auto-pipeline integration is wired (Step 4)
- [ ] Apply-mode integration is wired (Step 5)
- [ ] Tests pass

## Definition of Done

- [ ] `modes/cover-letter.md` authored
- [ ] `scripts/render_cover_letter.py` produces valid PDF on a real role
- [ ] `data/cover_letter_template.html` exists
- [ ] Cover for role 4 (Netflix) generated successfully (or rejected by audit with clear reason)
- [ ] `docs/state/project-state.md` updated
- [ ] No regressions in existing `pytest tests/`

## Rollback

```bash
rm modes/cover-letter.md tests/test_cover_letter_mode.py tests/test_render_cover_letter.py
rm scripts/render_cover_letter.py data/cover_letter_template.html
git checkout .claude/skills/coin/SKILL.md modes/_shared.md modes/auto-pipeline.md modes/apply.md config.py docs/state/project-state.md
rm -f data/resumes/generated/*_cover.json data/resumes/generated/*_cover.pdf
```

## Notes for the executor

- The 280-word budget is firm. Hard-stop the generator if it goes over and have the agent re-draft.
- Honesty in the "fit" paragraph is the entire differentiator — DON'T paper over the CS-degree gap; lean into PMP + 15-yr delivery as the closing argument.
- Auto-pipeline integration must be additive — if cover-letter fails, resume-render still ships. Cover letter is an enhancement, not a blocker for the auto-pipeline.
- Render security parity with `render_pdf.py`: Jinja autoescape on, base_url scoped to data/.
- The recipient_name field stays nullable. Looking up hiring managers by name is a separate manual step (and proficiently pattern); we keep the field for when COIN-NETWORK-SCAN surfaces one.
