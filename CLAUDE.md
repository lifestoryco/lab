# lab — Claude Code session brief

This repo (`lifestoryco/lab`, working tree at `/Users/tealizard/Documents/lab/`)
hosts Sean's interactive lab projects. Read this once at session start. Don't
trust your priors about what lives where — the layout is unusual.

## Repo map

```
lab/
├── coin/                 Career-ops engine (Python). Modal /coin skill, scrapers,
│                         scoring, tailoring, scheduler. Owns coin/data/db/pipeline.db.
├── web/                  Next.js 14 app for the lab gallery + dynamic project pages
│                         (acid, aion, signal, holo, shrine, coin). Deploys to its
│                         own Vercel project (lab-lifestoryco). NOT to handoffpack-www.
├── santos-coy-legacy/    Static HTML exhibit. ⚠ Authoritative copy lives in the
│                         sibling repo lifestoryco/handoffpack-www, NOT here. Any
│                         santos-coy-legacy/ inside this repo is legacy debris from
│                         older worktrees and may drift.
└── docs/                 Project state, advisory-board minutes, task prompts.
```

## ⚠ Two-repo deployment topology — read before deploying anything

**`www.handoffpack.com` is served by TWO repos via a Vercel rewrite seam.**

| Repo | GitHub | Vercel project | Owns | URL paths |
|---|---|---|---|---|
| `lifestoryco/handoffpack-www` | `~/Documents/handoffpack-www` | `handoffpack-www` | marketing shell, `/lab/coy` static, OG images, gallery card metadata | `www.handoffpack.com/*` |
| `lifestoryco/lab` (this repo) | `~/Documents/lab` | `lab-lifestoryco` (created 2026-04-28) | dynamic `/lab/*` pages | served at `lab-lifestoryco-...vercel.app/*`; surfaced at `www.handoffpack.com/lab/*` via `LAB_URL` rewrite on the `handoffpack-www` Vercel env |

The seam is `next.config.js` rewrites in `handoffpack-www`:

```js
// inside handoffpack-www, NOT this repo:
async rewrites() {
  // /lab/coy is always served from handoffpack-www's own /public/lab/coy/.
  // Other /lab/* paths rewrite to LAB_URL when set (i.e. to this repo's deploy).
}
```

### Three things must agree, or the lab pages render broken

This is non-obvious and bit us once already (2026-04-28: /lab/coin shipped looking like a bulleted text dump because Tailwind/JS chunks 404'd). The rewrite proxies HTML fine, but Next.js asset URLs (`/_next/static/css/<hash>.css`, JS chunks) live in a per-app namespace. www has its own `/_next` and won't have lab's hashes.

Fix requires three coordinated settings:

1. **Lab side — `assetPrefix`:** `web/next.config.js` reads `LAB_PUBLIC_URL` and emits absolute asset URLs pointing back at the canonical lab origin. Set `LAB_PUBLIC_URL=https://lab-lifestoryco.vercel.app` on the lab-lifestoryco Vercel **production** env. Local dev leaves it unset → relative paths still work.
2. **www side — CSP whitelist:** `handoffpack-www/next.config.js` CSP must allow `https://lab-lifestoryco.vercel.app` in `script-src`, `style-src`, `font-src`, `img-src`, and `connect-src`. Without this, the browser blocks the cross-origin assets (CSP error in console).
3. **Smoke test:** `web/scripts/postdeploy-smoke.sh` curls a known `/_next/static/css/...` reference through both origins and exits non-zero on 404. Run after every lab deploy that could rotate hashes; CI-friendly.

If `/lab/coin` (or any `/lab/*`) renders unstyled in the future, check (1) and (2) first.

### Hard rules for Claude sessions in this repo

1. **NEVER `vercel link` or `vercel deploy` `lab/web/` to the `handoffpack-www` Vercel project.** It will overwrite the live marketing site. The `web/.vercel/project.json` MUST point to `lab-lifestoryco`. The `web/scripts/predeploy-check.sh` script enforces this — do not delete it.
2. **NEVER copy `/lab/coy/*` files into this repo.** Coy is owned by `handoffpack-www`. If you see `web/public/lab/coy/` here, it's stale debris — delete it.
3. **NEVER edit files inside `~/Documents/handoffpack-www/`.** That's a separate repo with its own session. Cross-repo work goes through GitHub PRs, not local edits.
4. **The COIN web UI in `web/components/lab/coin/` is local-dev-friendly only.** It reads `coin/data/db/pipeline.db` via `better-sqlite3` and writes via a Python subprocess (`careerops.web_cli`). On Vercel: a committed snapshot of pipeline.db at `web/data/coin/pipeline.db` powers the read-only dashboard; mutation endpoints return 503. To refresh the snapshot, run `cp coin/data/db/pipeline.db web/data/coin/pipeline.db` then commit.

## Local commands you'll actually run

```bash
# Start the lab dev server (defaults port 3103)
cd web && npm run dev

# Build verify
cd web && npm run build

# COIN tests (Python)
cd coin && .venv/bin/pytest tests/ -q

# Sync the bundled COIN DB snapshot before a deploy
cp coin/data/db/pipeline.db web/data/coin/pipeline.db
```

## Where state lives

- **Roadmap + session log:** `coin/docs/state/project-state.md` (yes, even for non-coin work — it's the de-facto session log for the whole lab repo right now)
- **Task prompts:** `coin/docs/tasks/prompts/{pending,complete}/*.md`
- **Worktrees:** `.claude/worktrees/<name>/` for the lab repo, `coin/.claude/worktrees/<name>/` for coin-specific sessions

## Common gotchas

- **Path of least resistance is wrong:** the lab gallery's COIN card (`web/components/lab/lab-projects.ts`) links to `/lab/coin`. On Vercel that loads but mutations fail with 503. That's intentional — see Tier 4 in earlier session notes.
- **`coin/` and `web/` look like sibling repos but share one `.git`.** `git status` from anywhere in the tree shows everything.
- **Dev-server port conflicts:** the lab web server uses 3103. If `lsof -i :3103` shows another process, it's likely a stale `next dev` from a prior worktree. `pkill -f "next dev -p 3103"` and restart.

## Sibling-repo cheatsheet

If you actually need to coordinate changes with `handoffpack-www`, do it through that repo's own session — open a fresh Claude window in `~/Documents/handoffpack-www/`. Don't reach across the filesystem.
