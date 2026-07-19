# Contributing

Thanks for your interest in IntuitivePromptEngine! This is a portfolio/research
project, but issues and pull requests are welcome.

## Development setup

**Backend:**

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements-dev.txt
pre-commit install                # optional but recommended — runs ruff/mypy/prettier on staged files
python run.py                     # http://127.0.0.1:8000
```

**Frontend** (separate terminal, in `frontend/`):

```bash
npm install
npm run dev                       # http://localhost:5173, proxies /api and /ws to :8000
```

Run both together to work on the UI against a live backend, or use the convenience script that starts both and stops both on Ctrl+C: `./scripts/dev.sh` (Linux/macOS) or `./scripts/dev.ps1` (Windows PowerShell). If you change any backend Pydantic models/routes that affect the API shape, regenerate the frontend's TypeScript types afterwards:

```bash
cd frontend
npm run generate-types            # backend must be running; writes src/types/api.d.ts
```

Do not hand-edit `frontend/src/types/api.d.ts` — it's generated and excluded from Prettier.

## Before you push

The CI pipeline (`.github/workflows/ci.yml`) runs these on Python 3.10–3.12.
Run them locally first — they must all pass:

```bash
ruff check .      # lint
mypy              # type-check
pytest            # unit + integration tests
```

Or run every gate (backend + frontend + a hygiene scan) with one command:

```bash
./scripts/verify.sh                # Linux/macOS   (.\scripts\verify.ps1 on Windows)
./scripts/verify.sh --repeat 3     # repeat pytest to surface flaky tests
```

To sweep out tool caches, coverage artifacts, and editor leftovers:

```bash
./scripts/clean.sh                 # dry-run: shows what would be deleted
./scripts/clean.sh --apply         # delete (never touches git-tracked files)
```

Both are thin wrappers over `tools/audit.py` (`scan` / `clean` / `verify`), which also
reports suspiciously named files (`temp.py`, `final_copy.js`, ...) for manual review —
it never deletes those automatically.

A parallel CI job does the same for the frontend (in `frontend/`):

```bash
npm run lint            # ESLint
npm run format:check    # Prettier
npm run test            # Vitest + Testing Library
npm run build            # tsc -b && vite build
```

When adding a frontend component or hook, add a corresponding Vitest spec (see `src/hooks/useSession.test.ts` or `src/components/ErrorBanner.test.tsx` for patterns) and check basic keyboard/aria accessibility (dialogs need `role`, focus handling, and a dismiss affordance — see `SettingsModal.tsx`).

**PR checklist:**
- [ ] Backend and/or frontend tests updated for behavior changes
- [ ] `frontend/src/types/api.d.ts` regenerated if the API contract changed
- [ ] Docs updated (`README.md`, `docs/API.md`, `docs/ROADMAP.md`) if behavior or setup steps changed
- [ ] No new accessibility regressions in touched UI (keyboard nav, `aria-*`, focus trapping in modals)

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
- Gesture→intent rules belong in ontology packs (`plugins/*/ontology.yaml`),
  not code — see the authoring guide in `docs/GESTURE_ONTOLOGY.md`. If you
  change the built-in tables in `backend/intent/ontology.py`, regenerate the
  default pack (`tests/test_ontology_pack.py` enforces they stay identical).
- Add or update tests for behavior changes. Debug pipeline behavior after the
  fact with `python tools/replay.py show <session_id>`.
