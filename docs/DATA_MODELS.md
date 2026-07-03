# Data Models

## Runtime models (Pydantic, `backend/*/schema.py`)

```python
LandmarkFrame:      ts, hands: list[HandLandmarks], pose: PoseLandmarks|None,
                    face: FaceSignals|None, frame_size
GestureFeatureVector: ts, openness, separation, expansion_rate, verticality,
                    vertical_velocity, pointing: vec3|None, circularity, tempo,
                    smoothness, symmetry, posture_lean, head_yaw, head_pitch,
                    valence, arousal, stillness
SequenceSegment:    id, primitive: MotionPrimitive, t_start, t_end, confidence,
                    params: dict (direction, plane, radius, speed)
IntentFrame:        id, ts, target: "global"|object_id|"new_object",
                    attribute, value, confidence, evidence: list[segment_id],
                    modifiers: list[str]
AttributeValue:     value, confidence, updated_at, provenance
SceneObject:        id, category, attributes, salience
SceneGraph:         objects, globals, history, meta
OptimizedPrompt:    positive, negative, guidance, steps, aspect_ratio, seed|None,
                    model_hint
GeneratedImage:     id, session_id, prompt_id, path, backend, latency_ms, created_at
```

## SQLite schema (SQLAlchemy, `backend/storage/models.py`)

```
sessions        (id PK, started_at, ended_at, config_json)
gesture_events  (id PK, session_id FK, ts, primitive, confidence, params_json)
intent_events   (id PK, session_id FK, ts, target, attribute, value, confidence)
scene_snapshots (id PK, session_id FK, revision, ts, graph_json, completeness)
prompts         (id PK, session_id FK, snapshot_id FK, positive, negative,
                 params_json, generator)
generations     (id PK, session_id FK, prompt_id FK, backend, image_path,
                 latency_ms, created_at)
```

Append-only event tables → full session replay for offline analysis / future model training (research value: dataset of gesture→intent→image triples).

## Config (`config.yaml`)

```yaml
camera: {index: 0, width: 640, height: 480, fps: 30}
vision: {hands: true, pose: true, face: true}
intent: {window_s: 1.5, decay_half_life_s: 90, min_confidence: 0.35}
scene:  {completeness_threshold: 0.6, stability_s: 2.0, regen_diff: 0.25}
prompting: {strategy: auto, ollama_model: qwen2.5:3b}   # auto → ollama if up, else template
imagegen:
  backend: pollinations          # pollinations | huggingface | comfyui
  huggingface: {model: stabilityai/stable-diffusion-xl-base-1.0, token_env: HF_TOKEN}
  comfyui: {url: "http://127.0.0.1:8188", workflow: sdxl_default}
server: {host: 127.0.0.1, port: 8000}
```
