// Enclosure detection for Cage Mode.
// Mirror of useChainReaction's BFS, but flood-fills EMPTY cells instead
// of filled ones: start at the monster's cell, walk through every empty
// neighbor, stop when we reach a grid edge OR exhaust the reachable region.
//
// Returns {trapped, reachable} — trapped = true iff no edge cell was reachable.
// `reachable` is the set of empty cells the monster could still move through
// (used for "cage size" scoring and the edge-distance fade effect in W5).

import { blockKey } from '../utils/isoMath'

export interface EnclosureResult {
  trapped: boolean
  reachable: Set<string>
  edgeCells: Set<string>          // edge cells the monster could still reach
  distanceToEdge: number          // 0 = at edge, Infinity = fully trapped
}

const DIRS: [number, number][] = [[-1, 0], [1, 0], [0, -1], [0, 1]]

export function isEnclosed(
  monster: { col: number; row: number },
  blocks: Map<string, unknown>,
  cols: number,
  rows: number,
): EnclosureResult {
  const origin = blockKey(monster.col, monster.row)
  const visited = new Set<string>([origin])
  const reachable = new Set<string>([origin])
  const edgeCells = new Set<string>()
  const queue: Array<{ col: number; row: number; depth: number }> = [
    { col: monster.col, row: monster.row, depth: 0 },
  ]
  let minEdgeDepth = Infinity

  while (queue.length > 0) {
    const cur = queue.shift()!
    const atEdge =
      cur.col === 0 || cur.col === cols - 1 ||
      cur.row === 0 || cur.row === rows - 1
    if (atEdge) {
      edgeCells.add(blockKey(cur.col, cur.row))
      if (cur.depth < minEdgeDepth) minEdgeDepth = cur.depth
    }
    for (const [dc, dr] of DIRS) {
      const nc = cur.col + dc
      const nr = cur.row + dr
      if (nc < 0 || nc >= cols || nr < 0 || nr >= rows) continue
      const k = blockKey(nc, nr)
      if (visited.has(k)) continue
      if (blocks.has(k)) continue // wall — monster cannot cross
      visited.add(k)
      reachable.add(k)
      queue.push({ col: nc, row: nr, depth: cur.depth + 1 })
    }
  }

  return {
    trapped: edgeCells.size === 0,
    reachable,
    edgeCells,
    distanceToEdge: minEdgeDepth,
  }
}

// Returns the next cell the monster would step toward the nearest edge,
// following the shortest-path first-step produced by BFS.
// null = fully trapped, no legal move.
export function nextStepTowardEdge(
  monster: { col: number; row: number },
  blocks: Map<string, unknown>,
  cols: number,
  rows: number,
): { col: number; row: number } | null {
  // BFS layer by layer; remember the first step taken out of origin
  const origin = blockKey(monster.col, monster.row)
  const visited = new Set<string>([origin])
  type Node = { col: number; row: number; firstStep: { col: number; row: number } | null }
  const queue: Node[] = [{ col: monster.col, row: monster.row, firstStep: null }]

  while (queue.length > 0) {
    const cur = queue.shift()!
    const atEdge =
      cur.col === 0 || cur.col === cols - 1 ||
      cur.row === 0 || cur.row === rows - 1
    if (atEdge && cur.firstStep) {
      return cur.firstStep
    }
    for (const [dc, dr] of DIRS) {
      const nc = cur.col + dc
      const nr = cur.row + dr
      if (nc < 0 || nc >= cols || nr < 0 || nr >= rows) continue
      const k = blockKey(nc, nr)
      if (visited.has(k)) continue
      if (blocks.has(k)) continue
      visited.add(k)
      queue.push({
        col: nc,
        row: nr,
        firstStep: cur.firstStep ?? { col: nc, row: nr },
      })
    }
  }
  return null
}

// Predict the monster's next N steps along the shortest path to an edge.
// Used by PathHintVisualizer to glow the cells ahead of it.
export function predictPath(
  monster: { col: number; row: number },
  blocks: Map<string, unknown>,
  cols: number,
  rows: number,
  maxSteps = 3,
): Array<{ col: number; row: number }> {
  const path: Array<{ col: number; row: number }> = []
  const virtualBlocks = new Map(blocks)
  let cursor = { col: monster.col, row: monster.row }
  for (let i = 0; i < maxSteps; i++) {
    const next = nextStepTowardEdge(cursor, virtualBlocks, cols, rows)
    if (!next) break
    path.push(next)
    // Mark the cell as "visited" for the next iteration so we don't loop.
    virtualBlocks.set(blockKey(cursor.col, cursor.row), true)
    cursor = next
  }
  return path
}
