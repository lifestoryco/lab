// Audio engine for Signal.
// Runs on Tone.js AudioWorklet thread, decoupled from render loop.
// All timing goes through Tone.Transport for sample-accurate scheduling.
//
// Audio layers:
//   1. FMSynth voices (5 per world, melodic, user-driven via block placement)
//   2. MembraneSynth kick drum — four-on-the-floor, always present during
//      play. Pitch shifts per world; the pulse is the game's clock.
//   3. Monster motif — a 4-note ostinato that loops every 2 bars when a
//      monster is alive. Memorable, world-specific.
//   4. Level-entry flourish — 3 notes from the world's scale on enter.

import * as Tone from 'tone'
import { getGameState, useGameStore } from '../engine/useGameStore'
import { midiToNoteName } from './scales'
import { GRID_COLS, blockKey } from '../utils/isoMath'

// --- Instrument Definitions ---
// Phase 1: Handpan-inspired FMSynth for all 5 instrument slots.
// Phase 4 will differentiate per-world.

let instruments: Tone.PolySynth[] = []
let kick: Tone.MembraneSynth | null = null
let motifSynth: Tone.PolySynth | null = null
let flourishSynth: Tone.PolySynth | null = null
let reverb: Tone.Reverb
let delay: Tone.PingPongDelay
let compressor: Tone.Compressor
let effectsBus: Tone.Channel
let initialized = false
let currentWorldIndex = 0

// Beat bus — 4n tick counter + subscribers. Used by useCage to step the
// monster in lock-step with the transport (fixes wall-clock drift).
let beatCounter = 0
type BeatSub = (step: number, time: number) => void
const beatSubs = new Set<BeatSub>()
export function onBeat(fn: BeatSub): () => void {
  beatSubs.add(fn)
  return () => { beatSubs.delete(fn) }
}

// Whether the monster motif should loop this session (set by cage hook).
let motifActive = false
export function setMotifActive(active: boolean) {
  motifActive = active
}

// Instrument colors for the selector dots (B&W for world 1)
export const INSTRUMENT_COLORS = [
  '#ffffff', // Slot 0 — white
  '#cccccc', // Slot 1 — light gray
  '#999999', // Slot 2 — mid gray
  '#666666', // Slot 3 — dark gray
  '#333333', // Slot 4 — near black
]

export const INSTRUMENT_NAMES = [
  'Slot 0',
  'Slot 1',
  'Slot 2',
  'Slot 3',
  'Slot 4',
]

