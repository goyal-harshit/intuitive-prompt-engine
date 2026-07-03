# GestureGPT — System Architecture

GestureGPT is an intent-driven multimodal HCI system. It does **not** map gestures to commands. It extracts continuous semantic features from body language, accumulates evidence over time, and maintains an evolving Scene Graph of the user's creative intent, which is compiled into optimized prompts for image generation models.

## 1. Pipeline

```
Webcam (30 fps)
   │
   ▼
┌──────────────────┐   raw frames
│ Vision Processing │  OpenCV capture, MediaPipe Tasks:
│  (vision/)        │  hand (21 pts ×2), pose (33 pts), face blendshapes
└──────────────────┘
   │  LandmarkFrame (normalized, timestamped)
   ▼
┌──────────────────┐
│ Gesture Analysis  │  Continuous semantic features per window:
│  (gestures/)      │  openness, expansion_rate, verticality, circularity,
└──────────────────┘  tempo, symmetry, pointing vector, posture lean, valence
   │  GestureFeatureVector + SequenceSegment
   ▼
┌──────────────────┐
│ Intent Engine     │  Temporal evidence fusion → IntentFrame(s):
│  (intent/)        │  semantic hypotheses with confidence, NOT commands
└──────────────────┘  e.g. {attribute: scale, direction: +, conf: 0.82}
   │  IntentFrame[]
   ▼
┌──────────────────┐
│ Scene Graph       │  Persistent, additive world model:
│  (scene/)         │  objects + global attributes, confidence, provenance,
└──────────────────┘  temporal decay, conflict resolution by evidence weight
   │  SceneGraph snapshot (when completeness ≥ threshold or user "commit" intent)
   ▼
┌──────────────────┐
│ Prompt Generation │  Strategy interface:
│  (prompting/)     │  LLM (Ollama: qwen2.5/mistral) or deterministic template
└──────────────────┘
   │  OptimizedPrompt {positive, negative, params}
   ▼
┌──────────────────┐
│ Image Generation  │  Adapter interface:
│  (imagegen/)      │  Pollinations (free, default) | HF Inference | ComfyUI(SDXL/FLUX)
└──────────────────┘
   │  GeneratedImage
   ▼
┌──────────────────┐
│ Feedback Engine + │  FastAPI + WebSocket → SPA frontend:
│ Frontend          │  live features, scene graph viz, image, refinement loop
└──────────────────┘
```

All stages communicate through typed dataclasses/Pydantic models on an in-process event bus (`pipeline/orchestrator.py`). Every arrow is an interface (ABC) — any stage can be replaced independently.

## 2. Design principles

- **Semantic features, not gesture classes.** The gestures layer emits continuous measurements (e.g., `hand_openness ∈ [0,1]`, `expansion_rate` in units/s, `circularity` score). Discrete "gesture names" exist only as weak evidence labels, never as commands.
- **Evidence accumulation.** The Intent Engine fuses features over sliding windows (default 1.5 s) using exponential decay + hysteresis, producing hypotheses that must persist to affect the Scene Graph. A single frame can never mutate the scene.
- **Additive world model.** Scene Graph updates merge; they never replace. Each attribute stores value, confidence, timestamp, and provenance (which intent frames produced it).
- **Strategy + Adapter everywhere.** `PromptGenerator`, `ImageGenerator`, `IntentModel`, `LandmarkExtractor` are ABCs. Swapping FLUX for SDXL, or a rules-based intent model for an LLM-based one, touches one file.
- **Graceful degradation.** No GPU → Pollinations API. No Ollama → template prompt generator. No face model → mood inferred from motion tempo only. The system always runs.

## 3. Module contracts

| Module | Input | Output | Replaceable via |
|---|---|---|---|
| `vision.capture` | device index | BGR frames | `FrameSource` ABC |
| `vision.landmarks` | frame | `LandmarkFrame` | `LandmarkExtractor` ABC |
| `gestures.features` | `LandmarkFrame` stream | `GestureFeatureVector` | pure functions |
| `gestures.sequence` | feature stream | `SequenceSegment` (motion primitives) | `SequenceSegmenter` ABC |
| `intent.engine` | segments + history | `IntentFrame[]` | `IntentModel` ABC |
| `scene.graph` | `IntentFrame[]` | `SceneGraph` | — (core state) |
| `prompting.*` | `SceneGraph` | `OptimizedPrompt` | `PromptGenerator` ABC |
| `imagegen.*` | `OptimizedPrompt` | `GeneratedImage` | `ImageGenerator` ABC |
| `storage.*` | events/snapshots | SQLite rows | SQLAlchemy repository |
| `pipeline.orchestrator` | all above | WebSocket state events | — |

## 4. Concurrency model

- Vision loop runs in a dedicated thread (camera I/O bound).
- Feature extraction + intent run synchronously in that loop (cheap, <5 ms).
- Scene Graph is owned by the asyncio event loop; vision thread posts via `asyncio.run_coroutine_threadsafe`.
- Prompt + image generation run as background asyncio tasks (network bound), debounced: a new generation cancels only if the scene changed materially (graph diff score > threshold).

## 5. Directory structure

```
gesturegpt/
├── backend/
│   ├── app/               # FastAPI entry, routes, websocket
│   ├── core/              # config, event bus, logging
│   ├── vision/            # capture, landmark extraction
│   ├── gestures/          # feature math, sequence segmentation
│   ├── intent/            # ontology, evidence fusion, intent models
│   ├── scene/             # scene graph, schema, diffing
│   ├── prompting/         # base, template, ollama
│   ├── imagegen/          # base, pollinations, hf_api, comfyui
│   ├── storage/           # SQLAlchemy models, repositories
│   └── pipeline/          # orchestrator wiring
├── frontend/              # SPA (static; Vite/React in Phase 6)
├── docs/
├── tests/
├── config.yaml
├── requirements.txt
└── run.py
```

## 6. Trade-offs recorded

- **Server-side vision (OpenCV/MediaPipe Python)** over browser-side (MediaPipe JS): keeps CV in Python (research value, testability); costs one process and a camera permission. Interface `LandmarkExtractor` allows a future browser-landmark WebSocket source without touching downstream stages.
- **In-process event bus** over message broker: single-user local app; Redis/NATS is premature. The bus API mirrors pub/sub so a broker can be substituted later.
- **SQLite** over Postgres: zero-install, adequate write rate (~10 events/s). Repository pattern isolates the choice.
- **Debounced continuous generation** over explicit "generate" gesture: preserves the no-command philosophy; hysteresis prevents API flooding.
