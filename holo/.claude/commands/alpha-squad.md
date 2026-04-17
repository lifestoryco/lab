---
description: Convene the Holo Advisory Board. Seven specialists (CTO, CRO, CMO, COO, UX Lead, SaaS Psych, PO) plus dynamic consultants research independently, debate hard, and produce decisions with action items. Use for any strategic fork — roadmap, monetization, architecture, GTM.
---

# /alpha-squad

Convenes the Holo Advisory Board. Each member researches independently before
the meeting starts. Decisions are earned through debate, not consensus.

> **Read-only command.** Tools permitted: Read, Grep, Glob, Agent (Explore), Bash
> (read-only: git log, git diff, ls), WebSearch, WebFetch.
> Do NOT call Edit, Write, or any file-modifying Bash command.
> Log bugs found during research as action items — do not fix inline.

Topic: $ARGUMENTS

---

## Step 0 — Context Gathering (silent)

Read these files silently before printing anything:

1. `docs/advisory-board/charter.md` — board personas, mission, rules of engagement
2. `docs/advisory-board/meetings/README.md` — count table rows to determine next meeting number; extract last 3 meeting file paths
3. Read those 3 most recent meeting files — focus on **Decisions** and **Action Items** for continuity
4. `docs/state/project-state.md` — current state, blockers, live features, roadmap

If `$ARGUMENTS` is empty, ask:
```
What topic should the board debate today?
```
Wait for response before continuing.

---

## Step 1 — Scope Lock

Print this block and wait for confirmation:

```
═══════════════════════════════════════════════════════════════
  HOLO ADVISORY BOARD — Meeting #{next_number}
  Date:    {today's date}
  Topic:   {topic}

  Core:    CTO · CRO · CMO · COO · UX Lead · SaaS Psych · PO
  Guests:  {1-3 dynamic consultants selected based on topic}

  Prior:   Reviewed meetings #{N}, #{N-1}, #{N-2}
═══════════════════════════════════════════════════════════════
  Confirm topic, or adjust.
```

Wait for confirmation. Update topic or guests if the Founder adjusts.

---

## Step 2 — Independent Member Research

Every member prepares BEFORE the meeting. Each has their own lens and arrives
with a position they are ready to defend.

### CTO — Technical Architecture
- Grep/Glob/Read codebase: `api/index.py`, `pokequant/`, `config.py`, `tests/`, `vercel.json`
- Find actual implementations relevant to the topic — specific line numbers
- Check test coverage gaps: what's untested that the topic touches?
- WebSearch for relevant Python/Vercel/scraping patterns or constraints
- **Position:** What's the right technical path, and what breaks if we go the other way?

### CRO — Revenue & Monetization
- Review `docs/state/project-state.md` for current monetization status (none)
- WebSearch for TCG tool pricing (TCGFish, PokeData), trading tool SaaS benchmarks,
  freemium conversion rates for niche data products
- Calculate revenue scenarios: what does $X/month × N subscribers look like?
- **Position:** What's the highest-leverage monetization move given the topic?

### CMO — Go-To-Market & Community
- WebSearch for Pokémon TCG Discord servers, content creators, r/pkmntcg community dynamics,
  card shop networks, tournament circuit reach
- Analyze how top TCG tools grew (TCGPlayer, Limitless TCG, PriceCharting) — what was their
  early community wedge?
- **Position:** What's the fastest path to 1,000 real users who care?

### COO — Operations & Efficiency
- Review `docs/state/project-state.md` blockers section
- Assess scraper reliability, Vercel function costs, SQLite cache hit rates
- Evaluate build/buy/defer for whatever the topic proposes
- **Position:** What's the real operational cost and what's the risk of cutting corners?

### UX/UI Lead — User Journey & Design
- Read `handoffpack-www/components/lab/holo/HoloPage.tsx` — find relevant UI sections
- WebSearch for best-in-class patterns from Linear, Robinhood, Bloomberg, Stripe, Vercel dashboard
- Consider the primary user: serious trader on mobile, post-pack-opening, needs instant clarity
- **Position:** What does the ideal user experience look like for this topic?

### SaaS Psychologist — Behavioral Design & Retention
- Analyze the topic through habit loops, loss aversion, social proof, and FOMO mechanics
- Consider the TCG trader's psychology: the thrill of finding alpha before others,
  fear of leaving money on the table, identity as a "smart" investor
