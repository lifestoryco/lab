// Cage Mode runtime.
// Steps the monster on actual Tone.Transport beats (via onBeat subscription)
// so monster cadence is rock-solid with the kick drum — no wall-clock drift.
// On every player placement, checks enclosure; on cage-close, celebrates.

import { useEffect, useRef } from 'react'
import { useGameStore, getGameState } from './useGameStore'
import { stepMonster } from '../cage/monster'
import { isEnclosed } from '../cage/enclosure'
import { CAGE_COLS, CAGE_ROWS } from '../cage/levels'
import { onBeat, setMotifActive, playLevelFlourish } from '../audio/audioEngine'

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
    // Runs on every transport 4n. Monster moves when (beatIdx % beatsPerStep) === 0.
    const unsubBeat = onBeat((beatIdx) => {
      const s = getGameState()
      if (s.mode !== 'cage') return
      if (s.gamePhase !== 'playing') return
      if (!s.monster || !s.cageLevel) return
      if (s.cageLastResult) return

      // Stun: skip steps until the stun expires.
      if (s.monsterStunUntilBeat !== null && beatIdx < s.monsterStunUntilBeat) return

      const bps = s.cageLevel.beatsPerStep
      if (!isFinite(bps)) return
      if (beatIdx % bps !== 0) return
      if (s.cageLevel.rule === 'static' || s.cageLevel.rule === 'silence') return

      const result = stepMonster(
        s.monster,
        s.blocks,
        CAGE_COLS,
        CAGE_ROWS,
        s.cageLevel.rule,
      )
      s.setMonster(result.next)

      if (result.escaped) {
        s.failCageLevel()
      }
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

      // Player placed a new block — enclosure check.
      if (
        state.gamePhase === 'playing' &&
        state.cageLevel &&
        state.monster &&
        state.blocks.size !== lastBlockSize.current
      ) {
        lastBlockSize.current = state.blocks.size

        // Silence rule: a single placement at the centre cell wins; any other
        // placement fails the round outright.
        if (state.cageLevel.rule === 'silence') {
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

        // Normal enclosure: flood from monster, if no edge reachable → caged.
        const res = isEnclosed(state.monster, state.blocks, CAGE_COLS, CAGE_ROWS)
        if (res.trapped) {
          const flair = Math.min(8, Math.max(5, res.reachable.size))
          state.triggerChain(state.monster.col, state.monster.row, flair)
          state.solveCageLevel()
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
