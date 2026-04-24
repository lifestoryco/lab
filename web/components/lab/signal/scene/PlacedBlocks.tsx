'use client'

import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { useGameStore } from '../engine/useGameStore'
import { gridToWorld, TILE_SIZE } from '../utils/isoMath'
import { INSTRUMENT_COLORS } from '../audio/audioEngine'
import { easeOutBack } from '../utils/easing'

const MAX_BLOCKS = 200
const PLACE_ANIM_DURATION = 300 // ms
const PULSE_DURATION = 200 // ms

export default function PlacedBlocks() {
  const meshRef = useRef<THREE.InstancedMesh>(null!)
  const dummy = useMemo(() => new THREE.Object3D(), [])
  const tempColor = useMemo(() => new THREE.Color(), [])
  const whiteColor = useMemo(() => new THREE.Color('#ffffff'), [])
  // Memoize accent color to avoid new THREE.Color() allocation per block per frame
  const biome = useGameStore(s => s.biome)
  const accentColor = useMemo(
    () => new THREE.Color(biome.palette.bright),
    [biome.palette.bright],
  )

  useFrame(() => {
    const mesh = meshRef.current
    if (!mesh) return

    const { blocks, blockAnimations, pulsingBlocks, saturation } = useGameStore.getState()
    const now = performance.now()
    let visibleCount = 0

    for (const [key, block] of blocks) {
      if (visibleCount >= MAX_BLOCKS) break

      const [x, , z] = gridToWorld(block.col, block.row)
      const anim = blockAnimations.get(key)
      const isPulsing = pulsingBlocks.has(key)

      // Placement animation: squash & stretch with easeOutBack
      let scaleY = 1
      let posY = TILE_SIZE * 0.5
      if (anim && anim.type === 'place') {
        const elapsed = now - anim.startTime
        const t = Math.min(1, elapsed / PLACE_ANIM_DURATION)
        const eased = easeOutBack(t)
        scaleY = eased
        posY = TILE_SIZE * 0.5 * eased
      }

      // Pulse animation: emissive flash (scale bump)
      let pulseScale = 1
      if (isPulsing) {
        pulseScale = 1.08
      }

      dummy.position.set(x, posY, z)
      dummy.scale.set(
        TILE_SIZE * 0.85 * pulseScale,
        TILE_SIZE * 0.85 * scaleY,
        TILE_SIZE * 0.85 * pulseScale,
      )
      dummy.updateMatrix()
      mesh.setMatrixAt(visibleCount, dummy.matrix)

      // Color: instrument base color, mixed with accent based on saturation
      const instrumentColor = INSTRUMENT_COLORS[block.instrumentIndex] || '#ffffff'
      tempColor.set(instrumentColor)

      // Mix in world accent color based on saturation
      if (biome.palette.hasAccent && saturation > 0) {
        tempColor.lerp(accentColor, saturation * 0.6)
      }

      // Pulse: flash bright white
      if (isPulsing) {
        tempColor.lerp(whiteColor, 0.5)
      }

      mesh.setColorAt(visibleCount, tempColor)
      visibleCount++
    }

    // Hide unused instances
    for (let i = visibleCount; i < MAX_BLOCKS; i++) {
      dummy.position.set(0, -100, 0) // off-screen
      dummy.scale.set(0, 0, 0)
      dummy.updateMatrix()
      mesh.setMatrixAt(i, dummy.matrix)
    }

    mesh.instanceMatrix.needsUpdate = true
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true
    mesh.count = visibleCount
  })

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, MAX_BLOCKS]}>
      <boxGeometry args={[1, 1, 1]} />
      <meshBasicMaterial color="#ffffff" toneMapped={false} />
    </instancedMesh>
  )
}
