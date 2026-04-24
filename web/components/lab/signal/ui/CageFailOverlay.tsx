'use client'

// On-fail overlay for Cage Mode. Replaces the full ResultScreen gameover
// with a 1-tap retry (Super Meat Boy). ResultScreen remains for full-arc
// complete and for Zen Mode session ends.

import { useEffect, useState } from 'react'
import { useGameStore } from '../engine/useGameStore'
import { stopTransport, startTransport } from '../audio/audioEngine'

const SERIF = '"Cormorant Garamond", Georgia, serif'
const REVEAL_DELAY_MS = 1100 // let the monster-sink settle first

export default function CageFailOverlay() {
  const mode            = useGameStore(s => s.mode)
  const gamePhase       = useGameStore(s => s.gamePhase)
  const cageLevel       = useGameStore(s => s.cageLevel)
  const retryCageLevel  = useGameStore(s => s.retryCageLevel)
  const reset           = useGameStore(s => s.reset)

  const [revealed, setRevealed] = useState(false)

  const shouldShow =
    mode === 'cage' &&
    gamePhase === 'gameover' &&
    !!cageLevel

  useEffect(() => {
    if (!shouldShow) { setRevealed(false); return }
    const t = setTimeout(() => setRevealed(true), REVEAL_DELAY_MS)
    return () => clearTimeout(t)
  }, [shouldShow])

  function handleRetry(e: React.PointerEvent | React.MouseEvent) {
    e.stopPropagation()
    // Stop and restart the transport so the monster motif rewinds cleanly.
    stopTransport()
    retryCageLevel()
    if (cageLevel) startTransport(cageLevel.bpm)
  }

  function handleGiveUp(e: React.PointerEvent | React.MouseEvent) {
    e.stopPropagation()
    stopTransport()
    reset()
  }

  if (!shouldShow) return null

  return (
    <div
      role="dialog"
      aria-label="Level failed — choose retry or give up"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 35,
        background: 'radial-gradient(ellipse at center, rgba(0,0,0,0.4) 0%, rgba(0,0,0,0.85) 70%)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        opacity: revealed ? 1 : 0,
        transition: 'opacity 0.8s ease',
        padding: '40px 24px',
        pointerEvents: revealed ? 'auto' : 'none',
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
          marginBottom: 12,
        }}
      >
        Level {cageLevel?.id}
      </div>
      <div
        aria-hidden="true"
        style={{
          fontFamily: SERIF,
          fontStyle: 'italic',
          fontSize: 'clamp(1.2rem, 3vw, 1.8rem)',
          color: '#cc4444',
          letterSpacing: '0.15em',
          marginBottom: 36,
        }}
      >
        It reached the edge.
      </div>
      <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', justifyContent: 'center' }}>
        <button
          onClick={handleRetry}
          onPointerDown={(e) => e.stopPropagation()}
          style={primaryBtn}
        >
          Retry
        </button>
        <button
          onClick={handleGiveUp}
          onPointerDown={(e) => e.stopPropagation()}
          style={secondaryBtn}
        >
          Back to menu
        </button>
      </div>
    </div>
  )
}

const primaryBtn: React.CSSProperties = {
  fontFamily: SERIF,
  fontSize: 'clamp(1rem, 2vw, 1.2rem)',
  color: '#ffffff',
  background: 'rgba(255,255,255,0.08)',
  border: '1px solid rgba(255,255,255,0.4)',
  padding: '14px 32px',
  minHeight: 48,
  borderRadius: 2,
  cursor: 'pointer',
  letterSpacing: '0.14em',
  WebkitTapHighlightColor: 'transparent',
}
const secondaryBtn: React.CSSProperties = {
  ...primaryBtn,
  color: '#888',
  background: 'transparent',
  border: '1px solid rgba(255,255,255,0.15)',
}
