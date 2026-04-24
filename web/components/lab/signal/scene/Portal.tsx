'use client'

// Portal — glowing trilithon that appears at the grid's left edge when the player
// has placed enough blocks to survive. Built as an R3F mesh so it receives the
// PostFX Bloom pass and glows. Clickable: player can enter the portal early rather
// than waiting for nightfall.

import { useRef, useMemo, useCallback } from 'react'
import { useFrame, ThreeEvent } from '@react-three/fiber'
import * as THREE from 'three'
import { useGameStore, getGameState } from '../engine/useGameStore'
import { gridToWorld, GRID_ROWS, TILE_SIZE } from '../utils/isoMath'
import { stopTransport } from '../audio/audioEngine'

const PILLAR_W = 0.09          // cross-section of each pillar
const PORTAL_HEIGHT = 2.6      // pillar height (above grid surface)
const PORTAL_SPAN = 1.9        // z-distance between pillar centres
const GLOW_OPACITY_BASE = 0.12 // fill plane base opacity

// Left-of-grid offset: how many tile-widths to step outside col=0
const LEFT_OFFSET = TILE_SIZE * 1.6

export default function Portal() {
  const mat1 = useRef<THREE.MeshBasicMaterial>(null!)
  const mat2 = useRef<THREE.MeshBasicMaterial>(null!)
  const mat3 = useRef<THREE.MeshBasicMaterial>(null!)
  const matFill = useRef<THREE.MeshBasicMaterial>(null!)

  const gamePhase = useGameStore(s => s.gamePhase)
  const hasTriggeredChain = useGameStore(s => s.hasTriggeredChain)
  const biome = useGameStore(s => s.biome)
  const setGamePhase = useGameStore(s => s.setGamePhase)

  const isVisible = gamePhase === 'playing' && hasTriggeredChain

  // Position: one tile left of col=0, centred on Z axis
  const portalPos = useMemo((): [number, number, number] => {
    const [gx] = gridToWorld(0, Math.floor(GRID_ROWS / 2))
    return [gx - LEFT_OFFSET, 0, 0]
  }, [])

  // Accent colour — biome bright, or silver for world 1 (B&W)
  const accentHex = biome.palette.hasAccent ? biome.palette.bright : '#bbbbbb'
  const baseColor = useMemo(() => new THREE.Color(accentHex), [accentHex])

  useFrame(() => {
    if (!isVisible) return
    const t = performance.now() * 0.001
    const pulse = 0.85 + 0.15 * Math.sin(t * 1.7)
    const intensity = 3.2 * pulse // >1 drives PostFX Bloom

    const c = baseColor.clone().multiplyScalar(intensity)
    mat1.current?.color.copy(c)
    mat2.current?.color.copy(c)
    mat3.current?.color.copy(c)

    if (matFill.current) {
      matFill.current.color.copy(baseColor.clone().multiplyScalar(0.6 * pulse))
      matFill.current.opacity = (GLOW_OPACITY_BASE + 0.08 * Math.sin(t * 1.7)) * pulse
    }
  })

  // Early portal entry — player can choose when to advance
  const handleClick = useCallback((e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation()
    const state = getGameState()
    if (state.gamePhase !== 'playing') return
    if (!state.hasTriggeredChain) return
    stopTransport()
    setGamePhase('transition')
  }, [setGamePhase])

  if (!isVisible) return null

  return (
    <group position={portalPos} onPointerUp={handleClick}>
      {/* Left pillar */}
      <mesh position={[0, PORTAL_HEIGHT / 2, -PORTAL_SPAN / 2]}>
        <boxGeometry args={[PILLAR_W, PORTAL_HEIGHT, PILLAR_W]} />
        <meshBasicMaterial ref={mat1} color={baseColor.clone()} toneMapped={false} />
      </mesh>

      {/* Right pillar */}
      <mesh position={[0, PORTAL_HEIGHT / 2, PORTAL_SPAN / 2]}>
        <boxGeometry args={[PILLAR_W, PORTAL_HEIGHT, PILLAR_W]} />
        <meshBasicMaterial ref={mat2} color={baseColor.clone()} toneMapped={false} />
      </mesh>

      {/* Lintel */}
      <mesh position={[0, PORTAL_HEIGHT, 0]}>
        <boxGeometry args={[PILLAR_W, PILLAR_W, PORTAL_SPAN + PILLAR_W]} />
        <meshBasicMaterial ref={mat3} color={baseColor.clone()} toneMapped={false} />
      </mesh>

      {/* Translucent fill plane — gives depth to the arch */}
      <mesh position={[0, PORTAL_HEIGHT / 2 - 0.05, 0]}>
        <planeGeometry args={[0.06, PORTAL_HEIGHT - 0.1]} />
        <meshBasicMaterial
          ref={matFill}
          color={baseColor.clone()}
          transparent
          opacity={GLOW_OPACITY_BASE}
          side={THREE.DoubleSide}
          toneMapped={false}
          depthWrite={false}
        />
      </mesh>
    </group>
  )
}
