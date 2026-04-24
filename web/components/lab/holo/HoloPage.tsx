'use client'

import React, { useState, useEffect, useCallback, useRef, useMemo, useId, FormEvent } from 'react'
import Image from 'next/image'
import ReactDOM from 'react-dom'

// ═══════════════════════════════════════════════════════════════════════════
// HOLO — Pokémon TCG price intelligence
// Design: Orbitron brand / Space Grotesk UI / JetBrains Mono prices
// Card-influenced accent colors via canvas color extraction
// ═══════════════════════════════════════════════════════════════════════════

const API_BASE = process.env.NEXT_PUBLIC_HOLO_API_URL || '/api/holo'

// ═══════════════════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════════════════

type Grade = 'raw' | 'psa9' | 'psa10'
type TimeRange = '7' | '30' | '90' | '365'
type Tab = 'overview' | 'sales' | 'flip' | 'grade'

interface Ability {
  name: string
  text: string
  type?: string
}

interface Attack {
  name: string
  cost: string[]
  damage?: string
  text?: string
  convertedEnergyCost?: number
}

interface Weakness {
  type: string
  value: string
}

interface CardMeta {
  id: string
  name: string
  number: string
  image_small: string
  image_large: string
  set_name: string
  set_series: string
  set_symbol: string
  set_logo: string
  rarity: string
  release_date: string
  tcgplayer_url: string
  // Extended (all optional — older cached rows won't have them)
  hp?: string
  types?: string[]
  subtypes?: string[]
  supertype?: string
  evolvesFrom?: string
  evolvesTo?: string[]
  abilities?: Ability[]
  attacks?: Attack[]
  weaknesses?: Weakness[]
  resistances?: Weakness[]
  retreatCost?: string[]
  convertedRetreatCost?: number
  flavorText?: string
  artist?: string
  nationalPokedexNumbers?: number[]
  regulationMark?: string
  set_printed_total?: number
  set_total?: number
}

interface SpeciesData {
  name?: string
  genus?: string
  flavor_text?: string
  habitat?: string | null
  color?: string | null
  generation?: string | null
  is_legendary?: boolean
  is_mythical?: boolean
  height_m?: number
  weight_kg?: number
  types?: string[]
  stats?: { hp?: number; attack?: number; defense?: number; 'sp-atk'?: number; 'sp-def'?: number; speed?: number }
  sprite?: string | null
}

interface PokedexData {
  meta: CardMeta
  species: SpeciesData
}

interface Source {
  name: string
  label: string
  url: string
  count: number
}

interface HistoryPoint {
  date: string
  price: number
  count: number
}

interface HistoryData {
  card: string
  grade: Grade
  days: number
  points: HistoryPoint[]
  summary: {
    current: number
    first: number
    high: number
    low: number
    change: number
    change_pct: number
    sales_count: number
  }
  synthetic_ratio?: number
  data_quality_warning?: string | null
  sources: Source[]
  meta?: CardMeta
  error?: string
}

interface GradeROIData {
  card: string
  service: string
  service_cost: number
  turnaround: string
  prices: Record<Grade, { cmc: number; sales_used: number; confidence: string } | null>
  assumptions: {
    p10: number
    p9: number
    p_sub: number
    sell_fees: number
    shipping: number
  }
  breakdown: {
    expected_psa10_value: number
    expected_psa9_value: number
    expected_sub_value: number
    expected_revenue: number
    total_cost: number
    net_ev: number
    raw_baseline: number
    delta: number
    delta_pct: number
  }
  verdict: string
  verdict_tone: 'buy' | 'sell' | 'neutral'
  rationale: string
  error?: string
}

interface PriceData {
  card: string
  cmc: number
  mean: number
  delta_pct: number
  confidence: string
  volatility: string
  stddev: number
  sales_used: number
  newest: string
  oldest: string
  insufficient_data_warning?: string
  sources: Source[]
  grade: Grade
  error?: string
}

interface SignalData {
  card: string
  signal: string
  price: number
  sma30: number | null
  dip_pct: number | null
  rsi: number | null
  vol_3d: number
  vol_surge_pct: number | null
  sources: Source[]
  grade: Grade
  error?: string
}

interface GradesData {
  card: string
  grades: Record<Grade, null | {
    cmc: number
    mean: number
    sales_used: number
    confidence: string
    oldest: string
    newest: string
    error?: string
  }>
  error?: string
}

interface SalesFeedData {
  card: string
  grade: Grade
  count: number
  total_available: number
  sales: Array<{
    date: string
    price: number
    condition: string
    source: string
    source_label: string
    source_url: string
  }>
  error?: string
}

interface FlipData {
  card: string
  method: string
  raw_cost: number
  packs: number | null
  cmc: number
  cost_basis: number
  platform_fee: number
  shipping_cost: number
  shipping_type: string
  profit: number
  margin_pct: number
  verdict: string
  break_even: number
  confidence: string
  sales_used: number
  grade: Grade
  synthetic_only?: boolean
  synthetic_ratio?: number
  data_quality_warning?: string | null
  sources: Source[]
  error?: string
}

// ═══════════════════════════════════════════════════════════════════════════
// Formatting helpers
// ═══════════════════════════════════════════════════════════════════════════

