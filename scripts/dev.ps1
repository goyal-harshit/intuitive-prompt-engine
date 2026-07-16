# Runs the backend (FastAPI, :8000) and frontend (Vite, :5173) dev servers
# together. Assumes .venv and frontend/node_modules are already set up
# (see start.bat / CONTRIBUTING.md). Ctrl+C stops both.

$root = Split-Path -Parent $PSScriptRoot

$frontend = Start-Process -FilePath "npm" `
    -ArgumentList "run", "dev" `
    -WorkingDirectory (Join-Path $root "frontend") `
    -NoNewWindow -PassThru

try {
    & (Join-Path $root ".venv\Scripts\python.exe") (Join-Path $root "run.py")
} finally {
    if (-not $frontend.HasExited) {
        Stop-Process -Id $frontend.Id -Force
    }
}
