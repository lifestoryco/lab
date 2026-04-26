# Coin Mode — `recruiter-eye` (30-second human-screener heuristic audit)

> Load `modes/_shared.md` first.

**Purpose:** Run the same 30-second visual scan a recruiter does on first
glance. ATS parsers can pass a resume that a human eye instantly rejects.
This audit catches the human-screener failure modes that the structural
truth gate doesn't:

- Name too small or centered (parses worse on some ATS, looks weak)
- Contact in header/footer (some ATS skip; recruiters miss it)
- Date format inconsistent
- Bullet density imbalanced (12 bullets on most-recent, 1 on prior — looks like cherry-picking)
- Newest role doesn't visually dominate
- Unicode glyph icons (font-icon characters from FontAwesome PUA range)
- Multi-page when single-page is appropriate
- Two-column-via-tables (Jobscan's Lever test produced word salad)

This mode is invoked automatically by `scripts/render_resume.py` per
locked decision #4 — every render gets a recruiter-eye pass before the
score panel reports SHIP-READY.

---

## Hard refusals

| Refusal | Why |
|---|---|
| Marking a render SHIP-READY when recruiter-eye fails | The score panel's verdict must NEVER mask a human-screener red flag |
| Suggesting Unicode-glyph fixes ("just use a different bullet character") that aren't in the ATS-safe set `–•·*` | Per resume-eng research, anything outside this set risks ATS dropout |
| Skipping page-count enforcement on the ATS-strict variant | Multi-page hurts ATS parsers' reading-order recovery |
| Auto-fixing the resume — recruiter-eye is read-only | Fixes happen in tailor.md or in the source data; this mode reports |

---

## Step 1 — Re-parse the rendered PDF

```python
from careerops.parser import parse_resume_pdf
parse = parse_resume_pdf(pdf_path)
```

This gives us:
- `parse.fields` — name / email / phone / url / location
- `parse.sections` — canonical section detection
- `parse.lines` — every line with x/y/height
- `parse.n_pages`
- `parse.ats_score()` — composite 0..100

---

## Step 2 — Visual checks (each is a hard pass/fail or warn)

For each check below, emit one of:
- `PASS` (green)
- `WARN` (yellow — fixable but not blocking)
- `FAIL` (red — blocks SHIP-READY verdict)

### 2.1 Name presence + size

- FAIL if `parse.fields.name` is missing.
- FAIL if the line carrying the name has `avg_height < 14`.
  (Body text is ~10pt; name should be 14-18pt — RenderCV's 9 themes all
  conform, this catches custom-broken templates.)
- WARN if name line is centered horizontally (some ATS parse worse).

### 2.2 Contact block in document body

- FAIL if email or phone is in a line whose y-coordinate is in the top
  20pt of the page (likely header) or bottom 30pt (likely footer).
  pypdfium2 reports y in PDF coords (bottom-up); use `parse.n_pages`
  + per-page heights to check.

### 2.3 Date format consistency

- For each section.lines containing a date, count occurrences of:
  - `Mon YYYY – Mon YYYY` (preferred)
  - `MM/YYYY` (acceptable)
  - `YYYY` only (acceptable for education)
  - Any other format → WARN

- FAIL if dates are mixed within a single position entry.

### 2.4 Section labels canonical

- FAIL if `experience` canonical section missing.
- FAIL if `education` canonical section missing.
- WARN if `summary` section is missing (most resumes benefit; some
  ATS-strict variants intentionally skip).

### 2.5 Bullet density per role

- For each ExperienceEntry section, count bullets.
- WARN if newest role has fewer bullets than the prior role
  (cherry-picking signal).
- FAIL if any role has ≥ 8 bullets (reads as overstuffed).
- WARN if total bullets across resume < 8 (looks thin).

### 2.6 Unicode glyph garbage

- FAIL if `parse.raw_text` contains Private-Use-Area chars (U+E000-U+F8FF).
- WARN if non-ASCII bullet characters outside `–•·*` appear.

### 2.7 Page count discipline

- For ATS-strict variant: FAIL if `parse.n_pages > 1`.
- For designed variants: FAIL if `parse.n_pages > 2`.

### 2.8 Mono-column layout

- Use `careerops.parser._looks_monocolumn(lines)` heuristic.
- FAIL on the ATS-strict variant if not mono-column.

---

## Step 3 — Aggregate verdict

```
PASS = no FAILs (WARNs allowed)
FAIL = any FAIL
```

Persist as part of the `render_artifact.notes` field (e.g.
`"recruiter-eye: PASS (2 WARN)"` or `"recruiter-eye: FAIL — name <14pt; experience section missing"`).

---

## Step 4 — Surface in the score panel

The score panel's printed report includes the recruiter-eye summary line:

```
  Recruiter-eye 30-sec audit:    PASS ✅
  Recruiter-eye 30-sec audit:    FAIL ❌  (name <14pt; experience section missing)
```

A FAIL flips the score panel verdict to `RECRUITER-EYE FAIL` even if
ATS, truthfulness, and density all pass.

---

## Required structural tests

`tests/test_recruiter_eye_mode.py` asserts:
- Eight visual-check sections present (2.1–2.8)
- The four hard refusals present
- Page-count rules differ between ATS-strict and designed
- Glyph blacklist includes the PUA range
- The aggregate verdict is binary (PASS/FAIL)