// Per-world instrument configs for the 5 synthesis slots
function getWorldInstrumentConfigs(worldIndex: number) {
  switch (worldIndex) {
    case 0: // The Signal — metallic, alien, cold
      return [
        {
          type: 'FMSynth' as const,
          harmonicity: 4.5,
          modulationIndex: 2.8,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.0005, decay: 1.0, sustain: 0, release: 1.2 },
          modulation: { type: 'sine' as const },
          modulationEnvelope: { attack: 0.001, decay: 0.7, sustain: 0, release: 0.4 },
          maxPolyphony: 8,
        },
        {
          type: 'FMSynth' as const,
          harmonicity: 2.5,
          modulationIndex: 3.5,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.002, decay: 1.5, sustain: 0, release: 1.0 },
          modulation: { type: 'triangle' as const },
          modulationEnvelope: { attack: 0.005, decay: 1.0, sustain: 0, release: 0.6 },
          maxPolyphony: 6,
        },
        {
          type: 'FMSynth' as const,
          harmonicity: 7.0,
          modulationIndex: 3.2,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.0003, decay: 0.4, sustain: 0, release: 0.5 },
          modulation: { type: 'sine' as const },
          modulationEnvelope: { attack: 0.0005, decay: 0.2, sustain: 0, release: 0.3 },
          maxPolyphony: 8,
        },
        {
          type: 'FMSynth' as const,
          harmonicity: 3.0,
          modulationIndex: 2.0,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.001, decay: 0.9, sustain: 0, release: 0.9 },
          modulation: { type: 'sine' as const },
          modulationEnvelope: { attack: 0.002, decay: 0.5, sustain: 0, release: 0.5 },
          maxPolyphony: 7,
        },
        {
          type: 'FMSynth' as const,
          harmonicity: 0.6,
          modulationIndex: 2.2,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.0015, decay: 1.2, sustain: 0, release: 0.8 },
          modulation: { type: 'sine' as const },
          modulationEnvelope: { attack: 0.003, decay: 0.8, sustain: 0, release: 0.4 },
          maxPolyphony: 6,
        },
      ]
    case 1: // The Temple — classical, sacred, resonant
      return [
        {
          type: 'FMSynth' as const,
          harmonicity: 1.5,
          modulationIndex: 1.8,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.01, decay: 2.0, sustain: 0.1, release: 1.5 },
          modulation: { type: 'sine' as const },
          modulationEnvelope: { attack: 0.01, decay: 1.2, sustain: 0, release: 0.8 },
          maxPolyphony: 6,
        },
        {
          type: 'FMSynth' as const,
          harmonicity: 2.0,
          modulationIndex: 1.5,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.012, decay: 1.8, sustain: 0.1, release: 1.3 },
          modulation: { type: 'sine' as const },
          modulationEnvelope: { attack: 0.012, decay: 1.0, sustain: 0, release: 0.7 },
          maxPolyphony: 5,
        },
        {
          type: 'FMSynth' as const,
          harmonicity: 0.9,
          modulationIndex: 2.0,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.008, decay: 2.2, sustain: 0.15, release: 1.6 },
          modulation: { type: 'sine' as const },
          modulationEnvelope: { attack: 0.008, decay: 1.3, sustain: 0, release: 0.8 },
          maxPolyphony: 5,
        },
        {
          type: 'FMSynth' as const,
          harmonicity: 1.2,
          modulationIndex: 1.6,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.015, decay: 1.9, sustain: 0.1, release: 1.4 },
          modulation: { type: 'sine' as const },
          modulationEnvelope: { attack: 0.015, decay: 1.1, sustain: 0, release: 0.7 },
          maxPolyphony: 5,
        },
        {
          type: 'FMSynth' as const,
          harmonicity: 1.8,
          modulationIndex: 1.3,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.018, decay: 2.0, sustain: 0.12, release: 1.5 },
          modulation: { type: 'sine' as const },
          modulationEnvelope: { attack: 0.018, decay: 1.2, sustain: 0, release: 0.8 },
          maxPolyphony: 4,
        },
      ]
    case 2: // The Deep — underwater, mysterious, sustaining
      return [
        {
          type: 'FMSynth' as const,
          harmonicity: 0.5,
          modulationIndex: 1.5,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.02, decay: 3.0, sustain: 0.2, release: 2.0 },
          modulation: { type: 'sine' as const },
          modulationEnvelope: { attack: 0.02, decay: 1.8, sustain: 0.1, release: 1.0 },
          maxPolyphony: 4,
        },
        {
          type: 'FMSynth' as const,
          harmonicity: 0.7,
          modulationIndex: 1.3,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.025, decay: 2.8, sustain: 0.25, release: 1.8 },
          modulation: { type: 'sine' as const },
          modulationEnvelope: { attack: 0.025, decay: 1.6, sustain: 0.1, release: 0.9 },
          maxPolyphony: 4,
        },
        {
          type: 'FMSynth' as const,
          harmonicity: 0.4,
          modulationIndex: 1.8,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.015, decay: 3.5, sustain: 0.3, release: 2.2 },
          modulation: { type: 'sine' as const },
          modulationEnvelope: { attack: 0.015, decay: 2.0, sustain: 0.15, release: 1.1 },
          maxPolyphony: 4,
        },
        {
          type: 'FMSynth' as const,
          harmonicity: 0.6,
          modulationIndex: 1.4,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.022, decay: 3.2, sustain: 0.22, release: 1.9 },
          modulation: { type: 'sine' as const },
          modulationEnvelope: { attack: 0.022, decay: 1.7, sustain: 0.1, release: 0.95 },
          maxPolyphony: 4,
        },
        {
          type: 'FMSynth' as const,
          harmonicity: 0.8,
          modulationIndex: 1.2,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.03, decay: 3.0, sustain: 0.25, release: 1.8 },
          modulation: { type: 'sine' as const },
          modulationEnvelope: { attack: 0.03, decay: 1.8, sustain: 0.12, release: 1.0 },
          maxPolyphony: 3,
        },
      ]
    case 3: // The Garden — organic, natural, varied
      return [
        {
          type: 'FMSynth' as const,
          harmonicity: 3.5,
          modulationIndex: 2.5,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.005, decay: 1.3, sustain: 0, release: 0.9 },
          modulation: { type: 'sine' as const },
          modulationEnvelope: { attack: 0.005, decay: 0.8, sustain: 0, release: 0.5 },
          maxPolyphony: 7,
        },
        {
          type: 'FMSynth' as const,
          harmonicity: 2.2,
          modulationIndex: 2.8,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.008, decay: 1.5, sustain: 0, release: 1.0 },
          modulation: { type: 'triangle' as const },
          modulationEnvelope: { attack: 0.008, decay: 0.9, sustain: 0, release: 0.6 },
          maxPolyphony: 6,
        },
        {
          type: 'FMSynth' as const,
          harmonicity: 5.0,
          modulationIndex: 2.0,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.004, decay: 1.2, sustain: 0, release: 0.8 },
          modulation: { type: 'sine' as const },
          modulationEnvelope: { attack: 0.004, decay: 0.7, sustain: 0, release: 0.4 },
          maxPolyphony: 8,
        },
        {
          type: 'FMSynth' as const,
          harmonicity: 1.8,
          modulationIndex: 3.0,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.01, decay: 1.4, sustain: 0, release: 0.95 },
          modulation: { type: 'sine' as const },
          modulationEnvelope: { attack: 0.01, decay: 0.85, sustain: 0, release: 0.55 },
          maxPolyphony: 6,
        },
        {
          type: 'FMSynth' as const,
          harmonicity: 2.8,
          modulationIndex: 2.3,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.007, decay: 1.1, sustain: 0, release: 0.85 },
          modulation: { type: 'sine' as const },
          modulationEnvelope: { attack: 0.007, decay: 0.65, sustain: 0, release: 0.45 },
          maxPolyphony: 7,
        },
      ]
    case 4: // The Truth — ethereal, transcendent, bell-like
      return [
        {
          type: 'FMSynth' as const,
          harmonicity: 8.5,
          modulationIndex: 0.8,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.03, decay: 2.5, sustain: 0.05, release: 1.8 },
          modulation: { type: 'sine' as const },
          modulationEnvelope: { attack: 0.03, decay: 1.5, sustain: 0, release: 0.9 },
          maxPolyphony: 4,
        },
        {
          type: 'FMSynth' as const,
          harmonicity: 6.0,
          modulationIndex: 1.0,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.035, decay: 2.7, sustain: 0.08, release: 1.9 },
          modulation: { type: 'sine' as const },
          modulationEnvelope: { attack: 0.035, decay: 1.6, sustain: 0, release: 0.95 },
          maxPolyphony: 4,
        },
        {
          type: 'FMSynth' as const,
          harmonicity: 9.0,
          modulationIndex: 0.9,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.025, decay: 2.4, sustain: 0.06, release: 1.7 },
          modulation: { type: 'sine' as const },
          modulationEnvelope: { attack: 0.025, decay: 1.4, sustain: 0, release: 0.85 },
          maxPolyphony: 4,
        },
        {
          type: 'FMSynth' as const,
          harmonicity: 7.2,
          modulationIndex: 0.85,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.04, decay: 2.6, sustain: 0.07, release: 1.85 },
          modulation: { type: 'sine' as const },
          modulationEnvelope: { attack: 0.04, decay: 1.55, sustain: 0, release: 0.92 },
          maxPolyphony: 3,
        },
        {
          type: 'FMSynth' as const,
          harmonicity: 10.0,
          modulationIndex: 0.75,
          oscillator: { type: 'sine' as const },
          envelope: { attack: 0.045, decay: 2.8, sustain: 0.1, release: 2.0 },
          modulation: { type: 'sine' as const },
          modulationEnvelope: { attack: 0.045, decay: 1.7, sustain: 0, release: 1.0 },
          maxPolyphony: 3,
        },
      ]
    default:
      return getWorldInstrumentConfigs(0)
  }
}

