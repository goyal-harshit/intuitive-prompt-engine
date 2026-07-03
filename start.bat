@echo off
setlocal EnableDelayedExpansion
title GestureGPT

REM ============================================================
REM  GestureGPT launcher
REM  - creates the virtual environment on first run
REM  - installs / updates dependencies when needed
REM  - starts the server (auto-selects a free port)
REM ============================================================

cd /d "%~dp0"

echo.
echo   ===============================================
echo    GestureGPT  -  intent-driven creative interface
echo   ===============================================
echo.

REM ---- 1. locate a Python interpreter -------------------------------------
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY (
    python --version >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo [ERROR] Python 3.10-3.12 was not found on your PATH.
    echo         Install it from https://www.python.org/downloads/ and
    echo         tick "Add Python to PATH" during setup, then re-run this file.
    echo.
    pause
    exit /b 1
)
echo [1/3] Using Python: !PY!

REM ---- 2. virtual environment --------------------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo [2/3] Creating virtual environment ^(first run, please wait^)...
    !PY! -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create the virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [2/3] Virtual environment found.
)

set "VENV_PY=.venv\Scripts\python.exe"

REM ---- 3. dependencies ----------------------------------------------------
REM Install only when the stamp is missing or requirements.txt is newer.
set "NEED_INSTALL=1"
if exist ".venv\.deps-installed" (
    for /f %%i in ('powershell -NoProfile -Command "if((Get-Item requirements.txt).LastWriteTime -le (Get-Item .venv\.deps-installed).LastWriteTime){'0'}else{'1'}"') do set "NEED_INSTALL=%%i"
)

if "!NEED_INSTALL!"=="1" (
    echo [3/3] Installing dependencies ^(this can take a few minutes^)...
    "%VENV_PY%" -m pip install --upgrade pip >nul
    "%VENV_PY%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Dependency installation failed. See the messages above.
        pause
        exit /b 1
    )
    echo installed> ".venv\.deps-installed"
) else (
    echo [3/3] Dependencies up to date.
)

echo.
echo   Launching server... a browser tab will open automatically.
echo   Press CTRL+C in this window to stop.
echo.

"%VENV_PY%" run.py

echo.
echo   Server stopped.
pause
