'use client'

// Big synesthetic celebration when the monster is caged. Builds on the
// existing chain-cascade stack (camera breath + bloom bump + particle burst
// + audio swell) by adding a swirling Sparkles field at the cage origin.
// Per-world tint = biome accent.
//
// Uses @react-three/drei's Sparkles — GPU-batched, <1ms overhead per frame.

import { useEffect, useMemo, useRef, useState } from 'react'
import { Sparkles } from '@react-three/drei'
import * as THREE from 'three'
import { useGameStore, getGameState } from '../engine/useGameStore'
import { gridToWorld, TILE_SIZE } from '../utils/isoMath'

const LIFE_MS = 2200

export default function CageCelebration() {
  const lastResult = useGameStore(s => s.cageLastResult)
  const mode       = useGameStore(s => s.mode)

  const [burst, setBurst] = useState<{
    x: number; z: number; y: number; accent: string; at: number
  } | null>(null)
  const clearTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (mode !== 'cage') return
    if (!lastResult?.solved) return
    const s = getGameState()
    if (!s.monster) return
    const [x, , z] = gridToWorld(s.monster.col, s.monster.row)
    const accent = s.biome.palette.hasAccent ? s.biome.palette.bright : '#ffffff'
    setBurst({
      x,
      z,
      y: TILE_SIZE * 0.6,
      accent,
      at: performance.now(),
    })
    if (clearTimer.current) clearTimeout(clearTimer.current)
    clearTimer.current = setTimeout(() => setBurst(null), LIFE_MS)
    return () => {
      if (clearTimer.current) clearTimeout(clearTimer.current)
    }
  }, [lastResult, mode])

  const color = useMemo(() => new THREE.Color(burst?.accent ?? '#ffffff'), [burst?.accent])

  if (!burst) return null

  return (
    <group position={[burst.x, burst.y, burst.z]}>
      <Sparkles
        count={80}
        size={12}
        scale={[3.5, 2.8, 3.5]}
        speed={1.2}
        noise={2.1}
        color={color}
        opacity={0.95}
      />
    </group>
  )
}
