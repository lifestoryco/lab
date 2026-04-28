---
task: COIN-WEB-UI
title: Build /lab/coin Next.js dashboard — phone-shareable, kanban-driven, SaaS-grade UX
phase: UX Surface Expansion
size: XL
depends_on: COIN-SCORE-V2 (soft — falls back to fit_score if not landed)
created: 2026-04-27
---

# COIN-WEB-UI: Build the `/lab/coin` Next.js dashboard

## Context

Coin lives entirely inside Claude Code today. Sean hits `/coin status` and gets
a Rich-rendered Bloomberg-style dashboard in his terminal. That's perfect for
in-session work — but it has three failure modes that block the next stage of
throughput:

1. **Recruiter calls.** When Filevine's recruiter pings on Sean's phone at
   2pm, he can't open his terminal. He needs a phone-tappable URL that shows
   the role, the JD, the score breakdown, and the matched stories — in 3
   seconds, not 30.
2. **Read-only sharing.** A friend at Pluralsight asks "what does your resume
   look like for the SE role I forwarded?" — there's no shareable preview. The
   PDF lives on Sean's laptop in `data/resumes/generated/`.
3. **Pipeline visualization.** A 75-role pipeline doesn't fit on one Rich
   screen. Sean wants a kanban: drag a card from Discovered → Tailored →
   Applied, see the queue depth at every stage, find the stale ones at a
   glance.

The user explicitly asked for "next-level UI / SaaS enterprise standard." The
existing `/lab/holo` page is the proof point that this lab can host
project-specific dashboards alongside the marketing site. Coin gets the same
treatment.

## Goal

Ship `/lab/coin` — a Next.js page on `lab.handoffpack.com` that mirrors the
`/lab/holo` architecture and exposes the entire Coin pipeline as a tabbed
SaaS-style dashboard: kanban board, role detail drawer, discover feed,
network panel, ofertas comparison, and stories preview. Local dev only for
v1; Vercel deploy is gated behind a basic-auth env var. Read path is direct
SQLite via `better-sqlite3`; mutation path is a Python subprocess shim
(`careerops.web_cli`) so business logic stays in one source of truth.

## Pre-conditions

- [ ] `web/` Next.js 14 app exists at the repo root and `cd web && npm run dev` works today
- [ ] `web/components/lab/holo/HoloPage.tsx` is intact (used as architecture reference)
- [ ] `coin/data/db/pipeline.db` exists with current schema (roles, outreach, connections, offers tables)
- [ ] `coin/.venv/bin/python` is on PATH or accessible by absolute path from `web/`
- [ ] Node 18+ available locally (better-sqlite3 native build requires it)
- [ ] COIN-SCORE-V2 ideally landed (so `score_stage1` / `score_stage2` columns exist). If not, the API and UI fall back to the legacy `fit_score` column without erroring.

## Architecture decision: read vs. mutate

This is the single most important design choice in this task. Get it wrong
and we end up with two copies of the scoring math, the comp-band labels, the
state transitions — drift inevitable.

| Path | Tech | Why |
|---|---|---|
| **Read** (dashboards, lists, role detail) | Node `better-sqlite3` opens `pipeline.db` read-only | Zero-latency. No subprocess overhead per request. SQLite is the source of truth for state already. |
| **Mutate** (status transition, tailor invocation, notes append) | Node `child_process.spawn` → `python -m careerops.web_cli <cmd>` | Business logic (state machine validation, tailoring, scoring) stays in Python. The web layer is a thin front. One source of truth. |

This is the same pattern `/lab/holo` uses (Node proxies to a Python backend
for AI work). Document this decision in code comments — every future
contributor will ask why.

## Steps

### Step 1 — Backend CLI shim (`careerops/web_cli.py`)

Create `coin/careerops/web_cli.py`. This is a tiny `argparse`-based JSON CLI.
Every command emits a single line of JSON to stdout. Exit code is 0 on
success, 1 on user error (bad role_id, invalid status), 2 on internal error.

**Subcommands:**

```
python -m careerops.web_cli track --id N --status STATUS [--note TEXT]
python -m careerops.web_cli tailor --id N
python -m careerops.web_cli notes --id N --append TEXT
```

