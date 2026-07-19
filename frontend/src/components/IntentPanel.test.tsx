import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { IntentPanel } from './IntentPanel'
import type { IntentFrame } from '../types/domain'

const frame: IntentFrame = {
  id: 'int_1',
  ts: 1,
  target: 'global',
  category: null,
  attribute: 'mood',
  value: 'calm, serene',
  confidence: 0.35,
  evidence: [],
  modifiers: ['ambient'],
}

describe('IntentPanel', () => {
  it('shows a placeholder with no intents', () => {
    render(<IntentPanel intents={[]} />)
    expect(screen.getByText(/inferred intentions will appear here/i)).toBeInTheDocument()
  })

  it('renders attribute, value, confidence and modifiers', () => {
    render(<IntentPanel intents={[frame]} />)
    expect(screen.getByText('mood')).toBeInTheDocument()
    expect(screen.getByText(/calm, serene/)).toBeInTheDocument()
    expect(screen.getByText(/0.35, ambient/)).toBeInTheDocument()
  })
})
