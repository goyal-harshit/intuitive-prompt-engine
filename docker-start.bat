@echo off
setlocal EnableDelayedExpansion
title IntuitivePromptEngine (Docker)

REM ============================================================
REM  Docker launcher for IntuitivePromptEngine.
REM  - detects Docker
REM  - builds the images from scratch if they are not present yet
REM  - starts the full stack (backend API + nginx frontend)
REM  Use start.bat instead for the native, webcam-enabled dev run.
REM ============================================================

cd /d "%~dp0"

echo.
echo   =====================================================
echo    IntuitivePromptEngine  -  Docker stack launcher
echo   =====================================================
echo.

REM ---- 1. detect Docker ---------------------------------------------------
docker version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker was not found or the Docker engine is not running.
    echo         Install Docker Desktop from https://www.docker.com/products/docker-desktop/
    echo         start it, then re-run this file. ^(For a no-Docker run use start.bat.^)
    echo.
    pause
    exit /b 1
)
echo [1/3] Docker detected.

REM ---- 2. build images if missing ----------------------------------------
docker image inspect intuitive-prompt-engine-backend >nul 2>&1
if errorlevel 1 (
    echo [2/3] Backend image not present - building from scratch ^(first run, several minutes^)...
    docker compose build
    if errorlevel 1 (
        echo [ERROR] Image build failed. See the messages above.
        pause
        exit /b 1
    )
) else (
    echo [2/3] Images found - skipping build. ^(Run "docker compose build" to rebuild.^)
)

REM ---- 3. start the stack -------------------------------------------------
echo [3/3] Starting the stack...
echo.
echo   Frontend : http://localhost:8080
echo   API      : http://localhost:8000/api/health   (docs at /docs)
echo   Press CTRL+C to stop, then run: docker compose down
echo.
docker compose up

echo.
echo   Stack stopped.
pause
