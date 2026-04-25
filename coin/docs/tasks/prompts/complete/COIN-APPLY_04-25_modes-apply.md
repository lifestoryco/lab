---
task: COIN-APPLY
title: Author modes/apply.md — assisted ATS form fill (Greenhouse, Lever, Workday)
phase: Modes Build-Out
size: L
depends_on: COIN-AUDIT, COIN-AUTOPIPELINE
created: 2026-04-25
---

# COIN-APPLY: Author `modes/apply.md`

## Context

After auto-pipeline produces a tailored PDF, the last-mile friction is filling out the ATS form: copy-paste address, paste resume PDF, paste cover letter, click "yes I am authorized to work in the US", check 6 EEO boxes, click "Submit". This is 5–15 minutes per application × dozens of applications. It is the highest-volume manual cost in the job search.

The proficiently/proficiently-claude-skills repo solved this with browser automation patterns for the three major ATS providers. We installed their reference at `.claude/skills/coin/references/ats-patterns.md` — it contains exact field selectors, URL patterns, iframe quirks, and known-impossible operations (e.g., Workday account creation) for Greenhouse, Lever, and Workday.

`apply` mode wires that reference into a callable Coin command. It does NOT submit; it pre-fills every field it can, leaves the human gate at "Submit", surfaces fields that still need manual answers (essays, work-history detail).

## Goal

Create `modes/apply.md` so that `/coin apply <id>` opens the role's apply URL in a browser, detects the ATS provider from the URL, follows the patterns in `references/ats-patterns.md` to pre-fill every standard field using data from `data/resumes/base.py` PROFILE and the tailored JSON, then stops at the Submit button and surfaces a checklist of any field it couldn't fill so Sean can finish manually.

## Pre-conditions

- [ ] `references/ats-patterns.md` exists at `.claude/skills/coin/references/ats-patterns.md` with patterns for Greenhouse, Lever, Workday
- [ ] Role has status `resume_generated` and a tailored JSON exists in `data/resumes/generated/`
- [ ] PDF artifact exists at `..._recruiter.pdf` (else run `/coin pdf <id> --recruiter` first)
- [ ] The MCP browser tool (Claude in Chrome / Claude Preview) is available and connected to a Chrome instance
- [ ] PROFILE.email, phone, city, linkedin are populated (these are the most-asked ATS fields)

## Steps

### Step 1 — ATS detection

Author `modes/apply.md`. The mode must instruct the agent to detect the ATS provider from the role's `url` field:

```
URL contains "greenhouse.io" or "boards.greenhouse.io" or "job-boards.greenhouse.io"  → ATS = greenhouse
URL contains "jobs.lever.co"                                                          → ATS = lever
URL contains "myworkdayjobs.com" or "*.wd*.myworkdayjobs.com"                         → ATS = workday
URL contains "ashbyhq.com"                                                            → ATS = ashby (best-effort, no reference yet)
URL contains "linkedin.com/jobs/view"                                                 → ATS = linkedin (Easy Apply only — see Step 6)
URL anything else                                                                     → ATS = unknown — open and ask Sean to identify
```

After detection, load the corresponding section from `references/ats-patterns.md` into context. If `unknown`, fall back to the generic flow in Step 4.

### Step 2 — Open the apply URL

