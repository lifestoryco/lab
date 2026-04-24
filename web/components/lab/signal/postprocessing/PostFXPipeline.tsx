'use client'

import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import { EffectComposer, Bloom, Vignette, ChromaticAberration, Noise } from '@react-three/postprocessing'
import { BlendFunction } from 'postprocessing'
import type { BloomEffect, ChromaticAberrationEffect } from 'postprocessing'
import * as THREE from 'three'
import { getGameState } from '../engine/useGameStore'

const BLOOM_BASE_INTENSITY = 0.5

// Imperatively updates effect parameters each frame
function EffectUpdater({
  caRef,
  bloomRef,
}: {
  caRef: React.MutableRefObject<ChromaticAberrationEffect | null>
  bloomRef: React.MutableRefObject<BloomEffect | null>
}) {
  const lastChainAt = useRef(0)
  const bloomBumpStart = useRef(0)
  const bloomBumpStrength = useRef(0)

  useFrame(() => {
    if (!caRef.current) return
    const { timeOfDay, gamePhase, lastChain } = getGameState()

    // Chromatic aberration peaks at dawn (0-0.1) and deep dusk (0.85-1.0)
    const dawnFactor = Math.max(0, (0.12 - timeOfDay) / 0.12)
    const duskFactor = gamePhase === 'gameover' ? 1 : Math.max(0, (timeOfDay - 0.82) / 0.18)
    const edgeFactor = Math.max(dawnFactor, duskFactor)
    const strength = 0.0002 + edgeFactor * 0.0015
    caRef.current.offset.set(strength, strength * 0.65)

    // Bloom bump: fires on chains ≥3, 220ms in / 900ms out, ease-out expo.
    if (lastChain && lastChain.at !== lastChainAt.current && lastChain.length >= 3) {
      lastChainAt.current = lastChain.at
      bloomBumpStart.current = performance.now()
      // Respect reduced-motion: dampen the flash to 20% of spec.
      const reduced = typeof window !== 'undefined'
        && window.matchMedia('(prefers-reduced-motion: reduce)').matches
      const base = Math.min(0.6, lastChain.length * 0.1)
      bloomBumpStrength.current = reduced ? base * 0.2 : base
    }

    if (bloomRef.current) {
      let bumpFactor = 0
      if (bloomBumpStart.current > 0) {
        const t = performance.now() - bloomBumpStart.current
        const IN = 220, OUT = 900
        if (t < IN) {
          const u = t / IN
          bumpFactor = (1 - Math.pow(1 - u, 3)) * bloomBumpStrength.current
        } else if (t < IN + OUT) {
          const u = (t - IN) / OUT
          bumpFactor = Math.pow(1 - u, 2) * bloomBumpStrength.current
        } else {
          bloomBumpStart.current = 0
        }
      }
      bloomRef.current.intensity = BLOOM_BASE_INTENSITY * (1 + bumpFactor)
    }
  })
  return null
}

export default function PostFXPipeline() {
  // @react-three/postprocessing types incorrectly use typeof Effect (constructor)
  // instead of Effect (instance) for ref generics. Cast to silence the mismatch.
  const caRef = useRef<ChromaticAberrationEffect | null>(null)
  const bloomRef = useRef<BloomEffect | null>(null)
  const initOffset = useMemo(() => new THREE.Vector2(0.0002, 0.00015), [])

  return (
    <>
      <EffectComposer>
        {/* Bloom: only the brightest things glow (placed blocks + playhead beam) */}
        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
        <Bloom
          ref={bloomRef as any}
          luminanceThreshold={0.6}
          luminanceSmoothing={0.7}
          intensity={BLOOM_BASE_INTENSITY}
          mipmapBlur
        />
        {/* Chromatic aberration: barely perceptible at midday, builds toward dawn/dusk */}
        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
        {/* Note: @react-three/postprocessing types the ref as constructor (typeof Effect)
            instead of instance (Effect). Cast to any — correct at runtime. */}
        <ChromaticAberration
          ref={caRef as any}
          offset={initOffset}
          radialModulation={false}
          modulationOffset={0}
        />
        {/* Vignette: frames the grid, darkens edges like a lens */}
        <Vignette
          eskil={false}
          offset={0.38}
          darkness={0.52}
        />
        {/* Film grain: makes it feel analog, not digital */}
        <Noise
          opacity={0.038}
          blendFunction={BlendFunction.SOFT_LIGHT}
        />
      </EffectComposer>
      <EffectUpdater caRef={caRef} bloomRef={bloomRef} />
    </>
  )
}
