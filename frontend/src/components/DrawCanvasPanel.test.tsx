import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DrawCanvasPanel } from './DrawCanvasPanel'
import type { DrawnShape } from '../types/domain'

const shape: DrawnShape = {
  id: 'shape1',
  shape: 'circle',
  points: [
    { ts: 0, x: 0.2, y: 0.2 },
    { ts: 1, x: 0.8, y: 0.2 },
  ],
  bbox_center: [0.5, 0.5],
  bbox_size: 0.3,
  position_label: 'center',
  duration_s: 1.2,
  confidence: 0.87,
}

describe('DrawCanvasPanel', () => {
  it('shows the placeholder hint when there is no stroke or shape yet', () => {
    render(<DrawCanvasPanel drawPoints={[]} lastShape={null} onClear={() => {}} />)
    expect(screen.getByText(/pinch thumb and index finger/i)).toBeInTheDocument()
  })

  it('renders the finalized shape label with confidence and position', () => {
    render(<DrawCanvasPanel drawPoints={[]} lastShape={shape} onClear={() => {}} />)
    expect(screen.getByText('circle')).toBeInTheDocument()
    expect(screen.getByText(/87%/)).toBeInTheDocument()
    expect(screen.getByText('center')).toBeInTheDocument()
  })

  it('calls onClear when the Clear button is clicked', async () => {
    const onClear = vi.fn()
    render(<DrawCanvasPanel drawPoints={[]} lastShape={shape} onClear={onClear} />)
    await userEvent.click(screen.getByRole('button', { name: 'Clear' }))
    expect(onClear).toHaveBeenCalledTimes(1)
  })
})
