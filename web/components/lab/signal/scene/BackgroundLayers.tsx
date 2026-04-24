'use client'

// BackgroundLayers — Firewatch-inspired silhouette depth layers.
// Each world renders a distinct background silhouette group positioned behind
// the grid (at x=-12 to -6, z=-12 to -6 in isometric space, appearing at the
// far "top corner" of the orthographic view). Opacity fades between worlds.

import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { getGameState } from '../engine/useGameStore'

const FADE_SPEED = 0.025
const MAX_OPACITY = 0.72

// --- Silhouette components per world ---

function Signal() {
  return (
    <>
      <mesh position={[0, 0.22, 0]}>
        <boxGeometry args={[22, 0.1, 0.4]} />
        <meshBasicMaterial color="#181818" transparent opacity={0} toneMapped={false} />
      </mesh>
      <mesh position={[0, 3.8, 0]}>
        <boxGeometry args={[0.13, 7.6, 0.13]} />
        <meshBasicMaterial color="#181818" transparent opacity={0} toneMapped={false} />
      </mesh>
      <mesh position={[0, 7.6, 0.5]} rotation={[0.4, 0, 0]}>
        <boxGeometry args={[2.6, 0.09, 2.2]} />
        <meshBasicMaterial color="#1c1c1c" transparent opacity={0} toneMapped={false} />
      </mesh>
      <mesh position={[4.5, 2.2, 1.2]}>
        <boxGeometry args={[0.1, 4.4, 0.1]} />
        <meshBasicMaterial color="#141414" transparent opacity={0} toneMapped={false} />
      </mesh>
      <mesh position={[4.5, 4.5, 1.6]} rotation={[0.5, 0, 0]}>
        <boxGeometry args={[1.6, 0.08, 1.3]} />
        <meshBasicMaterial color="#141414" transparent opacity={0} toneMapped={false} />
      </mesh>
      <mesh position={[-4, 1.4, 1.8]}>
        <boxGeometry args={[0.08, 2.8, 0.08]} />
        <meshBasicMaterial color="#111111" transparent opacity={0} toneMapped={false} />
      </mesh>
      <mesh position={[-4, 2.9, 2.1]} rotation={[0.5, 0, 0]}>
        <boxGeometry args={[1.0, 0.06, 0.8]} />
        <meshBasicMaterial color="#111111" transparent opacity={0} toneMapped={false} />
      </mesh>
    </>
  )
}

function Temple() {
  const colPositions = [-6.5, -3.5, 0, 3.5, 6.5]
  const colHeights = [4.8, 5.5, 6.2, 5.1, 4.5]
  return (
    <>
      <mesh position={[0, 0.18, 0]}>
        <boxGeometry args={[20, 0.36, 0.8]} />
        <meshBasicMaterial color="#1a1500" transparent opacity={0} toneMapped={false} />
      </mesh>
      {colPositions.map((x, i) => (
        <group key={i}>
          <mesh position={[x, colHeights[i] / 2, 0]}>
            <boxGeometry args={[0.42, colHeights[i], 0.42]} />
            <meshBasicMaterial color="#181300" transparent opacity={0} toneMapped={false} />
          </mesh>
          <mesh position={[x, colHeights[i] + 0.22, 0]}>
            <boxGeometry args={[0.7, 0.28, 0.7]} />
            <meshBasicMaterial color="#1a1500" transparent opacity={0} toneMapped={false} />
          </mesh>
        </group>
      ))}
      <mesh position={[0, 6.55, 0]}>
        <boxGeometry args={[16, 0.22, 0.55]} />
        <meshBasicMaterial color="#1a1500" transparent opacity={0} toneMapped={false} />
      </mesh>
      {[0, 1, 2, 3, 4].map((step) => (
        <mesh key={step} position={[-10, step * 1.0 + 0.5, 3.5]}>
          <boxGeometry args={[5 - step * 0.9, 0.95, 0.5]} />
          <meshBasicMaterial color="#121000" transparent opacity={0} toneMapped={false} />
        </mesh>
      ))}
      <mesh position={[-10, 5.2, 3.5]}>
        <boxGeometry args={[0.35, 0.6, 0.35]} />
        <meshBasicMaterial color="#121000" transparent opacity={0} toneMapped={false} />
      </mesh>
    </>
  )
}

