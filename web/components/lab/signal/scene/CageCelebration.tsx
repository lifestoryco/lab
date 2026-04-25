'use client'

// Per-world celebration on monster-cage. Each biome gets a distinct visual
// signature on top of the existing camera-breath / bloom-bump / particle-burst
// stack. All variants are GPU-batched (drei Sparkles) so cost is <1ms/frame.
//
// Sparkles instances stay mounted across cage solves and toggle visibility
// instead of unmount/remount, avoiding GPU buffer churn on iOS Safari.

import { useEffect, useMemo, useRef, useState } from 'react'
import { Sparkles } from '@react-three/drei'
import * as THREE from 'three'
import { useGameStore, getGameState } from '../engine/useGameStore'
import { gridToWorld, TILE_SIZE } from '../utils/isoMath'

const LIFE_MS = 2400

interface BurstSpec {
  count: number
  size: number
  scale: [number, number, number]
  speed: number
  noise: number
  yOffset: number
}

const VARIANT_BY_WORLD: BurstSpec[] = [
  { count: 80,  size: 12, scale: [3.5, 2.8, 3.5], speed: 1.2, noise: 2.1, yOffset: 0.6 },
  { count: 110, size: 10, scale: [1.6, 6.0, 1.6], speed: 1.6, noise: 1.4, yOffset: 1.4 },
  { count: 140, size: 9,  scale: [6.0, 1.2, 6.0], speed: 0.9, noise: 2.6, yOffset: 0.25 },
  { count: 130, size: 13, scale: [5.2, 4.0, 5.2], speed: 0.6, noise: 3.4, yOffset: 1.1 },
  { count: 180, size: 16, scale: [5.8, 5.8, 5.8], speed: 2.2, noise: 2.0, yOffset: 0.9 },
]

// Each biome gets two colours — primary core + secondary halo — so the burst
// silhouettes against the floor instead of washing into it. Secondary tones
// are intentionally darker / complementary so green-on-green and white-on-white
// floors still read.
function colorPairFor(worldIndex: number): [string, string] {
  switch (worldIndex) {
    case 0: return ['#ffffff', '#666666']  // signal: white core, charcoal halo
    case 1: return ['#ffd27a', '#7a3a10']  // temple: gold core, ember-brown halo
    case 2: return ['#7fdfff', '#0d3a66']  // deep:   cyan core, indigo halo
    case 3: return ['#a8e063', '#1a3d1a']  // garden: lime core, dark-green halo
    case 4: return ['#fff7c2', '#4a3000']  // truth:  cream core, deep-amber halo
    default: return ['#ffffff', '#222222']
  }
}

export default function CageCelebration() {
  const lastResult = useGameStore(s => s.cageLastResult)
  const mode       = useGameStore(s => s.mode)

  const [burst, setBurst] = useState<{
    x: number; z: number; worldIndex: number; at: number
  } | null>(null)
  const clearTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Effect cleanup must run unconditionally so a mid-burst unmount or rapid
  // result-change cancels any pending setBurst(null).
  useEffect(() => {
    if (mode !== 'cage') return
    if (!lastResult?.solved) return
    const s = getGameState()
    if (!s.monster) return
    const [x, , z] = gridToWorld(s.monster.col, s.monster.row)
    setBurst({ x, z, worldIndex: s.worldIndex, at: performance.now() })
    if (clearTimer.current) clearTimeout(clearTimer.current)
    clearTimer.current = setTimeout(() => setBurst(null), LIFE_MS)
  }, [lastResult, mode])

  useEffect(() => () => {
    if (clearTimer.current) clearTimeout(clearTimer.current)
  }, [])

  // Use the burst's worldIndex for variant selection while the burst is live;
  // when no burst, fall back to current world so geometry is pre-allocated for
  // the upcoming world's variant.
  const fallbackWorld = useGameStore(s => s.worldIndex)
  const activeWorld = burst?.worldIndex ?? fallbackWorld
  const variant = VARIANT_BY_WORLD[activeWorld] ?? VARIANT_BY_WORLD[0]
  const [primary, secondary] = colorPairFor(activeWorld)

  const colorPrimary   = useMemo(() => new THREE.Color(primary),   [primary])
  const colorSecondary = useMemo(() => new THREE.Color(secondary), [secondary])

  const x = burst?.x ?? 0
  const z = burst?.z ?? 0
  const visible = !!burst

  return (
    <group position={[x, variant.yOffset * TILE_SIZE, z]} visible={visible}>
      {/* Primary core burst */}
      <Sparkles
        count={variant.count}
        size={variant.size}
        scale={variant.scale}
        speed={variant.speed}
        noise={variant.noise}
        color={colorPrimary}
        opacity={0.95}
      />
      {/* Secondary halo — wider, complementary tone so the burst stays legible
          against any biome floor. */}
      <Sparkles
        count={Math.round(variant.count * 0.45)}
        size={variant.size * 1.6}
        scale={[variant.scale[0] * 1.35, variant.scale[1] * 1.1, variant.scale[2] * 1.35]}
        speed={variant.speed * 0.55}
        noise={variant.noise * 1.2}
        color={colorSecondary}
        opacity={0.55}
      />
    </group>
  )
}
