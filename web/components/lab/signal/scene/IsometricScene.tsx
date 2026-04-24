'use client'

import { useCallback, useRef, useEffect } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import GridPlane from './GridPlane'
import PlacedBlocks from './PlacedBlocks'
import PlayheadBeam from './PlayheadBeam'
import Lighting from './Lighting'
import Particles from './Particles'
import GestureControls from './GestureControls'
import Portal from './Portal'
import Monster from './Monster'
import BackgroundLayers from './BackgroundLayers'
import MonsterPawn from './MonsterPawn'
import PathHintVisualizer from './PathHintVisualizer'
import CageCelebration from './CageCelebration'
import PostFXPipeline from '../postprocessing/PostFXPipeline'
import { useGameStore, getGameState } from '../engine/useGameStore'
import { initAudio, startTransport, stopTransport, triggerPlacementNote, isInitialized } from '../audio/audioEngine'

// Timer component — runs in the R3F render loop for smooth timing
function GameTimer() {
  const lastTime = useRef(performance.now())

  useFrame(() => {
    const now = performance.now()
    const delta = now - lastTime.current
    lastTime.current = now
    getGameState().tick(delta)
  })

  return null
}

// Camera breath — reacts to lastChain by briefly zooming the orthographic camera.
// Chain length → zoom factor (clamped at 8%). ~180 ms ease-in, 600 ms ease-out.
function CameraBreath() {
  const { camera } = useThree()
  const lastSeen = useRef<number>(0)
  const breathStart = useRef<number>(0)
  const breathStrength = useRef<number>(0)
  const baseZoom = useRef<number>(0)
  const reducedMotion = useRef<boolean>(false)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    reducedMotion.current = mq.matches
    const onChange = () => { reducedMotion.current = mq.matches }
    mq.addEventListener?.('change', onChange)
    return () => mq.removeEventListener?.('change', onChange)
  }, [])

  useFrame(() => {
    const { lastChain } = getGameState()
    if (lastChain && lastChain.at !== lastSeen.current && lastChain.length >= 3) {
      lastSeen.current = lastChain.at
      breathStart.current = performance.now()
      breathStrength.current = Math.min(0.08, lastChain.length * 0.012)
      if (reducedMotion.current) breathStrength.current = 0
      const ortho = camera as THREE.OrthographicCamera
      baseZoom.current = ortho.zoom / (1 + 0) // snapshot current "resting" zoom
    }

    // Envelope: 180ms in, 600ms out
    if (breathStart.current === 0) return
    const t = performance.now() - breathStart.current
    const ortho = camera as THREE.OrthographicCamera
    const IN = 180, OUT = 600
    let factor = 0
    if (t < IN) {
      const u = t / IN
      factor = (1 - Math.pow(1 - u, 3)) * breathStrength.current // ease-out-cubic
    } else if (t < IN + OUT) {
      const u = (t - IN) / OUT
      factor = (1 - u * u * u) * breathStrength.current // ease-in-cubic settle
    } else {
      breathStart.current = 0
      factor = 0
    }
    ortho.zoom = baseZoom.current * (1 + factor)
    ortho.updateProjectionMatrix()
  })

  return null
}

// Clear pulse state after a short delay
function PulseClearer() {
  const lastStep = useRef(-1)
  const pulseTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useFrame(() => {
    const { playheadStep } = getGameState()
    if (playheadStep !== lastStep.current) {
      lastStep.current = playheadStep
      if (pulseTimer.current) globalThis.clearTimeout(pulseTimer.current)
      pulseTimer.current = globalThis.setTimeout(() => {
        getGameState().setPulsingBlocks([])
      }, 150)
    }
  })

  return null
}

