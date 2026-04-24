'use client'

import { useState, useRef, useEffect, useId } from 'react'
import { createPortal } from 'react-dom'
import { type AionControls, type Geometry, DEFAULT_CONTROLS, PRESETS } from './useAionEngine'

interface AionControlsProps {
  controls: AionControls
  onChange: (controls: AionControls) => void
}

const gold = (a: number) => `rgba(201,169,98,${a})`

const GEOMETRIES: { value: Geometry; label: string }[] = [
  { value: 'radial', label: 'RADIAL' },
  { value: 'spiral', label: 'SPIRAL' },
  { value: 'horizontal', label: 'HORIZ' },
  { value: 'vertical', label: 'VERT' },
  { value: 'diamond', label: 'DIAMOND' },
  { value: 'hexagonal', label: 'HEX' },
]

export default function AionControlsPanel({ controls, onChange }: AionControlsProps) {
  const [panelOpen, setPanelOpen] = useState(false)
  const [activePreset, setActivePreset] = useState(0)
  const [mounted, setMounted] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => { setMounted(true) }, [])

  function update(key: keyof AionControls, value: number | boolean | string) {
    onChange({ ...controls, [key]: value })
  }

  function applyPreset(index: number) {
    const preset = PRESETS[index]
    if (preset) {
      onChange({ ...DEFAULT_CONTROLS, ...preset.controls } as AionControls)
      setActivePreset(index)
    }
  }

  function reset() {
    onChange({ ...DEFAULT_CONTROLS })
    setActivePreset(0)
  }

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const active = el.children[activePreset] as HTMLElement | undefined
    if (active) active.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' })
  }, [activePreset])

  // ── Full control panel (portaled to escape stacking context) ─────
  const panel = panelOpen && mounted ? createPortal(
    <div
      style={{
        position: 'fixed',
        bottom: 'calc(max(12px, env(safe-area-inset-bottom, 12px)) + 90px)',
        left: '50%',
        transform: 'translateX(-50%)',
        width: 'min(420px, calc(100vw - 24px))',
        maxHeight: 'calc(100vh - 180px)',
        overflowY: 'auto',
        backgroundColor: 'rgba(8,8,12,0.92)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        border: `1px solid ${gold(0.15)}`,
        borderRadius: '8px',
        padding: '20px',
        zIndex: 39,
        animation: 'aion-slide-up 250ms ease forwards',
        scrollbarWidth: 'thin' as const,
      }}
    >
      {/* Panel header with close button */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: '16px', paddingBottom: '12px',
        borderBottom: `1px solid ${gold(0.1)}`,
      }}>
        <div style={{
          fontSize: '10px', letterSpacing: '0.3em', color: gold(0.6),
          fontFamily: 'monospace',
        }}>
          PARAMETERS
        </div>
        <button
          onClick={() => setPanelOpen(false)}
          aria-label="Close controls panel"
          style={{
            background: 'none', border: 'none', cursor: 'pointer', padding: '4px',
            color: gold(0.5), transition: 'color 0.2s ease',
          }}
          onMouseEnter={e => { e.currentTarget.style.color = gold(0.9) }}
          onMouseLeave={e => { e.currentTarget.style.color = gold(0.5) }}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M4 4L12 12M12 4L4 12" strokeLinecap="round" />
          </svg>
        </button>
      </div>

      {/* ── Geometry ─────────────────────────────────────────────── */}
      <SectionLabel>GEOMETRY</SectionLabel>
      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginBottom: '16px' }}>
        {GEOMETRIES.map(g => (
          <button
            key={g.value}
            onClick={() => update('geometry', g.value)}
            style={{
              flex: '1 0 auto',
              minWidth: '52px',
              padding: '5px 8px',
              fontSize: '9px',
              fontFamily: 'monospace',
              letterSpacing: '0.08em',
              color: controls.geometry === g.value ? gold(0.95) : 'rgba(100,116,139,0.6)',
              backgroundColor: controls.geometry === g.value ? gold(0.12) : 'transparent',
              border: `1px solid ${controls.geometry === g.value ? gold(0.35) : 'rgba(255,255,255,0.06)'}`,
              borderRadius: '4px',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            {g.label}
          </button>
        ))}
      </div>

      {/* ── Core ─────────────────────────────────────────────────── */}
      <SectionLabel>CORE</SectionLabel>
      <Slider label="TIME DEPTH" value={controls.ringCount} min={4} max={64} step={1} display={`${controls.ringCount}`} onChange={v => update('ringCount', v)} />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <Label>{controls.invert ? 'PAST INWARD' : 'PRESENT INWARD'}</Label>
        <Toggle value={controls.invert} onChange={v => update('invert', v)} />
      </div>

      {/* ── Op Art ───────────────────────────────────────────────── */}
      <SectionLabel>OP ART</SectionLabel>
      <Slider label="MOIRE" value={controls.moireIntensity} min={0} max={1} step={0.05} display={pct(controls.moireIntensity)} onChange={v => update('moireIntensity', v)} />
      <Slider label="CHROMATIC" value={controls.chromaticAberration} min={0} max={1} step={0.05} display={pct(controls.chromaticAberration)} onChange={v => update('chromaticAberration', v)} />
      <Slider label="BLOOM" value={controls.bloomIntensity} min={0} max={1} step={0.05} display={pct(controls.bloomIntensity)} onChange={v => update('bloomIntensity', v)} />
      <div style={{ marginBottom: '12px' }}>
        <Label>KALEIDOSCOPE</Label>
        <PillGroup options={[0, 3, 6, 8, 12]} labels={['Off', '3', '6', '8', '12']} value={controls.kaleidoscope} onChange={v => update('kaleidoscope', v)} />
      </div>

      {/* ── Trippy ──────────────────────────────────────────────── */}
      <SectionLabel>TRIPPY</SectionLabel>
      <Slider label="FEEDBACK LOOP" value={controls.feedbackLoop} min={0} max={1} step={0.05} display={pct(controls.feedbackLoop)} onChange={v => update('feedbackLoop', v)} />
      <Slider label="RGB TIME SHIFT" value={controls.rgbTimeShift} min={0} max={1} step={0.05} display={pct(controls.rgbTimeShift)} onChange={v => update('rgbTimeShift', v)} />
      <Slider label="HUE ROTATION" value={controls.hueRotation} min={0} max={360} step={5} display={`${Math.round(controls.hueRotation)}\u00B0`} onChange={v => update('hueRotation', v)} />
      <Slider label="HUE SPEED" value={controls.hueSpeed} min={0} max={1} step={0.05} display={pct(controls.hueSpeed)} onChange={v => update('hueSpeed', v)} />
      <Slider label="POSTERIZE" value={controls.posterize} min={0} max={8} step={1} display={controls.posterize === 0 ? 'Off' : `${controls.posterize}`} onChange={v => update('posterize', v)} />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <Label>COLOR INVERT</Label>
        <Toggle value={controls.colorInvert} onChange={v => update('colorInvert', v)} />
      </div>

      {/* ── Motion ──────────────────────────────────────────────── */}
      <SectionLabel>MOTION</SectionLabel>
      <Slider label="MOTION GLOW" value={controls.motionGlow} min={0} max={1} step={0.05} display={pct(controls.motionGlow)} onChange={v => update('motionGlow', v)} />
      <Slider label="MOTION DISTORT" value={controls.motionDistort} min={0} max={1} step={0.05} display={pct(controls.motionDistort)} onChange={v => update('motionDistort', v)} />
      <Slider label="EDGE DETECT" value={controls.edgeDetect} min={0} max={1} step={0.05} display={pct(controls.edgeDetect)} onChange={v => update('edgeDetect', v)} />

      {/* ── FX ──────────────────────────────────────────────────── */}
      <SectionLabel>FX</SectionLabel>
      <Slider label="SCANLINES" value={controls.scanlines} min={0} max={1} step={0.05} display={pct(controls.scanlines)} onChange={v => update('scanlines', v)} />
      <div style={{ marginBottom: '12px' }}>
        <Label>MIRROR</Label>
        <PillGroup options={[0, 1, 2, 3]} labels={['Off', 'H', 'V', 'Quad']} value={controls.mirror} onChange={v => update('mirror', v)} />
      </div>

      {/* ── Reset ───────────────────────────────────────────────── */}
      <div style={{ borderTop: `1px solid ${gold(0.08)}`, paddingTop: '16px', marginTop: '8px' }}>
        <button
          onClick={reset}
          style={{
            width: '100%', padding: '10px', fontSize: '10px', fontFamily: 'monospace',
            letterSpacing: '0.15em', color: 'rgba(239,100,100,0.7)',
            backgroundColor: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.15)',
            borderRadius: '4px', cursor: 'pointer', transition: 'all 0.15s ease',
          }}
          onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'rgba(239,68,68,0.15)' }}
          onMouseLeave={e => { e.currentTarget.style.backgroundColor = 'rgba(239,68,68,0.06)' }}
        >
          RESET TO DEFAULT
        </button>
      </div>

      <style>{`
        @keyframes aion-slide-up {
          from { opacity: 0; transform: translateX(-50%) translateY(16px); }
          to { opacity: 1; transform: translateX(-50%) translateY(0); }
        }
      `}</style>
    </div>,
    document.body,
  ) : null

  return (
    <>
      {/* ── Preset bar (always visible at bottom) ────────────────── */}
      <div
        style={{
          position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 40,
          background: 'linear-gradient(to top, rgba(5,5,5,0.95) 0%, rgba(5,5,5,0.8) 70%, transparent 100%)',
          paddingBottom: 'max(12px, env(safe-area-inset-bottom, 12px))', paddingTop: '20px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '10px' }}>
          <button
            onClick={() => setPanelOpen(!panelOpen)}
            aria-label={panelOpen ? 'Close controls' : 'Open controls'}
            style={{
              background: 'none', border: 'none', cursor: 'pointer', padding: '6px 16px',
              display: 'flex', alignItems: 'center', gap: '6px', opacity: 0.4,
              transition: 'opacity 0.3s ease',
            }}
            onMouseEnter={e => { e.currentTarget.style.opacity = '0.8' }}
            onMouseLeave={e => { e.currentTarget.style.opacity = '0.4' }}
          >
            <svg
              width="14" height="14" viewBox="0 0 14 14" fill="none" stroke={gold(0.8)} strokeWidth="1.5"
              style={{ transition: 'transform 0.3s ease', transform: panelOpen ? 'rotate(180deg)' : 'none' }}
            >
              <path d="M3 9L7 5L11 9" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span style={{ fontSize: '9px', letterSpacing: '0.25em', color: gold(0.6), fontFamily: 'monospace' }}>
              {panelOpen ? 'CLOSE' : 'CONTROLS'}
            </span>
          </button>
        </div>

        <div
          ref={scrollRef}
          style={{
            display: 'flex', gap: '8px', overflowX: 'auto', overflowY: 'hidden',
            paddingLeft: '16px', paddingRight: '16px', paddingBottom: '4px',
            scrollSnapType: 'x mandatory', WebkitOverflowScrolling: 'touch',
            scrollbarWidth: 'none' as const,
          }}
        >
          {PRESETS.map((preset, i) => {
            const active = activePreset === i
            return (
              <button
                key={preset.name}
                onClick={() => applyPreset(i)}
                aria-label={`${preset.name}: ${preset.subtitle}`}
                style={{
                  flexShrink: 0, scrollSnapAlign: 'center', padding: '8px 16px', minWidth: '90px',
                  textAlign: 'center',
                  backgroundColor: active ? gold(0.1) : 'rgba(255,255,255,0.03)',
                  border: `1px solid ${active ? gold(0.5) : 'rgba(255,255,255,0.06)'}`,
                  borderRadius: '4px', cursor: 'pointer', transition: 'all 0.2s ease',
                }}
                onMouseEnter={e => {
                  if (!active) { e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.06)'; e.currentTarget.style.borderColor = gold(0.25) }
                }}
                onMouseLeave={e => {
                  if (!active) { e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.03)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)' }
                }}
              >
                <div style={{
                  fontSize: '11px', fontFamily: 'monospace', letterSpacing: '0.15em',
                  color: active ? gold(0.95) : 'rgba(232,220,200,0.5)',
                  fontWeight: active ? 500 : 400, marginBottom: '2px',
                }}>{preset.name}</div>
                <div style={{
                  fontSize: '8px', letterSpacing: '0.08em',
                  color: active ? gold(0.5) : 'rgba(255,255,255,0.2)', fontStyle: 'italic',
                }}>{preset.subtitle}</div>
              </button>
            )
          })}
          <button
            onClick={() => setPanelOpen(true)}
            aria-label="Open custom controls"
            style={{
              flexShrink: 0, scrollSnapAlign: 'center', padding: '8px 16px', minWidth: '80px',
              textAlign: 'center', backgroundColor: 'rgba(255,255,255,0.02)',
              border: '1px dashed rgba(255,255,255,0.1)', borderRadius: '4px',
              cursor: 'pointer', transition: 'all 0.2s ease',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = gold(0.3) }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)' }}
          >
            <div style={{ fontSize: '11px', fontFamily: 'monospace', letterSpacing: '0.1em', color: 'rgba(255,255,255,0.25)' }}>+</div>
            <div style={{ fontSize: '8px', color: 'rgba(255,255,255,0.15)', letterSpacing: '0.06em' }}>custom</div>
          </button>
        </div>
      </div>

      {panel}
    </>
  )
}

