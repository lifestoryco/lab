'use client'

// Lantern reveal — world 5 special. While revealActiveUntil is in the future,
// pulses a soft halo on the silence-rule's correct cell (centre of the cage
// grid). The mechanic in useCage uses the same SILENCE_CELL constant.

import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { getGameState } from '../engine/useGameStore'
import { gridToWorld, TILE_SIZE } from '../utils/isoMath'
import { CAGE_COLS, CAGE_ROWS } from '../cage/levels'

const CENTER_COL = Math.floor(CAGE_COLS / 2)
const CENTER_ROW = Math.floor(CAGE_ROWS / 2)
const ACCENT = '#ffcb6b'

export default function RevealMarker() {
  const ringRef = useRef<THREE.Mesh>(null)
  const coreRef = useRef<THREE.Mesh>(null)
  const groupRef = useRef<THREE.Group>(null)

  const [x, , z] = gridToWorld(CENTER_COL, CENTER_ROW)

  useFrame(() => {
    const s = getGameState()
    const expires = s.revealActiveUntil
    const visible = !!expires && performance.now() < expires
    if (groupRef.current) groupRef.current.visible = visible
    if (!visible) return

    // Soft 1.2Hz pulse over the reveal duration.
    const t = performance.now() * 0.001
    const pulse = 0.5 + 0.5 * Math.sin(t * 7.5)
    if (ringRef.current) {
      const m = ringRef.current.material as THREE.MeshBasicMaterial
      m.opacity = 0.35 + pulse * 0.45
      ringRef.current.scale.setScalar(1.0 + pulse * 0.18)
    }
    if (coreRef.current) {
      const m = coreRef.current.material as THREE.MeshBasicMaterial
      m.opacity = 0.55 + pulse * 0.4
    }
  })

  return (
    <group ref={groupRef} position={[x, TILE_SIZE * 0.05, z]} visible={false}>
      {/* Floor halo */}
      <mesh ref={ringRef} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[TILE_SIZE * 0.45, TILE_SIZE * 0.85, 48]} />
        <meshBasicMaterial color={ACCENT} transparent opacity={0.6} side={THREE.DoubleSide} />
      </mesh>
      {/* Glowing core dot — visible through bloom */}
      <mesh ref={coreRef} position={[0, TILE_SIZE * 0.05, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[TILE_SIZE * 0.32, 32]} />
        <meshBasicMaterial color={ACCENT} transparent opacity={0.85} />
      </mesh>
    </group>
  )
}
