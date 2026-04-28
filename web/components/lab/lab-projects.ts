// Lab project registry — metadata for the /lab gallery index.
// Add new projects here as they're built.

export interface LabProject {
  slug: string
  name: string
  tagline: string
  gradient: string
  accentColor: string
  techTags: string[]
  dateAdded: string
  ogImage?: string
  externalUrl?: string  // if set, card links externally instead of /lab/slug
}

export const LAB_PROJECTS: LabProject[] = [
  {
    slug: 'acid',
    name: 'ACID',
    tagline: '22 living formulas rendered in ASCII light.',
    gradient: 'linear-gradient(145deg, #1E0533 0%, #7C3AED 35%, #DB2777 65%, #F59E0B 100%)',
    accentColor: '#DB2777',
    techTags: ['ASCII', 'Canvas 2D', 'Generative Math'],
    dateAdded: '2026-03-15',
  },
  {
    slug: 'aion',
    name: 'AION',
    tagline: 'Every moment you\'ve ever been is still here, superimposed.',
    gradient: 'linear-gradient(145deg, #0F172A 0%, #5B21B6 30%, #3B82F6 60%, #F59E0B 100%)',
    accentColor: '#7C3AED',
    techTags: ['Webcam', 'Radial Time', 'Op Art'],
    dateAdded: '2026-03-28',
  },
  {
    slug: 'signal',
    name: 'SIGNAL',
    tagline: 'Build worlds that play themselves.',
    gradient: 'linear-gradient(145deg, #000000 0%, #333333 35%, #666666 65%, #ffffff 100%)',
    accentColor: '#888888',
    techTags: ['Three.js', 'Tone.js', 'Isometric', 'Generative Music'],
    dateAdded: '2026-04-02',
  },
  {
    slug: 'book-of-claude',
    name: 'BOOK OF CLAUDE',
    tagline: 'The pragmatic playbook for building with Claude Code. Open source.',
    gradient: 'linear-gradient(145deg, #0a0a0a 0%, #1a1a2e 30%, #16213e 60%, #0f3460 100%)',
    accentColor: '#4a9eff',
    techTags: ['Open Source', 'Claude Code', 'Playbook', 'GitHub'],
    dateAdded: '2026-04-04',
    externalUrl: 'https://github.com/lifestoryco/book-of-claude',
  },
  {
    slug: 'holo',
    name: 'HOLO',
    tagline: 'Pokémon TCG price intelligence — live comps, signals, flip profit.',
    gradient: 'linear-gradient(145deg, #0a0a0a 0%, #1a1000 30%, #3d2800 60%, #f0c040 100%)',
    accentColor: '#f0c040',
    techTags: ['Python', 'Next.js', 'PriceCharting', 'TCGPlayer'],
    dateAdded: '2026-04-15',
  },
  {
    slug: 'coin',
    name: 'COIN',
    tagline: 'Career ops intelligence — pipeline, scoring, offer comparison.',
    gradient: 'linear-gradient(145deg, #050510 0%, #0d1117 30%, #1a0a2e 60%, #7c3aed 100%)',
    accentColor: '#7c3aed',
    techTags: ['Python', 'Next.js', 'SQLite', 'Career Ops'],
    dateAdded: '2026-04-28',
  },
  {
    slug: 'shrine',
    name: 'THE SHRINE',
    tagline: 'An archive of the awakened. One ensō, twenty masters, 1,800 years.',
    gradient: 'linear-gradient(145deg, #0A0705 0%, #2A1810 30%, #8A0016 65%, #B8001F 100%)',
    accentColor: '#B8001F',
    techTags: ['Canvas 2D', 'Sumi-e', 'Framer Motion', 'RAG (planned)'],
    dateAdded: '2026-04-23',
  },
  {
    slug: 'coy',
    name: 'SANTOS COY',
    tagline: 'Blood, frontier, and the making of Texas. Sixteen generations from Lepe to Houston.',
    gradient: 'linear-gradient(145deg, #1c1a17 0%, #2a2723 30%, #704214 65%, #c9a961 100%)',
    accentColor: '#c9a961',
    techTags: ['Genealogy', 'Static HTML', 'GSAP', 'Tailwind'],
    dateAdded: '2026-04-27',
  },
]

export const LAB_PROJECTS_MAP: Record<string, LabProject> = LAB_PROJECTS.reduce(
  (acc, p) => ({ ...acc, [p.slug]: p }),
  {} as Record<string, LabProject>
)
