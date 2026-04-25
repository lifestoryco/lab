# Coin Mode — `network-scan` (LinkedIn warm-intro discovery)

> Load `modes/_shared.md` and `.claude/skills/coin/references/network-patterns.md` first.

**Purpose:** Find Sean's existing LinkedIn connections at a target company,
rank by warm-intro probability, and draft a personalized DM per top contact
that Sean copy-pastes manually.

This is a **discovery + drafting** mode. Coin does NOT auto-send DMs.

---

## Hard refusals (read first)

| Refusal | Why |
|---|---|
| Auto-sending DMs via the browser MCP tool | LinkedIn TOS + Sean writes better |
| Inventing a shared history ("we worked together at X") not in PROFILE.positions | Truthfulness gate (Operating Principle #1) |
| Scraping with Sean's logged-in session cookies | Account ban risk + we have the export |
| Surfacing connections at an `out_of_band` employer for tailoring purposes | Pedigree quarantine still applies |
| Drafting outreach for a role with `fit_score < 55` (D/F grade) | Don't burn warm intros on bad fits |
| Auto-setting `outreach.sent_at` or `outreach.replied_at` | Sending happens outside Coin — Sean updates manually |

---

## Step 1 — Resolve target company + role

Two invocations:

**A. By role id:**
```
/coin network-scan <id>
```

```bash
.venv/bin/python scripts/print_role.py --id <id>
```

Pull `company`, `title`, `lane`, `fit_score` from the row. If `fit_score < 55`,
STOP — print the refusal from above. If `lane == 'out_of_band'`, STOP with
the same refusal.

**B. By company free-text:**
```
/coin network-scan <company> [<title>]
```

If only company is given, prompt: *"What role title are you targeting at <company>? (free-text)"*

Normalize the company string with the same rules as `scripts/import_linkedin_connections.py::normalize_company`.

---

## Step 2 — Query connections

```bash
.venv/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/db/pipeline.db')
conn.row_factory = sqlite3.Row
rows = conn.execute(
    'SELECT * FROM connections WHERE company_normalized = ? OR company_normalized LIKE ?',
    ('<normalized>', '%<normalized>%'),
).fetchall()
print('found', len(rows))
for r in rows:
    print(dict(r))
"
```

If the `connections` table doesn't exist yet, instruct Sean:

> *"No connections imported yet. Run:*
> *`.venv/bin/python scripts/import_linkedin_connections.py`*
> *after dropping your LinkedIn export at `data/network/linkedin_connections.csv`. See network-patterns.md for the export-how-to."*

If 0 rows match the normalized company, also try LIKE on the raw company
string (Cox Communications vs Cox Inc.). If still 0, fall through to Step 3.

---

## Step 3 — Live-scrape fallback (optional)

Only if the browser MCP tool is connected AND Sean confirms (*"Live-scrape
LinkedIn for additional connections at <company>? Risk: low; we hit the
public 1st-degree people-search page only. (y/n)"*):

Navigate to:
```
https://www.linkedin.com/search/results/people/?company=<URL-encoded>&network=%5B%22F%22%5D
```

Read the first page (max 10 cards). Parse name + title + profile URL into the
`connections` table for future runs. Surface the count to Sean before scoring.

If Sean declines, proceed with whatever the export gave us (even 0).

---

## Step 4 — Score per contact

For each candidate connection compute:

```
recency_score    (40% weight)
seniority_score  (35% weight)
relevance_score  (25% weight)

warmth = 0.40*recency + 0.35*seniority + 0.25*relevance
```

Use the tables from `references/network-patterns.md`:

- **recency_score** — Connected On bucket (hot/warm/cold/unknown → 100/60/30/40)
- **seniority_score** — title classification (leadership=100, senior_ic=75, peer=50; recruiter override=90)
- **relevance_score** — title overlap to target role + archetype keywords (100/70/50/30)

Rank descending. Take top 8 PLUS any recruiters not already in the top 8.

---

## Step 5 — Draft outreach per top contact

For each contact, pick the template by **recency tier** from
`references/network-patterns.md`:

- Hot reconnect (≤ 12 mo) — only if Sean has confirmed last interaction this session
- Warm reconnect (12–36 mo)
- Cold reconnect (> 36 mo)
- Recruiter (any tier) — special-cased for `seniority='recruiter'` (title contains "recruit" / "talent")

Each draft must include:
1. Contact's first name
2. Target company
3. Target role title
4. ONE proof point tied to a real PROFILE.position (load `data/resumes/base.py`)
5. ≤ 600 chars total

**Truthfulness gate before each draft:** Cox / TitanX / Safeguard outcomes
must be framed as Hydrant engagements (Sean was Hydrant's PM/COO/lead, not
the client's employee). Re-read `_shared.md` Operating Principle #3.

---

## Step 6 — Output the brief

```
═══════════════════════════════════════════════
  Network Scan — <company> / <role title>
  Role <id> — <fit grade>
═══════════════════════════════════════════════

<N> connections found. Top picks:

[1] Jane Doe · VP Eng @ Cox · connected Mar 2021
    Warmth 92 (recency 60 · seniority 100 · relevance 100)
    Draft DM:
    > Hey Jane — long time. Cox is hiring a Sr TPM on the Networks team
    > and the JD reads almost exactly like the True-Local-Labs work I led
    > at Hydrant ($1M Year 1 revenue, 12 mo ahead of plan). Mind a 10-min
    > call this week to see if it's a fit, or pointing me to the hiring
    > manager?

[2] John Smith · Senior PM @ Cox · connected Aug 2019
    Warmth 78 (recency 30 · seniority 75 · relevance 100)
    Draft DM:
    > ...

NEXT
  → Pick contacts to message
  → Send via LinkedIn manually (Coin will NOT send)
  → After sending, update outreach.sent_at:
    /coin track-outreach <outreach_id> sent
  → If a reply comes in: /coin track <id> contact
```

---

## Step 7 — Persist outreach state

Insert one row per surfaced contact into `outreach`:

```bash
.venv/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/db/pipeline.db')
conn.execute('''
    INSERT INTO outreach (role_id, connection_id, warmth_score, draft_message)
    VALUES (?, ?, ?, ?)
''', (<role_id>, <conn_id>, <warmth>, <draft>))
conn.commit()
"
```

`sent_at` and `replied_at` stay NULL — Sean updates manually after sending.
**Never auto-set them.** This is the seed for the `followup` mode integration:
contacts with a draft but no `sent_at` should bubble up as TODOs in
`/coin followup` after this lands.

---

## Reference

| File | Purpose |
|---|---|
| `.claude/skills/coin/references/network-patterns.md` | Schema, weights, templates, refusals |
| `scripts/import_linkedin_connections.py` | CSV → `connections` table (idempotent) |
| `data/network/linkedin_connections.csv` | LinkedIn "Get a copy of your data" export |
| `connections` / `outreach` tables | Created by import script on first run |
