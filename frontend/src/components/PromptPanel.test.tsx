import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PromptPanel } from './PromptPanel'

describe('PromptPanel', () => {
  it('renders the compiled prompt text', () => {
    render(<PromptPanel prompt="cinematic digital painting, 8k" />)
    expect(screen.getByText('cinematic digital painting, 8k')).toBeInTheDocument()
  })
})
