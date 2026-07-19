import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TopBar } from './TopBar'

function renderTopBar(overrides: Partial<Parameters<typeof TopBar>[0]> = {}) {
  const handlers = {
    onStart: vi.fn(),
    onStop: vi.fn(),
    onTogglePause: vi.fn(),
    onReset: vi.fn(),
    onOpenSettings: vi.fn(),
    onOpenHelp: vi.fn(),
  }
  render(
    <TopBar
      statusText="Ready"
      statusTone="idle"
      starting={false}
      sessionActive={false}
      paused={false}
      {...handlers}
      {...overrides}
    />,
  )
  return handlers
}

describe('TopBar', () => {
  it('announces status via a live region', () => {
    renderTopBar({ statusText: 'Session live' })
    expect(screen.getByRole('status')).toHaveTextContent('Session live')
  })

  it('enables only Start (and Settings/Help) when no session is active', () => {
    renderTopBar()
    expect(screen.getByRole('button', { name: /start session/i })).toBeEnabled()
    expect(screen.getByRole('button', { name: /stop/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Pause' })).toBeDisabled()
    expect(screen.getByRole('button', { name: /reset scene/i })).toBeDisabled()
  })

  it('flips control availability while a session is active', () => {
    renderTopBar({ sessionActive: true })
    expect(screen.getByRole('button', { name: /start session/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /stop/i })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Pause' })).toBeEnabled()
  })

  it('labels the pause toggle Resume while paused', () => {
    renderTopBar({ sessionActive: true, paused: true })
    expect(screen.getByRole('button', { name: 'Resume' })).toBeEnabled()
  })

  it('wires each control to its callback', async () => {
    const handlers = renderTopBar({ sessionActive: true })
    await userEvent.click(screen.getByRole('button', { name: /stop/i }))
    await userEvent.click(screen.getByRole('button', { name: 'Pause' }))
    await userEvent.click(screen.getByRole('button', { name: /reset scene/i }))
    await userEvent.click(screen.getByRole('button', { name: /settings/i }))
    await userEvent.click(screen.getByRole('button', { name: /how it works/i }))
    expect(handlers.onStop).toHaveBeenCalledTimes(1)
    expect(handlers.onTogglePause).toHaveBeenCalledTimes(1)
    expect(handlers.onReset).toHaveBeenCalledTimes(1)
    expect(handlers.onOpenSettings).toHaveBeenCalledTimes(1)
    expect(handlers.onOpenHelp).toHaveBeenCalledTimes(1)
  })
})