// ─── Shared UI ──────────────────────────────────────────────────────────────────

function pct(v: number) { return `${Math.round(v * 100)}%` }

const labelCSS: React.CSSProperties = {
  fontSize: '10px', letterSpacing: '0.18em', color: 'rgba(232,220,200,0.35)',
  marginBottom: '6px', fontFamily: 'monospace',
}
const sectionCSS: React.CSSProperties = {
  fontSize: '9px', letterSpacing: '0.25em', color: gold(0.5),
  marginBottom: '10px', marginTop: '16px', fontFamily: 'monospace',
  borderBottom: `1px solid ${gold(0.08)}`, paddingBottom: '6px',
}

function SectionLabel({ children }: { children: React.ReactNode }) { return <div style={sectionCSS}>{children}</div> }
function Label({ children }: { children: React.ReactNode }) { return <div style={labelCSS}>{children}</div> }

function Slider({ label, value, min, max, step, display, onChange }: {
  label: string; value: number; min: number; max: number; step: number; display: string; onChange: (v: number) => void
}) {
  const id = useId()
  const pctFill = ((value - min) / (max - min)) * 100
  return (
    <div style={{ marginBottom: '12px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <label htmlFor={id} style={labelCSS}>{label}</label>
        <div style={{ fontSize: '11px', fontFamily: 'monospace', color: gold(0.4) }}>{display}</div>
      </div>
      <input
        id={id} type="range" min={min} max={max} step={step} value={value}
        aria-label={label} aria-valuemin={min} aria-valuemax={max} aria-valuenow={value}
        onChange={e => onChange(Number(e.target.value))}
        style={{
          width: '100%', height: '3px', appearance: 'none', WebkitAppearance: 'none',
          background: `linear-gradient(to right, ${gold(0.4)} ${pctFill}%, rgba(255,255,255,0.06) ${pctFill}%)`,
          borderRadius: '2px', outline: 'none', cursor: 'pointer',
        }}
      />
    </div>
  )
}

function Toggle({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!value)}
      aria-pressed={value}
      style={{
        width: '40px', height: '22px', borderRadius: '11px', border: 'none',
        backgroundColor: value ? gold(0.25) : 'rgba(255,255,255,0.08)',
        cursor: 'pointer', position: 'relative', transition: 'background-color 0.3s ease',
      }}
    >
      <div style={{
        width: '16px', height: '16px', borderRadius: '50%',
        backgroundColor: value ? gold(0.9) : 'rgba(150,150,150,0.5)',
        position: 'absolute', top: '3px', left: value ? '21px' : '3px',
        transition: 'all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)',
      }} />
    </button>
  )
}

function PillGroup({ options, labels, value, onChange }: {
  options: number[]; labels: string[]; value: number; onChange: (v: number) => void
}) {
  return (
    <div style={{ display: 'flex', gap: '4px' }}>
      {options.map((n, i) => (
        <button
          key={n} onClick={() => onChange(n)}
          style={{
            flex: 1, padding: '5px 0', fontSize: '10px', fontFamily: 'monospace',
            letterSpacing: '0.05em',
            color: value === n ? gold(0.95) : 'rgba(100,116,139,0.5)',
            backgroundColor: value === n ? gold(0.1) : 'transparent',
            border: `1px solid ${value === n ? gold(0.3) : 'rgba(255,255,255,0.06)'}`,
            borderRadius: '4px', cursor: 'pointer', transition: 'all 0.15s ease',
          }}
        >{labels[i]}</button>
      ))}
    </div>
  )
}
