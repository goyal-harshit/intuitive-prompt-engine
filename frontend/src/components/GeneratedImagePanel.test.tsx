import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { GeneratedImagePanel } from './GeneratedImagePanel'

describe('GeneratedImagePanel', () => {
  it('shows the waiting hint with no image and not generating', () => {
    render(<GeneratedImagePanel imageUrl={null} generating={false} />)
    expect(screen.getByText(/waiting for the scene/i)).toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('announces generation progress via a live region', () => {
    render(<GeneratedImagePanel imageUrl={null} generating />)
    expect(screen.getByRole('status')).toHaveTextContent(/generating/i)
    expect(screen.getByText(/rendering your scene/i)).toBeInTheDocument()
  })

  it('renders the generated image with alt text', () => {
    render(<GeneratedImagePanel imageUrl="/api/images/img_1" generating={false} />)
    expect(screen.getByRole('img', { name: 'Generated scene' })).toHaveAttribute(
      'src',
      '/api/images/img_1',
    )
  })
})
