import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SettingsModal } from './SettingsModal'

describe('SettingsModal', () => {
  beforeEach(() => localStorage.clear())

  it('renders an accessible dialog prefilled with the saved backend URL on open', () => {
    // The app mounts the modal closed and toggles it open — the prefill
    // happens on that transition, so mirror it here.
    const { rerender } = render(<SettingsModal open={false} onOpenChange={() => {}} />)
    rerender(<SettingsModal open onOpenChange={() => {}} />)
    expect(screen.getByRole('dialog', { name: /api backend settings/i })).toBeInTheDocument()
    expect(screen.getByLabelText('Backend API URL')).toHaveValue('http://localhost:8000')
  })

  it('saves the entered URL to localStorage and closes', async () => {
    const onOpenChange = vi.fn()
    render(<SettingsModal open onOpenChange={onOpenChange} />)
    const input = screen.getByLabelText('Backend API URL')
    await userEvent.clear(input)
    await userEvent.type(input, 'my-server:9000')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(localStorage.getItem('backend_url')).toBe('http://my-server:9000')
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('cancel closes without persisting changes', async () => {
    const onOpenChange = vi.fn()
    render(<SettingsModal open onOpenChange={onOpenChange} />)
    const input = screen.getByLabelText('Backend API URL')
    await userEvent.clear(input)
    await userEvent.type(input, 'http://discard-me:1234')
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(localStorage.getItem('backend_url')).toBeNull()
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })
})
