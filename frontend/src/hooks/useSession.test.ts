import { describe, expect, it } from 'vitest'
import { initialState, reducer, type SessionState } from './useSession'
import type { SceneGraph, WsMessage } from '../types/domain'

const scene: SceneGraph = {
  objects: {
    obj1: {
      id: 'obj1',
      category: 'tree',
      attributes: {},
      salience: 0.5,
    },
  },
  globals: {},
  history: [],
  meta: { created_at: 0, updated_at: 0, revision: 1, completeness: 0.42 },
}

function dispatchAll(state: SessionState, messages: WsMessage[]): SessionState {
  return messages.reduce((s, msg) => reducer(s, { type: 'WS_MESSAGE', msg }), state)
}

describe('useSession reducer', () => {
  it('starts a session and clears prior state', () => {
    const started = reducer(initialState, { type: 'START_REQUESTED' })
    expect(started.starting).toBe(true)
    expect(started.statusTone).toBe('busy')

    const withSession = reducer(started, { type: 'STARTED', sessionId: 'abc123' })
    expect(withSession.starting).toBe(false)
    expect(withSession.sessionId).toBe('abc123')
  })

  it('marks start as failed on backend error', () => {
    const result = reducer(initialState, { type: 'START_FAILED' })
    expect(result.starting).toBe(false)
    expect(result.statusTone).toBe('err')
    expect(result.statusText).toBe('backend error')
  })

  it('resets to initial state when stopped', () => {
    const started = reducer(initialState, { type: 'STARTED', sessionId: 'abc123' })
    const stopped = reducer(started, { type: 'STOPPED' })
    expect(stopped).toEqual(initialState)
  })

  it('toggles pause status text and tone', () => {
    const paused = reducer(initialState, { type: 'PAUSED', paused: true })
    expect(paused.statusText).toBe('paused')
    expect(paused.statusTone).toBe('busy')

    const resumed = reducer(paused, { type: 'PAUSED', paused: false })
    expect(resumed.statusText).toBe('live')
    expect(resumed.statusTone).toBe('ok')
  })

  it('applies scene_update messages and tracks completeness', () => {
    const next = dispatchAll(initialState, [{ type: 'scene_update', data: scene }])
    expect(next.scene).toEqual(scene)
    expect(next.completeness).toBeCloseTo(0.42)
  })

  it('caps primitive and intent logs at MAX_LOG_ROWS (30), newest first', () => {
    const primitives: WsMessage[] = Array.from({ length: 35 }, (_, i) => ({
      type: 'primitive',
      data: {
        id: `p${i}`,
        primitive: 'sweep',
        t_start: i,
        t_end: i + 1,
        confidence: 0.9,
        params: {},
      },
    }))
    const next = dispatchAll(initialState, primitives)
    expect(next.primitives).toHaveLength(30)
    expect(next.primitives[0].id).toBe('p34')
  })

  it('shows a non-warn banner for CAMERA_UNAVAILABLE and clears it on next features message', () => {
    const withError = dispatchAll(initialState, [
      { type: 'error', data: { code: 'CAMERA_UNAVAILABLE', message: 'no camera' } },
    ])
    expect(withError.banner?.title).toBe('Camera unavailable')
    expect(withError.banner?.warn).toBe(false)

    const featureVector = {
      ts: 0,
      hands_visible: 1,
      openness: 0,
      pinch: 1,
      separation: 0,
      expansion_rate: 0,
      verticality: 0,
      vertical_velocity: 0,
      pointing_up: 0,
      pointing_forward: 0,
      circularity: 0,
      circle_overhead: 0,
      horizontal_travel: 0,
      depth_velocity: 0,
      tempo: 0,
      smoothness: 0,
      symmetry: 0,
      posture_lean: 0,
      head_yaw: 0,
      head_pitch: 0,
      valence: 0,
      arousal: 0,
      stillness: 0,
    }
    const cleared = dispatchAll(withError, [{ type: 'features', data: featureVector }])
    expect(cleared.banner).toBeNull()
  })

  it('shows a warn banner for BACKEND_DOWN that features messages do not clear', () => {
    const withError = dispatchAll(initialState, [
      { type: 'error', data: { code: 'BACKEND_DOWN', message: 'timeout' } },
    ])
    expect(withError.banner?.warn).toBe(true)

    const featureVector = {
      ts: 0,
      hands_visible: 1,
      openness: 0,
      pinch: 1,
      separation: 0,
      expansion_rate: 0,
      verticality: 0,
      vertical_velocity: 0,
      pointing_up: 0,
      pointing_forward: 0,
      circularity: 0,
      circle_overhead: 0,
      horizontal_travel: 0,
      depth_velocity: 0,
      tempo: 0,
      smoothness: 0,
      symmetry: 0,
      posture_lean: 0,
      head_yaw: 0,
      head_pitch: 0,
      valence: 0,
      arousal: 0,
      stillness: 0,
    }
    const stillShown = dispatchAll(withError, [{ type: 'features', data: featureVector }])
    expect(stillShown.banner?.warn).toBe(true)
  })

  it('tracks generation lifecycle from generation_started to generation_done', () => {
    const started = dispatchAll(initialState, [
      { type: 'generation_started', data: { positive: 'a glowing forest', generator: 'sd' } },
    ])
    expect(started.generating).toBe(true)
    expect(started.prompt).toBe('a glowing forest')

    const done = dispatchAll(started, [
      {
        type: 'generation_done',
        data: {
          image_id: 'img1',
          url: '/api/images/img1',
          prompt: 'a glowing forest',
          latency_ms: 1234,
          backend: 'sd',
        },
      },
    ])
    expect(done.generating).toBe(false)
    expect(done.imageUrl).toContain('/api/images/img1')
    expect(done.prompt).toContain('sd, 1234 ms')
  })

  it('accumulates draw_stroke points and resets them on draw_shape', () => {
    const withStrokes = dispatchAll(initialState, [
      { type: 'draw_stroke', data: { ts: 0, x: 0.1, y: 0.1 } },
      { type: 'draw_stroke', data: { ts: 1, x: 0.2, y: 0.2 } },
    ])
    expect(withStrokes.drawPoints).toHaveLength(2)
    expect(withStrokes.lastShape).toBeNull()

    const shape = {
      id: 'shape1',
      shape: 'circle',
      points: withStrokes.drawPoints,
      bbox_center: [0.5, 0.5] as [number, number],
      bbox_size: 0.3,
      position_label: 'center',
      duration_s: 1.2,
      confidence: 0.87,
    }
    const withShape = dispatchAll(withStrokes, [{ type: 'draw_shape', data: shape }])
    expect(withShape.lastShape).toEqual(shape)
    expect(withShape.drawPoints).toHaveLength(0)
  })

  it('clears drawPoints and lastShape on draw_clear', () => {
    const withStrokes = dispatchAll(initialState, [
      { type: 'draw_stroke', data: { ts: 0, x: 0.1, y: 0.1 } },
    ])
    const cleared = dispatchAll(withStrokes, [{ type: 'draw_clear', data: {} }])
    expect(cleared.drawPoints).toHaveLength(0)
    expect(cleared.lastShape).toBeNull()
  })

  it('stores the latest gesture_debug payload', () => {
    const debug = {
      drawing: true,
      matches: [
        { primitive: 'expand', match_score: 0.7, would_mean: 'scene → grows', base_weight: 0.8 },
      ],
    }
    const next = dispatchAll(initialState, [{ type: 'gesture_debug', data: debug }])
    expect(next.gestureDebug).toEqual(debug)
  })

  it('applies face_calibrating and ambient from status messages', () => {
    const next = dispatchAll(initialState, [
      {
        type: 'status',
        data: {
          session_id: 's1',
          paused: false,
          completeness: 0.2,
          revision: 1,
          generating: false,
          face_calibrating: true,
          ambient: { valence: 0.1, arousal: 0.2 },
        },
      },
    ])
    expect(next.faceCalibrating).toBe(true)
    expect(next.ambient).toEqual({ valence: 0.1, arousal: 0.2 })
  })
})
