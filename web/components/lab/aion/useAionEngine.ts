import { useRef, useEffect, useCallback, useState } from 'react'

// ─── Types ────────────────────────────────────────────────────────────────────

export type Geometry = 'radial' | 'spiral' | 'horizontal' | 'vertical' | 'diamond' | 'hexagonal'

export interface AionControls {
  // Core
  ringCount: number
  invert: boolean
  geometry: Geometry
  // Op Art
  moireIntensity: number
  chromaticAberration: number
  kaleidoscope: number
  // Trippy
  feedbackLoop: number
  hueRotation: number
  hueSpeed: number
  motionGlow: number
  motionDistort: number
  edgeDetect: number
  posterize: number
  scanlines: number
  rgbTimeShift: number
  mirror: number
  colorInvert: boolean
  bloomIntensity: number
}

export const DEFAULT_CONTROLS: AionControls = {
  ringCount: 16,
  invert: true,
  geometry: 'radial',
  moireIntensity: 0.4,
  chromaticAberration: 0.3,
  kaleidoscope: 0,
  feedbackLoop: 0,
  hueRotation: 0,
  hueSpeed: 0,
  motionGlow: 0.3,
  motionDistort: 0,
  edgeDetect: 0,
  posterize: 0,
  scanlines: 0,
  rgbTimeShift: 0,
  mirror: 0,
  colorInvert: false,
  bloomIntensity: 0,
}

export interface PresetDef {
  name: string
  subtitle: string
  controls: Partial<AionControls>
}

export const PRESETS: PresetDef[] = [
  {
    name: 'AION',
    subtitle: 'Eternal return',
    controls: { ...DEFAULT_CONTROLS },
  },
  {
    name: 'KRONOS',
    subtitle: 'Devourer of time',
    controls: {
      ringCount: 32, invert: true, geometry: 'horizontal',
      feedbackLoop: 0.2, moireIntensity: 0.1, chromaticAberration: 0.15,
      motionGlow: 0.4, scanlines: 0.3,
    },
  },
  {
    name: 'KAIROS',
    subtitle: 'The decisive moment',
    controls: {
      ringCount: 8, invert: true, geometry: 'radial',
      feedbackLoop: 0.1, moireIntensity: 0.2, chromaticAberration: 0.1,
      motionGlow: 0.5, bloomIntensity: 0.3,
    },
  },
  {
    name: 'MORPHEUS',
    subtitle: 'Shaper of dreams',
    controls: {
      ringCount: 20, invert: true, geometry: 'spiral',
      feedbackLoop: 0.5, hueSpeed: 0.15, moireIntensity: 0.3,
      chromaticAberration: 0.4, bloomIntensity: 0.5, motionGlow: 0.3,
    },
  },
  {
    name: 'LETHE',
    subtitle: 'River of forgetting',
    controls: {
      ringCount: 48, invert: true, geometry: 'radial',
      feedbackLoop: 0.65, moireIntensity: 0.15, chromaticAberration: 0.2,
      bloomIntensity: 0.6, motionGlow: 0.2, hueSpeed: 0.05,
    },
  },
  {
    name: 'EREBUS',
    subtitle: 'Primordial darkness',
    controls: {
      ringCount: 24, invert: true, geometry: 'diamond',
      feedbackLoop: 0.3, edgeDetect: 0.6, moireIntensity: 0.5,
      chromaticAberration: 0.3, colorInvert: true, motionGlow: 0.4,
    },
  },
  {
    name: 'PSYCHE',
    subtitle: 'The soul perceiving',
    controls: {
      ringCount: 12, invert: true, geometry: 'radial',
      kaleidoscope: 6, feedbackLoop: 0.35, hueSpeed: 0.2,
      chromaticAberration: 0.5, motionGlow: 0.4, bloomIntensity: 0.3,
    },
  },
  {
    name: 'CHIMERA',
    subtitle: 'Impossible form',
    controls: {
      ringCount: 40, invert: true, geometry: 'hexagonal',
      rgbTimeShift: 0.6, feedbackLoop: 0.4, hueSpeed: 0.5,
      chromaticAberration: 0.7, motionDistort: 0.5, posterize: 5,
      motionGlow: 0.5,
    },
  },
  {
    name: 'KOSMOS',
    subtitle: 'Order from chaos',
    controls: {
      ringCount: 16, invert: true, geometry: 'spiral',
      kaleidoscope: 8, feedbackLoop: 0.25, moireIntensity: 0.4,
      chromaticAberration: 0.4, bloomIntensity: 0.4, motionGlow: 0.3,
    },
  },
  {
    name: 'APEIRON',
    subtitle: 'The boundless',
    controls: {
      ringCount: 64, invert: true, geometry: 'radial',
      feedbackLoop: 0.7, hueSpeed: 0.8, rgbTimeShift: 0.5,
      chromaticAberration: 0.8, motionGlow: 0.6, motionDistort: 0.3,
      bloomIntensity: 0.5, moireIntensity: 0.3,
    },
  },
  {
    name: 'ELYSIUM',
    subtitle: 'Fields of the blessed',
    controls: {
      ringCount: 14, invert: true, geometry: 'radial',
      feedbackLoop: 0.2, bloomIntensity: 0.6, moireIntensity: 0.2,
      chromaticAberration: 0.15, motionGlow: 0.6, hueRotation: 30,
      hueSpeed: 0.08,
    },
  },
]