function createInstruments(): Tone.PolySynth[] {
  const configs = getWorldInstrumentConfigs(currentWorldIndex)
  return configs.map((config) => {
    if (config.type === 'FMSynth') {
      const poly = new Tone.PolySynth(Tone.FMSynth, {
        harmonicity: config.harmonicity,
        modulationIndex: config.modulationIndex,
        oscillator: config.oscillator,
        envelope: config.envelope,
        modulation: config.modulation,
        modulationEnvelope: config.modulationEnvelope,
      })
      poly.maxPolyphony = config.maxPolyphony
      return poly
    }
    const poly = new Tone.PolySynth(Tone.FMSynth, {})
    poly.maxPolyphony = 8
    return poly
  })
}

// Swap instruments when the player transitions to a new world.
// Called from the Zustand worldIndex subscription — transport is already
// stopped by this point (nextWorld() sets isPlaying: false).
function switchWorldInstruments(newWorldIndex: number) {
  currentWorldIndex = newWorldIndex
  for (const inst of instruments) {
    inst.disconnect()
    inst.dispose()
  }
  instruments = createInstruments()
  for (const inst of instruments) {
    inst.toDestination()
    inst.connect(effectsBus)
  }
  console.log('[Signal] switchWorldInstruments: world', newWorldIndex, 'instruments rebuilt')
}

