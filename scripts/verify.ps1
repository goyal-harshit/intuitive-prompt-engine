# Thin wrapper: run every CI quality gate locally. Logic lives in tools/audit.py.
#   .\scripts\verify.ps1                  all gates once
#   .\scripts\verify.ps1 --repeat 3       repeat pytest to surface flaky tests
#   .\scripts\verify.ps1 --skip-frontend  backend gates only
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = Join-Path $root ".venv/bin/python" }
if (-not (Test-Path $py)) { $py = "python" }
& $py (Join-Path $root "tools\audit.py") verify @args
exit $LASTEXITCODE
