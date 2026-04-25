# SIGNAL — session state & next-session handoff

**Last session ended:** 2026-04-25

---

## What Was Just Done (2026-04-25)

### Specials + celebrations + P2 fixes ✅ COMPLETE

**New files:**
- `cage/specials.ts` — per-world special-item registry + STUN/REVEAL constants
- `ui/SpecialButton.tsx` — bottom-left ability button with flash + keyboard shortcut
- `scene/RevealMarker.tsx` — lantern halo on the silence cell

**Modified:**
- P2 quartet: matchMedia hoist in PostFXPipeline, final-biome `signal_biome_complete`, sessionSummary memo, body lock during play
- Per-world specials in `engine/useGameStore.ts` + wired into `useCage.ts`
- 5 distinct biome celebration variants in `scene/CageCelebration.tsx`

**Commits:**
- `0789643` — feat(web/signal): per-world special items + celebrations + P2 fixes
- `c72637b` — refactor(web/signal): apply code-review fixes (a11y zoom, contrast, GPU buffer churn, etc.)

### World-transition freeze fix ✅ COMPLETE

**Modified:** `ui/WorldTransition.tsx`
**Commit:** `d5283f8` — fix(web/signal): world-transition overlay no longer freezes mid-sequence
**Decision:** Move schedule timers to a ref. nextWorld() mid-schedule was triggering an effect re-run whose cleanup nuked the still-pending fade-out timers, leaving the overlay stuck at opacity 1 with pointer-events blocking. Pre-existing bug, surfaced now because cage mode advances to 'playing' (no overlay layered on top to hide the stuck transition).

### Puzzle redesign — A + B + C ✅ COMPLETE

**Modified (12 files, +671/-252):**
- `cage/levels.ts` — `monsters: MonsterSpawn[]` per level + `blockBudget` + `parBlocks` + `beatLocked`; 15 levels reseeded with intentional puzzle solutions
- `cage/monster.ts` — `MonsterState` now carries `id` + `rule`; `spawnMonster(id, rule, col, row, dir?)`
- `cage/enclosure.ts` — added `areAllEnclosed(monsters[])` that treats other monsters as walls
- `audio/audioEngine.ts` — `isPlacementBeat(beatsPerStep)` exported for the beat-lock check
- `engine/useGameStore.ts` — `monster | null` → `monsters[]`; placeBlock gates on budget + beat window; new tracking fields (cageBlocksUsedThisLevel, cageStarsThisRun, cageLastTapMissed); useSpecial fans out across all monsters; dev-only `window.__signalStore` for E2E probes
- `engine/useCage.ts` — iterates monsters, fails on any escape, uses areAllEnclosed for solve
- `scene/MonsterPawn.tsx` — renders N pawns, per-rule eye colour (drift red, bounce amber, split violet, silence cyan)
- `scene/PathHintVisualizer.tsx` — aggregates predicted paths across all monsters with brightest-wins compositing
- `scene/CageCelebration.tsx` — burst centroid is the monster cluster
- `ui/CageHud.tsx` — BudgetDots row + BeatWindowIndicator pulse + missed-tap whispers
- `ui/LevelCompleteOverlay.tsx` — ★ + 'par N · solved in M' on starred solves

**Commit:** `21b9c60` — feat(web/signal): puzzle redesign — block budget + beat-lock + multi-monster
**Decisions:**
- Three-pillar redesign over single-mechanic addition. Spam-no-longer-works was the bigger problem than any one bolted-on feature.
- Static & silence levels keep beatLocked off — they're spatial puzzles, not rhythm puzzles.
- ALL monsters must be enclosed to solve. Each monster's BFS treats every other monster's cell as a wall.
- Specials fan out to ALL matching monsters (Stun halts every monster regardless of rule; Mirror reverses every bounce monster).

**Verified in preview:**
- World transition advances cleanly (no freeze)
- Multi-monster level 3-2 spawns drift + bounce
- Beat-lock rejects off-beat taps (`lastMissed.reason === 'beat'`)

