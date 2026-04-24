'use client'

import { useState, useRef, useEffect, useCallback, memo } from 'react'
import { VT323, Cormorant_Garamond } from 'next/font/google'
import { ARCHETYPES, ARCHETYPE_MAP, type Archetype, type GridState } from './archetypes'
import { ARCHETYPE_META_MAP, FAMILY_ORDER, FAMILY_LABEL } from './archetype-meta'

const getUrlFormula = (): string | null => {
  if (typeof window === 'undefined') return null
  const h = window.location.hash.replace('#', '')
  return h && ARCHETYPE_MAP[h] ? h : null
}

// Pre-computed family groups: each family with its archetypes (preserving original idx)
const FAMILY_GROUPS = FAMILY_ORDER.map(family => ({
  family,
  items: ARCHETYPES
    .map((arch, idx) => ({ arch, idx, meta: ARCHETYPE_META_MAP[arch.name] }))
    .filter(x => x.meta?.family === family),
}))

// ─── CardPreview ────────────────────────────────────────────────────────────
// Tiny live preview that plays the archetype inside a gallery card.
// IntersectionObserver pauses it when the card is off-screen.
// Falls back to static gradient for grid-based archetypes (too expensive for previews).
interface CardPreviewProps { archetype: Archetype; accent: string }
const CardPreview = memo(function CardPreview({ archetype }: CardPreviewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animRef = useRef<number>(0)
  const tRef = useRef<number>(Math.random() * 8) // stagger so not all cards sync
  const lastFrameRef = useRef<number>(0)
  const visibleRef = useRef<boolean>(false)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !archetype.pixel) return
    const obs = new IntersectionObserver(
      entries => { for (const e of entries) visibleRef.current = e.isIntersecting },
      { threshold: 0.05 }
    )
    obs.observe(canvas)
    return () => obs.disconnect()
  }, [archetype])

  useEffect(() => {
    if (!archetype.pixel) return
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const cellW = 4, cellH = 4
    const W = canvas.width, H = canvas.height
    const cols = Math.floor(W / cellW)
    const rows = Math.floor(H / cellH)
    const loop = (now: number) => {
      if (!visibleRef.current) {
        animRef.current = requestAnimationFrame(loop)
        return
      }
      // ~10fps
      if (now - lastFrameRef.current < 100) {
        animRef.current = requestAnimationFrame(loop)
        return
      }
      lastFrameRef.current = now
      const pixelFn = archetype.pixel
      if (!pixelFn) return
      const paletteFn = archetype.palette
      for (let row = 0; row < rows; row++) {
        for (let col = 0; col < cols; col++) {
          const nx = (col - cols * 0.5) / (cols * 0.25)
          const ny = (row - rows * 0.5) / (rows * 0.25) * 0.55 * 2.0
          const v = Math.max(0, Math.min(1, pixelFn(nx, ny, tRef.current)))
          const [r, g, b] = paletteFn(v, tRef.current)
          ctx.fillStyle = `rgb(${r},${g},${b})`
          ctx.fillRect(col * cellW, row * cellH, cellW, cellH)
        }
      }
      tRef.current += archetype.tStep * 2.2 // a bit faster than full speed so preview stays lively
      animRef.current = requestAnimationFrame(loop)
    }
    animRef.current = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(animRef.current)
  }, [archetype])

  // Grid-based archetypes: no preview (performance + complexity). Just render nothing;
  // card gradient shows through.
  if (!archetype.pixel) return null

  return (
    <canvas
      ref={canvasRef}
      width={96}
      height={144}
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        mixBlendMode: 'screen',
        opacity: 0.75,
        pointerEvents: 'none',
      }}
    />
  )
})

const vt323 = VT323({ weight: '400', subsets: ['latin'] })
const cormorant = Cormorant_Garamond({
  weight: ['300', '400', '500'],
  style: ['normal', 'italic'],
  subsets: ['latin'],
  display: 'swap',
})

const GRADIENT = " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"

type Phase = 'intro' | 'gallery' | 'animating' | 'about'

// ─── Icons ────────────────────────────────────────────────────────────────────
const GridIcon = () => (
  <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
    <rect x="1" y="1" width="6.5" height="6.5" rx="1.5" fill="currentColor" />
    <rect x="10.5" y="1" width="6.5" height="6.5" rx="1.5" fill="currentColor" />
    <rect x="1" y="10.5" width="6.5" height="6.5" rx="1.5" fill="currentColor" />
    <rect x="10.5" y="10.5" width="6.5" height="6.5" rx="1.5" fill="currentColor" />
  </svg>
)
const PlayIcon = ({ active }: { active: boolean }) => (
  <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
    <circle cx="11" cy="11" r="9" stroke="currentColor" strokeWidth="1.5" opacity={active ? 1 : 0.5} />
    {active && <circle cx="11" cy="11" r="3.5" fill="currentColor" />}
    {!active && <circle cx="11" cy="11" r="3" fill="currentColor" opacity="0.5" />}
  </svg>
)
const InfoIcon = () => (
  <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
    <circle cx="9" cy="9" r="7.5" stroke="currentColor" strokeWidth="1.5" />
    <line x1="9" y1="8.5" x2="9" y2="13.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    <circle cx="9" cy="5.5" r="1.2" fill="currentColor" />
  </svg>
)

// ─── Component ────────────────────────────────────────────────────────────────

