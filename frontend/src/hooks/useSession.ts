import { useCallback, useReducer, useRef } from 'react'
import { createSession, endSession, imageUrl as buildImageUrl } from '../api/client'
import { getWsUrl } from '../lib/backendUrl'
import { useWebSocket } from './useWebSocket'
import type {
  DrawnShape,
  GestureDebugPayload,
  GestureFeatureVector,
  IntentFrame,
  SceneGraph,
  SequenceSegment,
  StrokePoint,
  WsMessage,
} from '../types/domain'

const MAX_LOG_ROWS = 30

export type StatusTone = 'ok' | 'busy' | 'err' | 'idle'

interface Banner {
  title: string
  message: string
  warn: boolean
}

export interface SessionState {
  sessionId: string | null
  starting: boolean
  paused: boolean
  statusText: string
  statusTone: StatusTone
  completeness: number
  features: GestureFeatureVector | null
  primitives: SequenceSegment[]
  intents: IntentFrame[]
  scene: SceneGraph | null
  generating: boolean
  prompt: string
  imageUrl: string | null
  banner: Banner | null
  drawPoints: StrokePoint[]
  lastShape: DrawnShape | null
  gestureDebug: GestureDebugPayload | null
  faceCalibrating: boolean
  ambient: Record<string, number>
}

export const initialState: SessionState = {
  sessionId: null,
  starting: false,
  paused: false,
  statusText: 'disconnected',
  statusTone: 'err',
  completeness: 0,
  features: null,
  primitives: [],
  intents: [],
  scene: null,
  generating: false,
  prompt: 'The prompt built from your gestures appears here.',
  imageUrl: null,
  banner: null,
  drawPoints: [],
  lastShape: null,
  gestureDebug: null,
  faceCalibrating: false,
  ambient: {},
}

type Action =
  | { type: 'START_REQUESTED' }
  | { type: 'STARTED'; sessionId: string }
  | { type: 'START_FAILED' }
  | { type: 'STOPPED' }
  | { type: 'PAUSED'; paused: boolean }
  | { type: 'WS_STATUS'; tone: StatusTone; text: string }
  | { type: 'BANNER_SHOW'; banner: Banner }
  | { type: 'BANNER_HIDE' }
  | { type: 'WS_MESSAGE'; msg: WsMessage }

export function reducer(state: SessionState, action: Action): SessionState {
  switch (action.type) {
    case 'START_REQUESTED':
      return { ...initialState, starting: true, statusText: 'connecting…', statusTone: 'busy' }
    case 'STARTED':
      return { ...state, starting: false, sessionId: action.sessionId }
    case 'START_FAILED':
      return { ...state, starting: false, statusText: 'backend error', statusTone: 'err' }
    case 'STOPPED':
      return { ...initialState }
    case 'PAUSED':
      return {
        ...state,
        paused: action.paused,
        statusText: action.paused ? 'paused' : 'live',
        statusTone: action.paused ? 'busy' : 'ok',
      }
    case 'WS_STATUS':
      return { ...state, statusText: action.text, statusTone: action.tone }
    case 'BANNER_SHOW':
      return { ...state, banner: action.banner }
    case 'BANNER_HIDE':
      return { ...state, banner: null }
    case 'WS_MESSAGE':
      return applyMessage(state, action.msg)
    default:
      return state
  }
}

