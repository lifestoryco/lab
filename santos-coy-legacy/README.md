# Santos Coy Legacy

A museum-quality digital exhibit chronicling sixteen generations of the Santos Coy family — from 16th-century Lepe, Spain, to present-day Houston, Texas.

## Stack
- HTML5 + Tailwind CSS (CDN) + Vanilla JS
- GSAP 3.12 + ScrollTrigger (CDN) for scroll-driven animation
- Google Fonts: Playfair Display (serif) + Inter (sans)

## Local preview
Open `index.html` directly in a browser, or serve the folder:
```bash
python3 -m http.server 8000
# then visit http://localhost:8000/
```

## Deployment
Targets `handoffpack.com/labl/coy`. All asset paths are **relative** (`css/`, `js/`, `images/`) — drop the entire `santos-coy-legacy/` folder contents into that subdirectory and it will work without modification.

## Files
- `index.html` — full single-page exhibit
- `css/style.css` — frames, timeline, paper-noise, reveal initial state
- `js/main.js` — GSAP entrance + scroll animations
- `images/` — empty; add real family photos here (see `IMAGE_INVENTORY.txt`)

## Replacing placeholder imagery
All hero / figure / caption images currently load from Unsplash with descriptive `alt` text describing exactly what real artifact belongs in each slot. See `IMAGE_INVENTORY.txt` for a line-by-line replacement guide.

## Site map
- `index.html` — hero, descendant's note, timeline, figure grid, three bloodlines, sources
- `people/bernardo.html` — Generation I, Lepe → Saltillo
- `people/nicolas.html` — Generation II, 1716 Ramón expedition
- `people/cristobal.html` — Generation III, schoolteacher + Curbelo marriage
- `people/pablo.html` — Generation V, Battle of Medina
- `people/antonio-clemente.html` — Generation VI, San Jacinto + Jack Hays + Lipan
- `people/juan-coy.html` — Generation VII, the outlaw
- `people/modern.html` — Generations VIII–XI, Bastrop → Houston

Each person page includes: hero, sidebar stat-card with linked references, long-form descendant-voice narrative with inline citations, three- or four-image gallery, full Sources & Further Reading list with WorldCat / Handbook of Texas / Wikipedia / archive links, and prev/next pager.

© 2026 The Santos Coy Family Archive.
