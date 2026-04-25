// Cage Mode level progression — 15 levels across 5 biomes.
//
// Redesigned around three pillars:
//   A. **Block budget** — every level gives a tight number of placements.
//      Solve under par = star. Spend the budget without caging = fail.
//   B. **Beat-locked placement** — when `beatLocked` is true, blocks can
//      only be placed in the 1-beat window before each monster step.
//      Off-beat taps are rejected with a soft tick. Static / silence /
//      tutorial levels keep beatLocked off.
//   C. **Multiple monsters** — each level spawns one or more monsters,
//      each with its own rule. The level solves only when ALL monsters
//      are enclosed (BFS from each must reach no edge).

import { BIOMES } from '../worlds/biomeConfigs'

export const CAGE_COLS = 10
export const CAGE_ROWS = 10

export type CageRule =
  | 'static'     // monster doesn't move
  | 'drift'      // steps toward nearest edge every N beats
  | 'bounce'     // bounces off walls at 90°
  | 'split'      // leaves an echo-pawn a step behind
  | 'silence'    // one correct cell

export interface MonsterSpawn {
  rule: CageRule
  col: number
  row: number
  // Initial direction for bounce monsters. Defaults to (1,0).
  dirCol?: number
  dirRow?: number
}

export interface CageLevel {
  id: string                      // '1-1', '1-2', '2-1'...
  worldIndex: number              // 0..4 — biome palette + scale
  name: string                    // biome.name at entry
  monsters: MonsterSpawn[]        // 1+ monsters, each with own rule
  beatsPerStep: number            // monster step cadence in 4n beats
  beatLocked: boolean             // require placement on the pre-step beat
  blockBudget: number             // hard cap on placements before fail
  parBlocks: number               // solve in <= this many = star
  bpm: number                     // music BPM at this level
  seedBlocks: Array<{ col: number; row: number }>
  timeLimitMs?: number            // falls back to SESSION_DURATION_MS
}

// Centre cell of the 10×10 grid
const C = Math.floor(CAGE_COLS / 2) // 5
const R = Math.floor(CAGE_ROWS / 2) // 5

// Helpers for legibility
const near = (dc: number, dr: number) => ({ col: C + dc, row: R + dr })
const m = (rule: CageRule, dc: number, dr: number, dir?: { col: number; row: number }): MonsterSpawn => ({
  rule,
  col: C + dc,
  row: R + dr,
  ...(dir ? { dirCol: dir.col, dirRow: dir.row } : {}),
})

