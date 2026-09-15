# SwasthyaLens

SwasthyaLens uses React/TypeScript/Vite/Tailwind and FastAPI. Phase 2 adds Supabase authentication through backend-managed HttpOnly cookies, protected navigation, and private profile/language/timezone settings. The four health destinations retain their honest empty states.

**Phase 2's confirmed-account authentication and ownership checks passed.** Real two-user API/RLS tests, profile/settings persistence, browser flows and Phase 1 regressions are verified. **Known limitation, confirmed by the owner:** the current Supabase Free project uses the built-in sender and locks the Confirm signup template, so it cannot be changed to display `{{ .Token }}`. Actual signup-email delivery and OTP-code verification remain unverified. See the [Phase 2 handoff](docs/phase-2-handoff.md) for the full results and limitation. Phase 3 is on hold by the owner's instruction.

Uploads, report storage, OCR, AI, health measurements, trend calculations, voice, notifications and exports remain unimplemented. No service-role key or browser-managed Supabase session is used. Git publishing remains with the project owner.

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

This reports service liveness, not a person's health or readiness of future integrations. The sidebar connection indicator calls this endpoint through the centralized API client and offers retry when unavailable. With Phase 2 enabled, protected content is hidden if authentication cannot be verified; a service outage is not treated as a confirmed logout.

## Configuration

Real authentication requires the Supabase development project and applied [database migration](database/README.md). Keep populated environment files local. Copy only examples for files that do not already exist:

```powershell
Set-Location P:\Projects\SwasthyAlens
if (-not (Test-Path .env.local)) { Copy-Item .env.example .env.local }
if (-not (Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
```

| Variable | Location | Meaning/default |
|---|---|---|
| `VITE_API_BASE_URL` | Root `.env.local` | Frontend-safe API address; blank/unset uses `/api`. Account calls must remain on the browser's origin. |
| `SUPABASE_URL` | `backend/.env` | Exact HTTPS project origin, copied from Supabase Connect. Public identifier, used server-side. |
| `SUPABASE_PUBLISHABLE_KEY` | `backend/.env` | Publishable application key; requests also carry the verified user's JWT. Never substitute a service-role/secret key. |
| `CSRF_SIGNING_KEY` | `backend/.env` | Server-only random secret generated locally with `secrets.token_urlsafe(32)`. Never expose in Vite or logs. |
| `APP_ORIGIN` | `backend/.env` | Exact browser origin; local value `http://127.0.0.1:5173`. |
| `CORS_ALLOWED_ORIGINS` | `backend/.env` | JSON array. With auth enabled, use exactly `["http://127.0.0.1:5173"]` locally. `[]` disables CORS. |
| `ENVIRONMENT` | `backend/.env` | `development` for loopback HTTP; `production` requires HTTPS and Secure cookies. |
| `AUTH_RATE_LIMIT_MODE` | `backend/.env` | `local` uses a bounded in-process development limiter. `edge` declares a separately configured production edge limiter; it does not provision one. |

Vite loads public configuration from the project root using `envDir`; it does not load it from `frontend/.env`. Restart Vite after changes. Vite embeds `VITE_` values into browser assets, so these values must never contain secrets.

Backend settings load `backend/.env`, regardless of the terminal working directory. Configure all three Supabase/CSRF values together. Partial or insecure configuration fails startup without exposing input values. With all three absent, the public health endpoint remains available for isolated foundation testing, but account endpoints are unavailable.

Vite dev and preview proxy `/api` to `http://127.0.0.1:8000` and remove the prefix. Use `127.0.0.1` consistently; mixing it with `localhost` breaks cookie expectations. Authentication uses credentialed requests, exact Origin checks, signed CSRF headers and JSON bodies. GET `/health` remains credential-free. Production requires a real same-origin `/api` reverse proxy and externally enforced rate limits; Vite preview is not production hosting.

The owner supplied project values in ignored `backend/.env.phase2`; implementation transfers them into the validated `backend/.env` with a locally generated CSRF secret. The staging file is not a runtime environment source. Examples contain variable names and blank values only. No Supabase value needs a `VITE_` prefix. SMTP credentials, if configured later, belong in Supabase's dashboard, not this application.

## Supabase setup and migrations

