---
task: COIN-NETWORK-SCAN
title: Author modes/network-scan.md — LinkedIn warm-intro discovery (proficiently port)
phase: Modes Build-Out
size: M
depends_on: COIN-AUTOPIPELINE
created: 2026-04-25
---

# COIN-NETWORK-SCAN: Author `modes/network-scan.md`

## Context

The single highest-leverage missing capability in Coin is *warm-intro discovery*. Cold applications through ATS portals convert at 1–3%; warm intros via 1st-degree LinkedIn connections convert at 30%+. Sean has a 1500+ contact LinkedIn graph from 15 years in wireless / IoT / RevOps. Most applications today bypass that graph entirely.

The `proficiently` skill collection (referenced in `.claude/skills/coin/references/`) ships a working LinkedIn warm-intro pattern: given a target company + role, surface the user's 1st/2nd-degree connections at that company, rank by recency of last interaction and relevance to the role, and draft a personalized outreach DM. We are porting that pattern into a Coin mode.

This is a **discovery + drafting** mode, not a browser automation mode. Coin will not auto-send LinkedIn DMs (TOS risk + Sean writes better outreach). It produces a ranked contact list and a per-contact draft message that Sean copy-pastes.

## Goal

Create `modes/network-scan.md` so that `/coin network-scan <id>` (or `/coin network-scan <company>`) finds Sean's LinkedIn connections at the target company, ranks them by warm-intro probability (recency × seniority × relevance to the role), and drafts a personalized outreach DM per contact for Sean to review and send.

## Pre-conditions

