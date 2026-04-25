'use client'

import { useState, useCallback, useEffect, useMemo, useRef } from 'react'
import dynamic from 'next/dynamic'
import { useGameStore } from './engine/useGameStore'
import { useChainReaction } from './engine/useChainReaction'
import { useCage } from './engine/useCage'
import InstrumentSelector from './ui/InstrumentSelector'
import TitleScreen from './ui/TitleScreen'
import ResultScreen from './ui/ResultScreen'
import WorldTransition from './ui/WorldTransition'
import NarrativeOverlays from './ui/NarrativeOverlays'
import CageHud from './ui/CageHud'
import SpecialButton from './ui/SpecialButton'
import LevelCompleteOverlay from './ui/LevelCompleteOverlay'
import CageFailOverlay from './ui/CageFailOverlay'
import SceneErrorBoundary from './scene/SceneErrorBoundary'
import type { SharedSessionState } from './utils/shareState'
import { track } from './utils/analytics'

// Dynamic import R3F scene — cannot render server-side
const IsometricScene = dynamic(() => import('./scene/IsometricScene'), {
  ssr: false,
  loading: () => (
    <div style={{
      width: '100vw',
      height: '100vh',
      backgroundColor: '#000000',
    }} />
  ),
})

export default function SignalPage() {
  const gamePhase            = useGameStore(s => s.gamePhase)
  const worldIndex           = useGameStore(s => s.worldIndex)
  const biome                = useGameStore(s => s.biome)
  const mode                 = useGameStore(s => s.mode)
  const sessionBlocks        = useGameStore(s => s.sessionBlocks)
  const sessionBiomesCleared = useGameStore(s => s.sessionBiomesCleared)
  const sessionTotalChains   = useGameStore(s => s.sessionTotalChains)
  const reset                = useGameStore(s => s.reset)
  const [titleVisible, setTitleVisible] = useState(true)

  const cageLevelsCleared    = useGameStore(s => s.cageLevelsCleared)
  const cageAttempts         = useGameStore(s => s.cageAttempts)

  // Memoized so ResultScreen's encodeShareState memo doesn't bust every render.
  const sessionSummary: SharedSessionState = useMemo(() => ({
    mode,
    completed: gamePhase === 'complete',
    biomeClearBits: sessionBiomesCleared | (gamePhase === 'complete' ? (1 << worldIndex) : 0),
    blocks: sessionBlocks,
    totalChains: sessionTotalChains,
    finalWorld: worldIndex,
    cageLevelsCleared,
  }), [mode, gamePhase, sessionBiomesCleared, worldIndex, sessionBlocks, sessionTotalChains, cageLevelsCleared])

  // Chain reaction cascade — BFS flood-fill from each placed block
  useChainReaction()
  // Cage Mode engine — no-op when mode !== 'cage'
  useCage()

  // When advancing to a new world, re-show the title screen
  useEffect(() => {
    if (gamePhase === 'title' && worldIndex > 0) {
      setTitleVisible(true)
    }
  }, [gamePhase, worldIndex])

  // Funnel instrumentation
  const sessionStart = useRef<number | null>(null)
  const firstTapFired = useRef(false)
  const firstChainFired = useRef(false)
  const sessionEndFired = useRef(false)
  const lastWorldFired = useRef(-1)
  const cageStartFired = useRef(-1)
  const cageResolveFired = useRef<number | null>(null)

  const cageLastResult = useGameStore(s => s.cageLastResult)
  const cageLevel      = useGameStore(s => s.cageLevel)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    track('signal_entered', {
      ref: params.get('ref') ?? 'direct',
      mode,
    })
  }, [mode])

  useEffect(() => {
    if (gamePhase === 'playing' && !sessionStart.current) {
      sessionStart.current = performance.now()
    }
    // First tap = first block placed
    if (sessionBlocks.length > 0 && !firstTapFired.current && sessionStart.current) {
      firstTapFired.current = true
      track('signal_first_tap', {
        elapsed_ms: Math.round(performance.now() - sessionStart.current),
      })
    }
    if (sessionTotalChains > 0 && !firstChainFired.current) {
      firstChainFired.current = true
      track('signal_first_chain', { world_index: worldIndex })
    }
    if (gamePhase === 'title' && worldIndex !== lastWorldFired.current && worldIndex > 0) {
      lastWorldFired.current = worldIndex
      track('signal_biome_complete', {
        world_index: worldIndex - 1,
        mode,
      })
    }
    // Final biome never goes through 'title' → fire on 'complete' for last world.
    if (gamePhase === 'complete' && worldIndex !== lastWorldFired.current) {
      lastWorldFired.current = worldIndex
      track('signal_biome_complete', {
        world_index: worldIndex,
        mode,
      })
    }
    if ((gamePhase === 'gameover' || gamePhase === 'complete') && !sessionEndFired.current) {
      sessionEndFired.current = true
      track('signal_session_end', {
        completed: gamePhase === 'complete',
        final_world: worldIndex,
        mode,
        total_blocks: sessionBlocks.length,
        total_chains: sessionTotalChains,
        session_ms: sessionStart.current ? Math.round(performance.now() - sessionStart.current) : 0,
      })
    }
    if (gamePhase === 'title' && worldIndex === 0) {
      // Reset for a new session
      sessionStart.current = null
      firstTapFired.current = false
      firstChainFired.current = false
      sessionEndFired.current = false
      lastWorldFired.current = -1
      cageStartFired.current = -1
      cageResolveFired.current = null
    }
  }, [gamePhase, worldIndex, sessionBlocks.length, sessionTotalChains, mode])

  // Cage-mode funnel events — fire once per level start and once per resolve
  useEffect(() => {
    if (mode !== 'cage') return
    if (gamePhase === 'playing' && cageLevel && cageStartFired.current !== worldIndex) {
      cageStartFired.current = worldIndex
      track('signal_cage_started', {
        world_index: worldIndex,
        rule: cageLevel.rule,
        bpm: useGameStore.getState().bpm,
      })
    }
    if (cageLastResult && cageResolveFired.current !== cageLastResult.at) {
      cageResolveFired.current = cageLastResult.at
      track(cageLastResult.solved ? 'signal_cage_solved' : 'signal_cage_escaped', {
        world_index: worldIndex,
        taps: useGameStore.getState().cageTapsThisLevel,
      })
    }
  }, [mode, gamePhase, worldIndex, cageLevel, cageLastResult])

  // Lock body selection + scroll while playing — prevents Android browsers
  // from scroll-hijacking the BPM hold gesture and stops accidental text selection.
  useEffect(() => {
    if (typeof document === 'undefined') return
    if (gamePhase !== 'playing') return
    const body = document.body
    const prev = {
      userSelect: body.style.userSelect,
      webkitUserSelect: body.style.webkitUserSelect,
      overscroll: body.style.overscrollBehavior,
      touchAction: body.style.touchAction,
    }
    body.style.userSelect = 'none'
    body.style.webkitUserSelect = 'none'
    body.style.overscrollBehavior = 'none'
    body.style.touchAction = 'none'
    return () => {
      body.style.userSelect = prev.userSelect
      body.style.webkitUserSelect = prev.webkitUserSelect
      body.style.overscrollBehavior = prev.overscroll
      body.style.touchAction = prev.touchAction
    }
  }, [gamePhase])

  const handleFirstInteraction = useCallback(() => {
    // Fade title out after the opening tap
    setTimeout(() => setTitleVisible(false), 300)
  }, [])

  return (
    <div
      style={{
        width: '100vw',
        height: '100vh',
        backgroundColor: '#000000',
        overflow: 'hidden',
        cursor: 'crosshair',
        position: 'relative',
      }}
    >
      {/* R3F Canvas — full screen. Error boundary catches WebGL init / mid-run failures. */}
      <SceneErrorBoundary>
        <IsometricScene onFirstInteraction={handleFirstInteraction} />
      </SceneErrorBoundary>

      {/* Title overlay */}
      <TitleScreen
        visible={titleVisible && gamePhase === 'title'}
        worldName={biome.name}
        worldSubtitle={biome.subtitle}
      />

      {/* Instrument selector dots */}
      <InstrumentSelector />

      {/* World progress indicator — faint roman numerals, top-right */}
      {gamePhase !== 'title' && (
        <div
          aria-label={`World ${worldIndex + 1} of 5`}
          style={{
            position: 'fixed',
            top: 24,
            right: 28,
            zIndex: 10,
            pointerEvents: 'none',
            fontFamily: '"Cormorant Garamond", Georgia, serif',
            fontSize: 12,
            color: '#ffffff',
            opacity: 0.22,
            letterSpacing: '0.18em',
          }}
        >
          {['I', 'II', 'III', 'IV', 'V'][worldIndex]} / V
        </div>
      )}

      {/* In-play narrative text — ambient, whispers, hints */}
      <NarrativeOverlays />

      {/* Cage Mode HUD — timer bar, rule hint, fail whisper, level tag */}
      <CageHud />

      {/* Per-world special-item button (worlds 2-5, one charge per cage level) */}
      <SpecialButton />

      {/* Full-screen tap-to-continue after cage-solve */}
      <LevelCompleteOverlay />

      {/* Cage failure: instant retry overlay (Super Meat Boy pattern). */}
      {gamePhase === 'gameover' && mode === 'cage' && <CageFailOverlay />}

      {/* Result screen — Zen fail, or full-arc complete in either mode. */}
      {(gamePhase === 'complete' || (gamePhase === 'gameover' && mode === 'zen')) && (
        <ResultScreen
          state={sessionSummary}
          mode="live"
          onPlayAgain={reset}
        />
      )}

      {/* World transition overlay — always mounted, visible only during 'transition' phase */}
      <WorldTransition />
    </div>
  )
}