---
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
| `b30a78e` | docs(signal): port SESSION-STATE handoff for SIGNAL development continuity |
| `0789643` | feat(web/signal): per-world special items + celebrations + P2 fixes |
| `c72637b` | refactor(web/signal): apply 3-agent code-review fixes (a11y zoom, contrast, GPU buffer churn, Space/X shortcut) |
| `d5283f8` | fix(web/signal): world-transition overlay no longer freezes mid-sequence |
| `21b9c60` | feat(web/signal): puzzle redesign — block budget + beat-lock + multi-monster |

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
    │   │                                      + areAllEnclosed (multi-monster BFS)
    │   ├── levels.ts                        — 15 level specs: monsters[] + blockBudget +
    │   │                                      parBlocks + beatLocked + BPM + seeds
    │   ├── monster.ts                       — stepMonster (per-monster rule dispatch);
    │   │                                      MonsterState carries id + rule
    │   └── specials.ts                      — per-world ability registry (Sword/Mirror/
    │                                          Anchor/Lantern) + STUN/REVEAL constants
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
    │   ├── CageCelebration.tsx              — drei Sparkles burst on solve, 5 per-biome
    │   │                                      variants (puff / column / ripple / leaves /
    │   │                                      sunburst), centroid of monster cluster
    │   ├── RevealMarker.tsx                  — W5 lantern halo on the silence cell
    │   ├── SceneErrorBoundary.tsx           — WebGL fallback
    │   └── SceneFallback.tsx                — "requires a modern browser" copy
    │
    ├── ui/
    │   ├── TitleScreen.tsx                  — SIGNAL wordmark, mode pill, free-play link
    │   ├── InstrumentSelector.tsx           — BPM pad (tap-tempo + drag), SPEED label
    │   ├── NarrativeOverlays.tsx            — in-play whispers (Zen + Cage)
    │   ├── CageHud.tsx                      — level-ID intro + par, timer bar, rule hint,
    │   │                                      BudgetDots, BeatWindowIndicator, missed-tap
    │   │                                      whispers, fail copy by reason
    │   ├── SpecialButton.tsx                — bottom-left ability button (Space/X kbd)
    │   ├── LevelCompleteOverlay.tsx         — full-screen "Caged. / par N · solved in M"
    │   │                                      shows ★ when starred
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

### P0 — playtest the redesigned puzzle on a real device

Major mechanic changes shipped in `21b9c60`. Need real-device confirmation that:

1. **Block budget feels tight, not punishing.** Current pars: 1-1=1, 1-2=2, 1-3=3, 2-1=4, 2-2=4, 2-3=4, 3-1=4, 3-2=6, 3-3=6, 4-1=5, 4-2=6, 4-3=7, 5-1=1, 5-2=1, 5-3=1. Margin (budget - par) is +1 except in tutorial + silence (=0). Adjust upward if star feels unattainable, downward if it feels gifted.
2. **Beat-lock window is readable.** Currently 1-beat window before each step. The HUD pulse + soft "Wait for the pulse." whisper must give enough cue that off-beat misses don't feel arbitrary. Shorten BPM ramp if the window feels frantic at high BPM.
3. **Multi-monster levels (3-2, 3-3, 4-2, 4-3) are solvable, not chaotic.** Per-monster eye colour helps (drift red, bounce amber, split violet, silence cyan). Path hint shows aggregated paths. If players still can't tell monsters apart, add a subtle floor-tint under each.
4. **Tuning dials still in play (legacy P0):** monster motif volume / kick punch / `beatsPerStep` / placement-note decay. Tune in `audio/audioEngine.ts` and `cage/levels.ts` after watching real players fail.

### P1 — feature gaps you asked for that are not yet shipped

