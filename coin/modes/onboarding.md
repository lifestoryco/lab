# Coin Mode — `onboarding` (executable first-run profile setup)

> Load `modes/_shared.md` first.

**Purpose:** Walk a first-time user (or a re-onboarding Sean) through 7
deterministic AskUserQuestion blocks (Steps 2–8) and a final save-confirm
block (Step 9), then atomically write `config/profile.yml` and the identity
slice of `data/resumes/base.py`.

This replaces the prose Onboarding section that used to live in
`SKILL.md`. The agent no longer improvises which questions to ask —
this mode is the runtime.

> **Path constants** (from `config.py`): `ONBOARDING_DIR`,
> `ONBOARDING_MARKER`, `ONBOARDING_RAW_RESUME`. Reference these by import
> rather than hardcoding paths inside Python one-liners.

---

## Hard refusals (read first)

| Refusal | Why |
|---|---|
| Overwriting an existing `config/profile.yml` without explicit "Yes, replace" | Sean's profile is high-value; accidental overwrite is bad |
| Inferring `pedigree_constraint` automatically from resume content | Self-reported truth — Sean confirms |
| Writing `positions` / `education` / `skills_grid` via this flow | Manual-edit fields; onboarding only owns identity + targeting |
| Skipping any of the 9 questions in a fresh onboarding | Determinism is the goal; improvising is the bug we're fixing |
| Auto-running discover at scale (>5 results per lane) before Sean confirms results look right | Avoid filling DB with garbage on a misconfigured profile |

---

## Step 0 — Load the AskUserQuestion tool

`AskUserQuestion` is a deferred tool. At mode entry, run:

```
ToolSearch(query="select:AskUserQuestion", max_results=1)
```

Without this, none of the questions can fire.

---

## Step 1 — Existing-profile safety gate

Check current state:

```bash
.venv/bin/python -c "
from data.resumes.base import PROFILE
import os, pathlib
yml_exists = pathlib.Path('config/profile.yml').exists()
placeholder = PROFILE.get('name', '').upper().startswith('PLACEHOLDER')
print('yml_exists:', yml_exists, '/ placeholder:', placeholder)
"
```

Decision matrix:

- **placeholder = True OR yml_exists = False** → fresh onboarding (skip to Step 2)
- **Both populated** → AskUserQuestion (single-select):
  ```
  question: "An existing profile is in place. Re-onboard from scratch?"
  options: ["Yes, replace", "Update specific fields only", "Cancel"]
  ```
  - Cancel → exit mode cleanly
  - Update specific fields only → branch to **Step 1.5**
  - Yes, replace → continue to Step 2

### Step 1.5 — Targeted field-update branch

AskUserQuestion (multiSelect: true):
```
question: "Which fields do you want to update?"
options:
  - "Resume content"
  - "Target role(s)"
  - "Locations"
  - "Company stage"
  - "Industries"
  - "Comp floor"
  - "Pedigree constraint"
```

Walk only the chosen subset of questions below. Skip the smoke discovery
in Step 9 (existing pipeline already valid).

---

## Step 2 — Resume input (Question 1)

AskUserQuestion (single-select):
```
question: "How are you sharing your resume?"
options:
  - "File path on disk"
  - "Public URL (LinkedIn, portfolio)"
  - "Paste text directly"
  - "Free-text describe my background"
```

Branch on the answer:
- **File path** → free-text follow-up: full path → Read tool
- **URL** → free-text follow-up: URL → WebFetch (or `scripts/fetch_jd.py` for LinkedIn)
- **Paste** → free-text follow-up: full resume text
- **Describe** → free-text follow-up: bio paragraph

Persist the raw input to `config.ONBOARDING_RAW_RESUME`
(`data/onboarding/raw_resume.txt`; gitignored). Prefer creating it via
`tempfile.mkstemp(prefix='coin_resume_', dir=config.ONBOARDING_DIR)` and
unlinking after Step 9 saves successfully — keeps unencrypted PII off disk
once the structured profile is written.

---

## Step 3 — Target roles (Question 2)

Parse the raw input from Step 2 to extract candidate role keywords.
Build the option list deterministically from `_shared.md`'s 4 archetypes.

AskUserQuestion (multiSelect: true):
```
question: "Which target archetypes match what you're hunting?"
options:
  - "Mid-market TPM (Series B–D, B2B SaaS / IoT)"
  - "Enterprise SE / Solutions Architect"
  - "IoT / Wireless Solutions Architect"
  - "RevOps / BizOps Operator"
  - "Other — describe"
```

If "Other" picked, free-text follow-up captures the lane description.
Print warning: *"Custom lanes require manual `config/profile.yml` editing
post-onboarding."*

---

## Step 4 — Locations (Question 3)

