'use client'

// WorldTransition — full-screen black overlay between worlds.
//
// NORMAL WORLD timeline (worlds 1–4):
//   0 ms    : overlay on, opacity 0
//   30 ms   : fade to opacity 1
//   700 ms  : story fragment fades in
//   3000 ms : nextWorld() → gamePhase becomes 'title'
//   3400 ms : text fades out
//   3800 ms : overlay fades out
//   4800 ms : done
//
// FINAL WORLD timeline (world 5) — Option A ceremony:
//   0 ms    : overlay on, opacity 0
//   30 ms   : fade to opacity 1
//   700 ms  : "There are no aliens." fragment fades in
//   2800 ms : fragment fades out + nextWorld() called
//   2800–5800 ms: 3 seconds of pure black silence
//   5800 ms : "Appreciate your life." fades in alone (large, centred)
//   6400 ms : attribution fades in
//   11800 ms: text fades out
//   12400 ms: overlay fades out
//   13400 ms: done
//
// The component is always mounted — opacity + pointerEvents control visibility.

import { useState, useEffect, useRef } from 'react'
import { useGameStore } from '../engine/useGameStore'
import { STORY_FRAGMENTS, CLOSING_MESSAGE, CLOSING_ATTRIBUTION } from '../worlds/storyFragments'

const SERIF = '"Cormorant Garamond", Georgia, serif'

export default function WorldTransition() {
  const gamePhase = useGameStore(s => s.gamePhase)
  const worldIndex = useGameStore(s => s.worldIndex)
  const nextWorld  = useGameStore(s => s.nextWorld)

  const [opacity,        setOpacity]        = useState(0)
  const [textVisible,    setTextVisible]    = useState(false)
  const [closingVisible, setClosingVisible] = useState(false)
  const [attrVisible,    setAttrVisible]    = useState(false)
  const [blocking,       setBlocking]       = useState(false)

  const sequenceActive = useRef(false)
  const fragment       = useRef('')
  const isLastWorld    = useRef(false)
  const prevGamePhase  = useRef<string>('')

  // Schedule timers must outlive the effect that started them — `nextWorld()`
  // changes gamePhase mid-sequence, which would otherwise re-run this effect
  // and cancel the still-pending fade-out timers (the overlay then froze).
  // We park them on a ref instead, and only the unmount cleanup clears them.
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([])

  useEffect(() => {
    // Only react to entering 'transition'. Subsequent phase changes inside
    // the schedule (nextWorld → 'playing'/'title') must not interrupt it.
    if (gamePhase !== 'transition') {
      prevGamePhase.current = gamePhase
      return
    }
    if (prevGamePhase.current === 'transition' || sequenceActive.current) {
      prevGamePhase.current = gamePhase
      return
    }

    sequenceActive.current = true
    fragment.current    = STORY_FRAGMENTS[worldIndex] ?? ''
    isLastWorld.current = worldIndex === STORY_FRAGMENTS.length - 1

    const schedule = (fn: () => void, delay: number) => {
      timersRef.current.push(setTimeout(fn, delay))
    }

    setBlocking(true)
    schedule(() => setOpacity(1), 30)

    if (isLastWorld.current) {
      // ── Final world ceremony ──────────────────────────────────────────────
      schedule(() => setTextVisible(true),     700)
      schedule(() => setTextVisible(false),   2800)
      schedule(() => nextWorld(),             2800)  // game resets; overlay persists

      // 3-second silence (2800 → 5800ms) — nothing happens
      schedule(() => setClosingVisible(true), 5800)
      schedule(() => setAttrVisible(true),    6400)

      // 5-second hold (5800 → 10800ms)
      schedule(() => { setClosingVisible(false); setAttrVisible(false) }, 11800)
      schedule(() => setOpacity(0),            12400)
      schedule(() => { setBlocking(false); sequenceActive.current = false }, 13400)
    } else {
      // ── Normal world transition ────────────────────────────────────────────
      schedule(() => setTextVisible(true),  700)
      schedule(() => nextWorld(),          3000)
      schedule(() => setTextVisible(false), 3400)
      schedule(() => setOpacity(0),         3800)
      schedule(() => { setBlocking(false); sequenceActive.current = false }, 4800)
    }

    prevGamePhase.current = gamePhase
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gamePhase])

  // Only clear timers when the component truly unmounts (not on every
  // gamePhase change inside a running sequence).
  useEffect(() => () => {
    timersRef.current.forEach(clearTimeout)
    timersRef.current = []
  }, [])

  return (
    <div
      aria-hidden={!blocking}
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: '#000000',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 50,
        opacity,
        transition: 'opacity 0.9s ease',
        pointerEvents: blocking ? 'all' : 'none',
      }}
    >
      {/* Story fragment (worlds 1–5, fades before silence on last world) */}
      <p
        style={{
          fontFamily: SERIF,
          fontStyle: 'italic',
          fontSize: 'clamp(1rem, 2.8vw, 1.55rem)',
          fontWeight: 300,
          color: '#999999', // 6.3:1 on black — WCAG AA
          textAlign: 'center',
          letterSpacing: '0.12em',
          lineHeight: 1.9,
          maxWidth: 500,
          padding: '0 28px',
          whiteSpace: 'pre-line',
          opacity: textVisible ? 1 : 0,
          transition: 'opacity 1.2s ease',
        }}
      >
        {fragment.current}
      </p>

      {/* Final world only — Maezumi quote arrives alone after 3s silence */}
      {isLastWorld.current && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 16,
          }}
        >
          <p
            style={{
              fontFamily: SERIF,
              fontWeight: 300,
              fontSize: 'clamp(1.5rem, 4vw, 2.6rem)',
              color: '#ffffff',
              letterSpacing: '0.2em',
              textAlign: 'center',
              padding: '0 32px',
              opacity: closingVisible ? 1 : 0,
              transition: 'opacity 2.2s ease',
            }}
          >
            {CLOSING_MESSAGE}
          </p>
          <p
            style={{
              fontFamily: SERIF,
              fontStyle: 'italic',
              fontSize: 'clamp(0.8rem, 1.8vw, 1.05rem)',
              color: '#888888', // 5.74:1 on black — WCAG AA
              letterSpacing: '0.12em',
              opacity: attrVisible ? 1 : 0,
              transition: 'opacity 1.8s ease',
            }}
          >
            {CLOSING_ATTRIBUTION}
          </p>
        </div>
      )}
    </div>
  )
}
