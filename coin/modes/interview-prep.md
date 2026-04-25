# Mode: interview-prep

Generate a focused interview prep brief for an upcoming interview. Pulls the role's JD, Sean's tailored resume, and structured guidance for the most likely interview formats.

## Input

- `--id <role_id>` (required) — must be in status `interview` (or moving toward it)
- `--round <name>` (optional) — recruiter | hiring-manager | technical | panel | final
- `--interviewer <name>` (optional) — researches the specific person via WebSearch / LinkedIn

## Step 1 — Validate

- Role exists and status is `interview` (or `applied` with a confirmed scheduled interview — Sean tells you)
- Tailored JSON exists at `data/resumes/generated/<id:04d>_*.json` (the bullets you committed to in the application)
- JD parsed (if not, route to `score` first to extract required_skills / red_flags)

## Step 2 — Read the inputs

1. Role record + JD (`scripts/print_role.py --id <id>`)
2. Tailored JSON (the resume + cover hook you submitted — these define what you committed to)
3. PROFILE positions (your real proof points)
4. Lane's `north_star` from `config/profile.yml`
5. (If `--interviewer` provided) WebSearch the person's LinkedIn + recent posts for tone, areas of focus, recent talks/articles

## Step 3 — Build the prep brief

Output a single-screen brief with these sections:

```
═══════════════════════════════════════════════════════════════
  INTERVIEW PREP — Role <id>
  <company> — <title>  ·  Round: <recruiter|hm|technical|panel|final>
  <interviewer name + title if provided>
═══════════════════════════════════════════════════════════════

YOUR POSITIONING (north star + the 3 bullets you submitted)
  · <executive_summary's first sentence>
  · <top_bullets[0]>
  · <top_bullets[1]>
  · <top_bullets[2]>

LIKELY QUESTIONS (3-5, ranked by probability, each with a 1-paragraph
recommended answer drawing from PROFILE positions):

  Q1 (90% probability): "Walk me through your background."
     Answer hook: 3-sentence chronological narrative ending with
     "...which is what brought me to <company>'s <role>." Use
     PROFILE.positions in order: LINX → Utah Broadband → Hydrant →
     CA Engineering. Hit one metric per stop.

  Q2: "Tell me about a time you <skill JD asks for>."
     Answer hook: <STAR structure pulled from the matching PROFILE
     position>. Say the company by name, the metric, the outcome.

  Q3: <questions specific to lane>
     ...

GAPS THEY'LL PROBE (from your skills_gap)
  · <gap 1>: prep a "I haven't done X directly but I have done Y, which
            is the same muscle" framing
  · <gap 2>: ...

QUESTIONS YOU SHOULD ASK (3-5, lane-specific):
  · For SE: "What's the most common technical objection you hear from
            mid-market vs enterprise prospects, and how do SEs handle
            the difference?"
  · For TPM: "What's the longest-running program coordination problem
             that's still open, and what's blocked it?"
  · ...

RED FLAGS TO LISTEN FOR (from JD parse + cluster patterns):
  · <red_flag 1 if any>
  · "Wear many hats" → likely understaffed
  · "Move fast and break things" → may conflict with your delivery DNA
  · ...

LOGISTICS REMINDERS
  · If recruiter screen: keep it under 25 min, ask about process + comp band
  · If technical: ask up front whether it's whiteboard, system design, or
    case study, so you frame your answers right
  · If panel: have 1 strong question per interviewer
```

## Step 4 — Round-specific augmentation

If `--round recruiter`:
- Add a "Recruiter screen quick answers" section: years experience, current comp ($99K — note Sean is intentionally underpaid; frame as "looking to step into market range"), location (Salt Lake City; remote OK), authorization to work (yes, US citizen — Sean answers personally).

If `--round technical`:
- For SE/SA roles: drill 1 reference architecture from the lane's domain (e.g., for IoT-SA: AWS IoT Core architecture with Greengrass edge)
- For TPM roles: drill 1 program-management scenario ("a critical vendor slipped, what do you do") and prep STAR-formatted answers

If `--round hiring-manager`:
- Focus on the cover letter hook — that's likely what got the meeting
- Prep answer to "what attracted you to this role" using the hook's framing

If `--round final` or `--round panel`:
- Prep 1 anecdote per likely interviewer's function (eng, product, sales, ops)
- Prep "what's your decision timeline" question

## Step 5 — Save the brief

Write to `data/interview-prep/<id:04d>_<role_short>_<round>_<date>.md`. Sean opens it on his phone before the call.

## Hard rules

- Never coach Sean to lie. The brief draws ONLY from PROFILE positions and the JSON he already committed to in the application.
- Never claim a metric in the brief that isn't in PROFILE — if you reference an outcome, it must be from `PROFILE.positions[*].bullets`.
- Never coach overclaiming on `skills_gap` items. The gap-bridging framing is "haven't done X directly but Y is the same muscle" — not "I have done X".
- Don't pre-answer compensation questions. Recommend Sean defer to "I'm interested in your range; what's the band for this role?" until later in the process.

## Notes

- This mode does NOT trigger an `applied` or `interview` transition. Use `/coin track <id> interview` separately to record the actual scheduled call.
- If the company is a known weak-fit (cluster from `/coin patterns`), surface that warning at the top: "Note: your last 3 applications to <company-tier> got silent rejects — consider recalibrating expectations on this round."
- Reference: santifer/career-ops `modes/interview-prep.md` for the structure.
