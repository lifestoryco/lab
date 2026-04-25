'use client'

// MonsterPawn — renders all active cage monsters. Each pawn paces visually
// between its prev / next store-reported cell so motion feels smooth even
// though the logic is discrete (one cell per beat).
//
// Multi-monster: maps over the monsters array. Each pawn is keyed on the
// stable monster.id so React preserves per-pawn animation state across beats.
//
// Zen Mode: not mounted. See Monster.tsx for the gameover obelisk.

import { useEffect, useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { useGameStore } from '../engine/useGameStore'
import { gridToWorld, TILE_SIZE } from '../utils/isoMath'
import type { MonsterState } from '../cage/monster'

const PAWN_W = 0.56
const PAWN_H = 2.1
const SETTLE_MS = 220
const SPAWN_DURATION_MS = 900

// Subtle per-rule tint so two monsters in the same level read as different.
const RULE_EYE_COLOR: Record<MonsterState['rule'], string> = {
  static:  '#cc0000',
  drift:   '#cc0000',
  bounce:  '#ff8c00',  // amber — bounce reads as restless
  split:   '#cc66ff',  // violet — split reads as ghostly
  silence: '#7fdfff',  // pale cyan — silence reads as still
}

interface PawnProps {
  monster: MonsterState
  show: boolean
  endKind: 'solved' | 'failed' | null
  endAt: number | null
}

function SinglePawn({ monster, show, endKind, endAt }: PawnProps) {
  const groupRef = useRef<THREE.Group>(null!)
  const rimMatRef = useRef<THREE.MeshBasicMaterial>(null!)

  const prevPos = useRef<{ col: number; row: number; t: number } | null>(null)
  const curPos  = useRef<{ col: number; row: number; t: number } | null>(null)
  const spawnAt = useRef<number | null>(null)

  const baseColor = useMemo(() => new THREE.Color('#100000'), [])
  const eyeColor = RULE_EYE_COLOR[monster.rule]

  useEffect(() => {
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
  }, [monster.col, monster.row])

  useFrame(() => {
    if (!groupRef.current || !show || !curPos.current) return
    const now = performance.now()

    const prev = prevPos.current ?? curPos.current
    const dt = Math.min(1, (now - curPos.current.t) / SETTLE_MS)
    const ease = 1 - Math.pow(1 - dt, 3)
    const col = prev.col + (curPos.current.col - prev.col) * ease
    const row = prev.row + (curPos.current.row - prev.row) * ease
    const [wx, , wz] = gridToWorld(col, row)

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

    let scale = 1
    if (endKind && endAt !== null) {
      const since = now - endAt
      const u = Math.min(1, since / 1200)
      if (endKind === 'solved') {
        y = y + u * 1.8
        scale = Math.max(0, 1 - u * 1.05)
        if (rimMatRef.current) {
          const flash = 1 - u
          rimMatRef.current.color.setRGB(flash, flash, flash)
        }
      } else {
        y = y - u * (PAWN_H + 0.6)
        if (rimMatRef.current) {
          const intensity = 0.5 * (1 - u)
          rimMatRef.current.color.setRGB(intensity, 0, 0)
        }
      }
    } else if (rimMatRef.current) {
      const pulse = 0.55 + 0.45 * Math.sin(now * 0.005)
      const intensity = 0.35 + 0.25 * pulse
      rimMatRef.current.color.setRGB(intensity, 0, 0)
    }

    groupRef.current.position.set(wx, y, wz)
    groupRef.current.scale.setScalar(scale)
  })

  if (!show) return null

  return (
    <group ref={groupRef}>
      <mesh>
        <boxGeometry args={[PAWN_W, PAWN_H, PAWN_W]} />
        <meshBasicMaterial color={baseColor} toneMapped={false} />
      </mesh>
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
      <mesh position={[0.09, PAWN_H / 2 - 0.28, PAWN_W / 2 + 0.005]}>
        <planeGeometry args={[0.04, 0.06]} />
        <meshBasicMaterial color={eyeColor} toneMapped={false} />
      </mesh>
      <mesh position={[-0.09, PAWN_H / 2 - 0.28, PAWN_W / 2 + 0.005]}>
        <planeGeometry args={[0.04, 0.06]} />
        <meshBasicMaterial color={eyeColor} toneMapped={false} />
      </mesh>
    </group>
  )
}

export default function MonsterPawn() {
  const mode        = useGameStore(s => s.mode)
  const monsters    = useGameStore(s => s.monsters)
  const gamePhase   = useGameStore(s => s.gamePhase)
  const lastResult  = useGameStore(s => s.cageLastResult)

  if (mode !== 'cage') return null

  const showAll =
    monsters.length > 0 &&
    (gamePhase === 'playing' || gamePhase === 'transition' ||
     gamePhase === 'gameover' || gamePhase === 'complete')

  const endKind = lastResult ? (lastResult.solved ? 'solved' : 'failed') : null
  const endAt = lastResult ? lastResult.at : null

  return (
    <>
      {monsters.map((m) => (
        <SinglePawn
          key={m.id}
          monster={m}
          show={showAll}
          endKind={endKind}
          endAt={endAt}
        />
      ))}
    </>
  )
}
