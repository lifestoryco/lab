"use client";

import { useEffect, useRef } from "react";

type Props = {
  /** 0..1 — paint progress along the ensō */
  progress: number;
  /** color of the ink (warm near-black) */
  inkColor?: string;
  /** color of wet bleed (slightly warmer) */
  wetColor?: string;
  /** washi background */
  washiColor?: string;
  /** reduced motion — skip breath cycle */
  reducedMotion?: boolean;
};

const PATH_POINTS = 512;
const RADIAL_SEGMENTS = 8;

export default function EnsoCanvas({
  progress,
  inkColor = "#15100A",
  wetColor = "#2A1810",
  washiColor = "#F3ECDB",
  reducedMotion = false,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const washiRef = useRef<HTMLCanvasElement | null>(null);
  const rafRef = useRef<number | null>(null);
  const progressRef = useRef(progress);
  const displayProgressRef = useRef(0);
  const startTimeRef = useRef<number>(0);

  // Keep latest progress in a ref so the RAF loop always reads the current target
  useEffect(() => {
    progressRef.current = progress;
  }, [progress]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const resize = () => {
      const { clientWidth: w, clientHeight: h } = canvas;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      washiRef.current = buildWashi(w, h, washiColor);
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    startTimeRef.current = performance.now();

    const loop = (now: number) => {
      const { clientWidth: w, clientHeight: h } = canvas;
      const cx = w / 2;
      const cy = h / 2;
      const radius = Math.min(w, h) * 0.34;

      // Damped display progress
      const target = progressRef.current;
      displayProgressRef.current += (target - displayProgressRef.current) * 0.06;
      const p = displayProgressRef.current;

      // Breath cycle — ±3% on ink alpha
      const elapsed = (now - startTimeRef.current) / 1000;
      const breath = reducedMotion
        ? 0
        : Math.sin(elapsed * 0.6) * 0.03;

      // Clear
      ctx.clearRect(0, 0, w, h);

      // Paint washi base
      if (washiRef.current) {
        ctx.drawImage(washiRef.current, 0, 0, w, h);
      }

      // Draw ensō with multi-pass wet ink
      drawEnso(ctx, {
        cx,
        cy,
        radius,
        progress: p,
        inkColor,
        wetColor,
        breath,
      });

      rafRef.current = requestAnimationFrame(loop);
    };
    rafRef.current = requestAnimationFrame(loop);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      ro.disconnect();
    };
  }, [inkColor, wetColor, washiColor, reducedMotion]);

  return (
    <canvas
      ref={canvasRef}
      className="block h-full w-full"
      aria-hidden="true"
    />
  );
}

// ========================================================================
// Washi background — rendered once per resize to an offscreen canvas
// ========================================================================
function buildWashi(w: number, h: number, baseColor: string): HTMLCanvasElement {
  const off = document.createElement("canvas");
  off.width = Math.max(1, Math.floor(w));
  off.height = Math.max(1, Math.floor(h));
  const ctx = off.getContext("2d");
  if (!ctx) return off;

  // Warm radial base
  const grad = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, Math.max(w, h) * 0.75);
  grad.addColorStop(0, "#FBF7EE");
  grad.addColorStop(0.6, baseColor);
  grad.addColorStop(1, "#E8DEC4");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, w, h);

  // Fiber specks — long thin strokes like rice-paper fibers
  const fiberCount = Math.floor((w * h) / 6500);
  ctx.lineCap = "round";
  for (let i = 0; i < fiberCount; i++) {
    const x = Math.random() * w;
    const y = Math.random() * h;
    const len = 8 + Math.random() * 36;
    const a = Math.random() * Math.PI * 2;
    const dark = Math.random() < 0.5;
    ctx.strokeStyle = dark
      ? `rgba(90, 70, 45, ${0.04 + Math.random() * 0.04})`
      : `rgba(255, 250, 235, ${0.06 + Math.random() * 0.08})`;
    ctx.lineWidth = 0.4 + Math.random() * 0.6;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + Math.cos(a) * len, y + Math.sin(a) * len);
    ctx.stroke();
  }

  // Speckle noise
  const speckCount = Math.floor((w * h) / 900);
  for (let i = 0; i < speckCount; i++) {
    const x = Math.random() * w;
    const y = Math.random() * h;
    const alpha = Math.random() * 0.05;
    ctx.fillStyle = `rgba(60, 45, 25, ${alpha})`;
    ctx.fillRect(x, y, 1, 1);
  }

  // Subtle vignette
  const vignette = ctx.createRadialGradient(w / 2, h / 2, Math.min(w, h) * 0.3, w / 2, h / 2, Math.max(w, h) * 0.7);
  vignette.addColorStop(0, "rgba(0,0,0,0)");
  vignette.addColorStop(1, "rgba(60, 40, 20, 0.18)");
  ctx.fillStyle = vignette;
  ctx.fillRect(0, 0, w, h);

  return off;
}

