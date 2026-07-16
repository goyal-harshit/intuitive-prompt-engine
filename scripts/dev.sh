#!/usr/bin/env bash
# Runs the backend (FastAPI, :8000) and frontend (Vite, :5173) dev servers
# together. Assumes .venv and frontend/node_modules are already set up
# (see CONTRIBUTING.md). Ctrl+C stops both.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

npm --prefix "$root/frontend" run dev &
frontend_pid=$!
trap 'kill "$frontend_pid" 2>/dev/null || true' EXIT

"$root/.venv/bin/python" "$root/run.py"
