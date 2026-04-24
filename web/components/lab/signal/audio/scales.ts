// Pentatonic scale definitions — the safety net that makes it
// impossible to produce ugly sounds. Every note harmonizes.

// MIDI note names
const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

export function midiToNoteName(midi: number): string {
  const name = NOTE_NAMES[midi % 12]
  const octave = Math.floor(midi / 12) - 1
  return `${name}${octave}`
}

// Scale intervals (semitones from root)
export const SCALES = {
  // World 1: High Desert — D Dorian Pentatonic (warm, open)
  pentatonicDorian: [0, 2, 3, 7, 9],
  // World 2: Egyptian UFO — Bb Phrygian Dominant Pentatonic (exotic, golden)
  pentatonicPhrygian: [0, 1, 4, 7, 8],
  // World 3: Water — E Lydian Pentatonic (crystalline, spacious)
  pentatonicLydian: [0, 2, 4, 7, 9],
  // World 4: Forest — A Minor Pentatonic (natural, organic)
  pentatonicMinor: [0, 3, 5, 7, 10],
  // World 5: Zendo — C Miyako-bushi inspired (sparse, meditative)
  pentatonicMiyako: [0, 1, 5, 7, 8],
} as const

export type ScaleName = keyof typeof SCALES

// Build a row-to-MIDI mapping for the grid.
// 16 rows, spanning ~3 octaves of pentatonic notes.
// FLIPPED: row 0 (bottom-left in isometric) = lowest note,
//          row 15 (top-right in isometric) = highest note.
// The flip happens here so the audio layer is correct —
// visually, higher rows are closer to the camera (bottom of screen in iso),
// so we reverse: row 0 maps to the HIGHEST note, row 15 to the LOWEST.
// This makes top-right of the diamond = high pitch (like a piano).
export function buildRowToMidi(rootMidi: number, scale: readonly number[]): number[] {
  const notes: number[] = []
  for (let i = 0; i < 16; i++) {
    const octave = Math.floor(i / scale.length)
    const degree = i % scale.length
    notes.push(rootMidi + scale[degree] + octave * 12)
  }
  // Reverse so row 0 (top-right visually) = highest, row 15 (bottom-left) = lowest
  return notes.reverse()
}

// Root MIDI notes per world
export const WORLD_ROOTS = {
  desert: 50,    // D3
  egyptian: 46,  // Bb2
  water: 52,     // E3
  forest: 45,    // A2
  zendo: 48,     // C3
} as const
