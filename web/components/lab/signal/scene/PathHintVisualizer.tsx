'use client'

// Glows the monster's next predicted step(s), fading toward the edge.
// The closer a cell is to the edge, the brighter the warning — loss
// aversion made visible.
//
// Active only when mode === 'cage' && gamePhase === 'playing' && a
// monster exists. In Zen Mode this is invisible and skipped.

import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { getGameState } from '../engine/useGameStore'
import { gridToWorld, TILE_SIZE } from '../utils/isoMath'
import { predictPath } from '../cage/enclosure'
import { CAGE_COLS, CAGE_ROWS } from '../cage/levels'

const MAX_HINT_CELLS = 6
const HINT_DEPTH = 3 // show up to 3 steps ahead

export default function PathHintVisualizer() {
  const ref = useRef<THREE.InstancedMesh>(null!)
  // Pre-allocated Three objects — never allocated in useFrame.
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
      !!state.monster &&
      !!state.cageLevel &&
      state.cageLevel.rule !== 'static' &&
      state.cageLevel.rule !== 'silence'

    if (!shouldRender || !state.monster) {
      for (let i = 0; i < MAX_HINT_CELLS; i++) {
        dummy.scale.set(0, 0, 0)
        dummy.updateMatrix()
        mesh.setMatrixAt(i, dummy.matrix)
      }
      mesh.instanceMatrix.needsUpdate = true
      mesh.count = 0
      return
    }

    const path = predictPath(
      state.monster,
      state.blocks,
      CAGE_COLS,
      CAGE_ROWS,
      HINT_DEPTH,
    )

    const visible = Math.min(path.length, MAX_HINT_CELLS)
    for (let i = 0; i < visible; i++) {
      const cell = path[i]
      const [x, , z] = gridToWorld(cell.col, cell.row)
      dummy.position.set(x, TILE_SIZE * 0.08, z)
      dummy.scale.set(TILE_SIZE * 1.02, 0.08, TILE_SIZE * 1.02)
      dummy.updateMatrix()
      mesh.setMatrixAt(i, dummy.matrix)
      // Brighter for closer-to-monster cells, dimmer further ahead
      const u = i / Math.max(1, HINT_DEPTH)
      const intensity = (1 - u) * 1.4 + 0.25
      tmpColor.copy(baseColor).multiplyScalar(intensity)
      mesh.setColorAt(i, tmpColor)
    }

    for (let i = visible; i < MAX_HINT_CELLS; i++) {
      dummy.scale.set(0, 0, 0)
      dummy.updateMatrix()
      mesh.setMatrixAt(i, dummy.matrix)
    }

    mesh.instanceMatrix.needsUpdate = true
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true
    mesh.count = visible
  })

  return (
    <instancedMesh ref={ref} args={[undefined, undefined, MAX_HINT_CELLS]}>
      <boxGeometry args={[1, 1, 1]} />
      <meshBasicMaterial color="#ffffff" transparent opacity={0.55} toneMapped={false} />
    </instancedMesh>
  )
}