function money(n: number | null | undefined, digits = 2): string {
  if (n == null || !Number.isFinite(n)) return '—'
  return '$' + n.toLocaleString('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

function pct(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return '—'
  return (n >= 0 ? '+' : '') + n.toFixed(1) + '%'
}

function deltaTone(n: number | null | undefined): 'up' | 'down' | 'flat' {
  if (n == null || !Number.isFinite(n)) return 'flat'
  if (n > 0.5) return 'up'
  if (n < -0.5) return 'down'
  return 'flat'
}

function toneText(tone: 'up' | 'down' | 'flat'): string {
  if (tone === 'up') return 'text-emerald-400'
  if (tone === 'down') return 'text-red-400'
  return 'text-zinc-400'
}

function relativeDate(iso: string): string {
  try {
    const d = new Date(iso + 'T00:00:00Z')
    const diff = Date.now() - d.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    if (days === 0) return 'Today'
    if (days === 1) return 'Yesterday'
    if (days < 7) return `${days}d ago`
    if (days < 30) return `${Math.floor(days / 7)}w ago`
    return iso
  } catch {
    return iso
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// Watchlist (localStorage)
// ═══════════════════════════════════════════════════════════════════════════

function useWatchlist() {
  const [list, setList] = useState<string[]>([])

  useEffect(() => {
    try {
      const raw = localStorage.getItem('holo.watchlist')
      if (raw) setList(JSON.parse(raw))
    } catch {}
  }, [])

  const persist = useCallback((next: string[]) => {
    setList(next)
    try {
      localStorage.setItem('holo.watchlist', JSON.stringify(next))
    } catch {}
  }, [])

  const has = useCallback((name: string) => list.includes(name.toLowerCase()), [list])
  const add = useCallback((name: string) => {
    const key = name.trim().toLowerCase()
    if (!key || list.includes(key)) return
    persist([key, ...list].slice(0, 50))
  }, [list, persist])
  const remove = useCallback((name: string) => {
    persist(list.filter((x) => x !== name.toLowerCase()))
  }, [list, persist])
  const toggle = useCallback((name: string) => {
    if (has(name)) remove(name)
    else add(name)
  }, [has, add, remove])

  return { list, has, add, remove, toggle }
}

// ═══════════════════════════════════════════════════════════════════════════
// Recently Viewed (localStorage)
// ═══════════════════════════════════════════════════════════════════════════

function useRecentlyViewed() {
  const [list, setList] = useState<RecentItem[]>([])

  useEffect(() => {
    try {
      const raw = localStorage.getItem('holo.recently_viewed')
      if (raw) {
        const parsed = JSON.parse(raw)
        // Prune any stale entries from older schema versions that lack
        // a name/card — they crash the <Image>/first-letter fallback.
        const valid = Array.isArray(parsed)
          ? parsed.filter((x): x is RecentItem =>
              x && typeof x.card === 'string' && typeof x.name === 'string' && x.card && x.name
            )
          : []
        setList(valid)
        if (valid.length !== (parsed?.length ?? 0)) {
          try { localStorage.setItem('holo.recently_viewed', JSON.stringify(valid)) } catch {}
        }
      }
    } catch {}
  }, [])

  const add = useCallback((item: RecentItem) => {
    // Guard against incomplete meta — only store fully-formed entries.
    if (!item || !item.card || !item.name) return
    const safeItem: RecentItem = {
      card: item.card,
      name: item.name,
      image_small: item.image_small || '',
    }
    setList((prev) => {
      const filtered = prev.filter((x) => x.card !== safeItem.card)
      const next = [safeItem, ...filtered].slice(0, 10)
      try { localStorage.setItem('holo.recently_viewed', JSON.stringify(next)) } catch {}
      return next
    })
  }, [])

  return { list, add }
}

// ═══════════════════════════════════════════════════════════════════════════
// Ultra Ball — inline SVG. Yellow top with characteristic black "H"-shape
// stripes flaring from the button, black equator, white bottom. Used as
// loading spinner, lookup-screen accent, and brand mark.
// ═══════════════════════════════════════════════════════════════════════════

function Pokeball({
  size = 48,
  spin = false,
  className = '',
  style,
}: {
  size?: number
  spin?: boolean
  className?: string
  style?: React.CSSProperties
}) {
  const uid = React.useId()
  return (
    <svg
      viewBox="0 0 100 100"
      width={size}
      height={size}
      className={`${spin ? 'animate-spin' : ''} ${className}`}
      style={{
        filter: 'drop-shadow(0 6px 16px rgba(0,0,0,0.55))',
        ...style,
      }}
      aria-hidden="true"
    >
      <defs>
        <radialGradient id={`ub-top-${uid}`} cx="40%" cy="32%" r="72%">
          <stop offset="0%" stopColor="#FFE27A" />
          <stop offset="45%" stopColor="#F5C518" />
          <stop offset="85%" stopColor="#C99608" />
          <stop offset="100%" stopColor="#7A5A00" />
        </radialGradient>
        <radialGradient id={`ub-bot-${uid}`} cx="40%" cy="68%" r="70%">
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="65%" stopColor="#e4e4e7" />
          <stop offset="100%" stopColor="#52525b" />
        </radialGradient>
        <clipPath id={`ub-top-clip-${uid}`}>
          <path d="M50 4 A46 46 0 0 1 96 50 L4 50 A46 46 0 0 1 50 4 Z" />
        </clipPath>
      </defs>
      {/* Yellow top half */}
      <path d="M50 4 A46 46 0 0 1 96 50 L4 50 A46 46 0 0 1 50 4 Z" fill={`url(#ub-top-${uid})`} />
      {/* Ultra Ball's signature H-stripes — two black bands flaring from the
          center button out to the edges. Rendered inside clipped top half. */}
      <g clipPath={`url(#ub-top-clip-${uid})`}>
        <path d="M50 50 L18 4 L30 4 L57 50 Z" fill="#0a0a0a" />
        <path d="M50 50 L82 4 L70 4 L43 50 Z" fill="#0a0a0a" />
      </g>
      {/* Subtle highlight streak on top */}
      <path
        d="M22 22 Q40 10 58 14"
        stroke="#ffffff"
        strokeOpacity="0.35"
        strokeWidth="3"
        fill="none"
        strokeLinecap="round"
      />
      {/* Bottom (white) half */}
      <path d="M4 50 L96 50 A46 46 0 0 1 50 96 A46 46 0 0 1 4 50 Z" fill={`url(#ub-bot-${uid})`} />
      {/* Central black band */}
      <rect x="2" y="46" width="96" height="9" fill="#0a0a0a" />
      {/* Red accent pinstripe on equator */}
      <rect x="2" y="45.5" width="96" height="0.8" fill="#ef4444" opacity="0.55" />
      {/* Button: black outer, white ring, dot */}
      <circle cx="50" cy="50" r="14.5" fill="#0a0a0a" />
      <circle cx="50" cy="50" r="10.5" fill="#fafafa" />
      <circle cx="50" cy="50" r="6" fill="#F5C518" />
      <circle cx="46.5" cy="46.5" r="2.2" fill="#ffffff" opacity="0.95" />
    </svg>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// Card theme — extracts a full palette from the card art so the whole screen
// can echo the card's colour identity. Returns accent (mid-saturation for
// text/borders), glow (bright, for drop shadows), deep (dark, for gradient
// backgrounds), and hue (raw angle) for compositing.
// ═══════════════════════════════════════════════════════════════════════════

export interface CardTheme {
  accent: string
  glow: string
  deep: string
  /** Very dark, saturated — for full-page takeover gradient corners. */
  bgDeep: string
  /** Near-black with a hint of hue — for takeover gradient base. */
  bgBase: string
  hue: number
  /** Secondary palette colour — second-most-dominant hue extracted from
   *  the card art. Used to add depth to the takeover gradient so the page
   *  isn't just one flat hue. */
  accent2: string
  /** Tertiary palette colour — third hue, tints the opposite corner. */
  accent3: string
  /** True when hue sits in the warm band (yellow/orange) — callers boost
   *  luma so the colour reads as yellow, not olive/green. */
  isWarm: boolean
  ready: boolean
}

const DEFAULT_THEME: CardTheme = {
  accent: '#F5C518',
  glow: '#FFE27A',
  deep: '#78500a',
  bgDeep: '#1a1305',
  bgBase: '#0a0a0a',
  hue: 48,
  accent2: '#F59E0B',
  accent3: '#FBBF24',
  isWarm: true,
  ready: false,
}

// Module-level memo so revisiting a card skips the canvas sample entirely.
// Theme extraction is deterministic given the same image URL.
const THEME_CACHE: Map<string, CardTheme> = new Map()

function useCardTheme(imageUrl: string | undefined): CardTheme {
  const [theme, setTheme] = useState<CardTheme>(() => {
    if (imageUrl && THEME_CACHE.has(imageUrl)) return THEME_CACHE.get(imageUrl)!
    return DEFAULT_THEME
  })

  useEffect(() => {
    if (!imageUrl) {
      setTheme(DEFAULT_THEME)
      return
    }
    const cached = THEME_CACHE.get(imageUrl)
    if (cached) {
      setTheme(cached)
      return
    }
    let cancelled = false
    const img = new window.Image()
    img.crossOrigin = 'anonymous'
    img.onerror = () => { if (!cancelled) setTheme(DEFAULT_THEME) }
    img.onload = () => {
      if (cancelled) return
      try {
        const canvas = document.createElement('canvas')
        const N = 32
        canvas.width = N
        canvas.height = N
        const ctx = canvas.getContext('2d')
        if (!ctx) return
        ctx.drawImage(img, 0, 0, N, N)
        const data = ctx.getImageData(0, 0, N, N).data
        // Hue histogram: 12 buckets × 30°. For each colourful mid-luma pixel
        // we weight its bucket by chroma² × √luma — this heavily favours
        // bright, very-saturated pixels (Miraidon's gold/yellow) over
        // medium-luma saturated pixels (the cyan body). A plain saturation
        // sum was losing to high-coverage but duller cyan areas. We keep a
        // list of actual hues per bucket so the final pick is the median
        // hue within the dominant bucket.
        const BUCKETS = 12
        const weights = new Array<number>(BUCKETS).fill(0)
        const hueLists: number[][] = Array.from({ length: BUCKETS }, () => [])
        for (let i = 0; i < data.length; i += 4) {
          const R = data[i], G = data[i + 1], B = data[i + 2]
          const luma = (R * 299 + G * 587 + B * 114) / 1000
          if (luma < 40 || luma > 235) continue
          const rn = R / 255, gn = G / 255, bn = B / 255
          const mx = Math.max(rn, gn, bn), mn = Math.min(rn, gn, bn)
          const d = mx - mn
          if (d < 0.14) continue // skip greys a bit more aggressively
          const sat = mx === 0 ? 0 : d / mx
          let h = 0
          if (mx === rn) h = ((gn - bn) / d) % 6
          else if (mx === gn) h = (bn - rn) / d + 2
          else h = (rn - gn) / d + 4
          const hue = ((h * 60) + 360) % 360
          const bucket = Math.floor(hue / (360 / BUCKETS)) % BUCKETS
          // Weight = chroma² × √luma. Yellow (high-luma, high-chroma)
          // dominates cyan (mid-luma, high-chroma) even when cyan covers
          // more area of the card art.
          const lumaN = Math.sqrt(luma / 255)
          weights[bucket] += sat * sat * lumaN
          hueLists[bucket].push(hue)
        }
        // Rank buckets by weight; pick the top 3 that each hold real
        // coverage. We want distinct hues, not three variants of the same
        // bucket — enforce a 2-bucket minimum angular separation on
        // secondaries so the palette feels genuinely polychromatic.
        const ranked = weights
          .map((w, i) => ({ w, i }))
          .filter((x) => x.w > 0 && hueLists[x.i].length > 0)
          .sort((a, b) => b.w - a.w)
        if (ranked.length === 0) return
        const pickMedianHue = (bucket: number): number => {
          const s = hueLists[bucket].slice().sort((a, b) => a - b)
          return Math.round(s[Math.floor(s.length / 2)])
        }
        const hue = pickMedianHue(ranked[0].i)
        // Secondary: prefer bucket ≥2 apart from primary.
        let hue2 = hue
        for (let k = 1; k < ranked.length; k++) {
          const b = ranked[k].i
          const dist = Math.min(
            Math.abs(b - ranked[0].i),
            BUCKETS - Math.abs(b - ranked[0].i),
          )
          if (dist >= 2) { hue2 = pickMedianHue(b); break }
        }
        // Tertiary: 2+ apart from both primary and secondary, else derive.
        let hue3 = (hue + 180) % 360
        for (let k = 1; k < ranked.length; k++) {
          const b = ranked[k].i
          const h = pickMedianHue(b)
          const d1 = Math.min(Math.abs(h - hue), 360 - Math.abs(h - hue))
          const d2 = Math.min(Math.abs(h - hue2), 360 - Math.abs(h - hue2))
          if (d1 >= 45 && d2 >= 45) { hue3 = h; break }
        }
        if (cancelled) return
        // Warm hues (yellow/orange, ~25°-90°) read as olive/green at low luma.
        // Keep bgDeep/bgBase/deep luminance higher in that band so yellow
        // actually looks yellow on the page.
        const isWarm = hue >= 25 && hue <= 90
        // Warm hues (yellow/orange) read as olive/green at low luma — boost
        // luminance in the warm band so yellow actually looks yellow.
        const bgDeepL = isWarm ? 28 : 22
        const bgBaseL = isWarm ? 14 : 10
        const deepL = isWarm ? 34 : 26
        const next: CardTheme = {
          accent:  `hsl(${hue}, 92%, 62%)`,
          glow:    `hsl(${hue}, 100%, 72%)`,
          deep:    `hsl(${hue}, 72%, ${deepL}%)`,
          bgDeep:  `hsl(${hue}, 88%, ${bgDeepL}%)`,
          bgBase:  `hsl(${hue}, 68%, ${bgBaseL}%)`,
          hue,
          accent2: `hsl(${hue2}, 88%, 58%)`,
          accent3: `hsl(${hue3}, 85%, 60%)`,
          isWarm,
          ready: true,
        }
        THEME_CACHE.set(imageUrl, next)
        setTheme(next)
      } catch { /* CORS-tainted canvas — keep default theme */ }
    }
    img.onerror = () => {
      // Network failure (not CORS — that lands in onload's catch). Fall back
      // so the detail page doesn't inherit the previous card's palette.
      if (!cancelled) setTheme(DEFAULT_THEME)
    }
    img.src = imageUrl
    return () => { cancelled = true }
  }, [imageUrl])

  return theme
}

// Back-compat shim — some call sites still destructure { accent }.
function useCardAccent(imageUrl: string | undefined): { accent: string } {
  const { accent } = useCardTheme(imageUrl)
  return { accent }
}

// ═══════════════════════════════════════════════════════════════════════════
// Sparkline chart (SVG)
// ═══════════════════════════════════════════════════════════════════════════

interface SparklineProps {
  points: HistoryPoint[]
  height?: number
  tone: 'up' | 'down' | 'flat'
  showDots?: boolean
  accentColor?: string
}

interface ScrubState {
  idx: number
  pctX: number
  pctY: number
}

// Module-level constants so useMemo deps stay clean
const SPARK_WIDTH = 1000
const SPARK_PAD = 4

function formatScrubDate(dateStr: string): string {
  try {
    const d = new Date(dateStr)
    // timeZone: 'UTC' prevents ISO date strings like '2024-03-15' from
    // shifting one day back for users west of UTC (e.g. US Pacific)
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' })
  } catch {
    return '—'
  }
}

function Sparkline({ points, height = 140, tone, showDots, accentColor }: SparklineProps) {
  const [scrub, setScrub] = useState<ScrubState | null>(null)
  // useId: per-instance gradient ID — avoids collision when multiple
  // Sparklines render on the same page (e.g. TopMovers + card detail)
  const gradId = useId()

  // Memoize all point-derived geometry so it doesn't recompute at 60Hz
  // during scrub ticks (only recomputes when points or height change)
  const { xs, ys, strokePath, areaPath } = useMemo(() => {
    if (!points || points.length < 2) {
      return { xs: [] as number[], ys: [] as number[], strokePath: '', areaPath: '' }
    }
    const prices = points.map((p) => p.price)
    const min = Math.min(...prices)
    const max = Math.max(...prices)
    const range = max - min || 1
    const xs = points.map((_, i) =>
      (i / (points.length - 1)) * (SPARK_WIDTH - SPARK_PAD * 2) + SPARK_PAD
    )
    const ys = points.map((p) =>
      height - SPARK_PAD - ((p.price - min) / range) * (height - SPARK_PAD * 2)
    )
    const strokePath = xs
      .map((x, i) => `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${ys[i].toFixed(1)}`)
      .join(' ')
    const areaPath = `${strokePath} L ${xs[xs.length - 1].toFixed(1)} ${height} L ${xs[0].toFixed(1)} ${height} Z`
    return { xs, ys, strokePath, areaPath }
  }, [points, height])

  const clearScrub = useCallback(() => setScrub(null), [])

  // setPointerCapture on pointerdown keeps touch pointermove events firing
  // on this element even when the finger drifts outside its bounds — prevents
  // tooltip flicker on aggressive scrubs
  const handlePointerDown = useCallback((e: React.PointerEvent<SVGSVGElement>) => {
    e.currentTarget.setPointerCapture(e.pointerId)
  }, [])

  const handlePointerMove = useCallback((e: React.PointerEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    if (rect.width === 0) return
    const svgX = ((e.clientX - rect.left) / rect.width) * SPARK_WIDTH

    let nearest = 0
    let nearestDist = Infinity
    xs.forEach((x, i) => {
      const dist = Math.abs(x - svgX)
      if (dist < nearestDist) { nearestDist = dist; nearest = i }
    })

    setScrub({
      idx: nearest,
      pctX: (xs[nearest] / SPARK_WIDTH) * 100,
      // clamp to 0–100 so dot/tooltip never render outside the chart bounds
      pctY: Math.max(0, Math.min(100, (ys[nearest] / height) * 100)),
    })
  }, [xs, ys, height])

  const handlePointerUp = useCallback((e: React.PointerEvent<SVGSVGElement>) => {
    e.currentTarget.releasePointerCapture(e.pointerId)
    setScrub(null)
  }, [])

  if (!points || points.length < 2) {
    return (
      <div
        className="w-full bg-zinc-900/40 rounded-lg flex items-center justify-center text-xs text-zinc-600"
        style={{ height }}
      >
        Not enough data
      </div>
    )
  }

  const strokeColor = accentColor || (tone === 'up' ? '#10b981' : tone === 'down' ? '#ef4444' : '#a1a1aa')

  // Bounds-checked point access — guards against scrub.idx becoming stale
  // if points[] shrinks between when scrub was set and when this renders
  const scrubbedPt = scrub && scrub.idx < points.length ? points[scrub.idx] : null
  const isRight = scrub && scrub.pctX > 58

  return (
    <div className="relative select-none">
      <svg
        viewBox={`0 0 ${SPARK_WIDTH} ${height}`}
        preserveAspectRatio="none"
        className="w-full"
        // touchAction on the SVG only — wrapper div stays scrollable so
        // users can scroll past the chart on mobile
        style={{ height, cursor: 'crosshair', touchAction: 'none' }}
        role="img"
        aria-label="Price history chart — drag to inspect values"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={clearScrub}
        onPointerLeave={clearScrub}
      >
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={strokeColor} stopOpacity="0.25" />
            <stop offset="100%" stopColor={strokeColor} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={areaPath} fill={`url(#${gradId})`} />
        <path
          d={strokePath}
          fill="none"
          stroke={strokeColor}
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
        />
        {showDots && xs.map((x, i) => (
          <circle
            key={i}
            cx={x}
            cy={ys[i]}
            r={i === xs.length - 1 && !scrub ? 5 : 0}
            fill={strokeColor}
          />
        ))}
        {/* Crosshair vertical line */}
        {scrubbedPt && scrub && (
          <line
            x1={xs[scrub.idx]} y1={0}
            x2={xs[scrub.idx]} y2={height}
            stroke={strokeColor}
            strokeWidth="1.5"
            strokeOpacity="0.45"
            strokeDasharray="4 3"
            vectorEffect="non-scaling-stroke"
          />
        )}
      </svg>

      {/* Scrubber dot — outside SVG to stay circular regardless of aspect ratio */}
      {scrubbedPt && scrub && (
        <div
          className="pointer-events-none absolute w-3 h-3 rounded-full border-2"
          style={{
            left: `${scrub.pctX}%`,
            top: `${scrub.pctY}%`,
            transform: 'translate(-50%, -50%)',
            backgroundColor: strokeColor,
            borderColor: '#09090b',
            boxShadow: `0 0 0 3px ${strokeColor}30, 0 0 10px 2px ${strokeColor}60`,
            zIndex: 10,
          }}
        />
      )}

      {/* Floating tooltip */}
      {scrubbedPt && scrub && (
        <div
          className="pointer-events-none absolute top-1.5 bg-zinc-950/95 border border-zinc-700/60 rounded-lg px-2.5 py-1.5 backdrop-blur-sm shadow-2xl"
          style={{
            left: `${scrub.pctX}%`,
            transform: isRight ? 'translateX(calc(-100% - 10px))' : 'translateX(10px)',
            zIndex: 20,
          }}
        >
          <div
            className="text-sm font-bold tabular-nums leading-none"
            style={{ color: strokeColor, fontFamily: 'var(--font-mono, monospace)' }}
          >
            {money(scrubbedPt.price)}
          </div>
          <div className="text-[10px] text-zinc-400 mt-1 whitespace-nowrap tabular-nums">
            {formatScrubDate(scrubbedPt.date)}
          </div>
          {scrubbedPt.count > 1 && (
            <div className="text-[9px] text-zinc-600 mt-0.5 tabular-nums">
              {scrubbedPt.count} sales
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// Small UI primitives
// ═══════════════════════════════════════════════════════════════════════════

function GradeChip({ grade, onClick, active }: { grade: Grade; onClick?: () => void; active?: boolean }) {
  const cfg =
    grade === 'psa10' ? { label: 'PSA 10', cls: 'text-cyan-300 border-cyan-400/70 bg-cyan-950/40' } :
    grade === 'psa9'  ? { label: 'PSA 9',  cls: 'text-purple-300 border-purple-400/70 bg-purple-950/40' } :
                        { label: 'Raw',    cls: 'text-zinc-300 border-zinc-600 bg-zinc-800/50' }
  const inactive = 'text-zinc-500 border-zinc-800 bg-zinc-900 hover:border-zinc-600'
  const activeClass = active === false ? inactive : cfg.cls
  const Component = onClick ? 'button' : 'span'
  return (
    <Component
      type={onClick ? 'button' : undefined}
      onClick={onClick}
      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md border text-[10px] font-bold tracking-[0.15em] uppercase transition-colors ${activeClass}`}
      style={{ fontFamily: 'var(--font-space, system-ui)' }}
    >
      {cfg.label}
    </Component>
  )
}

function DeltaChip({ value, size = 'sm' }: { value: number | null; size?: 'sm' | 'md' }) {
  const tone = deltaTone(value)
  const bg =
    tone === 'up' ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' :
    tone === 'down' ? 'text-red-400 bg-red-500/10 border-red-500/30' :
    'text-zinc-400 bg-zinc-800/60 border-zinc-700'
  const sz = size === 'md' ? 'text-sm px-2.5 py-1' : 'text-[11px] px-2 py-0.5'
  return (
    <span className={`inline-flex items-center gap-1 rounded-md border font-semibold tabular-nums ${bg} ${sz}`}>
      {tone === 'up' ? '▲' : tone === 'down' ? '▼' : '—'} {pct(value)}
    </span>
  )
}

function StarButton({ active, onClick }: { active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-10 h-10 flex items-center justify-center rounded-full border transition-all ${
        active
          ? 'text-amber-400 border-amber-400/60 bg-amber-400/10'
          : 'text-zinc-500 border-zinc-800 hover:border-zinc-600 hover:text-zinc-300'
      }`}
      aria-label={active ? 'Remove from watchlist' : 'Add to watchlist'}
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill={active ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
      </svg>
    </button>
  )
}

function Spinner() {
  return (
    <div className="inline-block w-4 h-4 border-2 border-zinc-700 border-t-[var(--holo-accent,#fbbf24)] rounded-full animate-spin" />
  )
}

function SourcesRow({ sources }: { sources: Source[] | undefined }) {
  if (!sources || sources.length === 0) return null
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-zinc-500">
      <span className="tracking-[0.15em] uppercase text-zinc-600">Sources</span>
      {sources.map((s) => (
        s.url ? (
          <a
            key={s.name}
            href={s.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[var(--holo-accent,#fbbf24)] hover:opacity-80 underline decoration-current/40"
          >
            {s.label} ({s.count})
          </a>
        ) : (
          <span key={s.name}>{s.label} ({s.count})</span>
        )
      ))}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// Lightbox — fullscreen card image modal
// ═══════════════════════════════════════════════════════════════════════════

const TYPE_COLORS: Record<string, string> = {
  normal: '#A8A77A',
  fire: '#EE8130',
  water: '#6390F0',
  electric: '#F7D02C',
  grass: '#7AC74C',
  ice: '#96D9D6',
  fighting: '#C22E28',
  poison: '#A33EA1',
  ground: '#E2BF65',
  flying: '#A98FF3',
  psychic: '#F95587',
  bug: '#A6B91A',
  rock: '#B6A136',
  ghost: '#735797',
  dragon: '#6F35FC',
  dark: '#705746',
  steel: '#B7B7CE',
  fairy: '#D685AD',
  // TCG-only energy types
  colorless: '#A8A8A8',
  darkness: '#4A3B36',
  lightning: '#F7D02C',
  metal: '#B7B7CE',
}

const STAT_LABELS: Array<{ key: 'hp' | 'attack' | 'defense' | 'sp-atk' | 'sp-def' | 'speed'; label: string }> = [
  { key: 'hp', label: 'HP' },
  { key: 'attack', label: 'Atk' },
  { key: 'defense', label: 'Def' },
  { key: 'sp-atk', label: 'SpA' },
  { key: 'sp-def', label: 'SpD' },
  { key: 'speed', label: 'Spe' },
]

function typeColor(t: string): string {
  return TYPE_COLORS[(t || '').toLowerCase()] || '#6b7280'
}

function EnergyCircle({ type }: { type: string }) {
  return (
    <span
      className="inline-block w-4 h-4 rounded-full border border-black/40"
      style={{ background: typeColor(type) }}
      title={type}
      aria-label={type}
    />
  )
}

function TypeChip({ type }: { type: string }) {
  return (
    <span
      className="inline-block text-[10px] font-semibold uppercase tracking-widest px-2 py-0.5 rounded"
      style={{ background: typeColor(type), color: '#0a0a0a' }}
    >
      {type}
    </span>
  )
}

function Lightbox({
  open,
  onClose,
  meta,
  displayName,
}: {
  open: boolean
  onClose: () => void
  meta: CardMeta | undefined
  displayName: string
}) {
  const [data, setData] = useState<PokedexData | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', handler)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  useEffect(() => {
    if (!open || !displayName) return
    let cancelled = false
    setLoading(true)
    setData(null)
    // CRITICAL: pass the card id when we have one. Without it the backend
    // re-searches by name and can land on a DIFFERENT printing (e.g. the
    // Paldean Fates Miraidon ex #243 shows the Scarlet & Violet #081
    // printing's image in the overlay). Passing id pins the lookup.
    const idParam = meta?.id ? `&id=${encodeURIComponent(meta.id)}` : ''
    fetch(`${API_BASE}?action=pokedex&card=${encodeURIComponent(displayName)}${idParam}`)
      .then((r) => r.json())
      .then((j) => {
        if (cancelled) return
        if (j && j.meta) setData(j as PokedexData)
      })
      .catch(() => { /* fall back to meta prop */ })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [open, displayName, meta?.id])

  if (!open || !meta?.image_large) return null

  const richMeta: CardMeta = (data?.meta as CardMeta) || meta
  const species: SpeciesData = data?.species || {}

  const setLine = [richMeta.set_name, richMeta.set_series].filter(Boolean).join(' · ')
  const numberLine = richMeta.number
    ? `${richMeta.number}${richMeta.set_printed_total ? ` / ${richMeta.set_printed_total}` : (richMeta.set_total ? ` / ${richMeta.set_total}` : '')}`
    : ''

  const genChip = species.generation
    ? species.generation.replace('generation-', 'GEN ').toUpperCase()
    : ''

  const maxStat = 255
  const speciesFlavor = (species.flavor_text || '').replace(/[\n\f]+/g, ' ').trim()

  return ReactDOM.createPortal(
    <div
      className="fixed inset-0 z-50"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Pokedex entry"
    >
      {/* Solid dark scrim — Tailwind's default opacity scale doesn't
          include /92, which silently generated no bg previously and let
          the detail page bleed through the overlay. Inline rgba is
          guaranteed. Backdrop-blur adds frost on what little bleeds. */}
      <div
        className="absolute inset-0 backdrop-blur-2xl"
        aria-hidden="true"
        style={{ background: 'rgba(6,6,8,0.92)' }}
      />
      <div
        className="absolute inset-0 mix-blend-overlay opacity-25 pointer-events-none"
        style={{ background: 'radial-gradient(ellipse at 30% 20%, var(--holo-accent, #fbbf24) 0%, transparent 65%)' }}
        aria-hidden="true"
      />

      <div
        className="relative z-10 h-full w-full overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="max-w-6xl mx-auto p-4 sm:p-8 flex flex-col sm:flex-row sm:items-start gap-6 sm:gap-10">
          {/* Card image column */}
          <div className="flex-shrink-0 flex flex-col items-center sm:sticky sm:top-8">
            <Image
              src={richMeta.image_large}
              alt={displayName}
              width={420}
              height={588}
              className="rounded-2xl border border-white/10 shadow-[0_0_80px_rgba(0,0,0,0.9)] w-[260px] sm:w-[380px] md:w-[420px] h-auto"
              style={{ boxShadow: `0 0 80px rgba(0,0,0,0.9), 0 0 40px var(--holo-accent, #fbbf24)33` }}
              priority
            />
            <div className="mt-3 text-[10px] tracking-[0.25em] uppercase text-zinc-500 hidden sm:block">
              Tap outside to dismiss
            </div>
          </div>

          {/* Info panel */}
          <div className="flex-1 min-w-0 w-full sm:max-w-[500px] relative">
            <button
              type="button"
              onClick={onClose}
              className="absolute right-0 top-0 w-11 h-11 rounded-full border border-zinc-700 bg-zinc-900/80 text-zinc-400 hover:text-white hover:border-[var(--holo-accent,#fbbf24)] transition-all flex items-center justify-center"
              aria-label="Close"
              style={{ fontFamily: 'var(--font-orbitron)' }}
            >
              <span aria-hidden="true" className="text-lg leading-none">x</span>
            </button>

            {loading && !data && (
              <div className="flex items-center gap-2 text-xs text-zinc-500 mb-4">
                <span className="inline-block w-3 h-3 border-2 border-zinc-700 border-t-[var(--holo-accent,#fbbf24)] rounded-full animate-spin" />
                Loading Pokedex entry...
              </div>
            )}

            {/* Header strip */}
            <div className="pr-14">
              {(richMeta.set_logo || setLine) && (
                <div className="flex items-center gap-3 mb-2">
                  {richMeta.set_logo && (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img src={richMeta.set_logo} alt={richMeta.set_name} className="h-8 w-auto object-contain opacity-90" />
                  )}
                  <div className="text-[11px] text-zinc-400 leading-tight">
                    {setLine && <div>{setLine}</div>}
                    {richMeta.release_date && <div className="text-zinc-600">{richMeta.release_date}</div>}
                  </div>
                </div>
              )}

              <div className="flex flex-wrap items-center gap-2 mb-4">
                {numberLine && (
                  <span className="text-[10px] tracking-widest uppercase text-zinc-500 tabular-nums">#{numberLine}</span>
                )}
                {richMeta.rarity && (
                  <span
                    className="text-[10px] tracking-widest uppercase px-2 py-0.5 rounded font-semibold"
                    style={{ background: 'var(--holo-accent, #fbbf24)', color: '#0a0a0a' }}
                  >
                    {richMeta.rarity}
                  </span>
                )}
                {richMeta.regulationMark && (
                  <span className="text-[10px] tracking-widest uppercase px-2 py-0.5 rounded border border-zinc-700 text-zinc-400">
                    {richMeta.regulationMark}
                  </span>
                )}
                {richMeta.artist && (
                  <span className="text-[10px] text-zinc-500">Illus. {richMeta.artist}</span>
                )}
              </div>
            </div>

            {/* Species banner */}
            <div className="mb-5 pb-4 border-b border-zinc-800">
              <div
                className="text-2xl sm:text-3xl font-bold text-white leading-tight"
                style={{ fontFamily: 'var(--font-orbitron, var(--font-space, system-ui))' }}
              >
                {richMeta.name || displayName}
              </div>
              {species.genus && (
                <div className="text-[11px] tracking-[0.25em] uppercase text-zinc-400 mt-1">
                  {species.genus}
                </div>
              )}
              <div className="flex flex-wrap gap-1.5 mt-2">
                {genChip && (
                  <span className="text-[10px] tracking-widest uppercase px-2 py-0.5 rounded border border-zinc-700 text-zinc-300">
                    {genChip}
                  </span>
                )}
                {species.is_legendary && (
                  <span className="text-[10px] tracking-widest uppercase px-2 py-0.5 rounded bg-amber-400/20 text-amber-300 border border-amber-500/40">
                    Legendary
                  </span>
                )}
                {species.is_mythical && (
                  <span className="text-[10px] tracking-widest uppercase px-2 py-0.5 rounded bg-fuchsia-400/20 text-fuchsia-300 border border-fuchsia-500/40">
                    Mythical
                  </span>
                )}
                {species.habitat && (
                  <span className="text-[10px] tracking-widest uppercase px-2 py-0.5 rounded border border-zinc-800 text-zinc-500">
                    {species.habitat}
                  </span>
                )}
              </div>
            </div>

            {/* Physical stats row */}
            {(richMeta.hp || species.height_m || species.weight_kg) && (
              <div className="grid grid-cols-3 gap-2 mb-5">
                <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3 text-center">
                  <div className="text-[10px] tracking-widest uppercase text-zinc-500">HP</div>
                  <div className="text-lg font-bold text-white tabular-nums">{richMeta.hp || '—'}</div>
                </div>
                <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3 text-center">
                  <div className="text-[10px] tracking-widest uppercase text-zinc-500">Height</div>
                  <div className="text-lg font-bold text-white tabular-nums">{species.height_m ? `${species.height_m.toFixed(1)} m` : '—'}</div>
                </div>
                <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3 text-center">
                  <div className="text-[10px] tracking-widest uppercase text-zinc-500">Weight</div>
                  <div className="text-lg font-bold text-white tabular-nums">{species.weight_kg ? `${species.weight_kg.toFixed(1)} kg` : '—'}</div>
                </div>
              </div>
            )}

            {/* Types + weakness/resistance */}
            {((species.types && species.types.length > 0) || (richMeta.types && richMeta.types.length > 0) || (richMeta.weaknesses && richMeta.weaknesses.length > 0) || (richMeta.resistances && richMeta.resistances.length > 0)) && (
              <div className="mb-5 space-y-2">
                {((species.types && species.types.length > 0) || (richMeta.types && richMeta.types.length > 0)) && (
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] tracking-widest uppercase text-zinc-500 w-16">Type</span>
                    {(species.types && species.types.length > 0 ? species.types : (richMeta.types || [])).map((t, i) => (
                      <TypeChip key={`t-${i}`} type={t} />
                    ))}
                  </div>
                )}
                {richMeta.weaknesses && richMeta.weaknesses.length > 0 && (
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] tracking-widest uppercase text-zinc-500 w-16">Weak</span>
                    {richMeta.weaknesses.map((w, i) => (
                      <span key={`w-${i}`} className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold tabular-nums"
                        style={{ background: `${typeColor(w.type)}33`, color: typeColor(w.type), border: `1px solid ${typeColor(w.type)}66` }}>
                        {w.type} {w.value}
                      </span>
                    ))}
                  </div>
                )}
                {richMeta.resistances && richMeta.resistances.length > 0 && (
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] tracking-widest uppercase text-zinc-500 w-16">Resist</span>
                    {richMeta.resistances.map((w, i) => (
                      <span key={`r-${i}`} className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold tabular-nums"
                        style={{ background: `${typeColor(w.type)}22`, color: typeColor(w.type), border: `1px solid ${typeColor(w.type)}55` }}>
                        {w.type} {w.value}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Base stats bar chart */}
            {species.stats && (
              <div className="mb-5">
                <div className="text-[10px] tracking-widest uppercase text-zinc-500 mb-2">Base Stats</div>
                <div className="space-y-1.5">
                  {STAT_LABELS.map(({ key, label }) => {
                    const val = (species.stats as Record<string, number> | undefined)?.[key] ?? 0
                    const pct = Math.max(5, Math.round((val / maxStat) * 100))
                    return (
                      <div key={key} className="flex items-center gap-2 text-xs">
                        <span className="w-10 text-zinc-400 uppercase tracking-wider text-[10px]">{label}</span>
                        <span className="w-8 text-right tabular-nums text-zinc-200">{val}</span>
                        <div className="flex-1 h-2 bg-zinc-900 rounded-full overflow-hidden border border-zinc-800">
                          <div
                            className="h-full rounded-full"
                            style={{ width: `${pct}%`, background: 'var(--holo-accent, #fbbf24)' }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Species flavor text */}
            {speciesFlavor && (
              <div className="mb-5">
                <div className="text-[10px] tracking-widest uppercase text-zinc-500 mb-2">Pokedex Entry</div>
                <blockquote
                  className="pl-4 py-2 border-l-2 text-sm text-zinc-300 leading-relaxed"
                  style={{ borderColor: 'var(--holo-accent, #fbbf24)' }}
                >
                  {speciesFlavor}
                </blockquote>
              </div>
            )}

            {/* TCG abilities */}
            {richMeta.abilities && richMeta.abilities.length > 0 && (
              <div className="mb-5">
                <div className="text-[10px] tracking-widest uppercase text-zinc-500 mb-2">Abilities</div>
                <div className="space-y-2">
                  {richMeta.abilities.map((a, i) => (
                    <div key={`ab-${i}`} className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-bold text-white">{a.name}</span>
                        {a.type && (
                          <span className="text-[9px] tracking-widest uppercase px-1.5 py-0.5 rounded border border-zinc-700 text-zinc-400">
                            {a.type}
                          </span>
                        )}
                      </div>
                      {a.text && <div className="text-xs text-zinc-400 leading-relaxed">{a.text}</div>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TCG attacks */}
            {richMeta.attacks && richMeta.attacks.length > 0 && (
              <div className="mb-5">
                <div className="text-[10px] tracking-widest uppercase text-zinc-500 mb-2">Attacks</div>
                <div className="space-y-2">
                  {richMeta.attacks.map((atk, i) => (
                    <div key={`atk-${i}`} className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
                      <div className="flex items-center gap-2">
                        <div className="flex gap-0.5 flex-shrink-0">
                          {(atk.cost || []).map((c, ci) => (
                            <EnergyCircle key={`c-${i}-${ci}`} type={c} />
                          ))}
                        </div>
                        <span className="text-sm font-bold text-white flex-1 truncate">{atk.name}</span>
                        {atk.damage && (
                          <span
                            className="text-xl font-bold tabular-nums"
                            style={{ fontFamily: 'var(--font-space, system-ui)', color: 'var(--holo-accent, #fbbf24)' }}
                          >
                            {atk.damage}
                          </span>
                        )}
                      </div>
                      {atk.text && <div className="text-xs text-zinc-400 leading-relaxed mt-1.5">{atk.text}</div>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Retreat cost */}
            {richMeta.retreatCost && richMeta.retreatCost.length > 0 && (
              <div className="mb-5 flex items-center gap-2">
                <span className="text-[10px] tracking-widest uppercase text-zinc-500">Retreat</span>
                <div className="flex gap-0.5">
                  {richMeta.retreatCost.map((c, i) => (
                    <span key={`rc-${i}`} className="inline-block w-3.5 h-3.5 rounded-full bg-zinc-700 border border-zinc-600" title={c} />
                  ))}
                </div>
              </div>
            )}

            {/* TCG flavor text */}
            {richMeta.flavorText && (
              <div className="mb-5 text-xs italic text-zinc-500 leading-relaxed">
                {richMeta.flavorText}
                {richMeta.artist && <div className="not-italic text-[10px] text-zinc-600 mt-1">— Illus. {richMeta.artist}</div>}
              </div>
            )}

            {/* Footer */}
            <div className="mt-6 pt-4 border-t border-zinc-800 flex items-center justify-between text-[10px] tracking-widest uppercase text-zinc-500">
              <span className="sm:hidden">Tap outside to dismiss</span>
              <span className="hidden sm:inline">Press ESC to close</span>
              {richMeta.tcgplayer_url && (
                <a
                  href={richMeta.tcgplayer_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[var(--holo-accent,#fbbf24)] hover:underline"
                  onClick={(e) => e.stopPropagation()}
                >
                  View on TCGPlayer
                </a>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>,
    document.body
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// CardHeader — blurred card background hero zone
// ═══════════════════════════════════════════════════════════════════════════

function CardHeader({
  meta,
  cardName,
  grade,
  onGradeChange,
  onLightboxOpen,
}: {
  meta: CardMeta | undefined
  cardName: string
  grade: Grade
  onGradeChange: (g: Grade) => void
  onLightboxOpen: () => void
}) {
  const displayName = meta?.name || cardName
  const setLabel = meta ? `${meta.set_name}${meta.number ? ` · #${meta.number}` : ''}` : ''

  return (
    <div className="relative rounded-2xl overflow-hidden mb-4" style={{ minHeight: 240 }}>
      {/* Blurred card art background — richer saturation, brighter */}
      {meta?.image_large && (
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: `url(${meta.image_large})`,
            backgroundSize: 'cover',
            backgroundPosition: 'center top',
            filter: 'blur(32px) brightness(0.55) saturate(1.9) contrast(1.1)',
            transform: 'scale(1.2)',
          }}
        />
      )}
      {!meta?.image_large && (
        <div className="absolute inset-0 bg-gradient-to-b from-zinc-800 to-zinc-950" />
      )}
      {/* Accent tint overlay — paints the hero in the card's colour */}
      <div
        className="absolute inset-0 mix-blend-overlay opacity-50"
        style={{
          background: `radial-gradient(ellipse at 50% 30%, var(--holo-accent, #fbbf24) 0%, transparent 70%)`,
        }}
      />
      {/* Gradient overlay — fades to black at bottom for smooth panel transition */}
      <div className="absolute inset-0 bg-gradient-to-b from-black/5 via-black/30 to-black/90" />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center pt-6 pb-5 px-4">
        {/* Card image — clickable for lightbox */}
        {meta?.image_small ? (
          <button
            type="button"
            onClick={onLightboxOpen}
            className="cursor-zoom-in transition-all duration-200 hover:scale-105 active:scale-95 focus:outline-none"
            aria-label="View full card image"
            title="Tap to enlarge"
          >
            <Image
              src={meta.image_small}
              alt={displayName}
              width={140}
              height={196}
              className="rounded-xl border border-white/10"
              style={{
                boxShadow: `0 8px 40px rgba(0,0,0,0.8), 0 0 60px var(--holo-accent, transparent), 0 0 0 1px var(--holo-accent, #fbbf24)40`,
              }}
              priority
            />
          </button>
        ) : (
          <div
            className="rounded-xl border border-dashed border-zinc-700 bg-zinc-900/50 flex items-center justify-center text-zinc-600 text-xs"
            style={{ width: 140, height: 196 }}
          >
            No image
          </div>
        )}

        {/* Card name + set */}
        <div className="mt-3 text-center max-w-xs">
          <h1
            className="text-xl font-bold text-white leading-tight drop-shadow-lg"
            style={{ fontFamily: 'var(--font-space, system-ui)' }}
          >
            {displayName}
          </h1>
          {setLabel && (
            <div className="text-[11px] text-zinc-400 mt-0.5 drop-shadow">{setLabel}</div>
          )}
          {meta?.rarity && (
            <div
              className="text-[10px] text-[var(--holo-accent,#fbbf24)] tracking-widest uppercase mt-0.5 drop-shadow"
              style={{ fontFamily: 'var(--font-space, system-ui)' }}
            >
              {meta.rarity}
            </div>
          )}
        </div>

        {/* Grade selector chips */}
        <div className="flex gap-1.5 mt-3">
          {(['raw', 'psa9', 'psa10'] as Grade[]).map((g) => (
            <GradeChip key={g} grade={g} onClick={() => onGradeChange(g)} active={grade === g} />
          ))}
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// Card Detail view — the hero screen
// ═══════════════════════════════════════════════════════════════════════════

function CardDetail({
  cardName,
  grade,
  onGradeChange,
  onClose,
  watchlist,
  onMetaReady,
}: {
  cardName: string
  grade: Grade
  onGradeChange: (g: Grade) => void
  onClose: () => void
  watchlist: ReturnType<typeof useWatchlist>
  onMetaReady?: (meta: CardMeta) => void
}) {
  const [range, setRange] = useState<TimeRange>('30')
  const [tab, setTab] = useState<Tab>('overview')
  const [history, setHistory] = useState<HistoryData | null>(null)
  const [grades, setGrades] = useState<GradesData | null>(null)
  const [signal, setSignal] = useState<SignalData | null>(null)
  const [salesFeed, setSalesFeed] = useState<SalesFeedData | null>(null)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [loadingSignal, setLoadingSignal] = useState(false)
  const [loadingGrades, setLoadingGrades] = useState(false)
  const [loadingSales, setLoadingSales] = useState(false)
  const [error, setError] = useState('')
  const [lightboxOpen, setLightboxOpen] = useState(false)

  const meta = history?.meta
  const theme = useCardTheme(meta?.image_small)
  const accent = theme.accent

  // Notify parent once meta is available so it can record recently viewed
  const onMetaReadyRef = useRef(onMetaReady)
  onMetaReadyRef.current = onMetaReady
  useEffect(() => {
    if (meta && onMetaReadyRef.current) onMetaReadyRef.current(meta)
  }, [meta])

  // Fetch chart when card/grade/range changes
  useEffect(() => {
    if (!cardName) return
    let cancelled = false
    setLoadingHistory(true)
    setError('')
    fetch(`${API_BASE}?action=history&card=${encodeURIComponent(cardName)}&grade=${grade}&days=${range}`)
      .then((r) => r.json())
      .then((d: HistoryData) => {
        if (cancelled) return
        if (d.error) setError(d.error)
        else setHistory(d)
      })
      .catch(() => !cancelled && setError('Network error'))
      .finally(() => !cancelled && setLoadingHistory(false))
    return () => { cancelled = true }
  }, [cardName, grade, range])

  // Fetch signal once per card+grade
  useEffect(() => {
    if (!cardName) return
    let cancelled = false
    setLoadingSignal(true)
    fetch(`${API_BASE}?action=signal&card=${encodeURIComponent(cardName)}&grade=${grade}`)
      .then((r) => r.json())
      .then((d: SignalData) => {
        if (cancelled) return
        if (!d.error) setSignal(d)
      })
      .finally(() => !cancelled && setLoadingSignal(false))
    return () => { cancelled = true }
  }, [cardName, grade])

  // Fetch grades comparison once per card
  useEffect(() => {
    if (!cardName) return
    let cancelled = false
    setLoadingGrades(true)
    fetch(`${API_BASE}?action=grades&card=${encodeURIComponent(cardName)}`)
      .then((r) => r.json())
      .then((d: GradesData) => { if (!cancelled && !d.error) setGrades(d) })
      .finally(() => !cancelled && setLoadingGrades(false))
    return () => { cancelled = true }
  }, [cardName])

  // Fetch sales when Sales tab becomes active
  useEffect(() => {
    if (tab !== 'sales' || !cardName) return
    let cancelled = false
    setLoadingSales(true)
    fetch(`${API_BASE}?action=sales&card=${encodeURIComponent(cardName)}&grade=${grade}&limit=30`)
      .then((r) => r.json())
      .then((d: SalesFeedData) => { if (!cancelled && !d.error) setSalesFeed(d) })
      .finally(() => !cancelled && setLoadingSales(false))
    return () => { cancelled = true }
  }, [tab, cardName, grade])

  const tone = deltaTone(history?.summary?.change_pct)
  const cmc = history?.summary.current
  const signalText = signal?.signal || ''
  const displayName = meta?.name || cardName

  return (
    <div
      className="animate-in fade-in duration-300 relative"
      style={{
        '--holo-accent': theme.accent,
        '--holo-glow': theme.glow,
        '--holo-deep': theme.deep,
      } as React.CSSProperties}
    >
      {/* Dramatic full-page card-driven takeover. Two stacked layers:
          1. A saturated base flood that re-colours the whole viewport.
          2. A brighter radial bloom anchored to the hero. */}
      {/* Dramatic full-page card-driven takeover. All layers render
          unconditionally with opacity controlled by theme.ready so the
          palette crossfades in smoothly (~900ms) instead of snapping to
          the new colour the moment the canvas sample finishes. The key
          on the outer fragment is `theme.hue` — when the user switches
          cards, React re-keys the layer set so the new palette animates
          in from 0 opacity, giving a soft crossfade between cards.

          The gradients now weave THREE extracted hues (accent / accent2 /
          accent3) so the page reads as a rich polychromatic field taken
          from the card, not a single flat hue. */}
      <div
        key={`takeover-${theme.hue}`}
        className="pointer-events-none fixed inset-0 -z-10"
        aria-hidden="true"
        style={{
          opacity: theme.ready ? 1 : 0,
          transition: 'opacity 900ms cubic-bezier(0.22, 1, 0.36, 1)',
        }}
      >
        {/* Layer 1: full-viewport saturated flood. Holds bgDeep through
            nearly half the viewport before easing to bgBase, so the card
            hue is present at every scroll position. */}
        <div
          className="absolute inset-0"
          style={{
            background: `linear-gradient(180deg, ${theme.bgDeep} 0%, ${theme.bgDeep} 45%, ${theme.bgBase} 100%)`,
          }}
        />
        {/* Layer 2: top bloom — primary hue dominates the upper half. */}
        <div
          className="absolute inset-0"
          style={{
            background: `
              radial-gradient(ellipse 180% 110% at 50% 0%, ${theme.accent}dd 0%, ${theme.accent}99 20%, ${theme.accent}55 45%, ${theme.accent}22 70%, transparent 95%),
              radial-gradient(ellipse 130% 110% at 50% 35%, ${theme.deep} 0%, transparent 65%)
            `,
            mixBlendMode: 'screen',
          }}
        />
        {/* Layer 3: bottom bloom — now tinted with the secondary hue so
            the bottom of the viewport reads as a related-but-different
            colour, not a mirror of the top. */}
        <div
          className="absolute inset-0"
          style={{
            background: `radial-gradient(ellipse 160% 95% at 50% 100%, ${theme.accent2}88 0%, ${theme.accent2}44 30%, ${theme.deep}aa 55%, transparent 90%)`,
            mixBlendMode: 'screen',
          }}
        />
        {/* Layer 4: corner accents — each quadrant gets a DIFFERENT hue,
            so the page feels like an actual palette taken from the card,
            not a wash. Primary top-left, secondary top-right + bottom-left,
            tertiary bottom-right. */}
        <div
          className="absolute inset-0"
          style={{
            background: `
              radial-gradient(circle 720px at 8% 22%, ${theme.accent}aa 0%, transparent 72%),
              radial-gradient(circle 680px at 92% 25%, ${theme.accent2}88 0%, transparent 72%),
              radial-gradient(circle 740px at 10% 80%, ${theme.accent2}66 0%, transparent 74%),
              radial-gradient(circle 820px at 92% 82%, ${theme.accent3}77 0%, transparent 74%),
              radial-gradient(circle 560px at 50% 50%, ${theme.accent}33 0%, transparent 82%)
            `,
            mixBlendMode: 'screen',
          }}
        />
        {/* Layer 5: conic swirl — slow rotating conic gradient woven
            through all three hues. Gives the background subtle
            "card-foil" iridescence without moving fast enough to
            distract. animation runs 60s/rev at 4% opacity. */}
        <div
          className="absolute inset-0 holo-conic-drift"
          style={{
            background: `conic-gradient(from 0deg at 50% 50%,
              ${theme.accent}22 0deg,
              ${theme.accent2}33 80deg,
              ${theme.accent3}22 160deg,
              ${theme.accent}22 240deg,
              ${theme.accent2}33 320deg,
              ${theme.accent}22 360deg)`,
            mixBlendMode: 'screen',
            opacity: 0.4,
          }}
        />
        {/* Layer 6: global colour-purity wash — every pixel picks up
            primary accent via screen blend (60% alpha). */}
        <div
          className="absolute inset-0"
          style={{
            background: `${theme.accent}99`,
            mixBlendMode: 'screen',
          }}
        />
        {/* Layer 7: mid-screen halo — fills the band between hero and
            first panel so nothing feels like a dead zone. */}
        <div
          className="absolute inset-x-0 top-[30vh] h-[60vh]"
          style={{
            background: `radial-gradient(ellipse 130% 80% at 50% 50%, ${theme.accent}55 0%, ${theme.accent3}33 50%, transparent 75%)`,
            mixBlendMode: 'screen',
          }}
        />
      </div>
          {/* Top-of-fold scrim — keeps the header legible when the accent
              bloom above is bright on warm hues. */}
      <div
        className="pointer-events-none fixed inset-x-0 top-0 h-[120px] -z-10"
        aria-hidden="true"
        style={{
          background: 'linear-gradient(180deg, rgba(0,0,0,0.55) 0%, transparent 100%)',
        }}
      />
      {/* Top bar */}
      <div className="flex items-center justify-between mb-3">
        <button
          type="button"
          onClick={onClose}
          className="flex items-center gap-2 px-4 py-2 rounded-full border border-zinc-600 bg-zinc-900/80 text-zinc-100 hover:border-[var(--holo-accent)] hover:text-[var(--holo-accent)] transition-all backdrop-blur-sm min-h-[44px]"
        >
          <span className="text-sm">←</span>
          <span style={{ fontFamily: 'var(--font-orbitron)', fontSize: 10, letterSpacing: '0.2em' }}>
            SEARCH
          </span>
        </button>
        <StarButton active={watchlist.has(cardName)} onClick={() => watchlist.toggle(cardName)} />
      </div>

      {/* Card hero with blurred background */}
      <CardHeader
        meta={meta}
        cardName={cardName}
        grade={grade}
        onGradeChange={onGradeChange}
        onLightboxOpen={() => setLightboxOpen(true)}
      />

      {/* Lightbox */}
      <Lightbox
        open={lightboxOpen}
        onClose={() => setLightboxOpen(false)}
        meta={meta}
        displayName={displayName}
      />

      {/* Hero price + delta — heavy frost glass with extra card-colour bleed */}
      <div
        className="border rounded-xl p-5"
        style={{
          background: 'linear-gradient(180deg, rgba(18,16,20,0.45) 0%, rgba(8,7,10,0.55) 100%)',
          borderColor: 'var(--holo-accent, #fbbf24)77',
          backdropFilter: 'blur(28px) saturate(1.8)',
          WebkitBackdropFilter: 'blur(28px) saturate(1.8)',
          boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.12), 0 10px 40px rgba(0,0,0,0.5), 0 0 60px var(--holo-accent, #fbbf24)44',
        }}
      >
        <div className="flex items-baseline justify-between mb-1">
          <div
            className="text-[10px] text-zinc-400 tracking-[0.2em] uppercase"
            style={{ fontFamily: 'var(--font-press-start, var(--font-orbitron))' }}
          >
            Latest Price
          </div>
          {loadingHistory ? <Spinner /> : null}
        </div>
        <div className="flex items-baseline gap-3 mt-1">
          <div
            className={`text-4xl sm:text-5xl font-bold tabular-nums ${toneText(tone)}`}
            style={{
              fontFamily: '"JetBrains Mono", "SF Mono", ui-monospace, monospace',
              textShadow: tone === 'flat' ? `0 0 24px var(--holo-glow, #fde68a)60` : undefined,
            }}
          >
            {money(cmc)}
          </div>
          {history && <DeltaChip value={history.summary.change_pct} size="md" />}
        </div>
        {history && (
          <div className="text-[11px] text-zinc-500 mt-1 tabular-nums">
            {money(history.summary.change)} over {range === '365' ? '1Y' : `${range}D`} · {history.summary.sales_count} sales
          </div>
        )}

        {/* Time range tabs */}
        <div className="grid grid-cols-4 gap-1 mt-4">
          {(['7', '30', '90', '365'] as TimeRange[]).map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => setRange(r)}
              className={`py-2 rounded text-[11px] font-semibold tracking-wider transition-all ${
                range === r
                  ? 'text-black shadow-[0_0_20px_var(--holo-accent)]'
                  : 'bg-zinc-900/60 text-zinc-500 border border-zinc-800 hover:text-zinc-200 hover:border-zinc-600'
              }`}
              style={{
                fontFamily: 'var(--font-space, system-ui)',
                background: range === r ? 'var(--holo-accent)' : undefined,
              }}
            >
              {r === '365' ? '1Y' : `${r}D`}
            </button>
          ))}
        </div>

        {/* Sparkline */}
        <div className="mt-4">
          {history && history.points.length > 1 ? (
            <div>
              {range === '365' && history.points.length < 20 && (
                <div className="flex items-center gap-2 px-3 py-1.5 mb-2 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
                  <span className="text-yellow-400 text-[10px]">⚠</span>
                  <span className="text-[10px] text-yellow-400/80">
                    Limited 1Y data — {history.points.length} data points available
                  </span>
                </div>
              )}
              {history.data_quality_warning && (
                <div
                  className="flex items-center gap-2 px-3 py-1.5 mb-2 bg-amber-500/10 border border-amber-500/30 rounded-lg"
                  role="note"
                  aria-label="Data quality warning"
                  title={history.data_quality_warning}
                >
                  <span aria-hidden className="text-amber-400 text-[10px]">⚠</span>
                  <span className="text-[10px] text-amber-300/90 leading-snug">
                    {history.data_quality_warning}
                  </span>
                </div>
              )}
              <Sparkline
                points={history.points}
                tone={tone}
                height={160}
                showDots
                accentColor={tone === 'flat' ? accent : undefined}
              />
            </div>
          ) : (
            <div className="h-40 flex items-center justify-center text-xs text-zinc-600">
              {loadingHistory ? <Spinner /> : error || 'No chart data'}
            </div>
          )}
        </div>

        {/* Hi/Lo/Open row */}
        {history && (
          <div className="grid grid-cols-3 gap-4 mt-3 pt-3 border-t border-zinc-800 tabular-nums">
            <StatCell label="High" value={money(history.summary.high)} />
            <StatCell label="Low" value={money(history.summary.low)} />
            <StatCell label="Open" value={money(history.summary.first)} />
          </div>
        )}
      </div>

      {/* Tab bar — desktop only (mobile uses bottom nav) */}
      <div className="hidden sm:flex gap-1 mt-4 border-b border-zinc-700/60 overflow-x-auto">
        {(['overview', 'sales', 'flip', 'grade'] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`flex-1 py-2.5 text-xs font-semibold tracking-wider uppercase border-b-2 transition-colors whitespace-nowrap min-h-[44px] ${
              tab === t
                ? 'text-[var(--holo-accent)] border-[var(--holo-accent)]'
                : 'text-zinc-400 border-transparent hover:text-zinc-100'
            }`}
            style={{ fontFamily: 'var(--font-space, system-ui)' }}
          >
            {t === 'grade' ? 'Grade It?' : t}
          </button>
        ))}
      </div>
      {/* Mobile: subtle pill showing current tab */}
      <div className="sm:hidden mt-4 text-[10px] tracking-[0.25em] uppercase text-[var(--holo-accent)] text-center"
           style={{ fontFamily: 'var(--font-space, system-ui)' }}>
        · {tab === 'grade' ? 'Grade It?' : tab} ·
      </div>

      {/* Tab content */}
      <div className="mt-4">
        {tab === 'overview' && (
          <OverviewTab
            signal={signal}
            loadingSignal={loadingSignal}
            grades={grades}
            loadingGrades={loadingGrades}
            currentGrade={grade}
            onGradeChange={onGradeChange}
            sources={history?.sources}
          />
        )}
        {tab === 'sales' && (
          <SalesTab feed={salesFeed} loading={loadingSales} grade={grade} />
        )}
        {tab === 'flip' && (
          <FlipTab cardName={cardName} grade={grade} signalText={signalText} market={cmc} />
        )}
        {tab === 'grade' && (
          <GradeItTab cardName={cardName} />
        )}
      </div>

      {/* Mobile bottom nav — fixed, safe-area padded */}
      <nav
        className="sm:hidden fixed inset-x-0 bottom-0 z-40 border-t border-zinc-800 backdrop-blur-xl"
        style={{
          paddingBottom: 'env(safe-area-inset-bottom, 0px)',
          background: 'linear-gradient(180deg, rgba(10,10,10,0.85) 0%, rgba(5,5,5,0.95) 100%)',
        }}
        aria-label="Sections"
      >
        <div className="grid grid-cols-4">
          {(['overview', 'sales', 'flip', 'grade'] as Tab[]).map((t) => {
            const active = tab === t
            const label = t === 'grade' ? 'Grade' : t === 'overview' ? 'Overview' : t === 'sales' ? 'Sales' : 'Flip'
            const icon =
              t === 'overview' ? 'M3 12l9-9 9 9M5 10v10h14V10'
              : t === 'sales' ? 'M3 3v18h18M7 15l4-4 4 4 5-7'
              : t === 'flip' ? 'M4 7h16M4 12h16M4 17h10'
              : 'M12 2l2.39 4.84L20 8l-4 3.9.94 5.5L12 14.77 7.06 17.4 8 11.9 4 8l5.61-1.16L12 2z'
            return (
              <button
                key={t}
                type="button"
                onClick={() => setTab(t)}
                className="flex flex-col items-center justify-center gap-1 py-2.5 min-h-[56px] transition-colors"
                style={{ color: active ? 'var(--holo-accent)' : '#a1a1aa' }}
                aria-label={label}
                aria-current={active ? 'page' : undefined}
              >
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d={icon} />
                </svg>
                <span className="text-[10px] tracking-wider uppercase" style={{ fontFamily: 'var(--font-space, system-ui)' }}>
                  {label}
                </span>
                {active && (
                  <span
                    className="absolute top-0 left-0 right-0 h-[2px]"
                    style={{ display: 'none' }}
                  />
                )}
              </button>
            )
          })}
        </div>
      </nav>
    </div>
  )
}

function StatCell({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div
        className="text-[9px] text-zinc-500 tracking-[0.2em] uppercase"
        style={{ fontFamily: 'var(--font-space, system-ui)' }}
      >
        {label}
      </div>
      <div className="text-sm font-semibold text-zinc-200 mt-0.5 tabular-nums">{value}</div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// Overview tab
// ═══════════════════════════════════════════════════════════════════════════

function signalToneClass(signal: string): string {
  const s = signal.toUpperCase()
  if (s.includes('STRONG BUY')) return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/40'
  if (s.includes('BUY')) return 'bg-emerald-500/5 text-emerald-300 border-emerald-500/20'
  if (s.includes('STRONG SELL')) return 'bg-red-500/10 text-red-400 border-red-500/40'
  if (s.includes('SELL')) return 'bg-orange-500/10 text-orange-300 border-orange-500/30'
  return 'bg-zinc-800/60 text-zinc-400 border-zinc-700'
}

function signalHint(signal: string): string {
  const s = signal.toUpperCase()
  if (s.includes('STRONG BUY')) return 'Price dipped with volume confirmation. Strong entry.'
  if (s.includes('BUY')) return 'Price below trend. Consider adding.'
  if (s.includes('STRONG SELL')) return 'Price overextended. Take profits.'
  if (s.includes('SELL')) return 'Price elevated. Consider trimming.'
  return 'No clear edge. Hold or wait.'
}

function OverviewTab({
  signal,
  loadingSignal,
  grades,
  loadingGrades,
  currentGrade,
  onGradeChange,
  sources,
}: {
  signal: SignalData | null
  loadingSignal: boolean
  grades: GradesData | null
  loadingGrades: boolean
  currentGrade: Grade
  onGradeChange: (g: Grade) => void
  sources: Source[] | undefined
}) {
  return (
    <div className="space-y-4">
      <Panel title="Trade Signal">
        {loadingSignal ? (
          <div className="py-4 text-center text-zinc-500 text-xs"><Spinner /></div>
        ) : signal ? (
          <>
            <div className="flex items-center justify-between gap-3">
              <div className={`px-3 py-1.5 rounded-lg border font-bold text-sm tracking-wider ${signalToneClass(signal.signal)}`}
                   style={{ fontFamily: 'var(--font-space, system-ui)' }}>
                {signal.signal}
              </div>
              {signal.rsi != null && (
                <div className="text-right">
                  <div className="text-[9px] tracking-[0.2em] uppercase text-zinc-500">RSI</div>
                  <div className={`text-sm font-bold tabular-nums ${
                    signal.rsi < 30 ? 'text-emerald-400' :
                    signal.rsi > 70 ? 'text-red-400' :
                    'text-zinc-300'
                  }`}>
                    {signal.rsi.toFixed(0)}
                  </div>
                </div>
              )}
            </div>
            <p className="text-xs text-zinc-400 mt-2 leading-relaxed">{signalHint(signal.signal)}</p>
            <div className="grid grid-cols-3 gap-3 mt-3 pt-3 border-t border-zinc-800 tabular-nums">
              <StatCell label="Current" value={money(signal.price)} />
              <StatCell label="30D Avg" value={money(signal.sma30 || 0)} />
              <StatCell label="vs Trend" value={pct(signal.dip_pct)} />
            </div>
          </>
        ) : (
          <div className="py-4 text-center text-zinc-500 text-xs">Signal unavailable</div>
        )}
      </Panel>

      <Panel title="Grade Comparison · 30-day">
        {loadingGrades ? (
          <div className="py-4 text-center"><Spinner /></div>
        ) : grades ? (
          <div className="space-y-2">
            {(['raw', 'psa9', 'psa10'] as Grade[]).map((g) => {
              const data = grades.grades[g]
              const active = g === currentGrade
              return (
                <button
                  key={g}
                  type="button"
                  onClick={() => onGradeChange(g)}
                  className={`w-full flex items-center justify-between p-3 rounded-lg border transition-all ${
                    active
                      ? 'bg-[var(--holo-accent)]/5 border-[var(--holo-accent)]/40'
                      : 'bg-zinc-900/50 border-zinc-800 hover:border-zinc-700'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <GradeChip grade={g} active={active} />
                    {data && !data.error && (
                      <span className="text-[10px] text-zinc-500">{data.sales_used} sales · {data.confidence}</span>
                    )}
                  </div>
                  <div className="text-right">
                    {data && !data.error ? (
                      <span className="text-base font-bold tabular-nums text-zinc-100">{money(data.cmc)}</span>
                    ) : (
                      <span className="text-xs text-zinc-600">No data</span>
                    )}
                  </div>
                </button>
              )
            })}
            {grades.grades.raw && grades.grades.psa10 && !grades.grades.raw.error && !grades.grades.psa10.error && (
              <div className="mt-3 pt-3 border-t border-zinc-800 flex justify-between items-baseline text-[11px]">
                <span className="text-zinc-500 tracking-wider uppercase">Grading Premium</span>
                <span className="text-cyan-300 font-semibold tabular-nums">
                  {((grades.grades.psa10.cmc / grades.grades.raw.cmc - 1) * 100).toFixed(0)}× over raw
                </span>
              </div>
            )}
          </div>
        ) : (
          <div className="py-4 text-center text-zinc-500 text-xs">Grade data unavailable</div>
        )}
      </Panel>

      <SourcesRow sources={sources} />
    </div>
  )
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div
      className="rounded-xl p-4 border"
      style={{
        background: 'linear-gradient(180deg, rgba(16,16,20,0.45) 0%, rgba(8,8,10,0.55) 100%)',
        borderColor: 'var(--holo-accent, rgba(255,255,255,0.14))44',
        backdropFilter: 'blur(26px) saturate(1.7)',
        WebkitBackdropFilter: 'blur(26px) saturate(1.7)',
        boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.1), 0 10px 36px rgba(0,0,0,0.45), 0 0 40px var(--holo-accent, #fbbf24)22',
      }}
    >
      <div
        className="text-[10px] text-zinc-300 tracking-[0.2em] uppercase mb-3"
        style={{ fontFamily: 'var(--font-space, system-ui)' }}
      >
        {title}
      </div>
      {children}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// Sales tab
// ═══════════════════════════════════════════════════════════════════════════

function SalesTab({ feed, loading, grade }: { feed: SalesFeedData | null; loading: boolean; grade: Grade }) {
  if (loading) return <div className="py-8 text-center"><Spinner /></div>
  if (!feed || feed.sales.length === 0) {
    return <div className="py-8 text-center text-xs text-zinc-500">No recent sales data</div>
  }

  return (
    <div
      className="border rounded-xl overflow-hidden"
      style={{
        background: 'linear-gradient(180deg, rgba(24,24,27,0.72) 0%, rgba(10,10,12,0.78) 100%)',
        borderColor: 'rgba(255,255,255,0.08)',
        backdropFilter: 'blur(22px) saturate(1.4)',
        WebkitBackdropFilter: 'blur(22px) saturate(1.4)',
        boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.08), 0 8px 32px rgba(0,0,0,0.4)',
      }}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-700/50">
        <div className="text-[10px] tracking-[0.2em] uppercase text-zinc-300"
             style={{ fontFamily: 'var(--font-space, system-ui)' }}>
          Recent Sold · <GradeChip grade={grade} /> <span className="ml-1">({feed.count} of {feed.total_available})</span>
        </div>
      </div>
      <div className="divide-y divide-zinc-800/60">
        {feed.sales.map((s, i) => (
          <a
            key={i}
            href={s.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between px-4 py-2.5 hover:bg-zinc-800/30 transition-colors"
          >
            <div className="flex flex-col">
              <span className="text-xs text-zinc-300 font-medium">{relativeDate(s.date)}</span>
              <span className="text-[10px] text-zinc-500 tracking-wider uppercase">
                {s.source_label} · {s.condition}
              </span>
            </div>
            <span className="text-sm font-bold tabular-nums text-zinc-100">{money(s.price)}</span>
          </a>
        ))}
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// Flip tab — P&L calculator with proper box/pack/single math
// ═══════════════════════════════════════════════════════════════════════════

function FlipTab({ cardName, grade, market }: { cardName: string; grade: Grade; signalText: string; market: number | undefined }) {
  const [cost, setCost] = useState('')
  const [method, setMethod] = useState('single')
  const [packs, setPacks] = useState('36')
  const [result, setResult] = useState<FlipData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const costPlaceholder =
    method === 'box' ? 'Box price ($)' :
    method === 'pack' ? 'Pack price ($)' :
    'Your cost ($)'

  async function run(e: FormEvent) {
    e.preventDefault()
    if (!cost) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const packsParam = method === 'box' ? `&packs=${encodeURIComponent(packs)}` : ''
      const r = await fetch(
        `${API_BASE}?action=flip&card=${encodeURIComponent(cardName)}&cost=${encodeURIComponent(cost)}&method=${method}&grade=${grade}${packsParam}`,
      )
      const d: FlipData = await r.json()
      if (d.error) setError(d.error)
      else setResult(d)
    } catch {
      setError('Network error')
    } finally {
      setLoading(false)
    }
  }

  const profit = result?.profit ?? null

  const costLabel =
    result?.method === 'box' ? `Per-pull cost (÷ ${result.packs ?? 36} packs)` :
    result?.method === 'pack' ? 'Pack cost' :
    'Your cost'

  return (
    <Panel title="Flip Calculator">
      <form onSubmit={run} className="space-y-2.5">
        <div className="grid grid-cols-2 gap-2">
          <input
            className="px-3 py-2.5 bg-zinc-900 border border-zinc-700 rounded-lg text-zinc-200 text-sm placeholder:text-zinc-600 outline-none focus:border-[var(--holo-accent)] tabular-nums transition-colors"
            type="number"
            step="0.01"
            inputMode="decimal"
            placeholder={costPlaceholder}
            value={cost}
            onChange={(e) => setCost(e.target.value)}
          />
          <select
            className="px-3 py-2.5 bg-zinc-900 border border-zinc-700 rounded-lg text-zinc-200 text-sm outline-none focus:border-[var(--holo-accent)] appearance-none transition-colors"
            value={method}
            onChange={(e) => { setMethod(e.target.value); setResult(null) }}
          >
            <option value="single">Bought Single</option>
            <option value="pack">Pulled from Pack</option>
            <option value="box">Pulled from Box</option>
          </select>
        </div>

        {/* Box-specific: packs per box input + live cost preview */}
        {method === 'box' && (
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <div className="flex-1">
                <label
                  className="text-[10px] text-zinc-500 tracking-widest uppercase block mb-1"
                  style={{ fontFamily: 'var(--font-space, system-ui)' }}
                >
                  Packs in box
                </label>
                <input
                  type="number"
                  value={packs}
                  onChange={(e) => setPacks(e.target.value)}
                  min="1"
                  max="100"
                  className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg text-zinc-200 text-sm outline-none focus:border-[var(--holo-accent)] tabular-nums transition-colors"
                />
              </div>
            </div>
            {cost && (
              <div className="text-[11px] text-zinc-400 tabular-nums px-1">
                {money(parseFloat(cost))} ÷ {packs} packs ={' '}
                <span className="text-[var(--holo-accent)] font-semibold">
                  {money(parseFloat(cost) / Math.max(1, parseInt(packs) || 36))} per pull
                </span>
              </div>
            )}
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !cost}
          className="w-full py-2.5 font-bold text-xs tracking-[0.25em] uppercase rounded-lg hover:opacity-90 transition-opacity disabled:opacity-30"
          style={{
            background: 'var(--holo-accent, #fbbf24)',
            color: '#000',
            fontFamily: 'var(--font-orbitron)',
          }}
        >
          {loading ? 'Calculating…' : `Calculate at ${money(market)}`}
        </button>
      </form>

      {error && <div className="mt-3 px-3 py-2 text-xs text-red-400 bg-red-500/10 rounded-lg">{error}</div>}

      {result && (
        <div className="mt-4 space-y-2">
          <div className={`text-center py-3 rounded-lg border font-bold text-sm tracking-wider ${
            result.verdict.includes('FLIP') ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/40' :
            result.verdict.includes('HOLD') ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/40' :
            'bg-red-500/10 text-red-400 border-red-500/40'
          }`} style={{ fontFamily: 'var(--font-orbitron)' }}>
            {result.verdict}
          </div>
          {result.data_quality_warning && (
            <div
              className="flex items-start gap-2 px-3 py-2 rounded-lg border border-amber-500/40 bg-amber-500/10 text-amber-300 text-[11px] leading-snug"
              style={{ fontFamily: 'var(--font-space, system-ui)' }}
              role="note"
              aria-label="Data quality warning"
            >
              <span aria-hidden className="mt-[1px]">⚠</span>
              <span>{result.data_quality_warning}</span>
            </div>
          )}
          <div className="space-y-1 text-sm tabular-nums">
            <Row label="Market comp" value={money(result.cmc)} />
            <Row label={costLabel} value={`−${money(result.cost_basis)}`} />
            {result.method === 'box' && result.raw_cost && (
              <Row label="Box investment" value={money(result.raw_cost)} />
            )}
            <Row label={`Platform fees (${Math.round((result.platform_fee / result.cmc) * 100)}%)`} value={`−${money(result.platform_fee)}`} />
            <Row label={`Shipping (${result.shipping_type})`} value={`−${money(result.shipping_cost)}`} />
            <div className="flex justify-between py-2 border-t border-[var(--holo-accent)]/30 mt-1">
              <span
                className="text-xs font-bold uppercase tracking-wider"
                style={{ color: 'var(--holo-accent)', fontFamily: 'var(--font-space, system-ui)' }}
              >
                Net profit
              </span>
              <span className={`text-base font-bold tabular-nums ${deltaTone(profit) === 'up' ? 'text-emerald-400' : 'text-red-400'}`}>
                {profit != null && profit > 0 ? '+' : ''}{money(profit)} ({pct(result.margin_pct)})
              </span>
            </div>
            <Row label="Break-even" value={money(result.break_even)} />
          </div>
        </div>
      )}
    </Panel>
  )
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between items-baseline py-1 border-b border-zinc-800/50 last:border-0 text-sm">
      <span className="text-[11px] text-zinc-500 tracking-wide" style={{ fontFamily: 'var(--font-space, system-ui)' }}>{label}</span>
      <span className="font-semibold tabular-nums text-zinc-200">{value}</span>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// Should I Grade It? tab
// ═══════════════════════════════════════════════════════════════════════════

type GradingService = 'psa_value' | 'psa_regular' | 'psa_express' | 'cgc_standard' | 'cgc_express' | 'tag_grading'

const SERVICE_LABELS: Record<GradingService, string> = {
  psa_value: 'PSA Value · $25 · 45d',
  psa_regular: 'PSA Regular · $75 · 10d',
  psa_express: 'PSA Express · $150 · 5d',
  cgc_standard: 'CGC Standard · $18 · 30d',
  cgc_express: 'CGC Express · $35 · 7d',
  tag_grading: 'TAG Grading · $20 · 20d',
}

function GradeItTab({ cardName }: { cardName: string }) {
  const [service, setService] = useState<GradingService>('psa_value')
  const [p10, setP10] = useState('0.35')
  const [p9, setP9] = useState('0.45')
  const [data, setData] = useState<GradeROIData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!cardName) return
    let cancelled = false
    setLoading(true)
    setError('')
    const url = `${API_BASE}?action=gradeit&card=${encodeURIComponent(cardName)}&service=${service}&p10=${p10}&p9=${p9}`
    fetch(url)
      .then((r) => r.json())
      .then((d: GradeROIData) => {
        if (cancelled) return
        if (d.error) setError(d.error)
        else setData(d)
      })
      .catch(() => !cancelled && setError('Network error'))
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [cardName, service, p10, p9])

  const verdictClass =
    data?.verdict_tone === 'buy' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/40' :
    data?.verdict_tone === 'sell' ? 'bg-red-500/10 text-red-400 border-red-500/40' :
    'bg-yellow-500/10 text-yellow-400 border-yellow-500/40'

  return (
    <Panel title="Should I Grade It? · Expected Value">
      <div className="mb-3">
        <label className="text-[10px] text-zinc-500 tracking-[0.15em] uppercase block mb-1.5"
               style={{ fontFamily: 'var(--font-space, system-ui)' }}>
          Grading Service
        </label>
        <select
          className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg text-zinc-200 text-xs outline-none focus:border-[var(--holo-accent)] appearance-none transition-colors"
          value={service}
          onChange={(e) => setService(e.target.value as GradingService)}
        >
          {(Object.keys(SERVICE_LABELS) as GradingService[]).map((k) => (
            <option key={k} value={k}>{SERVICE_LABELS[k]}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-2 mb-4">
        <div>
          <label className="text-[10px] text-zinc-500 tracking-[0.15em] uppercase block mb-1"
                 style={{ fontFamily: 'var(--font-space, system-ui)' }}>
            PSA 10 Odds
          </label>
          <div className="relative">
            <input
              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg text-zinc-200 text-xs outline-none focus:border-cyan-400 tabular-nums transition-colors"
              type="number"
              step="0.05"
              min="0"
              max="1"
              value={p10}
              onChange={(e) => setP10(e.target.value)}
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-zinc-500 tabular-nums pointer-events-none">
              {(parseFloat(p10) * 100).toFixed(0)}%
            </span>
          </div>
        </div>
        <div>
          <label className="text-[10px] text-zinc-500 tracking-[0.15em] uppercase block mb-1"
                 style={{ fontFamily: 'var(--font-space, system-ui)' }}>
            PSA 9 Odds
          </label>
          <div className="relative">
            <input
              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg text-zinc-200 text-xs outline-none focus:border-purple-400 tabular-nums transition-colors"
              type="number"
              step="0.05"
              min="0"
              max="1"
              value={p9}
              onChange={(e) => setP9(e.target.value)}
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-zinc-500 tabular-nums pointer-events-none">
              {(parseFloat(p9) * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>

      {loading && !data && <div className="py-6 text-center"><Spinner /></div>}
      {error && <div className="px-3 py-2 text-xs text-red-400 bg-red-500/10 rounded-lg">{error}</div>}

      {data && (
        <div className="space-y-3">
          <div className={`text-center py-4 px-3 rounded-lg border font-bold text-lg tracking-wider ${verdictClass}`}
               style={{ fontFamily: 'var(--font-orbitron)' }}>
            {data.verdict}
            <div className="text-[11px] font-normal tracking-normal mt-1.5 opacity-90 leading-relaxed px-2"
                 style={{ fontFamily: 'var(--font-space, system-ui)' }}>
              {data.rationale}
            </div>
          </div>

          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <div className="text-[10px] text-zinc-500 tracking-[0.2em] uppercase mb-1"
                 style={{ fontFamily: 'var(--font-space, system-ui)' }}>
              Net EV vs Selling Raw
            </div>
            <div className="flex items-baseline justify-between">
              <div className={`text-2xl font-bold tabular-nums ${
                data.breakdown.delta > 0 ? 'text-emerald-400' :
                data.breakdown.delta < 0 ? 'text-red-400' :
                'text-zinc-300'
              }`}>
                {data.breakdown.delta > 0 ? '+' : ''}{money(data.breakdown.delta)}
              </div>
              <DeltaChip value={data.breakdown.delta_pct} size="md" />
            </div>
          </div>

          <div className="space-y-0.5 text-sm tabular-nums">
            <div className="text-[10px] text-zinc-500 tracking-[0.2em] uppercase mb-1.5"
                 style={{ fontFamily: 'var(--font-space, system-ui)' }}>
              Expected Revenue Breakdown
            </div>
            <Row label={`PSA 10 @ ${(data.assumptions.p10 * 100).toFixed(0)}%`} value={money(data.breakdown.expected_psa10_value)} />
            <Row label={`PSA 9 @ ${(data.assumptions.p9 * 100).toFixed(0)}%`} value={money(data.breakdown.expected_psa9_value)} />
            <Row label={`Sub / Returned @ ${(data.assumptions.p_sub * 100).toFixed(0)}%`} value={money(data.breakdown.expected_sub_value)} />
            <div className="flex justify-between py-1.5 border-t border-zinc-700 mt-1 text-sm">
              <span className="text-[11px] text-zinc-400 font-bold uppercase tracking-wider"
                    style={{ fontFamily: 'var(--font-space, system-ui)' }}>
                Expected Revenue
              </span>
              <span className="font-bold tabular-nums text-zinc-100">{money(data.breakdown.expected_revenue)}</span>
            </div>
            <Row label="Grading + shipping" value={`−${money(data.breakdown.total_cost)}`} />
            <div className="flex justify-between py-1.5 border-t border-[var(--holo-accent)]/30 mt-1">
              <span className="text-[11px] font-bold uppercase tracking-wider"
                    style={{ color: 'var(--holo-accent)', fontFamily: 'var(--font-space, system-ui)' }}>
                Net EV (Graded)
              </span>
              <span className="text-base font-bold tabular-nums text-zinc-100">{money(data.breakdown.net_ev)}</span>
            </div>
            <div className="flex justify-between py-1 text-xs">
              <span className="text-zinc-500">Baseline (sell raw)</span>
              <span className="tabular-nums text-zinc-400">{money(data.breakdown.raw_baseline)}</span>
            </div>
          </div>

          <div className="text-[10px] text-zinc-600 text-center pt-2 border-t border-zinc-800">
            Based on current comps:{' '}
            {data.prices.raw && <span className="text-zinc-400">Raw {money(data.prices.raw.cmc)}</span>}
            {' · '}{data.prices.psa9 && <span className="text-purple-400">PSA 9 {money(data.prices.psa9.cmc)}</span>}
            {' · '}{data.prices.psa10 && <span className="text-cyan-400">PSA 10 {money(data.prices.psa10.cmc)}</span>}
          </div>
        </div>
      )}
    </Panel>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// Top Movers — auto-scrolling marquee of the biggest 7-day price movers.
// Data comes from /api?action=movers (curated universe of ~12 liquid cards,
// ranked by |change_pct|). Direction colours the delta chip emerald/red.
// ═══════════════════════════════════════════════════════════════════════════

interface MoverItem {
  card: string
  name: string
  number: string
  current: number
  change_pct: number
  direction: 'up' | 'down'
  image_small: string
  sales_count: number
}

interface MoversResponse {
  window_days: number
  count: number
  movers: MoverItem[]
  error?: string
}

interface RecentItem {
  card: string
  name: string
  image_small: string
}

function TopMovers({ onOpen }: { onOpen: (name: string) => void }) {
  const [movers, setMovers] = useState<MoverItem[] | null>(null)
  const [error, setError] = useState(false)
  const [paused, setPaused] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const scrollerRef = React.useRef<HTMLDivElement | null>(null)
  const dragStateRef = React.useRef<{ active: boolean; startX: number; startScroll: number; moved: boolean }>({
    active: false, startX: 0, startScroll: 0, moved: false,
  })
  const [offset, setOffset] = React.useState(0)
  const rafRef = React.useRef<number | null>(null)
  const lastTsRef = React.useRef<number>(0)

  useEffect(() => {
    let cancelled = false
    fetch(`${API_BASE}?action=movers&limit=10&window=7`)
      .then((r) => r.json())
      .then((d: MoversResponse) => {
        if (cancelled) return
        if (d.error || !d.movers || d.movers.length === 0) {
          setError(true)
          return
        }
        setMovers(d.movers)
      })
      .catch(() => { if (!cancelled) setError(true) })
    return () => { cancelled = true }
  }, [])

  if (error) {
    return null // Silently hide if backend failed — homepage stays functional.
  }

  // Skeleton while loading — 8 placeholder cards
  const displayList: MoverItem[] = movers ?? Array.from({ length: 8 }, (_, i) => ({
    card: `__skeleton_${i}`,
    name: '',
    number: '',
    current: 0,
    change_pct: 0,
    direction: 'up' as const,
    image_small: '',
    sales_count: 0,
  }))

  // Gentle auto-scroll of the native scroller, pauses on hover/touch/drag.
  useEffect(() => {
    const el = scrollerRef.current
    if (!el || !movers) return
    let active = true
    const tick = (ts: number) => {
      if (!active) return
      if (!lastTsRef.current) lastTsRef.current = ts
      const dt = ts - lastTsRef.current
      lastTsRef.current = ts
      if (!paused && !dragStateRef.current.active) {
        const max = el.scrollWidth - el.clientWidth
        if (max > 0) {
          const next = el.scrollLeft + dt * 0.04 // ~40px/s
          if (next >= max - 1) el.scrollLeft = 0
          else el.scrollLeft = next
        }
      }
      rafRef.current = window.requestAnimationFrame(tick)
    }
    rafRef.current = window.requestAnimationFrame(tick)
    return () => {
      active = false
      if (rafRef.current) window.cancelAnimationFrame(rafRef.current)
      lastTsRef.current = 0
    }
  }, [paused, movers])

  const onPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    const el = scrollerRef.current
    if (!el) return
    dragStateRef.current = { active: true, startX: e.clientX, startScroll: el.scrollLeft, moved: false }
    setPaused(true)
    try { (e.target as Element).setPointerCapture?.(e.pointerId) } catch {}
  }
  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const s = dragStateRef.current
    if (!s.active) return
    const el = scrollerRef.current
    if (!el) return
    const dx = e.clientX - s.startX
    if (Math.abs(dx) > 4) s.moved = true
    el.scrollLeft = s.startScroll - dx
    setOffset(el.scrollLeft)
  }
  const onPointerUp = () => {
    dragStateRef.current.active = false
    // brief delay before resuming auto-scroll for nicer feel
    window.setTimeout(() => setPaused(false), 600)
  }

  return (
    <div className="mt-7">
      <div className="flex items-center justify-between mb-3 px-1">
        <h2
          className="text-[10px] text-zinc-300 tracking-[0.25em] uppercase flex items-center gap-2"
          style={{ fontFamily: 'var(--font-press-start, var(--font-orbitron))' }}
        >
          <span
            className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_currentColor]"
            aria-hidden="true"
          />
          Top Movers · 7D
        </h2>
        <button
          type="button"
          onClick={() => movers && setExpanded(true)}
          disabled={!movers}
          className="text-[9px] text-[#F5C518] hover:text-[#FFE27A] tracking-widest uppercase transition-colors disabled:opacity-40 px-2 py-1 rounded border border-[#F5C518]/30 hover:border-[#F5C518]/70"
          style={{ fontFamily: 'var(--font-space, system-ui)' }}
        >
          View all
        </button>
      </div>

      <div
        className="relative -mx-4"
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}
      >
        <div className="pointer-events-none absolute inset-y-0 left-0 w-8 z-10 bg-gradient-to-r from-black to-transparent" />
        <div className="pointer-events-none absolute inset-y-0 right-0 w-8 z-10 bg-gradient-to-l from-black to-transparent" />

        <div
          ref={scrollerRef}
          className="flex gap-3 py-2 px-4 overflow-x-auto no-scrollbar touch-pan-x select-none"
          style={{ scrollbarWidth: 'none', cursor: dragStateRef.current.active ? 'grabbing' : 'grab' }}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          onPointerLeave={() => { if (dragStateRef.current.active) onPointerUp() }}
        >
          {displayList.map((mover, idx) => {
            const isSkeleton = mover.card.startsWith('__skeleton_')
            const up = mover.direction === 'up'
            return (
              <button
                key={`${mover.card}-${idx}`}
                type="button"
                onClick={(e) => {
                  if (dragStateRef.current.moved) { e.preventDefault(); return }
                  if (!isSkeleton) onOpen(mover.card)
                }}
                disabled={isSkeleton}
                className="shrink-0 flex flex-col items-center gap-1.5 group"
                style={{ width: 88 }}
                aria-label={isSkeleton ? 'Loading' : `${mover.name} ${up ? 'up' : 'down'} ${Math.abs(mover.change_pct)}%`}
              >
                <div
                  className="relative rounded-xl overflow-hidden border border-zinc-700 group-hover:border-[#F5C518] group-hover:scale-105 group-hover:shadow-[0_0_28px_#F5C51899] transition-all duration-200"
                  style={{ width: 88, height: 122 }}
                >
                  {isSkeleton ? (
                    <div className="w-full h-full bg-zinc-800/60 animate-pulse" />
                  ) : mover.image_small ? (
                    <Image
                      src={mover.image_small}
                      alt={mover.name}
                      width={88}
                      height={122}
                      className="w-full h-full object-cover pointer-events-none"
                      draggable={false}
                    />
                  ) : (
                    <div className="w-full h-full bg-zinc-800 flex items-center justify-center text-xl font-bold text-zinc-500">
                      {mover.name[0] || '?'}
                    </div>
                  )}
                  {!isSkeleton && (
                    <div
                      className={`absolute top-1 right-1 px-1.5 py-0.5 rounded text-[9px] font-bold tabular-nums shadow-lg backdrop-blur-sm ${
                        up ? 'bg-emerald-500/95 text-black' : 'bg-red-500/95 text-white'
                      }`}
                      style={{ fontFamily: 'var(--font-space, system-ui)' }}
                    >
                      {up ? '▲' : '▼'} {Math.abs(mover.change_pct).toFixed(1)}%
                    </div>
                  )}
                </div>
                <span
                  className="text-[10px] text-zinc-300 text-center leading-tight w-full group-hover:text-[#F5C518] transition-colors tracking-wide line-clamp-2 min-h-[1.8em]"
                  style={{ fontFamily: 'var(--font-space, system-ui)' }}
                >
                  {mover.name || '\u00a0'}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      <MoversModal
        open={expanded}
        movers={movers || []}
        onClose={() => setExpanded(false)}
        onOpen={(c) => { setExpanded(false); onOpen(c) }}
      />

      <style jsx>{`
        .no-scrollbar::-webkit-scrollbar { display: none; }
      `}</style>
      {/* silence unused-offset lint — triggers re-render on drag for cursor */}
      <span className="hidden" aria-hidden="true">{offset}</span>
    </div>
  )
}

function MoversModal({
  open, movers, onClose, onOpen,
}: {
  open: boolean
  movers: MoverItem[]
  onClose: () => void
  onOpen: (card: string) => void
}) {
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', handler)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  if (!open) return null
  return ReactDOM.createPortal(
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-6"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="All top movers"
    >
      <div className="absolute inset-0 bg-black/85 backdrop-blur-md" />
      <div
        className="relative z-10 w-full sm:max-w-2xl max-h-[90vh] bg-[#0a0a0a] border border-[#F5C518]/30 rounded-t-2xl sm:rounded-2xl shadow-[0_0_60px_rgba(245,197,24,0.2)] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
          <h3
            className="text-[11px] text-[#F5C518] tracking-[0.25em] uppercase"
            style={{ fontFamily: 'var(--font-press-start, var(--font-orbitron))' }}
          >
            Top Movers · 7D
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="w-11 h-11 flex items-center justify-center rounded-full border border-zinc-700 text-zinc-300 hover:text-white hover:border-zinc-500"
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        <div className="overflow-y-auto p-4 grid grid-cols-2 sm:grid-cols-3 gap-3">
          {movers.map((m) => {
            const up = m.direction === 'up'
            return (
              <button
                key={m.card}
                type="button"
                onClick={() => onOpen(m.card)}
                className="flex items-center gap-3 p-2 bg-zinc-900/70 border border-zinc-800 hover:border-[#F5C518] rounded-xl text-left transition-colors min-h-[96px]"
              >
                <div className="relative w-[60px] h-[84px] shrink-0 rounded-lg overflow-hidden border border-zinc-800">
                  {m.image_small ? (
                    <Image src={m.image_small} alt={m.name} width={60} height={84} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full bg-zinc-800" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-xs text-zinc-100 font-medium leading-tight line-clamp-2">{m.name}</div>
                  <div className="text-[10px] text-zinc-400 mt-0.5 tabular-nums">{money(m.current)}</div>
                  <div className={`mt-1 inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold tabular-nums ${
                    up ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' : 'bg-red-500/20 text-red-300 border border-red-500/40'
                  }`}>
                    {up ? '▲' : '▼'} {Math.abs(m.change_pct).toFixed(1)}%
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      </div>
    </div>,
    document.body
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// Recently Viewed row
// ═══════════════════════════════════════════════════════════════════════════

function RecentlyViewed({ items, onOpen }: { items: RecentItem[]; onOpen: (card: string) => void }) {
  const scrollerRef = React.useRef<HTMLDivElement | null>(null)
  const dragStateRef = React.useRef<{ active: boolean; startX: number; startScroll: number; moved: boolean }>({
    active: false, startX: 0, startScroll: 0, moved: false,
  })
  const [, forceUpdate] = React.useState(0)

  if (items.length === 0) return null

  const onPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    const el = scrollerRef.current
    if (!el) return
    dragStateRef.current = { active: true, startX: e.clientX, startScroll: el.scrollLeft, moved: false }
    forceUpdate((n) => n + 1)
    try { (e.target as Element).setPointerCapture?.(e.pointerId) } catch {}
  }
  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const s = dragStateRef.current
    if (!s.active) return
    const el = scrollerRef.current
    if (!el) return
    const dx = e.clientX - s.startX
    if (Math.abs(dx) > 4) s.moved = true
    el.scrollLeft = s.startScroll - dx
  }
  const onPointerUp = () => {
    dragStateRef.current.active = false
    forceUpdate((n) => n + 1)
  }

  return (
    <div className="mt-7">
      <div className="flex items-center mb-3 px-1">
        <h2
          className="text-[10px] text-zinc-300 tracking-[0.25em] uppercase flex items-center gap-2"
          style={{ fontFamily: 'var(--font-press-start, var(--font-orbitron))' }}
        >
          <span
            className="inline-block w-1.5 h-1.5 rounded-full bg-violet-400 shadow-[0_0_8px_currentColor]"
            aria-hidden="true"
          />
          Recently Viewed
        </h2>
      </div>

      <div className="relative -mx-4">
        <div className="pointer-events-none absolute inset-y-0 left-0 w-8 z-10 bg-gradient-to-r from-black to-transparent" />
        <div className="pointer-events-none absolute inset-y-0 right-0 w-8 z-10 bg-gradient-to-l from-black to-transparent" />

        <div
          ref={scrollerRef}
          className="flex gap-3 py-2 px-4 overflow-x-auto no-scrollbar touch-pan-x select-none"
          style={{ scrollbarWidth: 'none', cursor: dragStateRef.current.active ? 'grabbing' : 'grab' }}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          onPointerLeave={() => { if (dragStateRef.current.active) onPointerUp() }}
        >
          {items.map((item, idx) => (
            <button
              key={`${item.card}-${idx}`}
              type="button"
              onClick={(e) => {
                if (dragStateRef.current.moved) { e.preventDefault(); return }
                onOpen(item.card)
              }}
              className="shrink-0 flex flex-col items-center gap-1.5 group"
              style={{ width: 88 }}
              aria-label={item.name}
            >
              <div
                className="relative rounded-xl overflow-hidden border border-zinc-700 group-hover:border-violet-400 group-hover:scale-105 group-hover:shadow-[0_0_28px_rgba(167,139,250,0.5)] transition-all duration-200"
                style={{ width: 88, height: 122 }}
              >
                {item.image_small ? (
                  <Image
                    src={item.image_small}
                    alt={item.name}
                    width={88}
                    height={122}
                    className="w-full h-full object-cover pointer-events-none"
                    draggable={false}
                  />
                ) : (
                  <div className="w-full h-full bg-zinc-800 flex items-center justify-center text-xl font-bold text-zinc-500">
                    {item.name?.[0] || '?'}
                  </div>
                )}
              </div>
              <span
                className="text-[10px] text-zinc-400 text-center leading-tight w-full group-hover:text-violet-300 transition-colors tracking-wide line-clamp-2 min-h-[1.8em]"
                style={{ fontFamily: 'var(--font-space, system-ui)' }}
              >
                {item.name}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// Watchlist
// ═══════════════════════════════════════════════════════════════════════════

function WatchlistRow({ name, onOpen, onRemove }: { name: string; onOpen: () => void; onRemove: () => void }) {
  const [data, setData] = useState<PriceData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    fetch(`${API_BASE}?action=price&card=${encodeURIComponent(name)}&grade=raw`)
      .then((r) => r.json())
      .then((d: PriceData) => { if (!cancelled) setData(d.error ? null : d) })
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [name])

  return (
    <div className="flex items-center bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden hover:border-zinc-700 transition-colors">
      <button
        type="button"
        onClick={onOpen}
        className="flex-1 flex items-center justify-between px-3 py-3 hover:bg-zinc-800/30 transition-colors text-left"
      >
        <div className="flex-1 min-w-0">
          <div
            className="text-sm text-zinc-100 font-medium truncate capitalize"
            style={{ fontFamily: 'var(--font-space, system-ui)' }}
          >
            {name}
          </div>
          {data ? (
            <div className="text-[10px] text-zinc-400 mt-0.5">
              {data.sales_used} sales · {data.confidence}
            </div>
          ) : loading ? (
            <div className="text-[10px] text-zinc-600 mt-0.5">Loading…</div>
          ) : (
            <div className="text-[10px] text-zinc-600 mt-0.5">No data</div>
          )}
        </div>
        <div className="text-right ml-3">
          {data ? (
            <>
              <div className="text-sm font-bold tabular-nums text-zinc-100">{money(data.cmc)}</div>
              <div className="mt-0.5">
                <DeltaChip value={data.delta_pct} />
              </div>
            </>
          ) : loading ? <Spinner /> : null}
        </div>
      </button>
      <button
        type="button"
        onClick={onRemove}
        className="px-3 self-stretch text-zinc-600 hover:text-red-400 transition-colors text-sm border-l border-zinc-800"
        aria-label="Remove from watchlist"
      >
        ×
      </button>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// Home view
// ═══════════════════════════════════════════════════════════════════════════

interface SearchResult {
  id: string
  name: string
  number: string
  set_name: string
  set_series: string
  release_date: string
  release_year: number
  image_small: string
  rarity: string
  supertype: string
}

function highlightMatch(text: string, term: string): React.ReactNode {
  if (!term) return text
  const lc = text.toLowerCase()
  const idx = lc.indexOf(term.toLowerCase())
  if (idx < 0) return text
  return (
    <>
      {text.slice(0, idx)}
      <mark style={{ background: 'transparent', color: '#FFE27A' }}>
        {text.slice(idx, idx + term.length)}
      </mark>
      {text.slice(idx + term.length)}
    </>
  )
}

type HomeTab = 'home' | 'movers' | 'watchlist' | 'search'

function HomeView({
  onOpen,
  watchlist,
  recentlyViewed,
}: {
  onOpen: (card: string) => void
  watchlist: ReturnType<typeof useWatchlist>
  recentlyViewed: ReturnType<typeof useRecentlyViewed>
}) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  const [activeTab, setActiveTab] = useState<HomeTab>('home')
  const [pulseMovers, setPulseMovers] = useState<MoverItem[] | null>(null)

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const inputRef = useRef<HTMLInputElement | null>(null)
  const searchHeroRef = useRef<HTMLDivElement | null>(null)
  const moversRef = useRef<HTMLDivElement | null>(null)
  const watchlistRef = useRef<HTMLDivElement | null>(null)
  const recentRef = useRef<HTMLDivElement | null>(null)
  const listboxId = 'holo-search-listbox'

  // Lightweight market pulse for the top chip — reuses the movers endpoint.
  useEffect(() => {
    let cancelled = false
    fetch(`${API_BASE}?action=movers&limit=10&window=7`)
      .then((r) => r.json())
      .then((d: MoversResponse) => {
        if (cancelled) return
        if (d?.movers && d.movers.length > 0) setPulseMovers(d.movers)
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [])

  function scrollToRef(ref: React.RefObject<HTMLDivElement | null>) {
    const el = ref.current
    if (!el) return
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  function focusSearch() {
    scrollToRef(searchHeroRef)
    // Defer focus so the scroll has started; mobile browsers handle this fine.
    setTimeout(() => inputRef.current?.focus(), 120)
  }

  function onTab(t: HomeTab) {
    setActiveTab(t)
    if (t === 'search') {
      focusSearch()
    } else if (t === 'movers') {
      scrollToRef(moversRef)
    } else if (t === 'watchlist') {
      scrollToRef(watchlistRef)
    } else {
      scrollToRef(searchHeroRef)
    }
  }

  const topPulse = pulseMovers && pulseMovers.length > 0 ? pulseMovers[0] : null

  const trimmedMatchTerm = useMemo(() => {
    const t = query.trim()
    // Strip trailing number token for highlight purposes.
    const m = t.match(/^(.*?)[\s]+\d{1,4}$/)
    return (m ? m[1] : t).trim()
  }, [query])

  // Debounced fetch.
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    const trimmed = query.trim()
    if (trimmed.length < 2) {
      setResults([])
      setLoading(false)
      setOpen(false)
      setHighlightedIndex(-1)
      if (abortRef.current) abortRef.current.abort()
      return
    }
    debounceRef.current = setTimeout(() => {
      if (abortRef.current) abortRef.current.abort()
      const ctrl = new AbortController()
      abortRef.current = ctrl
      setLoading(true)
      fetch(`${API_BASE}?action=search&q=${encodeURIComponent(trimmed)}&limit=12`, { signal: ctrl.signal })
        .then((r) => r.json())
        .then((data) => {
          if (ctrl.signal.aborted) return
          const list: SearchResult[] = Array.isArray(data?.results) ? data.results.slice(0, 12) : []
          setResults(list)
          setOpen(true)
          setHighlightedIndex(-1)
          setLoading(false)
        })
        .catch(() => {
          if (ctrl.signal.aborted) return
          setResults([])
          setOpen(false)
          setLoading(false)
        })
    }, 250)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [query])

  // Cleanup on unmount.
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
      if (abortRef.current) abortRef.current.abort()
    }
  }, [])

  // Click-outside to close.
  useEffect(() => {
    function onDocDown(e: MouseEvent) {
      if (!containerRef.current) return
      if (!containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onDocDown)
    return () => document.removeEventListener('mousedown', onDocDown)
  }, [])

  function selectResult(r: SearchResult) {
    const canonical = r.number ? `${r.name} ${r.number}` : r.name
    setOpen(false)
    setQuery(canonical)
    onOpen(canonical)
  }

  function handleSearch(e: FormEvent) {
    e.preventDefault()
    if (highlightedIndex >= 0 && results[highlightedIndex]) {
      selectResult(results[highlightedIndex])
      return
    }
    if (query.trim()) onOpen(query.trim())
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'ArrowDown') {
      if (!open && results.length > 0) setOpen(true)
      if (results.length === 0) return
      e.preventDefault()
      setHighlightedIndex((i) => (i + 1) % results.length)
    } else if (e.key === 'ArrowUp') {
      if (results.length === 0) return
      e.preventDefault()
      setHighlightedIndex((i) => (i <= 0 ? results.length - 1 : i - 1))
    } else if (e.key === 'Escape') {
      if (open) {
        e.preventDefault()
        setOpen(false)
        setHighlightedIndex(-1)
        inputRef.current?.focus()
      }
    } else if (e.key === 'Tab') {
      setOpen(false)
    }
  }

  const showDropdown =
    open && query.trim().length >= 2 && (results.length > 0 || !loading)
  const activeDescendant =
    highlightedIndex >= 0 ? `holo-option-${highlightedIndex}` : undefined
  const announcement = loading
    ? ''
    : query.trim().length >= 2
      ? results.length === 0
        ? 'no matches'
        : `${results.length} ${results.length === 1 ? 'match' : 'matches'}`
      : ''

  return (
    <div className="relative">
      {/* Ambient gold glow — Ultra Ball energy */}
      <div
        className="pointer-events-none fixed inset-x-0 top-0 h-[480px] -z-0 opacity-70"
        aria-hidden="true"
        style={{
          background: 'radial-gradient(ellipse 85% 70% at 50% 0%, rgba(245,197,24,0.32) 0%, rgba(245,197,24,0.12) 32%, transparent 72%)',
        }}
      />

      {/* Big decorative ultra ball — sits behind the search, subtle */}
      <div
        className="pointer-events-none absolute -top-8 -right-6 opacity-[0.12] hidden sm:block"
        aria-hidden="true"
      >
        <Pokeball size={260} />
      </div>

      {/* Market pulse chip — sits above the search hero. Gives an immediate
          "market is alive" cue before the user does anything. */}
      <div
        className="relative z-30 mb-3 flex items-center justify-between gap-3 px-3 py-2 rounded-full border backdrop-blur-sm"
        style={{
          background: 'linear-gradient(180deg, rgba(20,18,10,0.7) 0%, rgba(10,8,4,0.75) 100%)',
          borderColor: 'rgba(245,197,24,0.22)',
        }}
        aria-label="Market status"
      >
        <div className="flex items-center gap-2 min-w-0">
          <span
            className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_currentColor]"
            aria-hidden="true"
          />
          <span
            className="text-[9px] text-zinc-200 tracking-[0.25em] uppercase"
            style={{ fontFamily: 'var(--font-space, system-ui)' }}
          >
            Market · Live
          </span>
        </div>
        {topPulse ? (
          <button
            type="button"
            onClick={() => onOpen(topPulse.card)}
            className="min-w-0 flex items-center gap-1.5 text-[11px] truncate"
            style={{ fontFamily: 'var(--font-space, system-ui)' }}
            aria-label={`Open ${topPulse.name}`}
          >
            <span
              className="tabular-nums font-semibold"
              style={{ color: topPulse.direction === 'up' ? '#34d399' : '#f87171' }}
            >
              {topPulse.direction === 'up' ? '\u25B2' : '\u25BC'} {topPulse.change_pct >= 0 ? '+' : ''}
              {topPulse.change_pct.toFixed(1)}%
            </span>
            <span className="text-zinc-300 truncate">{topPulse.name}</span>
          </button>
        ) : (
          <span className="text-[10px] text-zinc-600 tracking-[0.2em] uppercase" style={{ fontFamily: 'var(--font-space, system-ui)' }}>
            Syncing
          </span>
        )}
      </div>

      {/* Search hero — elevated z so the autocomplete dropdown paints above
          TopMovers (which creates its own stacking context via transforms
          on the drag scroller). Without this the marquee card images punch
          through the dropdown on mobile. */}
      <div
        ref={searchHeroRef}
        className="relative z-40 backdrop-blur-md border rounded-2xl p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.08),0_8px_32px_rgba(0,0,0,0.55)]"
        style={{
          background: 'linear-gradient(180deg, rgba(28,24,14,0.8) 0%, rgba(12,10,6,0.85) 100%)',
          borderColor: 'rgba(245,197,24,0.3)',
        }}
      >
        <div className="flex items-center gap-2 mb-3">
          <Pokeball size={18} />
          <div
            className="text-[10px] text-zinc-200 tracking-[0.25em] uppercase"
            style={{ fontFamily: 'var(--font-press-start, var(--font-orbitron))' }}
          >
            Card Lookup
          </div>
        </div>
        <form onSubmit={handleSearch}>
          <div
            ref={containerRef}
            className="relative"
            role="combobox"
            aria-expanded={showDropdown}
            aria-controls={listboxId}
            aria-haspopup="listbox"
            aria-owns={listboxId}
          >
            <div className="relative">
              <input
                ref={inputRef}
                className="w-full px-4 py-3 pr-10 bg-black/70 border border-zinc-700 rounded-lg text-zinc-50 text-base placeholder:text-zinc-500 outline-none focus:border-[#F5C518] focus:shadow-[0_0_26px_rgba(245,197,24,0.32)] transition-all"
                type="text"
                placeholder="Card name + number — e.g. Umbreon ex 161"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onFocus={() => {
                  if (results.length > 0) setOpen(true)
                }}
                onKeyDown={onKeyDown}
                autoComplete="off"
                autoCapitalize="off"
                role="combobox"
                aria-autocomplete="list"
                aria-controls={listboxId}
                aria-expanded={showDropdown}
                aria-activedescendant={activeDescendant}
                style={{ fontFamily: 'var(--font-space, system-ui)' }}
              />
              {loading && (
                <span
                  aria-hidden="true"
                  className="absolute right-3 top-1/2 -translate-y-1/2 inline-block w-4 h-4 rounded-full border-2 border-zinc-600 border-t-[#F5C518] animate-spin"
                />
              )}
            </div>

            <span aria-live="polite" className="sr-only">
              {announcement}
            </span>

            {showDropdown && (
              <ul
                id={listboxId}
                role="listbox"
                className="absolute left-0 right-0 top-full mt-2 z-[60] rounded-xl backdrop-blur-xl border overflow-y-auto shadow-[inset_0_1px_0_rgba(255,255,255,0.1),0_20px_60px_rgba(0,0,0,0.75)]"
                style={{
                  background: 'linear-gradient(180deg, rgba(20,16,6,0.96) 0%, rgba(8,6,2,0.98) 100%)',
                  borderColor: 'rgba(245,197,24,0.4)',
                  maxHeight: '60vh',
                  animation: 'holoSearchFade 140ms ease-out',
                }}
              >
                {results.length === 0 ? (
                  <li
                    role="option"
                    aria-selected="false"
                    className="px-4 py-3 text-sm text-zinc-400"
                    style={{ fontFamily: 'var(--font-space, system-ui)' }}
                  >
                    No matches
                  </li>
                ) : (
                  results.map((r, idx) => {
                    const isActive = idx === highlightedIndex
                    const metaLine = [
                      r.set_name,
                      r.set_series,
                      r.release_year ? String(r.release_year) : '',
                      r.rarity,
                    ]
                      .filter(Boolean)
                      .join(' · ')
                    return (
                      <li
                        key={`${r.id}-${idx}`}
                        id={`holo-option-${idx}`}
                        role="option"
                        aria-selected={isActive}
                        onMouseEnter={() => setHighlightedIndex(idx)}
                        onMouseDown={(e) => {
                          // Prevent input blur before click.
                          e.preventDefault()
                        }}
                        onClick={() => selectResult(r)}
                        className="flex items-center gap-3 px-3 py-2 cursor-pointer transition-colors border-l-2"
                        style={{
                          minHeight: 60,
                          background: isActive ? 'rgba(245,197,24,0.08)' : 'transparent',
                          borderLeftColor: isActive ? '#F5C518' : 'transparent',
                        }}
                      >
                        <div
                          className="shrink-0 overflow-hidden rounded-sm bg-black/40"
                          style={{ width: 40, height: 56 }}
                        >
                          {r.image_small ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              src={r.image_small}
                              alt=""
                              width={40}
                              height={56}
                              loading="lazy"
                              style={{ width: 40, height: 56, objectFit: 'cover' }}
                            />
                          ) : null}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div
                            className="text-sm text-zinc-50 font-semibold truncate"
                            style={{ fontFamily: 'var(--font-space, system-ui)' }}
                          >
                            {highlightMatch(r.name, trimmedMatchTerm)}
                            {r.number ? (
                              <span className="text-zinc-400 font-normal"> · {r.number}</span>
                            ) : null}
                          </div>
                          {metaLine && (
                            <div
                              className="text-[10px] text-zinc-500 tracking-[0.12em] uppercase truncate mt-0.5"
                              style={{ fontFamily: 'var(--font-space, system-ui)' }}
                            >
                              {metaLine}
                            </div>
                          )}
                        </div>
                      </li>
                    )
                  })
                )}
              </ul>
            )}
          </div>

          <button
            type="submit"
            disabled={!query.trim()}
            className="w-full mt-3 py-3 font-bold text-xs tracking-[0.3em] uppercase rounded-lg hover:brightness-110 active:scale-[0.99] transition-all disabled:opacity-30 disabled:cursor-not-allowed shadow-[0_0_28px_rgba(245,197,24,0.45)]"
            style={{
              background: 'linear-gradient(135deg, #FFE27A 0%, #F5C518 45%, #C99608 100%)',
              color: '#0a0a0a',
              fontFamily: 'var(--font-press-start, var(--font-orbitron))',
              textShadow: '0 1px 0 rgba(255,255,255,0.2)',
            }}
          >
            Lookup
          </button>
        </form>
        <style jsx>{`
          @keyframes holoSearchFade {
            from { opacity: 0; transform: translateY(-4px); }
            to   { opacity: 1; transform: translateY(0); }
          }
        `}</style>
      </div>

      {/* Watchlist */}
      <div ref={watchlistRef}>
        {watchlist.list.length > 0 ? (
          <div className="mt-6">
            <div className="flex items-center justify-between mb-2">
              <h2
                className="text-[11px] text-zinc-500 tracking-[0.2em] uppercase"
                style={{ fontFamily: 'var(--font-space, system-ui)' }}
              >
                Watchlist
              </h2>
              <span className="text-[11px] text-zinc-600 tabular-nums">{watchlist.list.length}</span>
            </div>
            <div className="space-y-2">
              {watchlist.list.map((name) => (
                <WatchlistRow key={name} name={name} onOpen={() => onOpen(name)} onRemove={() => watchlist.remove(name)} />
              ))}
            </div>
          </div>
        ) : (
          <div className="mt-6 px-4 py-6 border border-dashed border-zinc-800 rounded-xl text-center">
            <p className="text-xs text-zinc-500" style={{ fontFamily: 'var(--font-space, system-ui)' }}>
              Star a card on its detail page to add to your watchlist.
            </p>
          </div>
        )}
      </div>

      {/* Top movers — auto-scroll marquee */}
      <div ref={moversRef}>
        <TopMovers onOpen={onOpen} />
      </div>

      {/* Recently viewed — last 10 cards, persisted in localStorage */}
      <div ref={recentRef}>
        <RecentlyViewed items={recentlyViewed.list} onOpen={onOpen} />
      </div>

      {/* Extra bottom spacing so the persistent mobile nav doesn't clip content */}
      <div className="h-20 sm:hidden" aria-hidden="true" />

      {/* Persistent mobile bottom nav — mirrors CardDetail's pattern. */}
      <nav
        className="sm:hidden fixed inset-x-0 bottom-0 z-40 border-t border-zinc-800 backdrop-blur-xl"
        style={{
          paddingBottom: 'env(safe-area-inset-bottom, 0px)',
          background: 'linear-gradient(180deg, rgba(10,10,10,0.85) 0%, rgba(5,5,5,0.95) 100%)',
        }}
        aria-label="Home sections"
      >
        <div className="grid grid-cols-4">
          {(['home', 'movers', 'watchlist', 'search'] as HomeTab[]).map((t) => {
            const active = activeTab === t
            const label = t === 'home' ? 'Home' : t === 'movers' ? 'Movers' : t === 'watchlist' ? 'Watchlist' : 'Search'
            const icon =
              t === 'home' ? 'M3 12l9-9 9 9M5 10v10h14V10'
              : t === 'movers' ? 'M3 17l6-6 4 4 8-8M14 7h7v7'
              : t === 'watchlist' ? 'M12 2l2.39 4.84L20 8l-4 3.9.94 5.5L12 14.77 7.06 17.4 8 11.9 4 8l5.61-1.16L12 2z'
              : 'M11 19a8 8 0 100-16 8 8 0 000 16zM21 21l-4.35-4.35'
            return (
              <button
                key={t}
                type="button"
                onClick={() => onTab(t)}
                className="flex flex-col items-center justify-center gap-1 py-2.5 min-h-[56px] transition-colors"
                style={{ color: active ? '#F5C518' : '#a1a1aa' }}
                aria-label={label}
                aria-current={active ? 'page' : undefined}
              >
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d={icon} />
                </svg>
                <span className="text-[10px] tracking-wider uppercase" style={{ fontFamily: 'var(--font-space, system-ui)' }}>
                  {label}
                </span>
              </button>
            )
          })}
        </div>
      </nav>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// Root
// ═══════════════════════════════════════════════════════════════════════════

export default function HoloPage() {
  const [cardName, setCardName] = useState<string>('')
  const [grade, setGrade] = useState<Grade>('raw')
  const watchlist = useWatchlist()
  const recentlyViewed = useRecentlyViewed()

  const handleMetaReady = useCallback((meta: CardMeta) => {
    recentlyViewed.add({ card: cardName, name: meta.name, image_small: meta.image_small })
  }, [cardName, recentlyViewed])

  return (
    <div
      className="min-h-dvh text-zinc-100 relative"
      style={{
        fontFamily: 'var(--font-space, system-ui)',
        isolation: 'isolate',
      }}
    >
      {/* Permanent base — sits behind everything so card-driven takeover
          layers (rendered at -z-10 inside CardDetail) paint above this but
          below content. Without this, removing the root bg would leak body. */}
      <div
        className="pointer-events-none fixed inset-0 -z-20"
        aria-hidden="true"
        style={{
          background: 'radial-gradient(ellipse at top, #14110a 0%, #0a0a0a 55%, #050505 100%)',
        }}
      />
      <div className="max-w-md mx-auto px-4 py-5 sm:max-w-xl sm:px-6 sm:py-8 pb-24 sm:pb-8">
        {/* Brand header */}
        <header className="flex items-center justify-between mb-5 gap-3">
          <div className="flex items-center gap-3 group">
            {/* Ultra Ball logo mark — front and center. Floats gently, spins on hover. */}
            <div className="shrink-0 holo-ball-float group-hover:holo-ball-spin cursor-pointer" onClick={() => setCardName('')}>
              <Pokeball size={56} />
            </div>
            <div>
              <h1
                className="text-5xl leading-none"
                style={{
                  fontFamily: 'var(--font-display), Georgia, serif',
                  fontWeight: 900,
                  fontStyle: 'italic',
                  fontVariationSettings: '"opsz" 144, "SOFT" 30, "WONK" 1',
                  background: 'linear-gradient(135deg, #FFE27A 0%, #F5C518 50%, #C99608 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text',
                  letterSpacing: '-0.03em',
                  filter: 'drop-shadow(0 0 22px rgba(245,197,24,0.55))',
                }}
              >
                Holo
              </h1>
              <p
                className="text-[8px] text-zinc-400 tracking-[0.3em] uppercase mt-1.5"
                style={{ fontFamily: 'var(--font-space, system-ui)' }}
              >
                Pokémon TCG · Price Intelligence
              </p>
            </div>
          </div>
          {cardName && (
            <div
              className="text-[9px] text-[#F5C518] tracking-[0.2em] uppercase flex items-center gap-1.5"
              style={{ fontFamily: 'var(--font-space, system-ui)' }}
            >
              <span
                className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_currentColor]"
                aria-hidden="true"
              />
              Market · Live
            </div>
          )}
        </header>

        {cardName ? (
          <CardDetail
            cardName={cardName}
            grade={grade}
            onGradeChange={setGrade}
            onClose={() => setCardName('')}
            watchlist={watchlist}
            onMetaReady={handleMetaReady}
          />
        ) : (
          <HomeView onOpen={(c) => setCardName(c)} watchlist={watchlist} recentlyViewed={recentlyViewed} />
        )}

        <footer
          className="text-center py-8 mt-8 text-[9px] text-zinc-500 tracking-[0.2em] uppercase"
          style={{ fontFamily: 'var(--font-space, system-ui)' }}
        >
          HOLO · PriceCharting · eBay · TCGPlayer
        </footer>
      </div>

      <style jsx global>{`
        @keyframes holo-float {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-3px) rotate(-3deg); }
        }
        @keyframes holo-spin-once {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
        .holo-ball-float { animation: holo-float 4s ease-in-out infinite; transition: transform 0.3s; }
        .holo-ball-float:hover { animation: holo-spin-once 0.9s ease-in-out; }
        @keyframes holo-conic-drift {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
        .holo-conic-drift {
          animation: holo-conic-drift 120s linear infinite;
          transform-origin: 50% 50%;
          will-change: transform;
        }
        @media (prefers-reduced-motion: reduce) {
          .holo-conic-drift { animation: none; }
          .holo-ball-float  { animation: none; }
        }
      `}</style>
    </div>
  )
}
