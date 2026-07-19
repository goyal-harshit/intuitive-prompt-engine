# Thin wrapper: repo hygiene cleanup. All logic lives in tools/audit.py.
#   .\scripts\clean.ps1           dry-run
#   .\scripts\clean.ps1 --apply   delete caches/coverage/temp artifacts
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = Join-Path $root ".venv/bin/python" }
if (-not (Test-Path $py)) { $py = "python" }
& $py (Join-Path $root "tools\audit.py") clean @args
exit $LASTEXITCODE