1. **Rebrand to PULSE** (or alternate). Held for explicit approval — user confirmed "keep SIGNAL for now" on 2026-04-25. Touch points still listed below for whenever the call changes: `web/app/lab/signal/layout.tsx`, `web/app/lab/signal/page.tsx` metadata, `web/components/lab/signal/ui/TitleScreen.tsx` wordmark string, `web/app/api/og/signal/route.tsx` hero text, OG meta in `web/app/lab/signal/s/[hash]/page.tsx`.
2. ~~**Sword / items for middle stages.**~~ ✅ shipped 2026-04-25 in `0789643` as per-world specials (Sword/Mirror/Anchor/Lantern), then expanded in `21b9c60` to fan out across all monsters in multi-monster levels.
3. **Bottom-row drum tracks.** User proposed "grid cells in the bottom row play drum sounds." Deferred. Would split `row === GRID_ROWS - 1` to map to kick/snare/hat/clap instead of pitch.
4. ~~**Per-world celebration animations.**~~ ✅ shipped 2026-04-25 in `0789643`/`c72637b` — 5 distinct biome variants in `scene/CageCelebration.tsx` (signal puff / temple column / deep ripple / garden leaves / truth sunburst) with biome-contrasting halo tones.
5. ~~**Second /code-review pass.**~~ ✅ ran 2026-04-25 — 3-agent parallel review (logic, architecture, UX, no security per scope) on `0789643`. 9 findings remediated in `c72637b`.

### P2 — known-but-not-critical bugs

1. ~~**`matchMedia` call inside `useFrame`**~~ ✅ fixed 2026-04-25 in `0789643` — hoisted to ref via `useEffect`, listens to media-query change events.
2. ~~**`signal_biome_complete` never fires for the final biome**~~ ✅ fixed 2026-04-25 in `0789643` — added `gamePhase === 'complete'` branch.
3. ~~**`encodeShareState` memoization**~~ ✅ fixed 2026-04-25 in `0789643` — wrapped `sessionSummary` in `useMemo` with stable deps.
4. ~~**`touchAction: 'none'` Android scroll**~~ ✅ fixed 2026-04-25 in `0789643`, then refined in `c72637b` (scope to user-select + overscroll-behavior only — `touch-action` on body breaks system pinch-zoom for low-vision users; per-control `touch-action` is handled at the BPM pad).

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
10. **Puzzle redesign over single-mechanic addition (2026-04-25).** "Cage one moving thing on a 10×10 grid with unlimited blocks" wasn't a puzzle. Block budget + beat-lock + multi-monster make every level a *find the right answer* problem instead of *spam until trapped*. Specials (Sword/Mirror/Anchor/Lantern) earn their place because multi-monster levels actually need them.
11. **Schedule timers go on refs, not in effects (2026-04-25).** Effect cleanups cancel pending setTimeouts. The world-transition freeze was caused by `nextWorld()` mid-schedule triggering a re-render whose cleanup nuked the still-pending fade-out timers. Lesson: anything that must outlive a state change goes on a ref.

---

## First three moves for the next session

1. **Real-device playtest of the redesigned puzzle.** Walk 1-1 → 1-3 (1/2/3-block tutorials) → 2-2 (first beat-locked level) → 3-2 (first multi-monster: drift + bounce) → 4-3 (2 splits) → 5-1 (silence with par-1). Note: are pars achievable, does beat-lock feel readable at higher BPM, can you tell monsters apart in 3-2/3-3, does Lantern reveal feel useful in 5-1.
2. **Tune the dials.** Most likely tweaks based on playtest: par margins in `cage/levels.ts`, monster step cadence (`beatsPerStep`), beat-lock window width in `audioEngine.isPlacementBeat`, motif volume in `audioEngine.ts`.
3. **Pick next feature wave.** Options ranked by impact:
   - Bottom-row drum tracks (~1 day, last shipped P1 item)
   - First-time discoverability whispers for special button + beat-lock + budget (~half day, medium-priority follow-up from review)
   - Local leaderboards / star count display (~half day)
   - **Repo cutover** (P0.5) — independent work. Vercel `LAB_URL` flip → verify rewrites → handoffpack-www cleanup PR. Requires Vercel dashboard access.

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
