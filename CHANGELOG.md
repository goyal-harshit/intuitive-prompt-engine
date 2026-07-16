# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
once it reaches 1.0.

## [Unreleased]

### Added
- Formal `/api/health` schema: `status`, `version`, `uptime_s`, `active_sessions`, `imagegen`, `prompting`.
- Opt-in per-IP rate limiting for `POST /api/*` (`RATE_LIMIT_PER_MINUTE`, off by default) returning `429` + `Retry-After`.
- `docs/DEPLOYMENT.md` covering native, Docker, and GitHub Pages + remote backend topologies.
- Open-source hygiene: `SECURITY.md`, `CODE_OF_CONDUCT.md`, GitHub issue forms, and a pull request template.
- Vite + React + TypeScript + Tailwind frontend, replacing the zero-build SPA (legacy version archived under `frontend/legacy/`).
- Frontend quality gates: ESLint, Prettier, Vitest + Testing Library, `openapi-typescript` codegen for backend-synced types.
- Multi-stage Docker build for the frontend (nginx-served static build); backend image no longer bundles frontend source.
- Frontend CI job (lint, format check, type-check, build, test) gating the Docker build job.
- `docs/ROADMAP.md`-driven industry-standard upgrade: Dependabot config (pip/npm/GitHub Actions), `pip-audit` and `npm audit` CI steps, pre-commit hooks (ruff, mypy, prettier), `.editorconfig`, `scripts/dev.{sh,ps1}` convenience launcher, Codecov coverage reporting.
- GitHub Pages deploy now gated on CI success via `workflow_run`, instead of deploying on every push to `main` unconditionally.

### Changed
- Backend now serves the built frontend from `frontend/dist` (was `frontend/`) in native/single-process mode.

## [0.1.0] — Phase 1–2 (vertical slice + robustness)

### Added
- Vision → gestures → intent → scene → prompting → imagegen pipeline (FastAPI + WebSocket backend).
- Pollinations (free, keyless) and Hugging Face image generation backends; template and Ollama prompting strategies.
- SQLite-backed session storage and event log.
- pytest suite (93 tests, 86% coverage) for gesture feature math, intent fusion, orchestrator, WebSocket, imagegen, and prompting.
- Zero-build SPA frontend (superseded — see Unreleased).