AskUserQuestion (multiSelect: true):
```
question: "Where are you open to working?"
options:
  - "Remote (US)"
  - "Remote (US, Pacific or Mountain TZ only)"
  - "Salt Lake City, UT"
  - "Lehi / Draper, UT"
  - "Open to relocation (specify city in next step)"
```

If "Open to relocation" picked, free-text follow-up captures cities.

---

## Step 5 — Company stage (Question 4)

AskUserQuestion (single-select):
```
question: "What company stages fit best?"
options:
  - "Seed / Series A (early, equity-heavy)"
  - "Series B–D (growth-stage, balanced cash + equity)"
  - "Established / Public (cash-heavy, RSU)"
  - "No preference"
```

---

## Step 6 — Industry / domain (Question 5)

Build option list from raw resume parsed keywords + the default set:

AskUserQuestion (multiSelect: true):
```
question: "Which industries / domains?"
options:
  - "Wireless / Telecom"
  - "IoT / Hardware"
  - "B2B SaaS"
  - "Aerospace / Defense"
  - "Industrial"
  - "Healthcare tech"
  - "Fintech"
  - "Other — describe"
```

---

## Step 7 — Compensation floor (Question 6)

Free-text capture (no AskUserQuestion — too constrained for $ ranges).
Three sub-prompts:

1. *"Base salary floor in USD? (Sean default: $130K — press Enter to accept, or type new value)"*
2. *"Total comp floor (base + RSU + bonus) in USD? (Sean default: $160K)"*
3. *"Equity expectation (% of company, $ value, or 'standard')?"*

Validate: base ≤ total. Re-prompt if not. If Sean enters a base below
$130K or total below $160K, surface a soft warning citing `_shared.md`'s
Operating Principle: comp floor exists because Sean is at $99K and
$130K/$160K is the realistic floor (top of range $230K total); lowering it
is allowed but should be a deliberate choice, not a fat-finger.

---

## Step 8 — Pedigree constraint (Question 7) — **load-bearing**

This is the question whose absence currently produces the most downstream
waste (tailored resumes for FAANG roles the user has 0% chance at). Hard-code
it; do NOT infer from resume content.

AskUserQuestion (single-select):
```
question: "How will FAANG / big-tech treat your resume at recruiter screen #1?"
options:
  - "Strong fit — CS degree + ex-FAANG / FAANG-tier role history"
  - "Borderline — recognized brand experience but no CS degree"
  - "Filtered out — no CS degree, no FAANG tour (Sean's case)"
```

If "Filtered out" → write `pedigree_constraint: 'filtered_out'` to
`profile.yml`. The scorer auto-quarantines `tier4_pedigree_filter` companies
to `out_of_band` for users with this flag.

---

## Step 9 — Confirm + write

Print a summary of all 7 captured answers, then:

AskUserQuestion (single-select):
```
question: "Save this profile?"
options:
  - "Yes, save"
  - "Edit a specific answer"
  - "Cancel — discard everything"
```

If **Edit**: AskUserQuestion (single-select) listing each prior question;
jump back to that step, then return here.

If **Yes, save** — atomic write protocol:

1. Stage to temp file `<config.ONBOARDING_DIR>/profile.staging.yml`
2. Validate via `yaml.safe_load` round-trip
3. Atomically replace `config/profile.yml`
4. Update `data/resumes/base.py` PROFILE — only the identity slice:
   `name`, `email`, `phone`, `city`, `state`, `linkedin`, `target_locations`,
   `target_archetypes`. Do **NOT** overwrite `positions`, `education`,
   `skills_grid`, `cert_grid` — those are separate manual edits.
5. Re-import `data.resumes.base` to confirm it still imports cleanly
6. Print the file diffs (`git diff config/profile.yml data/resumes/base.py`)
7. Delete the raw-resume tempfile from Step 2 (PII no longer needed)
8. AskUserQuestion (single-select):
   ```
   question: "Run a smoke discovery to confirm pipeline produces in-league results?"
   options: ["Yes, run smoke", "Skip"]
   ```
   - If yes → run `.venv/bin/python scripts/discover.py --lane <first archetype> --limit 5` and surface results
9. Mark onboarding complete: `touch <config.ONBOARDING_MARKER>`
   (file existence is the gate for "is this a first run" check)

If **Cancel**: discard everything, leave files untouched, exit.

---

## Reference

| File | Purpose |
|---|---|
| `config/profile.yml` | Written by Step 9 — archetypes, locations, comp floors, pedigree |
| `data/resumes/base.py` PROFILE | Identity slice only; positions/education are manual |
| `data/onboarding/raw_resume.txt` | User's raw resume input (gitignored) |
| `data/onboarding/.completed` | First-run gate marker |
| `_shared.md` | 4-archetype source of truth (drives Step 3 options) |