The [authentication plan](docs/phase-2-auth-plan.md) explains the approved design and initial project setup. Email confirmation remains enabled and the project uses an ES256 signing key. The implemented code-entry flow requires the Confirm signup email template to display `{{ .Token }}`. The owner confirmed that editing is locked on this Free project with the built-in sender, so this template requirement is unmet. Signup-email delivery and successful OTP-code verification must not be claimed as working. This matches [Supabase's Free/default-sender template restriction](https://supabase.com/changelog/46599-changes-to-email-template-customisation-on-free-tier). No OTP simulation, confirmation bypass, SMTP setup or alternative email flow has been added to resolve it; any future change requires separately agreed work.

For this phase the owner selected Supabase's built-in email sender for development. It is restricted to eligible project-team addresses and has a low sending quota; custom SMTP is not configured. Do not disable email confirmation or grant project access to work around mail delivery. Actual email verification remains a deferred acceptance item after a supported email flow is agreed and configured.

The reviewed migration is already applied to the current development project as `20260914164833 / auth_foundation`; do not rerun it there. For a fresh installation, apply the exact versioned SQL and run the verification scripts using the [database instructions](database/README.md). Do not create tables manually, expose the private helper schema, or use a service-role client for normal requests. The runtime needs no database password.

## Real two-user acceptance checks

The normal unit suite makes no live provider calls. The optional integration harness uses two distinct, dedicated Supabase development accounts and the running local API. It changes/restores test display names and preferences and signs out only its test sessions; use accounts containing no real health data. Do not run simultaneous acceptance runners against the same fixture accounts.

Create the two test accounts using Supabase Authentication → Users → Add user → Create new user, using distinct addresses you control and strong passwords. For these dedicated fixtures, use the dashboard's auto-confirm option so a limited development email quota does not block database isolation testing. This does not disable confirmation for public signup and does not test email ownership or delivery.

Copy `backend/tests/integration/.env.example` to ignored `backend/.env.integration`. Fill the two test email/password pairs locally, set `DISPOSABLE_TEST_ACCOUNTS_CONFIRMED=1`, and leave the optional loopback URL overrides blank unless needed. Never send passwords in chat or commit that file. With migrations applied and both servers running, run from `backend`:

```powershell
$env:RUN_SUPABASE_INTEGRATION='1'
try { .\.venv\Scripts\python.exe -m pytest tests/integration -q }
finally { Remove-Item Env:RUN_SUPABASE_INTEGRATION -ErrorAction SilentlyContinue }
```

This passed against the owner-provided accounts and tests real login/refresh, persistent profile/settings, anonymous denial, CSRF/Origin checks, private-schema exposure denial, direct Data API A/B isolation, forged owner/audit fields and replay after logout. Browser sign-in, reload/refresh, logout, cross-tab behavior and mobile navigation also passed against the production build. The two dedicated users were created with Auto Confirm for these tests only; they do not verify signup-email delivery or the OTP-code flow. Those checks remain deferred under the confirmed template limitation.

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

With Phase 2 enabled, apply the migration and sign in first before checking protected destinations. The public service-health endpoint remains available without signing in.

1. Start both services. Open `/` and confirm the sidebar says **Local API connected** and the overview says **No health data available yet.**
2. Navigate to `/reports`, `/trends`, and `/assistant`. Confirm each explicitly states the unavailable functionality. No medical measurements or generated chat responses should appear.
3. Refresh each route directly; use browser back/forward and check the active navigation state.
4. At a mobile viewport, open/close navigation, press Escape, and navigate. The menu should close, focus should remain usable, and the page should not scroll horizontally.
5. Use Tab/Enter for the skip link, navigation, buttons and links. Focus indicators should be visible.
6. Stop the backend and reload. Phase 2 should show **Unable to check your session**; restart it and choose **Try again**. A separate `/health` request failure while the session can still be verified shows **Local API unavailable** in the sidebar with **Retry connection**.
7. Visit an unknown frontend route to check the not-found page.
8. Open `/health` on port 8000 and compare the exact JSON above. POST is rejected with 405.

## Project organization

```text
frontend/
  src/
    components/       shared UI primitives and navigation
    layouts/          responsive application shell
    pages/            auth/settings pages, four empty-state destinations, not-found page
    features/auth/    session lifecycle, route protection and account controls
    features/system/  service connection indicator
    hooks/            API request lifecycle
    lib/              public configuration validation
    services/         centralized transport, health/auth/account contracts
    types/            service and account types
    styles/           design tokens and responsive styling
backend/
  app/
    api/              health/auth/profile/settings routes and verified-user dependency
    core/             configuration, cookies/CSRF, JWT/provider/session, owner repositories
    schemas/          strict request and response contracts
  tests/              isolated unit/security tests and opt-in real two-user checks
database/             versioned migration, schema assertions and rollback-only RLS tests
docs/                 audit, roadmap and phase handoff
.github/workflows/    checks only; no deployment
```

Authentication and account persistence are real Supabase integrations. Add health-domain models and further provider adapters only when their approved phase needs them; there are no fake medical integrations.

## Planning and delivery

- [Original technical audit and roadmap](docs/technical-audit.md) records the empty-workspace baseline before implementation.
- [Phase 1 handoff](docs/phase-1-handoff.md) records the historical foundation implementation and checks.
- [Phase 2 authentication plan](docs/phase-2-auth-plan.md) records the approved architecture and initial setup gate.
- [Phase 2 handoff](docs/phase-2-handoff.md) records the current implementation, evidence and remaining setup.

The owner has requested that the email-template restriction remain a documented Phase 2 limitation for now. Phase 2 is not represented as fully verified for public signup. Phase 3 remains on hold and requires the owner's explicit instruction to proceed; recording this limitation does not authorize another phase.
