// Monster stepping logic. Pure functions — the state lives in the Zustand
// store, the `useCage` hook invokes these on each playhead beat.

import type { CageRule } from './levels'
import { nextStepTowardEdge } from './enclosure'
import { blockKey } from '../utils/isoMath'

export interface MonsterState {
  col: number
  row: number
  // For 'bounce': current direction vector. Resets on block collision.
  dirCol: number
  dirRow: number
  // For 'split': position of the echo pawn (one step behind), or null.
  echoCol: number | null
  echoRow: number | null
}

export function spawnMonster(startCol: number, startRow: number): MonsterState {
  return {
    col: startCol,
    row: startRow,
    dirCol: 1, // default drift right on first move
    dirRow: 0,
    echoCol: null,
    echoRow: null,
  }
}

export interface StepResult {
  next: MonsterState
  // If true, monster reached a grid edge on this step → escape (lose condition).
  escaped: boolean
  // Note to play when the monster steps (optional — caller plays it).
  row: number
}

// Execute one step per the rule. Returns the new position and whether it escaped.
export function stepMonster(
  m: MonsterState,
  blocks: Map<string, unknown>,
  cols: number,
  rows: number,
  rule: CageRule,
): StepResult {
  switch (rule) {
    case 'static':
    case 'silence':
      return { next: m, escaped: false, row: m.row }

    case 'drift': {
      const next = nextStepTowardEdge(m, blocks, cols, rows)
      if (!next) return { next: m, escaped: false, row: m.row } // boxed in
      const atEdge =
        next.col === 0 || next.col === cols - 1 ||
        next.row === 0 || next.row === rows - 1
      return {
        next: { ...m, col: next.col, row: next.row },
        escaped: atEdge,
        row: next.row,
      }
    }

    case 'bounce': {
      // Try current direction. If blocked, reflect 90° clockwise and try again.
      let dirCol = m.dirCol
      let dirRow = m.dirRow
      for (let attempt = 0; attempt < 4; attempt++) {
        const nc = m.col + dirCol
        const nr = m.row + dirRow
        const inBounds = nc >= 0 && nc < cols && nr >= 0 && nr < rows
        const blocked = !inBounds || blocks.has(blockKey(nc, nr))
        if (!blocked) {
          const atEdge = nc === 0 || nc === cols - 1 || nr === 0 || nr === rows - 1
          return {
            next: { ...m, col: nc, row: nr, dirCol, dirRow },
            escaped: atEdge,
            row: nr,
          }
        }
        // rotate 90° clockwise: (dc, dr) → (-dr, dc)
        const newDc = -dirRow
        const newDr = dirCol
        dirCol = newDc
        dirRow = newDr
      }
      // Boxed in on all 4 sides (trapped) — stay put.
      return { next: m, escaped: false, row: m.row }
    }

    case 'split': {
      // Main pawn drifts toward edge; echo follows one step behind on the
      // previous main position.
      const prevCol = m.col
      const prevRow = m.row
      const next = nextStepTowardEdge(m, blocks, cols, rows)
      if (!next) return { next: m, escaped: false, row: m.row }
      const atEdge =
        next.col === 0 || next.col === cols - 1 ||
        next.row === 0 || next.row === rows - 1
      return {
        next: {
          ...m,
          col: next.col,
          row: next.row,
          echoCol: prevCol,
          echoRow: prevRow,
        },
        escaped: atEdge,
        row: next.row,
      }
    }
  }
}
