import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { GestureDebugPanel } from './GestureDebugPanel'
import type { GestureDebugPayload, GestureFeatureVector } from '../types/domain'

const features: GestureFeatureVector = {
  ts: 0,
  hands_visible: 1,
  openness: 0,
  pinch: 0,
  separation: 0,
  expansion_rate: 0,
  verticality: 0,
  vertical_velocity: 0,
  pointing_up: 0,
  pointing_forward: 0,
  circularity: 0,
  circle_overhead: 0,
  horizontal_travel: 0,
  depth_velocity: 0,
  tempo: 0,
  smoothness: 0,
  symmetry: 0,
  posture_lean: 0,
  head_yaw: 0,
  head_pitch: 0,
  valence: 0.4,
  arousal: 0.6,
  stillness: 0,
}

const debug: GestureDebugPayload = {
  drawing: true,
  matches: [
    { primitive: 'expand', match_score: 0.72, would_mean: 'scene → grows', base_weight: 0.8 },
  ],
}

describe('GestureDebugPanel', () => {
  it('shows a placeholder when there are no matches yet', () => {
    render(<GestureDebugPanel debug={null} features={null} ambient={{}} />)
    expect(screen.getByText(/move to see live primitive matches/i)).toBeInTheDocument()
    expect(screen.getByText(/start a session to compare/i)).toBeInTheDocument()
  })

  it('renders live matches with score and would-mean text, and the drawing badge', () => {
    render(<GestureDebugPanel debug={debug} features={features} ambient={{}} />)
    expect(screen.getByText('expand')).toBeInTheDocument()
    expect(screen.getByText('72%')).toBeInTheDocument()
    expect(screen.getByText(/scene → grows/)).toBeInTheDocument()
    expect(screen.getByText('drawing')).toBeInTheDocument()
  })

  it('shows raw vs. smoothed affect values once features are available', () => {
    render(
      <GestureDebugPanel
        debug={null}
        features={features}
        ambient={{ valence: 0.1, arousal: 0.2 }}
      />,
    )
    expect(screen.getByText(/raw 0\.40/)).toBeInTheDocument()
    expect(screen.getByText(/smoothed 0\.10/)).toBeInTheDocument()
  })
})
