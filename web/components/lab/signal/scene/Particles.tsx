'use client'

import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { getGameState } from '../engine/useGameStore'
import { perlin2 } from '../utils/perlin'
import { gridToWorld, GRID_COLS, GRID_ROWS, TILE_SIZE } from '../utils/isoMath'

// --- Ambient dust motes ---
const DUST_COUNT = 48

// Grid extends roughly ±8.5 on both axes (16 tiles × 1.08 effective, centered)
const GRID_HALF = ((GRID_COLS - 1) * 1.08) * 0.5 + 1.0 // ~8.7 + 1 = 9.7

interface DustMote {
  x: number
  y: number
  z: number
  phase: number    // unique Perlin phase offset
  speed: number    // drift speed multiplier
}

// --- Burst pool ---
const BURST_POOL = 192 // 16 simultaneous bursts × 12 grains

interface BurstParticle {
  x: number; y: number; z: number
  vx: number; vy: number; vz: number
  life: number
  maxLife: number
}

function initDust(): DustMote[] {
  return Array.from({ length: DUST_COUNT }, () => ({
    x: (Math.random() - 0.5) * GRID_HALF * 2,
    y: 0.3 + Math.random() * 2.5,
    z: (Math.random() - 0.5) * GRID_HALF * 2,
    phase: Math.random() * 100,
    speed: 0.25 + Math.random() * 0.35,
  }))
}

function initBurst(): BurstParticle[] {
  return Array.from({ length: BURST_POOL }, () => ({
    x: 0, y: 0, z: 0,
    vx: 0, vy: 0, vz: 0,
    life: 0,
    maxLife: 0.8,
  }))
}