export default function AcidGalleryPage() {
  const [phase, setPhase] = useState<Phase>('intro')
  const [activeIdx, setActiveIdx] = useState<number | null>(null)
  const [isPlaying, setIsPlaying] = useState(true)
  const [canvasVisible, setCanvasVisible] = useState(false)
  const [reflectionText, setReflectionText] = useState('')
  const [reflectionVisible, setReflectionVisible] = useState(false)
  const [pressedIdx, setPressedIdx] = useState<number | null>(null)
  const [navControls, setNavControls] = useState(true) // show canvas controls
  const [shuffleOn, setShuffleOn] = useState(false)
  const [shareToast, setShareToast] = useState(false)
  const shuffleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Animation engine refs
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animFrameRef = useRef<number>(0)
  const lastFrameTimeRef = useRef<number>(0)
  const frameCountRef = useRef<number>(0)
  const gridStateRef = useRef<GridState | null>(null)
  const currentArchRef = useRef<Archetype | null>(null)
  const tRef = useRef<number>(0)
  const isPlayingRef = useRef(true)
  const dPRRef = useRef(1)

  // Touch gesture refs
  const touchStartX = useRef(0)
  const touchStartY = useRef(0)
  const touchStartTime = useRef(0)

  // Carousel ref for scroll-to-active
  const carouselRef = useRef<HTMLDivElement>(null)

  // Nav hide timer
  const navTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // History / URL sync — tracks whether a phase change came from the browser
  // (popstate), so we don't double-push when reacting to it.
  const fromPopStateRef = useRef(false)
  const activeIdxRef = useRef<number | null>(null)
  useEffect(() => { activeIdxRef.current = activeIdx }, [activeIdx])

  // ─── Canvas resize ──────────────────────────────────────────────────────────
  const resizeCanvas = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const dPR = window.devicePixelRatio || 1
    dPRRef.current = dPR
    canvas.width = Math.floor(window.innerWidth * dPR)
    canvas.height = Math.floor(window.innerHeight * dPR)
    canvas.style.width = window.innerWidth + 'px'
    canvas.style.height = window.innerHeight + 'px'
  }, [])

  useEffect(() => {
    resizeCanvas()
    window.addEventListener('resize', resizeCanvas)
    return () => window.removeEventListener('resize', resizeCanvas)
  }, [resizeCanvas])

  // ─── Intro timer ────────────────────────────────────────────────────────────
  useEffect(() => {
    if (phase !== 'intro') return
    // If the user deep-linked to /lab/acid#<formula>, skip the intro and jump in.
    const deepLink = getUrlFormula()
    if (deepLink) {
      const idx = ARCHETYPES.findIndex(a => a.name === deepLink)
      if (idx >= 0) {
        setPhase('gallery')
        setTimeout(() => { startAnimation(ARCHETYPES[idx], idx) }, 30)
        return
      }
    }
    const t = setTimeout(() => setPhase('gallery'), 3100)
    return () => clearTimeout(t)
  }, [phase]) // eslint-disable-line react-hooks/exhaustive-deps

  // ─── History sync — push state per formula, handle browser back ──────────
  useEffect(() => {
    // When we enter animation (not as result of a popstate), push a new history entry
    if (phase === 'animating' && activeIdx !== null) {
      const name = ARCHETYPES[activeIdx].name
      const target = `#${name}`
      if (!fromPopStateRef.current && window.location.hash !== target) {
        window.history.pushState({ acid: name }, '', target)
      }
    }
    // When we return to gallery from animation (not via popstate), clear the hash
    if (phase === 'gallery' && !fromPopStateRef.current && window.location.hash) {
      window.history.replaceState(null, '', window.location.pathname + window.location.search)
    }
    fromPopStateRef.current = false
  }, [phase, activeIdx])

  useEffect(() => {
    const onPop = () => {
      fromPopStateRef.current = true
      const name = getUrlFormula()
      if (name) {
        const idx = ARCHETYPES.findIndex(a => a.name === name)
        if (idx >= 0 && idx !== activeIdxRef.current) {
          startAnimation(ARCHETYPES[idx], idx)
        }
      } else {
        // No hash = back to gallery
        if (currentArchRef.current) stopAnimation()
      }
    }
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Scroll grid to active card row ──────────────────────────────────────────
  useEffect(() => {
    if (phase === 'gallery' && activeIdx !== null && carouselRef.current) {
      const row = Math.floor(activeIdx / 5)
      const cardH = 102 + 7 // approx card height + gap
      carouselRef.current.scrollTo({ top: Math.max(0, row * cardH - 20), behavior: 'smooth' })
    }
  }, [phase, activeIdx])

  // ─── Keyboard shortcuts ────────────────────────────────────────────────────
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (reflectionVisible) { setReflectionVisible(false); return }
        if (phase === 'animating') stopAnimation()
        if (phase === 'about') setPhase('gallery')
        return
      }
      if (phase !== 'animating') return
      if (e.key === 'ArrowLeft') { e.preventDefault(); goToPrev() }
      else if (e.key === 'ArrowRight') { e.preventDefault(); goToNext() }
      else if (e.key === ' ') { e.preventDefault(); togglePlayPause() }
      else if (e.key === 'ArrowUp') { e.preventDefault(); showReflection() }
      else if (e.key === 'i' || e.key === 'I') { setPhase('about') }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [phase, reflectionVisible]) // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Animation engine ───────────────────────────────────────────────────────
  const stopAnimation = useCallback(() => {
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current)
      animFrameRef.current = 0
    }
    currentArchRef.current = null
    setCanvasVisible(false)
    setReflectionVisible(false)
    setPhase('gallery')
  }, [])

  const startAnimation = useCallback((arch: Archetype, idx: number) => {
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current)
      animFrameRef.current = 0
    }

    currentArchRef.current = arch
    tRef.current = 0
    frameCountRef.current = 0
    isPlayingRef.current = true
    setIsPlaying(true)
    setActiveIdx(idx)

    resizeCanvas()

    document.fonts.ready.then(() => {
      const canvas = canvasRef.current
      if (!canvas || currentArchRef.current !== arch) return

      const dPR = dPRRef.current
      const logW = Math.floor(canvas.width / dPR)
      const logH = Math.floor(canvas.height / dPR)
      const charW = 9, charH = 15
      const cCols = Math.floor(logW / charW)
      const cRows = Math.floor(logH / charH)

      if (arch.init) gridStateRef.current = arch.init(cCols, cRows)
      else gridStateRef.current = null

      setCanvasVisible(true)
      setPhase('animating')

      const loop = (now: number) => {
        if (!currentArchRef.current || currentArchRef.current !== arch) return

        if (!isPlayingRef.current) {
          animFrameRef.current = requestAnimationFrame(loop)
          return
        }

        if (now - lastFrameTimeRef.current < 40) {
          animFrameRef.current = requestAnimationFrame(loop)
          return
        }
        lastFrameTimeRef.current = now

        const c = canvasRef.current
        if (!c) return
        const ctx = c.getContext('2d')
        if (!ctx) return

        const cw = Math.floor(c.width / dPRRef.current)
        const ch = Math.floor(c.height / dPRRef.current)
        const cols = Math.floor(cw / charW)
        const rows = Math.floor(ch / charH)

        if (arch.update && gridStateRef.current) {
          arch.update(gridStateRef.current, tRef.current, frameCountRef.current, cols, rows)
        }

        ctx.setTransform(dPRRef.current, 0, 0, dPRRef.current, 0, 0)
        ctx.fillStyle = '#000'
        ctx.fillRect(0, 0, cw, ch)
        ctx.font = `15px 'VT323', monospace`
        ctx.textBaseline = 'top'

        for (let row = 0; row < rows; row++) {
          for (let col = 0; col < cols; col++) {
            const nx = (col - cols * 0.5) / (cols * 0.25)
            const ny = (row - rows * 0.5) / (rows * 0.25) * 0.55 * 2.0

            let val: number
            if (arch.gridPixel && gridStateRef.current) {
              val = arch.gridPixel(gridStateRef.current, col, row)
            } else if (arch.pixel) {
              val = arch.pixel(nx, ny, tRef.current)
            } else {
              val = 0
            }

            val = Math.max(0, Math.min(1, val))
            const [r, g, b] = arch.palette(val, tRef.current)
            const ci = Math.floor(val * 69)
            const char = GRADIENT[ci] ?? ' '

            ctx.fillStyle = `rgb(${r},${g},${b})`
            ctx.fillText(char, col * charW, row * charH)
          }
        }

        tRef.current += arch.tStep
        frameCountRef.current++
        animFrameRef.current = requestAnimationFrame(loop)
      }

      animFrameRef.current = requestAnimationFrame(loop)
    })
  }, [resizeCanvas])

  const togglePlayPause = useCallback(() => {
    isPlayingRef.current = !isPlayingRef.current
    setIsPlaying(isPlayingRef.current)
  }, [])

  const goToPrev = useCallback(() => {
    if (activeIdx === null) return
    const nextIdx = (activeIdx - 1 + ARCHETYPES.length) % ARCHETYPES.length
    startAnimation(ARCHETYPES[nextIdx], nextIdx)
  }, [activeIdx, startAnimation])

  const goToNext = useCallback(() => {
    if (activeIdx === null) return
    const nextIdx = (activeIdx + 1) % ARCHETYPES.length
    startAnimation(ARCHETYPES[nextIdx], nextIdx)
  }, [activeIdx, startAnimation])

  const goToRandom = useCallback(() => {
    const idx = Math.floor(Math.random() * ARCHETYPES.length)
    startAnimation(ARCHETYPES[idx], idx)
  }, [startAnimation])

  const toggleShuffle = useCallback(() => {
    setShuffleOn(prev => {
      const next = !prev
      if (!next && shuffleTimerRef.current) {
        clearInterval(shuffleTimerRef.current)
        shuffleTimerRef.current = null
      }
      if (next && phase !== 'animating') goToRandom()
      return next
    })
  }, [phase, goToRandom])

  const copyShareLink = useCallback(async () => {
    if (activeIdx === null) return
    const name = ARCHETYPES[activeIdx].name
    const url = `${window.location.origin}${window.location.pathname}#${name}`
    try {
      await navigator.clipboard.writeText(url)
      setShareToast(true)
      setTimeout(() => setShareToast(false), 1500)
    } catch {
      // fallback — prompt the URL so user can copy manually
      window.prompt('Copy this link:', url)
    }
  }, [activeIdx])

  // Shuffle auto-advance — every 20s, jump to a new random formula while on.
  useEffect(() => {
    if (shuffleTimerRef.current) { clearInterval(shuffleTimerRef.current); shuffleTimerRef.current = null }
    if (!shuffleOn) return
    shuffleTimerRef.current = setInterval(() => {
      const current = activeIdxRef.current
      let idx = Math.floor(Math.random() * ARCHETYPES.length)
      if (idx === current) idx = (idx + 1) % ARCHETYPES.length
      startAnimation(ARCHETYPES[idx], idx)
    }, 20000)
    return () => { if (shuffleTimerRef.current) clearInterval(shuffleTimerRef.current) }
  }, [shuffleOn, startAnimation])

  const showReflection = useCallback(() => {
    if (!currentArchRef.current) return
    setReflectionText(currentArchRef.current.reflection)
    setReflectionVisible(true)
    setTimeout(() => setReflectionVisible(false), 3500)
  }, [])

  // Show nav controls briefly on touch
  const flashNavControls = useCallback(() => {
    setNavControls(true)
    if (navTimerRef.current) clearTimeout(navTimerRef.current)
    navTimerRef.current = setTimeout(() => setNavControls(false), 3000)
  }, [])

  // ─── Touch gesture handling (on canvas during animation) ─────────────────
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX
    touchStartY.current = e.touches[0].clientY
    touchStartTime.current = Date.now()
    flashNavControls()
  }, [flashNavControls])

  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    const dx = e.changedTouches[0].clientX - touchStartX.current
    const dy = e.changedTouches[0].clientY - touchStartY.current
    const dt = Date.now() - touchStartTime.current
    const absDx = Math.abs(dx), absDy = Math.abs(dy)
    const vx = absDx / dt, vy = absDy / dt

    const SWIPE_MIN = 50
    const VELOCITY_MIN = 0.25

    if (reflectionVisible) {
      setReflectionVisible(false)
      return
    }

    if (absDy > SWIPE_MIN && vy > VELOCITY_MIN && absDy > absDx && dy < 0) {
      // Swipe up → show reflection
      showReflection()
    } else if (absDx > SWIPE_MIN && vx > VELOCITY_MIN && absDx > absDy) {
      // Horizontal swipe → prev / next
      if (dx > 0) goToPrev()
      else goToNext()
    } else if (absDx < 12 && absDy < 12 && dt < 250) {
      // Tap → toggle play/pause
      togglePlayPause()
    }
  }, [reflectionVisible, showReflection, goToPrev, goToNext, togglePlayPause])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
      if (navTimerRef.current) clearTimeout(navTimerRef.current)
    }
  }, [])

  const isGallery = phase === 'gallery'
  const isAnimating = phase === 'animating'
  const isAbout = phase === 'about'
  const isIntro = phase === 'intro'

  return (
    <>
      <style>{`
        @keyframes word-slam {
          0%   { opacity: 0; transform: translateX(-32px) skewX(-5deg); filter: blur(4px); }
          14%  { opacity: 1; transform: translateX(0) skewX(0); filter: blur(0); }
          72%  { opacity: 1; transform: translateX(0); filter: blur(0); }
          90%  { opacity: 0.4; filter: blur(2px); }
          100% { opacity: 0; filter: blur(8px); transform: translateX(6px); }
        }
        @keyframes letter-flare {
          0%, 100% { text-shadow: 0 0 24px currentColor, 0 0 48px currentColor; }
          50%       { text-shadow: 0 0 48px currentColor, 0 0 96px currentColor, 0 0 140px currentColor; }
        }
        @keyframes pulse-ring {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.15); opacity: 0.7; }
        }
        .pulse { animation: pulse-ring 2s ease-in-out infinite; }
        @keyframes fade-up {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .fade-up { animation: fade-up 0.6s ease forwards; }
        ::-webkit-scrollbar { display: none; }
        * { -webkit-tap-highlight-color: transparent; }
        .card-tap { transition: transform 0.15s ease, box-shadow 0.15s ease; }
        .card-tap:active { transform: scale(0.96) !important; }
      `}</style>

      {/* ── Root ──────────────────────────────────────────────────────── */}
      <div
        className={vt323.className}
        style={{
          position: 'fixed',
          inset: 0,
          background: '#080808',
          overflow: 'hidden',
          userSelect: 'none',
          WebkitUserSelect: 'none',
        }}
      >
        {/* ── Scanlines ──────────────────────────────────────────────── */}
        <div style={{
          position: 'fixed', inset: 0, zIndex: 100, pointerEvents: 'none',
          backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.08) 2px, rgba(0,0,0,0.08) 4px)',
        }} />

        {/* ── Canvas (always in DOM) ──────────────────────────────────── */}
        <canvas
          ref={canvasRef}
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
          onMouseMove={() => { if (isAnimating) flashNavControls() }}
          onWheel={e => {
            if (!isAnimating) return
            if (Math.abs(e.deltaX) < 20) return
            if (e.deltaX > 0) goToNext()
            else goToPrev()
          }}
          style={{
            position: 'fixed', inset: 0, zIndex: 10,
            opacity: canvasVisible ? 1 : 0,
            filter: reflectionVisible ? 'brightness(0.25)' : 'brightness(1)',
            transition: 'opacity 0.5s ease, filter 0.4s ease',
          }}
        />

        {/* ── INTRO ──────────────────────────────────────────────────── */}
        {isIntro && (
          <div style={{
            position: 'fixed', inset: 0, zIndex: 50,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: '0 28px',
          }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {([
                { letter: 'A', rest: 'LGORITHMIC', color: '#00ff41', delay: '0s' },
                { letter: 'C', rest: 'REATIVE',    color: '#00e5ff', delay: '0.12s' },
                { letter: 'I', rest: 'NTELLIGENCE',color: '#bf5aff', delay: '0.24s' },
                { letter: 'D', rest: 'ISPLAY',     color: '#ff9500', delay: '0.36s' },
              ] as const).map(({ letter, rest, color, delay }) => (
                <div
                  key={letter}
                  className={vt323.className}
                  style={{
                    display: 'flex',
                    alignItems: 'baseline',
                    gap: 4,
                    animation: `word-slam 2.8s ${delay} cubic-bezier(0.16,1,0.3,1) both`,
                  }}
                >
                  <span style={{
                    fontSize: 76,
                    lineHeight: 0.9,
                    color,
                    animation: `letter-flare 1.4s ${delay} ease-in-out infinite`,
                  }}>{letter}</span>
                  <span style={{
                    fontSize: 26,
                    letterSpacing: '0.12em',
                    color: 'rgba(255,255,255,0.38)',
                  }}>{rest}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── GALLERY ────────────────────────────────────────────────── */}
        <div style={{
          position: 'fixed', inset: 0, zIndex: 20,
          background: '#080808',
          opacity: isGallery ? 1 : 0,
          pointerEvents: isGallery ? 'auto' : 'none',
          transition: 'opacity 0.7s ease',
          display: 'flex', flexDirection: 'column',
        }}>
          {/* Gallery Header */}
          <div style={{
            padding: '48px 16px 12px',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <div style={{
              fontFamily: vt323.style.fontFamily,
              fontSize: 20, letterSpacing: '0.18em',
              color: '#00ff41',
              textShadow: '0 0 8px rgba(0,255,65,0.35)',
            }}>
              ACID
            </div>
            <button
              onClick={toggleShuffle}
              aria-label="Toggle shuffle"
              style={{
                background: shuffleOn ? 'rgba(0,255,65,0.15)' : 'transparent',
                border: `1px solid ${shuffleOn ? '#00ff41' : 'rgba(255,255,255,0.15)'}`,
                borderRadius: 999,
                padding: '6px 14px',
                cursor: 'pointer',
                fontFamily: vt323.style.fontFamily,
                fontSize: 12, letterSpacing: '0.18em',
                color: shuffleOn ? '#00ff41' : 'rgba(255,255,255,0.55)',
                display: 'flex', alignItems: 'center', gap: 6,
                transition: 'all 0.2s ease',
              }}
            >
              <span aria-hidden="true">⇌</span>
              SHUFFLE
            </button>
          </div>

          {/* Grid — grouped by family */}
          <div
            ref={carouselRef}
            style={{
              flex: 1,
              overflowY: 'auto',
              overflowX: 'hidden',
              padding: '4px 12px 96px',
              scrollbarWidth: 'none',
            } as React.CSSProperties}
          >
            {FAMILY_GROUPS.map(({ family, items }) => (
              <div key={family} data-family={family} style={{ marginBottom: 24 }}>
                <div style={{
                  padding: '14px 4px 10px',
                  display: 'flex', alignItems: 'center', gap: 10,
                }}>
                  <div style={{
                    fontFamily: vt323.style.fontFamily,
                    fontSize: 10,
                    letterSpacing: '0.35em',
                    color: 'rgba(255,255,255,0.38)',
                  }}>
                    {FAMILY_LABEL[family]}
                  </div>
                  <div style={{
                    flex: 1, height: 1,
                    background: 'linear-gradient(to right, rgba(255,255,255,0.1), transparent)',
                  }} />
                </div>
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(5, 1fr)',
                  gap: 7,
                }}>
                  {items.map(({ arch, idx, meta }) => {
                    if (!meta) return null
                    const isActive = activeIdx === idx
                    return (
                      <div
                        key={arch.name}
                        className="card-tap"
                        onClick={() => startAnimation(arch, idx)}
                        onTouchStart={() => setPressedIdx(idx)}
                        onTouchEnd={() => setPressedIdx(null)}
                        style={{
                          aspectRatio: '2/3',
                          borderRadius: 10,
                          overflow: 'hidden',
                          position: 'relative',
                          cursor: 'pointer',
                          border: isActive
                            ? `1.5px solid ${meta.accent}`
                            : '1px solid rgba(255,255,255,0.09)',
                          boxShadow: isActive
                            ? `0 0 16px ${meta.accent}55, inset 0 0 12px ${meta.accent}22`
                            : '0 2px 12px rgba(0,0,0,0.55)',
                          transform: pressedIdx === idx ? 'scale(0.93)' : 'scale(1)',
                          background: meta.gradient,
                          transition: 'transform 0.12s ease, box-shadow 0.2s ease, border-color 0.2s ease',
                        }}
                      >
                        {/* Live preview (pixel-based only) */}
                        <CardPreview archetype={arch} accent={meta.accent} />

                        {/* Inner light — top highlight */}
                        <div style={{
                          position: 'absolute', inset: 0,
                          background: 'radial-gradient(ellipse at 50% 20%, rgba(255,255,255,0.14) 0%, transparent 65%)',
                          pointerEvents: 'none',
                        }} />

                        {/* Active glow pulse */}
                        {isActive && (
                          <div style={{
                            position: 'absolute', inset: 0,
                            background: `radial-gradient(ellipse at 50% 50%, ${meta.accent}1a 0%, transparent 70%)`,
                            pointerEvents: 'none',
                          }} />
                        )}

                        {/* Bottom gradient for text */}
                        <div style={{
                          position: 'absolute', bottom: 0, left: 0, right: 0,
                          height: '60%',
                          background: 'linear-gradient(to bottom, transparent 0%, rgba(0,0,0,0.88) 100%)',
                          pointerEvents: 'none',
                        }} />

                        {/* Card number */}
                        <span style={{
                          position: 'absolute', top: 6, right: 7,
                          fontFamily: vt323.style.fontFamily, fontSize: 9,
                          color: 'rgba(255,255,255,0.25)', letterSpacing: '0.04em',
                        }}>
                          {String(idx + 1).padStart(2, '0')}
                        </span>

                        {/* Now playing dot */}
                        {isActive && (
                          <span style={{
                            position: 'absolute', top: 7, left: 7,
                            width: 5, height: 5, borderRadius: '50%',
                            background: meta.accent,
                            boxShadow: `0 0 6px ${meta.accent}`,
                            display: 'block',
                          }} />
                        )}

                        {/* Name */}
                        <div style={{
                          position: 'absolute', bottom: 0, left: 0, right: 0,
                          padding: '0 6px 6px',
                          pointerEvents: 'none',
                        }}>
                          <div style={{
                            fontFamily: vt323.style.fontFamily,
                            fontSize: 13, letterSpacing: '0.05em',
                            color: isActive ? meta.accent : '#ffffff',
                            lineHeight: 1,
                            textShadow: isActive ? `0 0 8px ${meta.accent}` : '0 1px 4px rgba(0,0,0,0.8)',
                            transition: 'color 0.2s ease',
                            overflow: 'hidden',
                            whiteSpace: 'nowrap',
                            textOverflow: 'ellipsis',
                          }}>
                            {arch.name}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>

          {/* Scroll minimap — right side, shows family positions */}
          <div style={{
            position: 'fixed', right: 8, top: '50%', transform: 'translateY(-50%)',
            zIndex: 22,
            display: 'flex', flexDirection: 'column', gap: 6,
            pointerEvents: 'auto',
          }}>
            {FAMILY_GROUPS.map(({ family }) => {
              const hasActive = activeIdx !== null && FAMILY_GROUPS
                .find(g => g.family === family)?.items.some(x => x.idx === activeIdx)
              return (
                <button
                  key={family}
                  onClick={() => {
                    const root = carouselRef.current
                    if (!root) return
                    const el = root.querySelector(`[data-family="${family}"]`) as HTMLElement | null
                    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
                  }}
                  aria-label={`Jump to ${FAMILY_LABEL[family]}`}
                  style={{
                    width: 6, height: 24,
                    borderRadius: 3, border: 'none',
                    background: hasActive ? '#00ff41' : 'rgba(255,255,255,0.2)',
                    cursor: 'pointer',
                    padding: 0,
                    boxShadow: hasActive ? '0 0 8px rgba(0,255,65,0.6)' : 'none',
                    transition: 'background 0.2s, box-shadow 0.2s',
                  }}
                />
              )
            })}
          </div>

          {/* Now Playing sticky card — shows the last-played formula when in gallery */}
          {activeIdx !== null && (() => {
            const arch = ARCHETYPES[activeIdx]
            const meta = ARCHETYPE_META_MAP[arch.name]
            if (!meta) return null
            return (
              <div
                onClick={() => startAnimation(arch, activeIdx)}
                style={{
                  position: 'fixed', left: 16, right: 16, bottom: 68,
                  zIndex: 21, pointerEvents: 'auto',
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '10px 14px',
                  background: 'rgba(8,8,8,0.92)',
                  border: `1px solid ${meta.accent}`,
                  borderRadius: 12,
                  cursor: 'pointer',
                  backdropFilter: 'blur(12px)',
                  WebkitBackdropFilter: 'blur(12px)',
                  maxWidth: 480, margin: '0 auto',
                  boxShadow: `0 8px 32px rgba(0,0,0,0.6), 0 0 16px ${meta.accent}33`,
                }}
              >
                <div style={{
                  width: 40, height: 56, borderRadius: 6,
                  background: meta.gradient,
                  flexShrink: 0,
                }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontFamily: vt323.style.fontFamily, fontSize: 9,
                    letterSpacing: '0.2em', color: 'rgba(255,255,255,0.4)',
                  }}>
                    LAST PLAYED
                  </div>
                  <div style={{
                    fontFamily: vt323.style.fontFamily, fontSize: 16,
                    color: meta.accent, letterSpacing: '0.06em',
                    textShadow: `0 0 8px ${meta.accent}88`,
                    marginTop: 2,
                  }}>
                    {arch.name}
                  </div>
                </div>
                <div style={{
                  fontFamily: vt323.style.fontFamily, fontSize: 12,
                  letterSpacing: '0.14em', color: '#00ff41',
                  flexShrink: 0,
                }}>
                  ▶ RESUME
                </div>
              </div>
            )
          })()}
        </div>

        {/* ── ANIMATION OVERLAYS ────────────────────────────────────── */}
        {isAnimating && (
          <>
            {/* Desktop prev/next arrow buttons (fade in on hover via CSS) */}
            <button
              onClick={goToPrev}
              aria-label="Previous formula"
              style={{
                position: 'fixed', left: 16, top: '50%', transform: 'translateY(-50%)',
                zIndex: 35,
                width: 48, height: 48, borderRadius: '50%',
                background: 'rgba(0,0,0,0.4)',
                border: '1px solid rgba(255,255,255,0.18)',
                color: 'rgba(255,255,255,0.75)',
                fontFamily: vt323.style.fontFamily, fontSize: 28, lineHeight: 1,
                cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                opacity: navControls ? 0.8 : 0,
                transition: 'opacity 0.3s ease, background 0.2s ease',
                backdropFilter: 'blur(8px)',
                WebkitBackdropFilter: 'blur(8px)',
              }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'rgba(0,255,65,0.18)' }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'rgba(0,0,0,0.4)' }}
            >
              ‹
            </button>
            <button
              onClick={goToNext}
              aria-label="Next formula"
              style={{
                position: 'fixed', right: 16, top: '50%', transform: 'translateY(-50%)',
                zIndex: 35,
                width: 48, height: 48, borderRadius: '50%',
                background: 'rgba(0,0,0,0.4)',
                border: '1px solid rgba(255,255,255,0.18)',
                color: 'rgba(255,255,255,0.75)',
                fontFamily: vt323.style.fontFamily, fontSize: 28, lineHeight: 1,
                cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                opacity: navControls ? 0.8 : 0,
                transition: 'opacity 0.3s ease, background 0.2s ease',
                backdropFilter: 'blur(8px)',
                WebkitBackdropFilter: 'blur(8px)',
              }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'rgba(0,255,65,0.18)' }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'rgba(0,0,0,0.4)' }}
            >
              ›
            </button>

            {/* Archetype name (top left) — persistent at 50% opacity */}
            <div style={{
              position: 'fixed', top: 'env(safe-area-inset-top, 0px)',
              left: 0, right: 0,
              padding: '18px 20px 0',
              zIndex: 30, pointerEvents: 'none',
              opacity: navControls ? 1 : 0.5,
              transition: 'opacity 0.4s ease',
              display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
            }}>
              <div>
                <div style={{
                  fontFamily: vt323.style.fontFamily,
                  fontSize: 15, letterSpacing: '0.12em',
                  color: 'rgba(0,255,65,0.5)',
                }}>
                  {activeIdx !== null ? ARCHETYPES[activeIdx]?.name : ''}
                </div>
                <div className={cormorant.className} style={{
                  fontSize: 11, fontStyle: 'italic',
                  color: 'rgba(255,255,255,0.25)', marginTop: 2,
                }}>
                  {activeIdx !== null ? ARCHETYPE_META_MAP[ARCHETYPES[activeIdx]?.name]?.vibe : ''}
                </div>
              </div>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 12,
                marginTop: 3, pointerEvents: 'auto',
              }}>
                <button
                  onClick={copyShareLink}
                  aria-label="Copy share link"
                  style={{
                    background: 'transparent',
                    border: '1px solid rgba(255,255,255,0.18)',
                    borderRadius: 999,
                    padding: '4px 10px',
                    cursor: 'pointer',
                    fontFamily: vt323.style.fontFamily,
                    fontSize: 11, letterSpacing: '0.14em',
                    color: 'rgba(255,255,255,0.6)',
                    display: 'flex', alignItems: 'center', gap: 5,
                    transition: 'all 0.2s ease',
                  }}
                  onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = '#00ff41' }}
                  onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = 'rgba(255,255,255,0.6)' }}
                >
                  <span aria-hidden="true">⇌</span>
                  SHARE
                </button>
                <div style={{
                  fontFamily: vt323.style.fontFamily,
                  fontSize: 11, color: 'rgba(255,255,255,0.2)',
                  letterSpacing: '0.1em',
                }}>
                  {activeIdx !== null ? `${activeIdx + 1} / ${ARCHETYPES.length}` : ''}
                </div>
              </div>
            </div>

            {/* Share toast */}
            {shareToast && (
              <div style={{
                position: 'fixed', top: 80, left: '50%', transform: 'translateX(-50%)',
                zIndex: 60, pointerEvents: 'none',
                background: 'rgba(0,255,65,0.95)',
                color: '#000',
                padding: '8px 16px',
                borderRadius: 999,
                fontFamily: vt323.style.fontFamily, fontSize: 13,
                letterSpacing: '0.14em',
                boxShadow: '0 4px 24px rgba(0,255,65,0.5)',
              }}>
                LINK COPIED
              </div>
            )}

            {/* Hint text (bottom, above nav) — responsive desktop vs mobile */}
            <div style={{
              position: 'fixed', bottom: 80, left: 0, right: 0,
              display: 'flex', justifyContent: 'center',
              zIndex: 30, pointerEvents: 'none',
              opacity: navControls ? 0.55 : 0.18,
              transition: 'opacity 0.4s ease',
            }}>
              <div className={cormorant.className} style={{
                fontSize: 11, fontStyle: 'italic',
                color: 'rgba(255,255,255,0.55)',
                letterSpacing: '0.08em',
                textAlign: 'center',
                padding: '0 16px',
              }}>
                {isPlaying
                  ? '← → cycle  ·  ↑ meaning  ·  space pause  ·  esc back'
                  : '⏸ paused  ·  tap or space to resume'}
              </div>
            </div>
          </>
        )}

        {/* ── REFLECTION OVERLAY ────────────────────────────────────── */}
        {isAnimating && (
          <div
            onClick={() => setReflectionVisible(false)}
            style={{
              position: 'fixed', inset: 0, zIndex: 40,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              padding: '0 clamp(24px, 8vw, 64px)',
              pointerEvents: reflectionVisible ? 'auto' : 'none',
              opacity: reflectionVisible ? 1 : 0,
              transition: 'opacity 0.5s ease',
            }}
          >
            <p className={`${cormorant.className} fade-up`} style={{
              fontSize: 'clamp(18px, 4.5vw, 28px)',
              fontWeight: 300, fontStyle: 'italic',
              color: 'rgba(255,255,255,0.9)',
              textAlign: 'center', lineHeight: 1.7,
              letterSpacing: '0.02em',
              textShadow: '0 0 40px rgba(255,255,255,0.1)',
            }}>
              {reflectionText}
            </p>
          </div>
        )}

        {/* ── ABOUT SCREEN ──────────────────────────────────────────── */}
        <div style={{
          position: 'fixed', inset: 0, zIndex: 25,
          opacity: isAbout ? 1 : 0,
          pointerEvents: isAbout ? 'auto' : 'none',
          transition: 'opacity 0.5s ease',
          overflowY: 'auto',
          display: 'flex', flexDirection: 'column',
          padding: 'clamp(48px, 8vw, 80px) clamp(24px, 6vw, 64px)',
          paddingBottom: 100,
          background: '#080808',
        }}>
          <button
            onClick={() => setPhase('gallery')}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              fontFamily: vt323.style.fontFamily, fontSize: 13,
              color: 'rgba(255,255,255,0.3)', letterSpacing: '0.12em',
              padding: 0, marginBottom: 40, alignSelf: 'flex-start',
              textDecoration: 'none',
            }}
          >
            ← GALLERY
          </button>

          <div style={{
            fontFamily: vt323.style.fontFamily, fontSize: 52,
            letterSpacing: '0.15em', color: '#00ff41',
            textShadow: '0 0 20px rgba(0,255,65,0.3)',
          }}>
            ACID
          </div>

          <div className={cormorant.className} style={{
            fontSize: 18, fontStyle: 'italic', fontWeight: 300,
            color: 'rgba(255,255,255,0.5)', marginTop: 6, letterSpacing: '0.04em',
          }}>
            Algorithmic Creative Intelligence Display
          </div>

          <div style={{
            height: 1, background: 'rgba(255,255,255,0.1)',
            margin: '28px 0',
          }} />

          <div className={cormorant.className} style={{
            fontSize: 16, fontWeight: 300, lineHeight: 1.85,
            color: 'rgba(255,255,255,0.65)', letterSpacing: '0.02em',
            maxWidth: 480,
          }}>
            It started as a terminal — formulas generating living ASCII art in real time,
            frame by frame, pure math rendered as character and light.
            <br /><br />
            Then the question: what if they lived in a browser? Fullscreen, mobile-first,
            available to anyone? What if the interface was as deliberate as the mathematics?
            <br /><br />
            Each formula is a conversation between intent and execution. The math is old.
            The collaboration is new.
          </div>

          <div style={{ marginTop: 40 }}>
            <a
              href="https://handoffpack.com"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                fontFamily: vt323.style.fontFamily, fontSize: 13,
                color: 'rgba(0,255,65,0.5)', letterSpacing: '0.1em',
                textDecoration: 'none',
              }}
            >
              Made by HandoffPack →
            </a>
          </div>
        </div>

        {/* ── BOTTOM NAV ──────────────────────────────────────────────── */}
        {!isIntro && (
          <div style={{
            position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 50,
            backdropFilter: 'blur(24px)',
            WebkitBackdropFilter: 'blur(24px)',
            background: 'rgba(8,8,8,0.88)',
            borderTop: '1px solid rgba(255,255,255,0.06)',
            paddingBottom: 'env(safe-area-inset-bottom, 8px)',
            opacity: isAnimating && !navControls ? 0.3 : 1,
            transition: 'opacity 0.4s ease',
          }}>
            <div style={{
              display: 'flex', justifyContent: 'space-around', alignItems: 'center',
              height: 56,
            }}>
              {/* Gallery */}
              <button
                onClick={() => {
                  if (isAnimating) stopAnimation()
                  else if (isAbout) setPhase('gallery')
                }}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  color: isGallery ? '#00ff41' : 'rgba(255,255,255,0.35)',
                  transition: 'color 0.2s',
                  padding: '4px 20px',
                }}
              >
                <GridIcon />
                <span style={{ fontFamily: vt323.style.fontFamily, fontSize: 10, letterSpacing: '0.1em' }}>
                  GALLERY
                </span>
              </button>

              {/* Now Playing */}
              <button
                onClick={() => {
                  if (activeIdx !== null && !isAnimating) {
                    startAnimation(ARCHETYPES[activeIdx], activeIdx)
                  }
                }}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  color: isAnimating ? '#00ff41' : 'rgba(255,255,255,0.25)',
                  transition: 'color 0.2s',
                  padding: '4px 20px',
                }}
              >
                <div className={isAnimating ? 'pulse' : ''}>
                  <PlayIcon active={isAnimating} />
                </div>
                <span style={{ fontFamily: vt323.style.fontFamily, fontSize: 10, letterSpacing: '0.1em' }}>
                  {isAnimating ? (isPlaying ? 'NOW' : 'PAUSED') : 'NOW'}
                </span>
              </button>

              {/* About */}
              <button
                onClick={() => {
                  if (isAnimating) stopAnimation()
                  setPhase('about')
                }}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  color: isAbout ? '#00ff41' : 'rgba(255,255,255,0.35)',
                  transition: 'color 0.2s',
                  padding: '4px 20px',
                }}
              >
                <InfoIcon />
                <span style={{ fontFamily: vt323.style.fontFamily, fontSize: 10, letterSpacing: '0.1em' }}>
                  ABOUT
                </span>
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  )
}
