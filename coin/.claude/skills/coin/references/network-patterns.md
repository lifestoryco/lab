# Network Scan — LinkedIn Warm-Intro Patterns

Reference doc loaded by `modes/network-scan.md`. Encodes the schema,
ranking math, outreach templates, and forbidden behaviors for the
warm-intro discovery flow ported from `proficiently`.

---

## Connection-export schema

LinkedIn's official "Get a copy of your data" → Connections export. CSV
columns (as of 2026-04):

| Column | Type | Notes |
|---|---|---|
| `First Name` | text | sometimes blank for legacy contacts |
| `Last Name` | text | |
| `URL` | text | `https://www.linkedin.com/in/<slug>` — primary key |
| `Email Address` | text | populated for ~10% of contacts |
| `Company` | text | most-recent employer at time of connection |
| `Position` | text | title at time of connection (NOT current — stale fast) |
| `Connected On` | text | `DD MMM YYYY` (e.g. `12 Mar 2021`) |

The export is the canonical input. Live scraping is a fallback only.

---

## Recency tiers

Bucket by `Connected On` distance from today:

| Tier | Window | recency_score |
|---|---|---|
| `hot` | ≤ 12 months | 100 |
| `warm` | 12–36 months | 60 |
| `cold` | > 36 months | 30 |
| `unknown` | (no date) | 40 |

Recency reflects when the relationship was established, NOT when last
seen. Future enrichment (DM history, last public interaction) feeds the
nullable `connections.last_seen` column.

---

## Seniority signals

Title-keyword classification:

| Seniority | Triggers (lowercase substring) |
|---|---|
| `leadership` | `vp`, `vice president`, `director`, `head of`, `chief`, `cxo`, `c-suite`, `founder`, `co-founder`, `partner` |
| `senior_ic` | `senior`, `sr.`, `principal`, `staff`, `lead `, `architect` |
| `peer` | (default — no leadership / senior_ic match) |

**Recruiter override:** any title containing `recruit`, `talent acquisition`,
or `talent partner` → `seniority_score = 90` regardless of recency tier.
Recruiter intros are the highest-leverage warm intro for at-grade roles.

---

## Relevance signals

Compare contact's `position` to the target role's archetype:

| Match level | Trigger | relevance_score |
|---|---|---|
| Exact role overlap | substring of target role title appears in contact's position | 100 |
| Same archetype | contact's title hits any keyword from `config/profile.yml`'s archetype `keyword_emphasis` | 70 |
| Adjacent | contact in eng / product / sales / ops org but not the target archetype | 50 |
| Unrelated | none of the above | 30 |

---

## Warmth composite

```
warmth = recency_score (40%) + seniority_score (35%) + relevance_score (25%)
```

Rank descending. Surface top 8 plus any recruiters (even if outside top 8).

---

## Outreach templates

Keyed by **recency tier** (NOT seniority — voice should match how recently
you've been in touch):

### Hot reconnect (≤ 12 mo)

> Hey {first_name} — saw {company} is hiring a {role_title}. Aligns well
> with my {one_line_proof_from_PROFILE}. Mind a 10-min call this week to
> see if it's a fit, or pointing me to the hiring manager?

Use *only* if Sean has confirmed last interaction this session. Don't
fabricate a memory ("loved your post last month") if we have no record.

### Warm reconnect (12–36 mo)

> Hey {first_name} — long-ish time. Quick favor: {company} is hiring a
> {role_title} that lines up with the {project_or_role_at_PROFILE}.
> Mind sharing what the team's like, or who'd be a good warm intro to
> the hiring manager?

### Cold reconnect (> 36 mo)

> Hey {first_name} — long time. Quick favor: {company} is hiring a
> {role_title} that lines up well with my {hydrant_role + one_metric} and
> {utah_broadband_role + one_metric}. Open to a 10-min call to see if
> there's a fit on your team?

### Recruiter (any tier)

> Hi {first_name} — I'm targeting {role_title} at {company}. PMP, MBA,
> 15 yrs B2B SaaS / IoT delivery; comp expectation $200K+ TC. Open
> roles I should know about?

---

## Hard rules — every draft

1. Length cap: ≤ 600 chars. LinkedIn truncates at ~700 in the inbox preview.
2. First name required (never "Hey there").
3. Target company + role title required.
4. ONE proof point tied to a real PROFILE.position — never invented.
5. Cox / TitanX / Safeguard outcomes → frame as Hydrant engagements
   (Sean was Hydrant's PM/COO/lead, not the client's employee).

---

## Forbidden behaviors

| Forbidden | Why |
|---|---|
| Auto-sending DMs via the browser MCP tool | LinkedIn TOS + Sean writes better than templates |
| Inventing a shared history ("we worked together at X") not in PROFILE.positions | Truthfulness gate (Operating Principle #1) |
| Scraping with Sean's logged-in session cookies | Account ban risk + we have the export |
| Surfacing connections at an `out_of_band` employer for tailoring | Wasted effort — pedigree quarantine still applies |
| Drafting outreach for a role with `fit_score < 55` (D/F grade) | Don't burn warm intros on bad fits |

---

## Future enrichment (deferred)

- **`last_seen`** — populate from LinkedIn message-export (separate export)
- **Mutual connections count** — second-degree triangulation
- **Recent post engagement** — surface contacts who recently liked / commented
  on Sean's posts (highest-recency signal we can detect non-fabricated)
