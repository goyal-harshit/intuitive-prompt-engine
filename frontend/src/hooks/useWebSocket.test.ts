import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useWebSocket } from './useWebSocket'

class MockWebSocket {
  static instances: MockWebSocket[] = []
  static OPEN = 1
  static CLOSED = 3

  readyState = 0
  onopen: (() => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  onmessage: ((event: MessageEvent<string>) => void) | null = null
  sent: string[] = []
  closed = false
  url: string

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  open() {
    this.readyState = MockWebSocket.OPEN
    this.onopen?.()
  }

  send(data: string) {
    this.sent.push(data)
  }

  close() {
    this.closed = true
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.()
  }
}

beforeEach(() => {
  MockWebSocket.instances = []
  vi.stubGlobal('WebSocket', MockWebSocket)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('useWebSocket', () => {
  it('does not connect when url is null', () => {
    renderHook(() => useWebSocket(null, { onMessage: vi.fn() }))
    expect(MockWebSocket.instances).toHaveLength(0)
  })

  it('connects on mount and reports status transitions via the latest callback', () => {
    const onStatusChange = vi.fn()
    const { rerender } = renderHook(
      ({ cb }) => useWebSocket('ws://test/ws/abc', { onMessage: vi.fn(), onStatusChange: cb }),
      { initialProps: { cb: onStatusChange } },
    )

    expect(MockWebSocket.instances).toHaveLength(1)
    expect(onStatusChange).toHaveBeenCalledWith('connecting')

    const secondCallback = vi.fn()
    rerender({ cb: secondCallback })

    MockWebSocket.instances[0].open()
    expect(secondCallback).toHaveBeenCalledWith('open')
    expect(onStatusChange).not.toHaveBeenCalledWith('open')
  })

  it('parses incoming messages and forwards them to onMessage', () => {
    const onMessage = vi.fn()
    renderHook(() => useWebSocket('ws://test/ws/abc', { onMessage }))

    const ws = MockWebSocket.instances[0]
    ws.open()
    ws.onmessage?.({
      data: JSON.stringify({ type: 'status', data: { session_id: 'x' } }),
    } as MessageEvent<string>)

    expect(onMessage).toHaveBeenCalledWith({ type: 'status', data: { session_id: 'x' } })
  })

  it('only sends when the socket is open', () => {
    const { result } = renderHook(() => useWebSocket('ws://test/ws/abc', { onMessage: vi.fn() }))
    const ws = MockWebSocket.instances[0]

    result.current.send({ type: 'pause' })
    expect(ws.sent).toHaveLength(0)

    ws.open()
    result.current.send({ type: 'pause' })
    expect(ws.sent).toEqual([JSON.stringify({ type: 'pause' })])
  })

  it('closes the socket on unmount', () => {
    const { unmount } = renderHook(() => useWebSocket('ws://test/ws/abc', { onMessage: vi.fn() }))
    const ws = MockWebSocket.instances[0]
    unmount()
    expect(ws.closed).toBe(true)
  })
})
