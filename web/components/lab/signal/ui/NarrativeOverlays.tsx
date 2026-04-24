'use client'

// NarrativeOverlays — all faint in-world text that appears during active play.
// Nothing here interrupts gameplay: every element is non-interactive, semi-transparent,
// and fades in naturally so the player absorbs it peripherally.
//
// Layers rendered (bottom to top):
//   1. Subtitle whisper   — biome subtitle persists at bottom for first 60s
//   2. Signal-strength    — fires at blockCount 2; first visit also shows a gesture cue
//   3. Ambient play text  — biome.playText fades in at 60s (session is 2:30 total now)
//   4. Portal whisper     — biome.portalWhisper appears once a chain ≥3 opens the portal

import { useState, useEffect, useRef } from 'react'
import { useGameStore } from '../engine/useGameStore'

const PLAY_TEXT_DELAY_MS = 60_000   // 60 s — session is 150 000 ms total
const SUBTITLE_DURATION_MS = 60_000 // 60 s from game start
const GESTURE_CUE_FLAG = 'signal.gestureCueSeen'

const SERIF = '"Cormorant Garamond", Georgia, serif'

export default function NarrativeOverlays() {
  const gamePhase         = useGameStore(s => s.gamePhase)
  const biome             = useGameStore(s => s.biome)
  const elapsedMs         = useGameStore(s => s.elapsedMs)
  const blockCount        = useGameStore(s => s.blocks.size)
  const worldIndex        = useGameStore(s => s.worldIndex)
  const hasTriggeredChain = useGameStore(s => s.hasTriggeredChain)

  // Gesture cue is only shown on the very first visit, anywhere.
  const [showGestureCue, setShowGestureCue] = useState(false)

  // ── 1. Subtitle whisper ─────────────────────────────────────────────────────
  // Show for first 60s of each world. Resets on world advance.
  const [subtitleVisible, setSubtitleVisible] = useState(false)
  const subtitleTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (gamePhase !== 'playing') { setSubtitleVisible(false); return }
    setSubtitleVisible(true)
    subtitleTimer.current = setTimeout(() => setSubtitleVisible(false), SUBTITLE_DURATION_MS)
    return () => {
      if (subtitleTimer.current) clearTimeout(subtitleTimer.current)
    }
  }, [gamePhase, worldIndex]) // reset on each new world

  // ── 2. Signal-strength hint ──────────────────────────────────────────────────
  // Shows once when block count first reaches 4, fades out after 4s.
  // Single effect tracks all three dependencies so reset and trigger
  // can't race if worldIndex and blockCount change on the same tick.
  const [strengthVisible, setStrengthVisible] = useState(false)
  const strengthShown = useRef(false)
  const strengthTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (strengthTimer.current) clearTimeout(strengthTimer.current)

    // Reset on every world change (worldIndex in deps below)
    if (blockCount === 0) {
      strengthShown.current = false
      setStrengthVisible(false)
      setShowGestureCue(false)
      return
    }

    if (blockCount === 2 && !strengthShown.current && gamePhase === 'playing') {
      strengthShown.current = true
      setStrengthVisible(true)

      // First-visit-only: pair the caption with a silent gesture cue.
      const seen = typeof window !== 'undefined'
        ? window.localStorage.getItem(GESTURE_CUE_FLAG)
        : 'seen'
      if (!seen) {
        setShowGestureCue(true)
      }

      strengthTimer.current = setTimeout(() => {
        setStrengthVisible(false)
        setShowGestureCue(false)
        if (typeof window !== 'undefined') {
          window.localStorage.setItem(GESTURE_CUE_FLAG, '1')
        }
      }, 4000)
    }

    return () => {
      if (strengthTimer.current) clearTimeout(strengthTimer.current)
    }
  }, [blockCount, gamePhase, worldIndex])

  // ── 3. Ambient play text ─────────────────────────────────────────────────────
  // biome.playText fades in at 2:30 and stays until nightfall
  const playTextVisible = gamePhase === 'playing' && elapsedMs >= PLAY_TEXT_DELAY_MS

  // ── 4. Portal whisper ────────────────────────────────────────────────────────
  // Appears when the portal is visible (first chain ≥3 has fired).
  const portalWhisperVisible = gamePhase === 'playing' && hasTriggeredChain

  if (gamePhase !== 'playing') return null

  return (
    <>
      {/* 1. Subtitle whisper — bottom centre, fades out after 60s */}
      <div
        aria-hidden="true"
        style={{
          position: 'fixed',
          bottom: 'clamp(80px, 12vh, 110px)', // above InstrumentSelector dots
          left: '50%',
          transform: 'translateX(-50%)',
          pointerEvents: 'none',
          zIndex: 8,
          opacity: subtitleVisible ? 1 : 0,
          transition: 'opacity 2s ease',
          textAlign: 'center',
        }}
      >
        <span style={{
          fontFamily: SERIF,
          fontStyle: 'italic',
          fontSize: 'clamp(0.7rem, 1.6vw, 0.9rem)',
          color: '#888888', // 5.74:1 on black — WCAG AA
          letterSpacing: '0.12em',
        }}>
          {biome.subtitle}
        </span>
      </div>

      {/* 2. Signal-strength hint — centre screen, brief.
             First-visit-only: a radial pulse sits beside the caption to signal
             that the next tap should land adjacent to an existing block. */}
      <div
        aria-hidden="true"
        style={{
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          pointerEvents: 'none',
          zIndex: 8,
          opacity: strengthVisible ? 1 : 0,
          transition: 'opacity 1.2s ease',
          textAlign: 'center',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
        }}
      >
        <span style={{
          fontFamily: SERIF,
          fontStyle: 'italic',
          fontSize: 'clamp(0.8rem, 1.8vw, 1rem)',
          color: '#888888',
          letterSpacing: '0.14em',
        }}>
          Place another sound right beside it.
        </span>
        {showGestureCue && (
          <svg
            width="22"
            height="22"
            viewBox="0 0 22 22"
            fill="none"
            style={{ flexShrink: 0 }}
          >
            <circle
              cx="11"
              cy="11"
              r="4"
              stroke="#ffffff"
              strokeOpacity="0.4"
              strokeWidth="1"
              style={{
                transformOrigin: '11px 11px',
                animation: 'signalGesturePulse 1.4s ease-in-out infinite',
              }}
            />
            <style>{`
              @keyframes signalGesturePulse {
                0%, 100% { transform: scale(0.2); opacity: 0; }
                50%      { transform: scale(1);   opacity: 1; }
              }
            `}</style>
          </svg>
        )}
      </div>

      {/* 3. Ambient play text — appears at 2:30, stays until end */}
      <div
        aria-hidden="true"
        style={{
          position: 'fixed',
          top: '22%',
          left: '50%',
          transform: 'translateX(-50%)',
          pointerEvents: 'none',
          zIndex: 8,
          opacity: playTextVisible ? 1 : 0,
          transition: 'opacity 3s ease',
          textAlign: 'center',
          maxWidth: 360,
          padding: '0 24px',
        }}
      >
        <span style={{
          fontFamily: SERIF,
          fontStyle: 'italic',
          fontSize: 'clamp(0.75rem, 1.5vw, 0.9rem)',
          color: '#666666', // 5.74:1 on black — WCAG AA
          letterSpacing: '0.12em',
          lineHeight: 1.7,
        }}>
          {biome.playText}
        </span>
      </div>

      {/* 4. Portal whisper — appears when portal appears */}
      <div
        aria-hidden="true"
        style={{
          position: 'fixed',
          bottom: '32%',
          left: 'clamp(16px, 8vw, 80px)',
          pointerEvents: 'none',
          zIndex: 8,
          opacity: portalWhisperVisible ? 1 : 0,
          transition: 'opacity 2.5s ease',
        }}
      >
        <span style={{
          fontFamily: SERIF,
          fontStyle: 'italic',
          fontSize: 'clamp(0.7rem, 1.4vw, 0.85rem)',
          color: '#666666',
          letterSpacing: '0.1em',
        }}>
          {biome.portalWhisper}
        </span>
      </div>
    </>
  )
}
