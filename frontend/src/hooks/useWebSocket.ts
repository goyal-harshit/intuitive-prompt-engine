import { useEffect, useRef, useCallback } from 'react'
import type { WsMessage } from '../types/domain'

export type WsConnectionState = 'connecting' | 'open' | 'closed' | 'error'

interface UseWebSocketOptions {
  onMessage: (msg: WsMessage) => void
  onStatusChange?: (state: WsConnectionState) => void
}

/** Thin WebSocket lifecycle wrapper: connects when `url` is set, tears down on
 * unmount or URL change, and hands parsed messages to the latest callbacks
 * without forcing a reconnect every render. */
export function useWebSocket(url: string | null, options: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null)
  const optionsRef = useRef(options)

  useEffect(() => {
    optionsRef.current = options
  })

  useEffect(() => {
    if (!url) return undefined

    optionsRef.current.onStatusChange?.('connecting')
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => optionsRef.current.onStatusChange?.('open')
    ws.onclose = () => optionsRef.current.onStatusChange?.('closed')
    ws.onerror = () => optionsRef.current.onStatusChange?.('error')
    ws.onmessage = (event: MessageEvent<string>) => {
      optionsRef.current.onMessage(JSON.parse(event.data) as WsMessage)
    }

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [url])

  const send = useCallback((msg: Record<string, unknown>) => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg))
    }
  }, [])

  return { send }
}
