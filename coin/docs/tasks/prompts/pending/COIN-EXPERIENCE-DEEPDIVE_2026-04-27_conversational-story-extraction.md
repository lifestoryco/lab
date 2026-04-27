---
task: COIN-EXPERIENCE-DEEPDIVE
title: Conversational story-extraction mode + stories.yml library + tailor/audit integration
phase: Corpus Hardening
size: L
depends_on: COIN-ONBOARDING-EXECUTABLE
created: 2026-04-27
---

# COIN-EXPERIENCE-DEEPDIVE: Walk Sean Role-by-Role and Capture STAR Proof Points

## Context

`data/resumes/base.py::PROFILE` currently holds only ~5 proof points
(Cox True Local Labs, TitanX Series A, Utah Broadband acquisition, ARR
growth $6M→$13M, global engineering orchestration). Sean has 15+ years
of work — the vast majority of his concrete stories are not in the
corpus and therefore can't be lane-matched into resume bullets.

Downstream pain:

- **Tailor** repeats the same 5 stories every time, regardless of JD.
- **Audit Check 5 (metric provenance)** is constrained because there
  are too few metrics to draw from. Many bullets fail attribution
  because the metric isn't in PROFILE — but it isn't in PROFILE
  because we never asked Sean for it.
- New archetypes (RevOps, IoT/Wireless SA) inherit the same shallow
  evidence pool that was built for the original TPM lane.

We need a **deep-dive interview mode** that walks Sean role-by-role,
project-by-project, capturing STAR-format (Situation / Task / Action /
Result) proof points into a structured `data/resumes/stories.yml`
library. After this lands, tailor can rank stories by skill overlap
and grade; audit can trace every metric back to a story id.

## Goal

1. New file `data/resumes/stories.yml` — versioned story library, seeded
   with the existing 5 PROFILE stories migrated to STAR schema.
2. New module `careerops/stories.py` — pure-Python load / add / update /
   query / validate API.
3. New mode `modes/deep-dive.md` — interactive AskUserQuestion-driven
   interview. 30-min session yields 3–5 new stories per position.
4. `modes/tailor.md` — Step 3 (proof-point selection) consults
   stories.yml first, falls back to PROFILE.
5. `modes/audit.md` — Check 5 (metric provenance) traces metrics back
   to story ids; fails on unattributed metrics; warns on PROFILE-only.
6. `.claude/skills/coin/SKILL.md` — route `deep-dive` / `dive` /
   `expand-stories` → `modes/deep-dive.md`; add to Discovery menu.
7. Tests — 29 new tests across 4 files.

## Pre-conditions

- [ ] `data/resumes/base.py` PROFILE dict exists with `positions` list
- [ ] `modes/onboarding.md` exists (use as template for the
      AskUserQuestion-driven mode authoring pattern)
- [ ] `modes/tailor.md` exists (Step 3 will be extended)
- [ ] `modes/audit.md` exists (Check 5 will be extended)
- [ ] `pyyaml` is in `requirements.txt`
- [ ] AskUserQuestion is a deferred tool — confirm via ToolSearch at
      mode entry (mirror `modes/onboarding.md` Step 0)

## Steps

### Step 1 — Create `data/resumes/stories.yml`

Top-level shape:

```yaml
version: 1
stories:
  - id: <kebab-case unique id>
    role: <position id from base.py PROFILE.positions>
    project: <project name or null if role-level>
    dates:
      start: YYYY-MM
      end: YYYY-MM   # or "present"
    lanes_relevant_for:
      - mid-market-tpm
      - enterprise-sales-engineer
      # subset of the 4 archetypes
    situation: <2–4 sentences setup>
    task: <1–2 sentences what was being asked>
    action: <3–5 sentences what Sean specifically did>
    result: <2–3 sentences outcome>
    metrics:
      - value: "1M"
        unit: USD
        description: "Y1 revenue"
        source: "client invoice / Sean's notes"
      - value: "12"
        unit: months
        description: "ahead of schedule"
    team:
      size: 8
      composition: "3 PMs, 2 engineers, 2 designers, 1 ops"
      sean_role: "Lead PM"
    artifact: <link or description of evidence — PR, deck, dashboard URL, contract>
    named_account_ok: true   # can the company name appear in tailored prose?
    related_skills:
      - stakeholder management
      - RF systems
      - B2B SaaS
    grade: A   # A=hero, B=solid, C=situational
    created: 2026-04-27
    last_validated: 2026-04-27
```

**Initial seed:** migrate the existing 5 stories from `data/resumes/base.py`:

| Story id | Role | Notes |
|---|---|---|
| `cox-true-local-labs` | Hydrant engagement | $1M Y1 revenue; 12 months ahead. `sean_role: "Hydrant PM"`; `named_account_ok: true` |
| `titanx-fractional-coo` | Hydrant engagement | $27M Series A in <2 yrs. `sean_role: "Hydrant fractional COO"`; `named_account_ok: true` |
| `utah-broadband-acquisition` | Operator | $27M acquisition by Boston Omaha Corp. `named_account_ok: true` |
| `arr-growth-6m-to-13m` | Enterprise AM | $6M → $13M ARR. `named_account_ok` per the company |
| `global-engineering-orchestration` | Cross-continental delivery | Wireless + aerospace. `named_account_ok` per company |

All 5 seed stories: `grade: A`, `created: 2026-04-27`, `last_validated: 2026-04-27`.
Per the truthfulness gates in CLAUDE.md Rule #7, the Cox / TitanX /
Safeguard outcomes are framed via `sean_role` (e.g. "Hydrant PM") — never
as direct employment.

### Step 2 — Author `careerops/stories.py`

Pure-Python module. No LLM calls. All write paths use
**atomic file rename** (write to `stories.yml.tmp`, fsync, `os.replace`).

Public API:

```python
def load_stories() -> list[dict]:
    """Reads stories.yml, validates schema, returns list of story dicts.
    Raises ValueError on malformed YAML with a clear error message."""

def add_story(story: dict) -> str:
    """Validates, appends, atomic-writes. Returns story id.
    Raises ValueError on duplicate id or schema failure."""

def update_story(id: str, partial: dict) -> bool:
    """Merges partial into existing story (does NOT clobber unspecified
    fields). Atomic write. Returns True on success, False if id missing."""

def find_stories_for_lane(lane: str, min_grade: str = "B") -> list[dict]:
    """Filter by `lane in story['lanes_relevant_for']` and grade >= min_grade.
    Returns list sorted by grade then last_validated desc."""

def find_stories_for_skills(
    skills: list[str], lane: str | None = None
) -> list[dict]:
    """Rank by (skill overlap count) * (grade weight) * (recency factor).
    Grade weights: A=3, B=2, C=1. Recency: 1.0 if last_validated within
    2 years, 0.5 otherwise. Optionally pre-filter by lane."""

def validate_story(story: dict) -> tuple[bool, list[str]]:
    """Checks all required fields present, dates well-formed (YYYY-MM
    or 'present'), lanes_relevant_for ⊆ valid 4 archetypes, grade in
    {A,B,C}, metrics list well-formed. Returns (valid, [error strings])."""

def get_story_by_id(id: str) -> dict | None:
    """Lookup. Returns None on miss."""
```

All functions are pure (no side effects beyond the atomic file writes
in `add_story` / `update_story`).

The valid 4 archetypes for `lanes_relevant_for` validation:
`mid-market-tpm`, `enterprise-sales-engineer`, `iot-solutions-architect`,
`revenue-ops-operator` (per `modes/_shared.md`).

### Step 3 — Author `modes/deep-dive.md`

Mirror `modes/onboarding.md` structure. Mode preamble sets expectations:
*"This is interactive. You drive the cadence; Coin doesn't lecture. A
30-min session typically yields 3–5 new stories from one position. The
downstream payoff is audit Check 5 — every metric in a tailored resume
becomes traceable back to a story id, instead of failing with 'metric
not in PROFILE.'"*

**Step 0 — Load AskUserQuestion**

Mirror `modes/onboarding.md` Step 0 verbatim — call ToolSearch with
`select:AskUserQuestion` to load the deferred tool's schema.

**Step 1 — Snapshot existing stories**

Load `stories.yml`. Print a table:

```
Existing stories: 5
By role:           Hydrant=2, Operator=1, Enterprise AM=1, Cross-continental=1
By lane:           mid-market-tpm=4, revenue-ops-operator=2, iot-sa=1, ent-se=2
By grade:          A=5, B=0, C=0
```

**Step 2 — Ask which position to dive into**

```
AskUserQuestion (single-select):
  question: "Which position do you want to dive into?"
  options:
    - <PROFILE.positions[0].label>
    - <PROFILE.positions[1].label>
    - ... (one option per position in PROFILE)
    - "A project not on the resume"
    - "Skip — wrap up"
```

If "Skip" → jump to Step 9. If "A project not on the resume" → free-text
follow-up captures position context, then continue to Step 3 with that.

**Step 3 — Position-level intro**

```
AskUserQuestion (free-form via "Other"):
  question: "Walk me through your top 3 wins, top 1 fail, and biggest
            lesson from <position>. Take your time — no structure
            imposed yet, just narrative."
  options:
    - "Other (paste narrative)"
```