export default function Particles() {
  const dustRef = useRef<THREE.InstancedMesh>(null!)
  const burstRef = useRef<THREE.InstancedMesh>(null!)

  const dust = useRef<DustMote[]>(initDust())
  const bursts = useRef<BurstParticle[]>(initBurst())

  const tmpMatrix = useMemo(() => new THREE.Matrix4(), [])
  const tmpColor  = useMemo(() => new THREE.Color(), [])
  const clock     = useRef(0)

  // Track last seen placement by object reference — no store mutation needed
  const lastSeenCell = useRef<{ col: number; row: number } | null>(null)

  // Track last chain celebration — spawns a bigger burst scaled by chain length
  const lastSeenChainAt = useRef<number>(0)

  // Next index to reuse in burst pool (ring buffer within dead particles)
  const burstPoolIdx = useRef(0)

  useFrame((_state, delta) => {
    clock.current += delta
    const t = clock.current

    // --- Spawn bursts from newly placed blocks ---
    const gameState = getGameState()
    const { lastPlacedCell, lastChain } = gameState
    if (lastPlacedCell && lastPlacedCell !== lastSeenCell.current) {
      lastSeenCell.current = lastPlacedCell
      const { col, row } = lastPlacedCell
      const [wx, , wz] = gridToWorld(col, row)
      const wy = TILE_SIZE * 0.5 + 0.1 // top of block

      // Spawn 12 grains radially, recycling dead slots
      let spawned = 0
      const poolSize = bursts.current.length
      for (let attempt = 0; attempt < poolSize && spawned < 12; attempt++) {
        const idx = (burstPoolIdx.current + attempt) % poolSize
        const p = bursts.current[idx]
        if (p.life <= 0) {
          const angle = (spawned / 12) * Math.PI * 2 + Math.random() * 0.4
          const horizSpeed = 1.2 + Math.random() * 1.6
          p.x = wx + (Math.random() - 0.5) * 0.2
          p.y = wy
          p.z = wz + (Math.random() - 0.5) * 0.2
          p.vx = Math.cos(angle) * horizSpeed * 0.55
          p.vy = 1.8 + Math.random() * 1.4
          p.vz = Math.sin(angle) * horizSpeed * 0.55
          p.maxLife = 0.55 + Math.random() * 0.35
          p.life = p.maxLife
          burstPoolIdx.current = (idx + 1) % poolSize
          spawned++
        }
      }
    }

    // --- Chain celebration burst: bigger, longer, scales with chain length ---
    if (lastChain && lastChain.at !== lastSeenChainAt.current && lastChain.length >= 3) {
      lastSeenChainAt.current = lastChain.at
      const [wx, , wz] = gridToWorld(lastChain.originCol, lastChain.originRow)
      const wy = TILE_SIZE * 0.5 + 0.2
      const count = Math.min(40, 8 + lastChain.length * 6)

      let spawned = 0
      const poolSize = bursts.current.length
      for (let attempt = 0; attempt < poolSize && spawned < count; attempt++) {
        const idx = (burstPoolIdx.current + attempt) % poolSize
        const p = bursts.current[idx]
        if (p.life <= 0) {
          const angle = (spawned / count) * Math.PI * 2 + Math.random() * 0.35
          const horizSpeed = 2.2 + Math.random() * 2.4
          p.x = wx + (Math.random() - 0.5) * 0.25
          p.y = wy
          p.z = wz + (Math.random() - 0.5) * 0.25
          p.vx = Math.cos(angle) * horizSpeed * 0.7
          p.vy = 2.6 + Math.random() * 1.8
          p.vz = Math.sin(angle) * horizSpeed * 0.7
          p.maxLife = 0.9 + Math.random() * 0.4
          p.life = p.maxLife
          burstPoolIdx.current = (idx + 1) % poolSize
          spawned++
        }
      }
    }

    // --- Update dust motes ---
    if (dustRef.current) {
      for (let i = 0; i < DUST_COUNT; i++) {
        const m = dust.current[i]

        // Perlin-driven drift in XZ plane
        const noiseX = perlin2(m.x * 0.25 + t * 0.08, m.phase)
        const noiseZ = perlin2(m.z * 0.25 + m.phase, t * 0.08)
        const noiseY = perlin2(t * 0.12 + i * 0.07, m.phase * 0.5)

        m.x += noiseX * delta * m.speed * 0.8
        m.z += noiseZ * delta * m.speed * 0.8
        m.y += (noiseY * 0.25 - 0.03) * delta * m.speed // gentle downward drift + noise

        // Boundary wrapping — keep motes inside the visible area
        const bound = GRID_HALF
        if (m.x >  bound) m.x = -bound + 0.5
        if (m.x < -bound) m.x =  bound - 0.5
        if (m.z >  bound) m.z = -bound + 0.5
        if (m.z < -bound) m.z =  bound - 0.5
        if (m.y > 3.0) m.y = 0.4
        if (m.y < 0.1) m.y = 2.5

        // Flickering brightness via low-frequency noise, tinted by biome
        const brightness = 0.08 + 0.12 * Math.abs(perlin2(t * 0.18 + i * 0.15, m.phase))
        const { biome } = getGameState()
        if (biome.palette.hasAccent) {
          // The Deep (water) is pressurized — deep palette, not bright.
          // Check slug once so biomeConfigs.ts rename propagates here automatically.
          const useDeep = biome.slug === 'water'
          tmpColor.set(useDeep ? biome.palette.deep : biome.palette.bright).multiplyScalar(brightness * 3.0)
        } else {
          tmpColor.setScalar(brightness)
        }
        dustRef.current.setColorAt(i, tmpColor)

        // Tiny sphere scale with slight shimmer
        const scale = 0.038 + 0.018 * Math.abs(noiseX)
        tmpMatrix.makeScale(scale, scale, scale)
        tmpMatrix.setPosition(m.x, m.y, m.z)
        dustRef.current.setMatrixAt(i, tmpMatrix)
      }
      dustRef.current.instanceMatrix.needsUpdate = true
      if (dustRef.current.instanceColor) dustRef.current.instanceColor.needsUpdate = true
    }

    // --- Update burst particles ---
    if (burstRef.current) {
      for (let i = 0; i < BURST_POOL; i++) {
        const p = bursts.current[i]

        if (p.life <= 0) {
          // Hide dead particles — scale to zero
          tmpMatrix.makeScale(0, 0, 0)
          burstRef.current.setMatrixAt(i, tmpMatrix)
          continue
        }

        p.life -= delta
        p.vy -= 5.5 * delta // gravity
        p.x += p.vx * delta
        p.y += p.vy * delta
        p.z += p.vz * delta

        const t01 = Math.max(0, p.life / p.maxLife) // 1 → 0 over lifetime
        const scale = t01 * 0.058 * (1 + (1 - t01) * 0.4) // grows slightly then shrinks
        tmpMatrix.makeScale(scale, scale, scale)
        tmpMatrix.setPosition(p.x, p.y, p.z)
        burstRef.current.setMatrixAt(i, tmpMatrix)

        // Bright → dim as it fades, tinted by biome accent
        const { biome } = getGameState()
        const burstIntensity = 0.6 + t01 * 0.4
        if (biome.palette.hasAccent) {
          tmpColor.set(biome.palette.bright).multiplyScalar(burstIntensity * 1.8)
        } else {
          tmpColor.setScalar(burstIntensity)
        }
        burstRef.current.setColorAt(i, tmpColor)
      }
      burstRef.current.instanceMatrix.needsUpdate = true
      if (burstRef.current.instanceColor) burstRef.current.instanceColor.needsUpdate = true
    }
  })

  return (
    <>
      {/* Ambient dust motes — tiny floating spheres */}
      <instancedMesh ref={dustRef} args={[undefined, undefined, DUST_COUNT]}>
        <sphereGeometry args={[1, 3, 2]} />
        <meshBasicMaterial color="#ffffff" transparent opacity={0.7} toneMapped={false} />
      </instancedMesh>

      {/* Burst grains — shoot out from block placement */}
      <instancedMesh ref={burstRef} args={[undefined, undefined, BURST_POOL]}>
        <sphereGeometry args={[1, 4, 3]} />
        <meshBasicMaterial color="#ffffff" transparent opacity={0.9} toneMapped={false} />
      </instancedMesh>
    </>
  )
}