function applyMessage(state: SessionState, msg: WsMessage): SessionState {
  switch (msg.type) {
    case 'features':
      return {
        ...state,
        features: msg.data,
        banner: state.banner && !state.banner.warn ? null : state.banner,
      }
    case 'primitive':
      return { ...state, primitives: [msg.data, ...state.primitives].slice(0, MAX_LOG_ROWS) }
    case 'intent':
      return { ...state, intents: [...msg.data, ...state.intents].slice(0, MAX_LOG_ROWS) }
    case 'scene_update':
      return { ...state, scene: msg.data, completeness: msg.data.meta.completeness }
    case 'generation_started':
      return { ...state, generating: true, prompt: msg.data.positive }
    case 'generation_done':
      return {
        ...state,
        generating: false,
        imageUrl: buildImageUrl(msg.data.url),
        prompt: `${msg.data.prompt}  ·  ${msg.data.backend}, ${msg.data.latency_ms} ms`,
      }
    case 'status':
      return {
        ...state,
        completeness: msg.data.completeness,
        generating: msg.data.generating,
        faceCalibrating: msg.data.face_calibrating,
        ambient: msg.data.ambient,
        statusText: msg.data.generating ? 'generating…' : state.paused ? 'paused' : 'live',
        statusTone: msg.data.generating ? 'busy' : state.paused ? 'busy' : 'ok',
      }
    case 'error':
      return applyError(state, msg.data.code, msg.data.message)
    case 'draw_stroke':
      return { ...state, drawPoints: [...state.drawPoints, msg.data] }
    case 'draw_shape':
      return { ...state, lastShape: msg.data, drawPoints: [] }
    case 'draw_clear':
      return { ...state, drawPoints: [], lastShape: null }
    case 'gesture_debug':
      return { ...state, gestureDebug: msg.data }
    default:
      return state
  }
}

function applyError(state: SessionState, code: string, message: string): SessionState {
  const withStatus: SessionState = { ...state, statusText: code, statusTone: 'err' }
  if (code === 'CAMERA_UNAVAILABLE') {
    return {
      ...withStatus,
      banner: {
        title: 'Camera unavailable',
        message:
          "GestureGPT couldn't open your webcam. Close any other app that may be using it " +
          '(Zoom, Teams, Camera), then click Start session again. On Windows also check ' +
          'Settings → Privacy & security → Camera → "Let desktop apps access your camera."',
        warn: false,
      },
    }
  }
  if (code === 'BACKEND_DOWN') {
    return {
      ...withStatus,
      banner: {
        title: 'Image backend error',
        message: `The image generator didn't respond: ${message}. Check your internet connection — the pipeline keeps running and will retry.`,
        warn: true,
      },
    }
  }
  return withStatus
}

export function useSession() {
  const [state, dispatch] = useReducer(reducer, initialState)
  const sessionIdRef = useRef<string | null>(null)

  const wsUrl = state.sessionId ? `${getWsUrl()}/ws/${state.sessionId}` : null

  const { send } = useWebSocket(wsUrl, {
    onMessage: (msg) => dispatch({ type: 'WS_MESSAGE', msg }),
    onStatusChange: (status) => {
      if (status === 'open') dispatch({ type: 'WS_STATUS', tone: 'ok', text: 'live' })
      else if (status === 'closed' && sessionIdRef.current)
        dispatch({ type: 'WS_STATUS', tone: 'err', text: 'disconnected' })
      else if (status === 'error')
        dispatch({ type: 'WS_STATUS', tone: 'err', text: 'connection error' })
    },
  })

  const start = useCallback(async () => {
    dispatch({ type: 'BANNER_HIDE' })
    dispatch({ type: 'START_REQUESTED' })
    try {
      if (sessionIdRef.current) {
        await endSession(sessionIdRef.current)
      }
      const { session_id } = await createSession()
      sessionIdRef.current = session_id
      dispatch({ type: 'STARTED', sessionId: session_id })
    } catch {
      dispatch({ type: 'START_FAILED' })
    }
  }, [])

  const stop = useCallback(async () => {
    const id = sessionIdRef.current
    sessionIdRef.current = null
    dispatch({ type: 'STOPPED' })
    if (id) await endSession(id)
  }, [])

  const togglePause = useCallback(() => {
    const next = !state.paused
    send({ type: next ? 'pause' : 'resume' })
    dispatch({ type: 'PAUSED', paused: next })
  }, [send, state.paused])

  const resetScene = useCallback(() => {
    send({ type: 'reset_scene' })
  }, [send])

  const clearDraw = useCallback(() => {
    send({ type: 'draw_clear' })
    dispatch({ type: 'WS_MESSAGE', msg: { type: 'draw_clear', data: {} } })
  }, [send])

  const dismissBanner = useCallback(() => dispatch({ type: 'BANNER_HIDE' }), [])

  return { state, start, stop, togglePause, resetScene, clearDraw, dismissBanner }
}
