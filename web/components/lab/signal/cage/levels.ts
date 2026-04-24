// Cage Mode level progression — 15 levels across 5 biomes.
//
// Mario-style ramp:
//   · 1-1 / 1-2 / 1-3 are tutorials with pre-seeded walls so the player
//     cannot fail on a calm first read. Each reveals one more responsibility.
//   · Biomes 2–5 teach the new rule with compounding difficulty, rising BPM.
//   · BPM schedule hits Sean's targets:
//       biome 1 → ~80  biome 2 → ~100  biome 3 → ~115
//       biome 4 → ~120–130  biome 5 → ~140–160
//
// Each level's music BPM also drives the monster step cadence via the
// audioEngine's onBeat subscription. BPM is the difficulty dial.

import { BIOMES } from '../worlds/biomeConfigs'

export const CAGE_COLS = 10
export const CAGE_ROWS = 10

export type CageRule =
  | 'static'     // monster doesn't move
  | 'drift'      // steps toward nearest edge every N beats
  | 'bounce'     // bounces off walls at 90°
  | 'split'      // leaves an echo-pawn a step behind
  | 'silence'    // one correct cell

export interface CageLevel {
  id: string                 // '1-1', '1-2', '2-1'...
  worldIndex: number         // 0..4 — biome palette + scale
  name: string               // biome.name at entry
  rule: CageRule
  startCol: number
  startRow: number
  beatsPerStep: number       // monster step cadence in 4n beats
  bpm: number                // music BPM at this level
  seedBlocks: Array<{ col: number; row: number }>
  timeLimitMs?: number       // falls back to SESSION_DURATION_MS
}

// Centre cell of the 10×10 grid
const C = Math.floor(CAGE_COLS / 2) // 5
const R = Math.floor(CAGE_ROWS / 2) // 5

// Helpers for legibility
const near = (dc: number, dr: number) => ({ col: C + dc, row: R + dr })

export const CAGE_LEVELS: CageLevel[] = [
  // ────────── Biome 1 · The Signal — tutorial (static) ──────────
  {
    id: '1-1', worldIndex: 0, name: BIOMES[0].name, rule: 'static',
    startCol: C, startRow: R,
    beatsPerStep: Infinity,
    bpm: 80,
    // 3 walls pre-placed. Player taps one cell to close.
    seedBlocks: [near(-1, 0), near(1, 0), near(0, -1)],
  },
  {
    id: '1-2', worldIndex: 0, name: BIOMES[0].name, rule: 'static',
    startCol: C, startRow: R,
    beatsPerStep: Infinity,
    bpm: 85,
    // 2 walls. Player taps two cells to close.
    seedBlocks: [near(-1, 0), near(1, 0)],
  },
  {
    id: '1-3', worldIndex: 0, name: BIOMES[0].name, rule: 'static',
    startCol: C, startRow: R,
    beatsPerStep: Infinity,
    bpm: 90,
    // 1 wall. Taps 3 cells.
    seedBlocks: [near(1, 0)],
  },

  // ────────── Biome 2 · The Temple — drift enters ──────────
  {
    id: '2-1', worldIndex: 1, name: BIOMES[1].name, rule: 'drift',
    startCol: C, startRow: R,
    beatsPerStep: 16,          // very slow drift — first taste
    bpm: 100,
    // Two bookend walls give the player a hallway to exploit
    seedBlocks: [near(-2, 0), near(2, 0)],
  },
  {
    id: '2-2', worldIndex: 1, name: BIOMES[1].name, rule: 'drift',
    startCol: C, startRow: R,
    beatsPerStep: 12,
    bpm: 105,
    seedBlocks: [near(-2, 0), near(2, 0)],
  },
  {
    id: '2-3', worldIndex: 1, name: BIOMES[1].name, rule: 'drift',
    startCol: C, startRow: R,
    beatsPerStep: 10,
    bpm: 110,
    seedBlocks: [],
  },

  // ────────── Biome 3 · The Deep — bounce enters ──────────
  {
    id: '3-1', worldIndex: 2, name: BIOMES[2].name, rule: 'bounce',
    startCol: C, startRow: R,
    beatsPerStep: 10,
    bpm: 110,
    // A pair of reflector walls north-west to hint at the bounce idea.
    seedBlocks: [near(-2, -2), near(2, 2)],
  },
  {
    id: '3-2', worldIndex: 2, name: BIOMES[2].name, rule: 'bounce',
    startCol: C, startRow: R,
    beatsPerStep: 8,
    bpm: 115,
    seedBlocks: [near(-2, -2)],
  },
  {
    id: '3-3', worldIndex: 2, name: BIOMES[2].name, rule: 'bounce',
    startCol: C, startRow: R,
    beatsPerStep: 8,
    bpm: 120,
    seedBlocks: [],
  },

  // ────────── Biome 4 · The Garden — split enters ──────────
  {
    id: '4-1', worldIndex: 3, name: BIOMES[3].name, rule: 'split',
    startCol: C, startRow: R,
    beatsPerStep: 8,
    bpm: 120,
    seedBlocks: [near(-2, 0), near(0, -2)],
  },
  {
    id: '4-2', worldIndex: 3, name: BIOMES[3].name, rule: 'split',
    startCol: C, startRow: R,
    beatsPerStep: 7,
    bpm: 125,
    seedBlocks: [near(-2, 0)],
  },
  {
    id: '4-3', worldIndex: 3, name: BIOMES[3].name, rule: 'split',
    startCol: C, startRow: R,
    beatsPerStep: 6,
    bpm: 130,
    seedBlocks: [],
  },

  // ────────── Biome 5 · The Truth — silence ──────────
  {
    id: '5-1', worldIndex: 4, name: BIOMES[4].name, rule: 'silence',
    startCol: C, startRow: R,
    beatsPerStep: Infinity,
    bpm: 140,
    seedBlocks: [],
    timeLimitMs: 30_000,
  },
  {
    id: '5-2', worldIndex: 4, name: BIOMES[4].name, rule: 'silence',
    startCol: C, startRow: R,
    beatsPerStep: Infinity,
    bpm: 150,
    seedBlocks: [],
    timeLimitMs: 25_000,
  },
  {
    id: '5-3', worldIndex: 4, name: BIOMES[4].name, rule: 'silence',
    startCol: C, startRow: R,
    beatsPerStep: Infinity,
    bpm: 160,
    seedBlocks: [],
    timeLimitMs: 20_000,
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
