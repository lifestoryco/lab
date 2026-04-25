---
task: COIN-ONBOARDING-EXECUTABLE
title: Convert SKILL.md narrative onboarding to executable AskUserQuestion blocks (job-scout port)
phase: Skill Hardening
size: M
depends_on: COIN-AUTOPIPELINE
created: 2026-04-25
---

# COIN-ONBOARDING-EXECUTABLE: Make SKILL.md Onboarding Section Actually Run

## Context

`.claude/skills/coin/SKILL.md` has a 9-step "Onboarding (for first-time users)" section authored as prose: *"Drop a resume file path...", "Use AskUserQuestion with options derived from the resume..."*. It reads like a spec, not a runtime. When a new user runs `/coin setup` or first-runs `/coin` with a placeholder PROFILE, nothing actually fires AskUserQuestion — the agent has to improvise the onboarding flow each time, often skipping steps, misaligning option lists with the resume, or forgetting to write `config/profile.yml`.

The `job-scout` skill (referenced in `.claude/skills/coin/references/`) ships an executable onboarding pattern: a dedicated mode file with explicit `AskUserQuestion` invocations, structured option lists derived deterministically from the resume input, and a single write step at the end that produces both `profile.yml` and `base.py` updates atomically.

This task ports that pattern. After it lands, `/coin setup` (or any first-run with a placeholder PROFILE) deterministically walks Sean (or any future user) through the 9 questions in order, with the right option set at each step, and lands on a written profile.

## Goal

Move the onboarding flow from prose-in-SKILL.md to an executable `modes/onboarding.md`. The mode uses literal AskUserQuestion blocks with deterministic option lists. After completion, `config/profile.yml` and `data/resumes/base.py` are updated and a smoke discovery runs.

## Pre-conditions

