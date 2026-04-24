// DK barrel chain reaction system.
// When a block is placed adjacent to existing blocks, a BFS cascade fires:
//   - Each connected block pulses visually with a staggered delay
//   - Each cascaded block plays its note (ascending feel across the chain)
//   - Chains of ≥3 blocks give a saturation bonus

import { useEffect, useRef } from 'react'
import { useGameStore, getGameState } from './useGameStore'
import { triggerPlacementNote, chainSwell } from '../audio/audioEngine'
import { blockKey } from '../utils/isoMath'

const STEP_DELAY_MS = 38  // ms between BFS levels (feels like a ripple)
const MAX_DEPTH = 8        // max cascade depth to prevent runaway on dense grids
const MIN_CHAIN_FOR_BONUS = 2  // minimum adjacent blocks to trigger saturation bonus

// Neighbor directions: left, right, up, down
const DIRS: [number, number][] = [[-1,0],[1,0],[0,-1],[0,1]]

export function useChainReaction() {
  // Track the last placement object by reference to avoid re-triggering
  const lastSeenCell = useRef<{ col: number; row: number } | null>(null)
  // Store active timeouts so we can cancel on unmount
  const timeouts = useRef<ReturnType<typeof setTimeout>[]>([])

  useEffect(() => {
    const unsub = useGameStore.subscribe((state) => {
      const { lastPlacedCell, blocks, gamePhase, biome, saturation } = state
      if (!lastPlacedCell || gamePhase !== 'playing') return
      // Object reference check: only fire when a NEW placement object arrives
      if (lastPlacedCell === lastSeenCell.current) return
      lastSeenCell.current = lastPlacedCell

      const { col, row } = lastPlacedCell
      const originKey = blockKey(col, row)

      // BFS from the newly placed block
      const visited = new Set<string>([originKey])
      const queue: Array<{ col: number; row: number; depth: number }> = []

      for (const [dc, dr] of DIRS) {
        const nc = col + dc; const nr = row + dr
        const nk = blockKey(nc, nr)
        if (blocks.has(nk) && !visited.has(nk)) {
          visited.add(nk)
          queue.push({ col: nc, row: nr, depth: 1 })
        }
      }

      if (queue.length === 0) return // isolated block — no cascade

      // Expand BFS up to MAX_DEPTH
      let qi = 0
      while (qi < queue.length) {
        const cur = queue[qi++]
        if (cur.depth >= MAX_DEPTH) continue
        for (const [dc, dr] of DIRS) {
          const nc = cur.col + dc; const nr = cur.row + dr
          const nk = blockKey(nc, nr)
          if (blocks.has(nk) && !visited.has(nk)) {
            visited.add(nk)
            queue.push({ col: nc, row: nr, depth: cur.depth + 1 })
          }
        }
      }

      const chainLength = queue.length // number of cascaded blocks (excluding origin)

      // Announce the chain to any FX layers listening (camera breath, bloom bump,
      // particle burst, audio swell). `triggerChain` also flips `hasTriggeredChain`
      // for the portal unlock when chainLength >= 3.
      getGameState().triggerChain(col, row, chainLength)

      // Audio swell — subtle bus volume bump on big cascades only.
      if (chainLength >= 5) chainSwell()

      // Schedule each cascade step
      for (const cb of queue) {
        const delay = cb.depth * STEP_DELAY_MS
        const tid = setTimeout(() => {
          const s = getGameState()
          if (s.gamePhase !== 'playing') return

          const block = s.blocks.get(blockKey(cb.col, cb.row))
          if (!block) return

          // Visual pulse
          s.setPulsingBlocks([blockKey(cb.col, cb.row)])

          // Play this block's note — creates the cascade melody
          triggerPlacementNote(block.row, block.instrumentIndex)
        }, delay)
        timeouts.current.push(tid)
      }

      // Saturation bonus: chains of ≥2 give extra color bleed
      // A 5-block chain ≈ 3× the saturation of a single placement
      if (chainLength >= MIN_CHAIN_FOR_BONUS) {
        const bonusBlocks = Math.min(chainLength * 0.5, 4) // up to 4 extra "virtual blocks"
        const newSat = Math.min(1, (blocks.size + bonusBlocks) / biome.maxSaturationBlocks)
        if (newSat > saturation) {
          const bonusDelay = chainLength * STEP_DELAY_MS + 60
          const tid = setTimeout(() => {
            const s = getGameState()
            if (s.saturation < newSat) {
              useGameStore.setState({ saturation: newSat })
            }
          }, bonusDelay)
          timeouts.current.push(tid)
        }
      }
    })

    return () => {
      unsub()
      // Cancel any pending cascade timeouts on unmount
      for (const tid of timeouts.current) clearTimeout(tid)
      timeouts.current = []
    }
  }, [])
}
