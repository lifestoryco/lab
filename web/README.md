# Lab Web

Sean's Lab — interactive art + tools. Next.js 14 app. Serves `handoffpack.com/lab/*` via Vercel rewrites from `www.handoffpack.com`.

## Projects

- `/lab` — gallery index (`app/lab/page.tsx`)
- `/lab/acid` — 33 living formulas rendered in ASCII light
- `/lab/aion` — radial time / op-art webcam piece
- `/lab/holo` — Pokémon TCG price intelligence terminal (frontend; Python backend lives at `../holo/`)
- `/lab/signal` — isometric R3F + Tone.js generative world
- `/lab/shrine` — contemplative archive of deceased Buddhist masters

## Dev

```bash
cd web
npm install
npm run dev
```

Opens at http://localhost:3000 which redirects to `/lab`.

## Deploy

Separate Vercel project at `lab.handoffpack.com`. `www.handoffpack.com/lab/*` rewrites here via the main site's `next.config.js`.

## Design system

All design tokens are in `app/globals.css` — mirrored 1:1 from `handoffpack-www` to keep light/dark themes identical. Do not diverge. Changes land in both repos.