- [ ] AskUserQuestion tool is available in the executing session (it's a deferred tool — confirm via ToolSearch at mode entry)
- [ ] Existing PROFILE in `data/resumes/base.py` is either placeholder (Sean must opt-in to a re-onboard) or first-run state
- [ ] `config/profile.yml` is writeable; if it exists, mode prompts before overwrite

## Steps

### Step 1 — Author `modes/onboarding.md`

Structure the mode as 9 explicit AskUserQuestion blocks, in order. Each block specifies exactly one question, the multiSelect flag, the option list (or "free-text"), and the persistence key.

**Top-level safety gate at the start:**

```
If config/profile.yml exists AND base.py PROFILE['name'] != 'PLACEHOLDER':
  AskUserQuestion: "An existing profile is in place. Re-onboard from scratch?"
    options: ["Yes, replace", "Update specific fields only", "Cancel"]
  If "Cancel" → exit mode cleanly
  If "Update specific fields only" → branch to Step 1.5 (field menu)
  If "Yes, replace" → continue to Step 2
```

**Step 1.5 — Targeted field-update branch.** AskUserQuestion (multiSelect: true): "Which fields do you want to update?" with options [Resume content / Target role(s) / Locations / Company stage / Industries / Comp floor / Pedigree constraint]. Then jump to only those steps below, skipping the rest.

### Step 2 — Resume input (Question 1)

```
AskUserQuestion (single-select):
  question: "How are you sharing your resume?"
  options:
    - "File path on disk"
    - "Public URL (LinkedIn, portfolio)"
    - "Paste text directly"
    - "Free-text describe my background"
```

Branch on the answer:
- File path → free-text follow-up: full path → read file via Read tool
- URL → free-text follow-up: URL → fetch via WebFetch (or scripts/fetch_jd.py for LinkedIn)
- Paste → free-text follow-up: full resume text
- Describe → free-text follow-up: bio paragraph

Persist the raw input to `data/onboarding/raw_resume.txt` (gitignore that subdir).

### Step 3 — Target roles (Question 2)

Parse the raw input from Step 2 to extract candidate role keywords. Build the option list deterministically:
- Always include the 4 current archetypes from `_shared.md` (mid-market-tpm, enterprise-sales-engineer, iot-solutions-architect, revenue-ops-operator)
- Add "Other (describe)" as a free-text escape

```
AskUserQuestion (multiSelect: true):
  question: "Which target archetypes match what you're hunting?"
  options:
    - "Mid-market TPM (Series B–D, B2B SaaS / IoT)"
    - "Enterprise SE / Solutions Architect"
    - "IoT / Wireless Solutions Architect"
    - "RevOps / BizOps Operator"
    - "Other — describe"
```

If "Other" picked, free-text follow-up describes the lane. Mode prints a warning: *"Custom lanes require manual `config/profile.yml` editing post-onboarding."*

### Step 4 — Locations (Question 3)

```
AskUserQuestion (multiSelect: true):
  question: "Where are you open to working?"
  options:
    - "Remote (US)"
    - "Remote (US, Pacific or Mountain TZ only)"
    - "Salt Lake City, UT"
    - "Lehi / Draper, UT"
    - "Open to relocation (specify city in next step)"
```

If "Open to relocation" picked, free-text follow-up captures cities.

### Step 5 — Company stage (Question 4)

```
AskUserQuestion (single-select):
  question: "What company stages fit best?"
  options:
    - "Seed / Series A (early, equity-heavy)"
    - "Series B–D (growth-stage, balanced cash + equity)"
    - "Established / Public (cash-heavy, RSU)"
    - "No preference"
```

### Step 6 — Industry / domain (Question 5)

Build option list from raw resume parsed keywords + a default set:
- Always include: Wireless / Telecom · IoT / Hardware · B2B SaaS · Aerospace / Defense · Industrial · Healthcare tech · Fintech · Other (free-text)

```
AskUserQuestion (multiSelect: true):
  question: "Which industries / domains?"
  options: [list above]
```

### Step 7 — Compensation floor (Question 6)

Free-text capture (no AskUserQuestion — too constrained for $ ranges). Three sub-prompts:
1. "Base salary floor in USD?"
2. "Total comp floor (base + RSU + bonus) in USD?"
3. "Equity expectation (% of company, $ value, or 'standard')?"

Validate: base ≤ total. Re-prompt if not.

### Step 8 — Pedigree constraint (Question 7)

```
AskUserQuestion (single-select):
  question: "How will FAANG / big-tech treat your resume at recruiter screen #1?"
  options:
    - "Strong fit — CS degree + ex-FAANG / FAANG-tier role history"
    - "Borderline — recognized brand experience but no CS degree"
    - "Filtered out — no CS degree, no FAANG tour (Sean's case)"
```

If "Filtered out" selected → write `pedigree_constraint: 'filtered_out'` to profile.yml. This auto-triggers the `out_of_band` quarantine for FAANG-tier companies in the scorer.

This is the question Sean's onboarding flow most consistently skips when improvised. Hard-coding it with AskUserQuestion fixes that.

### Step 9 — Confirm + write

Print a summary of all 8 answers, then:

```
AskUserQuestion (single-select):
  question: "Save this profile?"
  options:
    - "Yes, save"
    - "Edit a specific answer"
    - "Cancel — discard everything"
```

If "Edit", AskUserQuestion (single-select) listing each prior question — jump back to that step, then return here.

If "Yes, save":
1. Write `config/profile.yml` with the captured archetypes, locations, company_stage, industries, comp floors, pedigree_constraint
2. Update `data/resumes/base.py` PROFILE — only the fields onboarding owns (name, email, phone, city, state, linkedin, target_locations, target_archetypes). Do NOT overwrite `positions`, `education`, `skills_grid`, `cert_grid` — those are separate manual edits Sean owns.
3. Print the file diffs (use `git diff` after write)
4. Ask: *"Run a smoke discovery to confirm pipeline produces in-league results? (y/n)"*
   - If yes → run `scripts/discover.py --lane <first archetype> --limit 5` and surface results
5. Mark onboarding complete by writing `data/onboarding/.completed` (timestamp marker; gates the "is this a first run" check)

### Step 10 — Replace SKILL.md prose

In `.claude/skills/coin/SKILL.md`:
- DELETE the existing 9-step prose Onboarding section
- REPLACE with a 5-line pointer:
  ```
  ## Onboarding (first-time users)

  If `data/onboarding/.completed` is missing OR `data/resumes/base.py` PROFILE['name'] is the placeholder string, dispatch to `modes/onboarding.md` immediately. The mode walks 9 AskUserQuestion blocks, then writes `config/profile.yml` + base.py atomic-ish, then runs a smoke discovery. Re-onboarding is supported via `/coin setup` at any time.
  ```
- Add to Mode Routing table:
  ```
  | `setup` or `onboard` or `re-onboard` | `modes/onboarding.md` |
  ```
- Update the First-Run Setup Checklist to call `modes/onboarding.md` between step 5 (init DB) and step 6 (smoke test)

### Step 11 — Add safety guards

The mode must explicitly REFUSE:

| Refusal | Why |
|---|---|
| Overwriting an existing profile.yml without explicit "Yes, replace" | Sean's profile is high-value; accidental overwrite is bad |
| Inferring `pedigree_constraint` automatically from resume content | Self-reported truth — Sean confirms |
| Writing positions / education / skills_grid via this flow | Those are manual-edit fields; onboarding only owns identity + targeting |
| Skipping any of the 9 questions in a fresh onboarding | Determinism is the goal; improvising is the bug we're fixing |
| Auto-running discover at scale (>5 results per lane) before Sean confirms results look right | Avoid filling the DB with garbage on a misconfigured profile |

### Step 12 — Test

Add `tests/test_onboarding_mode.py`:
1. Read `modes/onboarding.md`
2. Assert all 9 questions are present, in order
3. Assert each question specifies multiSelect (true/false) and an option list (or 'free-text')
4. Assert the safety gate at top (existing-profile prompt) is present
5. Assert all 5 Step 11 refusals are documented
6. Assert the file-write step writes BOTH `config/profile.yml` and PROFILE fields, NOT positions/education/skills_grid
7. Assert SKILL.md no longer contains the deleted 9-step prose (regression check via grep)
8. Assert SKILL.md's Mode Routing table contains `setup` or `onboard` → `modes/onboarding.md`

Add `tests/test_skill_md_onboarding_pointer.py`:
1. Read SKILL.md
2. Assert "modes/onboarding.md" appears in the Onboarding section
3. Assert the deleted prose ("Drop a resume file path", "Use AskUserQuestion with options derived from the resume") is gone

### Step 13 — Smoke

Manually run the mode against a non-Sean placeholder PROFILE (use a fixture user). Walk all 9 questions. Confirm:
- Every question fires (no improv)
- Final profile.yml is well-formed (load it, assert keys)
- base.py was updated only in expected fields (diff is bounded)
- Smoke discovery runs and returns ≥1 result OR fails cleanly with a "no roles match this lane yet" message

Restore Sean's real PROFILE after the test (or run in a worktree branch).

## Verification

```bash
cd /Users/tealizard/Documents/lab/coin
.venv/bin/pytest tests/test_onboarding_mode.py tests/test_skill_md_onboarding_pointer.py -v --tb=short

# Confirm SKILL.md was actually trimmed
grep -c "Drop a resume file path" .claude/skills/coin/SKILL.md   # should print 0
grep -c "modes/onboarding.md" .claude/skills/coin/SKILL.md       # should print >= 1
```

- [ ] `modes/onboarding.md` exists with all 9 questions explicit
- [ ] AskUserQuestion blocks specify options + multiSelect flag explicitly
- [ ] SKILL.md prose section deleted; pointer in place
- [ ] All 5 Step 11 refusals are explicit
- [ ] Targeted-field-update branch (1.5) works
- [ ] Save / Edit / Cancel flow at the end works
- [ ] Smoke run on a placeholder PROFILE produces valid profile.yml
- [ ] Tests pass

## Definition of Done

- [ ] `modes/onboarding.md` authored
- [ ] SKILL.md trimmed + routing wired
- [ ] `data/onboarding/` directory exists in .gitignore (raw_resume.txt + .completed)
- [ ] First-Run Setup Checklist updated
- [ ] `docs/state/project-state.md` updated
- [ ] No regressions in existing `pytest tests/`

## Rollback

```bash
rm modes/onboarding.md tests/test_onboarding_mode.py tests/test_skill_md_onboarding_pointer.py
git checkout .claude/skills/coin/SKILL.md docs/state/project-state.md .gitignore
rm -rf data/onboarding/
```

Sean's existing PROFILE is unaffected by rollback (mode never overwrites without explicit confirmation).

## Notes for the executor

- AskUserQuestion is a deferred tool — the mode must instruct the agent to call ToolSearch with `select:AskUserQuestion` at the top of execution to load its schema. Without this, the mode silently can't fire any question.
- The 9-question structure is the proven `job-scout` pattern. Don't add a 10th question — the goal is determinism, not exhaustiveness. Anything beyond identity + targeting belongs in a separate `/coin profile-edit` flow (out of scope).
- The `pedigree_constraint` question (Step 8) is the most important — it's the question whose absence currently produces the most downstream waste (tailored resumes for FAANG roles Sean has 0% chance at). Treat it as load-bearing.
- For "Update specific fields only" branch, walk only the chosen subset of questions and do NOT re-run the smoke discovery (already valid).
- The save step should write to a temp file, validate (yaml.safe_load round-trip + base.py imports cleanly), THEN replace the real file. Atomic-ish.
