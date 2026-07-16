## What & why

<!-- What does this PR change, and what problem does it solve?
     Link the issue if one exists: Fixes #123 -->

## How it was tested

<!-- pytest / vitest / manual run — paste relevant output or describe the manual steps -->

## Checklist

- [ ] `ruff check .`, `mypy`, and `pytest` pass locally
- [ ] Frontend: `npm run lint`, `npm run format:check`, `npm test`, `npm run build` pass (if frontend touched)
- [ ] Tests added/updated for behavior changes
- [ ] `frontend/src/types/api.d.ts` regenerated if the API contract changed (`npm run generate-types`)
- [ ] Docs updated (`README.md`, `docs/API.md`, `CHANGELOG.md`) if behavior or setup changed
- [ ] No new accessibility regressions in touched UI (keyboard nav, `aria-*`, focus trapping)
