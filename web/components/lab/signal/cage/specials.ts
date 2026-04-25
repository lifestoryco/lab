// Per-world special items. One charge per cage level (worlds 2-5).
// World 1 has no special — it's the tutorial biome.

export type SpecialKind = 'stun' | 'reverse' | 'banish' | 'reveal'

export interface SpecialMeta {
  kind: SpecialKind
  name: string                // shown on the button + tooltip
  glyph: string               // single-glyph icon (Cormorant-rendered)
  hint: string                // one-line italic instruction
  accent: string              // accent colour for button glow + activation flash
}

const SPECIALS: Record<number, SpecialMeta> = {
  1: { kind: 'stun',    name: 'Sword',   glyph: '†', hint: 'Hold the monster still.',         accent: '#ff5f6d' },
  2: { kind: 'reverse', name: 'Mirror',  glyph: '◊', hint: 'Reverse the monster.',            accent: '#7fdfff' },
  3: { kind: 'banish',  name: 'Anchor',  glyph: '∗', hint: 'Banish the echo.',                accent: '#a8e063' },
  4: { kind: 'reveal',  name: 'Lantern', glyph: '✶', hint: 'Reveal the answer for a moment.', accent: '#ffcb6b' },
}

export const STUN_DURATION_BEATS = 6
export const REVEAL_DURATION_MS = 3000

export function specialForWorld(worldIndex: number): SpecialMeta | null {
  return SPECIALS[worldIndex] ?? null
}
