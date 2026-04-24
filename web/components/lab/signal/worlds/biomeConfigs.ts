// Master configuration for each of the 5 worlds.
// Each biome defines its musical tuning, color palette, and character.

import { SCALES, WORLD_ROOTS, buildRowToMidi, type ScaleName } from '../audio/scales'

export interface BiomePalette {
  primary: string
  bright: string
  deep: string
  hasAccent: boolean
}

export type BroadcastRule = 'shape' | 'rhythm' | 'rotation' | 'recursion' | 'silence'

export interface BiomeConfig {
  name: string
  subtitle: string
  slug: string
  palette: BiomePalette
  rootMidi: number
  scaleName: ScaleName
  rowToMidi: number[]
  bpm: number
  minBlocksForPortal: number
  maxSaturationBlocks: number
  // Narrative text shown during play
  playText: string
  portalWhisper: string
  // Broadcast Mode (W2) — machine-plays-pattern-you-echo mechanic
  broadcastRule: BroadcastRule
  broadcastPatternSize: number
  broadcastIntervalMs: number
  broadcastWindowMs: number
  broadcastHint: string  // temporary copy; SIG-3.1 finalizes
}

interface BroadcastOverride {
  rule?: BroadcastRule
  patternSize?: number
  intervalMs?: number
  windowMs?: number
  hint?: string
}

function createBiome(
  name: string,
  subtitle: string,
  slug: string,
  palette: BiomePalette,
  rootMidi: number,
  scaleName: ScaleName,
  bpm: number,
  playText: string,
  portalWhisper: string,
  broadcast?: BroadcastOverride,
): BiomeConfig {
  return {
    name,
    subtitle,
    slug,
    palette,
    rootMidi,
    scaleName,
    rowToMidi: buildRowToMidi(rootMidi, SCALES[scaleName]),
    bpm,
    minBlocksForPortal: 8,
    maxSaturationBlocks: 20,
    playText,
    portalWhisper,
    broadcastRule: broadcast?.rule ?? 'shape',
    broadcastPatternSize: broadcast?.patternSize ?? 3,
    broadcastIntervalMs: broadcast?.intervalMs ?? 30_000,
    broadcastWindowMs: broadcast?.windowMs ?? 20_000,
    broadcastHint: broadcast?.hint ?? 'Place where it sang.',
  }
}

export const BIOMES: BiomeConfig[] = [
  createBiome(
    'The Signal',
    'Everything starts with a tap.',
    'desert',
    { primary: '#888888', bright: '#cccccc', deep: '#444444', hasAccent: false },
    WORLD_ROOTS.desert,
    'pentatonicDorian',
    72,
    'Place two adjacent notes to begin.',
    'Step through the new chain.',
    { rule: 'shape', patternSize: 3, hint: 'Put sound exactly where you heard it.' },
  ),
  createBiome(
    'The Temple',
    'Order matters here.',
    'egyptian',
    { primary: '#DCAE1D', bright: '#F7C331', deep: '#d8ab4e', hasAccent: true },
    WORLD_ROOTS.egyptian,
    'pentatonicPhrygian',
    80,
    'Count the rhythm of the placements.',
    'A door opens in sequence.',
    { rule: 'rhythm', patternSize: 4, hint: 'Follow the exact sequence.' },
  ),
  createBiome(
    'The Deep',
    'Listen from the other side.',
    'water',
    { primary: '#1561ad', bright: '#7acfd6', deep: '#2d545e', hasAccent: true },
    WORLD_ROOTS.water,
    'pentatonicLydian',
    54,
    'Rotate the shape before placing it.',
    'Step through the shifted shape.',
    { rule: 'rotation', patternSize: 4, hint: 'Place the shape exactly as it turns.' },
  ),
  createBiome(
    'The Garden',
    'Everything repeats, offset.',
    'forest',
    { primary: '#3d7c47', bright: '#7ebc59', deep: '#478559', hasAccent: true },
    WORLD_ROOTS.forest,
    'pentatonicMinor',
    60,
    'The same shape plays twice.',
    'Step into the repeating pattern.',
    { rule: 'recursion', patternSize: 3, hint: 'Match both halves of the echo.' },
  ),
  createBiome(
    'The Truth',
    'There is one correct sound.',
    'zendo',
    { primary: '#b11a21', bright: '#e0474c', deep: '#9e363a', hasAccent: true },
    WORLD_ROOTS.zendo,
    'pentatonicMiyako',
    48,
    'Listen for where the quiet rests.',
    'Nowhere left to go except through.',
    { rule: 'silence', patternSize: 1, windowMs: 15_000, hint: 'Place exactly one block.' },
  ),
]