// Set up orthographic camera with true isometric angle looking at origin
function IsometricCamera() {
  const { camera, size } = useThree()

  useEffect(() => {
    // Position for isometric view: equal X, Y, Z creates 45-degree rotation
    camera.position.set(20, 20, 20)
    camera.lookAt(0, 0, 0)
    // Scale zoom for viewport: 28 is tuned for ~800px wide; scale proportionally
    const ortho = camera as THREE.OrthographicCamera
    const baseZoom = Math.max(16, Math.min(40, (size.width / 800) * 28))
    ortho.zoom = baseZoom
    camera.updateProjectionMatrix()
  }, [camera, size])

  return null
}

interface IsometricSceneProps {
  onFirstInteraction?: () => void
}

export default function IsometricScene({ onFirstInteraction }: IsometricSceneProps) {
  const audioStarted = useRef(false)
  const twoFingerActive = useRef(false)

  // Stop audio transport on unmount
  useEffect(() => {
    return () => {
      stopTransport()
    }
  }, [])

  const handleTwoFingerActive = useCallback((active: boolean) => {
    twoFingerActive.current = active
  }, [])

  // Shared audio boot — idempotent, safe to call from any interaction path
  const ensureAudio = useCallback(async () => {
    if (audioStarted.current) return
    await initAudio()
    audioStarted.current = true
    getGameState().setAudioReady(true)
  }, [])

  const handleCellClick = useCallback(async (col: number, row: number) => {
    // Suppress single-finger block placement while two-finger gesture is active
    if (twoFingerActive.current) return
    const state = getGameState()

    await ensureAudio()

    // Start game from title screen (first world or any subsequent world)
    if (state.gamePhase === 'title') {
      if (state.mode === 'cage') {
        // First tap from title on Cage always starts at level 0 (1-1).
        // Subsequent biome entries come via nextCageLevel which already sets
        // the level, so we read cageLevelIndex (falls back to 0).
        state.startCageLevel(state.cageLevel ? state.cageLevelIndex : 0)
      }
      state.startPlaying()
      onFirstInteraction?.()
      // Use the level's BPM in Cage so progression ramps correctly.
      const startBpm = state.mode === 'cage' && state.cageLevel
        ? state.cageLevel.bpm
        : state.biome.bpm
      startTransport(startBpm)
      return // don't place a block on the tap that starts the world
    }

    // Place block + immediate audio feedback
    state.placeBlock(col, row)
    triggerPlacementNote(row, state.selectedInstrument)
  }, [ensureAudio, onFirstInteraction])

  const handleCellLongPress = useCallback((col: number, row: number) => {
    if (twoFingerActive.current) return
    getGameState().removeBlock(col, row)
  }, [])

  // Handle click on the canvas itself (before any grid tile is hit)
  // Also handles world 2+ title-screen taps that land outside the grid
  const handleCanvasClick = useCallback(async () => {
    const state = getGameState()
    if (state.gamePhase !== 'title') return

    await ensureAudio()
    if (state.mode === 'cage') {
      state.startCageLevel(state.worldIndex)
    }
    state.startPlaying()
    onFirstInteraction?.()
    startTransport(state.biome.bpm)
  }, [ensureAudio, onFirstInteraction])

  return (
    <Canvas
      style={{ background: '#000000' }}
      gl={{ antialias: true, alpha: false }}
      dpr={[1, 2]}
      orthographic
      camera={{ zoom: 28, near: 0.1, far: 1000, position: [20, 20, 20] }}
      onPointerDown={handleCanvasClick}
      role="application"
      aria-label="Signal — isometric music grid. Tap to place blocks and compose. Long-press to remove."
    >
      <IsometricCamera />
      <GestureControls onTwoFingerActive={handleTwoFingerActive} />
      <Lighting />
      <BackgroundLayers />
      <GridPlane
        onCellClick={handleCellClick}
        onCellLongPress={handleCellLongPress}
      />
      <PlacedBlocks />
      <PlayheadBeam />
      <PathHintVisualizer />
      <MonsterPawn />
      <CageCelebration />
      <Portal />
      <Monster />
      <Particles />
      <PostFXPipeline />
      <GameTimer />
      <PulseClearer />
      <CameraBreath />
    </Canvas>
  )
}
