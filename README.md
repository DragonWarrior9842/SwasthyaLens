# SwasthyaLens

Phase 1 creates the local engineering foundation: a responsive React application and a FastAPI service. The four application destinations show honest empty states. The only backend capability is a real service-liveness endpoint.

No authentication, database, uploads, file storage, OCR, AI, health measurements, trend calculations, voice, notifications, or export functionality is implemented. No external service account or key is required. Git creation and publishing remain with the project owner.

## Prerequisites

- Node.js 24 or newer and npm 11 or newer. Node 24 is recommended; `.nvmrc` pins the tested 24.19.0 runtime.
- Python 3.12 is recommended. The backend declares Python 3.12–3.14 support; the Phase 1 validation uses Python 3.12.14.
- Access to the public npm and Python package registries for the initial dependency installation.

The commands below assume Windows PowerShell and a terminal starting in this project. Run the frontend and backend in separate terminals. Virtual environment activation is optional because commands use its Python executable directly.

## Install the frontend

```powershell
Set-Location P:\Projects\SwasthyAlens\frontend
npm ci
```

`package-lock.json` records the dependency graph. Direct dependencies are pinned in `package.json`; use `npm ci` for repeatable installs. There is no root npm package: run npm commands in `frontend`.

## Install the backend

```powershell
Set-Location P:\Projects\SwasthyAlens\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements-dev.lock
```

Check `python --version` first. If your default is a different version, select your Python 3.12 executable when creating the environment, or use `py -3.12 -m venv .venv` if the Windows Python launcher is installed.

The development lock includes the runtime and quality tools. The runtime-only lock is `requirements.lock`. Dependencies originate in `backend/pyproject.toml`; lockfile regeneration is documented in the phase handoff.

## Start local development

Backend terminal:

```powershell
Set-Location P:\Projects\SwasthyAlens\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend terminal:

```powershell
Set-Location P:\Projects\SwasthyAlens\frontend
npm run dev
```

Open [SwasthyaLens](http://127.0.0.1:5173). The API listens at [http://127.0.0.1:8000](http://127.0.0.1:8000), with interactive API documentation at [/docs](http://127.0.0.1:8000/docs).

Both development servers bind to loopback rather than the local network. Vite uses strict port 5173 and fails clearly if it is occupied. Stop a server with Ctrl+C in its terminal.

`GET /health` returns:

```json
{"status":"ok","service":"swasthyalens-api"}
```

This reports service liveness, not a person's health or readiness of future integrations. The sidebar connection indicator calls this endpoint through the centralized API client. An unavailable API leaves the pages usable and offers a manual retry.

## Configuration

Defaults work without creating environment files. To override them, copy only the relevant example to its matching local file; do not overwrite an existing configuration:

```powershell
Set-Location P:\Projects\SwasthyAlens
Copy-Item .env.example .env.local
Copy-Item backend\.env.example backend\.env
```

| Variable | Location | Meaning/default |
|---|---|---|
| `VITE_API_BASE_URL` | Root `.env.local` | Public API base URL; blank/unset uses `http://127.0.0.1:8000`. HTTP(S) only, without credentials/query/fragment. |
| `CORS_ALLOWED_ORIGINS` | `backend/.env` | Server-only JSON array; blank/unset permits `http://localhost:5173` and `http://127.0.0.1:5173`. `[]` disables cross-origin access. |

Vite loads public configuration from the project root using `envDir`; it does not load it from `frontend/.env`. Restart Vite after changes. Vite embeds `VITE_` values into browser assets, so these values must never contain secrets.

Backend settings load `backend/.env`, regardless of the terminal working directory. Invalid/wildcard CORS origins fail startup. Local CORS permits GET and does not permit credentials. CORS is a browser policy, not authentication.

Examples contain blank values and comments only. Local env files are ignored by Git. Future database, AI, OCR, auth and storage credentials must stay in backend-only configuration or server secret stores; no such credentials are needed or configured now.

## Quality checks

From `frontend`:

```powershell
npm run lint
npm run typecheck
npm test
npm run build
```

For watch mode, use `npm run test:watch`. Vitest runs focused API/configuration tests in Node; it does not require a browser test framework or DOM emulator.

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pip check
```

Use `ruff format .` to apply Python formatting. The backend has no separate compilation build: dependency installation, import/startup, type checks and tests validate it.

The checked-in GitHub Actions workflow runs the frontend/backend checks after the owner pushes to a GitHub repository with Actions enabled. It performs no deployment and requires no application secrets. It has not been executed remotely during this local phase.

## Preview the frontend production build

```powershell
Set-Location P:\Projects\SwasthyAlens\frontend
npm run build
npm run preview
```

Stop the frontend development server first: preview also uses port 5173 so it matches the local CORS defaults. Keep the backend running to verify connectivity. Vite preview is for local build verification, not production hosting.

## Manual Phase 1 checks

1. Start both services. Open `/` and confirm the sidebar says **Local API connected** and the overview says **No health data available yet.**
2. Navigate to `/reports`, `/trends`, and `/assistant`. Confirm each explicitly states the unavailable functionality. No medical measurements or generated chat responses should appear.
3. Refresh each route directly; use browser back/forward and check the active navigation state.
4. At a mobile viewport, open/close navigation, press Escape, and navigate. The menu should close, focus should remain usable, and the page should not scroll horizontally.
5. Use Tab/Enter for the skip link, navigation, buttons and links. Focus indicators should be visible.
6. Stop the backend, reload the page, and confirm **Local API unavailable**. Restart it and choose **Retry connection**; the indicator should recover.
7. Visit an unknown frontend route to check the not-found page.
8. Open `/health` on port 8000 and compare the exact JSON above. POST is rejected with 405.

## Project organization

```text
frontend/
  src/
    components/       shared UI primitives and navigation
    layouts/          responsive application shell
    pages/            four empty-state destinations and not-found page
    features/system/  service connection indicator
    hooks/            API request lifecycle
    lib/              public configuration validation
    services/         centralized transport and health response validation
    types/            service contract
    styles/           design tokens and responsive styling
backend/
  app/
    api/              endpoint routing
    core/             validated server configuration
    schemas/          response contract
  tests/              health/CORS/configuration tests
docs/                 audit, roadmap and phase handoff
.github/workflows/    checks only; no deployment
```

Add models, domain services, persistence or provider adapters only when a later phase needs them. There are no empty architecture packages or fake integration implementations.

## Planning and delivery

- [Original technical audit and roadmap](docs/technical-audit.md) records the empty-workspace baseline before implementation.
- [Phase 1 handoff](docs/phase-1-handoff.md) records the implemented files, dependencies, commands, verification and limitations.

After Phase 1, work stops. Phase 2 concerns real identity and user ownership, with external setup explained and confirmed before dependent integration work. It will begin only on the owner's next explicit `continue` instruction.
