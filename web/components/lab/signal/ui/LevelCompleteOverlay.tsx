'use client'

// Full-screen post-cage-solve overlay. Replaces the tiny R3F portal as the
// level-advance affordance. Appears ~700 ms after solve (lets the cage
// celebration breathe), dims the scene, shows the level name, gives the
// player a big tap target. Auto-advances after 10 s if they idle.

import { useEffect, useState, useRef } from 'react'
import { useGameStore } from '../engine/useGameStore'

const SERIF = '"Cormorant Garamond", Georgia, serif'
const AUTO_ADVANCE_MS = 10_000
const REVEAL_DELAY_MS = 700 // breathe for the cage celebration

export default function LevelCompleteOverlay() {
  const mode            = useGameStore(s => s.mode)
  const gamePhase       = useGameStore(s => s.gamePhase)
  const cageLevel       = useGameStore(s => s.cageLevel)
  const cageLevelIndex  = useGameStore(s => s.cageLevelIndex)
  const cageResult      = useGameStore(s => s.cageLastResult)
  const blocksUsed      = useGameStore(s => s.cageBlocksUsedThisLevel)
  const biome           = useGameStore(s => s.biome)
  const nextCageLevel   = useGameStore(s => s.nextCageLevel)

  const [visible, setVisible] = useState(false)
  const [revealed, setRevealed] = useState(false)
  const autoTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const revealTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const shouldShow =
    mode === 'cage' &&
    gamePhase === 'playing' &&
    !!cageResult?.solved

  useEffect(() => {
    if (shouldShow) {
      setVisible(true)
      // Delay reveal so the cage celebration plays uninterrupted.
      revealTimer.current = setTimeout(() => setRevealed(true), REVEAL_DELAY_MS)
      // Auto-advance after 10s idle.
      autoTimer.current = setTimeout(() => {
        handleAdvance()
      }, REVEAL_DELAY_MS + AUTO_ADVANCE_MS)
    } else {
      setVisible(false)
      setRevealed(false)
      if (autoTimer.current) clearTimeout(autoTimer.current)
      if (revealTimer.current) clearTimeout(revealTimer.current)
    }
    return () => {
      if (autoTimer.current) clearTimeout(autoTimer.current)
      if (revealTimer.current) clearTimeout(revealTimer.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shouldShow])

  function handleAdvance() {
    if (autoTimer.current) clearTimeout(autoTimer.current)
    // nextCageLevel branches: same-biome → fast advance; biome-change →
    // 'transition' ceremony; final-level → 'complete'. Transport stops only
    // when a ceremony fires (startCageLevel re-uses the same transport).
    nextCageLevel()
  }

  if (!visible) return null

  const accent = biome.palette.hasAccent ? biome.palette.bright : '#cccccc'
  const levelId = cageLevel?.id ?? `${cageLevelIndex + 1}`
  const par = cageLevel?.parBlocks ?? 0
  const starred = !!cageResult?.starred
  const parCopy = starred
    ? `★ par ${par} · solved in ${blocksUsed}`
    : `par ${par} · solved in ${blocksUsed}`

  return (
    <button
      onClick={handleAdvance}
      onPointerDown={(e) => e.stopPropagation()}
      aria-label="Continue to the next level"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 40,
        background: 'radial-gradient(ellipse at center, rgba(0,0,0,0.35) 0%, rgba(0,0,0,0.78) 70%)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        border: 'none',
        cursor: 'pointer',
        opacity: revealed ? 1 : 0,
        transition: 'opacity 0.8s ease',
        padding: '40px 24px',
        WebkitTapHighlightColor: 'transparent',
      }}
    >
      <div
        aria-hidden="true"
        style={{
          fontFamily: SERIF,
          fontSize: 'clamp(0.7rem, 1.6vw, 0.9rem)',
          color: '#888',
          letterSpacing: '0.2em',
          textTransform: 'uppercase',
          marginBottom: 20,
        }}
      >
        Level {levelId} · {cageLevel?.name ?? biome.name}
      </div>
      <div
        aria-hidden="true"
        style={{
          fontFamily: SERIF,
          fontSize: 'clamp(2rem, 6vw, 4rem)',
          fontWeight: 300,
          letterSpacing: '0.2em',
          color: '#ffffff',
          marginBottom: 14,
          textShadow: `0 0 30px ${accent}`,
        }}
      >
        Caged.
      </div>
      <div
        aria-hidden="true"
        style={{
          fontFamily: SERIF,
          fontStyle: starred ? 'normal' : 'italic',
          fontSize: 'clamp(0.95rem, 2vw, 1.2rem)',
          color: starred ? accent : '#aaaaaa',
          letterSpacing: '0.18em',
          marginBottom: 24,
          textShadow: starred ? `0 0 14px ${accent}88` : 'none',
        }}
      >
        {parCopy}
      </div>
      <div
        aria-hidden="true"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          opacity: 0.85,
        }}
      >
        <span
          style={{
            display: 'inline-block',
            width: 10,
            height: 10,
            borderRadius: '50%',
            backgroundColor: accent,
            animation: 'signalPulse 1.4s ease-in-out infinite',
          }}
        />
        <span
          style={{
            fontFamily: SERIF,
            fontStyle: 'italic',
            fontSize: 'clamp(0.85rem, 1.8vw, 1.1rem)',
            color: '#cccccc',
            letterSpacing: '0.14em',
          }}
        >
          Tap anywhere to continue
        </span>
      </div>
      <style>{`
        @keyframes signalPulse {
          0%, 100% { transform: scale(0.6); opacity: 0.4; }
          50%      { transform: scale(1.2); opacity: 1; }
        }
      `}</style>
    </button>
  )
}
