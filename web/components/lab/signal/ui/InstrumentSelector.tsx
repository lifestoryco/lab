'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useGameStore } from '../engine/useGameStore'
import { INSTRUMENT_COLORS, INSTRUMENT_NAMES, rampBpm } from '../audio/audioEngine'

const BPM_HINT_FLAG = 'signal.bpm.hintSeen'
const BPM_MIN = 30
const BPM_MAX = 200
// Tap-tempo: accept taps up to 2s apart; use the last 4 intervals
const TAP_WINDOW_MS = 2000
const TAP_BUFFER = 4
// Press-and-hold threshold before drag-scrub engages
const DRAG_ENGAGE_MS = 120
const DRAG_ENGAGE_PX = 4
// 1 px of vertical travel = 0.5 BPM
const DRAG_BPM_PER_PX = 0.5

function clampBpm(v: number) {
  return Math.max(BPM_MIN, Math.min(BPM_MAX, v))
}

export default function InstrumentSelector() {
  const selectedInstrument = useGameStore(s => s.selectedInstrument)
  const selectInstrument = useGameStore(s => s.selectInstrument)
  const gamePhase = useGameStore(s => s.gamePhase)
  const saturation = useGameStore(s => s.saturation)
  const biome = useGameStore(s => s.biome)
  const bpm = useGameStore(s => s.bpm)
  const playMode = useGameStore(s => s.mode)
  const setBpm = useGameStore(s => s.setBpm)

  const [visible, setVisible] = useState(true)
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)
  const fadeTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // BPM control — tap-tempo + press-hold-and-drag-scrub.
  const tapTimes = useRef<number[]>([])
  const pressStart = useRef<{ t: number; y: number; bpm: number } | null>(null)
  const pressTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const isDragging = useRef<boolean>(false)
  const [bpmPressing, setBpmPressing] = useState(false)
  const [bpmHintVisible, setBpmHintVisible] = useState(false)

  // Auto-fade after 3s of inactivity
  const resetFadeTimer = useCallback(() => {
    setVisible(true)
    if (fadeTimer.current) clearTimeout(fadeTimer.current)
    fadeTimer.current = setTimeout(() => setVisible(false), 3000)
  }, [])

  useEffect(() => {
    resetFadeTimer()
    return () => {
      if (fadeTimer.current) clearTimeout(fadeTimer.current)
    }
  }, [resetFadeTimer])

  // Show on any pointer movement
  useEffect(() => {
    const handler = () => resetFadeTimer()
    window.addEventListener('pointermove', handler)
    return () => window.removeEventListener('pointermove', handler)
  }, [resetFadeTimer])

  // Arrow keys: up/down = BPM, left/right = instrument
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (gamePhase !== 'playing') return
      const step = e.shiftKey ? 10 : 2
      if (e.key === 'ArrowUp') {
        const next = clampBpm(bpm + step)
        setBpm(next)
        rampBpm(next)
        resetFadeTimer()
      } else if (e.key === 'ArrowDown') {
        const next = clampBpm(bpm - step)
        setBpm(next)
        rampBpm(next)
        resetFadeTimer()
      } else if (e.key === 'ArrowRight') {
        selectInstrument((selectedInstrument + 1) % 5)
        resetFadeTimer()
      } else if (e.key === 'ArrowLeft') {
        selectInstrument((selectedInstrument + 4) % 5)
        resetFadeTimer()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [gamePhase, bpm, setBpm, selectedInstrument, selectInstrument, resetFadeTimer])

  // First-visit BPM hint — shows once, cleared after 3s.
  useEffect(() => {
    if (gamePhase !== 'playing') return
    if (typeof window === 'undefined') return
    if (window.localStorage.getItem(BPM_HINT_FLAG)) return
    setBpmHintVisible(true)
    const tid = setTimeout(() => {
      setBpmHintVisible(false)
      window.localStorage.setItem(BPM_HINT_FLAG, '1')
    }, 3000)
    return () => clearTimeout(tid)
  }, [gamePhase])

  // Commit a new BPM with a ramp (avoids clicks during rapid scrubs).
  const commitBpm = useCallback((next: number) => {
    const v = clampBpm(Math.round(next))
    setBpm(v)
    rampBpm(v)
  }, [setBpm])

  // Press handler for the BPM pad — differentiates tap-tempo vs drag scrub.
  const handleBpmPointerDown = useCallback((e: React.PointerEvent<HTMLButtonElement>) => {
    e.preventDefault()
    ;(e.target as HTMLElement).setPointerCapture?.(e.pointerId)
    const t = performance.now()
    pressStart.current = { t, y: e.clientY, bpm }
    isDragging.current = false
    setBpmPressing(true)
    resetFadeTimer()
    // If the user holds without moving past the threshold, engage drag mode.
    if (pressTimer.current) clearTimeout(pressTimer.current)
    pressTimer.current = setTimeout(() => {
      if (pressStart.current) isDragging.current = true
    }, DRAG_ENGAGE_MS)
  }, [bpm, resetFadeTimer])

  const handleBpmPointerMove = useCallback((e: React.PointerEvent<HTMLButtonElement>) => {
    const ps = pressStart.current
    if (!ps) return
    const dy = e.clientY - ps.y
    // Engage drag early if the user moves past the px threshold before the timer.
    if (!isDragging.current && Math.abs(dy) > DRAG_ENGAGE_PX) {
      isDragging.current = true
      if (pressTimer.current) clearTimeout(pressTimer.current)
    }
    if (isDragging.current) {
      commitBpm(ps.bpm - dy * DRAG_BPM_PER_PX) // drag up = faster
    }
  }, [commitBpm])

  const handleBpmPointerUp = useCallback((e: React.PointerEvent<HTMLButtonElement>) => {
    const ps = pressStart.current
    pressStart.current = null
    setBpmPressing(false)
    if (pressTimer.current) { clearTimeout(pressTimer.current); pressTimer.current = null }
    ;(e.target as HTMLElement).releasePointerCapture?.(e.pointerId)
    if (!ps) return

    if (isDragging.current) {
      isDragging.current = false
      return // drag already committed its final value
    }

    // Tap-tempo: record the tap, average the last 4 intervals when available.
    const now = performance.now()
    const buf = tapTimes.current
    // Drop taps older than the window
    while (buf.length && now - buf[0] > TAP_WINDOW_MS) buf.shift()
    buf.push(now)
    if (buf.length > TAP_BUFFER) buf.shift()
    if (buf.length >= 2) {
      const intervals: number[] = []
      for (let i = 1; i < buf.length; i++) intervals.push(buf[i] - buf[i - 1])
      const avg = intervals.reduce((a, b) => a + b, 0) / intervals.length
      if (avg > 0) commitBpm(60_000 / avg)
    }
  }, [commitBpm])

  const handleBpmPointerCancel = useCallback(() => {
    pressStart.current = null
    setBpmPressing(false)
    if (pressTimer.current) { clearTimeout(pressTimer.current); pressTimer.current = null }
    isDragging.current = false
  }, [])

  if (gamePhase !== 'playing') return null

  // Dot accent color: B&W default, biome accent when saturated
  const getDotColor = (index: number) => {
    const base = INSTRUMENT_COLORS[index]
    if (!biome.palette.hasAccent || saturation < 0.1) return base
    const accents = [biome.palette.bright, biome.palette.primary, biome.palette.deep]
    const accent = accents[index % accents.length]
    if (saturation > 0.5) return accent
    return base
  }

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 'clamp(16px, 3vh, 48px)', // responsive — not fixed 32px
        left: '50%',
        transform: 'translateX(-50%)',
        display: 'flex',
        gap: 0, // gaps handled by button padding
        alignItems: 'center',
        opacity: visible ? 1 : 0,
        transition: 'opacity 0.6s ease',
        pointerEvents: visible ? 'auto' : 'none',
        zIndex: 10,
      }}
    >
      {INSTRUMENT_COLORS.map((_, index) => (
        <button
          key={index}
          onClick={() => {
            selectInstrument(index)
            resetFadeTimer()
          }}
          onMouseEnter={() => setHoveredIndex(index)}
          onMouseLeave={() => setHoveredIndex(null)}
          aria-label={INSTRUMENT_NAMES[index]}
          aria-pressed={index === selectedInstrument}
          style={{
            // 44×44px touch target (WCAG 2.5.5)
            width: 44,
            height: 44,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: 0,
            position: 'relative',
            WebkitTapHighlightColor: 'transparent',
          }}
        >
          {/* Visual dot — smaller than hit area */}
          <span
            style={{
              display: 'block',
              width: index === selectedInstrument ? 16 : 10,
              height: index === selectedInstrument ? 16 : 10,
              borderRadius: '50%',
              backgroundColor: getDotColor(index),
              border: index === selectedInstrument
                ? '2px solid #ffffff'
                : '1px solid rgba(255,255,255,0.25)',
              transition: 'all 0.2s ease',
              // Subtle pulse ring on selected dot
              boxShadow: index === selectedInstrument
                ? `0 0 0 3px rgba(255,255,255,0.08)`
                : 'none',
            }}
          />

          {/* Tooltip on hover */}
          {hoveredIndex === index && (
            <span
              aria-hidden="true"
              style={{
                position: 'absolute',
                bottom: 42,
                left: '50%',
                transform: 'translateX(-50%)',
                fontFamily: '"Cormorant Garamond", Georgia, serif',
                fontStyle: 'italic',
                fontSize: 12,
                color: '#888888', // #888 = 5.74:1 on black, passes AA
                whiteSpace: 'nowrap',
                pointerEvents: 'none',
              }}
            >
              {INSTRUMENT_NAMES[index]}
            </span>
          )}
        </button>
      ))}

      {/* BPM control — tap the pad to sync (tap-tempo), press-and-drag vertically to scrub. */}
      <button
        onPointerDown={handleBpmPointerDown}
        onPointerMove={handleBpmPointerMove}
        onPointerUp={handleBpmPointerUp}
        onPointerCancel={handleBpmPointerCancel}
        aria-label={`Beats per minute. Current: ${bpm}. Tap to sync or drag vertically to adjust.`}
        style={{
          // 44×44 hit area via padding on a compact visual label
          minWidth: 56,
          minHeight: 44,
          padding: '6px 10px',
          marginLeft: 4,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 2,
          background: 'none',
          border: 'none',
          cursor: bpmPressing ? 'ns-resize' : 'pointer',
          WebkitTapHighlightColor: 'transparent',
          touchAction: 'none', // prevent scroll-hijack during vertical drag
          position: 'relative',
          userSelect: 'none',
        }}
      >
        {playMode === 'cage' && (
          <span
            aria-hidden="true"
            style={{
              fontFamily: '"Cormorant Garamond", Georgia, serif',
              fontSize: 9,
              color: '#666',
              letterSpacing: '0.2em',
              textTransform: 'uppercase',
              pointerEvents: 'none',
            }}
          >
            Speed · {bpm < 90 ? 'slow' : bpm < 120 ? 'steady' : bpm < 145 ? 'fast' : 'frantic'}
          </span>
        )}
        <span
          style={{
            fontFamily: '"Cormorant Garamond", Georgia, serif',
            fontSize: 12,
            color: '#888888',
            letterSpacing: '0.08em',
            transform: bpmPressing ? 'scale(1.2)' : 'scale(1)',
            transition: 'transform 0.12s ease',
            pointerEvents: 'none',
          }}
        >
          {bpm} bpm
        </span>
        {bpmHintVisible && (
          <span
            aria-hidden="true"
            style={{
              fontFamily: '"Cormorant Garamond", Georgia, serif',
              fontStyle: 'italic',
              fontSize: 10,
              color: '#888888',
              letterSpacing: '0.1em',
              opacity: bpmHintVisible ? 1 : 0,
              transition: 'opacity 0.8s ease',
              pointerEvents: 'none',
              whiteSpace: 'nowrap',
            }}
          >
            tap or drag
          </span>
        )}
      </button>
    </div>
  )
}
