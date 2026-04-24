'use client'

import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { useGameStore } from '../engine/useGameStore'

// Dawn-to-dusk-to-night lighting.
// Sun arc + nightfall darkening: the scene visibly dims in the final 30% of time
// so approaching night is felt before it arrives.
export default function Lighting() {
  const dirLightRef = useRef<THREE.DirectionalLight>(null!)
  const ambientRef = useRef<THREE.AmbientLight>(null!)

  useFrame(() => {
    const { timeOfDay } = useGameStore.getState()

    // Sun angle: east (−X) at dawn → west (+X) at dusk
    const angle = (timeOfDay - 0.5) * Math.PI * 0.67
    const height = Math.cos(timeOfDay * Math.PI) * 5 + 8
    const x = Math.sin(angle) * 10
    const y = Math.max(2, height)

    if (dirLightRef.current) {
      dirLightRef.current.position.set(x, y, 5)

      // Noon factor: 1.0 at noon, 0 at dawn/dusk
      const noonFactor = 1 - Math.abs(timeOfDay - 0.5) * 2

      // Nightfall factor: ramps up sharply in the final 30% of time
      // 0 until timeOfDay=0.7, then 0→1 by timeOfDay=1.0
      const nightFall = Math.max(0, (timeOfDay - 0.7) / 0.3)
      const nightEased = nightFall * nightFall // ease-in

      // Directional: peaks at noon, dims significantly at nightfall
      const baseIntensity = 1.5 + noonFactor * 1.0
      dirLightRef.current.intensity = baseIntensity * (1 - nightEased * 0.75)

      // Color: warm amber at dawn/dusk, cool blue-gray toward night
      const warmth = 1 - noonFactor
      const r = 1 - nightEased * 0.15
      const g = 1 - warmth * 0.1 - nightEased * 0.25
      const b = 1 - warmth * 0.2 + nightEased * 0.1
      dirLightRef.current.color.setRGB(r, Math.max(0, g), Math.min(1, b))
    }

    // Ambient: dims toward night, giving the whole scene a deep-shadow feel
    if (ambientRef.current) {
      const nightFall = Math.max(0, (timeOfDay - 0.7) / 0.3)
      ambientRef.current.intensity = 1.2 - nightFall * nightFall * 0.85
    }
  })

  return (
    <>
      <ambientLight ref={ambientRef} intensity={1.2} color="#ffffff" />
      <directionalLight
        ref={dirLightRef}
        position={[-10, 8, 5]}
        intensity={0.6}
        castShadow={false}
      />
    </>
  )
}
