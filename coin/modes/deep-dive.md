# Coin Mode — `deep-dive` (interactive STAR proof-point capture)

> Load `modes/_shared.md` first.

**Purpose:** Walk Sean role-by-role and capture STAR-format proof points
into `data/resumes/stories.yml`. A 30-min session typically yields 3–5
new stories from a single position. Powers `modes/tailor.md` Step 3 and
`modes/audit.md` Check 5 (metric provenance).

**Why this mode exists:** `data/resumes/base.py` PROFILE has only ~5
proof points. Tailor repeats them every time. Audit Check 5 fails on
"metric not in PROFILE" cases too often. This mode is the forcing
function that grows the corpus.

**Style:** INTERACTIVE. Sean drives the cadence. Coin does NOT lecture.
Probe questions below are SUGGESTIONS — skip a probe if Sean already
answered it in his Step 3 narrative. Truthfulness gates from CLAUDE.md
Rule #7 still apply: never frame Hydrant client outcomes as direct
employment. Use the `sean_role` field to make framing explicit.

---

## Step 0 — Load AskUserQuestion

`AskUserQuestion` is a deferred tool. At mode entry, run:

```
ToolSearch(query="select:AskUserQuestion", max_results=1)
```

Without this, none of the questions can fire.

---

## Step 1 — Snapshot existing stories

```python
from careerops.stories import load_stories
stories = load_stories()
```

Print a compact table:

```
Existing stories: <count>
By role:           <role_id>=<n>, ...
By lane:           mid-market-tpm=<n>, enterprise-sales-engineer=<n>,
                   iot-solutions-architect=<n>, revenue-ops-operator=<n>
By grade:          A=<n>, B=<n>, C=<n>
```

This sets context — Sean knows what's already covered before diving in.

---

## Step 2 — Ask which position to dive into

```
AskUserQuestion (single-select):
  question: "Which position do you want to dive into?"
  options:
    - <PROFILE.positions[0].label>
    - <PROFILE.positions[1].label>
    - ... one option per position in PROFILE
    - "A project not on the resume"
    - "Skip — wrap up"
```

Branch:
- `Skip` → jump to Step 9.
- `A project not on the resume` → free-text follow-up captures
  position context, then continue to Step 3 with that.
- Otherwise → continue to Step 3 with that position.

---

## Step 3 — Position-level intro

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

---

## Step 4 — Probe each win

For each win mentioned, run a probe loop. The questions below are
SUGGESTIONS. Skip any that Sean already answered in his Step 3
narrative.

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
    options: ["mid-market-tpm", "enterprise-sales-engineer",
              "iot-solutions-architect", "revenue-ops-operator"]
  AskUserQuestion (single-select): "Grade?"
    options: ["A — hero story", "B — solid", "C — situational"]
```

---

## Step 5 — Probe the fail

Same probe loop as Step 4, except replace the dollar-figure question
with:

```
"What did you learn? What would you do differently?"
```

The fail still gets metrics if applicable (cost of failure, blast
radius, recovery time).

---

## Step 6 — Validate against existing stories

For each new story candidate:

```python
from careerops.stories import find_stories_for_skills
existing = find_stories_for_skills(
    candidate["related_skills"],
    lane=candidate["lanes_relevant_for"][0],
)
```

If any existing story scores high overlap (≥ 3 shared skills, same
role, overlapping date range):

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
- `Update` → call `update_story(existing.id, candidate)` (merge)
- `Different facet` → continue to Step 7 (add as new)
- `Duplicate` → discard, log skip

---

## Step 7 — Atomic write

Assemble each story dict. Run `validate_story(story)` first. If the
validator returns errors, surface them inline and re-prompt for the
bad fields ONLY (don't restart the whole probe loop).

On valid:

```python
from careerops.stories import add_story
story_id = add_story(story)
```

`add_story` uses the atomic write pattern internally (tempfile in same
dir → fsync → os.replace). Print confirmation:

```
✓ Wrote story: <id>
  Role: <role> · Grade: <grade>
  Lanes: <lanes_relevant_for>
  Metrics: <count>
```

---

## Step 8 — Loop or exit

```
AskUserQuestion (single-select):
  question: "Dive into another position, or wrap up?"
  options:
    - "Dive into another position"
    - "Wrap up"
```

If `Dive into another` → return to Step 2 (skip Step 1 reprint).

---

## Step 9 — Summary

Print delta:

```
Stories before:  <n>
Stories after:   <n>
New by lane:     mid-market-tpm: +<n>, enterprise-sales-engineer: +<n>, ...
New by grade:    A: +<n>, B: +<n>, C: +<n>
```

Then prompt:

```
Next step: run `/coin tailor <role_id>` for any role. Tailor will now
consult these stories first and rank by skill overlap × grade × recency.

Run audit on a recent tailor output to see Check 5 trace metrics back
to story ids — that's the payoff.
```

---

## Hard refusals

| Refusal | Why |
|---|---|
| Auto-generating story content from base.py without Sean's narrative | The whole point of this mode is to capture stories Sean hasn't volunteered yet |
| Skipping the named_account_ok question | Truthfulness gate — Hydrant client outcomes need explicit framing |
| Writing a story that fails `validate_story` | Schema is the contract with audit Check 5 |
| Inventing metrics that Sean didn't supply | If Sean doesn't have a number, leave the metric off; never fabricate |
