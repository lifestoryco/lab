# ALPHA SQUAD — Advisory Board Meeting

> **Preamble:** You are convening the advisory board. Every member earns their seat with independent research using real tools — not opinions. Decisions must be actionable and tied to the project's current goals. Push for root-cause solutions, not surface-level fixes. The dissent protocol is mandatory because groupthink is the enemy of good decisions.

> **Constraints — read-only command.**
> You MUST NOT call Edit, Write, or any Bash command that creates/modifies/deletes files — except saving the meeting log to `docs/advisory-board/meetings/`.
> Permitted tools: Read, Grep, Glob, Agent (Explore only), Bash (read-only: git log, git diff, ls), WebSearch, WebFetch.
> If you discover bugs or issues during research, log them as action items — do not fix them inline.

Topic: $ARGUMENTS

---

## Step 0 — Context Gathering (silent)

Read these files silently — do NOT output anything yet:

1. `docs/advisory-board/charter.md` — load personas, mission, rules of engagement
2. `docs/advisory-board/meetings/README.md` — count table rows to determine next meeting number. Extract the **last 3 meeting entries** (file paths)
3. Read those 3 most recent meeting files — focus on their **Decisions** and **Action Items** sections for continuity
4. `docs/state/project-state.md` — current project state, blockers, what was just done

If `$ARGUMENTS` is empty or missing, ask the Founder:
```
What topic should the board debate today?
```
Wait for their response before continuing.

---

## Step 1 — Scope Lock

Print this block and wait for confirmation:

```
═══════════════════════════════════════════════════════════════
  ADVISORY BOARD — Meeting #{next_number}
  Date:    {today's date}
  Topic:   {extracted topic}

  Core:    CTO · CRO · CMO · COO · UX/UI Lead · SaaS Psych · PO
  Guests:  {1-3 dynamic consultants selected based on topic}

  Prior:   Reviewed meetings #{N}, #{N-1}, #{N-2}
═══════════════════════════════════════════════════════════════
  Confirm topic, or adjust.
```

Wait for confirmation. If the Founder adjusts the topic or guests, update accordingly.

---

## Step 2 — Independent Member Research

This is the critical step. Each member prepares INDEPENDENTLY before the meeting starts. Each member has their own lens and arrives with their own data.

**Execute actual research for each member using tools:**

### CTO — Technical Architecture
- Grep/Glob/Read codebase files relevant to the topic (find actual implementations, schemas, configs)
- Identify technical debt, scaling concerns, or architecture gaps
- WebSearch for latest framework or infrastructure trends if applicable
- Form a technical position backed by specific file paths and line numbers

### CRO — Revenue & Monetization
- Review pricing context from project state and any pricing references
- WebSearch for competitor pricing models, conversion benchmarks relevant to the topic
- Calculate revenue implications or unit economics impact where possible
- Form a revenue-first position

### CMO — Go-To-Market & Positioning
- WebSearch for market trends, organic growth channels, positioning strategies
- Analyze competitive landscape and differentiation angles
- Form a growth-first position

### COO — Operations & Efficiency
- Assess operational cost, timeline impact, and process efficiency
- Review current blockers and shipping velocity from the state doc
- Evaluate build-vs-buy and resource allocation tradeoffs
- Form an efficiency-first position

### UX/UI Lead — User Journey & Design
- WebSearch for best-in-class UX patterns from top SaaS products (Linear, Notion, Vercel, Stripe)
- Analyze user journey impact and friction points
- Review existing UI implementations in the codebase
- Form a user-experience-first position

### SaaS Psychologist — Behavioral Design
- Analyze behavioral triggers, cognitive load, and motivation engineering angles
- Consider activation, retention, and "aha!" moment implications
- Review user flow and decision architecture
- Form a psychology-first position

### Product Owner — Roadmap & Adoption
- Review the flight plan context for roadmap fit
- Assess pain point alignment and adoption risk
- Evaluate feature priority against current timeline
- Form a user-needs-first position

### Dynamic Consultants (1-3)
- Research their specialty area with the same depth and independence

**Important:** Each member must arrive with a POSITION, not just observations. They are prepared to argue it.

---

## Step 3 — The Meeting

### Tone & Style Rules
- **Assertive and direct.** No hedging. Each member states their position and defends it.
- **Evidence-based.** Members cite their research — file paths, data points, competitor examples. Not vibes.
- **Genuine disagreement.** Members challenge each other when their research leads to different conclusions.
- **Practical.** Everything ties back to the current goals and timeline. No theoretical navel-gazing.

### Meeting Flow

