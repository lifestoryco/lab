// ─── Shared Math Helpers ────────────────────────────────────────────────────

function hash2d(ix: number, iy: number): number {
  let n = (((ix * 374761393) + (iy * 668265263)) >>> 0)
  n = (((n ^ (n >>> 13)) * 1274126177) >>> 0) & 0x7fffffff
  return n / 0x7fffffff
}

function noise2d(x: number, y: number): number {
  const ix = Math.floor(x) & 255
  const iy = Math.floor(y) & 255
  const fx = x - Math.floor(x)
  const fy = y - Math.floor(y)
  const ux = fx * fx * (3 - 2 * fx)
  const uy = fy * fy * (3 - 2 * fy)
  const a = hash2d(ix, iy)
  const b = hash2d(ix + 1, iy)
  const c = hash2d(ix, iy + 1)
  const d = hash2d(ix + 1, iy + 1)
  return a + ux * (b - a) + uy * (c - a + ux * (a - b - c + d))
}

function fbm6(x: number, y: number): number {
  let v = 0, amp = 0.5, freq = 1.0
  for (let i = 0; i < 6; i++) {
    v += amp * noise2d(x * freq, y * freq)
    freq *= 2
    amp *= 0.5
  }
  return v
}

function fbm4(x: number, y: number): number {
  let v = 0, amp = 0.5, freq = 1.0
  for (let i = 0; i < 4; i++) {
    v += amp * noise2d(x * freq, y * freq)
    freq *= 2
    amp *= 0.5
  }
  return v
}

function pymod(a: number, b: number): number {
  return ((a % b) + b) % b
}

function clamp01(v: number): number {
  return Math.max(0, Math.min(1, v))
}

function cc(v: number): number {
  return Math.max(0, Math.min(255, Math.round(v)))
}

function smin(a: number, b: number, k = 0.1): number {
  const h = Math.max(k - Math.abs(a - b), 0) / k
  return Math.min(a, b) - h * h * k * 0.25
}

// ─── Types ───────────────────────────────────────────────────────────────────

export interface GridState {
  [k: string]: unknown
}

export interface Archetype {
  name: string
  reflection: string
  vibe: string
  frames: number
  tStep: number
  // Standard: per-pixel function
  pixel?: (nx: number, ny: number, t: number) => number
  // Grid: state-based
  init?: (w: number, h: number) => GridState
  update?: (s: GridState, t: number, frame: number, w: number, h: number) => void
  gridPixel?: (s: GridState, x: number, y: number) => number
  // Shared palette
  palette: (val: number, t: number) => readonly [number, number, number]
}

// ─── 22 Archetypes ───────────────────────────────────────────────────────────

