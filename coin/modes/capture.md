# Coin Mode — `capture` (STAR-format experience capture)

> Load `modes/_shared.md` first.

**Purpose:** Walk Sean through a STAR-format capture session that
extracts career proof points beyond what's already in `data/resumes/base.py`.
Each pass produces ONE accomplishment row + 0..N outcome rows + 0..N
evidence rows + skill tags + per-lane relevance scores.

This is how the **experience database** gets richer than what base.py
seeded. Use it for:
- Side projects, board work, advisory roles, fractional gigs
- Older positions Sean wants surfaced for specific lanes
- New stories that came up in interviews and should be canonized
- Anything you want available for future tailoring + interview prep

The same `accomplishment` rows feed `modes/tailor.md`,
`modes/cover-letter.md`, `modes/interview-prep.md`, and the structural
truthfulness gate.

---

## Hard refusals

| Refusal | Why |
|---|---|
| Inventing metrics not provided by Sean | Truthfulness is structural — every metric must trace to an outcome row Sean confirmed |
| Skipping the seniority-ceiling question | Title-ladder coherence is a load-bearing anti-hallucination signal |
| Auto-tagging skills not in Lightcast subset | Skill IDs MUST come from the candidate list emitted by `careerops.skill_tagger` |
| Writing accomplishment rows without `evidence` rows | Self_reported is the seed default; the schema requires at least one evidence row per outcome |
| Refusing to ask all 7 STAR questions in a fresh capture | Determinism — improvising drops fields that the linter relies on |

---

## Step 0 — Load AskUserQuestion

```
ToolSearch(query="select:AskUserQuestion", max_results=1)
```

---

## Step 1 — Run migrations + load skills

Before any capture, make sure the schema and Lightcast skills are loaded:

```bash
.venv/bin/python scripts/migrations/m005_experience_db.py
.venv/bin/python scripts/migrations/m006_seed_lightcast.py
```

Both are idempotent.

---

## Step 2 — Story seed (AskUserQuestion)

```
question: "What story do you want to capture?"
header: "Story"
multiSelect: false
options:
  - label: "A specific accomplishment I haven't written down yet"
    description: "Free-form story — I'll walk you through STAR + metrics"
  - label: "Cox / TitanX / Safeguard / Utah Broadband / LINX side angle"
    description: "Existing position — capture an angle base.py doesn't surface"
  - label: "Side project / board / advisory / fractional gig"
    description: "Outside of W2 history; new position_slug"
  - label: "I'll paste a draft and you extract STAR + outcomes"
    description: "Quick-path: I'll structure it from your prose"
```

Branching: A free-form path goes through Steps 3-9. The "paste a draft"
option offers a single textarea-style prompt; we still produce STAR fields.

---

## Step 3 — Position attribution

```
question: "Which position does this come from?"
header: "Position"
multiSelect: false
options:
  - label: "ca_engineering (CA Engineering, Jan 2025–Present)"
  - label: "hydrant (Hydrant, Jul 2019–Dec 2024)"
  - label: "utah_broadband (Utah Broadband, Apr 2013–Jul 2019)"
  - label: "linx (LINX Communications, Jan 2011–Apr 2013)"
  - label: "Other / new position_slug"
```

If "Other": follow up free-form for new slug + dates.

---

## Step 4 — STAR extraction

Ask 4 sequential AskUserQuestion blocks (or one combined free-form prompt
that the agent decomposes):

1. **Situation** — what was the context? 1-2 sentences.
2. **Task** — what did you specifically own? 1 sentence.
3. **Action** — what did you DO? 2-4 sentences with action verbs.
4. **Result** — what was the outcome? 1-2 sentences.

Persist into `accomplishment.situation/task/action/result`.

---

## Step 5 — Outcomes (quantified metrics)

Ask: "What metrics quantify the result? List each as a number+unit."

For each metric Sean provides, ask:
- `metric_name` (one word/phrase, e.g. "ARR growth", "P&L impact",
  "First call resolution")
