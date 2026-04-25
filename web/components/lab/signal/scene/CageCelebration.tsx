'use client'

// Per-world celebration on monster-cage. Each biome gets a distinct visual
// signature on top of the existing camera-breath / bloom-bump / particle-burst
// stack. All variants are GPU-batched (drei Sparkles) so cost is <1ms/frame.

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
  yOffset: number   // hover above the cell
}

// World-specific celebration personalities. Index = worldIndex (0..4).
const VARIANT_BY_WORLD: BurstSpec[] = [
  // 0 — The Signal: tight white sparkle puff (default tutorial-friendly)
  { count: 80,  size: 12, scale: [3.5, 2.8, 3.5], speed: 1.2, noise: 2.1, yOffset: 0.6 },
  // 1 — The Temple: vertical golden column rising
  { count: 110, size: 10, scale: [1.6, 6.0, 1.6], speed: 1.6, noise: 1.4, yOffset: 1.4 },
  // 2 — The Deep: wide cyan ripple, low and broad
  { count: 140, size: 9,  scale: [6.0, 1.2, 6.0], speed: 0.9, noise: 2.6, yOffset: 0.25 },
  // 3 — The Garden: green falling-leaves spread, slow drift
  { count: 130, size: 13, scale: [5.2, 4.0, 5.2], speed: 0.6, noise: 3.4, yOffset: 1.1 },
  // 4 — The Truth: bright sunburst — many big sparkles, fast spread
  { count: 180, size: 16, scale: [5.8, 5.8, 5.8], speed: 2.2, noise: 2.0, yOffset: 0.9 },
]

// Each biome gets two colours — primary + secondary halo — so the burst feels
// layered instead of monochrome. Falls back to white when biome has no accent.
function colorPairFor(worldIndex: number): [string, string] {
  switch (worldIndex) {
    case 0: return ['#ffffff', '#cccccc']
    case 1: return ['#ffd27a', '#ff8c5a']  // temple gold + ember
    case 2: return ['#7fdfff', '#3aa0e0']  // deep cyan + indigo wash
    case 3: return ['#a8e063', '#56ab2f']  // garden lime + leaf-green
    case 4: return ['#fff7c2', '#ffb84a']  // truth bright cream + sun-amber
    default: return ['#ffffff', '#aaaaaa']
  }
}

export default function CageCelebration() {
  const lastResult = useGameStore(s => s.cageLastResult)
  const mode       = useGameStore(s => s.mode)

  const [burst, setBurst] = useState<{
    x: number; z: number; worldIndex: number; at: number
  } | null>(null)
  const clearTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (mode !== 'cage') return
    if (!lastResult?.solved) return
    const s = getGameState()
    if (!s.monster) return
    const [x, , z] = gridToWorld(s.monster.col, s.monster.row)
    setBurst({ x, z, worldIndex: s.worldIndex, at: performance.now() })
    if (clearTimer.current) clearTimeout(clearTimer.current)
    clearTimer.current = setTimeout(() => setBurst(null), LIFE_MS)
    return () => {
      if (clearTimer.current) clearTimeout(clearTimer.current)
    }
  }, [lastResult, mode])

  const variant = burst ? VARIANT_BY_WORLD[burst.worldIndex] ?? VARIANT_BY_WORLD[0] : null
  const [primary, secondary] = burst
    ? colorPairFor(burst.worldIndex)
    : ['#ffffff', '#ffffff']

  const colorPrimary   = useMemo(() => new THREE.Color(primary),   [primary])
  const colorSecondary = useMemo(() => new THREE.Color(secondary), [secondary])

  if (!burst || !variant) return null

  return (
    <group position={[burst.x, variant.yOffset * TILE_SIZE, burst.z]}>
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
      {/* Secondary halo — wider, fewer particles, slower, complementary tone */}
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
