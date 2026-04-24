---
description: Plain-English interface. Ask anything about your job search — Coin interprets and routes to the right module.
---

# /coin [question]

**Usage:**
- `/coin should I apply to this Stripe TPM role?` — paste a URL or job description
- `/coin what's my strongest lane right now?` — strategic analysis
- `/coin how many roles am I tracking?` — pipeline status
- `/coin rewrite my summary for a sales role at Salesforce`

---

## Routing logic

Parse the user's question and route:

| Intent | Route to |
|--------|----------|
| Find new roles | `/coin-search` with detected lane |
| Generate resume for specific role | `/coin-apply` |
| Pipeline status question | `/coin-track` |
| Strategic / "should I" | `/alpha-squad` with question as topic |
| Rewrite request without specific role | `transformer.transform()` with lane + generic role |
| Comp question | `compensation.lookup()` |

Always confirm the routing before executing:
```
I'll {action}. Proceed? [y/n]
```

Wait for confirmation, then execute.

## Rules
- Never execute destructive pipeline operations (delete, archive) from plain-English commands — require explicit `/coin-track` usage
- If the lane is ambiguous, ask: "Which lane? tpm-high / pm-ai / sales-ent"