Capture the raw narrative. Do NOT structure it yet. Print back a parsed
list of wins / fail / lesson for Sean to confirm before probing.

**Step 4 — Probe each win**

For each win mentioned, run a probe loop. The probe questions below are
**SUGGESTIONS for the agent — not rigid scripts**. The agent should
adapt based on what Sean already offered narratively (skip a probe if
he already answered it).

```
For each win:
  AskUserQuestion (free-form): "What was the dollar number on this win?
                                (revenue / cost saved / valuation / ARR)"
  AskUserQuestion (free-form): "Who was on the team and what was your
                                specific role?"
  AskUserQuestion (free-form): "What's the artifact — PR link, deck,
                                dashboard URL, or contract?"
  AskUserQuestion (single-select): "Can the client/company name appear
                                    in your resume?"
    options: ["Yes", "No", "Needs permission first"]
  AskUserQuestion (multiSelect: true): "Which lanes does this story sell?"
    options: [the 4 archetypes]
  AskUserQuestion (single-select): "Grade?"
    options: ["A — hero story", "B — solid", "C — situational"]
```

**Step 5 — Probe the fail**

Same probe loop as Step 4, except replace *"What was the dollar number?"*
with *"What did you learn? What would you do differently?"* The fail
still gets metrics if applicable (e.g. cost of failure, blast radius).

**Step 6 — Validate against existing stories**

For each new story candidate, call
`find_stories_for_skills(candidate.related_skills, lane=candidate.lanes_relevant_for[0])`
and compare against existing stories by skill+date overlap.

If any existing story scores high overlap:

```
AskUserQuestion (single-select):
  question: "This sounds similar to existing story
             '<existing.id>' — '<existing.situation[:60]>'.
             Is this a different facet, an update, or a duplicate?"
  options:
    - "Different facet — add as new story"
    - "Update — merge into existing"
    - "Duplicate — discard new"
```

Branch:
- "Update" → call `update_story(existing.id, candidate)` (merge)
- "Different facet" → continue to Step 7 (add as new)
- "Duplicate" → discard, log skip

**Step 7 — Atomic write**

Assemble each story dict. Run `validate_story(story)` — if errors, surface
them inline and re-prompt for the bad fields only (don't restart the
whole probe loop). On valid, call `add_story(story)`. Print confirmation:

```
✓ Wrote story: <id>
  Role: <role> · Grade: <grade>
  Lanes: <lanes_relevant_for>
  Metrics: <count>
```

**Step 8 — Loop or exit**

```
AskUserQuestion (single-select):
  question: "Dive into another position, or wrap up?"
  options:
    - "Dive into another position"
    - "Wrap up"
```

If "Dive into another" → return to Step 2 (skip Step 1 snapshot reprint).

**Step 9 — Summary**

Print delta:

```
Stories before:  5
Stories after:   12
New by lane:     mid-market-tpm: +3, ent-se: +2, iot-sa: +2
New by grade:    A: +4, B: +3, C: +0
```

Then prompt:

```
Next step: run `/coin tailor <role_id>` for any role. Tailor will now
consult these stories first and rank by skill overlap × grade × recency.

Run audit on a recent tailor output to see Check 5 trace metrics back
to story ids — that's the payoff.
```

### Step 4 — Extend `modes/tailor.md` Step 3

In Step 3 (proof-point selection), insert a new sub-step **before** the
PROFILE base.py fallback:

```
Sub-step 3a — Consult stories.yml first

  from careerops.stories import find_stories_for_skills
  candidates = find_stories_for_skills(jd.required_skills, lane=target_lane)

  Rank order:
    1. Grade A > B > C
    2. named_account_ok=true preferred IF the role/JD allows naming
       (e.g. JD doesn't say "no client name disclosure" and Sean's
       `named_account_ok` for that story is true)
    3. Recent stories (last_validated within 2 years) preferred

  When emitting a bullet derived from a story, embed the story id in
  the bullet's source attribution:

    "<bullet text> [story:<id>]"

  This lets audit Check 5 trace metrics back to the source story.

Sub-step 3b — Fallback to PROFILE base.py

  Only if find_stories_for_skills returns < N candidates needed for
  the target bullet count, fall back to PROFILE proof_points. Bullets
  derived from PROFILE get the attribution "[source:PROFILE]" instead
  of a story id.
```

### Step 5 — Extend `modes/audit.md` Check 5 (metric provenance)

Replace the current Check 5 logic with:

```
Check 5 — Metric provenance (HARDENED)

For each metric appearing in a tailored bullet:
  1. Parse the bullet's source attribution suffix:
       - "[story:<id>]" → story-attributed
       - "[source:PROFILE]" → PROFILE-attributed
       - none → UNATTRIBUTED
  2. If story-attributed:
       - Load story via get_story_by_id(id)
       - Verify the metric value/unit in the bullet matches a metric
         in story.metrics[] EXACTLY (value + unit string)
       - If no match → FAIL with "metric drift: bullet says <X>,
         story says <Y>"
  3. If PROFILE-attributed:
       - PASS with WARNING: "metric source is PROFILE, not stories.yml.
         Consider running /coin deep-dive to capture this story properly."
  4. If UNATTRIBUTED:
       - FAIL with "metric has no source attribution — tailor must
         use stories.yml or explicit PROFILE fallback"

The unattributed-FAIL is the load-bearing change: it forces tailoring
to use stories.yml (or explicit PROFILE fallback) and prevents the
agent from inventing metrics on the fly.
```

### Step 6 — Extend `.claude/skills/coin/SKILL.md`

Add to the Mode Routing table:

```
| `deep-dive` or `dive` or `expand-stories` | `modes/deep-dive.md` |
```

Add to the Discovery menu (wherever `/coin status`, `/coin tailor` etc.
are listed):

```
/coin deep-dive    Walk a position role-by-role and capture STAR proof
                   points to data/resumes/stories.yml. ~30 min per
                   position. Powers tailor + audit Check 5.
```

### Step 7 — Tests

Write 4 test files, 29 tests total.

**`tests/test_stories.py` (15 tests)**

1. `load_stories` on empty file → returns `[]`
2. `load_stories` on populated file → returns list of dicts
3. `load_stories` on malformed YAML → raises ValueError with clear msg
4. `add_story` writes new id correctly
5. `add_story` atomic file rename works (no half-written file on simulated crash)
6. `add_story` rejects duplicate id with ValueError
7. `update_story` merges partial dict
8. `update_story` doesn't clobber unspecified fields
9. `validate_story` accepts a fully-valid story
10. `validate_story` rejects missing required field with specific error
11. `validate_story` rejects malformed dates (e.g. "2026-13" or "April 2026")
12. `validate_story` rejects invalid lane in `lanes_relevant_for`
13. `validate_story` rejects grade outside {A,B,C}
14. `find_stories_for_lane` filters correctly + respects min_grade
15. `find_stories_for_skills` ranks by skill overlap × grade × recency
    (assert order on a fixture with 3 stories of varying overlap/grade/age)

Bonus assertions inside the suite (not separately numbered):
- `get_story_by_id` hit + miss
- Schema migration: assert all 5 seeded stories from base.py exist in
  stories.yml after fixture load (id, role, named_account_ok)

**`tests/test_deep_dive_mode.py` (8 tests)**

1. `modes/deep-dive.md` file exists
2. Mode mentions Step 0 AskUserQuestion ToolSearch load
3. Mode mentions stories.yml + add_story
4. Mode mentions probe loop questions (dollar number, team, artifact, lanes, grade)
5. Mode mentions validation against existing stories (find_stories_for_skills + duplicate prompt)
6. Mode mentions named_account_ok handling (Yes/No/Needs permission)
7. Mode mentions atomic write pattern
8. SKILL.md routing entry exists for `deep-dive`

**`tests/test_tailor_mode_uses_stories.py` (3 tests)**

1. `modes/tailor.md` mentions `find_stories_for_skills`
2. `modes/tailor.md` mentions story id attribution syntax `[story:<id>]`
3. `modes/tailor.md` mentions A > B > C grade preference

**`tests/test_audit_check5_uses_stories.py` (3 tests)**

1. `modes/audit.md` Check 5 mentions story id traceability
2. `modes/audit.md` Check 5 fails on unattributed metrics
3. `modes/audit.md` Check 5 warns on PROFILE-only attribution

### Step 8 — Verification

```bash
cd /Users/tealizard/Documents/lab/coin
.venv/bin/pytest tests/ -q --tb=short
# Expected: 228 + Sprint 1-2 deltas + 29 new = 320+ tests passing

cat data/resumes/stories.yml | head -40
# Expected: valid YAML, version: 1, 5 seeded stories

.venv/bin/python -c "from careerops.stories import find_stories_for_lane; \
  print(find_stories_for_lane('mid-market-tpm', min_grade='A'))"
# Expected: at least 2 stories returned

.venv/bin/python -c "from careerops.stories import validate_story, load_stories; \
  [print(validate_story(s)) for s in load_stories()]"
# Expected: all (True, []) for seeded stories
```

