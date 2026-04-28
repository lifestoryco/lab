# `/lab/coin` — Career Ops dashboard

> **Read first:** `/Users/tealizard/Documents/lab/CLAUDE.md` for the two-repo
> topology and the rule about never `vercel link`-ing this app to `handoffpack-www`.

## What this is

A Next.js dashboard over Sean's COIN career-ops pipeline. Surfaces the SQLite DB
(`coin/data/db/pipeline.db`) read-only and routes mutations through a Python
subprocess (`careerops.web_cli`) that's the source of truth for state-machine
validation, comp math, and tailoring.

Six tabs: **Pipeline** (kanban with drag-and-drop), **Discover** (filtered feed),
**Roles** (grid), **Network** (outreach drafts), **Ofertas** (offer comparison),
**Stories** (raw `stories.yml`).

Gated behind `COIN_WEB_PASSWORD` via `web/middleware.ts`. Login at
`/lab/coin/login` sets a `coin_auth` cookie.

## Local-only by design (mutations)

| Capability | Local dev | Vercel deploy |
|---|---|---|
| Read dashboard / pipeline / roles / offers / stories | ✅ from `coin/data/db/pipeline.db` (or env override) | ✅ from bundled `web/data/coin/pipeline.db` snapshot |
| Track a role to a new status | ✅ via `careerops.web_cli` | ❌ returns 503 — use local CLI |
| Queue a tailored resume build | ✅ writes marker file | ❌ returns 503 |
| Append a note | ✅ updates DB | ❌ returns 503 |

The "read on Vercel" path is supported because `web/data/coin/pipeline.db` is
committed to the repo as a snapshot. **Refresh it before a deploy** if you want
the prod dashboard to reflect recent local discover/track activity:

```bash
cp coin/data/db/pipeline.db web/data/coin/pipeline.db
git add web/data/coin/pipeline.db
git commit -m "chore(coin): refresh DB snapshot for deploy"
```

`next.config.js` has an `experimental.outputFileTracingIncludes` entry that
explicitly bundles `data/coin/**/*` into the `/api/coin/*` and `/lab/coin/*`
serverless function output. Don't remove it — without it the deploy will boot
with no DB and show empty state.

## Why mutations are 503 on Vercel

`careerops.web_cli` is a Python subprocess. Vercel serverless functions don't
have Python at the runtime path, the SQLite DB on Vercel is read-only (deploys
are immutable), and even if both were solved, the COIN state machine in
`careerops/pipeline.py` is the canonical validator. Deploying a parallel
JS-side mutation path would split the source of truth and cause drift.

If you ever want public mutations, the smallest viable port is:
1. Move pipeline.db to a hosted Postgres (Supabase / Neon / Turso)
2. Replace `better-sqlite3` calls in `server.ts` with the Postgres client
3. Run `careerops.web_cli` as a long-lived Python service on Railway/Fly,
   exposed to the Next.js app via HTTP

That's a real project. Not in scope for the local-tool-on-public-domain era.

## Files

```
app/
├── lab/coin/
│   ├── page.tsx              SSR shell, fetches initial dashboard via server.ts
│   ├── layout.tsx            metadata only
│   └── login/page.tsx        password form (Suspense for useSearchParams)
└── api/coin/[...slug]/
    └── route.ts              GET (read) + POST (mutate); 503 on read-only deploys

components/lab/coin/
├── CoinPage.tsx              top-level client; tab nav, mutate helper, error toast
├── Kanban.tsx                7 columns including action-only "Resume Builder"
│                             and "Not a Fit"; drag-and-drop via framer-motion
├── DiscoverFeed.tsx          filtered grid by lane × age window
├── NetworkView.tsx           outreach drafts table
├── OfertasView.tsx           offer comparison cards
├── StoriesView.tsx           raw stories.yml viewer
├── RoleCard.tsx              compact card with company logo, grade, comp, link to JD
├── RoleDetail.tsx            modal with score breakdown, JD toggle, PDF, notes
├── ScoreChart.tsx            horizontal bars (no chart library)
├── server.ts                 better-sqlite3 + child_process.spawn glue
├── store.ts                  zustand store for tab/selection state
└── types.ts                  shared interfaces
```

## Drag-and-drop semantics

| Column | Drop action |
|---|---|
| Discovered / Scored / Tailored / Applied / Interviewing / Offer | `onTrack(id, statuses[0])` — moves to that status |
| **Resume Builder** | `onTailor(id)` — enqueues a tailor job; role stays in current column |
| **Not a Fit** | `onTrack(id, 'no_apply', '[user_dismissed:not_a_fit]')` — terminal status with note tag for future scoring tuning |

The note tag `[user_dismissed:not_a_fit]` is intentionally a parseable token so a
future scoring iteration can mine the rejection corpus. Don't change the format
without updating any consumer in `careerops/score.py` or `modes/patterns.md`.

## Adding a new tab

1. Add the tab id to `Tab` union in `CoinPage.tsx`
2. Add an entry to `TABS`
3. Create the view component in this directory
4. Add a GET handler in `app/api/coin/[...slug]/route.ts` if new data is needed
5. Add a server helper in `server.ts` if SSR is needed

## Adding a new kanban column

Edit `Kanban.tsx::COLUMNS`. For status-pure columns, just add `{id, label,
statuses, color}`. For action-only columns (like Resume Builder), add
`action: 'queue_tailor' | 'reject_not_fit'` and an empty `statuses` array, then
extend `handleDrop` with the action branch. Don't forget to keep `id` in sync
with the dispatch in `handleDrop` — otherwise drops silently no-op.

## Common bugs to not reintroduce

- **Default kanban tab on mobile** must compute the largest non-empty column at
  render. Hard-coding to 0 lands users on "Discovered" which is almost always
  empty (roles get scored at discover time).
- **`fileMustExist: true`** on the better-sqlite3 constructor crashes the SSR
  if the DB isn't present. Use the `openDb()` helper in `server.ts` which
  returns null and lets callers degrade gracefully.
- **`server-only`** import in `server.ts` is required — without it, webpack
  will try to bundle native `better-sqlite3` into the client and the route
  will silently 404. The package is also listed in
  `next.config.js::experimental.serverComponentsExternalPackages`.