export const CAGE_LEVELS: CageLevel[] = [
  // ────────── Biome 1 · The Signal — tutorial (static) ──────────
  // Block-budget tutorial: each level you place exactly the par count.
  {
    id: '1-1', worldIndex: 0, name: BIOMES[0].name,
    monsters: [m('static', 0, 0)],
    beatsPerStep: Infinity, beatLocked: false,
    blockBudget: 1, parBlocks: 1,
    bpm: 80,
    // 3 walls pre-placed. One specific gap. One correct tap.
    seedBlocks: [near(-1, 0), near(1, 0), near(0, -1)],
  },
  {
    id: '1-2', worldIndex: 0, name: BIOMES[0].name,
    monsters: [m('static', 0, 0)],
    beatsPerStep: Infinity, beatLocked: false,
    blockBudget: 2, parBlocks: 2,
    bpm: 85,
    // 2 walls. Two specific cells.
    seedBlocks: [near(-1, 0), near(1, 0)],
  },
  {
    id: '1-3', worldIndex: 0, name: BIOMES[0].name,
    monsters: [m('static', 0, 0)],
    beatsPerStep: Infinity, beatLocked: false,
    blockBudget: 3, parBlocks: 3,
    bpm: 90,
    // 1 wall. Three specific cells.
    seedBlocks: [near(1, 0)],
  },

  // ────────── Biome 2 · The Temple — drift + beat-lock teaches ──────────
  // 2-1 introduces drift gently with no beat-lock. 2-2 turns on beat-lock.
  // 2-3 ramps the budget down so the player has to plan.
  {
    id: '2-1', worldIndex: 1, name: BIOMES[1].name,
    monsters: [m('drift', 0, 0)],
    beatsPerStep: 16, beatLocked: false,
    blockBudget: 5, parBlocks: 4,
    bpm: 100,
    // Bookend hallway. 4 placements close it; 5 gives a margin.
    seedBlocks: [near(-2, 0), near(2, 0)],
  },
  {
    id: '2-2', worldIndex: 1, name: BIOMES[1].name,
    monsters: [m('drift', 0, 0)],
    beatsPerStep: 12, beatLocked: true,
    blockBudget: 5, parBlocks: 4,
    bpm: 105,
    seedBlocks: [near(-2, 0), near(2, 0)],
  },
  {
    id: '2-3', worldIndex: 1, name: BIOMES[1].name,
    monsters: [m('drift', 0, 0)],
    beatsPerStep: 10, beatLocked: true,
    blockBudget: 4, parBlocks: 4,
    bpm: 110,
    seedBlocks: [near(-2, 0)],
  },

  // ────────── Biome 3 · The Deep — bounce + multi-monster ──────────
  // 3-2 introduces a SECOND monster (drift + bounce). Special items earn
  // their place here: stun the bounce while you wall the drift.
  {
    id: '3-1', worldIndex: 2, name: BIOMES[2].name,
    monsters: [m('bounce', 0, 0, { col: 1, row: 0 })],
    beatsPerStep: 10, beatLocked: true,
    blockBudget: 5, parBlocks: 4,
    bpm: 110,
    seedBlocks: [near(-2, -2), near(2, 2)],
  },
  {
    id: '3-2', worldIndex: 2, name: BIOMES[2].name,
    monsters: [
      m('bounce', -1, -1, { col: 1, row: 0 }),
      m('drift', 1, 1),
    ],
    beatsPerStep: 10, beatLocked: true,
    blockBudget: 7, parBlocks: 6,
    bpm: 115,
    seedBlocks: [near(-3, 0), near(3, 0)],
  },
  {
    id: '3-3', worldIndex: 2, name: BIOMES[2].name,
    monsters: [
      m('bounce', -1, 0, { col: 1, row: 0 }),
      m('bounce', 1, 0, { col: -1, row: 0 }),
    ],
    beatsPerStep: 8, beatLocked: true,
    blockBudget: 7, parBlocks: 6,
    bpm: 120,
    seedBlocks: [],
  },

  // ────────── Biome 4 · The Garden — split + multi-monster ──────────
  {
    id: '4-1', worldIndex: 3, name: BIOMES[3].name,
    monsters: [m('split', 0, 0)],
    beatsPerStep: 8, beatLocked: true,
    blockBudget: 6, parBlocks: 5,
    bpm: 120,
    seedBlocks: [near(-2, 0), near(0, -2)],
  },
  {
    id: '4-2', worldIndex: 3, name: BIOMES[3].name,
    monsters: [
      m('split', -1, -1),
      m('drift', 1, 1),
    ],
    beatsPerStep: 8, beatLocked: true,
    blockBudget: 7, parBlocks: 6,
    bpm: 125,
    seedBlocks: [near(-3, 0)],
  },
  {
    id: '4-3', worldIndex: 3, name: BIOMES[3].name,
    monsters: [
      m('split', -1, -1),
      m('split', 1, 1),
    ],
    beatsPerStep: 7, beatLocked: true,
    blockBudget: 8, parBlocks: 7,
    bpm: 130,
    seedBlocks: [],
  },

  // ────────── Biome 5 · The Truth — silence + reveal ──────────
  // 1 block budget by design — there is exactly one correct cell. The
  // Lantern special reveals it. Failure on any non-centre placement.
  {
    id: '5-1', worldIndex: 4, name: BIOMES[4].name,
    monsters: [m('silence', 0, 0)],
    beatsPerStep: Infinity, beatLocked: false,
    blockBudget: 1, parBlocks: 1,
    bpm: 140,
    seedBlocks: [],
  },
  {
    id: '5-2', worldIndex: 4, name: BIOMES[4].name,
    monsters: [m('silence', 0, 0)],
    beatsPerStep: Infinity, beatLocked: false,
    blockBudget: 1, parBlocks: 1,
    bpm: 150,
    seedBlocks: [],
  },
  {
    id: '5-3', worldIndex: 4, name: BIOMES[4].name,
    monsters: [m('silence', 0, 0)],
    beatsPerStep: Infinity, beatLocked: false,
    blockBudget: 1, parBlocks: 1,
    bpm: 160,
    seedBlocks: [],
  },
]

export const TOTAL_CAGE_LEVELS = CAGE_LEVELS.length

// Legacy helper — code that treated biomes as levels calls this.
export function levelFor(worldIndex: number): CageLevel {
  const idx = Math.max(0, Math.min(CAGE_LEVELS.length - 1, worldIndex * 3))
  return CAGE_LEVELS[idx]
}

// New primary accessor: by cage level index 0..14.
export function cageLevelAt(index: number): CageLevel {
  const i = Math.max(0, Math.min(CAGE_LEVELS.length - 1, index))
  return CAGE_LEVELS[i]
}