Manual (not blocking):
- Run `/coin deep-dive` interactively
- Walk through one position, dive into one win
- Verify the new story lands in stories.yml with all required fields

## Style notes (the mode is interactive)

- The mode is **INTERACTIVE** — it relies on AskUserQuestion for each
  probe. Sean drives the cadence; Coin does NOT lecture.
- The probe questions are **SUGGESTIONS** for the executing agent —
  not rigid scripts. If Sean already offered the dollar figure in his
  Step 3 narrative, skip the dollar-figure probe in Step 4.
- A 30-min session typically yields 3–5 new stories from one position.
  Set this expectation in the mode preamble so Sean budgets time.
- Reference the audit Check 5 hardening as the downstream payoff —
  Sean understands why this matters because audit currently fails on
  too many "metric not in PROFILE" cases.
- Truthfulness gates from CLAUDE.md Rule #7 still apply: never frame
  Hydrant client outcomes as direct employment. Use the `sean_role`
  field on each story to keep that explicit.

## Definition of Done

- [ ] `data/resumes/stories.yml` exists with 5 seeded stories, valid YAML
- [ ] `careerops/stories.py` exists with all 7 public functions, atomic writes
- [ ] `modes/deep-dive.md` exists, all 9 steps explicit, AskUserQuestion-driven
- [ ] `modes/tailor.md` Step 3 extended (stories.yml first, PROFILE fallback)
- [ ] `modes/audit.md` Check 5 extended (story id traceability, unattributed FAIL)
- [ ] `.claude/skills/coin/SKILL.md` routing + Discovery menu updated
- [ ] All 29 new tests pass; full suite is green (320+ total)
- [ ] `data/onboarding/` style — no new gitignore entries needed
      (stories.yml IS committed; it's the corpus, not generated output)
- [ ] `docs/state/project-state.md` updated to reflect new mode + corpus

## Rollback

```bash
rm data/resumes/stories.yml
rm careerops/stories.py
rm modes/deep-dive.md
rm tests/test_stories.py tests/test_deep_dive_mode.py \
   tests/test_tailor_mode_uses_stories.py tests/test_audit_check5_uses_stories.py
git checkout modes/tailor.md modes/audit.md \
   .claude/skills/coin/SKILL.md docs/state/project-state.md
```

PROFILE in `data/resumes/base.py` is unchanged by this task — rollback
restores the pre-stories.yml world cleanly.

## Notes for the executor

- AskUserQuestion is a deferred tool — the mode MUST instruct the
  agent to call ToolSearch with `select:AskUserQuestion` at the top of
  execution to load its schema. Without this, the mode silently can't
  fire any question. Mirror `modes/onboarding.md` Step 0 verbatim.
- The 4 archetypes are canonical (per `modes/_shared.md` and CLAUDE.md):
  `mid-market-tpm`, `enterprise-sales-engineer`, `iot-solutions-architect`,
  `revenue-ops-operator`. Hard-code these in `validate_story`'s
  lane-allowlist — do NOT read them dynamically (we want the validator
  to fail loudly if a future archetype refactor forgets to update it).
- Atomic writes: `tempfile.NamedTemporaryFile` in same dir → fsync →
  `os.replace`. Same pattern as `careerops/pipeline.py`'s SQLite-adjacent
  writes. Do NOT use a lockfile — single-user app.
- `find_stories_for_skills` recency: use `datetime.date.today()` minus
  `last_validated` parsed as YYYY-MM-DD. < 730 days → recent (1.0);
  else → stale (0.5). Don't bake the cutoff date into a constant; use
  `datetime.date.today()` so the test fixture can monkeypatch it.
- Story id collision: `add_story` rejects duplicates. The deep-dive
  mode (Step 6) handles the human-meaningful "this is similar"
  prompt BEFORE calling add_story — so Step 7 should never hit a
  duplicate-id error in practice, but the API still defends against it.
- The existing 5 PROFILE stories migrate verbatim into stories.yml.
  After this task, PROFILE keeps the proof_points list as a
  fallback-source-of-truth marker, but the canonical story corpus is
  stories.yml. A future task may delete PROFILE.proof_points; not in
  scope here.
- The 30-min / 3–5 stories cadence is empirical from Sean's prior
  story-extraction sessions. Don't try to extract more per session —
  fatigue degrades story quality, and Step 8's loop-or-exit prompt is
  there exactly to let Sean cap the session voluntarily.
- Audit Check 5's unattributed-FAIL is the load-bearing rule. Without
  it, tailor will keep emitting bullets with metrics from thin air
  and audit will rubber-stamp them. The FAIL is the forcing function
  that pulls Sean back to deep-dive when stories.yml is shallow.
