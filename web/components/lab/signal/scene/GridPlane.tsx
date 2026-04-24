'use client'

import { useRef, useMemo, useCallback } from 'react'
import { useFrame, ThreeEvent } from '@react-three/fiber'
import * as THREE from 'three'
import { GRID_COLS, GRID_ROWS, TILE_SIZE, TILE_GAP, gridToWorld } from '../utils/isoMath'
import { useGameStore, getGameState } from '../engine/useGameStore'

const EFFECTIVE = TILE_SIZE + TILE_GAP
const TOTAL_TILES = GRID_COLS * GRID_ROWS

// Map from instance index to grid (col, row)
const INSTANCE_TO_GRID: { col: number; row: number }[] = []
for (let col = 0; col < GRID_COLS; col++) {
  for (let row = 0; row < GRID_ROWS; row++) {
    INSTANCE_TO_GRID.push({ col, row })
  }
}

interface GridPlaneProps {
  onCellClick: (col: number, row: number) => void
  onCellLongPress?: (col: number, row: number) => void
}

export default function GridPlane({ onCellClick, onCellLongPress }: GridPlaneProps) {
  const meshRef = useRef<THREE.InstancedMesh>(null!)
  const pressTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pressCell = useRef<{ col: number; row: number } | null>(null)

  const dummy = useMemo(() => new THREE.Object3D(), [])
  const colorObj = useMemo(() => new THREE.Color(), [])
  const accentObj = useMemo(() => new THREE.Color(), [])

  // Single useFrame handles both init and per-frame color updates
  const initialized = useRef(false)

  useFrame(() => {
    const mesh = meshRef.current
    if (!mesh) return

    const { playheadStep, saturation, biome } = getGameState()

    // Initialize positions once (first frame after mount)
    if (!initialized.current) {
      initialized.current = true
      let i = 0
      for (let col = 0; col < GRID_COLS; col++) {
        for (let row = 0; row < GRID_ROWS; row++) {
          const [x, , z] = gridToWorld(col, row)
          dummy.position.set(x, 0, z)
          dummy.scale.set(1, 1, 1)
          dummy.updateMatrix()
          mesh.setMatrixAt(i, dummy.matrix)
          i++
        }
      }
      mesh.instanceMatrix.needsUpdate = true
    }

    // Update colors every frame
    for (let i = 0; i < TOTAL_TILES; i++) {
      const { col, row } = INSTANCE_TO_GRID[i]

      // Checkerboard B&W
      const isLight = (col + row) % 2 === 0
      const isPlayhead = col === playheadStep

      if (isPlayhead) {
        colorObj.set(isLight ? '#ffffff' : '#e0e0e0')
      } else {
        colorObj.set(isLight ? '#888888' : '#666666')
      }

      // Accent color tint from saturation
      if (biome.palette.hasAccent && saturation > 0) {
        accentObj.set(isPlayhead ? biome.palette.primary : biome.palette.deep)
        colorObj.lerp(accentObj, saturation * (isPlayhead ? 0.4 : 0.15))
      }

      mesh.setColorAt(i, colorObj)
    }

    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true
  })

  const handlePointerDown = useCallback((e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation()
    if (e.instanceId === undefined) return
    const cell = INSTANCE_TO_GRID[e.instanceId]
    if (!cell) return
    pressCell.current = cell

    if (onCellLongPress) {
      pressTimer.current = setTimeout(() => {
        if (pressCell.current) {
          onCellLongPress(pressCell.current.col, pressCell.current.row)
          pressCell.current = null
        }
      }, 500)
    }
  }, [onCellLongPress])

  const handlePointerUp = useCallback((e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation()
    if (pressTimer.current) {
      clearTimeout(pressTimer.current)
      pressTimer.current = null
    }
    if (pressCell.current) {
      onCellClick(pressCell.current.col, pressCell.current.row)
      pressCell.current = null
    }
  }, [onCellClick])

  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, TOTAL_TILES]}
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerUp}
    >
      <boxGeometry args={[TILE_SIZE * 0.92, 0.12, TILE_SIZE * 0.92]} />
      <meshBasicMaterial color="#ffffff" toneMapped={false} />
    </instancedMesh>
  )
}
