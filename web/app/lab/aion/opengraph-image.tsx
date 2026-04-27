import { ImageResponse } from 'next/og'
import { OGCard, OG_SIZE, OG_CONTENT_TYPE } from '@/components/lab/og-card'

export const runtime = 'edge'
export const size = OG_SIZE
export const contentType = OG_CONTENT_TYPE
export const alt = 'AION — Every moment you\'ve ever been is still here, superimposed.'

export default async function Image() {
  return new ImageResponse(
    (
      <OGCard
        badge="aion"
        name="AION"
        tagline="Every moment you've ever been is still here, superimposed."
        url="handoffpack.com/lab/aion"
        gradient="linear-gradient(145deg, #0F172A 0%, #5B21B6 30%, #3B82F6 60%, #F59E0B 100%)"
        accent="#7C3AED"
      />
    ),
    { ...size }
  )
}
