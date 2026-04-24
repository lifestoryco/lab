import { create } from 'zustand'
import { BIOMES, type BiomeConfig } from '../worlds/biomeConfigs'
import { blockKey } from '../utils/isoMath'
import { midiToNoteName } from '../audio/scales'
import type { MonsterState } from '../cage/monster'
import { spawnMonster } from '../cage/monster'
import { cageLevelAt, CAGE_LEVELS, type CageLevel } from '../cage/levels'

// --- Types ---

export interface PlacedBlock {
  col: number
  row: number
  instrumentIndex: number
  placedAt: number // timestamp
}

export type GamePhase = 'title' | 'playing' | 'transition' | 'gameover' | 'complete'
export type PlayMode = 'zen' | 'cage'

const MODE_STORAGE_KEY = 'signal.mode'

function readInitialMode(): PlayMode {
  // Cage is the default post-pivot. Zen is the opt-in free-play mode.
  if (typeof window === 'undefined') return 'cage'
  const v = window.localStorage.getItem(MODE_STORAGE_KEY)
  if (v === 'broadcast') {
    // Legacy: Broadcast users promote to Cage on next load.
    try { window.localStorage.setItem(MODE_STORAGE_KEY, 'cage') } catch { /* swallow */ }
    return 'cage'
  }
  return v === 'zen' ? 'zen' : 'cage'
}

export interface BlockAnimation {
  key: string
  startTime: number
  type: 'place' | 'pulse' | 'remove'
}

// --- Store ---

interface GameState {
  // World
  worldIndex: number
  biome: BiomeConfig
  gamePhase: GamePhase

  // Grid
  blocks: Map<string, PlacedBlock>

  // Sequencer
  playheadStep: number
  isPlaying: boolean

  // Timer
  elapsedMs: number
  timeOfDay: number // derived: 0 = dawn, 1 = dusk

  // Color saturation (0..1, earned through block placement)
  saturation: number

  // UI
  selectedInstrument: number

  // Animations
  blockAnimations: Map<string, BlockAnimation>
  pulsingBlocks: Set<string>

  // Audio
  audioReady: boolean
  bpm: number

  // Burst trigger for particles (set on block place, cleared by Particles component)
  lastPlacedCell: { col: number; row: number } | null

  // Portal unlock: flips true on first chain of ≥3 in the current biome (Zen)
  // OR on a successful cage enclosure (Cage).
  hasTriggeredChain: boolean

  // Celebration trigger — set by useChainReaction on any chain, consumed by scene FX
  lastChain: { originCol: number; originRow: number; length: number; at: number } | null

  // --- Session-wide aggregate for share screen -----------------------------
  sessionStartedAt: number | null
  sessionBlocks: Array<{ biome: number; col: number; row: number }>
  sessionBiomesCleared: number // bitmask; bit N = biome N cleared
  sessionTotalChains: number
  // -----------------------------------------------------------------------

  mode: PlayMode

  // --- Cage Mode ---------------------------------------------------------
  cageLevelIndex: number        // 0..14 — which of the 15 cage levels
  cageLevel: CageLevel | null
  monster: MonsterState | null
  cageAttempts: number          // across the session
  cageLevelsCleared: number     // bitmask by biome (0..4) — one bit = biome fully solved
  cageSubLevelsCleared: number  // bitmask by level index (0..14) — granular completion
  cageTapsThisLevel: number     // reset on level start
  cageLevelStartedAt: number | null
  cageLastResult: { solved: boolean; at: number } | null
  // -----------------------------------------------------------------------

  // Actions
  placeBlock: (col: number, row: number) => void
  removeBlock: (col: number, row: number) => void
  setPlayheadStep: (step: number) => void
  setPulsingBlocks: (keys: string[]) => void
  tick: (deltaMs: number) => void
  setGamePhase: (phase: GamePhase) => void
  nextWorld: () => void
  selectInstrument: (index: number) => void
  setAudioReady: (ready: boolean) => void
  setBpm: (bpm: number) => void
  startPlaying: () => void
  triggerChain: (originCol: number, originRow: number, length: number) => void
  setMode: (m: PlayMode) => void
  // Cage Mode actions
  startCageLevel: (levelIndex: number) => void
  setMonster: (m: MonsterState | null) => void
  solveCageLevel: () => void
  failCageLevel: () => void
  retryCageLevel: () => void
  nextCageLevel: () => void
  reset: () => void
}