**Contract per command:**

- `track`:
  - Validates STATUS against the 11-state machine in `careerops/pipeline.py`
  - Calls `pipeline.update_status(role_id, status)`
  - If `--note` provided, also calls `pipeline.update_role_notes(role_id, note, append=True)`
  - Returns `{"ok": true, "role_id": N, "status": STATUS, "previous_status": "..."}`
- `tailor`:
  - Confirms role exists
  - Writes a marker file at `data/tailor_pending/<id>.txt` containing the timestamp + "queued by web_cli"
  - Updates role notes to record "tailor requested via web at <ts>"
  - Returns `{"ok": true, "role_id": N, "queued": true, "note": "Run /coin tailor <id> in next Claude session"}`
  - Rationale: actual tailoring requires the host LLM session. Web can only queue intent.
- `notes`:
  - Calls `pipeline.update_role_notes(role_id, text, append=True)`
  - Returns `{"ok": true, "role_id": N, "appended": <chars>}`

**Error shape:**
```json
{"ok": false, "error": "role_id 999 not found", "code": "ROLE_NOT_FOUND"}
```

**Stdin/stdout discipline:** Never print anything other than the single JSON
line. No log lines, no warnings, no progress bars. The Node caller parses
stdout as JSON; one stray print breaks everything. Route any internal logging
to stderr.

### Step 2 — Backend tests (`coin/tests/test_web_cli.py`)

Eight tests minimum:

1. `test_track_happy_path` — insert a role, transition `discovered` → `scored`, assert JSON shape and DB state
2. `test_track_with_note` — same but `--note "foo"`, assert notes column updated
3. `test_track_bad_role_id` — `--id 99999` with no such row, assert exit code 1 and `code: ROLE_NOT_FOUND`
4. `test_track_invalid_status` — `--status bogus`, assert exit code 1 and `code: INVALID_STATUS`
5. `test_tailor_happy_path` — assert marker file written + notes appended + JSON returned
6. `test_tailor_bad_role_id` — assert exit code 1
7. `test_notes_append` — assert notes column grew by N chars
8. `test_notes_empty_text` — `--append ""`, assert exit code 1 (empty text is a user error)

Use `pytest`'s `monkeypatch` to point `pipeline` at a temp DB so tests don't
touch real data. Use `subprocess.run` with `[sys.executable, "-m",
"careerops.web_cli", ...]` to exercise the actual CLI surface, not the
internal functions — that's the whole point of the tests.

### Step 3 — Next.js page route (`web/app/lab/coin/page.tsx`)

Server component. Fetches initial dashboard data so first paint is
populated, not a spinner.

```tsx
// web/app/lab/coin/page.tsx
// Mirrors the architecture of /lab/holo (see web/app/lab/holo/page.tsx).
// Read path: better-sqlite3 directly. Mutation path: subprocess to careerops.web_cli.

import { CoinPage } from '@/components/lab/coin/CoinPage';
import { fetchDashboard } from '@/components/lab/coin/server';

export default async function Page() {
  const initial = await fetchDashboard();
  return <CoinPage initialData={initial} />;
}
```

`fetchDashboard()` is a server-only helper in `web/components/lab/coin/server.ts`
that opens the SQLite DB and returns the same shape the `/api/coin/dashboard`
endpoint returns. This avoids a self-fetch on first render.

If `COIN_WEB_PASSWORD` is set in the environment, wrap the page render in an
`AuthGate` that checks for the `coin_auth` cookie. If absent, render the
login form. If `COIN_WEB_PASSWORD` is unset (local dev), bypass entirely.

### Step 4 — Layout (`web/app/lab/coin/layout.tsx`)

Mirror `web/app/lab/holo/layout.tsx`. Set:

- `metadata.title = "Coin — Career Ops"`
- `metadata.description = "Sean Ivins career pipeline — discover, score, tailor, track."`
- Dark theme by default
- Apply Orbitron / Space Grotesk / JetBrains Mono fonts already loaded in the root layout

### Step 5 — API route (`web/app/api/coin/[...slug]/route.ts`)

One catch-all route handler. Switch on `slug` array.

**Read endpoints** (open DB read-only via `better-sqlite3`):