function Deep() {
  return (
    <>
      <mesh position={[0, 0.15, 0]}>
        <boxGeometry args={[22, 0.3, 0.6]} />
        <meshBasicMaterial color="#001428" transparent opacity={0} toneMapped={false} />
      </mesh>
      <mesh position={[-3.5, 3.8, 0]}>
        <boxGeometry args={[0.7, 7.6, 0.55]} />
        <meshBasicMaterial color="#001220" transparent opacity={0} toneMapped={false} />
      </mesh>
      <mesh position={[3.5, 3.8, 0]}>
        <boxGeometry args={[0.7, 7.6, 0.55]} />
        <meshBasicMaterial color="#001220" transparent opacity={0} toneMapped={false} />
      </mesh>
      <mesh position={[0, 7.8, 0]}>
        <boxGeometry args={[7.5, 0.9, 0.6]} />
        <meshBasicMaterial color="#001824" transparent opacity={0} toneMapped={false} />
      </mesh>
      <mesh position={[-2.8, 7.2, 0]}>
        <boxGeometry args={[0.9, 0.55, 0.55]} />
        <meshBasicMaterial color="#001824" transparent opacity={0} toneMapped={false} />
      </mesh>
      <mesh position={[2.8, 7.2, 0]}>
        <boxGeometry args={[0.9, 0.55, 0.55]} />
        <meshBasicMaterial color="#001824" transparent opacity={0} toneMapped={false} />
      </mesh>
      <mesh position={[-7, 2, 2.5]}>
        <boxGeometry args={[0.4, 4, 0.4]} />
        <meshBasicMaterial color="#000e18" transparent opacity={0} toneMapped={false} />
      </mesh>
      <mesh position={[-4, 2, 2.5]}>
        <boxGeometry args={[0.4, 4, 0.4]} />
        <meshBasicMaterial color="#000e18" transparent opacity={0} toneMapped={false} />
      </mesh>
      <mesh position={[-5.5, 4.1, 2.5]}>
        <boxGeometry args={[3.6, 0.55, 0.4]} />
        <meshBasicMaterial color="#000e18" transparent opacity={0} toneMapped={false} />
      </mesh>
      {[-6, -3, 0, 3, 6, 9].map((x, i) => (
        <mesh key={i} position={[x - 2, 8 - (i % 3) * 0.8, -0.5]}>
          <boxGeometry args={[0.18, 1.2 + (i % 3) * 0.6, 0.18]} />
          <meshBasicMaterial color="#001020" transparent opacity={0} toneMapped={false} />
        </mesh>
      ))}
    </>
  )
}

function Garden() {
  const trees = [
    { x: -8, z: 0, h: 5.5, cw: 3.2, ch: 3.8 },
    { x: -4, z: 0.5, h: 7, cw: 2.6, ch: 4.5 },
    { x: 0, z: 0, h: 6, cw: 3.8, ch: 3.2 },
    { x: 4, z: 0.3, h: 8, cw: 2.4, ch: 5 },
    { x: 7, z: 0, h: 5, cw: 2.8, ch: 3 },
    { x: -6, z: 2, h: 4, cw: 2, ch: 2.8 },
    { x: 2, z: 2, h: 5, cw: 1.8, ch: 3 },
    { x: 9, z: 2, h: 3.5, cw: 1.6, ch: 2.2 },
  ]
  return (
    <>
      <mesh position={[0, 0.15, 0]}>
        <boxGeometry args={[24, 0.3, 0.5]} />
        <meshBasicMaterial color="#001a00" transparent opacity={0} toneMapped={false} />
      </mesh>
      {trees.map((t, i) => (
        <group key={i} position={[t.x, 0, t.z]}>
          <mesh position={[0, t.h * 0.4, 0]}>
            <boxGeometry args={[0.22, t.h * 0.8, 0.22]} />
            <meshBasicMaterial color="#001200" transparent opacity={0} toneMapped={false} />
          </mesh>
          <mesh position={[0, t.h * 0.82, 0]}>
            <boxGeometry args={[t.cw, t.ch * 0.65, t.cw * 0.7]} />
            <meshBasicMaterial color="#001600" transparent opacity={0} toneMapped={false} />
          </mesh>
          <mesh position={[0, t.h * 0.72, 0]}>
            <boxGeometry args={[t.cw * 0.8, t.ch * 0.8, t.cw * 0.55]} />
            <meshBasicMaterial color="#001400" transparent opacity={0} toneMapped={false} />
          </mesh>
        </group>
      ))}
    </>
  )
}