let worldSubscribed = false

export async function initAudio() {
  if (initialized) return
  initialized = true // Guard immediately — prevents StrictMode double-invoke race
  console.log('[Signal] initAudio: starting Tone.js...')
  try {
    await Tone.start()
  } catch (err) {
    console.warn('[Signal] initAudio: Tone.start() failed, continuing anyway', err)
  }
  console.log('[Signal] initAudio: AudioContext state =', Tone.getContext().state)

  reverb = new Tone.Reverb({ decay: 4, wet: 0.5 })
  await reverb.ready
  delay = new Tone.PingPongDelay({ delayTime: '8n', feedback: 0.25, wet: 0.2 })
  compressor = new Tone.Compressor({ threshold: -20, ratio: 4 })

  instruments = createInstruments()

  // Dry signal direct to destination + wet signal through effects
  // Using a Channel as a send bus avoids chain issues
  effectsBus = new Tone.Channel({ volume: -6 })
  effectsBus.chain(delay, reverb, compressor, Tone.getDestination())

  for (const inst of instruments) {
    // Dry: direct to output (immediate, clean)
    inst.toDestination()
    // Wet: send to effects bus (reverb + delay)
    inst.connect(effectsBus)
  }

  // Percussion: MembraneSynth kick drum, four-on-the-floor. Pitch shifts per
  // world (lower = heavier bass, used for later worlds).
  kick = new Tone.MembraneSynth({
    pitchDecay: 0.06,
    octaves: 6,
    oscillator: { type: 'sine' },
    envelope: { attack: 0.001, decay: 0.4, sustain: 0.0, release: 1.4 },
  }).toDestination()
  // Slightly compressed and loud enough to carry the pulse on phone speakers.
  const kickGain = new Tone.Gain(0.75).toDestination()
  kick.connect(kickGain)

  // Monster motif — darker, more menacing PolySynth. Sustained so the refrain
  // sits under the kick.
  motifSynth = new Tone.PolySynth(Tone.FMSynth, {
    harmonicity: 1.25,
    modulationIndex: 6.0,
    oscillator: { type: 'sine' },
    envelope: { attack: 0.02, decay: 0.25, sustain: 0.35, release: 0.8 },
    modulation: { type: 'square' },
    modulationEnvelope: { attack: 0.02, decay: 0.2, sustain: 0.1, release: 0.4 },
  })
  motifSynth.volume.value = -10
  motifSynth.toDestination()
  motifSynth.connect(effectsBus)

  // Level-entry flourish — bright, bell-like, 3 notes on biome scale.
  flourishSynth = new Tone.PolySynth(Tone.FMSynth, {
    harmonicity: 3.5,
    modulationIndex: 1.5,
    oscillator: { type: 'sine' },
    envelope: { attack: 0.001, decay: 0.6, sustain: 0.0, release: 0.9 },
    modulation: { type: 'sine' },
    modulationEnvelope: { attack: 0.001, decay: 0.3, sustain: 0.0, release: 0.4 },
  })
  flourishSynth.volume.value = -6
  flourishSynth.toDestination()
  flourishSynth.connect(effectsBus)

  console.log('[Signal] initAudio: complete. Instruments:', instruments.length)

  // Subscribe to world changes — rebuild instruments when worldIndex transitions.
  // Guard against double-subscription on React StrictMode double-invocation.
  // Zustand v5: single-listener subscribe, compare manually.
  if (!worldSubscribed) {
    worldSubscribed = true
    useGameStore.subscribe((state, prevState) => {
      if (state.worldIndex !== prevState.worldIndex) {
        if (!initialized) return
        switchWorldInstruments(state.worldIndex)
      }
    })
  }
}