| Path | Returns |
|---|---|
| `GET /api/coin/dashboard` | `{ pipeline_counts: { discovered: n, scored: n, ... }, top_roles: [...], stale_applications: [...], updated_at: ISO }` |
| `GET /api/coin/roles?status=&lane=&grade=&limit=100` | Array of role rows sorted by `fit_score DESC`, max 100 unless overridden. Filterable by status, lane, grade. |
| `GET /api/coin/role/[id]` | Full role detail: all columns + `score_breakdown` (parse from `score_breakdown_json` if present) + parsed JD |
| `GET /api/coin/role/[id]/pdf` | Streams the latest `data/resumes/generated/<id:04d>_<lane>_*.pdf` if it exists, else 404. Use `fs.createReadStream` and `Content-Type: application/pdf`. |
| `GET /api/coin/outreach` | Array from `outreach` table joined to `connections` where applicable |
| `GET /api/coin/offers` | All rows from `offers` table where `is_active=1` plus the `market_anchor` row(s) |
| `GET /api/coin/offers/compare` | Subprocess to `python -m careerops.web_cli compare-offers` — returns Y1 TC / 3yr TC / vest curve per offer. Keeps comp math in one place. |
| `GET /api/coin/stories` | Reads `data/resumes/stories.yml` if present (forward-compat with COIN-EXPERIENCE-DEEPDIVE), returns `[]` if absent |

**Mutation endpoints** (subprocess to `web_cli`):

| Path | Body | Action |
|---|---|---|
| `POST /api/coin/role/[id]/track` | `{status, note?}` | shells out to `web_cli track` |
| `POST /api/coin/role/[id]/tailor` | `{}` | shells out to `web_cli tailor` |
| `POST /api/coin/role/[id]/notes` | `{text}` | shells out to `web_cli notes` |

**Auth:** if `process.env.COIN_WEB_PASSWORD` is set, every endpoint checks
`request.cookies.get('coin_auth')?.value === sha256(COIN_WEB_PASSWORD)`. If
unset, all endpoints open. Add a `POST /api/coin/login` that accepts
`{password}`, sets the cookie if it matches, returns 401 otherwise.

**Database path:** `process.env.COIN_DB_PATH || '../coin/data/db/pipeline.db'`
resolved relative to the `web/` working directory. Open the DB read-only
(`new Database(path, { readonly: true, fileMustExist: true })`) for the read
endpoints. Mutation endpoints don't touch the DB directly — they shell out.

**Subprocess discipline:**

```ts
import { spawn } from 'node:child_process';

const py = process.env.COIN_PYTHON || '../coin/.venv/bin/python';
const child = spawn(py, ['-m', 'careerops.web_cli', ...args], {
  cwd: '../coin',
  timeout: 15_000,
});
// Buffer stdout, parse as JSON. On non-zero exit, return 500 with stderr included for debugging (only in dev).
```

15-second timeout protects the dashboard from a stuck subprocess. Stream
stderr to the Node logs but never to the client (could leak paths).

### Step 6 — Components (`web/components/lab/coin/`)

Create the directory and these files. Each is a TS React component or module.

#### `types.ts`

TS interfaces matching the SQLite shape one-to-one:

```ts
export interface Role {
  id: number;
  company: string;
  title: string;
  location: string | null;
  url: string | null;
  source: string;
  lane: string;
  status: RoleStatus;
  fit_score: number | null;
  fit_grade: string | null;
  score_stage1?: number | null;
  score_stage2?: number | null;
  comp_min: number | null;
  comp_max: number | null;
  comp_band: string | null;
  posted_at: string | null;
  discovered_at: string;
  jd_raw: string | null;
  jd_parsed: string | null;  // JSON-encoded
  notes: string | null;
  dq_reasons: string | null;  // JSON-encoded array
}

export type RoleStatus =
  | 'discovered' | 'scored' | 'resume_generated' | 'applied'
  | 'responded' | 'contact' | 'interviewing' | 'offer'
  | 'rejected' | 'withdrawn' | 'closed' | 'no_apply';

export interface RoleScoreBreakdown {
  composite: number;
  grade: string;
  dimensions: {
    [key: string]: { weight: number; raw: number; contribution: number };
  };
}

export interface Outreach {
  id: number;
  role_id: number | null;
  recipient_name: string;
  recipient_handle: string | null;
  channel: 'linkedin' | 'email' | 'twitter';
  draft: string;
  sent_at: string | null;
  reply_at: string | null;
  reply_text: string | null;
}

export interface Connection {
  id: number;
  name: string;
  company: string;
  title: string;
  linkedin_url: string | null;
  warm_score: number;  // 0-100
}

export interface Offer {
  id: number;
  company: string;
  title: string;
  base: number;
  bonus: number;
  rsu_total: number;
  rsu_years: number;
  vest_curve: 'cliff_25_25_25_25' | 'monthly_after_cliff' | 'custom';
  signing_bonus: number;
  is_active: boolean;
  is_market_anchor: boolean;
  source: 'levels.fyi' | 'glassdoor' | 'sean_received';
  captured_at: string;
}

export interface Story {
  id: string;
  lane: string;
  headline: string;
  context: string;
  metric: string;
  source_of_truth: string;  // citation
}
```

#### `CoinPage.tsx`

Top-level client component. Renders a `Tabs` strip:

- Pipeline (default)
- Discover
- Roles (full list with filters)
- Network
- Ofertas
- Stories

Tab state in a Zustand store at `web/components/lab/coin/store.ts`. Mirror
how Holo manages tab state — same naming convention, same hook shape.

Header bar shows: "Coin — Career Ops" title, a refresh button (re-fetches
dashboard), the comp floor badge ($160K base / $200K total), and a small
status chip showing total active roles + last-updated timestamp.

Header comment cites `/lab/holo` as the architecture reference and notes the
read-vs-mutate split.

#### `Kanban.tsx`

Six-column kanban: Discovered / Scored / Tailored / Applied / Interviewing /
Offer. (Maps to: `discovered` | `scored` | `resume_generated` | `applied` |
`interviewing`+`responded`+`contact` | `offer`. Rejected/withdrawn/closed/no_apply
hidden by default; toggle to reveal as a 7th "Closed" column.)

Each column:
- Header with name + count badge
- Scrollable list of `<RoleCard />` instances
- `framer-motion` `Reorder.Group` for drag-and-drop within and between columns

On drop into a different column, POST to `/api/coin/role/[id]/track` with the
new status. Show optimistic UI; revert on error with a toast.

Header comment cites `santifer/career-ops dashboard/internal/ui/screens/pipeline.go`
for the column taxonomy (MIT license).

Mobile: columns stack vertically, swipe left/right to switch active column;
drag-and-drop disabled on mobile (use a tap → action sheet to change status
instead).

#### `RoleCard.tsx`

Compact card. Shows:

- Company logo placeholder (initials in a colored circle, hash company name to color)
- Title (truncate to 1 line)
- Lane badge (color-coded: mid-market-tpm = blue, enterprise-sales-engineer = green, iot-solutions-architect = purple, revenue-ops-operator = amber)
- Fit grade letter in a circle (A/B/C/D/F, color-coded)
- Fit score number (bottom-right)
- Posted-age badge ("3d", "2w", "stale" if >30d)
- Comp band if explicit ($160-200K shown as badge)
- DQ badge if `dq_reasons` non-empty — red, "DQ" text, hover/tap shows reasons
- Click opens `<RoleDetail />` drawer

Compact: ~120px tall. 8 cards per column visible on a 1080p screen without scroll.

#### `RoleDetail.tsx`

Modal on desktop, full-screen drawer on mobile. Sections:

1. **Header:** company, title, location, lane, score, grade, source link to original posting
2. **Score breakdown:** `<ScoreChart />` — 8 horizontal bars
3. **JD:** collapsed by default ("Show JD →"); expanded shows `jd_raw` in a monospace block, syntax-light
4. **Parsed JD:** structured view of `jd_parsed` JSON — responsibilities, requirements, must-have, nice-to-have
5. **DQ reasons:** if any, red callout listing them
6. **Audit results:** if `notes` contains the audit-verdict line (per `modes/auto-pipeline.md` Step 2.7), parse and show as a labeled chip (CLEAN / NEEDS REVISION / BLOCK)
7. **PDF preview:** `<iframe src={`/api/coin/role/${id}/pdf`} />` — if 404, show "No PDF generated yet" with a "Tailor now" button
8. **Notes:** read-only history + textarea + "Append" button (POST to `/api/coin/role/[id]/notes`)
9. **Action bar (sticky bottom):**
   - Tailor (POSTs to `/api/coin/role/[id]/tailor`, shows toast: "Queued — finish in next Claude session")
   - Open in ATS (window.open to `url`)
   - Mark Applied (POSTs `track` with `status: 'applied'` — confirmation modal first because this is the real-world commitment gate)

#### `ScoreChart.tsx`

Pure-Tailwind bar chart. No charting library. Eight horizontal bars, one per
scoring dimension (whatever `score_breakdown.dimensions` keys exist). Each
bar:

- Label on left (dimension name)
- Bar width proportional to contribution (weight × raw)
- Color-coded: green if contribution > 70% of weight, amber 40-70%, red <40%
- Number on right showing `raw / weight`

Total composite shown as a separate big number above with the grade letter.

#### `DiscoverFeed.tsx`

Sortable table. Filters: A-tier only (default), date range (7d / 14d / 30d /
all), lane. Columns: Date, Company, Title, Lane, Grade, Score, Comp, Action.
Action column has a "Tailor & Open PDF" button — fires both the tailor POST
and (if PDF already exists) opens it in a new tab.

#### `NetworkView.tsx`

Two stacked tables:

- **Outreach drafts:** rows from `outreach` table where `sent_at IS NULL` —
  recipient, channel, draft preview (first 80 chars), "Send" button
  (window.open to LinkedIn message URL pre-filled if possible, or copies to
  clipboard with a toast for email)
- **Warm contacts at target companies:** join `connections` to `roles` on
  matching `company` where role is in `discovered`/`scored`/`resume_generated`
  status. Shows: name, title, company, role they could refer to, warm_score,
  LinkedIn link

#### `OfertasView.tsx`

Multi-offer side-by-side comparison. Up to 4 columns side-by-side on desktop
(stacked on mobile). Each column shows:

- Company + title header
- Source pill (sean_received / levels.fyi / glassdoor)
- Year-1 TC big number
- 3-year TC big number
- Vest curve mini-bar-chart (4 bars for 4 years, height proportional to that year's RSU release)
- Base / Bonus / RSU total / Signing bonus rows

Data fetched from `GET /api/coin/offers/compare` so the math stays in
`coin/careerops/offer_math.py`. Do NOT replicate the math in TS — that
guarantees drift the first time the user changes vest assumptions.

Highlight the best offer per row (green border on the highest base, highest
3yr TC, etc.). Show the comp floor ($160K base / $200K total) as a horizontal
reference line on the TC big-number bars.

#### `StoriesView.tsx`

Reads from `GET /api/coin/stories`. If empty (stories.yml absent, because
COIN-EXPERIENCE-DEEPDIVE hasn't shipped), shows an empty-state card:

> "No stories captured yet. Run `/coin deep-dive` in Claude to capture
> career proof points."

If populated: cards grouped by lane. Each card shows headline, context,
metric, source-of-truth citation. "Edit" link is a deep-link explanation: a
modal that says "Story editing is mode-driven — run `/coin deep-dive` in
your next Claude session to revise."

#### `AuthGate.tsx`

If password is set and cookie absent, render a centered card with a password
input. POSTs to `/api/coin/login`. On 200, reload. On 401, show inline error.

### Step 7 — Server helper (`web/components/lab/coin/server.ts`)

Server-only module (`'server-only'` import at top). Exports:

- `openDb()` — returns the better-sqlite3 instance, opened read-only
- `fetchDashboard()` — runs the dashboard queries, returns the JSON shape
- `fetchRoles(filters)` — same signature as the API endpoint
- `fetchRole(id)` — full detail
- `runWebCli(args, body?)` — spawns the subprocess, returns parsed JSON or throws

The API route handler imports from this module so there's no code duplication
between server-rendered initial state and client-fetched updates.

### Step 8 — Lab gallery registration

Edit `web/components/lab/lab-projects.ts` to add a Coin entry:

- title: "Coin"
- subtitle: "Career-ops engine"
- description: 1-2 sentences about pipeline + tailored resumes
- href: `/lab/coin`
- thumbnail: a placeholder for now (use the same approach Holo uses — emoji or simple icon)
- tags: ["career", "ai", "kanban"]

Mirror the existing Holo entry's shape exactly. The lab index page picks it
up automatically.

### Step 9 — package.json updates

Add to `web/package.json`:

```json
"dependencies": {
  "better-sqlite3": "^11.3.0"
},
"devDependencies": {
  "@types/better-sqlite3": "^7.6.11"
}
```

Run `npm install` from `web/`. If `better-sqlite3` fails to build natively,
run `npm rebuild better-sqlite3` (Sean's Mac may need Xcode CLT). Document
this fallback in the integration doc.

### Step 10 — Documentation (`web/docs/coin-integration.md`)

New file. Sections:

1. **Architecture overview** — the read-vs-mutate split, why we chose it, the diagram
2. **Local dev** — exact commands to run
3. **Auth model** — env var, cookie, sha256, no multi-user
4. **DB path resolution** — `COIN_DB_PATH` precedence, default
5. **Subprocess invocation** — `COIN_PYTHON`, working directory, timeout
6. **Vercel deploy notes** — explicitly: v1 is local-only. Production deploy
   needs a synced copy of `pipeline.db` because Vercel's filesystem is
   ephemeral. That's a separate task (COIN-WEB-DEPLOY). For now the page
   404s in production unless the env vars are set, which they shouldn't be
   for v1.
7. **PDF streaming** — the `Content-Type` requirement for iframe preview
8. **Citations** — santifer/career-ops for kanban taxonomy, /lab/holo for
   proxy pattern

### Step 11 — Manual smoke + verification

After everything compiles:

```bash
# Backend tests
cd /Users/tealizard/Documents/lab/coin/coin
.venv/bin/pytest tests/test_web_cli.py -v --tb=short

# Frontend build
cd /Users/tealizard/Documents/lab/coin/web
npm install
npm run build

# Local dev smoke
COIN_DB_PATH=../coin/data/db/pipeline.db \
COIN_PYTHON=../coin/.venv/bin/python \
npm run dev
# Open http://localhost:3000/lab/coin
```

Manually verify (check off each):

- [ ] Pipeline tab renders with real role counts
- [ ] Discover tab shows A/B-tier roles from last 7 days
- [ ] Roles tab shows the full filterable list
- [ ] Network tab shows outreach drafts + warm contacts
- [ ] Ofertas tab shows offer comparison (or empty state if no offers)
- [ ] Stories tab shows stories or the empty state
- [ ] Click a role card → detail modal opens with JD, score chart, audit chip, PDF iframe
- [ ] Drag a role from "Discovered" to "Scored" → DB row updates (verify with `sqlite3 coin/data/db/pipeline.db "SELECT id, status FROM roles ORDER BY id DESC LIMIT 5;"`)
- [ ] Click "Tailor" → toast shows queued message, marker file appears in `coin/data/tailor_pending/`
- [ ] Append a note → DB notes column grows
- [ ] DevTools mobile viewport (375x667): kanban columns stack vertically, role detail is full-screen
- [ ] No console errors, no failed network requests

## Verification

```bash
# Coin pytests
cd /Users/tealizard/Documents/lab/coin/coin
.venv/bin/pytest tests/ -q --tb=short

# Web build
cd /Users/tealizard/Documents/lab/coin/web
npm run build

# Web type check
npx tsc --noEmit

# Web lint
npm run lint
```

- [ ] All Coin pytests pass (228 baseline + Sprint 1-2 deltas + 8 new in test_web_cli.py)
- [ ] `npm run build` produces no TS errors and no Next.js build errors
- [ ] `npx tsc --noEmit` is clean
- [ ] `npm run lint` is clean
- [ ] Manual smoke checklist above all checked
- [ ] PDF preview iframe loads for at least one role with a generated PDF
- [ ] Mobile viewport renders correctly

## Definition of Done

- [ ] `coin/careerops/web_cli.py` exists with three subcommands
- [ ] `coin/tests/test_web_cli.py` has 8 passing tests
- [ ] `web/app/lab/coin/page.tsx` renders dashboard with SSR initial data
- [ ] `web/app/lab/coin/layout.tsx` exists with metadata
- [ ] `web/app/api/coin/[...slug]/route.ts` handles all read + mutate endpoints
- [ ] All 9 components in `web/components/lab/coin/` exist and render
- [ ] `web/components/lab/coin/server.ts` is the single source of DB access
- [ ] `web/components/lab/lab-projects.ts` registers the Coin tile
- [ ] `web/package.json` has `better-sqlite3` and types
- [ ] `web/docs/coin-integration.md` documents the architecture
- [ ] All 6 tabs render and function
- [ ] Drag-and-drop status transitions persist to SQLite
- [ ] PDF preview works via iframe
- [ ] Mobile viewport stacks correctly
- [ ] Header comments cite santifer/career-ops (Kanban) and /lab/holo (route + page)
- [ ] No regressions in `pytest tests/` or `npm run build`
- [ ] `docs/state/project-state.md` updated with this surface

## Out of scope (future tasks)

Explicitly NOT in this task — punt to follow-ups:

- **Production deploy with synced DB** (COIN-WEB-DEPLOY) — Vercel needs the
  SQLite file shipped via blob storage or replaced with Postgres
- **Multi-user / sharing tokens** (COIN-WEB-SHARE) — read-only share links
  per role, expiring
- **Live tailor invocation from web** (COIN-WEB-TAILOR-LIVE) — would need
  the host LLM, so requires either Anthropic API (which Coin forbids) or a
  Claude Code background hook
- **Charting library** — v1 uses pure Tailwind bars. If we need stacked
  bars or time series, swap in Recharts later.
- **Real-time updates** — no WebSocket / SSE in v1. Manual refresh button.
- **Resume editing in the browser** — stays mode-driven (`/coin tailor`)

## Style notes

- Cite `santifer/career-ops dashboard/internal/ui/screens/pipeline.go` (MIT) in `Kanban.tsx` header for the column taxonomy
- Cite `web/app/lab/holo/page.tsx` and `web/components/lab/holo/HoloPage.tsx` as the architecture reference in `route.ts` and `CoinPage.tsx` headers
- Be explicit in code comments about the Python-vs-Node split: read = Node, mutate = Python subprocess. State why (one source of truth for business logic).
- The PDF endpoint MUST set `Content-Type: application/pdf` and use `fs.createReadStream` so the iframe preview works without download prompt
- Local dev skips auth (no env var = no gate); deploy gates via `COIN_WEB_PASSWORD`. NO multi-user yet — single shared password
- Use lucide-react icons throughout: Briefcase (Pipeline), Target (Discover), FileText (Roles), Users (Network), DollarSign (Ofertas), BookOpen (Stories), Settings (header)
- Tailwind spacing: stick to 4/8/12/16 multiples for vertical rhythm
- Dark theme primary; light-mode toggle is out of scope for v1

## Rollback

```bash
# Backend
rm /Users/tealizard/Documents/lab/coin/coin/careerops/web_cli.py
rm /Users/tealizard/Documents/lab/coin/coin/tests/test_web_cli.py

# Frontend
rm -rf /Users/tealizard/Documents/lab/coin/web/app/lab/coin
rm -rf /Users/tealizard/Documents/lab/coin/web/app/api/coin
rm -rf /Users/tealizard/Documents/lab/coin/web/components/lab/coin
rm /Users/tealizard/Documents/lab/coin/web/docs/coin-integration.md

# Revert package.json + lock
cd /Users/tealizard/Documents/lab/coin/web
git checkout package.json package-lock.json
npm install

# Revert lab gallery
cd /Users/tealizard/Documents/lab/coin
git checkout web/components/lab/lab-projects.ts
git checkout docs/state/project-state.md
```

The Coin Python pipeline is untouched by rollback — `web_cli.py` is purely
additive and removing it doesn't affect any existing mode or script. The
`/lab/holo` page and the marketing site are untouched throughout. This task
is fully reversible.
