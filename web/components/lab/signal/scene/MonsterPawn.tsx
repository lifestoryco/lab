'use client'

// MonsterPawn — an in-play rendering of the Monster obelisk, shrunk and
// placed on a grid cell. Paces visually between its previous and next
// store-reported position so motion feels smooth even though the logic
// is discrete (one cell per beat).
//
// Zen Mode: not mounted. See Monster.tsx for the gameover obelisk.

import { useEffect, useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { useGameStore } from '../engine/useGameStore'
import { gridToWorld, TILE_SIZE } from '../utils/isoMath'

// Larger pawn for mobile readability. Was 0.38 × 1.55.
const PAWN_W = 0.56
const PAWN_H = 2.1
const SETTLE_MS = 220         // lerp between grid cells
const SPAWN_DURATION_MS = 900 // rise out of the floor on level start

export default function MonsterPawn() {
  const mode        = useGameStore(s => s.mode)
  const monster     = useGameStore(s => s.monster)
  const gamePhase   = useGameStore(s => s.gamePhase)
  const cageLevel   = useGameStore(s => s.cageLevel)
  const lastResult  = useGameStore(s => s.cageLastResult)

  const groupRef = useRef<THREE.Group>(null!)
  const rimMatRef = useRef<THREE.MeshBasicMaterial>(null!)

  // Per-session interpolation state
  const prevPos = useRef<{ col: number; row: number; t: number } | null>(null)
  const curPos  = useRef<{ col: number; row: number; t: number } | null>(null)
  const spawnAt = useRef<number | null>(null)
  // End animation: set on both solve and fail. `kind` picks the treatment
  // (bright white flash + upward lift + fade for solve; red + sink for fail).
  const endAt   = useRef<{ t: number; kind: 'solved' | 'failed' } | null>(null)

  const show =
    mode === 'cage' &&
    !!monster &&
    (gamePhase === 'playing' || gamePhase === 'transition' ||
     gamePhase === 'gameover' || gamePhase === 'complete' || endAt.current !== null)

  // Track monster cell changes — start an interpolation
  useEffect(() => {
    if (!monster) {
      prevPos.current = null
      curPos.current = null
      spawnAt.current = null
      return
    }
    const now = performance.now()
    if (!curPos.current) {
      curPos.current = { col: monster.col, row: monster.row, t: now }
      prevPos.current = curPos.current
      spawnAt.current = now
      return
    }
    if (curPos.current.col !== monster.col || curPos.current.row !== monster.row) {
      prevPos.current = curPos.current
      curPos.current = { col: monster.col, row: monster.row, t: now }
    }
  }, [monster, cageLevel?.worldIndex])

  // Track solve/fail — schedule the end animation.
  useEffect(() => {
    if (lastResult) {
      endAt.current = { t: performance.now(), kind: lastResult.solved ? 'solved' : 'failed' }
    } else {
      endAt.current = null
    }
  }, [lastResult])

  const baseColor = useMemo(() => new THREE.Color('#100000'), [])

  useFrame(() => {
    if (!groupRef.current || !show || !curPos.current) return
    const now = performance.now()

    // Interpolate position between prev and current grid cells
    const prev = prevPos.current ?? curPos.current
    const dt = Math.min(1, (now - curPos.current.t) / SETTLE_MS)
    const ease = 1 - Math.pow(1 - dt, 3)
    const col = prev.col + (curPos.current.col - prev.col) * ease
    const row = prev.row + (curPos.current.row - prev.row) * ease
    const [wx, , wz] = gridToWorld(col, row)

    // Rise animation on spawn
    let y = PAWN_H / 2 + TILE_SIZE * 0.05
    if (spawnAt.current) {
      const since = now - spawnAt.current
      if (since < SPAWN_DURATION_MS) {
        const u = 1 - Math.pow(1 - since / SPAWN_DURATION_MS, 3)
        y = -PAWN_H * (1 - u) + y * u
      } else {
        spawnAt.current = null
      }
    }

    // End animation: cage-solved flashes bright white + dissolves upward;
    // escape fails sinks red into the grid.
    let scale = 1
    if (endAt.current) {
      const since = now - endAt.current.t
      const u = Math.min(1, since / 1200)
      if (endAt.current.kind === 'solved') {
        // Rise + shrink + flash white
        y = y + u * 1.8
        scale = Math.max(0, 1 - u * 1.05)
        if (rimMatRef.current) {
          const flash = 1 - u
          // White → cool blue-white sparkle as it dissolves
          rimMatRef.current.color.setRGB(flash, flash, flash)
        }
      } else {
        // Sink red
        y = y - u * (PAWN_H + 0.6)
        if (rimMatRef.current) {
          const intensity = 0.5 * (1 - u)
          rimMatRef.current.color.setRGB(intensity, 0, 0)
        }
      }
    } else if (rimMatRef.current) {
      // Normal red-eye pulse
      const pulse = 0.55 + 0.45 * Math.sin(now * 0.005)
      const intensity = 0.35 + 0.25 * pulse
      rimMatRef.current.color.setRGB(intensity, 0, 0)
    }

    groupRef.current.position.set(wx, y, wz)
    groupRef.current.scale.setScalar(scale)
  })

  if (!show || !monster) return null

  return (
    <group ref={groupRef}>
      {/* Core monolith */}
      <mesh>
        <boxGeometry args={[PAWN_W, PAWN_H, PAWN_W]} />
        <meshBasicMaterial color={baseColor} toneMapped={false} />
      </mesh>
      {/* Rim glow — BackSide mesh picks up bloom */}
      <mesh>
        <boxGeometry args={[PAWN_W + 0.06, PAWN_H + 0.04, PAWN_W + 0.06]} />
        <meshBasicMaterial
          ref={rimMatRef}
          color="#220000"
          toneMapped={false}
          side={THREE.BackSide}
          transparent
          opacity={0.9}
          depthWrite={false}
        />
      </mesh>
      {/* Twin eye-slits — same as the gameover obelisk */}
      <mesh position={[0.09, PAWN_H / 2 - 0.28, PAWN_W / 2 + 0.005]}>
        <planeGeometry args={[0.04, 0.06]} />
        <meshBasicMaterial color="#cc0000" toneMapped={false} />
      </mesh>
      <mesh position={[-0.09, PAWN_H / 2 - 0.28, PAWN_W / 2 + 0.005]}>
        <planeGeometry args={[0.04, 0.06]} />
        <meshBasicMaterial color="#cc0000" toneMapped={false} />
      </mesh>
    </group>
  )
}
