'use client'

// Glows the monsters' next predicted steps, fading toward each edge. The
// closer a cell is to a monster, the brighter the warning. With multiple
// monsters, paths overlap on cells that several monsters pass through —
// the brightest contribution wins (loss aversion stays legible).
//
// Active only when mode === 'cage' && gamePhase === 'playing'.

import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { getGameState } from '../engine/useGameStore'
import { gridToWorld, TILE_SIZE, blockKey } from '../utils/isoMath'
import { predictPath } from '../cage/enclosure'
import { CAGE_COLS, CAGE_ROWS } from '../cage/levels'

const MAX_HINT_CELLS = 24       // up to 4 monsters × 6 cells
const HINT_DEPTH = 5            // 5 steps ahead per monster

export default function PathHintVisualizer() {
  const ref = useRef<THREE.InstancedMesh>(null!)
  const dummy = useMemo(() => new THREE.Object3D(), [])
  const tmpColor = useMemo(() => new THREE.Color(), [])
  const baseColor = useMemo(() => new THREE.Color('#cc3333'), [])

  useFrame(() => {
    const mesh = ref.current
    if (!mesh) return
    const state = getGameState()

    const shouldRender =
      state.mode === 'cage' &&
      state.gamePhase === 'playing' &&
      state.monsters.length > 0 &&
      !!state.cageLevel

    if (!shouldRender) {
      for (let i = 0; i < MAX_HINT_CELLS; i++) {
        dummy.scale.set(0, 0, 0)
        dummy.updateMatrix()
        mesh.setMatrixAt(i, dummy.matrix)
      }
      mesh.instanceMatrix.needsUpdate = true
      mesh.count = 0
      return
    }

    // Aggregate path cells across all moving monsters. Brightest contribution
    // wins per cell.
    const cellIntensity = new Map<string, { col: number; row: number; intensity: number }>()
    for (const m of state.monsters) {
      if (m.rule === 'static' || m.rule === 'silence') continue
      const path = predictPath(m, state.blocks, CAGE_COLS, CAGE_ROWS, HINT_DEPTH)
      for (let i = 0; i < path.length; i++) {
        const cell = path[i]
        const u = i / Math.max(1, HINT_DEPTH)
        const intensity = (1 - u) * 1.4 + 0.25
        const k = blockKey(cell.col, cell.row)
        const prev = cellIntensity.get(k)
        if (!prev || prev.intensity < intensity) {
          cellIntensity.set(k, { col: cell.col, row: cell.row, intensity })
        }
      }
    }

    const cells = Array.from(cellIntensity.values()).slice(0, MAX_HINT_CELLS)
    for (let i = 0; i < cells.length; i++) {
      const cell = cells[i]
      const [x, , z] = gridToWorld(cell.col, cell.row)
      dummy.position.set(x, TILE_SIZE * 0.08, z)
      dummy.scale.set(TILE_SIZE * 1.02, 0.08, TILE_SIZE * 1.02)
      dummy.updateMatrix()
      mesh.setMatrixAt(i, dummy.matrix)
      tmpColor.copy(baseColor).multiplyScalar(cell.intensity)
      mesh.setColorAt(i, tmpColor)
    }

    for (let i = cells.length; i < MAX_HINT_CELLS; i++) {
      dummy.scale.set(0, 0, 0)
      dummy.updateMatrix()
      mesh.setMatrixAt(i, dummy.matrix)
    }

    mesh.instanceMatrix.needsUpdate = true
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true
    mesh.count = cells.length
  })

  return (
    <instancedMesh ref={ref} args={[undefined, undefined, MAX_HINT_CELLS]}>
      <boxGeometry args={[1, 1, 1]} />
      <meshBasicMaterial color="#ffffff" transparent opacity={0.55} toneMapped={false} />
    </instancedMesh>
  )
}
