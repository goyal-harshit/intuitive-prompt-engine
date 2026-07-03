# API Specification

FastAPI backend, default `http://127.0.0.1:8000`. Frontend served at `/`.

## REST

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness + active backends (image gen, LLM) |
| POST | `/api/session` | start session → `{session_id}` (starts vision loop) |
| DELETE | `/api/session/{id}` | stop session, persist final snapshot |
| GET | `/api/session/{id}/scene` | current SceneGraph JSON |
| GET | `/api/session/{id}/generations` | list generated images (metadata) |
| POST | `/api/session/{id}/generate` | force generation (dev/debug escape hatch) |
| GET | `/api/session/{id}/frame` | latest camera frame w/ overlay (single JPEG; `204` while warming up) |
| GET | `/api/session/{id}/video` | live MJPEG stream of the annotated camera feed |
| GET | `/api/images/{image_id}` | image bytes (PNG) |
| GET | `/api/config` | active config (models, thresholds) |

Interactive OpenAPI docs are served at `/docs` (Swagger UI) and `/redoc`; the raw schema is at `/openapi.json`.

## WebSocket `/ws/{session_id}`

Server → client events (JSON, `{"type": ..., "data": ...}`):

| type | data | cadence |
|---|---|---|
| `features` | GestureFeatureVector | 10 Hz |
| `primitive` | detected motion primitive + confidence | on detection |
| `intent` | IntentFrame list | on emission |
| `scene_update` | SceneGraph diff + full snapshot | on mutation |
| `generation_started` | prompt used | on trigger |
| `generation_done` | `{image_id, url, prompt, latency_ms}` | on completion |
| `status` | pipeline state, camera fps, backend health | 1 Hz |

Client → server:

| type | data | purpose |
|---|---|---|
| `pause` / `resume` | — | freeze intent updates (user leaves frame) |
| `reset_scene` | — | archive graph, start fresh |

## Error model

`{"error": {"code": "CAMERA_UNAVAILABLE" | "BACKEND_DOWN" | ..., "message": str}}` with proper HTTP codes; WebSocket errors sent as `{"type": "error"}` events — pipeline degrades rather than dies (e.g., image backend down → scene graph continues updating).
