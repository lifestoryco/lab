"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import EnsoCanvas, { ensoPositionAt } from "./EnsoCanvas";
import ShrineDrawer from "./ShrineDrawer";
import { MASTERS_SORTED, type Master } from "./masters";

const PAINT_DURATION_MS = 5200;
const HANKO_REVEAL_PAD = 0.02; // seals appear once paint passes their u + pad

export default function ShrinePage() {
  const [progress, setProgress] = useState(0);
  const [selected, setSelected] = useState<Master | null>(null);
  const [dimensions, setDimensions] = useState({ w: 0, h: 0 });
  const [reducedMotion, setReducedMotion] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  // Paint-in animation on mount (or instant if reduced motion)
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const rm = mq.matches;
    setReducedMotion(rm);
    if (rm) {
      setProgress(1);
      return;
    }
    const start = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / PAINT_DURATION_MS);
      // ease-out cubic — slower near completion, like a brush lifting
      const eased = 1 - Math.pow(1 - t, 3);
      setProgress(eased);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  // Track container dims for hanko positioning
  useEffect(() => {
    const el = rootRef.current;
    if (!el) return;
    const update = () => {
      setDimensions({ w: el.clientWidth, h: el.clientHeight });
    };
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Keyboard: ESC closes drawer
  useEffect(() => {
    if (!selected) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSelected(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selected]);

  const hankoPositions = useMemo(() => {
    const { w, h } = dimensions;
    if (!w || !h) return [];
    const cx = w / 2;
    const cy = h / 2;
    const radius = Math.min(w, h) * 0.34;
    // Offset seals outward from the stroke center so they sit *on* the paint
    const seals = MASTERS_SORTED.map((m, i) => {
      const u = i / MASTERS_SORTED.length;
      const p = ensoPositionAt(u, cx, cy, radius);
      // Place on a slightly larger radius so they sit on the outer edge of the stroke
      const dx = p.x - cx;
      const dy = p.y - cy;
      const len = Math.sqrt(dx * dx + dy * dy);
      const outward = 1.02;
      return {
        master: m,
        u,
        x: cx + (dx / len) * radius * outward,
        y: cy + (dy / len) * radius * outward * 0.985,
      };
    });
    return seals;
  }, [dimensions]);

  return (
    <div
      ref={rootRef}
      className="relative h-screen w-screen overflow-hidden"
      style={{ backgroundColor: "#F3ECDB", cursor: "default" }}
    >
      {/* Canvas layer */}
      <div className="absolute inset-0">
        <EnsoCanvas progress={progress} reducedMotion={reducedMotion} />
      </div>

      {/* Hanko seals layer */}
      <div className="absolute inset-0 pointer-events-none">
        {hankoPositions.map(({ master, u, x, y }) => {
          const revealed = progress >= u - HANKO_REVEAL_PAD;
          return (
            <Hanko
              key={master.id}
              master={master}
              x={x}
              y={y}
              revealed={revealed}
              onClick={() => setSelected(master)}
            />
          );
        })}
      </div>

      {/* Chrome — title top-left */}
      <div className="pointer-events-none absolute left-8 top-8 z-10 md:left-12 md:top-12">
        <h1
          className="text-xs uppercase tracking-[0.32em]"
          style={{
            color: "#4A4237",
            fontFamily: "var(--font-display)",
          }}
        >
          The Shrine
        </h1>
        <p
          className="mt-1 max-w-[22ch] text-[0.7rem] leading-[1.55]"
          style={{
            color: "#6A5A40",
            fontFamily: "'Cormorant Garamond', Georgia, serif",
            fontStyle: "italic",
          }}
        >
          An archive of the awakened. Press a seal to enter.
        </p>
      </div>

      {/* Chrome — attribution bottom-right */}
      <div className="pointer-events-none absolute bottom-8 right-8 z-10 text-right md:bottom-12 md:right-12">
        <p
          className="text-[0.65rem] uppercase tracking-[0.28em]"
          style={{ color: "#8A7050", fontFamily: "var(--font-display)" }}
        >
          Made by Sean Ivins
        </p>
      </div>

      {/* Chrome — timeline legend bottom-left */}
      <div className="pointer-events-none absolute bottom-8 left-8 z-10 md:bottom-12 md:left-12">
        <p
          className="text-[0.65rem] uppercase tracking-[0.28em]"
          style={{ color: "#8A7050", fontFamily: "var(--font-display)" }}
        >
          {MASTERS_SORTED[0].deathYear} — {MASTERS_SORTED[MASTERS_SORTED.length - 1].deathYear}
        </p>
        <p
          className="mt-1 text-[0.65rem] tracking-[0.12em]"
          style={{ color: "#A0896A", fontFamily: "var(--font-display)" }}
        >
          {MASTERS_SORTED.length} masters · one breath
        </p>
      </div>

      {/* Shrine drawer */}
      <ShrineDrawer master={selected} onClose={() => setSelected(null)} />
    </div>
  );
}

type HankoProps = {
  master: Master;
  x: number;
  y: number;
  revealed: boolean;
  onClick: () => void;
};

function Hanko({ master, x, y, revealed, onClick }: HankoProps) {
  const [hovered, setHovered] = useState(false);
  const [pressed, setPressed] = useState(false);

  const size = 46;

  return (
    <div
      className="absolute"
      style={{
        left: x - size / 2,
        top: y - size / 2,
        width: size,
        height: size,
        pointerEvents: revealed ? "auto" : "none",
        opacity: revealed ? 1 : 0,
        transform: `scale(${revealed ? 1 : 0.6})`,
        transition: `opacity 0.7s cubic-bezier(0.22, 1, 0.36, 1), transform 0.7s cubic-bezier(0.22, 1, 0.36, 1)`,
      }}
    >
      <button
        onClick={onClick}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => {
          setHovered(false);
          setPressed(false);
        }}
        onMouseDown={() => setPressed(true)}
        onMouseUp={() => setPressed(false)}
        aria-label={`Open ${master.primaryName}`}
        className="relative flex h-full w-full items-center justify-center rounded-[6px]"
        style={{
          backgroundColor: pressed ? "#8A0016" : "#B8001F",
          color: "#FFFFFF",
          boxShadow: hovered
            ? "0 2px 0 0 rgba(138,0,22,0.4), 0 4px 12px -2px rgba(184,0,31,0.35), inset 0 0 0 1px rgba(255,255,255,0.08)"
            : "0 1px 0 0 rgba(138,0,22,0.3), inset 0 0 0 1px rgba(255,255,255,0.06)",
          transform: `scale(${pressed ? 0.94 : hovered ? 1.06 : 1})`,
          transition: "all 180ms cubic-bezier(0.22, 1, 0.36, 1)",
          cursor: "pointer",
          // subtle rotation per master for hand-pressed feel
          filter: `brightness(${hovered ? 1.08 : 1})`,
        }}
      >
        {/* Inscription — script name or initial */}
        <span
          className="select-none leading-none"
          style={{
            fontFamily:
              "'Noto Serif JP', 'Noto Serif Tibetan', 'Cormorant Garamond', serif",
            fontSize: master.scriptName && master.scriptName.length <= 2 ? 18 : 12,
            fontWeight: 600,
            color: "#FFFFFF",
            opacity: 0.94,
            textShadow: "0 1px 0 rgba(0,0,0,0.15)",
          }}
        >
          {master.scriptName
            ? master.scriptName.slice(0, 2)
            : master.primaryName.slice(0, 2)}
        </span>

        {/* Ink bleed ring — always visible, stronger on hover */}
        <span
          aria-hidden="true"
          className="pointer-events-none absolute"
          style={{
            inset: -4,
            borderRadius: 9,
            background:
              "radial-gradient(circle, rgba(184,0,31,0.18) 30%, rgba(184,0,31,0) 70%)",
            opacity: hovered ? 1 : 0.5,
            transition: "opacity 200ms ease",
          }}
        />
      </button>

      {/* Tooltip */}
      {hovered && (
        <div
          className="pointer-events-none absolute left-1/2 -translate-x-1/2 whitespace-nowrap"
          style={{
            top: size + 10,
            fontFamily: "'Cormorant Garamond', Georgia, serif",
            fontSize: 13,
            color: "#0A0705",
            backgroundColor: "rgba(251, 247, 238, 0.96)",
            border: "1px solid #D6C8A5",
            padding: "4px 10px",
            borderRadius: 4,
            boxShadow: "0 4px 12px -4px rgba(42,34,24,0.2)",
          }}
        >
          <span style={{ fontWeight: 500 }}>{master.primaryName}</span>
          <span style={{ color: "#8A7050", marginLeft: 6, fontSize: 11 }}>
            {master.lifespan}
          </span>
        </div>
      )}
    </div>
  );
}
