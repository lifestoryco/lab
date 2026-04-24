'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { VT323 } from 'next/font/google'
import { ARCHETYPE_MAP, type Archetype, type GridState } from './archetypes'

const vt323 = VT323({ weight: '400', subsets: ['latin'] })

// ─── ASCII gradient (70 chars, 0=darkest → 69=brightest) ─────────────────────
const GRADIENT = " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"

// ─── Boot lines (after intro) ─────────────────────────────────────────────────
const BOOT_LINES = ['─────────────────────────────────────────', '']

// ─── Library output ───────────────────────────────────────────────────────────
const LIBRARY_LINES = [
  'APOTHECARY ─────────────────────────────────',
  '  attractor    Cosmic filament nebula',
  '  chrysalis    Machine elves bloom',
  '  codex        Ancient labyrinthine scripture',
  '  drift        Hazy slow-motion drift',
  '  fungl        Mycelial bioluminescent trails',
  '  gondwana     Ancient tectonic fracture',
  '  hydro        Liquid metal coalescence',
  '  kemet        Aperiodic sacred geometry',
  '  lightning    Fractal dendrite crystallization',
  '  luca         Primordial Turing patterns',
  '  luminous     Spectral orbit archaeology',
  '  morphic      Turbulent cloud consciousness',
  '  nexus        Hyperdimensional fiber cascade',
  '  ouroboros    Infinite self-consuming loop',
  '  parallax     Dimensional interference shimmer',
  '  sphinx       Topological paradox engine',
  '  spore        Bioluminescent forest breath',
  '  surya        Divine parametric radiance',
  '  trappist     Alien exoplanet hypnosis',
  '  warmwind     Divergence-free smoke currents',
  '  wavefunction Quantum superposition shimmer',
  '  zazen        Meditative void presence',
  '─────────────────────────────────────────',
]

type Phase = 'intro' | 'booting' | 'idle' | 'animating' | 'fading' | 'reflecting'

// ─── Component ────────────────────────────────────────────────────────────────

