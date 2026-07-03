# Contributing

Thanks for your interest in IntuitivePromptEngine! This is a portfolio/research
project, but issues and pull requests are welcome.

## Development setup

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements-dev.txt
```

## Before you push

The CI pipeline (`.github/workflows/ci.yml`) runs these on Python 3.10–3.12.
Run them locally first — they must all pass:

```bash
ruff check .      # lint
mypy              # type-check
pytest            # unit + integration tests
```

For Docker changes, verify the stack builds and boots:

```bash
docker compose up --build
# backend health: http://localhost:8000/api/health
# frontend:       http://localhost:8080
docker compose down -v
```

## Architecture

Every pipeline stage sits behind an interface (`FrameSource`,
`LandmarkExtractor`, `IntentModel`, `PromptGenerator`, `ImageGenerator`) — add a
new backend by implementing the interface and wiring it in the relevant
`factory.py`, without touching the rest. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Conventions

- Keep the vision/gesture/intent/scene layers pure and testable — no camera or
  network in the merge logic (see `tests/test_scene_graph.py`).
- New public config lives in `backend/core/config.py`; deployment knobs get an
  entry in `_ENV_OVERRIDES` and a line in `.env.example`.
- Add or update tests for behavior changes.
