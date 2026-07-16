# Deployment

How to run IntuitivePromptEngine beyond `python run.py` on your own machine.

> **The webcam constraint, up front:** the vision pipeline reads a webcam
> attached to the machine the *backend* runs on. A cloud-hosted backend has no
> camera, so a public deployment is useful for the API surface (health, config,
> replaying stored sessions/generations) — not for the live gesture loop. The
> intended production setup for the full experience is: frontend on GitHub
> Pages, backend running natively on the user's machine.

## Topologies

| Topology | Frontend | Backend | Live camera? |
|---|---|---|---|
| Native (default) | served by backend at `/` | `python run.py` | yes |
| Docker Compose | nginx `:8080` | container `:8000` | yes, with device passthrough (Linux) |
| Pages + local backend | GitHub Pages | `python run.py` on user's machine | yes |
| Pages + cloud backend | GitHub Pages | Railway / Fly.io / Render | no (API only) |

## 1. Native (single process)

```bash
pip install -r requirements.txt
cd frontend && npm ci && npm run build && cd ..
python run.py            # serves API + built frontend on :8000
```

The backend serves `frontend/dist/` at `/` when it exists.

## 2. Docker Compose

```bash
cp .env.example .env     # adjust ports/backends as needed
docker compose up --build
# frontend: http://localhost:8080   backend: http://localhost:8010
```

Webcam passthrough works on Linux only (`devices: /dev/video0`); on
Windows/macOS run the backend natively and use Docker for the frontend/Ollama
pieces, or run fully native.

## 3. GitHub Pages frontend + remote backend

The repo deploys `frontend/dist` to GitHub Pages automatically on every push
to `main` **after CI passes** (`.github/workflows/deploy.yml`).

On the Pages site, open **Settings** in the top bar and point the backend URL
at your backend (it persists in `localStorage`). For the backend itself:

1. Deploy the Docker image (or `pip install -r requirements.txt && python -m
   uvicorn backend.app.main:app`) to Railway, Fly.io, or Render.
2. Set the environment variables below — CORS must include your Pages origin.

### Required environment variables (public backend)

| Variable | Example | Why |
|---|---|---|
| `CORS_ORIGINS` | `https://<user>.github.io` | browser calls fail without it |
| `API_KEY` | a long random string | the API is otherwise open |
| `RATE_LIMIT_PER_MINUTE` | `10` | caps expensive POSTs (session/generation) per IP |
| `SESSION_TTL_S` | `900` | frees abandoned sessions sooner |
| `HF_TOKEN` | `hf_...` | optional: enables Hugging Face image generation/fallback |
| `SERVER_HOST` | `0.0.0.0` | bind on all interfaces inside the container |
| `PORT` / `SERVER_PORT` | set by platform | most PaaS inject `PORT`; `run.py` honors it |

`.env.example` documents every variable with defaults.

## Health checks

Point platform health checks at `GET /api/health` (never requires the API
key). Response schema:

```json
{
  "status": "ok",
  "version": "0.1.0",
  "uptime_s": 123.4,
  "active_sessions": 1,
  "imagegen": "pollinations",
  "prompting": "template"
}
```

## Scaling caveats

Sessions live in process memory (SQLite persists only the event log and
generated images). Run **one** backend process — multiple workers or replicas
would each hold disjoint session maps. If you need more, put a reverse proxy
in front with sticky routing and do real rate limiting there; the built-in
limiter is a single-process safety net.
