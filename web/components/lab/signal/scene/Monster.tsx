'use client'

// Monster — a dark obelisk that rises through the grid on game over.
// Appears only when the player didn't have enough blocks at nightfall.
// Uses the bloom pipeline: the faint red rim emits above threshold so it
// halos against the black scene.

import { useRef, useEffect } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { useGameStore } from '../engine/useGameStore'
import { easeOutExpo, easeInOutQuad } from '../utils/easing'

const RISE_DURATION_MS = 2800
const OBELISK_W = 1.1
const OBELISK_D = 0.38
const OBELISK_H = 4.5
const START_Y = -6
const END_Y = 1.6

export default function Monster() {
  const gamePhase = useGameStore(s => s.gamePhase)
  const groupRef = useRef<THREE.Group>(null!)
  const rimMatRef = useRef<THREE.MeshBasicMaterial>(null!)
  const spawnTime = useRef<number | null>(null)

  useEffect(() => {
    if (gamePhase === 'gameover') {
      spawnTime.current = performance.now()
    } else {
      spawnTime.current = null
    }
  }, [gamePhase])

  useFrame(() => {
    if (!groupRef.current || !spawnTime.current || gamePhase !== 'gameover') return

    const elapsed = performance.now() - spawnTime.current
    const t = Math.min(1, elapsed / RISE_DURATION_MS)
    const y = START_Y + easeOutExpo(t) * (END_Y - START_Y)
    groupRef.current.position.y = y

    // Slow red rim pulse — intensifies as the obelisk finishes rising
    if (rimMatRef.current) {
      const settled = easeInOutQuad(t)
      const pulse = 0.5 + 0.5 * Math.sin(performance.now() * 0.001 * 0.6)
      const intensity = settled * (0.4 + 0.15 * pulse)
      rimMatRef.current.color.setRGB(intensity, 0, 0)
    }
  })

  if (gamePhase !== 'gameover') return null

  return (
    <group ref={groupRef} position={[0, START_Y, 0]}>
      {/* Core body — near-black monolith */}
      <mesh>
        <boxGeometry args={[OBELISK_W, OBELISK_H, OBELISK_D]} />
        <meshBasicMaterial color="#080808" toneMapped={false} />
      </mesh>

      {/* Rim glow — BackSide mesh slightly larger; bloom picks up the red */}
      <mesh>
        <boxGeometry args={[OBELISK_W + 0.08, OBELISK_H + 0.06, OBELISK_D + 0.08]} />
        <meshBasicMaterial
          ref={rimMatRef}
          color="#000000"
          toneMapped={false}
          side={THREE.BackSide}
          transparent
          opacity={0.9}
          depthWrite={false}
        />
      </mesh>

      {/* Twin eye-slits — two tiny emissive planes near the top */}
      <mesh position={[0.18, OBELISK_H / 2 - 0.55, OBELISK_D / 2 + 0.01]}>
        <planeGeometry args={[0.06, 0.12]} />
        <meshBasicMaterial color="#cc0000" toneMapped={false} />
      </mesh>
      <mesh position={[-0.18, OBELISK_H / 2 - 0.55, OBELISK_D / 2 + 0.01]}>
        <planeGeometry args={[0.06, 0.12]} />
        <meshBasicMaterial color="#cc0000" toneMapped={false} />
      </mesh>
    </group>
  )
}