- `value_text` (display form, e.g. "$1M", "40%", "187 countries")
- `value_numeric` (parsed; agent computes via the linter's normalizer)
- `unit` (USD | pct | x | months | years | <count-unit>)
- `direction` (increase | decrease | absolute | reduction)
- `asof_date` (free-form, e.g. "Jul 2020")

Write each as one `outcome` row.

**Refusal:** If Sean offers a vague claim ("significantly increased revenue"), refuse
to write an outcome row. Ask for the exact number or skip the metric entirely.

---

## Step 6 — Evidence per outcome

For each outcome, prompt Sean to attach evidence:

```
question: "How do you back up '<metric_name>: <value_text>'?"
header: "Evidence"
multiSelect: false
options:
  - label: "URL (press release, dashboard screenshot, public deck)"
    description: "Best — public source; Sean provides URL"
  - label: "Manager quote or testimonial"
    description: "Manager_quoted; capture quote in notes"
  - label: "System export I can attach later"
    description: "system_exported; URL_or_path = TODO"
  - label: "Self-reported (I'll add proof later)"
    description: "Default seed; Sean upgrades via /coin add-evidence"
```

Write one `evidence` row per outcome. Source enum: `public | manager_quoted | system_exported | self_reported`.

---

## Step 7 — Seniority ceiling

```
question: "What scope did you genuinely own here?"
header: "Seniority"
multiSelect: false
options:
  - label: "Sole leader (founder / fractional COO / co-owner)"
    description: "seniority_ceiling = 'fractional_coo' or 'co_owner' or 'sole_lead'"
  - label: "Program lead (owned the program; multiple ICs reported in)"
    description: "seniority_ceiling = 'program_lead'"
  - label: "Senior IC / team-shaping IC"
    description: "seniority_ceiling = 'senior_ic'"
  - label: "Team member / individual contributor"
    description: "seniority_ceiling = 'team_member'"
```

The truth gate uses this to prevent the resume from claiming scope above
this level (Eightfold-style title-ladder check).

---

## Step 8 — Skill tagging via Claude (structured output)

For every accomplishment, run `careerops.skill_tagger.deterministic_skill_match`
against the action+result text. If <3 hits, build a Claude prompt via
`careerops.skill_tagger.build_skill_tag_prompt` and have Claude (this
session) emit JSON conforming to `SKILL_TAG_SCHEMA`.

Validate the response via `validate_skill_tag_response(response, valid_slugs=...)`.
Then call `experience.tag_skill(...)` for each accepted suggestion.

**Hard refusal:** never tag a skill_slug that wasn't in the candidate list.

---

## Step 9 — Lane relevance

```
question: "Which lanes does this accomplishment most directly support?"
header: "Lanes"
multiSelect: true
options:
  - label: "mid-market-tpm"
  - label: "enterprise-sales-engineer"
  - label: "iot-solutions-architect"
  - label: "revenue-ops-operator"
```

For each selected lane, set relevance_score=85 (manual_pin=true).
For unselected lanes, set relevance_score=30 (manual_pin=false).

Use `experience.set_lane_relevance(...)`.

---

## Step 10 — Persist + confirm

Run a final summary print of what was written:

```
✅ Captured accomplishment #<id>:
   position_slug: <slug>
   title: <first-60-chars>
   STAR: ✓ (situation/task/action/result)
   outcomes: <n>
   evidence: <n>  (sources: <histogram>)
   skills tagged: <n>
   lanes pinned: <slugs>
```

Ask Sean if he wants to capture another. If yes, loop to Step 2.

---

## Required structural tests

`tests/test_capture_mode.py` asserts:
- All 10 step headers are present
- The 5 hard refusals are present
- AskUserQuestion is loaded in Step 0
- The skill tagging step requires structured-output validation
- Lane relevance step is multiSelect=true
- Outcome step refuses vague claims
