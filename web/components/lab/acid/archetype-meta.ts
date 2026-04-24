// Archetype visual metadata — card gradients, vibes, and origin sentences.
// Matches renamed archetypes in archetypes.ts.

export type ArchetypeFamily = 'cosmic' | 'sacred' | 'living' | 'abstract' | 'atmospheric'

export interface ArchetypeMeta {
  name: string
  vibe: string      // 3 words — what it feels like
  origin: string    // 1 sentence — what it IS, not how it works
  gradient: string  // CSS gradient for gallery card
  accent: string    // Dominant hex color for glow / highlights
  family: ArchetypeFamily
}

export const FAMILY_ORDER: ArchetypeFamily[] = ['cosmic', 'sacred', 'living', 'abstract', 'atmospheric']

export const FAMILY_LABEL: Record<ArchetypeFamily, string> = {
  cosmic: 'COSMIC',
  sacred: 'SACRED',
  living: 'LIVING',
  abstract: 'ABSTRACT',
  atmospheric: 'ATMOSPHERIC',
}

export const ARCHETYPE_META: ArchetypeMeta[] = [
  // ── 1. chrysalis ─────────────────────────────────────────────────────────
  {
    name: 'chrysalis',
    vibe: 'machine elves bloom',
    origin: 'Mathematical chrysanthemums that unfold in recursive spirals, each petal containing the geometry of the next.',
    gradient: 'linear-gradient(145deg, #1E0533 0%, #7C3AED 35%, #DB2777 65%, #F59E0B 100%)',
    accent: '#DB2777',
    family: 'abstract',
  },
  // ── 2. zazen ─────────────────────────────────────────────────────────────
  {
    name: 'zazen',
    vibe: 'endless ensō breath',
    origin: 'A single brush traces the ensō in one endless revolution, the tail fading just as the head returns — enlightenment as perpetual motion.',
    gradient: 'linear-gradient(145deg, #000000 0%, #1A1612 40%, #3E3126 70%, #D4B896 100%)',
    accent: '#E8D9B5',
    family: 'sacred',
  },
  // ── 3. spore ─────────────────────────────────────────────────────────────
  {
    name: 'spore',
    vibe: 'bioluminescent forest breath',
    origin: 'A living forest floor where wave interference becomes breath and breathing becomes cold green light.',
    gradient: 'linear-gradient(145deg, #052E16 0%, #065F46 45%, #0D9488 75%, #4ADE80 100%)',
    accent: '#22C55E',
    family: 'atmospheric',
  },
  // ── 4. wavefunction ──────────────────────────────────────────────────────
  {
    name: 'wavefunction',
    vibe: 'quantum superposition shimmer',
    origin: 'Two probability clouds interfere until the act of observation collapses them into a single shimmering instant.',
    gradient: 'linear-gradient(145deg, #0F172A 0%, #1E3A5F 40%, #0EA5E9 75%, #22D3EE 100%)',
    accent: '#0EA5E9',
    family: 'abstract',
  },
  // ── 5. ouroboros ─────────────────────────────────────────────────────────
  {
    name: 'ouroboros',
    vibe: 'serpent swallows its tail',
    origin: 'The serpent curled in a perfect ring, its head eternally swallowing the tapering tip of its own tail — the archetype of self-generation.',
    gradient: 'linear-gradient(145deg, #1A0202 0%, #7F1D1D 30%, #C2410C 60%, #FBBF24 100%)',
    accent: '#EF4444',
    family: 'sacred',
  },
  // ── 6. drift ─────────────────────────────────────────────────────────────
  {
    name: 'drift',
    vibe: 'hazy slow-motion drift',
    origin: 'Time slows. Distortions compound on distortions until the ordinary world becomes warm liquid amber.',
    gradient: 'linear-gradient(145deg, #1A0500 0%, #78350F 35%, #D97706 65%, #FDBA74 100%)',
    accent: '#F97316',
    family: 'atmospheric',
  },
  // ── 7. morphic ───────────────────────────────────────────────────────────
  {
    name: 'morphic',
    vibe: 'flock as one mind',
    origin: 'A thousand birds move as a single organism — three simple rules become something that looks like consciousness.',
    gradient: 'linear-gradient(145deg, #1E1B4B 0%, #3B0764 35%, #86198F 70%, #F472B6 100%)',
    accent: '#C084FC',
    family: 'abstract',
  },
  // ── 8. gondwana ──────────────────────────────────────────────────────────
  {
    name: 'gondwana',
    vibe: 'continents drift and shimmer',
    origin: 'Seven landmasses drift across a deep ocean over eons, their collision edges shimmering gold where tectonic plates meet.',
    gradient: 'linear-gradient(145deg, #08142A 0%, #0D4F6C 40%, #B45309 70%, #FCD34D 100%)',
    accent: '#F0B459',
    family: 'living',
  },
  // ── 9. kemet ─────────────────────────────────────────────────────────────
  {
    name: 'kemet',
    vibe: 'mandala of the sun disk',
    origin: 'Sacred geometry opens like an eye — lapis and gold unfurling through five-fold symmetry that never repeats.',
    gradient: 'linear-gradient(145deg, #0C1E5C 0%, #1E40AF 30%, #B2571F 60%, #FCD34D 100%)',
    accent: '#D7A22A',
    family: 'sacred',
  },
  // ── 10. parallax ─────────────────────────────────────────────────────────
  {
    name: 'parallax',
    vibe: 'dimensional interference shimmer',
    origin: 'Three planes of waves rotate at angles that don\'t exist in ordinary space, colliding at frequencies only the eye can measure.',
    gradient: 'linear-gradient(145deg, #1E0B3B 0%, #581C87 40%, #7E22CE 65%, #EC4899 100%)',
    accent: '#A855F7',
    family: 'abstract',
  },
  // ── 11. hydro ────────────────────────────────────────────────────────────
  {
    name: 'hydro',
    vibe: 'orbital metaball choreography',
    origin: 'Six mercurial worlds dance in elliptical gravity, their edges merging and parting while a rogue comet sweeps through.',
    gradient: 'linear-gradient(145deg, #0A1628 0%, #1E3A8A 40%, #60A5FA 70%, #E0F2FE 100%)',
    accent: '#93C5FD',
    family: 'atmospheric',
  },
  // ── 12. sphinx ───────────────────────────────────────────────────────────
  {
    name: 'sphinx',
    vibe: 'flight over Giza at twilight',
    origin: 'A visitor hovers over the eternal watchers — sphinx and pyramids silhouetted at twilight beneath a patient sky.',
    gradient: 'linear-gradient(145deg, #0F0A2E 0%, #5B21B6 30%, #D97706 65%, #06B6D4 100%)',
    accent: '#22D3EE',
    family: 'sacred',
  },
  // ── 13. surya ────────────────────────────────────────────────────────────
  {
    name: 'surya',
    vibe: 'living sun with twelve rays',
    origin: 'The solar chariot crosses the sky endlessly — corona rotating, prominences breathing, flares erupting on cue.',
    gradient: 'linear-gradient(145deg, #3F0A05 0%, #B91C1C 35%, #F59E0B 70%, #FEF3C7 100%)',
    accent: '#F59E0B',
    family: 'cosmic',
  },
  // ── 14. trappist ─────────────────────────────────────────────────────────
  {
    name: 'trappist',
    vibe: 'seven worlds loop eternally',
    origin: 'A voyage through seven alien worlds that dives into a bioluminescent ocean and returns to exactly where it began.',
    gradient: 'linear-gradient(145deg, #060623 0%, #312E81 30%, #0E7490 60%, #2DD4BF 100%)',
    accent: '#22D3EE',
    family: 'cosmic',
  },
  // ── 15. warmwind ─────────────────────────────────────────────────────────
  {
    name: 'warmwind',
    vibe: 'golden hour through leaves',
    origin: 'Wind sweeps through the canopy at golden hour, and one leaf spirals down through amber light on its own private journey.',
    gradient: 'linear-gradient(145deg, #052E16 0%, #15803D 40%, #CA8A04 70%, #FEF3C7 100%)',
    accent: '#EAB308',
    family: 'living',
  },
  // ── 16. codex ────────────────────────────────────────────────────────────
  {
    name: 'codex',
    vibe: 'illuminated manuscript alive',
    origin: 'Ancient pilgrims walk a living labyrinth, leaving golden trails through shifting walls of warm amber scripture.',
    gradient: 'linear-gradient(145deg, #1C0803 0%, #78350F 40%, #B45309 70%, #FCD34D 100%)',
    accent: '#F59E0B',
    family: 'abstract',
  },
  // ── 17. fungl ────────────────────────────────────────────────────────────
  {
    name: 'fungl',
    vibe: 'mycelial forest floor',
    origin: 'Life spreads through the humus — mycelium seeking nutrients, fruiting bodies blooming and dying, spores carrying new growth outward.',
    gradient: 'linear-gradient(145deg, #0A0705 0%, #14532D 40%, #15803D 65%, #FB7185 100%)',
    accent: '#22C55E',
    family: 'living',
  },
  // ── 18. attractor ────────────────────────────────────────────────────────
  {
    name: 'attractor',
    vibe: 'black hole with accretion disc',
    origin: 'A massive dark heart bends spacetime — photon ring, glowing accretion disc, moons on Keplerian orbits, background stars lensed around the void.',
    gradient: 'linear-gradient(145deg, #050811 0%, #1E3A5F 30%, #C2410C 60%, #FBBF24 100%)',
    accent: '#F59E0B',
    family: 'cosmic',
  },
  // ── 19. luca ─────────────────────────────────────────────────────────────
  {
    name: 'luca',
    vibe: 'primordial replication',
    origin: 'The chemistry that learned to copy itself — Gray-Scott reactions drifting through every regime from spots to labyrinths to mitosis and back.',
    gradient: 'linear-gradient(145deg, #050F1A 0%, #0E7490 35%, #14B8A6 65%, #FCD34D 100%)',
    accent: '#14B8A6',
    family: 'living',
  },
  // ── 20. lightning ────────────────────────────────────────────────────────
  {
    name: 'lightning',
    vibe: 'rainy night, bright flash',
    origin: 'A farmhouse in the rain, one window lit warm amber — and every so often the sky erupts and reveals the whole world for a single heartbeat.',
    gradient: 'linear-gradient(145deg, #050A1C 0%, #1E3A8A 35%, #F59E0B 60%, #E0F2FE 100%)',
    accent: '#60A5FA',
    family: 'atmospheric',
  },
  // ── 21. nexus ────────────────────────────────────────────────────────────
  {
    name: 'nexus',
    vibe: 'hyperdimensional torus cascade',
    origin: 'Three interlocking tori of the Hopf fibration rotate through four dimensions while bright particles orbit along their fibers.',
    gradient: 'linear-gradient(145deg, #0D0221 0%, #5B21B6 25%, #0369A1 50%, #0D9488 75%, #10B981 100%)',
    accent: '#8B5CF6',
    family: 'cosmic',
  },
  // ── 22. luminous ─────────────────────────────────────────────────────────
  {
    name: 'luminous',
    vibe: 'octopus with a beautiful brain',
    origin: 'A translucent octopus drifts through deep water, eight arms undulating independently while chromatophores ripple color across its skin.',
    gradient: 'linear-gradient(145deg, #050814 0%, #1E1B4B 35%, #6D28D9 65%, #F472B6 100%)',
    accent: '#A78BFA',
    family: 'living',
  },
  // ── 23. pod ──────────────────────────────────────────────────────────────
  {
    name: 'pod',
    vibe: 'dolphins at sunset',
    origin: 'A pod of dolphins leaps across an endless sunset, each arc a moment of joy breaking the surface and returning to it.',
    gradient: 'linear-gradient(145deg, #0A1628 0%, #9A3412 30%, #F97316 60%, #FED7AA 100%)',
    accent: '#FB923C',
    family: 'living',
  },
  // ── 24. fractal ──────────────────────────────────────────────────────────
  {
    name: 'fractal',
    vibe: 'infinite self-similar descent',
    origin: 'An endless zoom into the Mandelbrot set — every point contains the whole, and the descent never finds a bottom.',
    gradient: 'linear-gradient(145deg, #0A0218 0%, #4C1D95 30%, #DB2777 60%, #F59E0B 100%)',
    accent: '#EC4899',
    family: 'abstract',
  },
  // ── 25. matrix ───────────────────────────────────────────────────────────
  {
    name: 'matrix',
    vibe: 'digital rain awakens',
    origin: 'Vertical columns of code cascade eternally — and every so often the pattern coalesces into a glimpse of the face beneath.',
    gradient: 'linear-gradient(145deg, #030808 0%, #052E16 30%, #15803D 65%, #4ADE80 100%)',
    accent: '#22C55E',
    family: 'abstract',
  },
  // ── 26. multiverse ───────────────────────────────────────────────────────
  {
    name: 'multiverse',
    vibe: 'parallel timelines branch',
    origin: 'Five versions of the same universe run in parallel, diverging from tiny perturbations — every choice is kept, somewhere.',
    gradient: 'linear-gradient(145deg, #0C0A3E 0%, #4C1D95 30%, #0E7490 55%, #F472B6 100%)',
    accent: '#A78BFA',
    family: 'cosmic',
  },
  // ── 27. holo ─────────────────────────────────────────────────────────────
  {
    name: 'holo',
    vibe: 'holographic glitch cascade',
    origin: 'A tesseract rotates through fourth-dimensional space, pixels shimmering and occasionally misaligning as the projection stutters.',
    gradient: 'linear-gradient(145deg, #050814 0%, #1E3A8A 30%, #A855F7 60%, #22D3EE 100%)',
    accent: '#22D3EE',
    family: 'abstract',
  },
  // ── 28. collapse ─────────────────────────────────────────────────────────
  {
    name: 'collapse',
    vibe: 'probability collapses into choice',
    origin: 'A probability cloud expands and collapses on a slow breath — every observation is the universe choosing one from many.',
    gradient: 'linear-gradient(145deg, #0A0F2E 0%, #4338CA 30%, #C026D3 60%, #FCD34D 100%)',
    accent: '#8B5CF6',
    family: 'abstract',
  },
  // ── 29. dragon ───────────────────────────────────────────────────────────
  {
    name: 'dragon',
    vibe: 'celestial serpent in clouds',
    origin: 'An Eastern dragon weaves through cloud banks, scales of jade and gold catching light that has traveled from distant stars.',
    gradient: 'linear-gradient(145deg, #0A1408 0%, #14532D 35%, #CA8A04 70%, #FEF3C7 100%)',
    accent: '#F59E0B',
    family: 'sacred',
  },
  // ── 30. dmt ──────────────────────────────────────────────────────────────
  {
    name: 'dmt',
    vibe: 'hyperspace entity realm',
    origin: 'A kaleidoscopic tunnel at impossible velocity — sacred geometry, pulsing light, the distinct feeling of being observed.',
    gradient: 'linear-gradient(145deg, #1E0533 0%, #7C3AED 25%, #F59E0B 55%, #22D3EE 100%)',
    accent: '#C084FC',
    family: 'sacred',
  },
  // ── 31. bardo ────────────────────────────────────────────────────────────
  {
    name: 'bardo',
    vibe: 'passage through the clear light',
    origin: 'The tunnel widens. Memory fragments drift on the periphery. Between lives, only the warm golden light remains.',
    gradient: 'linear-gradient(145deg, #0A0A0A 0%, #44403C 35%, #D97706 65%, #FEF3C7 100%)',
    accent: '#FBBF24',
    family: 'sacred',
  },
  // ── 32. now ──────────────────────────────────────────────────────────────
  {
    name: 'now',
    vibe: 'the present moment',
    origin: 'A single point of light that never moves. The whole universe, breathing gently, right here.',
    gradient: 'linear-gradient(145deg, #000000 0%, #0A0A0A 45%, #2A2418 75%, #F5EDD9 100%)',
    accent: '#F5EDD9',
    family: 'sacred',
  },
  // ── 33. deep ─────────────────────────────────────────────────────────────
  {
    name: 'deep',
    vibe: 'geological eons compressed',
    origin: 'The camera drifts down through strata of deep time — sediment, fossil hints, rare stars overhead when the rock gives way to sky.',
    gradient: 'linear-gradient(145deg, #0A0A0A 0%, #450A0A 30%, #92400E 60%, #F59E0B 100%)',
    accent: '#D97706',
    family: 'cosmic',
  },
]

export const ARCHETYPE_META_MAP: Record<string, ArchetypeMeta> = ARCHETYPE_META.reduce(
  (acc, m) => ({ ...acc, [m.name]: m }),
  {} as Record<string, ArchetypeMeta>
)