// Kick tuning per world — lower for heavier biomes.
const KICK_PITCH_BY_WORLD = ['C2', 'D2', 'A1', 'G2', 'E2']

// Monster motif — rootless 4-note descending-ascending ostinato sung from
// the biome's scale. Same rhythm every world, different notes. Plays on
// bar boundaries so it feels like the monster is "breathing" on a grid.
// Indices reference biome.rowToMidi (which is pre-built from the scale).
const MOTIF_ROW_OFFSETS = [0, 3, 2, 4] // four different rows of each scale

export function startTransport(bpm: number) {
  console.log('[Signal] startTransport: BPM =', bpm)
  const transport = Tone.getTransport()
  transport.bpm.value = bpm
  transport.cancel()
  beatCounter = 0

  transport.scheduleRepeat((time) => {
    const state = getGameState()
    if (!state.isPlaying) return

    const step = beatCounter % GRID_COLS

    // --- Four-on-the-floor kick: every quarter note, heartbeat of the game.
    //     Volume ducks in gameover/transition phases so endings stay clean.
    if (kick && state.gamePhase === 'playing') {
      const kickNote = KICK_PITCH_BY_WORLD[state.worldIndex] ?? 'C2'
      kick.triggerAttackRelease(kickNote, '16n', time, 0.85)
    }

    // --- Monster motif: a 4-note ostinato on the biome scale. One note per
    //     quarter-beat, looped across bars. Only while monster is alive.
    if (motifActive && motifSynth && state.gamePhase === 'playing') {
      const idx = MOTIF_ROW_OFFSETS[beatCounter % MOTIF_ROW_OFFSETS.length]
      const midi = state.biome.rowToMidi[idx]
      if (midi !== undefined) {
        // Drop the motif one octave for menace.
        motifSynth.triggerAttackRelease(midiToNoteName(midi - 12), '8n', time, 0.55)
      }
    }

    // --- Sequencer: play any blocks in this column (user's composition).
    const pulsingKeys: string[] = []
    for (const [key, block] of state.blocks) {
      if (block.col === step) {
        const midi = state.biome.rowToMidi[block.row]
        if (midi !== undefined) {
          const noteName = midiToNoteName(midi)
          const inst = instruments[block.instrumentIndex]
          if (inst) {
            const velocity = 0.4 + Math.random() * 0.3
            inst.triggerAttackRelease(noteName, '4n', time, velocity)
          }
        }
        pulsingKeys.push(key)
      }
    }

    // Sync visual state via Tone.Draw (defers to rAF)
    Tone.getDraw().schedule(() => {
      useGameStore.getState().setPlayheadStep(step)
      useGameStore.getState().setPulsingBlocks(pulsingKeys)
    }, time)

    // Fan out to any cage-step subscribers (monster AI, etc.)
    // Runs AFTER kick/motif so subscriber callbacks see a coherent beatCounter.
    for (const fn of beatSubs) {
      try { fn(beatCounter, time) } catch { /* swallow subscriber errors */ }
    }

    beatCounter += 1
  }, '4n')

  transport.start()
  console.log('[Signal] Transport started. State:', transport.state)
}

