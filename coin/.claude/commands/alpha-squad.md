---
description: Convene a 7-member advisory board for strategic decisions. Use for architecture tradeoffs, prioritization debates, or when stuck on a hard call.
---

# /alpha-squad [topic]

Spawn 7 specialist advisors. Each gives an independent opinion. You synthesize into a recommendation.

**Usage:** `/alpha-squad should we add LinkedIn API or keep scraping HTML?`

---

## The Board

| # | Advisor | Lens |
|---|---------|------|
| 1 | **The Pragmatist** | Shortest path to working software |
| 2 | **The Architect** | Long-term maintainability and clean boundaries |
| 3 | **The Security Auditor** | Attack surface, data exposure, API key risk |
| 4 | **The Product Manager** | Does this move Sean's job search forward? |
| 5 | **The Data Engineer** | Schema design, query performance, pipeline reliability |
| 6 | **The Career Strategist** | What actually gets interviews and offers? |
| 7 | **The Devil's Advocate** | What's wrong with the current plan? |

---

## Output format

```
═══════════════════════════════════════════════
  Alpha Squad — {topic}
═══════════════════════════════════════════════

[Pragmatist] {1-2 sentences}
[Architect]  {1-2 sentences}
[Security]   {1-2 sentences}
[PM]         {1-2 sentences}
[Data Eng]   {1-2 sentences}
[Career Str] {1-2 sentences}
[Devil's Adv]{1-2 sentences}

─────────────────────────────────────────────
Synthesis: {your recommendation, 2-3 sentences}
Dissent:   {strongest counterargument}
Decision:  {what to do, one sentence}
```
