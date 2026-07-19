#!/usr/bin/env bash
# Thin wrapper: repo hygiene cleanup. All logic lives in tools/audit.py.
#   ./scripts/clean.sh            dry-run
#   ./scripts/clean.sh --apply    delete caches/coverage/temp artifacts
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
py="$root/.venv/bin/python"; [ -x "$py" ] || py="$root/.venv/Scripts/python.exe"; [ -x "$py" ] || py="python3"
exec "$py" "$root/tools/audit.py" clean "$@"