// ─── Constants ────────────────────────────────────────────────────────────────

const CAPTURE_W = 320
const CAPTURE_H = 240
const BUFFER_SIZE = 120
const BYTES_PER_FRAME = CAPTURE_W * CAPTURE_H * 4

function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}

function clamp(v: number, lo: number, hi: number) { return v < lo ? lo : v > hi ? hi : v }

// ─── Geometry: compute normalized age from pixel position ─────────────────────

function computeAgeNorm(
  px: number, py: number, cx: number, cy: number,
  maxR: number, ringCount: number, geometry: Geometry,
): number {
  if (ringCount < 2) return 0
  const dx = px - cx, dy = py - cy

  switch (geometry) {
    case 'radial': {
      const r = Math.sqrt(dx * dx + dy * dy)
      const rNorm = Math.min(r / maxR, 1)
      const ring = Math.min(Math.floor(rNorm * ringCount), ringCount - 1)
      return ring / (ringCount - 1)
    }

    case 'spiral': {
      const r = Math.sqrt(dx * dx + dy * dy) / maxR
      const theta = (Math.atan2(dy, dx) + Math.PI) / (2 * Math.PI) // 0-1
      const turns = 3
      const spiralAge = (r + theta / turns) / (1 + 1 / turns)
      const ring = Math.min(Math.floor(Math.min(spiralAge, 1) * ringCount), ringCount - 1)
      return ring / (ringCount - 1)
    }

    case 'horizontal': {
      const yNorm = clamp(py / (cy * 2), 0, 1)
      const ring = Math.min(Math.floor(yNorm * ringCount), ringCount - 1)
      return ring / (ringCount - 1)
    }

    case 'vertical': {
      const xNorm = clamp(px / (cx * 2), 0, 1)
      const ring = Math.min(Math.floor(xNorm * ringCount), ringCount - 1)
      return ring / (ringCount - 1)
    }

    case 'diamond': {
      const d = (Math.abs(dx) + Math.abs(dy)) / maxR
      const dNorm = Math.min(d, 1)
      const ring = Math.min(Math.floor(dNorm * ringCount), ringCount - 1)
      return ring / (ringCount - 1)
    }

    case 'hexagonal': {
      const q = (2 / 3 * dx) / (maxR * 0.5)
      const r2 = (-1 / 3 * dx + Math.sqrt(3) / 3 * dy) / (maxR * 0.5)
      const hexDist = Math.min((Math.abs(q) + Math.abs(r2) + Math.abs(-q - r2)) / 2 / 2, 1)
      const ring = Math.min(Math.floor(hexDist * ringCount), ringCount - 1)
      return ring / (ringCount - 1)
    }

    default:
      return 0
  }
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useAionEngine(
  canvasRef: React.RefObject<HTMLCanvasElement | null>,
  controls: AionControls,
  shouldStart: boolean,
) {
  const controlsRef = useRef(controls)
  controlsRef.current = controls

  const [videoReady, setVideoReady] = useState(false)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const captureCanvasRef = useRef<HTMLCanvasElement | null>(null)
  const captureCtxRef = useRef<CanvasRenderingContext2D | null>(null)

  const bufferRef = useRef<Uint8ClampedArray[]>([])
  const bufferIndexRef = useRef(0)
  const frameCountRef = useRef(0)

  const prevFrameRef = useRef<Uint8ClampedArray | null>(null)
  const motionMapRef = useRef<Float32Array | null>(null)
  const feedbackRef = useRef<ImageData | null>(null)

  const collapseRef = useRef({ active: false, progress: 0, direction: 1 })
  const rafRef = useRef(0)
  const lastFrameRef = useRef(0)

  const collapse = useCallback(() => {
    if (!collapseRef.current.active) {
      collapseRef.current = { active: true, progress: 0, direction: 1 }
    }
  }, [])

  useEffect(() => {
    const buf: Uint8ClampedArray[] = []
    for (let i = 0; i < BUFFER_SIZE; i++) buf.push(new Uint8ClampedArray(BYTES_PER_FRAME))
    bufferRef.current = buf
    prevFrameRef.current = new Uint8ClampedArray(BYTES_PER_FRAME)
    motionMapRef.current = new Float32Array(CAPTURE_W * CAPTURE_H)
    const cc = document.createElement('canvas')
    cc.width = CAPTURE_W; cc.height = CAPTURE_H
    captureCanvasRef.current = cc
    captureCtxRef.current = cc.getContext('2d', { willReadFrequently: true })
  }, [])

  useEffect(() => {
    if (!shouldStart) return
    let cancelled = false
    async function start() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } }, audio: false,
        })
        if (cancelled) { stream.getTracks().forEach(t => t.stop()); return }
        streamRef.current = stream
        const video = document.createElement('video')
        video.srcObject = stream; video.playsInline = true; video.muted = true
        video.setAttribute('playsinline', '')
        try {
          await video.play()
        } catch (playErr) {
          console.error('Video play error:', playErr)
          stream.getTracks().forEach(t => t.stop())
          return
        }
        if (cancelled) { stream.getTracks().forEach(t => t.stop()); return }
        videoRef.current = video
        setVideoReady(true)
      } catch (err) { console.error('Webcam error:', err) }
    }
    start()
    return () => {
      cancelled = true
      streamRef.current?.getTracks().forEach(t => t.stop())
      streamRef.current = null; videoRef.current = null; setVideoReady(false)
    }
  }, [shouldStart])

  // ── Render loop ──────────────────────────────────────────────────────
  useEffect(() => {
    if (!videoReady || !canvasRef.current || !videoRef.current) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d', { alpha: false })!
    const video = videoRef.current!
    const captureCtx = captureCtxRef.current!

    const tempCanvas = document.createElement('canvas')
    const tempCtx = tempCanvas.getContext('2d')!

    let hueOffset = 0

    function renderFrame(timestamp: number) {
      if (timestamp - lastFrameRef.current < 30) { rafRef.current = requestAnimationFrame(renderFrame); return }
      lastFrameRef.current = timestamp
      const ctrl = controlsRef.current
      const W = canvas.width, H = canvas.height
      if (W === 0 || H === 0) { rafRef.current = requestAnimationFrame(renderFrame); return }

      // ── Capture ─────────────────────────────────────────────────────
      captureCtx.drawImage(video, 0, 0, CAPTURE_W, CAPTURE_H)
      const frameData = captureCtx.getImageData(0, 0, CAPTURE_W, CAPTURE_H)
      const idx = bufferIndexRef.current
      bufferRef.current[idx].set(frameData.data)
      bufferIndexRef.current = (idx + 1) % BUFFER_SIZE
      frameCountRef.current++

      // ── Motion detection ────────────────────────────────────────────
      const motionMap = motionMapRef.current!
      const prevFrame = prevFrameRef.current!
      const curData = frameData.data
      for (let i = 0; i < CAPTURE_W * CAPTURE_H; i++) {
        const si = i * 4
        const motion = (Math.abs(curData[si] - prevFrame[si]) + Math.abs(curData[si + 1] - prevFrame[si + 1]) + Math.abs(curData[si + 2] - prevFrame[si + 2])) / (255 * 3)
        motionMap[i] = motionMap[i] * 0.6 + motion * 0.4
      }
      prevFrame.set(curData)

      // ── Hue ─────────────────────────────────────────────────────────
      if (ctrl.hueSpeed > 0) hueOffset = (hueOffset + ctrl.hueSpeed * 2) % 360
      const totalHue = (ctrl.hueRotation + hueOffset) % 360

      // ── Collapse ────────────────────────────────────────────────────
      const col = collapseRef.current
      if (col.active) {
        col.progress += 0.04 * col.direction
        if (col.progress >= 1) { col.progress = 1; col.direction = -1 }
        else if (col.progress <= 0 && col.direction === -1) { col.progress = 0; col.active = false; col.direction = 1 }
      }
      const collapseAmount = col.active ? easeInOutCubic(col.progress) : 0

      // ── Core pixel loop ─────────────────────────────────────────────
      const output = ctx.createImageData(W, H)
      const outPx = output.data
      const cx = W / 2, cy = H / 2
      const maxR = Math.max(cx, cy) * 1.05
      const framesAvail = Math.min(frameCountRef.current, BUFFER_SIZE)
      const scaleX = CAPTURE_W / W, scaleY = CAPTURE_H / H
      const doRgbShift = ctrl.rgbTimeShift > 0.01

      // Pre-compute hue rotation matrix outside pixel loop
      const doHueRot = totalHue > 0.01
      let hm00 = 0, hm01 = 0, hm02 = 0, hm10 = 0, hm11 = 0, hm12 = 0, hm20 = 0, hm21 = 0, hm22 = 0
      if (doHueRot) {
        const rad = totalHue * Math.PI / 180, cos = Math.cos(rad), sin = Math.sin(rad)
        hm00 = 0.213 + cos * 0.787 - sin * 0.213; hm01 = 0.715 - cos * 0.715 - sin * 0.715; hm02 = 0.072 - cos * 0.072 + sin * 0.928
        hm10 = 0.213 - cos * 0.213 + sin * 0.143; hm11 = 0.715 + cos * 0.285 + sin * 0.140; hm12 = 0.072 - cos * 0.072 - sin * 0.283
        hm20 = 0.213 - cos * 0.213 - sin * 0.787; hm21 = 0.715 - cos * 0.715 + sin * 0.715; hm22 = 0.072 + cos * 0.928 + sin * 0.072
      }

      for (let py = 0; py < H; py++) {
        for (let px = 0; px < W; px++) {
          let ageNorm = computeAgeNorm(px, py, cx, cy, maxR, ctrl.ringCount, ctrl.geometry)

          // Motion distortion
          if (ctrl.motionDistort > 0.01) {
            const msx = clamp(Math.floor((W - 1 - px) * scaleX), 0, CAPTURE_W - 1)
            const msy = clamp(Math.floor(py * scaleY), 0, CAPTURE_H - 1)
            ageNorm = clamp(ageNorm + motionMap[msy * CAPTURE_W + msx] * ctrl.motionDistort * 0.5, 0, 1)
          }

          if (ctrl.invert) ageNorm = 1 - ageNorm
          ageNorm *= (1 - collapseAmount)

          // Mirror
          let mpx = px, mpy = py
          if (ctrl.mirror === 1 || ctrl.mirror === 3) mpx = px < cx ? px : W - 1 - px
          if (ctrl.mirror === 2 || ctrl.mirror === 3) mpy = py < cy ? py : H - 1 - py

          const srcX = clamp(Math.floor((W - 1 - mpx) * scaleX), 0, CAPTURE_W - 1)
          const srcY = clamp(Math.floor(mpy * scaleY), 0, CAPTURE_H - 1)
          const srcIdx = (srcY * CAPTURE_W + srcX) * 4

          let pR: number, pG: number, pB: number

          if (doRgbShift) {
            const ageR = clamp(ageNorm - ctrl.rgbTimeShift * 0.15, 0, 1)
            const ageB = clamp(ageNorm + ctrl.rgbTimeShift * 0.15, 0, 1)
            const fR = bufferRef.current[((bufferIndexRef.current - 1 - Math.floor(ageR * Math.max(framesAvail - 1, 0))) + BUFFER_SIZE * 10) % BUFFER_SIZE]
            const fG = bufferRef.current[((bufferIndexRef.current - 1 - Math.floor(ageNorm * Math.max(framesAvail - 1, 0))) + BUFFER_SIZE * 10) % BUFFER_SIZE]
            const fB = bufferRef.current[((bufferIndexRef.current - 1 - Math.floor(ageB * Math.max(framesAvail - 1, 0))) + BUFFER_SIZE * 10) % BUFFER_SIZE]
            pR = fR[srcIdx]; pG = fG[srcIdx + 1]; pB = fB[srcIdx + 2]
          } else {
            const age = Math.floor(ageNorm * Math.max(framesAvail - 1, 0))
            const frame = bufferRef.current[((bufferIndexRef.current - 1 - age) + BUFFER_SIZE * 10) % BUFFER_SIZE]
            pR = frame[srcIdx]; pG = frame[srcIdx + 1]; pB = frame[srcIdx + 2]
          }

          // Temporal color grading
          const warmth = 1 - ageNorm
          if (warmth > 0.5) { const w = (warmth - 0.5) * 2; pR = Math.min(255, pR + w * 20); pG = Math.min(255, pG + w * 5); pB = Math.max(0, pB - w * 15) }
          else { const c = (0.5 - warmth) * 2; pR = Math.max(0, pR - c * 30); pG = Math.max(0, pG - c * 10); pB = Math.min(255, pB + c * 25) }

          // Motion glow
          if (ctrl.motionGlow > 0.01) {
            const mi = clamp(Math.floor(py * scaleY), 0, CAPTURE_H - 1) * CAPTURE_W + clamp(Math.floor((W - 1 - px) * scaleX), 0, CAPTURE_W - 1)
            const m = motionMap[mi]
            if (m > 0.03) { const g = m * ctrl.motionGlow * 3; pR = Math.min(255, pR + g * 80); pG = Math.min(255, pG + g * 40); pB = Math.min(255, pB + g * 120) }
          }

          // Hue rotation (matrix pre-computed outside loop)
          if (doHueRot) {
            const nr = clamp(pR * hm00 + pG * hm01 + pB * hm02, 0, 255)
            const ng = clamp(pR * hm10 + pG * hm11 + pB * hm12, 0, 255)
            const nb = clamp(pR * hm20 + pG * hm21 + pB * hm22, 0, 255)
            pR = nr; pG = ng; pB = nb
          }

          // Posterize
          if (ctrl.posterize >= 2) { const l = ctrl.posterize; pR = Math.round(pR / 255 * (l - 1)) / (l - 1) * 255; pG = Math.round(pG / 255 * (l - 1)) / (l - 1) * 255; pB = Math.round(pB / 255 * (l - 1)) / (l - 1) * 255 }

          // Color invert
          if (ctrl.colorInvert) { pR = 255 - pR; pG = 255 - pG; pB = 255 - pB }

          const dstIdx = (py * W + px) * 4
          outPx[dstIdx] = pR; outPx[dstIdx + 1] = pG; outPx[dstIdx + 2] = pB; outPx[dstIdx + 3] = 255
        }
      }

      // ── Feedback loop ───────────────────────────────────────────────
      if (ctrl.feedbackLoop > 0.01 && feedbackRef.current && feedbackRef.current.width === W && feedbackRef.current.height === H) {
        const fb = feedbackRef.current.data, a = ctrl.feedbackLoop * 0.7
        for (let i = 0; i < outPx.length; i += 4) {
          outPx[i] = clamp(outPx[i] * (1 - a) + fb[i] * a, 0, 255)
          outPx[i + 1] = clamp(outPx[i + 1] * (1 - a) + fb[i + 1] * a, 0, 255)
          outPx[i + 2] = clamp(outPx[i + 2] * (1 - a) + fb[i + 2] * a, 0, 255)
        }
      }

      ctx.putImageData(output, 0, 0)

      // ── Edge detection (reuse outPx to avoid GPU readback) ─────────
      if (ctrl.edgeDetect > 0.01) {
        const ed = outPx
        const edgeOut = ctx.createImageData(W, H); const eo = edgeOut.data
        for (let y = 1; y < H - 1; y++) {
          for (let x = 1; x < W - 1; x++) {
            const i = (y * W + x) * 4, l = (y * W + x - 1) * 4, r = (y * W + x + 1) * 4, u = ((y - 1) * W + x) * 4, d = ((y + 1) * W + x) * 4
            const gx = Math.abs(ed[r] - ed[l]) + Math.abs(ed[r + 1] - ed[l + 1]) + Math.abs(ed[r + 2] - ed[l + 2])
            const gy = Math.abs(ed[d] - ed[u]) + Math.abs(ed[d + 1] - ed[u + 1]) + Math.abs(ed[d + 2] - ed[u + 2])
            const e = Math.min(255, (gx + gy) / 3); eo[i] = e; eo[i + 1] = e; eo[i + 2] = e; eo[i + 3] = 255
          }
        }
        tempCanvas.width = W; tempCanvas.height = H; tempCtx.putImageData(edgeOut, 0, 0)
        ctx.globalCompositeOperation = 'screen'; ctx.globalAlpha = ctrl.edgeDetect * 0.7
        ctx.drawImage(tempCanvas, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over'
      }

      // ── Scanlines ───────────────────────────────────────────────────
      if (ctrl.scanlines > 0.01) { ctx.fillStyle = `rgba(0,0,0,${ctrl.scanlines * 0.3})`; for (let y = 0; y < H; y += 3) ctx.fillRect(0, y, W, 1) }

      // ── Chromatic aberration ─────────────────────────────────────────
      if (ctrl.chromaticAberration > 0.01) {
        const ab = ctrl.chromaticAberration * 0.015
        tempCanvas.width = W; tempCanvas.height = H; tempCtx.drawImage(canvas, 0, 0)
        ctx.globalCompositeOperation = 'screen'
        ctx.save(); ctx.translate(cx, cy); ctx.scale(1 + ab, 1 + ab); ctx.translate(-cx, -cy); ctx.drawImage(tempCanvas, 0, 0); ctx.restore()
        ctx.save(); ctx.translate(cx, cy); ctx.scale(1 - ab * 0.5, 1 - ab * 0.5); ctx.translate(-cx, -cy); ctx.drawImage(tempCanvas, 0, 0); ctx.restore()
        ctx.globalAlpha = 0.55; ctx.globalCompositeOperation = 'source-over'; ctx.drawImage(tempCanvas, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over'
      }

      // ── Moire ───────────────────────────────────────────────────────
      if (ctrl.moireIntensity > 0.01) {
        const t = timestamp / 4000 * Math.PI * 2, p1 = 22, p2 = 24, a = ctrl.moireIntensity * 0.35
        ctx.globalCompositeOperation = 'overlay'; ctx.strokeStyle = `rgba(255,255,255,${a})`; ctx.lineWidth = 1
        for (let r2 = p1; r2 < maxR * 1.5; r2 += p1) { ctx.beginPath(); ctx.arc(cx, cy, r2, 0, Math.PI * 2); ctx.stroke() }
        ctx.save(); ctx.translate(cx, cy); ctx.rotate(Math.sin(t) * 0.08); ctx.translate(-cx, -cy)
        ctx.strokeStyle = `rgba(255,255,255,${a * 0.8})`
        for (let r2 = p2; r2 < maxR * 1.5; r2 += p2) { ctx.beginPath(); ctx.arc(cx, cy, r2, 0, Math.PI * 2); ctx.stroke() }
        ctx.restore(); ctx.globalCompositeOperation = 'source-over'
      }

      // ── Bloom ───────────────────────────────────────────────────────
      if (ctrl.bloomIntensity > 0.01) {
        tempCanvas.width = W; tempCanvas.height = H
        tempCtx.filter = `blur(${8 + ctrl.bloomIntensity * 12}px) brightness(${1.2 + ctrl.bloomIntensity * 0.5})`
        tempCtx.drawImage(canvas, 0, 0); tempCtx.filter = 'none'
        ctx.globalCompositeOperation = 'screen'; ctx.globalAlpha = ctrl.bloomIntensity * 0.5
        ctx.drawImage(tempCanvas, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over'
      }

      // ── Kaleidoscope ────────────────────────────────────────────────
      if (ctrl.kaleidoscope > 0) {
        const segs = ctrl.kaleidoscope, sa = (2 * Math.PI) / segs
        tempCanvas.width = W; tempCanvas.height = H; tempCtx.drawImage(canvas, 0, 0)
        ctx.clearRect(0, 0, W, H); ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H)
        for (let i = 0; i < segs; i++) {
          ctx.save(); ctx.translate(cx, cy); ctx.rotate(i * sa); if (i % 2 === 1) ctx.scale(-1, 1)
          ctx.beginPath(); ctx.moveTo(0, 0); ctx.arc(0, 0, maxR * 2, 0, sa); ctx.closePath(); ctx.clip()
          ctx.drawImage(tempCanvas, -cx, -cy); ctx.restore()
        }
      }

      // ── Collapse flash ──────────────────────────────────────────────
      if (col.active && col.progress > 0.3) {
        ctx.fillStyle = `rgba(254,243,199,${(col.progress - 0.3) / 0.7 * 0.15 * (col.direction === 1 ? 1 : 0.3)})`
        ctx.fillRect(0, 0, W, H)
      }

      // ── Vignette ────────────────────────────────────────────────────
      const vig = ctx.createRadialGradient(cx, cy, maxR * 0.5, cx, cy, maxR * 1.1)
      vig.addColorStop(0, 'rgba(0,0,0,0)'); vig.addColorStop(1, 'rgba(0,0,0,0.5)')
      ctx.fillStyle = vig; ctx.fillRect(0, 0, W, H)

      // ── Save feedback ───────────────────────────────────────────────
      if (ctrl.feedbackLoop > 0.01) feedbackRef.current = ctx.getImageData(0, 0, W, H)

      rafRef.current = requestAnimationFrame(renderFrame)
    }

    rafRef.current = requestAnimationFrame(renderFrame)
    return () => { cancelAnimationFrame(rafRef.current) }
  }, [videoReady, canvasRef])

  return { videoReady, collapse }
}