// ========================================================================
// Ensō — parametric closed curve with varied thickness, multi-pass wet ink
// ========================================================================
type EnsoOpts = {
  cx: number;
  cy: number;
  radius: number;
  progress: number;
  inkColor: string;
  wetColor: string;
  breath: number;
};

function drawEnso(ctx: CanvasRenderingContext2D, o: EnsoOpts) {
  const { cx, cy, radius, progress, inkColor, wetColor, breath } = o;
  if (progress <= 0) return;

  const startAngle = -Math.PI / 2 - 0.15; // top, slightly offset like a real ensō
  const sweep = Math.PI * 2 * progress;
  const points: Array<{ x: number; y: number; thickness: number; u: number }> = [];

  for (let i = 0; i <= PATH_POINTS; i++) {
    const u = i / PATH_POINTS;
    const a = startAngle + u * sweep;
    // eccentric radius + low-frequency noise
    const wobble =
      Math.sin(a * 3.1) * 0.018 +
      Math.cos(a * 7.3) * 0.01 +
      Math.sin(a * 13.7) * 0.004;
    const r = radius * (1 + wobble);
    // thickness ramps in, peaks, tails off (calligrapher's stroke)
    const thickness =
      thicknessProfile(u, progress) * (0.85 + 0.15 * Math.sin(u * 21.0));
    points.push({
      x: cx + Math.cos(a) * r,
      y: cy + Math.sin(a) * r * 0.985, // slight flatten
      thickness,
      u,
    });
  }

  // --- Pass 1: wet bleed halo (wide, low alpha) ---
  ctx.save();
  ctx.globalCompositeOperation = "multiply";
  ctx.strokeStyle = hexToRgba(wetColor, 0.09 + breath);
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1];
    const b = points[i];
    const w = (a.thickness + b.thickness) * 0.5 * radius * 0.16;
    ctx.lineWidth = w;
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  ctx.restore();

  // --- Pass 2: body of ink (medium width, higher alpha) ---
  ctx.save();
  ctx.globalCompositeOperation = "multiply";
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1];
    const b = points[i];
    const w = (a.thickness + b.thickness) * 0.5 * radius * 0.055;
    ctx.strokeStyle = hexToRgba(inkColor, 0.72 + breath);
    ctx.lineWidth = w;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  ctx.restore();

  // --- Pass 3: sharp core (thin, opaque) ---
  ctx.save();
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1];
    const b = points[i];
    const w = Math.max(0.6, (a.thickness + b.thickness) * 0.5 * radius * 0.012);
    ctx.strokeStyle = hexToRgba(inkColor, 0.95);
    ctx.lineWidth = w;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  ctx.restore();

  // --- Pass 4: ink splatter at brush tip ---
  if (progress < 1) {
    const tip = points[points.length - 1];
    drawSplatter(ctx, tip.x, tip.y, radius * 0.04, inkColor);
  }
}

function thicknessProfile(u: number, progress: number): number {
  // u is position along the drawn path 0..1
  // Ramp in from 0..0.05, peak around 0.2..0.7, taper 0.7..1
  // Also fade out the final segments when the path is still being drawn
  const ramp = smoothstep(0, 0.05, u);
  const body = 1 - Math.pow(Math.abs(u - 0.45) / 0.55, 2) * 0.3;
  const taper = 1 - smoothstep(0.85, 1.0, u) * 0.6;
  // Leading edge fade only matters when progress < 1
  const drawingEdge =
    progress < 1 ? 1 - smoothstep(progress - 0.02, progress, u) : 1;
  return ramp * body * taper * drawingEdge;
}

function smoothstep(a: number, b: number, x: number): number {
  const t = Math.max(0, Math.min(1, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
}

function drawSplatter(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  maxRadius: number,
  color: string
) {
  ctx.save();
  ctx.globalCompositeOperation = "multiply";
  for (let i = 0; i < 6; i++) {
    const angle = Math.random() * Math.PI * 2;
    const dist = Math.random() * maxRadius;
    const r = 0.4 + Math.random() * 1.6;
    ctx.fillStyle = hexToRgba(color, 0.3 + Math.random() * 0.4);
    ctx.beginPath();
    ctx.arc(x + Math.cos(angle) * dist, y + Math.sin(angle) * dist, r, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

function hexToRgba(hex: string, a: number): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${a})`;
}

// Exports for positioning hanko seals along the same curve
export function ensoPositionAt(
  u: number,
  cx: number,
  cy: number,
  radius: number
): { x: number; y: number } {
  const startAngle = -Math.PI / 2 - 0.15;
  const a = startAngle + u * Math.PI * 2;
  const wobble =
    Math.sin(a * 3.1) * 0.018 +
    Math.cos(a * 7.3) * 0.01 +
    Math.sin(a * 13.7) * 0.004;
  const r = radius * (1 + wobble);
  return {
    x: cx + Math.cos(a) * r,
    y: cy + Math.sin(a) * r * 0.985,
  };
}

// Unused exports kept for future use (wet/splatter tuning, RADIAL_SEGMENTS for 3D upgrade)
export { RADIAL_SEGMENTS };
