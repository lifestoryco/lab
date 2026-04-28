import { ImageResponse } from 'next/og'
import { OGCard, OG_SIZE, OG_CONTENT_TYPE } from '@/components/lab/og-card'

export const runtime = 'edge'
export const size = OG_SIZE
export const contentType = OG_CONTENT_TYPE
export const alt = 'HOLO — Pokémon TCG price intelligence.'

export default async function Image() {
  return new ImageResponse(
    (
      <OGCard
        badge="holo"
        name="HOLO"
        tagline="Pokémon TCG price intelligence — live comps, signals, flip profit."
        url="handoffpack.com/lab/holo"
        gradient="linear-gradient(145deg, #0a0a0a 0%, #1a1000 30%, #3d2800 60%, #f0c040 100%)"
        accent="#f0c040"
      />
    ),
    { ...size }
  )
}
