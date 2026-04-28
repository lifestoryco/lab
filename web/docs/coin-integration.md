# Coin — Web Integration

## Overview

Coin is the career-ops dashboard at `/lab/coin`. It provides a read/write UI over the SQLite pipeline DB managed by the `careerops` Python package.

## Data Flow

```
SQLite (pipeline.db)
  ↓ read (SSR)         better-sqlite3 via server.ts
  ↓ read (client)      GET /api/coin/*
  ↓ mutate             POST /api/coin/role/[id]/{track,tailor,notes}
                         → child_process.spawn python -m careerops.web_cli
```

Python stays the single source of truth for state-machine validation.

## Environment Variables

| Var | Default | Purpose |
|-----|---------|---------|
| `COIN_DB_PATH` | `~/Documents/lab/coin/data/db/pipeline.db` | Absolute path to SQLite DB |
| `COIN_WEB_PASSWORD` | *(unset = open)* | Cookie-based auth for production |

In local dev neither variable is required — the DB path is resolved relative to the repo.

## API Routes (`/api/coin/[...slug]`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/coin/dashboard` | Pipeline counts + top 5 roles |
| GET | `/api/coin/roles?limit=N&lane=X` | Role list with fit scores |
| GET | `/api/coin/role/[id]` | Single role detail |
| GET | `/api/coin/role/[id]/pdf` | Streams tailored resume PDF |
| GET | `/api/coin/offers` | Active + market-anchor offers |
| GET | `/api/coin/outreach` | Outreach drafts |
| GET | `/api/coin/stories` | Raw stories.yml text |
| POST | `/api/coin/role/[id]/track` | `{ status, note? }` → pipeline state change |
| POST | `/api/coin/role/[id]/tailor` | Enqueues tailor job (writes marker file) |
| POST | `/api/coin/role/[id]/notes` | `{ text }` → appends note |

## Components

```
CoinPage.tsx        Top-level client component; 6-tab nav
├── Kanban.tsx      Pipeline board (framer-motion DnD)
├── DiscoverFeed.tsx  Filtered role grid
├── NetworkView.tsx   Outreach drafts
├── OfertasView.tsx   Offer comparison cards
├── StoriesView.tsx   Raw YAML viewer
├── RoleCard.tsx    Compact role tile
├── RoleDetail.tsx  Modal with score breakdown + actions
└── ScoreChart.tsx  Horizontal bar chart (pure Tailwind)
```

State: Zustand store (`store.ts`) — tab selection, selected role, loading flag.

## Adding a New Tab

1. Add the tab ID to the `Tab` type in `CoinPage.tsx`
2. Add an entry to the `TABS` array
3. Create a new view component in `components/lab/coin/`
4. Add a GET handler in the API route if new data is needed
5. Add a server helper in `server.ts` if SSR is needed

## Running Locally

```bash
cd web
COIN_DB_PATH=/path/to/pipeline.db npm run dev
```

Or without the env var — the default path resolution handles a standard local checkout.