const SESSION_DURATION_MS = 150_000 // 2 min 30 s — one complete sitting per biome

export const useGameStore = create<GameState>((set, get) => ({
  worldIndex: 0,
  biome: BIOMES[0],
  gamePhase: 'title',

  blocks: new Map(),

  playheadStep: 0,
  isPlaying: false,

  elapsedMs: 0,
  timeOfDay: 0,

  saturation: 0,

  selectedInstrument: 0,
  bpm: BIOMES[0].bpm,

  blockAnimations: new Map(),
  pulsingBlocks: new Set(),

  audioReady: false,
  lastPlacedCell: null,
  hasTriggeredChain: false,
  lastChain: null,

  sessionStartedAt: null,
  sessionBlocks: [],
  sessionBiomesCleared: 0,
  sessionTotalChains: 0,

  mode: readInitialMode(),

  cageLevelIndex: 0,
  cageLevel: null,
  monster: null,
  cageAttempts: 0,
  cageLevelsCleared: 0,
  cageSubLevelsCleared: 0,
  cageTapsThisLevel: 0,
  cageLevelStartedAt: null,
  cageLastResult: null,

  placeBlock: (col, row) => {
    const state = get()
    if (state.gamePhase !== 'playing') return
    const key = blockKey(col, row)
    if (state.blocks.has(key)) return // already occupied

    const block: PlacedBlock = {
      col,
      row,
      instrumentIndex: state.selectedInstrument,
      placedAt: performance.now(),
    }

    const nextBlocks = new Map(state.blocks)
    nextBlocks.set(key, block)

    const nextAnims = new Map(state.blockAnimations)
    nextAnims.set(key, { key, startTime: performance.now(), type: 'place' })

    // Recompute saturation: blockCount / maxSaturationBlocks, clamped to 1
    const newSaturation = Math.min(1, nextBlocks.size / state.biome.maxSaturationBlocks)

    set({
      blocks: nextBlocks,
      blockAnimations: nextAnims,
      saturation: newSaturation,
      lastPlacedCell: { col, row },
      sessionBlocks: [...state.sessionBlocks, { biome: state.worldIndex, col, row }],
      cageTapsThisLevel: state.mode === 'cage' ? state.cageTapsThisLevel + 1 : state.cageTapsThisLevel,
    })
  },

  removeBlock: (col, row) => {
    const state = get()
    const key = blockKey(col, row)
    const nextBlocks = new Map(state.blocks)
    if (!nextBlocks.has(key)) return
    nextBlocks.delete(key)

    const newSaturation = Math.min(1, nextBlocks.size / state.biome.maxSaturationBlocks)
    set({ blocks: nextBlocks, saturation: newSaturation })
  },

  setPlayheadStep: (step) => set({ playheadStep: step }),

  setPulsingBlocks: (keys) => set({ pulsingBlocks: new Set(keys) }),

  tick: (deltaMs) => {
    const state = get()
    if (state.gamePhase !== 'playing') return

    const newElapsed = state.elapsedMs + deltaMs
    const newTimeOfDay = Math.min(1, newElapsed / SESSION_DURATION_MS)

    // Night falls
    if (newElapsed >= SESSION_DURATION_MS && state.gamePhase === 'playing') {
      set({
        elapsedMs: SESSION_DURATION_MS,
        timeOfDay: 1,
        gamePhase: state.hasTriggeredChain ? 'transition' : 'gameover',
        isPlaying: false,
      })
      return
    }

    set({ elapsedMs: newElapsed, timeOfDay: newTimeOfDay })
  },

  setGamePhase: (phase) => set({ gamePhase: phase }),

  nextWorld: () => {
    const state = get()
    // --- Cage Mode: advance to next cage level, skip title screen ---------
    // The WorldTransition ceremony calls nextWorld() at its end; in cage we
    // want to drop straight into the next level once the biome intro plays.
    if (state.mode === 'cage') {
      const nextIdx = state.cageLevelIndex + 1
      if (nextIdx >= CAGE_LEVELS.length) {
        // All 15 levels beaten → full-arc complete.
        set({
          gamePhase: 'complete',
          isPlaying: false,
          sessionBiomesCleared: state.cageLevelsCleared,
          cageLevel: null,
          monster: null,
        })
        return
      }
      get().startCageLevel(nextIdx)
      set({ gamePhase: 'playing', isPlaying: true })
      return
    }

    const clearedMask = state.sessionBiomesCleared | (1 << state.worldIndex)
    const nextIndex = state.worldIndex + 1
    if (nextIndex >= BIOMES.length) {
      // Final biome cleared — full-arc complete. Enter 'complete' phase so ResultScreen
      // can show the share composition. Preserves session aggregates for the share hash.
      set({
        gamePhase: 'complete',
        isPlaying: false,
        sessionBiomesCleared: clearedMask,
        // Cage: preserve cageLevelsCleared for the share payload, drop in-flight monster.
        cageLevel: null,
        monster: null,
      })
      return
    }
    set({
      worldIndex: nextIndex,
      biome: BIOMES[nextIndex],
      bpm: BIOMES[nextIndex].bpm,
      blocks: new Map(),
      blockAnimations: new Map(),
      pulsingBlocks: new Set(),
      elapsedMs: 0,
      timeOfDay: 0,
      saturation: 0,
      playheadStep: 0,
      isPlaying: false,
      gamePhase: 'title',
      lastPlacedCell: null,
      hasTriggeredChain: false,
      lastChain: null,
      sessionBiomesCleared: clearedMask,
      // Cage: drop the finished monster, retain cleared-levels bitmask.
      cageLevel: null,
      monster: null,
      cageTapsThisLevel: 0,
      cageLevelStartedAt: null,
    })
  },

  selectInstrument: (index) => set({ selectedInstrument: index }),

  setAudioReady: (ready) => set({ audioReady: ready }),

  setBpm: (bpm) => set({ bpm }),

  startPlaying: () => {
    const state = get()
    set({
      gamePhase: 'playing',
      isPlaying: true,
      sessionStartedAt: state.sessionStartedAt ?? performance.now(),
    })
  },

  triggerChain: (originCol, originRow, length) => {
    const state = get()
    set({
      lastChain: { originCol, originRow, length, at: performance.now() },
      // First chain of ≥3 opens the portal (replaces the old block-count gate)
      hasTriggeredChain: state.hasTriggeredChain || length >= 3,
      sessionTotalChains: state.sessionTotalChains + (length >= 3 ? 1 : 0),
    })
  },

  setMode: (m) => {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(MODE_STORAGE_KEY, m)
    }
    set({ mode: m })
  },

  // --- Cage Mode actions ---------------------------------------------------
  startCageLevel: (levelIndex) => {
    const level = cageLevelAt(levelIndex)
    const biome = BIOMES[level.worldIndex]

    // Apply seed blocks (pre-placed walls that teach the layout).
    const now = performance.now()
    const nextBlocks = new Map<string, PlacedBlock>()
    for (const seed of level.seedBlocks) {
      nextBlocks.set(blockKey(seed.col, seed.row), {
        col: seed.col,
        row: seed.row,
        instrumentIndex: 0,
        placedAt: now,
      })
    }

    set({
      cageLevelIndex: levelIndex,
      cageLevel: level,
      worldIndex: level.worldIndex,
      biome,
      bpm: level.bpm,
      monster: spawnMonster(level.startCol, level.startRow),
      blocks: nextBlocks,
      blockAnimations: new Map(),
      pulsingBlocks: new Set(),
      elapsedMs: 0,
      timeOfDay: 0,
      playheadStep: 0,
      hasTriggeredChain: false,
      lastChain: null,
      lastPlacedCell: null,
      cageTapsThisLevel: 0,
      cageLevelStartedAt: performance.now(),
      cageAttempts: get().cageAttempts + 1,
      cageLastResult: null,
    })
  },

  setMonster: (m) => set({ monster: m }),

  solveCageLevel: () => {
    const state = get()
    const biomeBit = 1 << state.worldIndex
    // Mark biome fully cleared only when the LAST level of the biome is solved
    // (levels 2, 5, 8, 11, 14 are the last-in-biome, but more robustly:
    //  the next level either doesn't exist or moves to a new worldIndex).
    const nextIdx = state.cageLevelIndex + 1
    const isBiomeBoundary =
      nextIdx >= CAGE_LEVELS.length ||
      CAGE_LEVELS[nextIdx].worldIndex !== state.worldIndex
    set({
      cageSubLevelsCleared: state.cageSubLevelsCleared | (1 << state.cageLevelIndex),
      cageLevelsCleared: isBiomeBoundary
        ? state.cageLevelsCleared | biomeBit
        : state.cageLevelsCleared,
      cageLastResult: { solved: true, at: performance.now() },
      hasTriggeredChain: true,
    })
  },

  failCageLevel: () => {
    set({
      cageLastResult: { solved: false, at: performance.now() },
      gamePhase: 'gameover',
      isPlaying: false,
    })
  },

  // Retry the current level — keeps progression, just re-seeds the level.
  retryCageLevel: () => {
    const idx = get().cageLevelIndex
    const level = cageLevelAt(idx)
    const now = performance.now()
    const nextBlocks = new Map<string, PlacedBlock>()
    for (const seed of level.seedBlocks) {
      nextBlocks.set(blockKey(seed.col, seed.row), {
        col: seed.col, row: seed.row, instrumentIndex: 0, placedAt: now,
      })
    }
    set({
      blocks: nextBlocks,
      blockAnimations: new Map(),
      pulsingBlocks: new Set(),
      elapsedMs: 0,
      timeOfDay: 0,
      playheadStep: 0,
      hasTriggeredChain: false,
      lastChain: null,
      lastPlacedCell: null,
      monster: spawnMonster(level.startCol, level.startRow),
      cageTapsThisLevel: 0,
      cageLevelStartedAt: performance.now(),
      cageAttempts: get().cageAttempts + 1,
      cageLastResult: null,
      gamePhase: 'playing',
      isPlaying: true,
    })
  },

  // Advance to the next cage level. If we cross a biome boundary, flow
  // through the existing WorldTransition ceremony. If the next level is
  // in the same biome, fast-resume without the biome intro.
  nextCageLevel: () => {
    const state = get()
    const next = state.cageLevelIndex + 1
    if (next >= CAGE_LEVELS.length) {
      set({
        gamePhase: 'complete',
        isPlaying: false,
        sessionBiomesCleared: state.cageLevelsCleared,
        monster: null,
        cageLevel: null,
      })
      return
    }
    const nextLevel = CAGE_LEVELS[next]
    const biomeChanged = nextLevel.worldIndex !== state.worldIndex
    if (biomeChanged) {
      // Enter transition — WorldTransition will animate then call nextWorld().
      set({ gamePhase: 'transition', isPlaying: false })
      return
    }
    // Same biome — fast-advance into the next level.
    get().startCageLevel(next)
    set({ gamePhase: 'playing', isPlaying: true })
  },
  // -----------------------------------------------------------------------

  reset: () => set({
    worldIndex: 0,
    biome: BIOMES[0],
    gamePhase: 'title',
    blocks: new Map(),
    blockAnimations: new Map(),
    pulsingBlocks: new Set(),
    elapsedMs: 0,
    timeOfDay: 0,
    saturation: 0,
    playheadStep: 0,
    isPlaying: false,
    selectedInstrument: 0,
    bpm: BIOMES[0].bpm,
    lastPlacedCell: null,
    hasTriggeredChain: false,
    lastChain: null,
    sessionStartedAt: null,
    sessionBlocks: [],
    sessionBiomesCleared: 0,
    sessionTotalChains: 0,
    cageLevelIndex: 0,
    cageLevel: null,
    monster: null,
    cageAttempts: 0,
    cageLevelsCleared: 0,
    cageSubLevelsCleared: 0,
    cageTapsThisLevel: 0,
    cageLevelStartedAt: null,
    cageLastResult: null,
  }),
}))

// Non-reactive getters for use in useFrame / audio callbacks
export const getGameState = useGameStore.getState
