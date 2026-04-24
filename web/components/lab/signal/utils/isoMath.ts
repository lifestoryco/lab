// Isometric coordinate system for Signal.
// Grid cells are (col, row) where col = X (beats/time) and row = Y (pitch).
// World coordinates are the Three.js positions for rendering.

// Standard isometric: camera at 45deg Y rotation, ~35.264deg X rotation.
// With OrthographicCamera, we rotate the GRID instead of the camera.

export const GRID_COLS = 16 // beats (X axis)
export const GRID_ROWS = 16 // pitch rows (Y axis) — true square
export const TILE_SIZE = 1.0
export const TILE_GAP = 0.08

const EFFECTIVE = TILE_SIZE + TILE_GAP

// Convert grid (col, row) to 3D world position on the ground plane.
// The isometric look comes from the camera angle, not from skewing coords.
// We lay tiles flat on the XZ plane, camera looks down at an angle.
export function gridToWorld(col: number, row: number): [number, number, number] {
  // Center the grid around origin
  const offsetX = (GRID_COLS - 1) * EFFECTIVE * 0.5
  const offsetZ = (GRID_ROWS - 1) * EFFECTIVE * 0.5
  const x = col * EFFECTIVE - offsetX
  const z = row * EFFECTIVE - offsetZ
  return [x, 0, z]
}

// Convert world position back to grid (col, row). Returns null if out of bounds.
export function worldToGrid(x: number, z: number): { col: number; row: number } | null {
  const offsetX = (GRID_COLS - 1) * EFFECTIVE * 0.5
  const offsetZ = (GRID_ROWS - 1) * EFFECTIVE * 0.5
  const col = Math.round((x + offsetX) / EFFECTIVE)
  const row = Math.round((z + offsetZ) / EFFECTIVE)
  if (col < 0 || col >= GRID_COLS || row < 0 || row >= GRID_ROWS) return null
  return { col, row }
}

// Block key for Map lookups
export function blockKey(col: number, row: number): string {
  return `${col},${row}`
}