export const ARCHETYPES: Archetype[] = [
  // 1. chrysalis — KEEPER (9/10)
  {
    name: 'chrysalis',
    reflection: 'The cosmic mirror unfolds.',
    vibe: 'Chrysanthemum machine elves',
    frames: 150,
    tStep: 0.30,
    pixel(nx, ny, t) {
      const speed = 1.0
      const rDist = Math.sqrt(nx * nx + ny * ny)
      let theta = Math.atan2(ny, nx)
      const angleFold = (2 * Math.PI) / 8
      theta = pymod(theta, angleFold) - angleFold / 2
      const fx = rDist * Math.cos(theta)
      const fy = rDist * Math.sin(theta)
      const v = Math.sin(fx * 20 - t * speed * 2) * Math.cos(fy * 20 + t * speed)
      return (v + 1) / 2
    },
    palette(val, t) {
      const r = cc((Math.sin(val * Math.PI + t) * 0.5 + 0.5) * 255)
      const g = cc((Math.sin(val * Math.PI + t + 2.0) * 0.5 + 0.5) * 200)
      const b = cc((Math.sin(val * Math.PI + t + 4.0) * 0.5 + 0.5) * 255)
      return [r, g, b] as const
    },
  },

  // 2. zazen — endless ensō (rebuilt 2026-04-22)
  {
    name: 'zazen',
    reflection: 'One stroke, without beginning.',
    vibe: 'Endless ensō breath',
    frames: 240,
    tStep: 0.04,
    pixel(nx, ny, t) {
      const r = Math.sqrt(nx * nx + ny * ny)
      const theta = Math.atan2(ny, nx)
      const R = 0.78 + Math.sin(t * 0.18) * 0.018
      const speed = 0.55
      const brushAngle = t * speed
      let phase = (brushAngle - theta) % (Math.PI * 2)
      if (phase < 0) phase += Math.PI * 2
      const freshness = 1 - phase / (Math.PI * 2)
      const thickness = 0.09 * (0.5 + 0.55 * freshness) + 0.03 * Math.sin(phase * 2.3 + 0.5)
      const dr = r - R
      const radial = Math.exp(-(dr * dr) / (thickness * thickness + 0.0005))
      const dryBrush = 0.82 + 0.18 * Math.sin(phase * 9 + brushAngle * 2)
      const fade = Math.pow(freshness, 0.78)
      let val = radial * fade * dryBrush
      const grain = 0.02 * noise2d(nx * 4 + t * 0.015, ny * 4)
      val += grain * (1 - radial)
      return clamp01(val)
    },
    palette(val, _t) {
      const v = Math.pow(val, 0.85)
      const r = cc(v * 248 + (1 - v) * 9)
      const g = cc(v * 240 + (1 - v) * 8)
      const b = cc(v * 220 + (1 - v) * 7)
      return [r, g, b] as const
    },
  },

  // 3. spore — KEEPER (10/10)
  {
    name: 'spore',
    reflection: 'Mycelial network awareness.',
    vibe: 'Bioluminescent forest breathing',
    frames: 150,
    tStep: 0.10,
    pixel(nx, ny, t) {
      const speed = 1.0
      const scale = 1 + Math.sin(t * speed * 0.5) * 0.2
      const sx = nx * 1.5 * scale
      const sy = ny * 1.5 * scale
      const v1 = Math.sin(sx + t * speed)
      const v2 = Math.cos(sy + Math.sin(sx * 0.5 - t * speed * 0.5))
      const v3 = Math.sin(Math.sqrt(sx * sx + sy * sy) * 3 - t * speed)
      return ((v1 + v2 + v3) / 3 + 1) / 2
    },
    palette(val, t) {
      const r = cc((Math.sin(val * Math.PI + t + 4) * 0.4 + 0.4) * 180)
      const g = cc((Math.sin(val * Math.PI + t * 0.5) * 0.5 + 0.5) * 255)
      const b = cc((Math.sin(val * Math.PI - t) * 0.5 + 0.5) * 255)
      return [r, g, b] as const
    },
  },

  // 4. wavefunction — KEEPER (9/10)
  {
    name: 'wavefunction',
    reflection: 'Probability collapses into being.',
    vibe: 'Quantum superposition shimmer',
    frames: 100,
    tStep: 0.10,
    pixel(nx, ny, t) {
      const speed = 1.2
      const angle1 = Math.atan2(ny - Math.sin(t * speed * 0.3), nx - Math.cos(t * speed * 0.2))
      const angle2 = Math.atan2(ny + Math.cos(t * speed * 0.4), nx + Math.sin(t * speed * 0.5))
      const d1 = Math.sqrt((nx - Math.cos(t * speed * 0.2)) ** 2 + (ny - Math.sin(t * speed * 0.3)) ** 2)
      const d2 = Math.sqrt((nx + Math.sin(t * speed * 0.5)) ** 2 + (ny + Math.cos(t * speed * 0.4)) ** 2)
      const v1 = Math.sin(angle1 * 5 + d1 * 4 - t * speed)
      const v2 = Math.cos(angle2 * 5 - d2 * 4 + t * speed * 0.7)
      const v3 = Math.sin(d1 * d2 * 3 + t * speed * 0.3)
      return (v1 * v2 + v3 + 2) / 4
    },
    palette(val, t) {
      const base = val * val
      const r = cc(80 + 120 * Math.sin(base * 6.28 + t * 0.6 + 3.8))
      const g = cc(100 + 130 * Math.sin(base * 6.28 + t * 0.6 + 4.2))
      const b = cc(160 + 95 * Math.sin(base * 6.28 + t * 0.6 + 5.0))
      return [r, g, b] as const
    },
  },

  // 5. ouroboros — serpent eating its tail, forever (rebuilt 2026-04-22)
  {
    name: 'ouroboros',
    reflection: 'The serpent devours its own light.',
    vibe: 'Serpent swallows its tail',
    frames: 240,
    tStep: 0.05,
    pixel(nx, ny, t) {
      const r = Math.sqrt(nx * nx + ny * ny)
      const theta = Math.atan2(ny, nx)
      const headAng = -Math.PI / 2
      let rel = headAng - theta
      while (rel < 0) rel += 2 * Math.PI
      while (rel >= 2 * Math.PI) rel -= 2 * Math.PI
      const R = 0.78
      const T_BASE = 0.11
      const headBulge = Math.exp(-(rel * rel) / 0.07) * 0.045
      const tailTaper = 1 - Math.pow(rel / (Math.PI * 2), 7)
      const thickness = (T_BASE + headBulge) * tailTaper
      const dr = r - R
      const body = thickness > 0.001
        ? Math.exp(-(dr * dr) / (thickness * thickness + 1e-5))
        : 0
      const scalePhase = rel * 24 - t * 2.2
      const scales = 0.38 * (0.5 + 0.5 * Math.sin(scalePhase))
      const spine = 0.3 * Math.exp(-(dr * dr) / 0.0008)
      const eyeR = R - 0.025
      const eyeX = eyeR * Math.cos(headAng)
      const eyeY = eyeR * Math.sin(headAng)
      const eyeDist2 = (nx - eyeX) ** 2 + (ny - eyeY) ** 2
      const socket = Math.exp(-eyeDist2 / 0.0025)
      const pupil = Math.exp(-eyeDist2 / 0.00015)
      let val = body * (0.62 + scales + spine * 0.35)
      val = val * (1 - socket * 0.85) + pupil * 0.95
      return clamp01(val)
    },
    palette(val, _t) {
      const v = val
      const r = cc(Math.pow(v, 0.9) * 255)
      const g = cc(Math.pow(Math.max(0, v - 0.35), 1.5) * 310)
      const b = cc(Math.pow(Math.max(0, v - 0.65), 2.2) * 200)
      return [r, g, b] as const
    },
  },

  // 6. drift — PALETTE REWORK (was flat green; now warm amber/umber with drama)
  {
    name: 'drift',
    reflection: 'Deep temporal illusion.',
    vibe: 'Hazy slow-motion drift',
    frames: 200,
    tStep: 0.035,
    pixel(nx, ny, t) {
      const speed = 0.9
      // Double-nested domain warping for compounding distortion
      const w1x = Math.sin(ny * 2.2 + t * speed * 0.8) * 1.6
      const w1y = Math.cos(nx * 1.7 - t * speed * 0.7) * 1.6
      const w2x = Math.sin((nx + w1x) * 1.5 + t * speed * 0.4) * 0.9
      const w2y = Math.cos((ny + w1y) * 1.4 - t * speed * 0.5) * 0.9
      const warpX = nx * 1.25 + w1x + w2x
      const warpY = ny * 1.25 + w1y + w2y
      const v1 = Math.sin(warpX * warpY * 0.8 + t * speed)
      const v2 = Math.cos((warpX + warpY) * 1.1 - t * speed * 0.6)
      const breath = 0.7 + 0.3 * Math.sin(t * 0.15)
      return ((v1 + v2 * 0.6) * breath + 1.5) / 3
    },
    palette(val, t) {
      // Warm amber → umber → dusty rose — high contrast
      const v = Math.pow(val, 0.8)
      const shift = Math.sin(t * 0.12) * 0.15
      const r = cc(30 + 225 * v * (0.8 + shift))
      const g = cc(15 + 130 * v * v + 40 * v * Math.sin(t * 0.2 + v * 3))
      const b = cc(25 + 80 * Math.pow(Math.max(0, v - 0.4), 1.8) + 35 * v)
      return [r, g, b] as const
    },
  },

  // 7. morphic — BOID MURMURATION (rebuilt: flock of birds at dusk)
  {
    name: 'morphic',
    reflection: 'No leader. No plan. Something that looks like mind.',
    vibe: 'Flock of birds, one intention',
    frames: 240,
    tStep: 0.05,
    init(w, h) {
      const N = 240
      const agents: Array<{ x: number; y: number; vx: number; vy: number }> = []
      for (let i = 0; i < N; i++) {
        const a = Math.random() * 2 * Math.PI
        agents.push({
          x: Math.random() * w,
          y: Math.random() * h,
          vx: Math.cos(a) * 0.6,
          vy: Math.sin(a) * 0.6,
        })
      }
      const field = new Float32Array(w * h)
      return { agents, field, w, h }
    },
    update(s, t, _frame, w, h) {
      const state = s as {
        agents: Array<{ x: number; y: number; vx: number; vy: number }>
        field: Float32Array
        w: number
        h: number
      }
      const { agents, field } = state
      // Decay field (trails)
      for (let i = 0; i < field.length; i++) field[i] *= 0.88
      // Spatial bucketing
      const bucketSize = 10
      const bw = Math.ceil(w / bucketSize)
      const bh = Math.ceil(h / bucketSize)
      const buckets: number[][] = new Array(bw * bh)
      for (let i = 0; i < buckets.length; i++) buckets[i] = []
      for (let i = 0; i < agents.length; i++) {
        const bx = Math.min(bw - 1, Math.max(0, Math.floor(agents[i].x / bucketSize)))
        const by = Math.min(bh - 1, Math.max(0, Math.floor(agents[i].y / bucketSize)))
        buckets[by * bw + bx].push(i)
      }
      // Slow attractor that drifts around
      const attX = w * (0.5 + 0.25 * Math.sin(t * 0.12))
      const attY = h * (0.5 + 0.25 * Math.cos(t * 0.09))
      const VIEW = 14
      const SEP = 5
      const MAX_V = 1.1
      for (let i = 0; i < agents.length; i++) {
        const a = agents[i]
        let sepX = 0, sepY = 0, aliX = 0, aliY = 0, cohX = 0, cohY = 0
        let neighbors = 0, sepCount = 0
        const bxI = Math.min(bw - 1, Math.max(0, Math.floor(a.x / bucketSize)))
        const byI = Math.min(bh - 1, Math.max(0, Math.floor(a.y / bucketSize)))
        for (let dby = -1; dby <= 1; dby++) {
          for (let dbx = -1; dbx <= 1; dbx++) {
            const bi = (byI + dby) * bw + (bxI + dbx)
            if (bi < 0 || bi >= buckets.length) continue
            const bucket = buckets[bi]
            for (let k = 0; k < bucket.length; k++) {
              const j = bucket[k]
              if (j === i) continue
              const b = agents[j]
              const dx = b.x - a.x
              const dy = b.y - a.y
              const d2 = dx * dx + dy * dy
              if (d2 < VIEW * VIEW) {
                aliX += b.vx; aliY += b.vy
                cohX += b.x; cohY += b.y
                neighbors++
                if (d2 < SEP * SEP && d2 > 0.01) {
                  const d = Math.sqrt(d2)
                  sepX -= dx / d; sepY -= dy / d
                  sepCount++
                }
              }
            }
          }
        }
        if (neighbors > 0) {
          aliX /= neighbors; aliY /= neighbors
          cohX = cohX / neighbors - a.x
          cohY = cohY / neighbors - a.y
        }
        if (sepCount > 0) { sepX /= sepCount; sepY /= sepCount }
        const atX = (attX - a.x) * 0.0006
        const atY = (attY - a.y) * 0.0006
        a.vx += sepX * 0.08 + aliX * 0.05 + cohX * 0.003 + atX
        a.vy += sepY * 0.08 + aliY * 0.05 + cohY * 0.003 + atY
        const spd = Math.sqrt(a.vx * a.vx + a.vy * a.vy)
        if (spd > MAX_V) { a.vx *= MAX_V / spd; a.vy *= MAX_V / spd }
        a.x = pymod(a.x + a.vx, w)
        a.y = pymod(a.y + a.vy, h)
        // Stamp the field
        const ix = Math.floor(a.x)
        const iy = Math.floor(a.y)
        if (ix >= 0 && ix < w && iy >= 0 && iy < h) {
          field[iy * w + ix] = Math.min(1, field[iy * w + ix] + 0.6)
          // Soft neighbor stamp for density
          if (ix + 1 < w) field[iy * w + ix + 1] = Math.min(1, field[iy * w + ix + 1] + 0.25)
          if (iy + 1 < h) field[(iy + 1) * w + ix] = Math.min(1, field[(iy + 1) * w + ix] + 0.25)
        }
      }
    },
    gridPixel(s, x, y) {
      const { field, w } = s as { field: Float32Array; w: number }
      return field[y * w + x] ?? 0
    },
    palette(val, t) {
      // Dusk sky: deep violet/navy base → silver-cyan trails → warm pink at density peaks
      const v = val
      const r = cc(18 + 200 * v * v + 60 * v * Math.sin(t * 0.3))
      const g = cc(22 + 140 * v + 80 * v * v)
      const b = cc(48 + 180 * Math.pow(Math.max(0, 1 - v), 1.5) + 90 * v)
      return [r, g, b] as const
    },
  },

  // 8. gondwana — PALETTE + MOTION REWORK (no more Christmas red/green)
  {
    name: 'gondwana',
    reflection: 'The supercontinent remembers.',
    vibe: 'Ancient tectonic drift',
    frames: 180,
    tStep: 0.04,
    pixel(nx, ny, t) {
      const speed = 0.35
      // 7 continental seeds drifting slowly
      let dMin1 = Infinity, dMin2 = Infinity
      let massField = 0
      for (let i = 0; i < 7; i++) {
        const phase = i * 0.9 + t * speed * 0.08 * (1 + (i % 3) * 0.3)
        const sx = Math.sin(phase) * 1.4 + Math.sin(phase * 0.3 + i) * 0.3
        const sy = Math.cos(phase * 1.1 + i * 0.7) * 1.4 + Math.cos(phase * 0.4) * 0.3
        const d = Math.sqrt((nx - sx) ** 2 + (ny - sy) ** 2)
        // Smooth mass contribution (fBM-shaped continent)
        const localNoise = fbm4(nx * 1.5 + i * 11, ny * 1.5 + i * 17)
        const mass = Math.exp(-d * d * 1.2) * (0.7 + localNoise * 0.6)
        massField += mass
        if (d < dMin1) { dMin2 = dMin1; dMin1 = d }
        else if (d < dMin2) { dMin2 = d }
      }
      // Edge shimmer where two continents meet (keep the shimmer element — user liked it)
      const edgeBand = Math.exp(-(dMin2 - dMin1) * 8)
      const shimmer = edgeBand * (0.5 + 0.5 * Math.sin(nx * 30 + ny * 30 + t * 2))
      // Combine smooth mass + edge shimmer
      const landmass = clamp01(massField * 1.1)
      return clamp01(landmass * 0.72 + shimmer * 0.55)
    },
    palette(val, t) {
      // Deep midnight ocean → warm earth ochre/sienna → bright cyan-gold at collision edges
      const v = val
      // Ocean base (dark blue-teal)
      const oceanR = 8, oceanG = 20, oceanB = 42
      // Earth mid (sienna)
      const earthR = 180, earthG = 120, earthB = 65
      // Shimmer peak (cyan-gold mix)
      const shimmerR = 240, shimmerG = 220, shimmerB = 110
      const landW = clamp01(v * 1.8)
      const shimmerW = Math.max(0, (v - 0.65)) * 2.8
      let r = oceanR * (1 - landW) + earthR * landW + shimmerR * shimmerW
      let g = oceanG * (1 - landW) + earthG * landW + shimmerG * shimmerW
      let b = oceanB * (1 - landW) + earthB * landW + shimmerB * shimmerW
      // Subtle atmospheric cycling
      r += 8 * Math.sin(t * 0.15)
      b += 10 * Math.sin(t * 0.15 + 1.2)
      return [cc(r), cc(g), cc(b)] as const
    },
  },

  // 9. kemet — NEW ARTISTIC APPROACH (mandala bloom, Egyptian palette, never stalls)
  {
    name: 'kemet',
    reflection: 'Sacred geometry opens like an eye.',
    vibe: 'Mandala of the sun disk',
    frames: 200,
    tStep: 0.05,
    pixel(nx, ny, t) {
      const r = Math.sqrt(nx * nx + ny * ny)
      const theta = Math.atan2(ny, nx)
      // 5-fold + 10-fold layered symmetry (Penrose-like)
      let sum = 0
      for (let k = 0; k < 5; k++) {
        const a = k * (2 * Math.PI / 5) + t * 0.11
        sum += Math.cos(nx * Math.cos(a) * 5.5 + ny * Math.sin(a) * 5.5 + t * 0.35)
      }
      const fivefold = (sum + 5) / 10
      // Radial pulse outward (mandala bloom)
      const pulse = Math.sin(r * 10 - t * 1.8)
      const bloom = 0.5 + 0.5 * pulse
      // Continuous rotation by rotational interference
      const rotField = Math.sin(theta * 5 - t * 0.6) * Math.cos(r * 6 + t * 0.4)
      const rotTerm = (rotField + 1) / 2
      // Radial falloff so we don't paint to the corners
      const radialMask = Math.exp(-r * r * 0.4)
      return clamp01((fivefold * 0.55 + bloom * 0.25 + rotTerm * 0.35) * radialMask * 1.2)
    },
    palette(val, t) {
      // Egyptian palette: deep lapis blue → gold leaf → terracotta → papyrus highlight
      const v = Math.pow(val, 0.85)
      const hueShift = Math.sin(t * 0.1) * 0.3
      // Four key colors mixed by val
      const lapisR = 12, lapisG = 30, lapisB = 92
      const goldR = 215, goldG = 160, goldB = 38
      const terraR = 178, terraG = 82, terraB = 42
      const papyrusR = 245, papyrusG = 228, papyrusB = 180
      let r: number, g: number, b: number
      if (v < 0.4) {
        const w = v / 0.4
        r = lapisR + (terraR - lapisR) * w
        g = lapisG + (terraG - lapisG) * w
        b = lapisB + (terraB - lapisB) * w
      } else if (v < 0.8) {
        const w = (v - 0.4) / 0.4
        r = terraR + (goldR - terraR) * w
        g = terraG + (goldG - terraG) * w
        b = terraB + (goldB - terraB) * w
      } else {
        const w = (v - 0.8) / 0.2
        r = goldR + (papyrusR - goldR) * w
        g = goldG + (papyrusG - goldG) * w
        b = goldB + (papyrusB - goldB) * w
      }
      // Gentle hue cycling so it never stalls
      r += 14 * hueShift
      b += 22 * hueShift
      return [cc(r), cc(g), cc(b)] as const
    },
  },

  // 10. parallax — KEEPER (9/10)
  {
    name: 'parallax',
    reflection: 'Worlds overlap at angles imperceptible.',
    vibe: 'Dimensional interference shimmer',
    frames: 120,
    tStep: 0.08,
    pixel(nx, ny, t) {
      const speed = 0.5
      const freq = 30
      const a1 = t * speed * 0.01
      const a2 = a1 + 0.04 + Math.sin(t * speed * 0.05) * 0.02
      const p1 = Math.sin(freq * (nx * Math.cos(a1) + ny * Math.sin(a1)))
      const p2 = Math.sin(freq * (nx * Math.cos(a2) + ny * Math.sin(a2)))
      const d = Math.sqrt(nx * nx + ny * ny)
      const p3 = Math.sin(d * 20 - t * speed * 0.5)
      const v = p1 * p2 * 0.7 + p1 * p3 * 0.3
      return (v + 1) / 2
    },
    palette(val, t) {
      const r = cc(127 + 128 * Math.sin(val * 6.28 + t * 0.4 + 3.5))
      const g = cc(50 + 60 * val)
      const b = cc(127 + 128 * Math.sin(val * 6.28 + t * 0.4 + 5.0))
      return [r, g, b] as const
    },
  },

  // 11. hydro — MORE LIFE, MORE MATH (6 orbs, metaball field, comet trails, rogue comet)
  {
    name: 'hydro',
    reflection: 'Mercurial worlds dance in liquid gravity.',
    vibe: 'Orbital metaball choreography',
    frames: 240,
    tStep: 0.06,
    pixel(nx, ny, t) {
      // 6 orbs on distinct elliptical orbits + 1 rogue comet
      const orbs: Array<{ x: number; y: number; mass: number; vx: number; vy: number }> = []
      for (let i = 0; i < 6; i++) {
        const a = 0.4 + i * 0.22         // semi-major
        const e = 0.15 + (i % 3) * 0.12  // eccentricity
        const b = a * Math.sqrt(1 - e * e)
        const period = 3.5 + i * 1.7
        const phase = t * (2 * Math.PI / period) + i * 1.1
        const precession = t * 0.02 * (1 + i * 0.15)
        const cx = a * Math.cos(phase) - a * e
        const cy = b * Math.sin(phase)
        const cp = Math.cos(precession), sp = Math.sin(precession)
        const x = cx * cp - cy * sp
        const y = cx * sp + cy * cp
        // Velocity (for comet trail direction)
        const vx = -a * Math.sin(phase) * cp - b * Math.cos(phase) * sp
        const vy = -a * Math.sin(phase) * sp + b * Math.cos(phase) * cp
        orbs.push({ x, y, mass: 0.9 + (i % 3) * 0.4, vx, vy })
      }
      // Rogue comet — parabolic sweep every ~16s
      const cometPeriod = 16
      const ct = (t % cometPeriod) / cometPeriod
      if (ct > 0.05 && ct < 0.85) {
        const s = (ct - 0.05) / 0.8
        const rogueX = -2.2 + s * 4.4
        const rogueY = -0.8 + Math.sin(s * Math.PI) * 1.2
        orbs.push({ x: rogueX, y: rogueY, mass: 0.5, vx: 4.4, vy: Math.cos(s * Math.PI) * 1.2 })
      }
      // Metaball field
      let field = 0
      let cometField = 0
      for (let i = 0; i < orbs.length; i++) {
        const o = orbs[i]
        const dx = nx - o.x
        const dy = ny - o.y
        const d2 = dx * dx + dy * dy + 0.005
        const contribution = (o.mass * 0.025) / d2
        field += contribution
        // Trail — project along velocity direction
        const vmag = Math.sqrt(o.vx * o.vx + o.vy * o.vy) + 0.001
        const proj = (dx * (-o.vx) + dy * (-o.vy)) / vmag
        if (proj > 0 && proj < 0.9) {
          const perp = (dx * (-o.vy) + dy * o.vx) / vmag
          const trailIntensity = Math.exp(-perp * perp * 40 - proj * 2.5) * 0.12
          field += trailIntensity
          if (i === orbs.length - 1 && orbs.length === 7) cometField += trailIntensity * 2
        }
      }
      return clamp01(field * 1.4 + cometField * 0.5)
    },
    palette(val, t) {
      // Liquid mercury blue with chrome silver highlights + amber comet tail
      const v = Math.pow(val, 0.7)
      const cold = { r: 18, g: 40, b: 92 }
      const mid = { r: 110, g: 165, b: 220 }
      const chrome = { r: 230, g: 240, b: 255 }
      let r: number, g: number, b: number
      if (v < 0.5) {
        const w = v / 0.5
        r = cold.r + (mid.r - cold.r) * w
        g = cold.g + (mid.g - cold.g) * w
        b = cold.b + (mid.b - cold.b) * w
      } else {
        const w = (v - 0.5) / 0.5
        r = mid.r + (chrome.r - mid.r) * w
        g = mid.g + (chrome.g - mid.g) * w
        b = mid.b + (chrome.b - mid.b) * w
      }
      // Subtle shimmer
      const shimmer = 0.08 * Math.sin(t * 0.7 + v * 6)
      return [cc(r * (1 + shimmer)), cc(g * (1 + shimmer)), cc(b)] as const
    },
  },

  // 12. sphinx — FLYING OVER GIZA AT TWILIGHT (scene composition + UFO)
  {
    name: 'sphinx',
    reflection: 'Visitors hover over eternal watchers.',
    vibe: 'Flight over Giza at twilight',
    frames: 300,
    tStep: 0.04,
    pixel(nx, ny, t) {
      // Parallax pan
      const camX = t * 0.05
      // Screen space: normalize so top=~-1.8 (sky), bottom=~+1.8 (ground)
      const nyScreen = ny
      const horizon = 0.3
      // ───── SKY
      let sky = 0
      if (nyScreen < horizon) {
        const skyY = (nyScreen + 1.8) / (horizon + 1.8) // 0 at top, 1 at horizon
        // Vertical gradient: deep indigo top → warm amber at horizon
        sky = 0.15 + 0.35 * skyY + fbm4(nx * 0.4 - camX * 0.2, nyScreen * 0.4) * 0.15
        // Stars (sparse)
        const starHash = hash2d(Math.floor((nx - camX * 0.1) * 80), Math.floor(nyScreen * 80))
        if (starHash > 0.995 && skyY < 0.55) {
          const twinkle = 0.6 + 0.4 * Math.sin(t * 3 + starHash * 100)
          sky += twinkle * 0.7
        }
      }
      // ───── UFO
      const ufoX = 0.5 + 0.08 * Math.sin(t * 0.4)
      const ufoY = -0.7 + 0.05 * Math.sin(t * 0.7)
      const ufoDx = nx - ufoX, ufoDy = nyScreen - ufoY
      const ufoEllipse = ufoDx * ufoDx / 0.012 + ufoDy * ufoDy / 0.0012
      const ufoBody = Math.exp(-ufoEllipse)
      const ufoGlow = Math.exp(-ufoEllipse * 0.2) * 0.35
      const ufoBeam = (nx > ufoX - 0.15 && nx < ufoX + 0.15 && nyScreen > ufoY && nyScreen < horizon - 0.2)
        ? Math.exp(-((nx - ufoX) ** 2) * 70) * 0.25 * (0.5 + 0.5 * Math.sin(t * 4))
        : 0
      // ───── PYRAMIDS (3 silhouettes at mid-ground, just above horizon)
      let pyramid = 0
      const pyramids = [
        { cx: -0.85, w: 0.55, h: 0.35 },
        { cx: -0.15, w: 0.65, h: 0.45 },
        { cx: 0.55, w: 0.48, h: 0.30 },
      ]
      for (const p of pyramids) {
        const pNx = nx - p.cx + Math.sin(camX * 0.5) * 0.05
        const base = horizon
        // Triangle SDF
        if (nyScreen < base && nyScreen > base - p.h) {
          const yFromApex = base - nyScreen
          const halfW = (yFromApex / p.h) * p.w * 0.5
          if (Math.abs(pNx) < halfW) {
            const edge = halfW - Math.abs(pNx)
            pyramid = Math.max(pyramid, 0.55 + 0.25 * Math.exp(-edge * 20))
          }
        }
      }
      // ───── SPHINX (foreground silhouette, lower right)
      const sphinxX = nx - 0.6 + camX * 0.3
      const sphinxY = nyScreen - 0.85
      let sphinx = 0
      // Body (elongated box)
      if (sphinxX > -0.45 && sphinxX < 0.35 && sphinxY > -0.35 && sphinxY < 0.25) {
        sphinx = 0.62
      }
      // Head (ellipse higher up)
      const headDx = sphinxX - 0.25, headDy = sphinxY - 0.45
      const head = Math.exp(-(headDx * headDx) / 0.012 - (headDy * headDy) / 0.022)
      sphinx = Math.max(sphinx, head * 0.75)
      // Eye glow
      const eyeD2 = (sphinxX - 0.28) ** 2 + (sphinxY - 0.42) ** 2
      const eye = Math.exp(-eyeD2 * 900) * 0.7
      sphinx = Math.max(sphinx, eye)
      // ───── SAND (foreground dunes)
      let sand = 0
      if (nyScreen > horizon) {
        const dune = Math.sin((nx + camX * 0.8) * 3.5) * 0.04 + fbm4(nx * 1.5 - camX, nyScreen * 1.5) * 0.08
        const sandY = nyScreen - horizon - dune
        sand = Math.min(0.45, sandY * 0.4 + 0.25)
      }
      // Composite
      let val = sky + pyramid * 0.9 + sand
      val = Math.max(val, sphinx)
      val += ufoBody * 1.2 + ufoGlow + ufoBeam
      return clamp01(val)
    },
    palette(val, t) {
      // Twilight indigo → warm amber horizon → moonlit gold for stone
      const v = val
      const ufoHue = Math.sin(t * 0.4) * 0.5 + 0.5 // 0..1, cyan → violet
      if (v > 0.95) {
        // UFO bright area — cyan/green/violet glow
        const r = cc(120 + 135 * ufoHue * 0.5)
        const g = cc(230 + 25 * Math.sin(t))
        const b = cc(180 + 75 * ufoHue)
        return [r, g, b] as const
      }
      const skyR = 30, skyG = 25, skyB = 65
      const horizonR = 240, horizonG = 140, horizonB = 85
      const stoneR = 200, stoneG = 165, stoneB = 100
      let r: number, g: number, b: number
      if (v < 0.35) {
        const w = v / 0.35
        r = skyR + (horizonR - skyR) * w * 0.5
        g = skyG + (horizonG - skyG) * w * 0.5
        b = skyB + (horizonB - skyB) * w * 0.5
      } else if (v < 0.7) {
        const w = (v - 0.35) / 0.35
        r = horizonR * 0.6 + stoneR * 0.4 * w + (horizonR - stoneR) * (1 - w) * 0.3
        g = horizonG * 0.6 + stoneG * 0.4 * w
        b = horizonB * 0.4 + stoneB * 0.3 * w
      } else {
        r = stoneR + 30
        g = stoneG + 20
        b = stoneB
      }
      return [cc(r), cc(g), cc(b)] as const
    },
  },

  // 13. surya — SUN GOD (core, chromosphere, 12-spoke corona, 7 prominences, flares)
  {
    name: 'surya',
    reflection: 'The chariot of the sun never stops.',
    vibe: 'Living sun with twelve rays',
    frames: 240,
    tStep: 0.05,
    pixel(nx, ny, t) {
      const r = Math.sqrt(nx * nx + ny * ny)
      const theta = Math.atan2(ny, nx)
      // Core (white-hot disk)
      const breath = 1 + 0.08 * Math.sin(t * 0.3)
      const coreR = 0.12 * breath
      const core = r < coreR ? 1 : Math.exp(-(r - coreR) * (r - coreR) * 200)
      // Chromosphere (plasma layer)
      const chromoN = fbm6(nx * 3 + t * 0.2, ny * 3 + t * 0.25)
      const chromoRing = Math.exp(-((r - 0.22) * (r - 0.22)) * 80) * (0.4 + chromoN * 0.8)
      // 12-spoke rotating corona
      const coronaAngle = t * 0.1
      const spokes = Math.pow(Math.abs(Math.sin(6 * (theta - coronaAngle))), 3)
      const coronaMask = Math.exp(-((r - 0.4) * (r - 0.4)) * 6)
      const corona = spokes * coronaMask * 0.85
      // 7 prominences (horses of Surya) — radial filaments
      let prominences = 0
      for (let i = 0; i < 7; i++) {
        const promAng = i * (2 * Math.PI / 7) + Math.sin(t * 0.08 + i) * 0.15
        const angDist = Math.abs(pymod(theta - promAng + Math.PI, 2 * Math.PI) - Math.PI)
        const length = 0.55 + 0.12 * Math.sin(t * 0.5 + i * 1.3)
        if (angDist < 0.08 && r > 0.3 && r < length) {
          const radialFall = Math.exp(-angDist * angDist * 600)
          const tipFade = 1 - Math.pow((r - 0.3) / (length - 0.3), 1.5)
          prominences = Math.max(prominences, radialFall * tipFade * 0.6)
        }
      }
      // Solar flares — periodic eruptions
      const flarePeriod = 4.0
      const flareIdx = Math.floor(t / flarePeriod)
      const flarePhase = (t % flarePeriod) / flarePeriod
      let flare = 0
      if (flarePhase < 0.4) {
        const flareAng = hash2d(flareIdx, 17) * 2 * Math.PI
        const angDist = Math.abs(pymod(theta - flareAng + Math.PI, 2 * Math.PI) - Math.PI)
        const reach = 0.25 + 0.6 * Math.sin(flarePhase * Math.PI / 0.4)
        if (angDist < 0.18 && r > 0.25 && r < 0.25 + reach) {
          const intensity = Math.sin(flarePhase * Math.PI / 0.4)
          const rad = (1 - angDist / 0.18) * (1 - Math.pow((r - 0.25) / reach, 2))
          flare = intensity * rad * 0.8
        }
      }
      // Spicules (outer edge granulation)
      let spicules = 0
      if (r > 0.6 && r < 0.95) {
        const sn = noise2d(theta * 12 + t * 0.3, r * 10)
        if (sn > 0.82) spicules = (sn - 0.82) * 3 * (1 - (r - 0.6) / 0.35) * 0.35
      }
      return clamp01(core + chromoRing * 0.7 + corona + prominences + flare + spicules)
    },
    palette(val, _t) {
      // Solar gradient: deep crimson void → red-orange → saffron gold → white-hot
      const v = Math.pow(val, 0.75)
      const r = cc(30 + 225 * v)
      const g = cc(Math.pow(Math.max(0, v - 0.2), 1.3) * 340)
      const b = cc(Math.pow(Math.max(0, v - 0.72), 2) * 350)
      return [r, g, b] as const
    },
  },

  // 14. trappist — PERFECT-LOOP 4-PHASE VOYAGE (seven worlds)
  {
    name: 'trappist',
    reflection: 'Against all odds, back where we started.',
    vibe: 'Seven worlds loop eternally',
    frames: 300,
    tStep: 0.04,
    pixel(nx, ny, t) {
      const T = 60 // loop period
      const phase = (t % T) / T // 0..1
      // 4 phases: 0-0.25 establish, 0.25-0.5 zoom into world, 0.5-0.75 underwater, 0.75-1.0 pull back
      // Zoom follows sin²(phase/2 * π) so it perfectly closes
      const zoomArc = Math.sin(phase * Math.PI) ** 2 // 0..1..0 over cycle
      const zoom = 1 + 9 * zoomArc
      // Apply zoom (into world chosen by floor time)
      const focusX = 0.4 * Math.cos(phase * 2 * Math.PI * 0.5)
      const focusY = 0.4 * Math.sin(phase * 2 * Math.PI * 0.5)
      const zx = (nx - focusX) * zoom + focusX
      const zy = (ny - focusY) * zoom + focusY
      // Hyperbolic disk (Poincaré) — 7 worlds on it
      const r = Math.sqrt(zx * zx + zy * zy)
      // Phase 1+4: 7 worlds on disk
      // Background starfield (always visible, slightly warped by 4D rot)
      const starX = nx * 0.6 + 0.2 * Math.sin(t * 0.1)
      const starY = ny * 0.6 + 0.2 * Math.cos(t * 0.1)
      const starHash = hash2d(Math.floor(starX * 100), Math.floor(starY * 100))
      const stars = starHash > 0.997 ? 0.7 : 0
      // 7 worlds
      let worlds = 0
      if (zoomArc < 0.4) {
        for (let i = 0; i < 7; i++) {
          const wAng = (i / 7) * 2 * Math.PI + t * 2 * Math.PI / T * 0.5
          const wR = 0.3 + (i % 3) * 0.22
          const wx = wR * Math.cos(wAng)
          const wy = wR * Math.sin(wAng)
          const dx = zx - wx, dy = zy - wy
          const d2 = dx * dx + dy * dy
          const size = 0.06 + (i % 2) * 0.02
          worlds += Math.exp(-d2 / (size * size)) * (0.6 + 0.4 * Math.sin(t * 0.3 + i))
        }
      }
      // Zoomed-in world: surface detail + city lights
      let surface = 0
      if (zoomArc > 0.2 && zoomArc < 0.8) {
        const surfR = Math.sqrt(zx * zx + zy * zy)
        if (surfR < 1) {
          const rot = t * 0.15
          const sx = zx * Math.cos(rot) + zy * Math.sin(rot)
          const sy = -zx * Math.sin(rot) + zy * Math.cos(rot)
          const cont = fbm6(sx * 3, sy * 3)
          surface = cont * 0.8 * (1 - surfR) * zoomArc
          // City lights on night side
          if (zx < 0 && cont > 0.55) {
            const cityHash = hash2d(Math.floor(sx * 40), Math.floor(sy * 40))
            if (cityHash > 0.92) surface += 0.5 * zoomArc
          }
        }
      }
      // Underwater phase (deepest zoom)
      let underwater = 0
      if (zoomArc > 0.75) {
        const deepPhase = (zoomArc - 0.75) / 0.25
        const bioHash = hash2d(Math.floor(nx * 50 + t * 3), Math.floor(ny * 50))
        underwater = bioHash > 0.93 ? 0.8 * deepPhase : 0.12 * deepPhase
        underwater += fbm4(nx * 4, ny * 4 + t * 0.5) * 0.15 * deepPhase
      }
      return clamp01(stars + worlds + surface + underwater)
    },
    palette(val, t) {
      const T = 60
      const phase = (t % T) / T
      const zoomArc = Math.sin(phase * Math.PI) ** 2
      const v = val
      // Color shifts with journey depth
      if (zoomArc > 0.75) {
        // Deep ocean bioluminescent phase
        const r = cc(10 + 80 * v)
        const g = cc(30 + 180 * v)
        const b = cc(60 + 180 * v)
        return [r, g, b] as const
      } else if (zoomArc > 0.25) {
        // Surface phase — atmospheric
        const atmHue = Math.sin(phase * 2 * Math.PI) * 0.5 + 0.5
        const r = cc(30 + 180 * v * (0.5 + atmHue * 0.5))
        const g = cc(45 + 160 * v)
        const b = cc(80 + 150 * v * (1 - atmHue * 0.5))
        return [r, g, b] as const
      } else {
        // Establish shot — cosmic violet
        const r = cc(30 + 180 * v * Math.sin(v * 6.28 + t * 0.3 + 4))
        const g = cc(20 + 80 * v)
        const b = cc(80 + 175 * v)
        return [r, g, b] as const
      }
    },
  },

  // 15. warmwind — FOREST CANOPY + FALLING LEAF (wind-through-leaves scene)
  {
    name: 'warmwind',
    reflection: 'Wind becomes visible in what it moves.',
    vibe: 'Golden hour through leaves',
    frames: 300,
    tStep: 0.05,
    pixel(nx, ny, t) {
      // Global wind wave (sweeps left-to-right)
      const windWave = Math.sin(nx * 2 - t * 1.2) * 0.08
      // Gust every ~8s
      const gust = 1 + 1.5 * Math.pow(Math.max(0, Math.sin(t * 0.8 - 1.2)), 8)
      const sway = windWave * gust
      // Canopy: 12 leaf clusters at varying depths + phases
      let canopy = 0
      for (let i = 0; i < 12; i++) {
        const depth = 0.3 + (i % 4) * 0.22
        const cx = -1.8 + (i * 0.37) % 3.6 + Math.sin(t * 0.3 + i) * 0.06
        const cy = -1.2 + (i * 0.29) % 2.4 + sway * (1 - depth) + Math.cos(t * 0.4 + i * 1.3) * 0.04
        const dx = nx - cx, dy = ny - cy
        // Leaf-shape mask: elongated ellipse rotated at i*π/6
        const ang = i * 0.52 + t * 0.05
        const lx = dx * Math.cos(ang) + dy * Math.sin(ang)
        const ly = -dx * Math.sin(ang) + dy * Math.cos(ang)
        const leafR = 0.28 * (0.7 + depth * 0.5)
        const shape = Math.exp(-(lx * lx) / (leafR * leafR * 0.6) - (ly * ly) / (leafR * leafR * 0.25))
        canopy += shape * (0.3 + depth * 0.7)
      }
      // Light shafts (4 vertical columns of warmth)
      let shafts = 0
      for (let i = 0; i < 4; i++) {
        const sx = -1.5 + i * 1.0 + Math.sin(t * 0.15 + i) * 0.15
        const d = Math.abs(nx - sx)
        shafts += Math.exp(-d * d * 8) * 0.18 * (1 - Math.abs(ny) * 0.3)
      }
      // Falling leaf (one leaf spirals down every ~10s)
      const leafCycle = 10
      const leafPhase = (t % leafCycle) / leafCycle
      const leafCycleIdx = Math.floor(t / leafCycle)
      const leafStartX = (hash2d(leafCycleIdx, 31) - 0.5) * 2
      const leafX = leafStartX + 0.25 * Math.sin(t * 0.8 + leafCycleIdx * 1.3)
      const leafY = -1.6 + leafPhase * 3.4
      const lDx = nx - leafX, lDy = ny - leafY
      const leafAng = t * 1.2 + leafCycleIdx
      const llx = lDx * Math.cos(leafAng) + lDy * Math.sin(leafAng)
      const lly = -lDx * Math.sin(leafAng) + lDy * Math.cos(leafAng)
      const fallingLeaf = Math.exp(-(llx * llx) / 0.004 - (lly * lly) / 0.0015) * 0.9
      // Shimmer
      const shimmer = 0.12 * Math.sin(nx * 40 + ny * 40 + t * 5)
      return clamp01(canopy * (1 + shimmer) + shafts + fallingLeaf)
    },
    palette(val, t) {
      // Deep forest green → sap green → amber gold → honey at peaks. Falling leaf = crimson accent.
      const v = Math.pow(val, 0.82)
      if (val > 0.75) {
        // Falling leaf tint + bright highlights
        const r = cc(200 + 55 * v + 30 * Math.sin(t + v * 4))
        const g = cc(120 + 100 * v)
        const b = cc(40 + 60 * v)
        return [r, g, b] as const
      }
      const r = cc(30 + 220 * v * v + 25 * v * Math.sin(t * 0.3))
      const g = cc(50 + 180 * v)
      const b = cc(22 + 60 * v * v)
      return [r, g, b] as const
    },
  },

  // 16. codex — LIVING LABYRINTH (maze + pilgrims, state-based)
  {
    name: 'codex',
    reflection: 'Ancient pilgrims walk the shifting walls.',
    vibe: 'Illuminated manuscript alive',
    frames: 300,
    tStep: 0.06,
    init(w, h) {
      // Generate a maze on a coarser grid, then upscale
      const cellSize = 6
      const mw = Math.max(8, Math.floor(w / cellSize))
      const mh = Math.max(8, Math.floor(h / cellSize))
      const walls = new Uint8Array(mw * mh).fill(1) // 1 = wall
      const stack: Array<[number, number]> = []
      const seen = new Uint8Array(mw * mh)
      const startX = 1, startY = 1
      walls[startY * mw + startX] = 0
      seen[startY * mw + startX] = 1
      stack.push([startX, startY])
      const dirs: Array<[number, number]> = [[2, 0], [-2, 0], [0, 2], [0, -2]]
      while (stack.length > 0) {
        const [cx, cy] = stack[stack.length - 1]
        const shuffled = dirs.slice().sort(() => Math.random() - 0.5)
        let advanced = false
        for (const [dx, dy] of shuffled) {
          const nxx = cx + dx, nyy = cy + dy
          if (nxx > 0 && nxx < mw - 1 && nyy > 0 && nyy < mh - 1 && !seen[nyy * mw + nxx]) {
            walls[nyy * mw + nxx] = 0
            walls[(cy + dy / 2) * mw + (cx + dx / 2)] = 0
            seen[nyy * mw + nxx] = 1
            stack.push([nxx, nyy])
            advanced = true
            break
          }
        }
        if (!advanced) stack.pop()
      }
      // 5 pilgrims
      const pilgrims: Array<{ x: number; y: number; dir: number; color: number }> = []
      for (let i = 0; i < 5; i++) {
        let px: number, py: number
        do {
          px = 1 + Math.floor(Math.random() * (mw - 2))
          py = 1 + Math.floor(Math.random() * (mh - 2))
        } while (walls[py * mw + px] === 1)
        pilgrims.push({ x: px, y: py, dir: Math.floor(Math.random() * 4), color: i })
      }
      const trails = new Float32Array(w * h)
      const keystones: Array<{ x: number; y: number; age: number }> = []
      return { walls, pilgrims, trails, keystones, mw, mh, cellSize, w, h, lastRegen: 0 }
    },
    update(s, t, _frame, w, h) {
      const state = s as {
        walls: Uint8Array
        pilgrims: Array<{ x: number; y: number; dir: number; color: number }>
        trails: Float32Array
        keystones: Array<{ x: number; y: number; age: number }>
        mw: number; mh: number; cellSize: number
        w: number; h: number
        lastRegen: number
      }
      // Decay trails
      for (let i = 0; i < state.trails.length; i++) state.trails[i] *= 0.96
      // Pilgrim movement (random valid-step walk)
      const dirX = [1, 0, -1, 0]
      const dirY = [0, 1, 0, -1]
      for (const p of state.pilgrims) {
        if (Math.random() < 0.35) p.dir = Math.floor(Math.random() * 4)
        // Try forward
        for (let tries = 0; tries < 4; tries++) {
          const nxx = p.x + dirX[p.dir]
          const nyy = p.y + dirY[p.dir]
          if (nxx > 0 && nxx < state.mw - 1 && nyy > 0 && nyy < state.mh - 1
              && state.walls[nyy * state.mw + nxx] === 0) {
            p.x = nxx; p.y = nyy
            break
          }
          p.dir = (p.dir + 1) % 4
        }
        // Stamp trail (in screen coords)
        const sx = p.x * state.cellSize + Math.floor(state.cellSize / 2)
        const sy = p.y * state.cellSize + Math.floor(state.cellSize / 2)
        for (let dy = -1; dy <= 1; dy++) {
          for (let dx = -1; dx <= 1; dx++) {
            const tx = sx + dx, ty = sy + dy
            if (tx >= 0 && tx < w && ty >= 0 && ty < h) {
              state.trails[ty * w + tx] = Math.min(1.5, state.trails[ty * w + tx] + 0.4)
            }
          }
        }
      }
      // Keystone flash every ~15s
      if (Math.floor(t * 0.2) !== Math.floor(state.lastRegen * 0.2) && Math.random() < 0.35) {
        const kx = 2 + Math.floor(Math.random() * (state.mw - 4))
        const ky = 2 + Math.floor(Math.random() * (state.mh - 4))
        if (state.walls[ky * state.mw + kx] === 0) {
          state.keystones.push({ x: kx * state.cellSize + 3, y: ky * state.cellSize + 3, age: 0 })
        }
      }
      // Advance keystone ages and expire after 50 frames (~2.5s)
      for (let i = state.keystones.length - 1; i >= 0; i--) {
        state.keystones[i].age++
        if (state.keystones[i].age > 50) state.keystones.splice(i, 1)
      }
      state.lastRegen = t
    },
    gridPixel(s, x, y) {
      const state = s as {
        walls: Uint8Array; trails: Float32Array
        keystones: Array<{ x: number; y: number; age: number }>
        mw: number; cellSize: number; w: number
      }
      // Wall intensity
      const mx = Math.floor(x / state.cellSize)
      const my = Math.floor(y / state.cellSize)
      const isWall = state.walls[my * state.mw + mx] === 1 ? 1 : 0
      const trail = state.trails[y * state.w + x] ?? 0
      let keystone = 0
      for (const k of state.keystones) {
        const bright = Math.sin((k.age / 50) * Math.PI)
        const d2 = (x - k.x) ** 2 + (y - k.y) ** 2
        keystone = Math.max(keystone, Math.exp(-d2 / 30) * bright)
      }
      return Math.min(1, isWall * 0.55 + trail * 0.8 + keystone)
    },
    palette(val, t) {
      // Deep parchment → warm amber walls → gold at trails → pure gold at keystones
      const v = val
      if (v > 0.85) {
        const r = cc(240 + 15 * Math.sin(t * 2))
        const g = cc(210 + 40 * v)
        const b = cc(80 + 60 * v)
        return [r, g, b] as const
      }
      const r = cc(35 + 220 * v * v)
      const g = cc(22 + 160 * v * v + 30 * v)
      const b = cc(12 + 50 * v)
      return [r, g, b] as const
    },
  },

  // 17. fungl — FULL MYCELIUM LIFECYCLE (grow, bloom, decay, panspermia)
  {
    name: 'fungl',
    reflection: 'Life claims new ground while old ground sleeps.',
    vibe: 'Mycelial forest floor',
    frames: 300,
    tStep: 0.05,
    init(w, h) {
      const trail = new Float32Array(w * h)
      const decay = new Float32Array(w * h)
      const agents: Array<{ x: number; y: number; angle: number; life: number }> = []
      for (let i = 0; i < 400; i++) {
        agents.push({
          x: Math.random() * w,
          y: Math.random() * h,
          angle: Math.random() * 2 * Math.PI,
          life: 100 + Math.random() * 200,
        })
      }
      const nutrients: Array<{ x: number; y: number; v: number }> = []
      for (let i = 0; i < 22; i++) {
        nutrients.push({ x: Math.random() * w, y: Math.random() * h, v: 1 })
      }
      const fruits: Array<{ x: number; y: number; age: number; life: number }> = []
      const spores: Array<{ x: number; y: number; vx: number; vy: number; life: number }> = []
      return { trail, decay, agents, nutrients, fruits, spores, w, h, camX: 0, camY: 0 }
    },
    update(s, t, _frame, w, h) {
      const state = s as {
        trail: Float32Array; decay: Float32Array
        agents: Array<{ x: number; y: number; angle: number; life: number }>
        nutrients: Array<{ x: number; y: number; v: number }>
        fruits: Array<{ x: number; y: number; age: number; life: number }>
        spores: Array<{ x: number; y: number; vx: number; vy: number; life: number }>
        w: number; h: number; camX: number; camY: number
      }
      // Camera drift
      state.camX = 0.04 * t * w * 0.002
      state.camY = 0.02 * Math.sin(t * 0.1) * h * 0.002
      // Fade trail → decay
      for (let i = 0; i < state.trail.length; i++) {
        if (state.trail[i] > 0.01) {
          const loss = state.trail[i] * 0.01
          state.trail[i] -= loss
          state.decay[i] = Math.min(1, state.decay[i] + loss * 0.5)
        }
        state.decay[i] *= 0.985
      }
      // Agents walk with nutrient chemotaxis
      for (const ag of state.agents) {
        ag.life--
        if (ag.life <= 0) { ag.x = Math.random() * w; ag.y = Math.random() * h; ag.life = 200; continue }
        let bestNutrient: typeof state.nutrients[0] | null = null
        let bestD2 = Infinity
        for (const n of state.nutrients) {
          if (n.v <= 0) continue
          const d2 = (n.x - ag.x) ** 2 + (n.y - ag.y) ** 2
          if (d2 < bestD2 && d2 < 400) { bestD2 = d2; bestNutrient = n }
        }
        const steerN = (noise2d(ag.x * 0.02 + t * 0.05, ag.y * 0.02) - 0.5) * 3
        if (bestNutrient) {
          const targetAng = Math.atan2(bestNutrient.y - ag.y, bestNutrient.x - ag.x)
          let delta = targetAng - ag.angle
          while (delta > Math.PI) delta -= 2 * Math.PI
          while (delta < -Math.PI) delta += 2 * Math.PI
          ag.angle += delta * 0.15 + steerN * 0.15
          if (bestD2 < 9) {
            bestNutrient.v -= 0.04
            if (bestNutrient.v < 0.1 && Math.random() < 0.08) {
              state.fruits.push({ x: bestNutrient.x, y: bestNutrient.y, age: 0, life: 60 })
              bestNutrient.v = 0
            }
          }
        } else {
          ag.angle += steerN * 0.3
        }
        ag.x = pymod(ag.x + Math.cos(ag.angle) * 0.9, w)
        ag.y = pymod(ag.y + Math.sin(ag.angle) * 0.9, h)
        const idx = Math.floor(ag.y) * w + Math.floor(ag.x)
        if (idx >= 0 && idx < state.trail.length) {
          state.trail[idx] = Math.min(1, state.trail[idx] + 0.14)
        }
      }
      // Fruits bloom and die
      for (let i = state.fruits.length - 1; i >= 0; i--) {
        state.fruits[i].age++
        if (state.fruits[i].age >= state.fruits[i].life) {
          // Pop — emit spores
          for (let k = 0; k < 8; k++) {
            const a = Math.random() * 2 * Math.PI
            state.spores.push({
              x: state.fruits[i].x, y: state.fruits[i].y,
              vx: Math.cos(a) * 2, vy: Math.sin(a) * 2, life: 80,
            })
          }
          state.fruits.splice(i, 1)
        }
      }
      // Spores drift + spawn new colony on landing
      for (let i = state.spores.length - 1; i >= 0; i--) {
        const sp = state.spores[i]
        sp.x += sp.vx; sp.y += sp.vy; sp.life--
        sp.vx *= 0.96; sp.vy *= 0.96
        if (sp.life <= 0) {
          // Land — seed new nutrient
          if (sp.x >= 0 && sp.x < w && sp.y >= 0 && sp.y < h) {
            state.nutrients.push({ x: sp.x, y: sp.y, v: 1 })
          }
          state.spores.splice(i, 1)
        }
      }
      // Limit nutrient count
      if (state.nutrients.length > 50) state.nutrients = state.nutrients.filter(n => n.v > 0.05).slice(0, 35)
    },
    gridPixel(s, x, y) {
      const state = s as {
        trail: Float32Array; decay: Float32Array
        fruits: Array<{ x: number; y: number; age: number; life: number }>
        spores: Array<{ x: number; y: number; vx: number; vy: number; life: number }>
        nutrients: Array<{ x: number; y: number; v: number }>
        w: number
      }
      const baseTrail = state.trail[y * state.w + x] ?? 0
      const baseDecay = (state.decay[y * state.w + x] ?? 0) * 0.35
      let val = baseTrail + baseDecay
      // Nutrient glow
      for (const n of state.nutrients) {
        if (n.v <= 0) continue
        const d2 = (n.x - x) ** 2 + (n.y - y) ** 2
        if (d2 < 100) val = Math.max(val, Math.exp(-d2 / 30) * n.v * 0.6)
      }
      // Fruit bloom
      for (const f of state.fruits) {
        const d2 = (f.x - x) ** 2 + (f.y - y) ** 2
        if (d2 < 80) {
          const pulse = Math.sin((f.age / f.life) * Math.PI)
          val = Math.max(val, Math.exp(-d2 / 15) * pulse * 0.9)
        }
      }
      // Spore
      for (const sp of state.spores) {
        const d2 = (sp.x - x) ** 2 + (sp.y - y) ** 2
        if (d2 < 10) val = Math.max(val, Math.exp(-d2 / 4) * 0.8)
      }
      return Math.min(1, val)
    },
    palette(val, t) {
      const v = val
      // Humus black → phosphorescent teal → amber nutrient → coral fruit → pale-blue spore
      const r = cc(15 + 55 * v + 200 * Math.pow(Math.max(0, v - 0.65), 1.8))
      const g = cc(25 + 230 * v * v + 60 * v * Math.sin(t * 0.3 + v * 4))
      const b = cc(30 + 110 * v)
      return [r, g, b] as const
    },
  },

  // 18. attractor — JWST GRAVITY SCENE (black hole + accretion disc + lensing + moons)
  {
    name: 'attractor',
    reflection: 'Gravity has a signature the eye can read.',
    vibe: 'Black hole with accretion disc',
    frames: 300,
    tStep: 0.04,
    pixel(nx, ny, t) {
      // Central black hole with photon ring
      const r = Math.sqrt(nx * nx + ny * ny)
      const theta = Math.atan2(ny, nx)
      const Rs = 0.1
      // Dark core inside event horizon
      const core = r < Rs ? 1 - r / Rs * 0.3 : 0
      // Photon ring — thin bright circle at ~1.5 Rs
      const photonR = Rs * 1.5
      const photonRing = Math.exp(-((r - photonR) ** 2) * 1800)
      // Accretion disc — tilted ellipse (squashed vertically for 3D look)
      const tilt = 0.35
      const discNy = ny / tilt // "un-squash" to work in disc's own frame
      const discR = Math.sqrt(nx * nx + discNy * discNy)
      const discInner = Rs * 2.2, discOuter = 0.85
      let disc = 0
      if (discR > discInner && discR < discOuter) {
        const discTheta = Math.atan2(discNy, nx)
        // Kepler velocity: ω ∝ r^(-3/2)
        const omega = Math.pow(discInner / discR, 1.5) * 2.5
        const swirl = Math.sin(discTheta * 3 - t * omega) * 0.3
        // Plasma turbulence
        const plasma = fbm4(nx * 3 + t * 0.4, discNy * 3 + t * 0.3)
        // Radial temperature: hotter inside
        const temp = 1 - (discR - discInner) / (discOuter - discInner)
        disc = temp * (0.6 + plasma * 0.4 + swirl)
        // Doppler beaming: left side (nx < 0) = approaching = brighter
        const doppler = nx < 0 ? 1.5 : 0.7
        disc *= doppler
        // Edge fade
        disc *= Math.pow(1 - Math.abs(discR - (discInner + discOuter) / 2) / ((discOuter - discInner) / 2), 0.6)
      }
      // Flare event every ~18s
      const flareT = t % 18
      if (flareT < 2) {
        const flareIntensity = Math.sin(flareT * Math.PI / 2) * (flareT < 1 ? flareT : 2 - flareT)
        disc *= 1 + flareIntensity * 1.2
      }
      // 4 orbiting moons
      let moons = 0
      for (let i = 0; i < 4; i++) {
        const a = 0.35 + i * 0.18
        const period = 6 + i * 2.5
        const phase = t * 2 * Math.PI / period + i * 1.3
        const mx = a * Math.cos(phase)
        const my = a * Math.sin(phase) * tilt // tilt with disc
        const d2 = (nx - mx) ** 2 + (ny - my) ** 2
        moons += Math.exp(-d2 * 2500)
      }
      // Background starfield (lensed)
      // Simple lensing: shift hash position by deflection angle
      const deflect = 4 * Rs / (r + 0.02)
      const lensAng = theta
      const lnx = nx - deflect * Math.cos(lensAng) * 0.3
      const lny = ny - deflect * Math.sin(lensAng) * 0.3
      const starHash = hash2d(Math.floor(lnx * 120), Math.floor(lny * 120))
      let stars = 0
      if (starHash > 0.996 && r > Rs * 1.8) {
        stars = (starHash - 0.996) * 250
      }
      // Einstein ring at photon sphere
      const einsteinRing = Math.exp(-((r - Rs * 2) ** 2) * 200) * 0.4
      // JWST-like nebula blob (soft fBM in background)
      const nebulaX = nx - 0.4 + Math.sin(t * 0.05) * 0.1
      const nebulaY = ny + 0.5
      const nebula = fbm6(nebulaX * 1.8, nebulaY * 1.8) * 0.3 * (0.6 + 0.4 * Math.sin(t * 0.1))
      return clamp01(disc + photonRing * 0.9 + moons + stars + einsteinRing + nebula * 0.4 - core * 0.8)
    },
    palette(val, _t) {
      // JWST false-color: deep cosmic black → violet-indigo → cyan gas → gold dust → white-hot
      const v = val
      const r = cc(15 + 240 * Math.pow(v, 1.1))
      const g = cc(10 + 85 * v + 140 * Math.pow(Math.max(0, v - 0.35), 1.3))
      const b = cc(40 + 180 * v - 60 * Math.pow(Math.max(0, v - 0.55), 2))
      return [r, g, b] as const
    },
  },

  // 19. luca — GRAY-SCOTT WITH PARAMETER DRIFT (fixed + alive)
  {
    name: 'luca',
    reflection: 'Chemistry remembers how to copy itself.',
    vibe: 'Primordial replication',
    frames: 400,
    tStep: 0.025,
    init(w, h) {
      const U = new Float32Array(w * h).fill(1)
      const V = new Float32Array(w * h).fill(0)
      // Seed multiple patches across the ENTIRE grid (bug fix: previously only seeded top)
      for (let i = 0; i < 18; i++) {
        const bx = 5 + Math.floor(Math.random() * (w - 10))
        const by = 5 + Math.floor(Math.random() * (h - 10))
        for (let dy = -4; dy <= 4; dy++) {
          for (let dx = -4; dx <= 4; dx++) {
            const yy = by + dy, xx = bx + dx
            if (yy >= 0 && yy < h && xx >= 0 && xx < w) {
              const idx = yy * w + xx
              V[idx] = 1
              U[idx] = 0.5
            }
          }
        }
      }
      return { U, V, w, h, injectionTimer: 0 }
    },
    update(s, t, _frame, w, h) {
      const state = s as { U: Float32Array; V: Float32Array; w: number; h: number; injectionTimer: number }
      // Parameter drift through phase-diagram hotspots
      const cycleT = 45
      const phase = (t % cycleT) / cycleT
      // 6 keyframes: spots, coral, stripes, labyrinths, mitosis, pulse, back
      const presets = [
        { f: 0.035, k: 0.062 }, // spots
        { f: 0.054, k: 0.063 }, // coral
        { f: 0.042, k: 0.061 }, // stripes
        { f: 0.039, k: 0.058 }, // labyrinths
        { f: 0.028, k: 0.062 }, // mitosis
        { f: 0.025, k: 0.060 }, // pulse
      ]
      const idx0 = Math.floor(phase * presets.length)
      const idx1 = (idx0 + 1) % presets.length
      const blend = phase * presets.length - idx0
      const f = presets[idx0].f * (1 - blend) + presets[idx1].f * blend
      const k = presets[idx0].k * (1 - blend) + presets[idx1].k * blend
      const Du = 0.16, Dv = 0.08
      // Multiple sub-steps per frame for stable dynamics
      for (let step = 0; step < 3; step++) {
        const U2 = state.U.slice()
        const V2 = state.V.slice()
        for (let y = 1; y < h - 1; y++) {
          for (let x = 1; x < w - 1; x++) {
            const i = y * w + x
            const lapU =
              state.U[(y - 1) * w + x] + state.U[(y + 1) * w + x] +
              state.U[y * w + (x - 1)] + state.U[y * w + (x + 1)] - 4 * state.U[i]
            const lapV =
              state.V[(y - 1) * w + x] + state.V[(y + 1) * w + x] +
              state.V[y * w + (x - 1)] + state.V[y * w + (x + 1)] - 4 * state.V[i]
            const uvv = state.U[i] * state.V[i] * state.V[i]
            U2[i] = state.U[i] + Du * lapU - uvv + f * (1 - state.U[i])
            V2[i] = state.V[i] + Dv * lapV + uvv - (f + k) * state.V[i]
          }
        }
        state.U = U2
        state.V = V2
      }
      // Periodic injection every ~8s (keeps system active through param transitions)
      state.injectionTimer += 1
      if (state.injectionTimer > 80) {
        state.injectionTimer = 0
        const bx = 5 + Math.floor(Math.random() * (w - 10))
        const by = 5 + Math.floor(Math.random() * (h - 10))
        for (let dy = -2; dy <= 2; dy++) {
          for (let dx = -2; dx <= 2; dx++) {
            const yy = by + dy, xx = bx + dx
            if (yy >= 0 && yy < h && xx >= 0 && xx < w) {
              state.V[yy * w + xx] = 1
              state.U[yy * w + xx] = 0.4
            }
          }
        }
      }
    },
    gridPixel(s, x, y) {
      const { V, U, w } = s as { V: Float32Array; U: Float32Array; w: number }
      return clamp01(V[y * w + x] * 1.2 + (1 - U[y * w + x]) * 0.2)
    },
    palette(val, t) {
      // Primordial ocean: abyssal blue → teal → phosphorescent green → amber edges
      const v = val
      const hue = Math.sin(t * 0.1) * 0.2
      const r = cc(10 + 80 * v + 200 * Math.pow(Math.max(0, v - 0.7), 2))
      const g = cc(30 + 220 * v + 30 * Math.sin(v * 8 + t * 0.2))
      const b = cc(60 + 150 * v * (1 - v * 0.5) + 25 * hue)
      return [r, g, b] as const
    },
  },

  // 20. lightning — RAINY NIGHT WITH FARMHOUSE + LIGHTNING FLASHES
  {
    name: 'lightning',
    reflection: 'The sky remembers for one bright instant.',
    vibe: 'Rainy night, bright flash, farmhouse',
    frames: 300,
    tStep: 0.04,
    pixel(nx, ny, t) {
      // Strike cycle: period 9s, flash at 8.0-8.5
      const period = 9
      const cycT = t % period
      const isStrike = cycT > 7.95 && cycT < 8.15
      const isFlash = cycT > 7.95 && cycT < 8.6
      const flashIntensity = isFlash
        ? (cycT < 8.1 ? (cycT - 7.95) / 0.15 : Math.max(0, 1 - (cycT - 8.1) / 0.5))
        : 0
      const tension = (cycT > 7 && cycT < 7.95)
        ? (Math.sin((cycT - 7) * Math.PI / 0.95) * 0.1) * (Math.sin(t * 30) > 0 ? 1 : 0.3)
        : 0
      const ambient = 0.05 + tension
      // Sky — always visible slightly, bright during flash
      const horizon = 0.35
      let val = ambient
      if (ny < horizon) {
        const skyY = (ny + 1.8) / (horizon + 1.8)
        const clouds = fbm4(nx * 0.8 + t * 0.05, ny * 0.8)
        val += (skyY * 0.1 + clouds * 0.15) * (ambient + flashIntensity * 3)
      }
      // Rain — continuous diagonal streaks
      const rainAng = 0.3
      const rainX = nx * Math.cos(rainAng) + ny * Math.sin(rainAng)
      const rainY = -nx * Math.sin(rainAng) + ny * Math.cos(rainAng)
      const rainPattern = Math.sin(rainX * 35 + rainY * 12 - t * 9)
      const rain = rainPattern > 0.92 ? 0.3 + flashIntensity * 0.7 : 0
      val += rain * 0.3
      // Farmhouse (center of screen, just above horizon)
      const hBaseY = horizon
      const hTopY = horizon - 0.35
      const hLeftX = -0.4, hRightX = 0.1
      const inWalls = nx > hLeftX && nx < hRightX && ny > hTopY && ny < hBaseY
      // Roof (triangle)
      const roofBaseY = hTopY
      const roofTopY = hTopY - 0.18
      const roofLeftX = hLeftX - 0.05, roofRightX = hRightX + 0.05
      const inRoof = ny > roofTopY && ny < roofBaseY
        && nx > roofLeftX + (roofBaseY - ny) / (roofBaseY - roofTopY) * 0.03
        && nx < roofRightX - (roofBaseY - ny) / (roofBaseY - roofTopY) * 0.03
      // Chimney
      const inChimney = nx > -0.1 && nx < -0.02 && ny > -0.4 && ny < roofTopY + 0.1
      // Window (always glowing warm)
      const windowX = -0.15, windowY = hTopY + 0.13
      const windowD2 = (nx - windowX) ** 2 + (ny - windowY) ** 2
      const windowGlow = Math.exp(-windowD2 * 600) * (0.5 + 0.3 * Math.sin(t * 0.5))
      // Barn (right side)
      const inBarn = nx > 0.25 && nx < 0.6 && ny > hTopY + 0.05 && ny < hBaseY
      // Farmhouse visibility — very dim normally, bright during flash
      const structureBrightness = 0.08 + flashIntensity * 0.55
      if (inWalls || inRoof || inChimney || inBarn) val = Math.max(val, structureBrightness)
      val = Math.max(val, windowGlow * 1.2)
      // Distant hills silhouette (visible only during flash)
      if (ny > horizon - 0.08 && ny < horizon && flashIntensity > 0.1) {
        const hills = fbm4(nx * 1.5, 0.2)
        if (ny > horizon - 0.03 - hills * 0.05) val = Math.max(val, 0.15 + flashIntensity * 0.2)
      }
      // Ground (visible during flash)
      if (ny > horizon) {
        val = Math.max(val, 0.04 + flashIntensity * 0.3 + fbm4(nx * 2, ny * 2) * 0.08)
      }
      // Lightning bolt (fractal path from top)
      if (isStrike) {
        // Bolt center path — computed deterministically from strike cycle
        const strikeIdx = Math.floor(t / period)
        const boltStartX = (hash2d(strikeIdx, 7) - 0.5) * 2
        // Walk: sample along y from top to horizon, lateral jitter
        const targetY = horizon
        const segments = 8
        for (let k = 0; k < segments; k++) {
          const y0 = -1.8 + (k / segments) * (targetY + 1.8)
          const y1 = -1.8 + ((k + 1) / segments) * (targetY + 1.8)
          const jit0 = (hash2d(strikeIdx, k) - 0.5) * 0.4
          const jit1 = (hash2d(strikeIdx, k + 1) - 0.5) * 0.4
          const x0 = boltStartX + jit0 - ((k / segments) - 0.5) * 0.3
          const x1 = boltStartX + jit1 - (((k + 1) / segments) - 0.5) * 0.3
          // Distance from point (nx, ny) to line segment (x0,y0)-(x1,y1)
          if (ny >= y0 - 0.02 && ny <= y1 + 0.02) {
            const tt = clamp01((ny - y0) / (y1 - y0 + 1e-5))
            const lx = x0 + (x1 - x0) * tt
            const d = Math.abs(nx - lx)
            if (d < 0.008) val = Math.max(val, 0.98 * Math.max(0, 1 - d * 100))
            else if (d < 0.05) val = Math.max(val, 0.2 * Math.exp(-d * d * 800))
          }
        }
      }
      return clamp01(val)
    },
    palette(val, t) {
      const v = val
      const period = 9
      const cycT = t % period
      const isFlash = cycT > 7.95 && cycT < 8.6
      if (v > 0.9) {
        // Lightning core — brilliant blue-white
        return [cc(220 + 35 * v), cc(235 + 20 * v), 255] as const
      }
      if (isFlash && v > 0.15) {
        // Flash-lit scene — day colors (farmhouse, pyramids, hills revealed)
        const r = cc(50 + 170 * v)
        const g = cc(60 + 160 * v)
        const b = cc(90 + 120 * v)
        return [r, g, b] as const
      }
      if (v > 0.55) {
        // Warm window glow (always visible as the home's heartbeat)
        return [cc(220 + 35 * v), cc(130 + 60 * v), cc(40 + 40 * v)] as const
      }
      // Night base: deep navy, cool silver rain
      const r = cc(10 + 75 * v * v)
      const g = cc(22 + 90 * v * v)
      const b = cc(40 + 150 * v)
      return [r, g, b] as const
    },
  },

  // 21. nexus — HAM SPIFF (Hopf + Villarceau + orbiting particles + resonance)
  {
    name: 'nexus',
    reflection: 'Four dimensions whisper through three.',
    vibe: 'Hyperdimensional torus cascade',
    frames: 240,
    tStep: 0.06,
    init(w, h) {
      const particles: Array<{ u: number; v: number; torus: number; trail: Array<[number, number]> }> = []
      for (let i = 0; i < 220; i++) {
        particles.push({
          u: Math.random() * 2 * Math.PI,
          v: Math.random() * 2 * Math.PI,
          torus: i % 3,
          trail: [],
        })
      }
      return { w, h, grid: new Float32Array(w * h), mx: 1, particles }
    },
    update(s, t, _frame, w, h) {
      const state = s as {
        grid: Float32Array; mx: number; w: number; h: number
        particles: Array<{ u: number; v: number; torus: number; trail: Array<[number, number]> }>
      }
      state.grid.fill(0)
      const resonance = Math.pow(Math.abs(Math.sin(t * Math.PI / 14)), 20)
      const rotXY = t * 0.15
      const rotZW = t * 0.22
      const rotations = [
        { axis1: rotXY, axis2: rotZW },
        { axis1: rotXY + 1.1, axis2: rotZW - 0.7 },
        { axis1: rotXY - 0.6, axis2: rotZW + 0.4 },
      ]
      // Trace 3 nested tori via parametric sampling
      for (let tI = 0; tI < 3; tI++) {
        const R = 1.0 + tI * 0.25
        const r = 0.32
        const rot = rotations[tI]
        const uCount = 80
        const vCount = 30
        for (let iu = 0; iu < uCount; iu++) {
          const u = (iu / uCount) * 2 * Math.PI + rot.axis1 * 0.3
          for (let iv = 0; iv < vCount; iv++) {
            const v = (iv / vCount) * 2 * Math.PI + rot.axis2 * 0.3
            const x3 = (R + r * Math.cos(v)) * Math.cos(u)
            const y3 = (R + r * Math.cos(v)) * Math.sin(u)
            const z3 = r * Math.sin(v)
            // 3D rotation
            const c1 = Math.cos(rot.axis1), s1 = Math.sin(rot.axis1)
            const c2 = Math.cos(rot.axis2), s2 = Math.sin(rot.axis2)
            const x1 = x3 * c1 - y3 * s1
            const y1 = x3 * s1 + y3 * c1
            const z1 = z3 * c2 - x1 * s2
            const x2 = z3 * s2 + x1 * c2
            // Project (z + 3 = camera offset)
            const proj = 3 / (3 - z1)
            const px = x2 * proj
            const py = y1 * proj
            const gx = Math.floor((px * 0.22 + 0.5) * w)
            const gy = Math.floor((py * 0.22 + 0.5) * h)
            if (gx >= 0 && gx < w && gy >= 0 && gy < h) {
              state.grid[gy * w + gx] += 0.4 + resonance * 0.8
            }
          }
        }
      }
      // Orbiting particles with trails
      for (const p of state.particles) {
        p.v += 0.08
        p.u += 0.02
        const R = 1.0 + p.torus * 0.25
        const r = 0.32
        const rot = rotations[p.torus]
        const x3 = (R + r * Math.cos(p.v)) * Math.cos(p.u)
        const y3 = (R + r * Math.cos(p.v)) * Math.sin(p.u)
        const z3 = r * Math.sin(p.v)
        const c1 = Math.cos(rot.axis1), s1 = Math.sin(rot.axis1)
        const c2 = Math.cos(rot.axis2), s2 = Math.sin(rot.axis2)
        const x1 = x3 * c1 - y3 * s1
        const y1 = x3 * s1 + y3 * c1
        const z1 = z3 * c2 - x1 * s2
        const x2 = z3 * s2 + x1 * c2
        const proj = 3 / (3 - z1)
        const px = x2 * proj
        const py = y1 * proj
        const gx = Math.floor((px * 0.22 + 0.5) * w)
        const gy = Math.floor((py * 0.22 + 0.5) * h)
        p.trail.unshift([gx, gy])
        if (p.trail.length > 10) p.trail.pop()
        for (let ti = 0; ti < p.trail.length; ti++) {
          const [tx, ty] = p.trail[ti]
          if (tx >= 0 && tx < w && ty >= 0 && ty < h) {
            state.grid[ty * w + tx] += 3 * Math.pow(1 - ti / p.trail.length, 2)
          }
        }
      }
      let mx = 1
      for (let i = 0; i < state.grid.length; i++) if (state.grid[i] > mx) mx = state.grid[i]
      state.mx = mx
    },
    gridPixel(s, x, y) {
      const { grid, w, mx } = s as { grid: Float32Array; w: number; mx: number }
      return Math.min(1, grid[y * w + x] / Math.max(mx * 0.3, 1))
    },
    palette(val, t) {
      const hue = pymod(val * 6.28 + t * 0.25, 6.28)
      const r = cc((127 + 128 * Math.sin(hue)) * Math.pow(val, 0.8))
      const g = cc((127 + 128 * Math.sin(hue + 2.09)) * Math.pow(val, 0.8))
      const b = cc((127 + 128 * Math.sin(hue + 4.19)) * Math.pow(val, 0.8))
      return [r, g, b] as const
    },
  },

  // ─── NEW FORMULAS — BATCH 2026-04-22 ─────────────────────────────────────
  // 23. pod — dolphins leaping over sunset ocean
  {
    name: 'pod',
    reflection: 'Joy breaks the surface and returns to it.',
    vibe: 'Dolphins at sunset',
    frames: 300,
    tStep: 0.05,
    pixel(nx, ny, t) {
      const horizon = 0.1
      // Sky gradient + sunset sun
      let sky = 0
      if (ny < horizon) {
        const skyY = (ny + 1.8) / (horizon + 1.8)
        const clouds = fbm4(nx * 0.5 + t * 0.03, ny * 0.5) * 0.2
        sky = 0.25 + 0.45 * skyY + clouds
        const sunDist2 = nx * nx + (ny + 0.1) * (ny + 0.1)
        sky += Math.exp(-sunDist2 * 14) * 0.9
      }
      // Ocean waves
      let ocean = 0
      let waveY = horizon + 0.08 * Math.sin(nx * 3.5 + t) + 0.04 * Math.sin(nx * 8 - t * 1.3)
      if (ny > waveY) {
        const depth = ny - waveY
        ocean = 0.22 + 0.35 * (1 - Math.min(1, Math.abs(nx) * 0.3))
          + 0.18 * Math.sin(nx * 22 + t * 4) * Math.exp(-depth * 3)
          + 0.12 * Math.sin(nx * 8 - t * 2 + ny * 4)
      }
      // 4 dolphins on their own jump arcs
      let dolphins = 0
      for (let i = 0; i < 4; i++) {
        const period = 4.8 + i * 1.2
        const phase = ((t + i * 1.3) % period) / period
        if (phase > 0.18 && phase < 0.72) {
          const p = (phase - 0.18) / 0.54
          const dX = -1.7 + i * 0.75 + p * 1.0
          const dY = horizon - 0.36 * Math.sin(p * Math.PI)
          const angle = Math.atan2(-0.36 * Math.PI * Math.cos(p * Math.PI), 1)
          const cA = Math.cos(angle), sA = Math.sin(angle)
          const dx = nx - dX, dy = ny - dY
          const lx = dx * cA + dy * sA
          const ly = -dx * sA + dy * cA
          const body = Math.exp(-(lx * lx) / 0.014 - (ly * ly) / 0.0015)
          dolphins = Math.max(dolphins, body * 0.95)
          // Splashes at entry/exit
          if (p < 0.08 || p > 0.92) {
            const sx = -1.7 + i * 0.75 + (p < 0.08 ? 0 : 1.0)
            const sd2 = (nx - sx) ** 2 + (ny - horizon) ** 2
            dolphins = Math.max(dolphins, Math.exp(-sd2 * 55) * 0.55)
          }
        }
      }
      return clamp01(sky + ocean * 0.7 + dolphins)
    },
    palette(val, _t) {
      if (val > 0.88) return [cc(225 + 30 * val), cc(220 + 35 * val), cc(215 + 40 * val)] as const
      const v = val
      const r = cc(20 + 235 * Math.pow(v, 0.68) * (0.55 + 0.45 * Math.sin(v * 2.8)))
      const g = cc(18 + 130 * v + 80 * Math.pow(Math.max(0, v - 0.3), 1.5))
      const b = cc(48 + 180 * v * (1 - v * 0.42))
      return [r, g, b] as const
    },
  },

  // 24. fractal — infinite Mandelbrot zoom
  {
    name: 'fractal',
    reflection: 'Every point contains the whole.',
    vibe: 'Infinite self-similar descent',
    frames: 300,
    tStep: 0.04,
    pixel(nx, ny, t) {
      // Cyclic zoom toward a known deep seahorse valley
      const targetRe = -0.743643887037151
      const targetIm = 0.131825904205330
      const T = 30
      const phase = (t % T) / T
      const zoom = Math.pow(2, 2 + phase * 16) // 4× → 262144×
      const cx = targetRe + nx * 1.2 / zoom
      const cy = targetIm + ny * 1.2 / zoom
      let zr = 0, zi = 0
      let iter = 0
      const maxIter = 90
      while (iter < maxIter) {
        const nr = zr * zr - zi * zi + cx
        const ni = 2 * zr * zi + cy
        zr = nr; zi = ni
        if (zr * zr + zi * zi > 4) break
        iter++
      }
      if (iter >= maxIter) return 0
      // Smooth iteration count for gradient coloring
      const logZn = Math.log(zr * zr + zi * zi) / 2
      const nu = Math.log(logZn / Math.log(2)) / Math.log(2)
      const smooth = iter + 1 - nu
      return clamp01(smooth / maxIter + 0.05 * Math.sin(t * 0.2))
    },
    palette(val, t) {
      const v = val
      const hue = v * 8 + t * 0.15
      const r = cc(30 + 220 * Math.pow(v, 0.7) * (0.5 + 0.5 * Math.sin(hue)))
      const g = cc(20 + 200 * v * (0.5 + 0.5 * Math.sin(hue + 2.1)))
      const b = cc(50 + 200 * v * (0.5 + 0.5 * Math.sin(hue + 4.2)))
      return [r, g, b] as const
    },
  },

  // 25. matrix — cascading code with awakening glimpses
  {
    name: 'matrix',
    reflection: 'The code underneath the world.',
    vibe: 'Digital rain awakens',
    frames: 300,
    tStep: 0.05,
    pixel(nx, ny, t) {
      // Column-based rain: map nx to column index, each column has its own head y
      const colIdx = Math.floor((nx + 2) * 16)
      const colSpeed = 0.3 + hash2d(colIdx, 7) * 0.8
      const colLen = 0.8 + hash2d(colIdx, 13) * 0.6
      const headY = pymod(t * colSpeed - hash2d(colIdx, 19) * 3, 4.4) - 2.2
      const distFromHead = ny - headY
      let rain = 0
      if (distFromHead > 0 && distFromHead < colLen) {
        const tail = 1 - distFromHead / colLen
        rain = Math.pow(tail, 0.6)
        // Bright head
        if (distFromHead < 0.08) rain = 1
      }
      // Cell flicker (char change)
      const cellY = Math.floor(ny * 16)
      const flicker = hash2d(colIdx * 113 + cellY, Math.floor(t * 6))
      rain *= 0.4 + 0.6 * flicker
      // Awakening pulse every ~22s — symbol coalesces briefly at screen center
      const awakenPhase = (t % 22) / 22
      let awaken = 0
      if (awakenPhase > 0.85) {
        const p = (awakenPhase - 0.85) / 0.15
        const r2 = nx * nx + ny * ny
        awaken = Math.exp(-r2 * 4) * Math.sin(p * Math.PI) * 0.7
      }
      return clamp01(rain + awaken)
    },
    palette(val, _t) {
      const v = val
      if (v > 0.95) return [cc(200 + 55 * v), 255, cc(200 + 55 * v)] as const
      const r = cc(5 + 20 * v)
      const g = cc(15 + 240 * Math.pow(v, 0.7))
      const b = cc(8 + 30 * v)
      return [r, g, b] as const
    },
  },

  // 26. multiverse — branching timelines diverging
  {
    name: 'multiverse',
    reflection: 'Every choice is kept.',
    vibe: 'Parallel timelines branch',
    frames: 300,
    tStep: 0.05,
    pixel(nx, ny, t) {
      // 5 parallel universes — same pendulum, tiny perturbations that compound
      let totalR = 0, totalG = 0, totalB = 0
      const phaseBase = t * 0.6
      for (let u = 0; u < 5; u++) {
        const eps = (u - 2) * 0.003
        const phase = phaseBase * (1 + eps) + u * 0.04
        const r = Math.sqrt(nx * nx + ny * ny)
        const theta = Math.atan2(ny, nx)
        const wave1 = Math.sin(r * 8 - phase * 2)
        const wave2 = Math.cos(theta * 4 + phase)
        const wave3 = Math.sin((nx + ny) * 3 + phase * 0.7)
        const v = (wave1 * wave2 + wave3 + 2) / 4
        // Each universe gets a different hue
        const hue = u * 1.2 + t * 0.1
        totalR += v * (0.5 + 0.5 * Math.sin(hue)) * 0.2
        totalG += v * (0.5 + 0.5 * Math.sin(hue + 2.1)) * 0.2
        totalB += v * (0.5 + 0.5 * Math.sin(hue + 4.2)) * 0.2
      }
      return clamp01((totalR + totalG + totalB) / 3)
    },
    palette(val, t) {
      // Multi-channel ghost rendering — intentionally shifted RGB
      const v = val
      const r = cc(30 + 220 * v * (0.5 + 0.5 * Math.sin(v * 6 + t * 0.3)))
      const g = cc(40 + 210 * v * (0.5 + 0.5 * Math.sin(v * 6 + t * 0.3 + 2.1)))
      const b = cc(60 + 195 * v * (0.5 + 0.5 * Math.sin(v * 6 + t * 0.3 + 4.2)))
      return [r, g, b] as const
    },
  },

  // 27. holo — holographic reality with glitch
  {
    name: 'holo',
    reflection: 'The projection remembers its projector.',
    vibe: 'Holographic glitch cascade',
    frames: 300,
    tStep: 0.06,
    pixel(nx, ny, t) {
      // Rotating 3D cube projected + pixel grid shimmer
      const rotY = t * 0.4
      const rotX = t * 0.25
      const cY = Math.cos(rotY), sY = Math.sin(rotY)
      const cX = Math.cos(rotX), sX = Math.sin(rotX)
      // 12 cube edges — sample along each edge
      const verts: [number, number, number][] = [
        [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
        [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1],
      ]
      const edges: [number, number][] = [
        [0, 1], [1, 2], [2, 3], [3, 0],
        [4, 5], [5, 6], [6, 7], [7, 4],
        [0, 4], [1, 5], [2, 6], [3, 7],
      ]
      // Glitch: every ~7s, offset the image briefly
      const glitchPhase = (t % 7) / 7
      const glitching = glitchPhase > 0.95
      const offX = glitching ? (Math.random() - 0.5) * 0.3 : 0
      let cube = 0
      for (const [a, b] of edges) {
        const va = verts[a], vb = verts[b]
        const samples = 20
        for (let s = 0; s <= samples; s++) {
          const t2 = s / samples
          let x = va[0] + (vb[0] - va[0]) * t2
          let y = va[1] + (vb[1] - va[1]) * t2
          let z = va[2] + (vb[2] - va[2]) * t2
          // Y rotation
          const x1 = x * cY + z * sY
          const z1 = -x * sY + z * cY
          // X rotation
          const y1 = y * cX - z1 * sX
          const z2 = y * sX + z1 * cX
          const proj = 2.8 / (2.8 - z2)
          const px = x1 * proj * 0.35 + offX
          const py = y1 * proj * 0.35
          const d2 = (nx - px) ** 2 + (ny - py) ** 2
          cube = Math.max(cube, Math.exp(-d2 * 120))
        }
      }
      // Pixel grid shimmer
      const cellX = Math.floor(nx * 40), cellY = Math.floor(ny * 40)
      const shimmer = 0.15 + 0.15 * Math.sin(cellX * 0.7 + cellY * 0.9 + t * 3)
      return clamp01(cube * 0.9 + shimmer * 0.25 + (glitching ? 0.15 : 0))
    },
    palette(val, t) {
      const v = val
      // Chromatic aberration — each channel shifted by different hue
      const shift = Math.sin(t * 2) * 0.1
      const r = cc(30 + 225 * Math.pow(v, 0.8) * (0.5 + 0.5 * Math.sin(v * 8 + shift)))
      const g = cc(40 + 210 * v * (0.5 + 0.5 * Math.sin(v * 8 + 2 + shift * 1.2)))
      const b = cc(70 + 185 * Math.pow(v, 0.9) * (0.5 + 0.5 * Math.sin(v * 8 + 4 + shift * 0.8)))
      return [r, g, b] as const
    },
  },

  // 28. collapse — wavefunction cloud → point → cloud
  {
    name: 'collapse',
    reflection: 'Observation is the act of becoming.',
    vibe: 'Probability collapses into choice',
    frames: 300,
    tStep: 0.04,
    pixel(nx, ny, t) {
      const T = 8
      const phase = (t % T) / T
      // 0-0.4: cloud expanding · 0.4-0.55: collapse to point · 0.55-1: re-expanding
      let sigma: number
      if (phase < 0.4) {
        sigma = 0.5 + phase * 0.8
      } else if (phase < 0.55) {
        sigma = 0.82 * (1 - (phase - 0.4) / 0.15) + 0.02
      } else {
        sigma = 0.02 + (phase - 0.55) * 1.05
      }
      const r2 = nx * nx + ny * ny
      // Cloud (Gaussian)
      const cloud = Math.exp(-r2 / (sigma * sigma))
      // Interference fringes during cloud phase
      const wave = Math.sin(r2 * 20 - t * 3) * 0.3 + 0.7
      // Brief brilliant flash at collapse moment
      const flashStrength = phase > 0.42 && phase < 0.52 ? Math.sin((phase - 0.42) / 0.1 * Math.PI) : 0
      const flash = Math.exp(-r2 * 100) * flashStrength * 1.5
      return clamp01(cloud * wave + flash)
    },
    palette(val, t) {
      const v = val
      if (v > 0.92) return [255, 255, cc(240 + 15 * v)] as const
      const r = cc(30 + 220 * v * (0.4 + 0.6 * Math.sin(t * 0.4)))
      const g = cc(50 + 190 * v)
      const b = cc(90 + 165 * v + 30 * Math.sin(v * 6))
      return [r, g, b] as const
    },
  },

  // 29. dragon — Eastern dragon through clouds
  {
    name: 'dragon',
    reflection: 'The dragon is the path making itself.',
    vibe: 'Celestial serpent in clouds',
    frames: 300,
    tStep: 0.05,
    pixel(nx, ny, t) {
      // Cloud backdrop
      const clouds = fbm4(nx * 1.4 + t * 0.08, ny * 1.4 - t * 0.05)
      // Dragon body — sinuous parametric curve
      // Body is 60 segments along a sin path traveling across screen
      let body = 0
      const segs = 45
      const bodyPhase = t * 0.6
      for (let i = 0; i < segs; i++) {
        const s = i / segs
        const sPhase = bodyPhase - s * 3
        const bx = -2 + s * 4 - 0.3 * Math.sin(sPhase)
        const by = 0.8 * Math.sin(sPhase * 0.8) + 0.3 * Math.sin(sPhase * 2.1)
        const dx = nx - bx, dy = ny - by
        const d2 = dx * dx + dy * dy
        const thickness = 0.09 * (1 - s * 0.7)  // taper toward tail
        body = Math.max(body, Math.exp(-d2 / (thickness * thickness)) * (1 - s * 0.35))
        // Scale ripple
        body += 0.12 * Math.exp(-d2 / 0.003) * Math.sin(s * 30 - t * 4)
      }
      // Head glow (first segment)
      const headS = 0
      const headSPhase = bodyPhase
      const headX = -2 + headS * 4 - 0.3 * Math.sin(headSPhase)
      const headY = 0.8 * Math.sin(headSPhase * 0.8)
      const headD2 = (nx - headX) ** 2 + (ny - headY) ** 2
      const headGlow = Math.exp(-headD2 * 20) * 0.5
      // Horns / whiskers — simple lines extending from head
      const whisker1 = Math.exp(-((nx - headX - 0.15) ** 2) * 200 - ((ny - headY + 0.08) ** 2) * 80) * 0.3
      const whisker2 = Math.exp(-((nx - headX - 0.12) ** 2) * 200 - ((ny - headY - 0.08) ** 2) * 80) * 0.3
      return clamp01(clouds * 0.22 + body + headGlow + whisker1 + whisker2)
    },
    palette(val, t) {
      const v = val
      if (v > 0.85) return [cc(255), cc(220 + 35 * v), cc(90 + 50 * v)] as const  // gold dragon scales
      if (v > 0.55) {
        // Jade green mid-body
        const r = cc(20 + 120 * v)
        const g = cc(80 + 175 * v + 30 * Math.sin(t + v * 4))
        const b = cc(60 + 90 * v)
        return [r, g, b] as const
      }
      // Misty clouds
      const r = cc(40 + 90 * v)
      const g = cc(50 + 110 * v)
      const b = cc(80 + 140 * v)
      return [r, g, b] as const
    },
  },

  // 30. dmt — visionary hyperspace
  {
    name: 'dmt',
    reflection: 'The geometry is looking back.',
    vibe: 'Hyperspace entity realm',
    frames: 300,
    tStep: 0.1,
    pixel(nx, ny, t) {
      // Radial tunnel with n-fold symmetry
      const r = Math.sqrt(nx * nx + ny * ny)
      const theta = Math.atan2(ny, nx)
      // Tunnel depth — pulls inward over time
      const tunnelR = r / (1 + r * 0.5)
      const depth = 1 / (tunnelR + 0.1) + t * 0.8
      // 6-fold kaleidoscopic fold
      const fold = (2 * Math.PI) / 12
      const thetaFold = pymod(theta, fold) - fold / 2
      // Sacred geometry pattern
      const pattern1 = Math.sin(depth * 4 + thetaFold * 20)
      const pattern2 = Math.cos(depth * 3 - thetaFold * 12 + t)
      const pattern3 = Math.sin(depth * 8 + thetaFold * 8 - t * 1.5)
      const combined = (pattern1 * pattern2 + pattern3) * 0.6
      // Pulse rhythm
      const pulse = 0.8 + 0.3 * Math.sin(t * 3)
      const val = ((combined + 1.5) / 3) * pulse
      // Entity hints — occasional face-like pattern emerges
      const entityN = noise2d(thetaFold * 3 + t * 0.2, depth * 0.5)
      const entity = entityN > 0.85 ? (entityN - 0.85) * 4 : 0
      return clamp01(val + entity * 0.4)
    },
    palette(val, t) {
      // Hyper-vibrant rainbow cycling
      const v = val
      const hue = v * 8 + t * 0.8
      const r = cc(30 + 225 * (0.5 + 0.5 * Math.sin(hue)))
      const g = cc(40 + 215 * (0.5 + 0.5 * Math.sin(hue + 2.1)))
      const b = cc(50 + 205 * (0.5 + 0.5 * Math.sin(hue + 4.2)))
      return [r, g, b] as const
    },
  },

  // 31. bardo — death passage through the light
  {
    name: 'bardo',
    reflection: 'Between lives, only the light remains.',
    vibe: 'Passage through the clear light',
    frames: 300,
    tStep: 0.03,
    pixel(nx, ny, t) {
      const r = Math.sqrt(nx * nx + ny * ny)
      const theta = Math.atan2(ny, nx)
      // Zoom cycle: expanding tunnel toward light
      const T = 30
      const phase = (t % T) / T
      const zoom = 0.3 + phase * 2.5
      // Tunnel
      const tunnelR = r / zoom
      const tunnelIntensity = 1 - Math.min(1, tunnelR * 1.3)
      // Memory fragments floating on the sides (noise patches)
      const memNoise = fbm4(nx * 2 + t * 0.15, ny * 2 - t * 0.1)
      const memFade = (1 - tunnelIntensity) * 0.4
      const memory = memNoise > 0.65 ? (memNoise - 0.65) * 3 * memFade : 0
      // Peripheral light rings at certain radii
      const rings = Math.exp(-((tunnelR - 0.6) ** 2) * 15) * 0.4
        + Math.exp(-((tunnelR - 1.2) ** 2) * 15) * 0.25
      // Periodic flash — moments of recognition
      const flashPhase = (t % 6) / 6
      const flash = flashPhase < 0.05 ? Math.sin(flashPhase / 0.05 * Math.PI) * 0.35 : 0
      return clamp01(tunnelIntensity * 1.1 + rings + memory + flash)
    },
    palette(val, _t) {
      const v = val
      if (v > 0.88) return [255, cc(245 + 10 * v), cc(230 + 25 * v)] as const
      // Warm golden-white light → soft amber → dark velvet periphery
      const r = cc(10 + 240 * Math.pow(v, 0.65))
      const g = cc(8 + 230 * Math.pow(v, 0.75))
      const b = cc(15 + 200 * Math.pow(v, 1.1))
      return [r, g, b] as const
    },
  },

  // 32. now — Maezumi Roshi, single point of presence
  {
    name: 'now',
    reflection: 'This. Just this.',
    vibe: 'The present moment',
    frames: 240,
    tStep: 0.02,
    pixel(nx, ny, t) {
      const r2 = nx * nx + ny * ny
      // Single bright point at center with very subtle breath
      const breath = 1 + 0.05 * Math.sin(t * 0.35)
      const core = Math.exp(-r2 * 200 / (breath * breath))
      // Ultra-soft glow halo
      const halo = Math.exp(-r2 * 3) * 0.08
      // Subtle concentric breath rings
      const rings = Math.exp(-((Math.sqrt(r2) - 0.4 - 0.15 * Math.sin(t * 0.2)) ** 2) * 30) * 0.04
      // A single faint zen stroke, very subtle
      const strokeY = ny - 0.75 + 0.005 * Math.sin(t * 0.1)
      const strokeMask = nx > -0.5 && nx < 0.5 ? 1 : 0
      const stroke = Math.exp(-(strokeY * strokeY) * 2000) * strokeMask * 0.08
      return clamp01(core + halo + rings + stroke)
    },
    palette(val, _t) {
      // Ink on paper, warm white → deep black. Minimal.
      const v = Math.pow(val, 0.82)
      const r = cc(v * 250 + (1 - v) * 8)
      const g = cc(v * 244 + (1 - v) * 8)
      const b = cc(v * 230 + (1 - v) * 10)
      return [r, g, b] as const
    },
  },

  // 33. deep — deep time, geological strata compression
  {
    name: 'deep',
    reflection: 'Everything here is also very old.',
    vibe: 'Geological eons compressed',
    frames: 300,
    tStep: 0.04,
    pixel(nx, ny, t) {
      // Camera drifts downward through strata; each layer is a geological age
      const camY = t * 0.1
      const worldY = ny + camY
      // Stratum boundaries (non-uniform spacing)
      const stratumN = fbm4(nx * 0.3 + worldY * 2, worldY * 0.8)
      const bandFreq = 7 + 3 * Math.sin(worldY * 0.3)
      const band = Math.sin(worldY * bandFreq) * 0.5 + 0.5
      // Fine rock texture (sediment particles)
      const sediment = noise2d(nx * 12 + Math.floor(worldY * 20) * 0.2, worldY * 12) * 0.5
      // Fossil bumps — rare bright patches (very subtle hints of life)
      const fossilHash = hash2d(Math.floor(nx * 8), Math.floor(worldY * 6))
      const fossil = fossilHash > 0.985 ? 0.5 * (fossilHash - 0.985) * 66 : 0
      // Stars high above (when camY crosses into sky region)
      const skyBand = Math.sin(worldY * 0.1) // cycles through sky/strata
      const star = skyBand > 0.95 && noise2d(nx * 30, worldY * 30) > 0.97 ? 0.7 : 0
      // Occasional time marker flash (eon marker)
      const markerPhase = (t % 7) / 7
      const marker = markerPhase < 0.03 ? Math.sin(markerPhase / 0.03 * Math.PI) * 0.2 : 0
      const base = band * 0.55 + stratumN * 0.35 + sediment * 0.12
      return clamp01(base + fossil + star + marker)
    },
    palette(val, t) {
      const v = val
      if (v > 0.92) return [cc(240 + 15 * v), cc(235 + 20 * v), cc(200 + 40 * v)] as const
      // Rock palette: deep iron red → ochre → sandstone → midnight strata
      const stratumHue = Math.sin(t * 0.03 + v * 3)
      const r = cc(30 + 200 * Math.pow(v, 0.85) + 25 * stratumHue)
      const g = cc(15 + 140 * Math.pow(v, 1.0))
      const b = cc(10 + 80 * Math.pow(v, 1.3))
      return [r, g, b] as const
    },
  },

  // 22. luminous — SWIMMING OCTOPUS WITH A BEAUTIFUL BRAIN
  {
    name: 'luminous',
    reflection: 'A mind with eight arms dreams in color.',
    vibe: 'Octopus with a beautiful brain',
    frames: 300,
    tStep: 0.05,
    pixel(nx, ny, t) {
      // Body position drifts in figure-8
      const bodyX = 0.5 * Math.sin(t * 0.15)
      const bodyY = 0.3 * Math.sin(t * 0.22 + 1.3)
      // Jet pulse contraction every ~6s
      const jetPhase = (t % 6) / 6
      const jetContract = jetPhase < 0.07 ? 1 - jetPhase * 3 : 1
      // Mantle (head ovoid)
      const mantleR = 0.22 * jetContract * (1 + 0.03 * Math.sin(t * 1.5))
      const dx = nx - bodyX, dy = ny - bodyY
      const mantleD2 = (dx * dx) / (mantleR * mantleR) + (dy * dy) / (mantleR * mantleR * 1.4)
      const mantle = Math.exp(-mantleD2 * 1.5)
      // Brain glow inside mantle
      const brainD2 = (dx - 0.02) ** 2 + (dy + 0.03) ** 2
      const brain = Math.exp(-brainD2 * 180) * 0.85
      // Chromatophore noise on body
      const chromo = noise2d(nx * 6 + t * 0.5, ny * 6 - t * 0.3)
      const chromoWave = 0.5 + 0.5 * Math.sin(nx * 4 - t * 2 + chromo * 5)
      // 8 tentacles
      let tentacles = 0
      const baseY = bodyY + mantleR * 0.7
      for (let i = 0; i < 8; i++) {
        const baseAng = i * Math.PI / 4 - Math.PI / 2  // arms fan down/out
        const phaseOffset = i * 0.8
        const L = 0.9
        // Sample arm curve
        for (let s = 0; s < 20; s++) {
          const sRat = s / 20
          const tx = bodyX + Math.cos(baseAng) * sRat * L
            + 0.15 * sRat * Math.sin(sRat * 6 + t * 2.5 - phaseOffset)
          const ty = baseY + Math.sin(baseAng) * sRat * L * 0.6
            + 0.12 * sRat * Math.cos(sRat * 6 + t * 2.5 - phaseOffset)
          const armDx = nx - tx, armDy = ny - ty
          const armD2 = armDx * armDx + armDy * armDy
          const armThick = 0.04 * (1 - sRat * 0.7)
          tentacles = Math.max(tentacles, Math.exp(-armD2 / (armThick * armThick)) * (0.55 - sRat * 0.3))
        }
      }
      // Combine
      let val = Math.max(mantle * (0.6 + chromoWave * 0.4), tentacles)
      val = Math.max(val, brain * mantle)
      return clamp01(val)
    },
    palette(val, t) {
      // Deep abyss → indigo skin → iridescent chromatophore bursts → warm-white brain
      const v = val
      const chromoCycle = Math.sin(t * 0.5)
      // Chromatophore hue shift: sapphire → teal → violet → copper
      const hue = t * 0.25
      const r = cc(10 + 100 * v * (0.5 + 0.5 * Math.sin(hue + v * 3))
        + 180 * Math.pow(Math.max(0, v - 0.78), 2))
      const g = cc(15 + 80 * v + 120 * v * (0.5 + 0.5 * Math.sin(hue + 2 + v * 3)))
      const b = cc(40 + 200 * v * (0.6 + 0.4 * Math.sin(hue + 4 + v * 2))
        + 60 * Math.pow(Math.max(0, v - 0.7), 2))
      // Brain glow breakthrough at peak
      if (v > 0.82) {
        const pulse = 1 + chromoCycle * 0.15
        return [cc(220 * pulse), cc(210 * pulse), cc(180 * pulse)] as const
      }
      return [r, g, b] as const
    },
  },
]

// Index by name for fast lookup
export const ARCHETYPE_MAP: Record<string, Archetype> = {}
for (const a of ARCHETYPES) {
  ARCHETYPE_MAP[a.name] = a
}