// Level-entry flourish — three notes from the biome scale, ascending, quick.
// Fires AFTER initAudio so flourishSynth is ready.
export function playLevelFlourish(rowToMidi: number[]) {
  if (!initialized || !flourishSynth) return
  const tune = [rowToMidi[0], rowToMidi[2], rowToMidi[4]]
  const now = Tone.now()
  try {
    for (let i = 0; i < tune.length; i++) {
      const midi = tune[i]
      if (midi === undefined) continue
      flourishSynth.triggerAttackRelease(midiToNoteName(midi + 12), '8n', now + i * 0.11, 0.6)
    }
  } catch { /* swallow — flourish is decorative */ }
}

export function updateBpm(bpm: number) {
  Tone.getTransport().bpm.value = bpm
}

// Smooth BPM change — avoids clicks on rapid scrubs (mobile drag).
// 25ms ramp is imperceptibly brief but eliminates transport discontinuity.
export function rampBpm(bpm: number) {
  try {
    Tone.getTransport().bpm.rampTo(bpm, 0.025)
  } catch {
    Tone.getTransport().bpm.value = bpm
  }
}

// Brief volume swell on the effects bus — fires on big chain cascades.
// +2 dB in, then ramp back over 800 ms. No-op if audio hasn't initialized.
let lastSwellAt = 0
export function chainSwell() {
  if (!initialized || !effectsBus) return
  const now = performance.now()
  if (now - lastSwellAt < 300) return // rate-limit overlapping chains
  lastSwellAt = now
  const ctxNow = Tone.now()
  try {
    effectsBus.volume.cancelScheduledValues(ctxNow)
    effectsBus.volume.setValueAtTime(-6, ctxNow)
    effectsBus.volume.linearRampToValueAtTime(-4, ctxNow + 0.08)
    effectsBus.volume.linearRampToValueAtTime(-6, ctxNow + 0.88)
  } catch {
    // Swell is decorative — silently ignore scheduling errors
  }
}

export function stopTransport() {
  Tone.getTransport().stop()
  Tone.getTransport().cancel()
}

// Trigger a single note on block placement. Quantized to the next
// sixteenth-note so every tap lands on a beat — placement IS music.
// At 120 BPM a 16n is 125 ms, so the delay is imperceptible but
// cohesion is total.
export function triggerPlacementNote(row: number, instrumentIndex: number) {
  if (!initialized) return
  const state = getGameState()
  const midi = state.biome.rowToMidi[row]
  if (midi === undefined) return
  const noteName = midiToNoteName(midi)
  const inst = instruments[instrumentIndex]
  if (!inst) return

  const transport = Tone.getTransport()
  if (transport.state === 'started') {
    try {
      // '@16n' = next sixteenth-note boundary from transport position.
      transport.scheduleOnce((time) => {
        inst.triggerAttackRelease(noteName, '8n', time, 0.68)
      }, '@16n')
      return
    } catch { /* fall through to immediate trigger */ }
  }

  // Fallback for pre-transport placements (title tap, very first press).
  try { inst.triggerAttackRelease(noteName, '8n', Tone.now(), 0.6) }
  catch { /* swallow */ }
}

export function isInitialized() {
  return initialized
}