Use the browser MCP tool to navigate to the role's apply URL. Specifically:
- Greenhouse: navigate to the iframe src directly (extract `boardToken` and `jobToken` per the JS snippet in ats-patterns.md, then build `https://job-boards.greenhouse.io/embed/job_app?for={boardToken}&token={jobToken}`)
- Lever: append `/apply` to the posting URL
- Workday: append `/applyManually` (NOT `/autofillWithResume` — autofill triggers Workday's resume parser which often misreads our PDF)

If the page requires login (Workday), STOP and tell Sean: *"Workday requires account creation/sign-in before form fields are accessible. Please sign in manually, then say 'continue' and I'll resume."*

### Step 3 — Per-ATS field-fill flows

The mode must enumerate the field-fill order for each ATS, drawn from `references/ats-patterns.md`:

**Greenhouse field order:**
1. First Name, Last Name (from PROFILE.name split on space)
2. Email (PROFILE.email)
3. Phone (PROFILE.phone)
4. Resume/CV file upload — PDF at `data/resumes/generated/<id:04d>_*_recruiter.pdf`
5. Cover Letter file upload (if generated; else skip)
6. Location (City) — PROFILE.city without state
7. Country Code (US) — dropdown
8. LinkedIn Profile (PROFILE.linkedin)
9. "How did you hear about us?" — Sean must answer (surface to checklist)
10. EEO section — leave blank, Sean answers
11. Work auth questions — Sean answers (don't auto-claim citizenship)
12. Privacy policy checkbox — leave for Sean
13. **STOP at Submit button**

**Lever field order:**
1. Resume/CV file upload (top of form)
2. Full name (PROFILE.name as one string)
3. Pronouns checkboxes — Sean fills
4. Email, Phone, Current location (PROFILE.city)
5. Current company — PROFILE.positions[0].company
6. LinkedIn URL, Twitter, GitHub, Portfolio (only fields Sean has — surface missing)
7. Additional Information textarea — paste the cover letter hook from JSON
8. Custom company sections — Sean fills
9. EEO survey — Sean fills
10. **STOP at Submit button**

**Workday field order (6-page wizard, fill what you can per page, stop at "Save and Continue" on each):**
- Page 1 (My Information): name, address, phone, email, country
- Page 2 (My Experience): map PROFILE.positions to Workday's experience entries — Sean reviews each
- Page 3 (Application Questions): all manual
- Page 4 (Voluntary Disclosures): all manual
- Page 5 (Self Identify): all manual
- Page 6 (Review): scroll, present, **STOP**

### Step 4 — Generic flow (unknown ATS)

If detection failed, open the URL, run a `read_page` snapshot, list every visible form field with its label, and ask Sean: *"This isn't a known ATS. Want me to fill standard fields where the labels are obvious? (y/n)"*. If yes, do best-effort using PROFILE data. If no, just leave the page open.

### Step 5 — Pre-fill protocol

For every field the mode fills, it MUST:
1. Read the current value first (don't overwrite if Sean already typed)
2. Type / select the value
3. Take a snapshot after fill to confirm it stuck (some Workday combo-boxes silently reject without errors)
4. Log the fill in a session manifest (in-memory, printed at end)

For every field it CAN'T fill (essays, conditional checkboxes, custom dropdowns), add to the manifest's "needs Sean" list.

### Step 6 — LinkedIn Easy Apply (special case)

If ATS = linkedin AND the URL is a LinkedIn job posting:
- Easy Apply is a multi-page modal, not a real form — skip browser automation
- Print: *"LinkedIn Easy Apply — modal-based, no browser automation. Open the posting in your browser and click 'Easy Apply' yourself. Sean's resume PDF: <path>. I'll wait for the 'applied' transition."*
- Skip to Step 7 with empty manifest

### Step 7 — Final checklist + human gate

Print the session manifest:

```
═══════════════════════════════════════════════
  Apply Session — Role <id>
  <company> — <title>
  ATS: <provider>
═══════════════════════════════════════════════

FILLED (n):
  ✓ First Name, Last Name
  ✓ Email
  ✓ Phone
  ✓ Resume/CV (uploaded data/resumes/.../0137_..._recruiter.pdf)
  ✓ LinkedIn URL
  ✓ City
  ✓ Country (US)
  ...

NEEDS YOU (m):
  □ "How did you hear about us?" — pick a value
  □ Work auth: "Are you authorized to work in the US?" — pick yes/no
  □ EEO section (Race, Gender, Veteran, Disability) — pick or skip
  □ Privacy policy checkbox

NEXT STEP
  → Finish the m fields above
  → Click Submit
  → Then: /coin track <id> applied
```

**HUMAN GATE — never automated:**
- Submit button click — NEVER auto-click. Sean clicks Submit.
- The `applied` transition — NEVER auto-set after fill. Sean confirms after Submit.

### Step 8 — Add safety guards

The mode file must explicitly REFUSE the following with a clear error:

| Refusal | Why |
|---|---|
| Auto-clicking Submit | Real-world commitment — only Sean submits |
| Filling work-authorization "Yes I am a US citizen" | Legal claim — Sean answers |
| Filling EEO/disability/veteran questions | Personal disclosure — Sean answers |
| Auto-creating a Workday account | Prohibited per ats-patterns.md and risk of TOS violation |
| Filling salary expectation fields | Negotiation matter — Sean answers strategically |

### Step 9 — Smoke test

Add `tests/test_apply_mode.py`. Browser automation is hard to unit-test, so this test verifies the structural safety:

1. Read `modes/apply.md` content
2. Assert each Step (1–8) is present
3. Assert all five "Refusal" rules from Step 8 are documented
4. Assert "STOP at Submit button" appears in each ATS section
5. Assert the human gates ("never auto-click", "never auto-set applied") are explicit

### Step 10 — Update SKILL.md trigger

The SKILL.md table already routes `apply <id>` to `modes/apply.md`. Confirm the routing line and the menu line.

## Verification

```bash
cd /Users/tealizard/Documents/lab/coin
.venv/bin/pytest tests/test_apply_mode.py -v --tb=short

# Manual smoke (need a real Greenhouse role)
# /coin apply <id-of-a-greenhouse-role>
# Expect: browser opens to the form, fields fill, manifest prints, NO submit
```

- [ ] `modes/apply.md` exists, follows the 10-step shape
- [ ] ATS detection covers Greenhouse, Lever, Workday, LinkedIn, Ashby (best-effort), unknown
- [ ] Per-ATS flows match `references/ats-patterns.md` field orders exactly
- [ ] All 5 Step 8 refusals are explicit in the mode text
- [ ] Submit button is never auto-clicked
- [ ] `applied` transition requires separate `/coin track <id> applied` command
- [ ] Smoke test passes

## Definition of Done

- [ ] `modes/apply.md` authored
- [ ] Manual smoke on a real Greenhouse role pre-fills 6+ fields and stops at Submit
- [ ] Manifest accurately lists FILLED vs NEEDS YOU
- [ ] `docs/state/project-state.md` updated
- [ ] No regressions in existing `pytest tests/`

## Rollback

```bash
rm modes/apply.md tests/test_apply_mode.py
git checkout .claude/skills/coin/SKILL.md
git checkout docs/state/project-state.md
```

The browser MCP tool remains available for ad-hoc use; only the wired mode is removed.

## Notes for the executor

- The browser MCP tool is "Claude in Chrome" or "Claude Preview" — both can navigate, read pages, and fill forms. Prefer Claude in Chrome for real ATS sites because Claude Preview has CSP restrictions.
- If the mode finds a new ATS pattern not in `references/ats-patterns.md`, document it inline in the role's `notes` field AND open a follow-up task to extend the reference doc. Do not silently bake undocumented patterns into the mode.
- File upload via browser automation is brittle. Use the `file_upload` MCP tool when present; fall back to printing the PDF path and asking Sean to drag-drop.