1. **Context** — Most relevant lead sets the stage (2-3 sentences: why we're here, what needs deciding)

2. **Key Findings** — Each member presents their independent research under their own heading. Lead with data, end with position.

3. **The Debate** — Members react to each other's findings:
   - Direct challenges: "CRO, your conversion estimate assumes X, but my UX research shows Y"
   - Building on each other: "COO's timeline concern is valid — here's how we solve it without the full rewrite"
   - Tradeoff surfacing: "We can't have CMO's positioning AND CTO's architecture without a 3-week delay"

4. **Dissent Protocol** — At least ONE member MUST argue the contrarian position on whatever the group is converging toward. This is mandatory. Name the dissenter explicitly. They argue with real evidence, not token opposition.

5. **🔶 Founder Decision Points** — When the board hits a genuine fork where the right path depends on strategic judgment only the Founder has:

   **PAUSE the meeting.** Print:
   ```
   ┌─────────────────────────────────────────────────────────┐
   │  🔶 FOUNDER DECISION NEEDED                             │
   │                                                         │
   │  [Describe the fork clearly]                            │
   │                                                         │
   │  Option A: [description]                                │
   │    → Who supports and why                               │
   │                                                         │
   │  Option B: [description]                                │
   │    → Who supports and why                               │
   │                                                         │
   │  Board's recommendation: [Option X] because [reason]    │
   └─────────────────────────────────────────────────────────┘
   ```

   **Wait for Founder input.** Then resume incorporating the decision.

   There may be 0, 1, or multiple Decision Points per meeting. Only pause for genuine forks — not rubber-stamping obvious choices.

6. **Decisions Table:**

   | # | Decision | Rationale | Confidence |
   |---|----------|-----------|------------|
   | 1 | ... | ... | High/Med/Low |

7. **Action Items:**

   | # | Action | Owner | Priority |
   |---|--------|-------|----------|
   | 1 | ... | ... | High/Med/Low |

### Meeting Output Format

```markdown
# Advisory Board Meeting #{N}: {Topic Title}

**Date:** {YYYY-MM-DD} | **Topic:** {one-line description}
**Attendees:** {core roles present} | **Guest Consultant:** {specialist names}
**Dissenter:** {Role} — argued against {leading position}

---

## Context
{2-4 sentences: current project state, why this meeting was called, prior meeting references}

---

## Key Findings

### CTO — {Area}
{Numbered findings with specific data, file paths, web research citations}

### CRO — {Area}
{Numbered findings}

### CMO — {Area}
{Numbered findings}

{...etc for each attendee...}

---

## Debate Highlights
{The most important exchanges, challenges, and turning points — not verbatim, but the key moments that shaped decisions}

---

## Founder Decisions
{Any decisions the Founder made during the meeting, with context}

---

## Decisions

| # | Decision | Rationale | Confidence |
|---|----------|-----------|------------|

---

## Action Items

| # | Action | Owner | Priority |
|---|--------|-------|----------|
```

---

## Step 4 — Save & Index

1. **Save the meeting** to `docs/advisory-board/meetings/{YYYY-MM-DD}-{topic-slug}.md`
   - topic-slug: lowercase, hyphens, max 6 words (e.g., `auth-architecture-decision`)
   - If a file with that date+slug exists, append `-2`, `-3`, etc.

2. **Update the README** — append a new row to `docs/advisory-board/meetings/README.md`:
   ```
   | {YYYY-MM-DD} | {Topic Title} | [{filename}](./{filename}) |
   ```

3. Confirm:
   ```
   ✅ Meeting #{N} saved: docs/advisory-board/meetings/{filename}
      Decisions: {count} | Action items: {count}
   ```

---

## Step 5 — Post-Meeting

```
━━━ What's next? ━━━
• "prompt N"   → Generate a /prompt-builder session for action item #N
• "deepen N"   → Reconvene the board focused on decision #N
• "done"       → Close the meeting
```

- **prompt N** → Run `/prompt-builder` with the action item as context
- **deepen N** → Re-enter Step 3 focused narrowly on that decision. Same research rigor, same debate intensity.
- **done** → Print: `Meeting #{N} adjourned.`

---

## Rules

- NEVER skip the independent research phase. Each member earns their seat with preparation.
- NEVER let the board reach unanimous agreement without testing it. The dissent protocol is mandatory.
- NEVER simulate Founder decisions. When the board hits a real fork, PAUSE and ASK.
- ALWAYS save the meeting file and update the README index.
- ALWAYS reference prior meetings when relevant — the board has institutional memory.
- Keep the tone intense, collaborative, and action-oriented.
