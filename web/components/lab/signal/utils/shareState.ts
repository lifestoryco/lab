// Encode / decode a compact share hash for a SIGNAL session.
//
// Fields:
//   v        — 1-byte version
//   mode     — 1 byte (0 = zen, 1 = broadcast)
//   outcome  — 1 byte (0 = partial, 1 = full-arc complete)
//   biomes   — 1 byte bitmask of which biomes were cleared (lowest bit = world 0)
//   blocks   — variable; each block is (biome u8, col u8, row u8)
//
// The whole thing is packed into a Uint8Array then URL-safe base64. Max ~200 blocks
// per share → ~800 bytes → ~1100 chars, well within a URL.

// Post-pivot the app only exposes Zen and Cage. The 'broadcast' tag is
// still accepted during v1 hash decode (legacy share URLs) but is
// translated to 'cage' on read; it is never emitted.
export type SharedMode = 'zen' | 'cage'

export interface SharedSessionState {
  mode: SharedMode
  completed: boolean
  biomeClearBits: number           // bitmask of biomes cleared, lowest bit = world 0
  blocks: Array<{ biome: number; col: number; row: number }>
  totalChains: number
  finalWorld: number               // 0..4 — furthest reached
  // v2 fields (backwards-compatible decode — defaults for v1 hashes)
  cageLevelsCleared?: number       // bitmask of cage levels cleared
}

const VERSION = 2
const VERSION_V1 = 1

function toUrlBase64(u8: Uint8Array): string {
  let bin = ''
  for (let i = 0; i < u8.length; i++) bin += String.fromCharCode(u8[i])
  const b64 = typeof btoa === 'function'
    ? btoa(bin)
    : Buffer.from(bin).toString('base64')
  return b64.replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '')
}

function fromUrlBase64(s: string): Uint8Array {
  const pad = s.length % 4 === 0 ? '' : '='.repeat(4 - (s.length % 4))
  const b64 = s.replaceAll('-', '+').replaceAll('_', '/') + pad
  const bin = typeof atob === 'function'
    ? atob(b64)
    : Buffer.from(b64, 'base64').toString('binary')
  const u8 = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i)
  return u8
}

// --- Mode codec ---------------------------------------------------------
// v1 used 0/1 for zen/broadcast. v2 uses 0=zen, 2=cage.
// Byte value 1 (legacy 'broadcast') is translated to 'cage' on read so
// v1 share URLs produced by the old app keep rendering post-pivot.
function modeToByte(mode: SharedMode): number {
  return mode === 'cage' ? 2 : 0
}
function byteToMode(b: number): SharedMode {
  if (b === 2) return 'cage'
  if (b === 1) return 'cage' // legacy 'broadcast' upgrade
  return 'zen'
}

export function encodeShareState(s: SharedSessionState): string {
  // v2 header: [version, mode, completed, biomeBits, finalWorld, totalChains,
  //             cageLevelsCleared, reserved]
  const header = 8
  const buf = new Uint8Array(header + s.blocks.length * 3)
  buf[0] = VERSION
  buf[1] = modeToByte(s.mode)
  buf[2] = s.completed ? 1 : 0
  buf[3] = s.biomeClearBits & 0x1f
  buf[4] = s.finalWorld & 0xff
  buf[5] = Math.min(255, s.totalChains)
  buf[6] = (s.cageLevelsCleared ?? 0) & 0x1f
  buf[7] = 0 // reserved
  let i = header
  for (const b of s.blocks) {
    buf[i++] = b.biome & 0xff
    buf[i++] = b.col & 0xff
    buf[i++] = b.row & 0xff
  }
  return toUrlBase64(buf)
}

// --- Decode hard caps -----------------------------------------------------
// Legitimate max session: ~200 blocks × 3 bytes + 6-byte header = 606 bytes
// → ~810 base64 chars. MAX_HASH_CHARS and MAX_BLOCKS are generous bounds that
// reject adversarial payloads without clipping any real session.
export const MAX_HASH_CHARS = 2048
export const MAX_BLOCKS = 200
const BIOMES_LEN = 5
const GRID_SIZE  = 16 // Zen grid dimension; also >= Cage grid

export function decodeShareState(hash: string): SharedSessionState | null {
  if (typeof hash !== 'string') return null
  if (hash.length === 0 || hash.length > MAX_HASH_CHARS) return null
  try {
    const buf = fromUrlBase64(hash)
    // Hard cap on buffer length — generous enough for both v1 (6-byte header)
    // and v2 (8-byte header) formats with MAX_BLOCKS blocks.
    if (buf.length < 6 || buf.length > 8 + MAX_BLOCKS * 3) return null
    const version = buf[0]
    if (version !== VERSION && version !== VERSION_V1) return null
    const headerLen = version === VERSION ? 8 : 6

    const mode: SharedMode = version === VERSION
      ? byteToMode(buf[1])
      // v1 encoded mode as 0=zen / 1=broadcast only. Upgrade 'broadcast' → 'cage'
      // so legacy shares feel consistent with the post-pivot audience split.
      : (buf[1] === 1 ? 'cage' : 'zen')

    const completed = buf[2] === 1
    const biomeClearBits = buf[3] & 0x1f
    const finalWorld = buf[4] < BIOMES_LEN ? buf[4] : 0
    const totalChains = buf[5]
    const cageLevelsCleared = version === VERSION ? (buf[6] & 0x1f) : 0

    const blocks: SharedSessionState['blocks'] = []
    for (let i = headerLen; i + 2 < buf.length && blocks.length < MAX_BLOCKS; i += 3) {
      const biome = buf[i], col = buf[i + 1], row = buf[i + 2]
      if (biome >= BIOMES_LEN) continue
      if (col >= GRID_SIZE || row >= GRID_SIZE) continue
      blocks.push({ biome, col, row })
    }
    return {
      mode,
      completed,
      biomeClearBits,
      blocks,
      totalChains,
      finalWorld,
      cageLevelsCleared,
    }
  } catch {
    return null
  }
}