- WebSearch for retention patterns in niche data tools and trading platforms
- **Position:** What behavioral design makes Holo genuinely sticky, not just useful once?

### Product Owner — Roadmap & Prioritization
- Review the H-1.x roadmap from `docs/state/project-state.md`
- Read `docs/ux-recommendation.md` and `docs/signal-quality-research.md` for prior research
- Assess how the topic fits the current roadmap sequence — does it unblock or block other items?
- **Position:** Should we build this now, later, or never given what's on the roadmap?

### Dynamic Consultants
Research their specialty area with the same depth and independence.
Arrive with a position, not just observations.

---

## Step 3 — The Meeting

### Tone
- **Direct.** No hedging. State your position and defend it.
- **Evidence-based.** File paths, data points, competitor examples. Not vibes.
- **Genuine disagreement.** Challenge each other when research leads to different conclusions.
- **Practical.** Tie everything to the current roadmap and realistic timeline.

### Meeting Flow

1. **Context** — Most relevant lead sets the stage (2-3 sentences: why we're here, what needs deciding)

2. **Key Findings** — Each member presents under their own heading. Lead with data, end with position.

3. **The Debate** — Members react to each other:
   - Direct challenges: "CRO, your conversion estimate assumes X, but UX research shows Y"
   - Building on: "COO's scraper risk is real — here's how we mitigate without delaying"
   - Surfacing tradeoffs: "We can't have CMO's community push AND CTO's rewrite without 3 weeks"

4. **Dissent Protocol** — At least ONE member MUST argue the contrarian position on whatever
   the group is converging toward. **Mandatory.** Name the dissenter explicitly.
   They argue with real evidence — no token opposition.

5. **🔶 Founder Decision Points** — When the board hits a fork only the Founder can resolve:

   **PAUSE the meeting.** Print:
   ```
   ┌─────────────────────────────────────────────────────────┐
   │  🔶 FOUNDER DECISION NEEDED                             │
   │                                                         │
   │  [Describe the fork clearly]                            │
   │                                                         │
   │  Option A: [description]                                │
   │    → Supported by: [who and why]                        │
   │                                                         │
   │  Option B: [description]                                │
   │    → Supported by: [who and why]                        │
   │                                                         │
   │  Board's recommendation: [Option X] because [reason]    │
   └─────────────────────────────────────────────────────────┘
   ```

   **Wait for Founder input.** Resume incorporating the decision.
   There may be 0, 1, or multiple Decision Points. Only pause for genuine forks.

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
**Attendees:** {core roles} | **Guests:** {specialist names}
**Dissenter:** {Role} — argued against {leading position}

---

## Context
{2-4 sentences: current project state, why this meeting was called, prior meeting continuity}

---

## Key Findings

### CTO — {Area}
{Numbered findings with file paths, line numbers, web research citations}

### CRO — {Area}
{Numbered findings}

### CMO — {Area}
{Numbered findings}

{...etc for each attendee...}

---

## Debate Highlights
{The most important exchanges — not verbatim, but the key moments that shaped decisions}

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
   - topic-slug: lowercase, hyphens, max 6 words (e.g., `monetization-freemium-tier-design`)
   - If that date+slug exists, append `-2`, `-3`, etc.

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
• "prompt N"   → Generate a task prompt for action item #N
• "deepen N"   → Reconvene the board focused on decision #N
• "done"       → Close the meeting
```

- **prompt N** → Write a detailed implementation task for action item #N into
  `docs/tasks/prompts/pending/` following the H-1.x naming convention
- **deepen N** → Re-enter Step 3 focused narrowly on decision #N.
  Same research rigor, same debate intensity.
- **done** → Print: `Meeting #{N} adjourned.`

---

## Rules

- NEVER skip the independent research phase. Members earn their positions with preparation.
- NEVER reach unanimous agreement without testing it. Dissent protocol is mandatory.
- NEVER simulate Founder decisions. Genuine forks get paused and asked.
- ALWAYS save the meeting file and update the README index.
- ALWAYS reference prior meetings — the board has institutional memory.
- Keep the tone intense, collaborative, and action-oriented.
- Every action item must be specific enough to execute without a follow-up question.
