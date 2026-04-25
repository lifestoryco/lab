'use client'

// Cage Mode HUD — visible only when mode === 'cage' && gamePhase === 'playing'.
//  · Level-ID intro (Mario-style "1-1") on every new level.
//  · Level countdown bar — top, contracts.
//  · Block-budget dots — top-centre. Dim as used. Red flash on missed tap
//    (over budget / off-beat / occupied).
//  · Beat indicator — pulses on the placement-allowed beat when beatLocked.
//  · Fleeting whisper on escape / fail.
//  · Level tag I/V + monster count bottom-left.

import { useEffect, useState } from 'react'
import { useGameStore } from '../engine/useGameStore'
import { isPlacementBeat } from '../audio/audioEngine'

const SERIF = '"Cormorant Garamond", Georgia, serif'
const DEFAULT_LEVEL_MS = 150_000

export default function CageHud() {
  const mode          = useGameStore(s => s.mode)
  const gamePhase     = useGameStore(s => s.gamePhase)
  const biome         = useGameStore(s => s.biome)
  const cageLevel     = useGameStore(s => s.cageLevel)
  const cageStartedAt = useGameStore(s => s.cageLevelStartedAt)
  const lastResult    = useGameStore(s => s.cageLastResult)
  const lastTapMissed = useGameStore(s => s.cageLastTapMissed)
  const worldIndex    = useGameStore(s => s.worldIndex)
  const monsters      = useGameStore(s => s.monsters)
  const blocksUsed    = useGameStore(s => s.cageBlocksUsedThisLevel)

  const [remaining, setRemaining] = useState(1)
  const [hintVisible, setHintVisible] = useState(false)
  const [failWhisper, setFailWhisper] = useState(false)
  const [missedFlash, setMissedFlash] = useState<{ at: number; reason: string } | null>(null)
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

  // Level-ID intro
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

  // Missed-tap flash (over budget / off-beat / occupied)
  useEffect(() => {
    if (!lastTapMissed) return
    setMissedFlash({ at: lastTapMissed.at, reason: lastTapMissed.reason })
    const t = setTimeout(() => setMissedFlash(null), 700)
    return () => clearTimeout(t)
  }, [lastTapMissed])

  if (mode !== 'cage' || gamePhase !== 'playing') return null

  const accent = biome.palette.hasAccent ? biome.palette.bright : '#dddddd'
  const budget = cageLevel?.blockBudget ?? 0
  const par = cageLevel?.parBlocks ?? budget
  const remainingBudget = Math.max(0, budget - blocksUsed)

  // Hint copy that actually describes the puzzle, not the legacy biome.
  const ruleNames = Array.from(new Set(monsters.map((m) => m.rule)))
  const ruleSummary = ruleNames.join(' + ')
  const baseHint = cageLevel?.beatLocked
    ? `Place on the pulse · ${ruleSummary}`
    : `${ruleSummary} · cage them all`

  const missCopy: Record<string, string> = {
    budget: 'Out of blocks.',
    beat: 'Wait for the pulse.',
    occupied: '',
  }

  return (
    <>
      {/* Level-ID intro */}
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
          {cageLevel?.name ?? ''} · par {par}
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

      {/* Block-budget dots — top centre, beneath the countdown bar */}
      <BudgetDots
        budget={budget}
        used={blocksUsed}
        par={par}
        accent={accent}
        flashOver={missedFlash?.reason === 'budget'}
      />

      {/* Beat-window indicator — only when beatLocked */}
      {cageLevel?.beatLocked && (
        <BeatWindowIndicator
          beatsPerStep={cageLevel.beatsPerStep}
          accent={accent}
        />
      )}

      {/* Rule hint, top centre — replaces stale broadcast text */}
      <div
        aria-hidden="true"
        style={{
          position: 'fixed',
          top: 86,
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
          {baseHint}
        </span>
      </div>

      {/* Missed-tap whisper */}
      {missedFlash && missCopy[missedFlash.reason] && (
        <div
          aria-hidden="true"
          style={{
            position: 'fixed',
            top: '54%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            zIndex: 9,
            pointerEvents: 'none',
            opacity: missedFlash ? 1 : 0,
            transition: 'opacity 0.4s ease',
            fontFamily: SERIF,
            fontStyle: 'italic',
            fontSize: 'clamp(0.85rem, 1.7vw, 1.05rem)',
            color: '#cc8844',
            letterSpacing: '0.12em',
          }}
        >
          {missCopy[missedFlash.reason]}
        </div>
      )}

      {/* Level tag — bottom-left */}
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
        {['I', 'II', 'III', 'IV', 'V'][worldIndex]} · {monsters.length === 1 ? 'hunted' : `${monsters.length} hunted`} · {remainingBudget} left
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
          {lastResult && !lastResult.solved
            ? (blocksUsed >= (cageLevel?.blockBudget ?? 0)
                ? 'Out of blocks. Try again.'
                : 'It reached the edge.')
            : ''}
        </span>
      </div>
    </>
  )
}

// Block-budget dots — N total, dimmed for used. Star-eligible cells (1..par)
// glow brighter than the over-par margin (par+1..budget).
function BudgetDots({
  budget,
  used,
  par,
  accent,
  flashOver,
}: {
  budget: number
  used: number
  par: number
  accent: string
  flashOver: boolean
}) {
  if (budget <= 0 || budget > 12) return null  // 1-block silence levels skip; sanity cap.
  const dots: JSX.Element[] = []
  for (let i = 0; i < budget; i++) {
    const isUsed = i < used
    const isOverPar = i >= par
    const size = isOverPar ? 6 : 8
    const color = isUsed
      ? (isOverPar ? '#553333' : '#444444')
      : (isOverPar ? `${accent}66` : accent)
    dots.push(
      <span
        key={i}
        style={{
          width: size,
          height: size,
          borderRadius: '50%',
          backgroundColor: color,
          boxShadow: !isUsed && !isOverPar ? `0 0 8px ${accent}88` : 'none',
          transition: 'background-color 0.25s ease',
        }}
      />,
    )
  }
  return (
    <div
      aria-hidden="true"
      style={{
        position: 'fixed',
        top: 38,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 9,
        pointerEvents: 'none',
        display: 'flex',
        gap: 8,
        alignItems: 'center',
        padding: '8px 14px',
        borderRadius: 999,
        background: flashOver ? 'rgba(204, 68, 68, 0.18)' : 'rgba(0,0,0,0.25)',
        transition: 'background-color 0.4s ease',
      }}
    >
      {dots}
    </div>
  )
}

// Beat-window indicator — pulses brighter on the placement-allowed beat.
// Polls the audio engine via useFrame at the canvas root would be cleaner,
// but the HUD lives outside R3F, so we use a 30Hz interval.
function BeatWindowIndicator({
  beatsPerStep,
  accent,
}: {
  beatsPerStep: number
  accent: string
}) {
  const [active, setActive] = useState(false)
  useEffect(() => {
    const id = setInterval(() => {
      setActive(isPlacementBeat(beatsPerStep))
    }, 33)
    return () => clearInterval(id)
  }, [beatsPerStep])
  return (
    <div
      aria-hidden="true"
      style={{
        position: 'fixed',
        top: 60,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 9,
        pointerEvents: 'none',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          backgroundColor: active ? accent : '#222',
          boxShadow: active ? `0 0 12px ${accent}` : 'none',
          transition: 'background-color 0.08s linear, box-shadow 0.08s linear',
        }}
      />
      <span style={{
        fontFamily: SERIF,
        fontStyle: 'italic',
        fontSize: 10,
        color: active ? '#cccccc' : '#555555',
        letterSpacing: '0.18em',
        transition: 'color 0.08s linear',
      }}>
        place
      </span>
    </div>
  )
}
