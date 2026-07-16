import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ErrorBanner } from './ErrorBanner'

describe('ErrorBanner', () => {
  it('announces the message via role=alert', () => {
    render(
      <ErrorBanner
        title="Camera unavailable"
        message="no camera found"
        warn={false}
        onDismiss={() => {}}
      />,
    )
    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('Camera unavailable')
    expect(alert).toHaveTextContent('no camera found')
  })

  it('calls onDismiss when the dismiss button is activated', async () => {
    const onDismiss = vi.fn()
    render(<ErrorBanner title="Oops" message="something broke" warn onDismiss={onDismiss} />)
    await userEvent.click(screen.getByRole('button', { name: 'Dismiss' }))
    expect(onDismiss).toHaveBeenCalledTimes(1)
  })
})