- [ ] Role exists in `data/db/pipeline.db` with status ≥ `scored` (so we know the target company + role title)
- [ ] OR a free-text company name is passed; mode prompts for target role title interactively
- [ ] LinkedIn data source: either a CSV export of Sean's 1st-degree connections at `data/network/linkedin_connections.csv` (preferred — LinkedIn's official "Get a copy of your data" export) OR live scraping of `linkedin.com/search/results/people?company=X` via the browser MCP tool (best-effort, fragile)
- [ ] PROFILE.linkedin populated (we use Sean's own URL to identify "self" rows in the export)

## Steps

### Step 1 — Reference scaffold

Create `.claude/skills/coin/references/network-patterns.md` with:
- **Connection-export schema** — column layout of LinkedIn's CSV export (`First Name`, `Last Name`, `URL`, `Email Address`, `Company`, `Position`, `Connected On`)
- **Recency tiers** — `Connected On` parsing, bucket into hot (<6mo since last public interaction we can detect), warm (<2yr), cold (>2yr or unknown)
- **Seniority signals** — title keywords mapping to seniority levels (`VP|Director|Head of|Chief` = leadership; `Senior|Staff|Principal` = senior IC; rest = peer)
- **Relevance signals** — title-overlap to the target role and shared archetype (an Enterprise SE at the target co is more useful than a Marketing intern)
- **Outreach templates** — three opener variants (cold reconnect, mutual project, recent post comment) keyed by recency tier
- **Forbidden behaviors** — never auto-send, never scrape logged-out pages with cookies, never fabricate "we worked together at X" if no shared employer in PROFILE.positions

### Step 2 — Connection ingestion script

Add `scripts/import_linkedin_connections.py`:
- Reads `data/network/linkedin_connections.csv`
- Normalizes company names (lowercase, strip "Inc.", "LLC", "&", trailing punctuation)
- Writes to a new `connections` table in `pipeline.db`:
  ```sql
  CREATE TABLE IF NOT EXISTS connections (
      id INTEGER PRIMARY KEY,
      first_name TEXT, last_name TEXT, full_name TEXT,
      linkedin_url TEXT UNIQUE, email TEXT,
      company TEXT, company_normalized TEXT,
      position TEXT, connected_on DATE,
      seniority TEXT,           -- 'leadership' | 'senior_ic' | 'peer'
      last_seen DATE,           -- nullable; placeholder for future enrichment
      notes TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  CREATE INDEX IF NOT EXISTS idx_connections_company ON connections(company_normalized);
  ```
- Idempotent: ON CONFLICT(linkedin_url) UPDATE
- Prints summary: total rows, by-seniority breakdown, top 10 companies by connection count

### Step 3 — Author `modes/network-scan.md`

The mode must instruct the agent to:

**3.1 — Resolve target.** Accept either `<role_id>` (lookup company + title in DB) or `<company> [<title>]` free-text. Normalize the company name with the same rules as Step 2.

**3.2 — Query connections.** Run a SQL query against `connections` filtering on `company_normalized = ?`. If 0 results, also try LIKE-match on the original company string (Cox Communications vs Cox Inc.). If still 0, fall back to Step 3.3 (live scrape).

**3.3 — Live-scrape fallback.** If the user has the browser MCP tool connected, navigate to `https://www.linkedin.com/search/results/people/?company=<URL-encoded>&network=%5B%22F%22%5D` (1st-degree only). Read the first page (max 10 cards), parse name + title + profile URL, write to `connections` table for future runs. Surface the count to Sean before scoring.

**3.4 — Score per contact.**
```
warmth = recency_score (40%) + seniority_score (35%) + relevance_score (25%)
```
- **recency_score** — `Connected On` within 12mo = 100, 12–36mo = 60, >36mo = 30, unknown = 40
- **seniority_score** — `leadership` at the target co = 100, `senior_ic` = 75, `peer` = 50; recruiters = 90 regardless of recency
- **relevance_score** — substring match between contact's `position` and the target role title or its archetype keywords from `config/profile.yml` = 100; same archetype but different exact title = 70; unrelated = 30

Rank descending, surface top 8 plus any recruiters.

**3.5 — Draft outreach per top contact.** For each, draft a short LinkedIn DM (≤ 600 chars) following the template from `references/network-patterns.md` keyed by recency tier:
- **Hot reconnect:** reference last interaction (only if Sean told us about one this session — never invent)
- **Warm reconnect:** "Saw you're at <co> — they're hiring a <role>. Mind sharing what the team's like / who'd be a good warm intro to the hiring manager?"
- **Cold reconnect:** "Long time. Quick favor — <co> is hiring a <role> that lines up well with my Hydrant TPM and Utah Broadband SE work. Open to a 10-min call to see if there's a fit?"
- Each draft must include: contact's first name, target company, target role title, ONE line tying Sean's actual proof point to the role (drawn from PROFILE.positions, not invented).

**3.6 — Output the brief.** Print a per-contact card:
```
═══════════════════════════════════════════════
  Network Scan — <company> / <role title>
  Role <id> — <fit grade>
═══════════════════════════════════════════════

8 connections found. Top picks:

[1] Jane Doe · VP Eng @ Cox · connected Mar 2021
    Warmth 92 (recency 60 · seniority 100 · relevance 100)
    Draft DM:
    > Hey Jane — long time. Cox is hiring a Sr TPM on the Networks team
    > and the JD reads almost exactly like the True-Local-Labs work I led
    > at Hydrant. Mind a 10-min call this week to see if it's a fit, or
    > pointing me to the hiring manager?

[2] John Smith · Senior PM @ Cox · connected Aug 2019
    ...

NEXT
  → Pick contacts to message
  → Send via LinkedIn manually (Coin will NOT send)
  → Then: /coin track <id> contact   (if a reply comes in)
```

**3.7 — Persist outreach state.** Write each surfaced contact to a new `outreach` table:
```sql
CREATE TABLE IF NOT EXISTS outreach (
    id INTEGER PRIMARY KEY,
    role_id INTEGER REFERENCES roles(id),
    connection_id INTEGER REFERENCES connections(id),
    drafted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP NULL,           -- Sean updates manually after send
    replied_at TIMESTAMP NULL,
    warmth_score REAL,
    draft_message TEXT,
    notes TEXT
);
```
The `sent_at` and `replied_at` columns are deliberately nullable + manually updated. **Never auto-set them** — sending happens outside Coin.

### Step 4 — Add safety guards

The mode must explicitly REFUSE:

| Refusal | Why |
|---|---|
| Auto-sending DMs via the browser MCP tool | LinkedIn TOS + Sean writes better than templates |
| Inventing a shared history ("we worked together at X") not in PROFILE.positions | Truthfulness gate (Operating Principle #1) |
| Scraping with Sean's logged-in session cookies | Account ban risk + we have the export |
| Surfacing connections at a `out_of_band` employer for tailoring | Wasted effort — pedigree quarantine still applies |
| Drafting outreach for a role with `fit_score < 55` (D/F grade) | Don't burn warm intros on bad fits |

### Step 5 — Test

Add `tests/test_network_scan_mode.py`:
1. Read `modes/network-scan.md` content
2. Assert each step (3.1–3.7) is present
3. Assert all 5 refusals from Step 4 are documented
4. Assert "never auto-send" appears at least twice
5. Assert `recency_score`, `seniority_score`, `relevance_score` and the 40/35/25 weights are documented exactly
6. Schema test: import the schema-creation snippet, run against a temp SQLite, assert `connections` and `outreach` tables exist with the expected columns

Add `tests/test_import_linkedin_connections.py`:
1. Build a 5-row CSV fixture in tests/fixtures/network/
2. Run `import_linkedin_connections.py` against a temp DB
3. Assert 5 rows in `connections`
4. Re-run, assert still 5 rows (idempotency)
5. Assert company normalization: "Cox Communications, Inc." and "cox communications inc" land in the same `company_normalized` bucket

### Step 6 — SKILL.md routing

Add to the Mode Routing table in `.claude/skills/coin/SKILL.md`:

```
| `network-scan <id>` or `network-scan <company>` | `modes/network-scan.md` (warm-intro discovery) |
```

Add to the Discovery menu (`/coin` no-arg banner):

```
  /coin network-scan <id>     Find warm intros at target company
```

### Step 7 — Update _shared.md mode catalog

Add row:

```
| `network-scan` | Find LinkedIn warm intros at target company | `modes/network-scan.md` |
```

## Verification

```bash
cd /Users/tealizard/Documents/lab/coin
.venv/bin/pytest tests/test_network_scan_mode.py tests/test_import_linkedin_connections.py -v --tb=short

# Manual smoke (requires Sean's LinkedIn export at data/network/linkedin_connections.csv)
.venv/bin/python scripts/import_linkedin_connections.py
# Then in /coin session:
# /coin network-scan 4    (Netflix role — should find 0–2 connections, mostly cold)
# /coin network-scan Filevine    (Utah-local — expect more)
```

- [ ] `modes/network-scan.md` exists, follows the step shape
- [ ] `scripts/import_linkedin_connections.py` is idempotent
- [ ] `connections` and `outreach` tables created on first import
- [ ] Top-N ranking math matches the documented weights exactly
- [ ] All 5 Step 4 refusals are explicit
- [ ] No DM is auto-sent under any code path
- [ ] Both test files pass

## Definition of Done

- [ ] `modes/network-scan.md` authored
- [ ] `scripts/import_linkedin_connections.py` works on a real LinkedIn export
- [ ] Schema migration tracked in `schema_migrations` table
- [ ] At least one role's network scan produces ranked output (live or empty-but-clean)
- [ ] `docs/state/project-state.md` updated
- [ ] No regressions in existing `pytest tests/`

## Rollback

```bash
rm modes/network-scan.md tests/test_network_scan_mode.py tests/test_import_linkedin_connections.py
rm scripts/import_linkedin_connections.py
rm .claude/skills/coin/references/network-patterns.md
git checkout .claude/skills/coin/SKILL.md modes/_shared.md docs/state/project-state.md
.venv/bin/python -c "
import sqlite3
db = sqlite3.connect('data/db/pipeline.db')
db.execute('DROP TABLE IF EXISTS outreach')
db.execute('DROP TABLE IF EXISTS connections')
db.commit()
"
```

## Notes for the executor

- LinkedIn's CSV export is the canonical input. Live scraping is a fallback only. If both fail, the mode should print a one-screen "how to export your connections" guide and stop, not error.
- Recruiters at the target company are special-cased to `seniority_score = 90` regardless of recency because a recruiter intro is the highest-value warm intro for at-grade roles.
- The `outreach` table is the seed for the future `followup` mode integration — surfaced contacts that never got a `sent_at` should bubble up as TODOs in `/coin followup` after this lands.
- Keep the draft DM under 600 chars; LinkedIn truncates at ~700 in the inbox preview.
- Match the Sean-truthfulness test from `modes/audit.md`: drafts must NOT claim Cox/TitanX/Safeguard outcomes as Sean's; he was Hydrant's PM/COO on those engagements.
