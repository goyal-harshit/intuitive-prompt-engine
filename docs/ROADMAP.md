# Development Roadmap

## Phase 1 — Vertical slice (this repo, MVP) ✅
1. Vision: OpenCV capture + MediaPipe hands/pose/face → LandmarkFrame. *(dep: none)* → live landmark stream
2. Gestures: feature math + prototype-based primitive segmentation. *(dep: 1)* → GestureFeatureVector, SequenceSegment
3. Intent: declarative ontology + evidence fusion with decay/hysteresis. *(dep: 2)* → IntentFrame
4. Scene Graph: merge semantics, completeness, diff. *(dep: 3)* → SceneGraph
5. Prompting: template generator + Ollama strategy (auto-detect). *(dep: 4)* → OptimizedPrompt
6. Imagegen: Pollinations adapter (free, keyless) + HF adapter. *(dep: 5)* → GeneratedImage
7. FastAPI + WebSocket + SPA frontend; SQLite persistence. *(dep: 4–6)* → runnable app

## Phase 2 — Robustness
- Unit tests for feature math and fusion (pytest, synthetic landmark fixtures)
- Session replay tool (`tools/replay.py`) from SQLite event log
- Calibration step (user hand-size / reach normalization)

## Phase 3 — Smarter intent
- Replace prototype matching with a small temporal model (1D-CNN/GRU on feature windows, PyTorch, trained on recorded sessions)
- LLM-based IntentModel option: feed segment descriptions + history to Ollama for hypothesis generation
- YAML-externalized ontology with hot reload

## Phase 4 — Generation quality
- ComfyUI adapter with SDXL/FLUX workflows (img2img refinement: new render conditioned on previous image + graph diff)
- Negative-prompt synthesis from rejected hypotheses
- Style memory across sessions

## Phase 5 — Interaction research
- Refinement gestures acting on the *rendered* image (point-at-region + gesture = local edit via inpainting)
- Attention/gaze weighting of object salience
- User studies: task completion vs. typed prompting baseline

## Phase 6 — Product polish
- Vite + React + Tailwind frontend (replace static SPA; WebSocket contract unchanged)
- Docker compose (backend + ComfyUI), CI (ruff, mypy, pytest) via GitHub Actions
- Plugin system for ontology packs (architecture, character design, etc.)

MVP = Phase 1. Everything else is enhancement; interfaces already anticipate it.
