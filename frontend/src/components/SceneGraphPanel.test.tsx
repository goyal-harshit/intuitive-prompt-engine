import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SceneGraphPanel } from './SceneGraphPanel'
import type { SceneGraph } from '../types/domain'

const attr = (value: string, confidence = 0.8) => ({
  value,
  confidence,
  updated_at: 0,
  provenance: [],
})

const scene: SceneGraph = {
  objects: {
    obj_1: {
      id: 'obj_1',
      category: 'airborne',
      salience: 0.72,
      attributes: { motion: attr('soaring upward') },
    },
  },
  globals: { camera_distance: attr('wide shot'), time_of_day: attr('night') },
  history: [],
  meta: { created_at: 0, updated_at: 0, revision: 4, completeness: 0.62 },
}

describe('SceneGraphPanel', () => {
  it('shows a hint while the scene is empty', () => {
    render(<SceneGraphPanel scene={null} completeness={0} />)
    expect(screen.getByText(/gesture to begin/i)).toBeInTheDocument()
    expect(screen.getByText('0%')).toBeInTheDocument()
  })

  it('renders objects with attributes and humanized global keys', () => {
    render(<SceneGraphPanel scene={scene} completeness={0.62} />)
    expect(screen.getByText('airborne')).toBeInTheDocument()
    expect(screen.getByText(/salience 0.72/)).toBeInTheDocument()
    expect(screen.getByText('soaring upward')).toBeInTheDocument()
    expect(screen.getByText('camera distance')).toBeInTheDocument() // underscore → space
    expect(screen.getByText('night')).toBeInTheDocument()
    expect(screen.getByText('62%')).toBeInTheDocument()
  })
})
