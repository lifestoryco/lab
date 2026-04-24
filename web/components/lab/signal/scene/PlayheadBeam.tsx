'use client'

import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { useGameStore } from '../engine/useGameStore'
import { gridToWorld, GRID_ROWS, TILE_SIZE, TILE_GAP } from '../utils/isoMath'

const BEAM_WIDTH = 0.04
const BEAM_HEIGHT = (GRID_ROWS + 1) * (TILE_SIZE + TILE_GAP)

export default function PlayheadBeam() {
  const meshRef = useRef<THREE.Mesh>(null!)
  const materialRef = useRef<THREE.MeshBasicMaterial>(null!)

  useFrame(() => {
    if (!meshRef.current) return

    const { playheadStep, isPlaying, saturation, biome } = useGameStore.getState()
    if (!isPlaying) {
      meshRef.current.visible = false
      return
    }
    meshRef.current.visible = true

    // Position at the center of the playhead column
    const [x] = gridToWorld(playheadStep, Math.floor(GRID_ROWS / 2))
    meshRef.current.position.set(x, 0.15, 0)

    // Color: white by default, accent color when saturated
    if (materialRef.current) {
      if (biome.palette.hasAccent && saturation > 0.3) {
        materialRef.current.color.set(biome.palette.bright)
      } else {
        materialRef.current.color.set('#ffffff')
      }
      materialRef.current.opacity = 0.25 + saturation * 0.15
    }
  })

  return (
    <mesh ref={meshRef} rotation={[0, 0, 0]}>
      <boxGeometry args={[BEAM_WIDTH, 0.3, BEAM_HEIGHT]} />
      <meshBasicMaterial
        ref={materialRef}
        color="#ffffff"
        transparent
        opacity={0.25}
        depthWrite={false}
      />
    </mesh>
  )
}
