# IntuitivePromptEngine — Frontend

Vite + React 19 + TypeScript + Tailwind v4 SPA that renders the live webcam features, primitive/intent log, Scene Graph, and generated images, and talks to the FastAPI backend over REST + a WebSocket.

The pre-migration zero-build SPA is archived at [`legacy/`](legacy) for reference; it is not built or served anymore.

## Development

Requires Node 22+. The backend (`python run.py` from the project root) should be running on `:8000` — the dev server proxies `/api` and `/ws` to it.

```bash
npm install
npm run dev              # http://localhost:5173, proxies /api and /ws to :8000
```

## Scripts

| Script                            | Purpose                                                                                          |
| --------------------------------- | ------------------------------------------------------------------------------------------------ |
| `npm run dev`                     | Vite dev server with HMR                                                                         |
| `npm run build`                   | Type-check (`tsc -b`) + production build → `dist/`                                               |
| `npm run preview`                 | Preview the production build locally                                                             |
| `npm run lint`                    | ESLint (flat config, `eslint-plugin-react-hooks`)                                                |
| `npm run format` / `format:check` | Prettier write / check                                                                           |
| `npm run test`                    | Vitest + Testing Library, jsdom environment                                                      |
| `npm run test:watch`              | Vitest in watch mode                                                                             |
| `npm run generate-types`          | Regenerate `src/types/api.d.ts` from the backend's live OpenAPI schema (backend must be running) |

## Layout

```
src/
  components/   ErrorBanner, SettingsModal, HelpModal, ...
  hooks/        useWebSocket (connection lifecycle), useSession (reducer over WS messages)
  types/        api.d.ts — generated from the backend's OpenAPI schema, do not hand-edit
```

## Notes

- The WebSocket message contract is defined in [`../docs/API.md`](../docs/API.md) and must stay in sync with the backend independently of this app's build.
- State that mirrors a changing prop (e.g. `SettingsModal`'s `open`) is synced during render (compare-and-`setState` in the render body), not in a `useEffect`, per the `react-hooks/set-state-in-effect` lint rule.
- Backend URL is configurable at runtime via the in-app Settings modal (stored in `localStorage`), so the same static build works against any backend origin — see the ⚙️ button in the topbar.
