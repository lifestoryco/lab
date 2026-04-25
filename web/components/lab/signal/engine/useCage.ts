// Cage Mode runtime.
// Steps every active monster on actual Tone.Transport beats so cadence is
// rock-solid with the kick drum. On every player placement, checks enclosure
// and the block-budget exhaustion condition.

import { useEffect, useRef } from 'react'
import { useGameStore, getGameState } from './useGameStore'
import { stepMonster, type MonsterState } from '../cage/monster'
import { areAllEnclosed } from '../cage/enclosure'
import { CAGE_COLS, CAGE_ROWS } from '../cage/levels'
import { onBeat, setMotifActive, playLevelFlourish } from '../audio/audioEngine'
import { blockKey } from '../utils/isoMath'

// Silence rule: the one-correct-cell is the grid centre.
const SILENCE_CELL = {
  col: Math.floor(CAGE_COLS / 2),
  row: Math.floor(CAGE_ROWS / 2),
}

export function useCage() {
  const lastBlockSize = useRef(0)
  const lastFlourishWorld = useRef(-1)

  useEffect(() => {
    // --- Beat-driven monster stepping ------------------------------------
    const unsubBeat = onBeat((beatIdx) => {
      const s = getGameState()
      if (s.mode !== 'cage') return
      if (s.gamePhase !== 'playing') return
      if (!s.cageLevel || s.monsters.length === 0) return
      if (s.cageLastResult) return

      // Stun: skip steps until the stun expires.
      if (s.monsterStunUntilBeat !== null && beatIdx < s.monsterStunUntilBeat) return

      const bps = s.cageLevel.beatsPerStep
      if (!isFinite(bps)) return
      if (beatIdx % bps !== 0) return

      // Step every monster whose rule actually moves. Treat each other monster
      // as a wall during its step (read positions BEFORE updating).
      const occupied = new Set<string>()
      for (const m of s.monsters) occupied.add(blockKey(m.col, m.row))

      let escaped = false
      const next: MonsterState[] = s.monsters.map((m) => {
        if (m.rule === 'static' || m.rule === 'silence') return m
        // Build augmented walls = real blocks + every OTHER monster's cell.
        // stepMonster only does `blocks.has(key)` so any truthy value works.
        const augmented: Map<string, unknown> = new Map(s.blocks)
        for (const k of occupied) {
          if (k === blockKey(m.col, m.row)) continue
          augmented.set(k, true)
        }
        const result = stepMonster(m, augmented, CAGE_COLS, CAGE_ROWS)
        if (result.escaped) escaped = true
        return result.next
      })

      s.setMonsters(next)
      if (escaped) s.failCageLevel()
    })

    // --- Store subscription: enclosure checks + motif + flourish ----------
    const unsub = useGameStore.subscribe((state, prev) => {
      if (state.mode !== 'cage') {
        setMotifActive(false)
        return
      }

      // Level entry: fire the 3-note flourish, wake the monster motif
      const justStartedPlaying =
        prev.gamePhase !== 'playing' && state.gamePhase === 'playing'
      const levelChanged = state.cageLevel?.worldIndex !== prev.cageLevel?.worldIndex
      if ((justStartedPlaying || levelChanged) && state.cageLevel) {
        lastBlockSize.current = 0
        setMotifActive(true)
        if (lastFlourishWorld.current !== state.cageLevel.worldIndex) {
          lastFlourishWorld.current = state.cageLevel.worldIndex
          playLevelFlourish(state.biome.rowToMidi)
        }
      }

      // Stop the motif when we leave 'playing' (solve / fail / portal).
      if (prev.gamePhase === 'playing' && state.gamePhase !== 'playing') {
        setMotifActive(false)
        lastFlourishWorld.current = -1
      }

      // Player placed a new block — enclosure + budget check.
      if (
        state.gamePhase === 'playing' &&
        state.cageLevel &&
        state.monsters.length > 0 &&
        state.blocks.size !== lastBlockSize.current
      ) {
        lastBlockSize.current = state.blocks.size

        // Silence rule: a single placement at the centre cell wins; any other
        // placement fails the round outright.
        const silenceMonster = state.monsters.find((m) => m.rule === 'silence')
        if (silenceMonster) {
          const justPlaced = state.lastPlacedCell
          if (justPlaced) {
            const isCentre =
              justPlaced.col === SILENCE_CELL.col &&
              justPlaced.row === SILENCE_CELL.row
            if (isCentre) {
              state.triggerChain(SILENCE_CELL.col, SILENCE_CELL.row, 8)
              state.solveCageLevel()
            } else {
              state.failCageLevel()
            }
          }
          return
        }

        // Multi-monster enclosure: every monster's BFS must reach no edge.
        const res = areAllEnclosed(state.monsters, state.blocks, CAGE_COLS, CAGE_ROWS)
        if (res.allTrapped) {
          // Fire celebration on the centroid of the monster cluster.
          const cx = state.monsters.reduce((a, m) => a + m.col, 0) / state.monsters.length
          const cy = state.monsters.reduce((a, m) => a + m.row, 0) / state.monsters.length
          const totalReach = res.perMonster.reduce((a, r) => a + r.reachable.size, 0)
          const flair = Math.min(8, Math.max(5, totalReach))
          state.triggerChain(Math.round(cx), Math.round(cy), flair)
          state.solveCageLevel()
          return
        }

        // Budget exhausted but still not caged → fail. Triggers the retry
        // overlay (Super Meat Boy pattern).
        const remaining = state.cageLevel.blockBudget - state.cageBlocksUsedThisLevel
        if (remaining <= 0) {
          state.failCageLevel()
        }
      }
    })

    return () => {
      unsubBeat()
      unsub()
      setMotifActive(false)
    }
  }, [])
}
