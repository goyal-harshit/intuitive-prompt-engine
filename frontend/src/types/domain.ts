/** Hand-modeled WebSocket payload shapes — the OpenAPI schema only covers REST.
 * Kept in sync with backend/gestures/schema.py, backend/scene/schema.py,
 * backend/intent/schema.py and the publish payloads in backend/pipeline/orchestrator.py. */

export const FEATURE_KEYS = [
  'openness',
  'separation',
  'expansion_rate',
  'verticality',
  'circularity',
  'tempo',
  'smoothness',
  'stillness',
  'valence',
  'arousal',
] as const

export type FeatureKey = (typeof FEATURE_KEYS)[number]

export interface GestureFeatureVector {
  ts: number
  hands_visible: number
  openness: number
  pinch: number
  separation: number
  expansion_rate: number
  verticality: number
  vertical_velocity: number
  pointing_up: number
  pointing_forward: number
  circularity: number
  circle_overhead: number
  horizontal_travel: number
  depth_velocity: number
  tempo: number
  smoothness: number
  symmetry: number
  posture_lean: number
  head_yaw: number
  head_pitch: number
  valence: number
  arousal: number
  stillness: number
}

export interface SequenceSegment {
  id: string
  primitive: string
  t_start: number
  t_end: number
  confidence: number
  params: Record<string, number | string>
}

export interface IntentFrame {
  id: string
  ts: number
  target: string
  category: string | null
  attribute: string
  value: string
  confidence: number
  evidence: string[]
  modifiers: string[]
}

export interface AttributeValue {
  value: string
  confidence: number
  updated_at: number
  provenance: string[]
}

export interface SceneObject {
  id: string
  category: string
  attributes: Record<string, AttributeValue>
  salience: number
}

export interface SceneEvent {
  ts: number
  kind: string
  detail: string
}

export interface SceneMeta {
  created_at: number
  updated_at: number
  revision: number
  completeness: number
}

export interface SceneGraph {
  objects: Record<string, SceneObject>
  globals: Record<string, AttributeValue>
  history: SceneEvent[]
  meta: SceneMeta
}

export interface GenerationStartedPayload {
  positive: string
  generator: string
  [key: string]: unknown
}

export interface GenerationDonePayload {
  image_id: string
  url: string
  prompt: string
  latency_ms: number
  backend: string
}

export interface StatusPayload {
  session_id: string
  paused: boolean
  completeness: number
  revision: number
  generating: boolean
  face_calibrating: boolean
  ambient: Record<string, number>
}

export type ErrorCode = 'CAMERA_UNAVAILABLE' | 'BACKEND_DOWN' | string

export interface ErrorPayload {
  code: ErrorCode
  message: string
}

export interface StrokePoint {
  ts: number
  x: number
  y: number
}

export interface DrawnShape {
  id: string
  shape: string
  points: StrokePoint[]
  bbox_center: [number, number]
  bbox_size: number
  position_label: string
  duration_s: number
  confidence: number
}

export interface GestureDebugMatch {
  primitive: string
  match_score: number
  would_mean: string
  base_weight: number
}

export interface GestureDebugPayload {
  drawing: boolean
  matches: GestureDebugMatch[]
}

export type WsMessage =
  | { type: 'features'; data: GestureFeatureVector }
  | { type: 'primitive'; data: SequenceSegment }
  | { type: 'intent'; data: IntentFrame[] }
  | { type: 'scene_update'; data: SceneGraph }
  | { type: 'generation_started'; data: GenerationStartedPayload }
  | { type: 'generation_done'; data: GenerationDonePayload }
  | { type: 'status'; data: StatusPayload }
  | { type: 'error'; data: ErrorPayload }
  | { type: 'draw_stroke'; data: StrokePoint }
  | { type: 'draw_shape'; data: DrawnShape }
  | { type: 'draw_clear'; data: Record<string, never> }
  | { type: 'gesture_debug'; data: GestureDebugPayload }
