'use client'

import { useEffect, useRef } from 'react'
import { useThree } from '@react-three/fiber'
import * as THREE from 'three'

interface GestureControlsProps {
  onTwoFingerActive?: (active: boolean) => void
}

const MIN_ZOOM = 10
const MAX_ZOOM = 80

export default function GestureControls({ onTwoFingerActive }: GestureControlsProps) {
  const { camera, gl } = useThree()

  // Track active pointer count for two-finger suppression
  const activePointers = useRef<Map<number, { x: number; y: number }>>(new Map())
  const lastPinchDist = useRef<number | null>(null)
  const lastPanMid = useRef<{ x: number; y: number } | null>(null)

  useEffect(() => {
    const el = gl.domElement

    const getDistance = (a: { x: number; y: number }, b: { x: number; y: number }) =>
      Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)

    const getMidpoint = (a: { x: number; y: number }, b: { x: number; y: number }) => ({
      x: (a.x + b.x) / 2,
      y: (a.y + b.y) / 2,
    })

    const onPointerDown = (e: PointerEvent) => {
      activePointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY })
      onTwoFingerActive?.(activePointers.current.size >= 2)
    }

    const onPointerMove = (e: PointerEvent) => {
      if (!activePointers.current.has(e.pointerId)) return
      activePointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY })

      const pointers = [...activePointers.current.values()]
      if (pointers.length < 2) {
        lastPinchDist.current = null
        lastPanMid.current = null
        return
      }

      const [a, b] = pointers
      const dist = getDistance(a, b)
      const mid = getMidpoint(a, b)

      // Pinch to zoom
      if (lastPinchDist.current !== null) {
        const delta = lastPinchDist.current - dist
        const ortho = camera as THREE.OrthographicCamera
        ortho.zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, ortho.zoom - delta * 0.15))
        ortho.updateProjectionMatrix()
      }
      lastPinchDist.current = dist

      // Two-finger pan
      if (lastPanMid.current !== null) {
        const dx = mid.x - lastPanMid.current.x
        const dy = mid.y - lastPanMid.current.y

        // Pan in world space: project screen delta onto camera right/up vectors
        const ortho = camera as THREE.OrthographicCamera
        const viewW = ortho.right - ortho.left
        const viewH = ortho.top - ortho.bottom
        const screenW = el.clientWidth
        const screenH = el.clientHeight

        const worldDx = (dx / screenW) * viewW / ortho.zoom
        const worldDy = (dy / screenH) * viewH / ortho.zoom

        // Camera right and up in world space
        const right = new THREE.Vector3()
        const up = new THREE.Vector3()
        camera.matrixWorld.extractBasis(right, up, new THREE.Vector3())

        camera.position.addScaledVector(right, -worldDx)
        camera.position.addScaledVector(up, worldDy)
      }
      lastPanMid.current = mid
    }

    const onPointerUp = (e: PointerEvent) => {
      activePointers.current.delete(e.pointerId)
      if (activePointers.current.size < 2) {
        lastPinchDist.current = null
        lastPanMid.current = null
      }
      onTwoFingerActive?.(activePointers.current.size >= 2)
    }

    const onPointerCancel = (e: PointerEvent) => {
      activePointers.current.delete(e.pointerId)
      if (activePointers.current.size < 2) {
        lastPinchDist.current = null
        lastPanMid.current = null
      }
      onTwoFingerActive?.(activePointers.current.size >= 2)
    }

    // Prevent native browser scroll/zoom on the canvas
    const onWheel = (e: WheelEvent) => {
      e.preventDefault()
      const ortho = camera as THREE.OrthographicCamera
      ortho.zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, ortho.zoom - e.deltaY * 0.05))
      ortho.updateProjectionMatrix()
    }

    el.addEventListener('pointerdown', onPointerDown)
    el.addEventListener('pointermove', onPointerMove)
    el.addEventListener('pointerup', onPointerUp)
    el.addEventListener('pointercancel', onPointerCancel)
    el.addEventListener('wheel', onWheel, { passive: false })

    return () => {
      el.removeEventListener('pointerdown', onPointerDown)
      el.removeEventListener('pointermove', onPointerMove)
      el.removeEventListener('pointerup', onPointerUp)
      el.removeEventListener('pointercancel', onPointerCancel)
      el.removeEventListener('wheel', onWheel)
    }
  }, [camera, gl, onTwoFingerActive])

  return null
}