export default function AcidPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animFrameRef = useRef<number>(0)
  const lastFrameTimeRef = useRef<number>(0)
  const frameCountRef = useRef<number>(0)
  const gridStateRef = useRef<GridState | null>(null)
  const currentArchetypeRef = useRef<Archetype | null>(null)
  const tRef = useRef<number>(0)

  const [phase, setPhase] = useState<Phase>('intro')
  const [bootLines, setBootLines] = useState<string[]>([])
  const [termOutput, setTermOutput] = useState<string[]>([])
  const [input, setInput] = useState('')
  const [canvasOpacity, setCanvasOpacity] = useState(0)
  const [reflection, setReflection] = useState('')
  const [reflectionVisible, setReflectionVisible] = useState(false)

  const inputRef = useRef<HTMLInputElement>(null)

  // ─── Intro → booting transition ─────────────────────────────────────────────
  useEffect(() => {
    if (phase !== 'intro') return
    const timer = setTimeout(() => setPhase('booting'), 6600)
    return () => clearTimeout(timer)
  }, [phase])

  // ─── Boot sequence ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (phase !== 'booting') return
    let cancelled = false
    const lines: string[] = []
    BOOT_LINES.forEach((line, i) => {
      setTimeout(() => {
        if (cancelled) return
        lines.push(line)
        setBootLines([...lines])
        if (i === BOOT_LINES.length - 1) {
          setTimeout(() => { if (!cancelled) setPhase('idle') }, 200)
        }
      }, 120 * (i + 1))
    })
    return () => { cancelled = true }
  }, [phase])

  // ─── Focus input when idle ──────────────────────────────────────────────────
  useEffect(() => {
    if (phase === 'idle') inputRef.current?.focus()
  }, [phase])

  // ─── Canvas sizing ──────────────────────────────────────────────────────────
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const resize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }
    resize()
    window.addEventListener('resize', resize)
    return () => window.removeEventListener('resize', resize)
  }, [])

  // ─── Escape key handler ─────────────────────────────────────────────────────
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      if (phase === 'animating' && currentArchetypeRef.current) {
        // Esc during animation → show reflection, then idle
        cancelAnimation()
        startReflection(currentArchetypeRef.current)
      } else if (phase === 'fading' || phase === 'reflecting') {
        cancelAnimation()
        resetToIdle()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [phase]) // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Animation loop ─────────────────────────────────────────────────────────
  const cancelAnimation = useCallback(() => {
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current)
      animFrameRef.current = 0
    }
  }, [])

  const resetToIdle = useCallback(() => {
    setCanvasOpacity(0)
    setReflectionVisible(false)
    setReflection('')
    setPhase('idle')
    gridStateRef.current = null
    currentArchetypeRef.current = null
    tRef.current = 0
    frameCountRef.current = 0
    setTimeout(() => { inputRef.current?.focus() }, 50)
  }, [])

  const startReflection = useCallback((arch: Archetype) => {
    setPhase('fading')
    setCanvasOpacity(0)
    setReflection(arch.reflection)
    setTimeout(() => {
      setReflectionVisible(true)
      setPhase('reflecting')
      setTimeout(() => {
        setReflectionVisible(false)
        setTimeout(() => { resetToIdle() }, 600)
      }, 2800)
    }, 900)
  }, [resetToIdle])

  const runAnimation = useCallback((arch: Archetype) => {
    const canvas = canvasRef.current
    if (!canvas) return

    document.fonts.ready.then(() => {
      const charH = 15
      const charW = 9
      const cols = Math.floor(canvas.width / charW)
      const rows = Math.floor(canvas.height / charH)

      if (arch.init) gridStateRef.current = arch.init(cols, rows)

      currentArchetypeRef.current = arch
      tRef.current = 0
      frameCountRef.current = 0
      lastFrameTimeRef.current = 0

      setCanvasOpacity(1)
      setPhase('animating')

      const loop = (now: number) => {
        if (!currentArchetypeRef.current) return
        const a = currentArchetypeRef.current

        if (now - lastFrameTimeRef.current < 40) {
          animFrameRef.current = requestAnimationFrame(loop)
          return
        }
        lastFrameTimeRef.current = now

        const ctx = canvas.getContext('2d')
        if (!ctx) return

        const cw = canvas.width
        const ch = canvas.height
        const cCols = Math.floor(cw / charW)
        const cRows = Math.floor(ch / charH)

        if (a.update && gridStateRef.current) {
          a.update(gridStateRef.current, tRef.current, frameCountRef.current, cCols, cRows)
        }

        ctx.fillStyle = '#000'
        ctx.fillRect(0, 0, cw, ch)
        ctx.font = `15px 'VT323', monospace`
        ctx.textBaseline = 'top'

        for (let row = 0; row < cRows; row++) {
          for (let col = 0; col < cCols; col++) {
            const nx = (col - cCols * 0.5) / (cCols * 0.25)
            const ny = (row - cRows * 0.5) / (cRows * 0.25) * 0.55 * 2.0

            let val: number
            if (a.gridPixel && gridStateRef.current) {
              val = a.gridPixel(gridStateRef.current, col, row)
            } else if (a.pixel) {
              val = a.pixel(nx, ny, tRef.current)
            } else {
              val = 0
            }

            val = Math.max(0, Math.min(1, val))
            const [r, g, b] = a.palette(val, tRef.current)
            const ci = Math.floor(val * 69)
            const char = GRADIENT[ci] ?? ' '

            ctx.fillStyle = `rgb(${r},${g},${b})`
            ctx.fillText(char, col * charW, row * charH)
          }
        }

        tRef.current += a.tStep
        frameCountRef.current++

        // ── Infinite loop: no frame limit. Runs until ESC. ──
        animFrameRef.current = requestAnimationFrame(loop)
      }

      animFrameRef.current = requestAnimationFrame(loop)
    })
  }, [])

  // ─── Command handler ────────────────────────────────────────────────────────
  const handleCommand = useCallback((raw: string) => {
    const cmd = raw.trim().toLowerCase()
    if (cmd === 'library') {
      setTermOutput(prev => [...prev, ...LIBRARY_LINES])
      return
    }
    const arch = ARCHETYPE_MAP[cmd]
    if (arch) {
      cancelAnimation()
      runAnimation(arch)
      return
    }
    // Unknown or empty — silent rejection
  }, [cancelAnimation, runAnimation])

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleCommand(input)
      setInput('')
    }
  }, [input, handleCommand])

  // Cleanup on unmount
  useEffect(() => { return () => cancelAnimation() }, [cancelAnimation])

  const isTerminalVisible = phase === 'booting' || phase === 'idle'
  const showPrompt = phase === 'idle'

  return (
    <>
      {/* ── Global styles ──────────────────────────────────────────── */}
      <style>{`
        @keyframes flicker {
          0%, 89%, 91%, 93%, 100% { opacity: 1; }
          90% { opacity: 0.93; }
          92% { opacity: 0.97; }
        }
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
        /* ── Intro: ACID materializes from chaos ── */
        @keyframes acid-materialize {
          0%   { opacity: 0; filter: blur(70px) brightness(5); transform: scale(2.8); letter-spacing: 2em; }
          12%  { opacity: 0.7; filter: blur(18px) brightness(2.2); transform: scale(1.35); letter-spacing: 0.45em; }
          32%  { opacity: 1; filter: blur(0px) brightness(1); transform: scale(1); letter-spacing: 0.12em; }
          62%  { opacity: 1; filter: blur(0px) brightness(1); transform: scale(1); letter-spacing: 0.12em; }
          78%  { opacity: 1; filter: blur(3px) brightness(1.5); transform: scale(1.08); letter-spacing: 0.22em; }
          100% { opacity: 0; filter: blur(45px) brightness(4); transform: scale(1.75); letter-spacing: 1.4em; }
        }
        /* ── Intro: psychedelic color cycling ── */
        @keyframes acid-spectral {
          0%   { color: #00ff41; text-shadow: 0 0 40px #00ff41, 0 0 80px rgba(0,255,65,0.4); }
          14%  { color: #00ffdd; text-shadow: 0 0 40px #00ffdd, 0 0 80px rgba(0,255,221,0.4); }
          28%  { color: #aa00ff; text-shadow: 0 0 40px #aa00ff, 0 0 80px rgba(170,0,255,0.4); }
          43%  { color: #ff5500; text-shadow: 0 0 40px #ff5500, 0 0 80px rgba(255,85,0,0.4); }
          57%  { color: #ffee00; text-shadow: 0 0 40px #ffee00, 0 0 80px rgba(255,238,0,0.4); }
          71%  { color: #ff0088; text-shadow: 0 0 40px #ff0088, 0 0 80px rgba(255,0,136,0.4); }
          85%  { color: #00aaff; text-shadow: 0 0 40px #00aaff, 0 0 80px rgba(0,170,255,0.4); }
          100% { color: #00ff41; text-shadow: 0 0 40px #00ff41, 0 0 80px rgba(0,255,65,0.4); }
        }
        .acid-intro-text {
          animation:
            acid-materialize 6.6s cubic-bezier(0.4, 0, 0.2, 1) forwards,
            acid-spectral 1.9s linear infinite;
          will-change: transform, opacity, filter;
        }
        .acid-cursor {
          display: inline-block;
          animation: blink 0.8s infinite;
          color: #00ff41;
          text-shadow: 0 0 5px #00ff41;
        }
        .acid-flicker {
          animation: flicker 8s infinite;
        }
        .acid-text {
          color: #00ff41;
          text-shadow: 0 0 5px #00ff41, 0 0 10px rgba(0,255,65,0.3);
        }
        .acid-dim {
          color: #00cc35;
          text-shadow: 0 0 3px rgba(0,204,53,0.2);
        }
        .acid-input {
          background: transparent;
          border: none;
          outline: none;
          color: #00ff41;
          text-shadow: 0 0 5px #00ff41, 0 0 10px rgba(0,255,65,0.3);
          caret-color: transparent;
          width: 100%;
          min-width: 0;
        }
        .acid-input::selection {
          background: rgba(0,255,65,0.2);
        }
      `}</style>

      {/* ── Root container ─────────────────────────────────────────── */}
      <div
        className={`${vt323.className} acid-flicker`}
        style={{
          position: 'fixed',
          inset: 0,
          background: '#010902',
          overflow: 'hidden',
          fontSize: 'clamp(15px, 4vw, 20px)',
          lineHeight: '1.4',
        }}
        onClick={() => inputRef.current?.focus()}
      >

        {/* ── CRT screen edge glow ──────────────────────────────── */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: '6px',
            boxShadow: 'inset 0 0 60px rgba(0,255,65,0.06), 0 0 30px rgba(0,255,65,0.08)',
            pointerEvents: 'none',
            zIndex: 10,
          }}
        />

        {/* ── Scanlines overlay ─────────────────────────────────── */}
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.10) 2px, rgba(0,0,0,0.10) 4px)',
            pointerEvents: 'none',
            zIndex: 20,
          }}
        />

        {/* ── Vignette overlay (lighter during animation for vivid edges) ── */}
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: phase === 'animating'
              ? 'radial-gradient(ellipse at center, transparent 60%, rgba(0,0,0,0.62) 100%)'
              : 'radial-gradient(ellipse at center, transparent 52%, rgba(0,0,0,0.82) 100%)',
            transition: 'background 1.2s ease',
            pointerEvents: 'none',
            zIndex: 21,
          }}
        />

        {/* ── Canvas (animation) ────────────────────────────────── */}
        <canvas
          ref={canvasRef}
          style={{
            position: 'absolute',
            inset: 0,
            opacity: canvasOpacity,
            transition: 'opacity 0.8s ease',
            zIndex: 1,
          }}
        />

        {/* ── Intro: ACID reveal ────────────────────────────────── */}
        {phase === 'intro' && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 8,
              pointerEvents: 'none',
            }}
          >
            <div
              className={`acid-intro-text ${vt323.className}`}
              style={{
                fontSize: 'min(20vw, 22vh)',
                letterSpacing: '0.12em',
                userSelect: 'none',
              }}
            >
              ACID
            </div>
          </div>
        )}

        {/* ── Terminal view ─────────────────────────────────────── */}
        {isTerminalVisible && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              padding: 'clamp(20px, 3vw, 40px) clamp(16px, 3.5vw, 48px)',
              overflowY: 'auto',
              overflowX: 'hidden',
              zIndex: 5,
            }}
          >
            {/* Boot lines */}
            {bootLines.map((line, i) => (
              <div key={i} className="acid-text" style={{ whiteSpace: 'pre' }}>
                {line || '\u00A0'}
              </div>
            ))}

            {/* Terminal output history */}
            {termOutput.map((line, i) => (
              <div key={`out-${i}`} className="acid-dim" style={{ whiteSpace: 'pre' }}>
                {line || '\u00A0'}
              </div>
            ))}

            {/* Input line */}
            {showPrompt && (
              <div style={{ display: 'flex', alignItems: 'baseline', marginTop: '4px' }}>
                <span className="acid-text" style={{ whiteSpace: 'nowrap', userSelect: 'none', flexShrink: 0 }}>
                  /acid{'\u00A0'}
                </span>
                <input
                  ref={inputRef}
                  className={`acid-input ${vt323.className}`}
                  style={{ fontSize: 'clamp(15px, 4vw, 20px)', lineHeight: '1.4' }}
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  autoComplete="off"
                  autoCorrect="off"
                  autoCapitalize="off"
                  spellCheck={false}
                  aria-label="terminal input"
                />
                {input === '' && (
                  <span className="acid-cursor" aria-hidden="true">_</span>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── Reflection screen ─────────────────────────────────── */}
        {(phase === 'reflecting' || phase === 'fading') && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 5,
              opacity: reflectionVisible ? 1 : 0,
              transition: 'opacity 0.6s ease',
            }}
          >
            <p
              className="acid-text"
              style={{
                fontSize: 'clamp(16px, 3.5vw, 24px)',
                letterSpacing: '0.06em',
                textAlign: 'center',
                maxWidth: 'min(600px, 85vw)',
                padding: '0 clamp(20px, 5vw, 48px)',
                lineHeight: '1.7',
              }}
            >
              {reflection}
            </p>
          </div>
        )}
      </div>
    </>
  )
}
