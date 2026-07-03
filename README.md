# IntuitivePromptEngine

**An intent-driven multimodal prompt generation system.** IntuitivePromptEngine watches your hands, posture, and expression through a standard webcam, infers your *creative intention* — not commands — and continuously compiles an evolving Scene Graph of your imagination into optimized prompts for generative image models. You never type a prompt.

## GitHub Pages Deployment
The frontend of this project is ready to be hosted statically on GitHub Pages!
- Set up GitHub Pages in your repository settings to build and deploy via GitHub Actions.
- When running the frontend on GitHub Pages, click the ⚙️ **Settings** button in the topbar to configure your local Python backend URL (default: `http://localhost:8000`). This bridges the static UI with your local webcam and models.

## Quick start (CPU-only, no API keys)

Requires Python 3.10–3.12 and a webcam.

**Windows — one click:** just double-click **`start.bat`**. On first run it creates the
virtual environment, installs dependencies, then launches the server and opens your
browser automatically. Subsequent runs skip straight to launch. If port 8000 is busy
it automatically moves to the next free port.

**Manual (any OS):**

```bash
git clone https://github.com/goyal-harshit/intuitive-prompt-engine && cd intuitive-prompt-engine
python -m venv .venv
.venv\Scripts\activate          # Windows   (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
python run.py
```

The server opens automatically (or open the printed URL — 127.0.0.1:8000 by default),
click **Start session**, and gesture. Images are generated through the free Pollinations FLUX endpoint by default — no GPU, no key.

Optional upgrades (each is a `config.yaml` change, nothing else):

- **Local LLM prompt optimization** — install [Ollama](https://ollama.com), `ollama pull qwen2.5:3b`. Auto-detected.
- **Hugging Face SDXL** — set `HF_TOKEN`, switch `imagegen.backend: huggingface`.
- **Local ComfyUI (SDXL/FLUX)** — Phase 4 adapter, see [docs/ROADMAP.md](docs/ROADMAP.md).

## How it works

Rather than mapping gestures to commands, GestureGPT extracts **continuous semantic features** (openness, expansion rate, circularity, tempo, smoothness, affect…), segments them into **motion primitives** by soft prototype matching, and fuses primitives with interaction history into **intent hypotheses** with confidence scores. Hypotheses merge into a persistent **Scene Graph** (objects + environment, mood, lighting, camera, style…) using noisy-OR reinforcement, confidence-decay conflict resolution, and object coreference. When the graph is sufficiently complete and stable, a swappable prompt strategy (Ollama LLM or deterministic template) compiles it into a diffusion-ready prompt, and a swappable image backend renders it. Your next gestures refine the same scene.

Full design: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/GESTURE_ONTOLOGY.md](docs/GESTURE_ONTOLOGY.md) · [docs/SCENE_GRAPH.md](docs/SCENE_GRAPH.md) · [docs/API.md](docs/API.md) · [docs/DATA_MODELS.md](docs/DATA_MODELS.md) · [docs/ROADMAP.md](docs/ROADMAP.md)

## Project structure

```
backend/
  vision/     webcam capture + MediaPipe landmark extraction
  gestures/   semantic feature math + motion-primitive segmentation
  intent/     declarative ontology + evidence-fusion engine
  scene/      Scene Graph: merge semantics, decay, completeness, diff
  prompting/  strategies: template | Ollama (auto-detected)
  imagegen/   adapters: Pollinations | HF Inference | ComfyUI
  storage/    SQLite event log (full session replay)
  pipeline/   orchestrator wiring
  app/        FastAPI + WebSocket
frontend/     zero-build SPA (live features, scene graph, image)
docs/         architecture & research design docs
```

Every stage sits behind an interface (`FrameSource`, `LandmarkExtractor`, `IntentModel`, `PromptGenerator`, `ImageGenerator`) — swap models without touching the rest.

## Tech

Python · OpenCV · MediaPipe · FastAPI · Pydantic · SQLAlchemy/SQLite · httpx · Ollama (Qwen/Mistral) · FLUX/SDXL. All free and open source.

## License

MIT