function Truth() {
  return (
    <>
      <mesh position={[0, 0.12, 0]}>
        <boxGeometry args={[20, 0.22, 0.4]} />
        <meshBasicMaterial color="#1a0002" transparent opacity={0} toneMapped={false} />
      </mesh>
      <mesh position={[-3.2, 4, 0]}>
        <boxGeometry args={[0.55, 8, 0.55]} />
        <meshBasicMaterial color="#180002" transparent opacity={0} toneMapped={false} />
      </mesh>
      <mesh position={[3.2, 4, 0]}>
        <boxGeometry args={[0.55, 8, 0.55]} />
        <meshBasicMaterial color="#180002" transparent opacity={0} toneMapped={false} />
      </mesh>
      <mesh position={[0, 7.2, 0]}>
        <boxGeometry args={[8.8, 0.65, 0.6]} />
        <meshBasicMaterial color="#1a0003" transparent opacity={0} toneMapped={false} />
      </mesh>
      <mesh position={[0, 8.1, 0]}>
        <boxGeometry args={[9.6, 0.38, 0.55]} />
        <meshBasicMaterial color="#1a0003" transparent opacity={0} toneMapped={false} />
      </mesh>
      <mesh position={[-4.6, 8.2, 0]}>
        <boxGeometry args={[0.7, 0.22, 0.45]} />
        <meshBasicMaterial color="#1a0003" transparent opacity={0} toneMapped={false} />
      </mesh>
      <mesh position={[4.6, 8.2, 0]}>
        <boxGeometry args={[0.7, 0.22, 0.45]} />
        <meshBasicMaterial color="#1a0003" transparent opacity={0} toneMapped={false} />
      </mesh>
      <mesh position={[-3.2, 6.2, 0]}>
        <boxGeometry args={[0.65, 0.3, 0.7]} />
        <meshBasicMaterial color="#160002" transparent opacity={0} toneMapped={false} />
      </mesh>
      <mesh position={[3.2, 6.2, 0]}>
        <boxGeometry args={[0.65, 0.3, 0.7]} />
        <meshBasicMaterial color="#160002" transparent opacity={0} toneMapped={false} />
      </mesh>
    </>
  )
}

export default function BackgroundLayers() {
  const groupRefs = useRef<(THREE.Group | null)[]>(Array(5).fill(null))
  const opacities = useRef<number[]>([MAX_OPACITY, 0, 0, 0, 0])

  useFrame(() => {
    const { worldIndex } = getGameState()

    for (let i = 0; i < 5; i++) {
      const target = i === worldIndex ? MAX_OPACITY : 0
      const prev = opacities.current[i]
      const next = THREE.MathUtils.lerp(prev, target, FADE_SPEED)
      opacities.current[i] = next

      const group = groupRefs.current[i]
      if (!group) continue
      group.traverse((obj) => {
        if (obj instanceof THREE.Mesh) {
          const material = obj.material as THREE.MeshBasicMaterial
          material.opacity = next
        }
      })
    }
  })

  const worlds = [Signal, Temple, Deep, Garden, Truth]

  return (
    <>
      {worlds.map((WorldComp, i) => (
        <group key={i} ref={(el) => { groupRefs.current[i] = el }} position={[-12, 0, -12]}>
          <WorldComp />
        </group>
      ))}
    </>
  )
}
