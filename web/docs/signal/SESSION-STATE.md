# SIGNAL — session state & next-session handoff

**Last session ended:** 2026-04-24
**Live URL:** https://www.handoffpack.com/lab/signal (rewrites to this repo's deployment when `LAB_URL` env var is set on handoffpack-www in Vercel)
**This repo:** [lifestoryco/lab](https://github.com/lifestoryco/lab) — `web/` is the Next.js 14 app
**Default mode:** Cage (puzzle). Free-play (Zen) accessible via bottom-right title link.

---

## Repo migration context (read first)

`/lab/*` was historically served from `lifestoryco/handoffpack-www`. As of `0c00ca3` on this repo (2026-04-24) the full lab tree was imported here under `web/`. handoffpack-www now has env-gated rewrites (`23df0f8` on that repo) so when `LAB_URL` is set in Vercel, all `/lab/*` traffic proxies to this deployment instead.

**Current cutover state:**
- **Code:** lives in BOTH repos; this repo is the active development target.
- **Vercel:** handoffpack-www still serves `/lab/*` from its own `app/lab` until `LAB_URL` is flipped.
- **Next move (per the rewrite commit):** flip `LAB_URL` → verify rewrites work → follow-up PR removes `app/lab` + `components/lab` from handoffpack-www so this repo becomes the sole source of truth.

**File paths in this doc** are relative to `web/` unless prefixed with `(handoffpack-www)`.

---

## What SIGNAL is (right now)

A Next.js 14 + Tone.js + React Three Fiber music-puzzle game at `/lab/signal`. Two modes:

- **Cage Mode (default).** 15 levels across 5 biomes. Trap a moving "monster" (obelisk pawn with red eyes) inside placed-block walls before it escapes to a grid edge. Music is generated in real time: four-on-the-floor kick drum (per-world tuned), a 4-note monster motif ostinato, and per-biome pentatonic scales on user placements. Every placement Thumper-quantizes to a 16th-note. BPM is the difficulty dial — it controls both the music tempo and the monster's step cadence via a single `onBeat` subscription to `Tone.Transport`.
- **Zen / Free Play.** Original meditative 16×16 grid, chain-reaction cascades, Maezumi Roshi closing. Byte-for-byte unchanged from the art-piece ship. Session length 2:30 per biome, 5 biomes.

Everything shares the same audioEngine, biome palettes, particle/bloom/camera FX, share hash, and OG-image route.

---

## Session history (in handoffpack-www, before import)

These commits are on `lifestoryco/handoffpack-www` `main`. They were imported here in a single squash via `0c00ca3 feat(web): add Next.js 14 app hosting all handoffpack.com/lab/* pages`.

| # | Commit (handoffpack-www) | What |
|---|---|---|
| 1 | `c8b9b81` | SIG-1/2/3 ship-prep: mobile BPM, chain celebration, pacing, original Broadcast Mode, shareable result, analytics, narrative rewrite |
| 2 | `04a2ade` | W1/W2/W3 task prompts moved to complete/, narrative candidates + launch copy |
| 3 | `b87e5ce` | Pre-existing Vercel build unblock: added missing `CONSULTANT_VALUE` to lib/constants, excluded `scripts/` from TS build |
| 4 | `005adbb` | Security patches from /code-review: decoder bounds, hash-length caps on OG route + /s/[hash] |
| 5 | `3cd7c87` | Cage pivot — engine foundation (enclosure BFS, monster AI, levels, useCage hook, PlayMode widens, store additions) |
| 6 | `49df391` | Cage scene + HUD (MonsterPawn, PathHintVisualizer, CageHud) |
| 7 | `9f29b4f` | Cage wiring + Broadcast removal (title toggle, SignalPage, shareState v2, CageHud replaces BroadcastHud; PlayMode narrows to `'zen' \| 'cage'`) |
| 8 | `0d5fae9` | Audio + feel overhaul: BPM accuracy fix (Tone.Transport onBeat subscription), kick drum, monster motif, level flourish, monster sink animation on solve AND fail, full-screen tap-to-continue replacing the tiny portal, Thumper-quantized placement |
| 9 | `ff040b4` | 15-level progression across 5 biomes, seeded tutorials (1-1: 3 walls pre-placed; 1-2: 2 walls; 1-3: 1 wall), per-level BPM ramp, instant retry on fail, level-ID intro overlay |
| 10 | `8d3f4b4` | Cage default on title, Free-play link bottom-right, "SPEED · slow/steady/fast/frantic" label, larger MonsterPawn, drei `<Sparkles>` cage-solve celebration |
| 11 | `ded47d5` | Original session-state handoff doc (committed to handoffpack-www; THIS file is the lab-repo equivalent) |

Plus the lab-repo-side commits:

| Commit (lifestoryco/lab) | What |
|---|---|
| `0c00ca3` | feat(web): add Next.js 14 app hosting all handoffpack.com/lab/* pages — squash import |
| (this commit) | docs(signal): port SESSION-STATE handoff for SIGNAL development continuity |

---

## Current file surface (in this repo, under `web/`)

```
web/
├── app/api/og/signal/route.tsx              — 1200×630 OG image route (edge runtime)
├── app/lab/signal/page.tsx                  — route + metadata
├── app/lab/signal/layout.tsx                — Cormorant Garamond font
├── app/lab/signal/s/[hash]/page.tsx         — shared-session viewer
│
└── components/lab/signal/
    ├── SignalPage.tsx                       — top-level page, mounts all hooks/overlays
    │
    ├── audio/
    │   ├── audioEngine.ts                   — Tone.js, kick drum, monster motif,
    │   │                                      level flourish, onBeat subscribers
    │   └── scales.ts                        — pentatonic scale math
    │
    ├── cage/                                — Cage-specific engine
    │   ├── enclosure.ts                     — isEnclosed / nextStepTowardEdge / predictPath
    │   ├── levels.ts                        — 15 level specs, BPM ramp, seed blocks
    │   └── monster.ts                       — stepMonster rule dispatch
    │
    ├── engine/
    │   ├── useCage.ts                       — cage runtime hook (onBeat subscriber)
    │   ├── useChainReaction.ts              — BFS cascade on block placement
    │   └── useGameStore.ts                  — Zustand store, PlayMode, mode persistence
    │
    ├── postprocessing/
    │   └── PostFXPipeline.tsx               — bloom / chromatic aberration / vignette / grain
    │
    ├── scene/                               — R3F scene components
    │   ├── IsometricScene.tsx               — Canvas root, camera, click handlers
    │   ├── BackgroundLayers.tsx
    │   ├── GridPlane.tsx                    — tappable instanced grid
    │   ├── PlacedBlocks.tsx
    │   ├── PlayheadBeam.tsx
    │   ├── Lighting.tsx
    │   ├── Particles.tsx                    — dust motes + placement burst pool
    │   ├── GestureControls.tsx              — pinch-zoom + two-finger pan
    │   ├── Portal.tsx                       — (mostly decorative; LevelCompleteOverlay handles advancement)
    │   ├── Monster.tsx                      — original Zen-gameover obelisk
    │   ├── MonsterPawn.tsx                  — in-play Cage pawn (rise + sink + flash)
    │   ├── PathHintVisualizer.tsx           — glows 3 cells of monster's predicted path
    │   ├── CageCelebration.tsx              — drei Sparkles burst on solve
    │   ├── SceneErrorBoundary.tsx           — WebGL fallback
    │   └── SceneFallback.tsx                — "requires a modern browser" copy
    │
    ├── ui/
    │   ├── TitleScreen.tsx                  — SIGNAL wordmark, mode pill, free-play link
    │   ├── InstrumentSelector.tsx           — BPM pad (tap-tempo + drag), SPEED label
    │   ├── NarrativeOverlays.tsx            — in-play whispers (Zen + Cage)
    │   ├── CageHud.tsx                      — level-ID intro, timer bar, rule hint, fail whisper
    │   ├── LevelCompleteOverlay.tsx         — full-screen "Caged. / Tap to continue"
    │   ├── CageFailOverlay.tsx              — Retry / Back to menu
    │   ├── WorldTransition.tsx              — biome-change ceremony
    │   └── ResultScreen.tsx                 — final composition, Share/Save, /s/[hash] viewer
    │
    ├── utils/
    │   ├── analytics.ts                     — PostHog track() wrapper
    │   ├── easing.ts
    │   ├── isoMath.ts                       — grid math, blockKey, gridToWorld
    │   ├── perlin.ts                        — 2D noise for dust motes
    │   └── shareState.ts                    — v1+v2 share-hash codec
    │
    └── worlds/
        ├── biomeConfigs.ts                  — 5 biome palette + scale + tempo + narrative
        └── storyFragments.ts                — transition copy + Maezumi closing
```

---

## What's still open (prioritized)

### P0 — gameplay / feel tuning after playtest

Real-device feedback required. None are bugs, all are knob-turns.

1. **Monster motif volume / timbre.** Currently plays at `-10dB` on effectsBus with FMSynth (harmonicity 1.25, square modulation). Tune in `web/components/lab/signal/audio/audioEngine.ts` `motifSynth` config.
2. **Kick drum punch.** `MembraneSynth` at `-3dB` equivalent via `Gain(0.75)`. May need sidechain-style ducking under placements, or swap to a 2-osc thump.
3. **Per-level `beatsPerStep`.** Current values: 1-1 ∞ · 2-1 16 · 2-2 12 · 2-3 10 · 3-1 10 · 3-2 8 · 3-3 8 · 4-1 8 · 4-2 7 · 4-3 6 · silence ∞. Tune in `web/components/lab/signal/cage/levels.ts` after watching real players fail.
4. **Placement-note duration/velocity.** Currently `'8n'` duration at 0.68 velocity. Might want shorter decay + louder attack for puzzle-feel.

### P1 — feature gaps you asked for that are not yet shipped

1. **Rebrand to PULSE** (or alternate). Held for explicit approval. Touch points: `web/app/lab/signal/layout.tsx`, `web/app/lab/signal/page.tsx` metadata, `web/components/lab/signal/ui/TitleScreen.tsx` wordmark string, `web/app/api/og/signal/route.tsx` hero text, OG meta in `web/app/lab/signal/s/[hash]/page.tsx`. URL path stays `/lab/signal` to preserve any existing share links.
2. **Sword / items for middle stages.** Unstarted. Rough scope: new placeable types with different behaviours (sword = kills monster on adjacency; warp block = teleports monster; mirror = reflects motif audio back). Would add a `placeable: 'wall' | 'sword' | 'warp'` field on `PlacedBlock` plus a selector UI. Estimate: 2-3 days.
3. **Bottom-row drum tracks.** User proposed "grid cells in the bottom row play drum sounds." Deferred. Would split `row === GRID_ROWS - 1` to map to kick/snare/hat/clap instead of pitch.
4. **Per-world celebration animations.** Sparkles is a start. Distinct celebrations per biome candidates: rising-water shimmer for The Deep; falling-leaves for The Garden; radial-sunburst for The Truth. Research drei (`<Trail>`, `<Float>`, `<MeshTransmissionMaterial>`) or `wawa-vfx` for variety.
5. **Second /code-review pass.** The previous pass only got Security results (3 other agents were rejected mid-run). Logic/Architecture/UX never ran.

### P2 — known-but-not-critical bugs

1. **`matchMedia` call inside `useFrame`** at `web/components/lab/signal/postprocessing/PostFXPipeline.tsx` (~line 45). Allocates a MediaQueryList every frame. Hoist into a ref set once via `useEffect`.
2. **`signal_biome_complete` never fires for the final biome** in `web/components/lab/signal/SignalPage.tsx`. Currently gated on `gamePhase === 'title' && worldIndex > 0` — but the final biome goes `playing → complete`, never through `title`. Add a branch that fires on `gamePhase === 'complete'` for the last biome too.
3. **`encodeShareState` memoization** in ResultScreen busts on every render because `state` is a new object each SignalPage render. Wrap SignalPage's `sessionSummary` in a `useMemo` with stable deps.
4. **`touchAction: 'none'` on the BPM button** doesn't stop the page from scrolling on some Android browsers during the initial hold. Consider adding `user-select: none` globally on `body` while `gamePhase === 'playing'`.

### P3 — nice-to-haves

- Seed-based level shuffling for replayability.
- Per-level "best time" + "fewest taps" local leaderboard (localStorage).
- Haptic feedback on mobile: `navigator.vibrate(30)` on placement + heavy on solve/fail.
- PWA manifest — save to home screen.

### P0.5 — repo cutover

- **Flip `LAB_URL` env var** in Vercel for handoffpack-www to point at this repo's Vercel deployment.
- **Verify rewrites work** by visiting `/lab/signal` on handoffpack.com and confirming it serves from the new deployment.
- **Follow-up PR on handoffpack-www:** delete `app/lab` + `components/lab` directories (now redundant).
- **Verify `docs/tasks/signal/SESSION-STATE.md` on handoffpack-www** is either deleted or marked superseded (this doc replaces it).

---

## Local dev quick-start (this repo)

```bash
cd /Users/tealizard/Documents/lab/web
npm install                # if first time
npm run dev                # http://localhost:3000/lab/signal
npx tsc --noEmit           # 0 errors expected
npm run build              # full build; catches edge-runtime OG route issues
```

**PostHog project:** `HandoffPack Marketing` (id 320389). Events to watch:
- `signal_entered` / `signal_cage_started` / `signal_cage_solved` / `signal_cage_escaped`
- `signal_session_end` with `completed=true` for full-arc wins
- `signal_result_shared` / `signal_shared_url_opened` for viral loop health

---

## Decisions made this session (post-pivot)

1. **Cage replaces Broadcast.** Pure puzzle mode. `'broadcast'` typing removed; v1 share URLs with `mode=1` auto-upgrade to `'cage'` on decode.
2. **15 levels, not 5.** Mario 1-1 style with seeded tutorials.
3. **Cage is the default mode.** Zen reachable via small italic link bottom-right.
4. **BPM IS the difficulty dial.** Per-level ramp 80 → 160. Monster step cadence derives from BPM × beatsPerStep.
5. **No external sample packs.** All audio Tone.js-native (MembraneSynth + PolySynth). Keeps bundle small.
6. **Synesthetic celebration stack.** Cage solve = camera breath + bloom bump + particle burst + audio swell + drei Sparkles fired together from one `triggerChain` call.
7. **Full-screen tap-to-continue** replaces tiny portal click target. 10s auto-advance.
8. **Instant retry on fail.** No menu round-trip. Super Meat Boy pattern.
9. **Repo migration.** SIGNAL lives in `lifestoryco/lab/web/` going forward; handoffpack-www becomes the marketing shell with env-gated rewrites.

---

## First three moves for the next session

1. **Real-device playtest on the deployed lab Vercel app.** Walk 1-1 → 1-3 (tutorial) → 2-1 → any level with split or silence. Note kick volume, motif droning, BPM feel, Sparkles intensity, tap-to-continue timing.
2. **Decide on rebrand.** PULSE / LOOP / REFRAIN / TRAP / keep SIGNAL. Single small commit when picked.
3. **Pick next feature wave.** Options ranked by impact:
   - Sword + items system (~2-3 days, biggest new mechanic)
   - Per-world celebration variety (~1 day, uses drei)
   - Analytics/perf fixes from P2 list (~2 hours)
   - Second full /code-review (reveals more work)
   - **Repo cutover** (P0.5) is independent work — can happen in parallel or in any order with the above.

---

## Code-location index for common next-session questions

| Question | File (under `web/`) |
|---|---|
| Where does the monster actually move? | `components/lab/signal/cage/monster.ts` + `engine/useCage.ts` (onBeat subscriber) |
| Where is the kick drum? | `components/lab/signal/audio/audioEngine.ts` — `kick` MembraneSynth + `KICK_PITCH_BY_WORLD` |
| How do I add a new level? | `components/lab/signal/cage/levels.ts` — push a `CageLevel` to `CAGE_LEVELS` |
| Why does BPM feel right now? | `onBeat(fn)` in `audioEngine.ts` runs on `Tone.Transport.scheduleRepeat('4n')`. Monster steps when `beatIdx % level.beatsPerStep === 0` |
| How does enclosure detection work? | `components/lab/signal/cage/enclosure.ts` `isEnclosed()` — BFS flood from monster cell through empty cells, returns trapped=true if no edge reached |
| Why do shares still work after the pivot? | `components/lab/signal/utils/shareState.ts` — v2 encoder + v1 decoder kept for backwards compat, legacy `mode=1 (broadcast)` upgrades to `cage` |
| Where does the Sparkles burst fire? | `components/lab/signal/scene/CageCelebration.tsx` — subscribes to `cageLastResult.solved === true` |
| Where are the rewrites that route to this repo? | `(handoffpack-www)/next.config.js` `rewrites()` function — gated on `LAB_URL` env var |
