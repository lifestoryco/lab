'use client'

// Cage Mode HUD — visible only when mode === 'cage' && gamePhase === 'playing'.
//  · Top bar contracts as the level's time budget runs out.
//  · Biome broadcast hint repurposed as the level rule hint.
//  · Fleeting whisper on escape / fail.
//  · Level tag (I / V) bottom-left to confirm progress at a glance.

import { useEffect, useState } from 'react'
import { useGameStore } from '../engine/useGameStore'

const SERIF = '"Cormorant Garamond", Georgia, serif'
const DEFAULT_LEVEL_MS = 150_000 // same 2:30 as Zen

export default function CageHud() {
  const mode          = useGameStore(s => s.mode)
  const gamePhase     = useGameStore(s => s.gamePhase)
  const biome         = useGameStore(s => s.biome)
  const cageLevel     = useGameStore(s => s.cageLevel)
  const cageStartedAt = useGameStore(s => s.cageLevelStartedAt)
  const lastResult    = useGameStore(s => s.cageLastResult)
  const worldIndex    = useGameStore(s => s.worldIndex)
  const monster       = useGameStore(s => s.monster)

  const [remaining, setRemaining] = useState(1)
  const [hintVisible, setHintVisible] = useState(false)
  const [failWhisper, setFailWhisper] = useState(false)
  // Level-ID intro — Mario-style "1-1" tag that fades in on every new level.
  const [introVisible, setIntroVisible] = useState(false)

  // Countdown bar
  useEffect(() => {
    if (!cageStartedAt || !cageLevel) {
      setRemaining(1)
      return
    }
    const limitMs = cageLevel.timeLimitMs ?? DEFAULT_LEVEL_MS
    let raf: number
    const tick = () => {
      const elapsed = performance.now() - cageStartedAt
      const left = Math.max(0, 1 - elapsed / limitMs)
      setRemaining(left)
      if (left > 0 && gamePhase === 'playing') raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [cageStartedAt, cageLevel, gamePhase])

  // Rule hint — fades in when a new level starts
  useEffect(() => {
    if (mode !== 'cage' || !cageLevel) { setHintVisible(false); return }
    setHintVisible(true)
    const t = setTimeout(() => setHintVisible(false), 4000)
    return () => clearTimeout(t)
  }, [mode, cageLevel?.id])

  // Level-ID intro — shows for 2.5s at every new level.
  useEffect(() => {
    if (mode !== 'cage' || !cageLevel) { setIntroVisible(false); return }
    setIntroVisible(true)
    const t = setTimeout(() => setIntroVisible(false), 2500)
    return () => clearTimeout(t)
  }, [mode, cageLevel?.id])

  // Fail whisper
  useEffect(() => {
    if (lastResult && !lastResult.solved) {
      setFailWhisper(true)
      const t = setTimeout(() => setFailWhisper(false), 2500)
      return () => clearTimeout(t)
    }
  }, [lastResult])

  if (mode !== 'cage' || gamePhase !== 'playing') return null

  const accent = biome.palette.hasAccent ? biome.palette.bright : '#dddddd'

  return (
    <>
      {/* Level-ID intro: "1-1" + biome name. Classic-game tag. */}
      <div
        aria-hidden="true"
        style={{
          position: 'fixed',
          top: '38%',
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 9,
          pointerEvents: 'none',
          opacity: introVisible ? 1 : 0,
          transition: 'opacity 0.9s ease',
          textAlign: 'center',
        }}
      >
        <div style={{
          fontFamily: SERIF,
          fontWeight: 300,
          fontSize: 'clamp(2.4rem, 8vw, 5rem)',
          color: '#ffffff',
          letterSpacing: '0.2em',
          textShadow: `0 0 30px ${accent}`,
        }}>
          {cageLevel?.id ?? ''}
        </div>
        <div style={{
          fontFamily: SERIF,
          fontStyle: 'italic',
          fontSize: 'clamp(0.8rem, 1.6vw, 1rem)',
          color: '#999',
          letterSpacing: '0.16em',
          marginTop: 6,
        }}>
          {cageLevel?.name ?? ''}
        </div>
      </div>

      {/* Level countdown bar — top, contracts */}
      <div
        aria-hidden="true"
        style={{
          position: 'fixed',
          top: 12,
          left: '12%',
          right: '12%',
          zIndex: 9,
          pointerEvents: 'none',
        }}
      >
        <div
          style={{
            height: 1,
            width: `${remaining * 100}%`,
            margin: '0 auto',
            backgroundColor: accent,
            opacity: 0.6,
            transition: 'width 60ms linear',
          }}
        />
      </div>

      {/* Rule hint, top centre */}
      <div
        aria-hidden="true"
        style={{
          position: 'fixed',
          top: 32,
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 9,
          pointerEvents: 'none',
          opacity: hintVisible ? 1 : 0,
          transition: 'opacity 1.4s ease',
          textAlign: 'center',
        }}
      >
        <span style={{
          fontFamily: SERIF,
          fontStyle: 'italic',
          fontSize: 'clamp(0.7rem, 1.4vw, 0.85rem)',
          color: '#888',
          letterSpacing: '0.12em',
        }}>
          {biome.broadcastHint}
        </span>
      </div>

      {/* Level tag — bottom-left, same muted style as the top-right Roman numeral */}
      <div
        aria-label={`Level ${worldIndex + 1} of 5`}
        style={{
          position: 'fixed',
          bottom: 24,
          left: 24,
          zIndex: 9,
          pointerEvents: 'none',
          fontFamily: SERIF,
          fontSize: 12,
          color: '#ffffff',
          opacity: 0.28,
          letterSpacing: '0.18em',
        }}
      >
        {['I', 'II', 'III', 'IV', 'V'][worldIndex]} · {monster ? 'hunted' : '—'}
      </div>

      {/* Fail whisper */}
      <div
        aria-hidden="true"
        style={{
          position: 'fixed',
          top: '48%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 9,
          pointerEvents: 'none',
          opacity: failWhisper ? 1 : 0,
          transition: 'opacity 1.2s ease',
        }}
      >
        <span style={{
          fontFamily: SERIF,
          fontStyle: 'italic',
          fontSize: 'clamp(0.8rem, 1.6vw, 1rem)',
          color: '#cc4444',
          letterSpacing: '0.12em',
        }}>
          It reached the edge.
        </span>
      </div>
    </>
  )
}
