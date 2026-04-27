import { ImageResponse } from 'next/og'
import { OGCard, OG_SIZE, OG_CONTENT_TYPE } from '@/components/lab/og-card'

export const runtime = 'edge'
export const size = OG_SIZE
export const contentType = OG_CONTENT_TYPE
export const alt = 'ACID — 22 living formulas rendered in ASCII light'

export default async function Image() {
  return new ImageResponse(
    (
      <OGCard
        badge="acid"
        name="ACID"
        tagline="22 living formulas rendered in ASCII light."
        url="handoffpack.com/lab/acid"
        gradient="linear-gradient(145deg, #1E0533 0%, #7C3AED 35%, #DB2777 65%, #F59E0B 100%)"
        accent="#DB2777"
      />
    ),
    { ...size }
  )
}
