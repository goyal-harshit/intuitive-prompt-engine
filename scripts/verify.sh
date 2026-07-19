#!/usr/bin/env bash
# Thin wrapper: run every CI quality gate locally. Logic lives in tools/audit.py.
#   ./scripts/verify.sh                 all gates once
#   ./scripts/verify.sh --repeat 3      repeat pytest to surface flaky tests
#   ./scripts/verify.sh --skip-frontend backend gates only
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
py="$root/.venv/bin/python"; [ -x "$py" ] || py="$root/.venv/Scripts/python.exe"; [ -x "$py" ] || py="python3"
exec "$py" "$root/tools/audit.py" verify "$@"
