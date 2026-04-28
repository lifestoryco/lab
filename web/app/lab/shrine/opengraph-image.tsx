import { ImageResponse } from 'next/og'
import { OGCard, OG_SIZE, OG_CONTENT_TYPE } from '@/components/lab/og-card'

export const runtime = 'edge'
export const size = OG_SIZE
export const contentType = OG_CONTENT_TYPE
export const alt = 'THE SHRINE — An archive of the awakened.'

export default async function Image() {
  return new ImageResponse(
    (
      <OGCard
        badge="shrine"
        name="THE SHRINE"
        tagline="An archive of the awakened. One ensō, twenty masters, 1,800 years."
        url="handoffpack.com/lab/shrine"
        gradient="linear-gradient(145deg, #0A0705 0%, #2A1810 30%, #8A0016 65%, #B8001F 100%)"
        accent="#B8001F"
      />
    ),
    { ...size }
  )
}
