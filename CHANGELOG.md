# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
once it reaches 1.0.

## [Unreleased]

### Added
- Repository hygiene & verification CLI (`tools/audit.py`): `scan` reports tool caches, coverage artifacts, temp/editor leftovers and suspiciously named files (report-only heuristic); `clean` deletes safe categories with dry-run default and git-tracked-file protection; `verify` mirrors every CI gate locally with `--repeat N` pytest runs for flake detection and a final hygiene check. Thin wrappers: `scripts/clean.{sh,ps1}`, `scripts/verify.{sh,ps1}`.
- Session replay CLI (`tools/replay.py`): list recorded sessions and print merged gesture/intent/scene/generation timelines from the SQLite event log (`--json`, `--speed` paced playback).
- Swappable YAML ontology packs under `plugins/` with a validated loader, `ONTOLOGY_PACK` / `intent.ontology_pack` selection, and an authoring guide in `docs/GESTURE_ONTOLOGY.md`.
- Real ComfyUI image backend: queue → poll → download against a local server, workflow templates under `backend/imagegen/workflows/`, reachability probe, and membership in the automatic fallback chain.
- Frontend test depth: SettingsModal, TopBar, SceneGraphPanel, IntentPanel, GeneratedImagePanel, PromptPanel and `lib/backendUrl` specs (26 → 46 tests) plus `npm run test:coverage`.

### Fixed
- CI: `npm ci` peer-dependency conflict (typescript pinned to 5.9.x for openapi-typescript), backend static-serving tests no longer require a locally built `frontend/dist` (`FRONTEND_DIST` override), Docker smoke test now targets compose's actual host port, and the unfixable transitive protobuf advisory (PYSEC-2026-1805, mediapipe pin) is suppressed with justification.
- Event log stored gesture/intent timestamps in the monotonic clock domain while scene/generation rows used wall-clock; converted at the storage boundary so replay timelines merge on one axis.
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
