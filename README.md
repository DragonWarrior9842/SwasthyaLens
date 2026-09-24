# SwasthyaLens

SwasthyaLens uses React/TypeScript/Vite/Tailwind and FastAPI. Supabase authentication runs through backend-managed HttpOnly cookies, protected navigation, and private profile/language/timezone settings. Reports support private upload, extraction and personal review. Phase 6 adds explicitly published health observations, manual weight/heart-rate entry, revision history and a dashboard backed by actual owned records. Trends and Assistant retain truthful empty states.

**Phase 2's confirmed-account authentication and ownership checks passed.** Real two-user API/RLS tests, profile/settings persistence, browser flows and Phase 1 regressions are verified. **Known limitation, confirmed by the owner:** the current Supabase Free project uses the built-in sender and locks the Confirm signup template, so it cannot be changed to display `{{ .Token }}`. Actual signup-email delivery and OTP-code verification remain unverified. See the [Phase 2 handoff](docs/phase-2-handoff.md) for that limitation and the [Phase 3 handoff](docs/phase-3-handoff.md) for report-storage verification and operational limits.

Phase 4 adds native PDF text extraction and local scanned-PDF/JPEG/PNG OCR, durable attempts, page provenance and a private extracted-text view. English and a small Hindi/English fixture set are evaluated; source files remain authoritative. See the [Phase 4 handoff](docs/phase-4-handoff.md) for setup, measured quality and development limits. Phase 5 adds deterministic parameter candidates, source inspection and append-only personal review/corrections; see the [Phase 5 handoff](docs/phase-5-handoff.md). Phase 6 adds curated observations and real history; see the [Phase 6 handoff](docs/phase-6-handoff.md). Phase 7 implements bounded synthetic report explanations, with live acceptance still pending as described below. Trend calculations, free-form assistant, voice, notifications and exports remain unimplemented. No service-role key or browser-managed Supabase session is used. Git publishing remains with the project owner.

## Prerequisites

- Node.js 24 or newer and npm 11 or newer. Node 24 is recommended; `.nvmrc` pins the tested 24.19.0 runtime.
- Python 3.12 (64-bit on Windows). Phase 4 narrows support to the tested Python 3.12 runtime because the pinned Windows OCR wheel is CPython 3.12-specific.
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

On Linux, install `libtesseract-dev`, `libleptonica-dev` and `pkg-config` before the Python dependencies. Windows uses the hash-pinned tesserocr/Tesseract wheel in the lock. Device application-control policy must permit that runtime; do not disable policy to install it. Extraction also needs the Phase 4 migrations, a private server processing key and verified English/Hindi/orientation models. Follow the [Phase 4 setup](docs/phase-4-handoff.md#setup-and-manual-test) before clicking **Extract text**.

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
| `REPORT_MAX_UPLOAD_BYTES` | `backend/.env` | Optional positive byte limit, default and maximum 5,242,880 (5 MiB). May lower the API limit; raising the database/bucket cap needs a reviewed migration. |

Vite loads public configuration from the project root using `envDir`; it does not load it from `frontend/.env`. Restart Vite after changes. Vite embeds `VITE_` values into browser assets, so these values must never contain secrets.

Backend settings load `backend/.env`, regardless of the terminal working directory. Configure all three Supabase/CSRF values together. Partial or insecure configuration fails startup without exposing input values. With all three absent, the public health endpoint remains available for isolated foundation testing, but account endpoints are unavailable.

Vite dev and preview proxy `/api` to `http://127.0.0.1:8000` and remove the prefix. Use `127.0.0.1` consistently; mixing it with `localhost` breaks cookie expectations. Authentication uses credentialed requests, exact Origin checks, signed CSRF headers and JSON bodies. GET `/health` remains credential-free. Production requires a real same-origin `/api` reverse proxy and externally enforced rate limits; Vite preview is not production hosting.

The owner supplied project values in ignored `backend/.env.phase2`; implementation transfers them into the validated `backend/.env` with a locally generated CSRF secret. The staging file is not a runtime environment source. Examples contain variable names and blank values only. No Supabase value needs a `VITE_` prefix. SMTP credentials, if configured later, belong in Supabase's dashboard, not this application.

## Supabase setup and migrations

The [authentication plan](docs/phase-2-auth-plan.md) explains the approved design and initial project setup. Email confirmation remains enabled and the project uses an ES256 signing key. The implemented code-entry flow requires the Confirm signup email template to display `{{ .Token }}`. The owner confirmed that editing is locked on this Free project with the built-in sender, so this template requirement is unmet. Signup-email delivery and successful OTP-code verification must not be claimed as working. This matches [Supabase's Free/default-sender template restriction](https://supabase.com/changelog/46599-changes-to-email-template-customisation-on-free-tier). No OTP simulation, confirmation bypass, SMTP setup or alternative email flow has been added to resolve it; any future change requires separately agreed work.

For this phase the owner selected Supabase's built-in email sender for development. It is restricted to eligible project-team addresses and has a low sending quota; custom SMTP is not configured. Do not disable email confirmation or grant project access to work around mail delivery. Actual email verification remains a deferred acceptance item after a supported email flow is agreed and configured.

The reviewed migrations are already applied to the development project as `20260914164833 / auth_foundation` and `20260915150720 / reports_foundation`; do not rerun them there. For a fresh installation, apply the exact versioned SQL in order and run the verification scripts using the [database instructions](database/README.md). The reports migration creates the private bucket and policies together. Do not create tables manually, expose the private helper schema, or use a service-role client for normal requests. The runtime needs no database password.

## Private reports

Sign in with a confirmed development account and open **Reports**. Select one PDF, JPEG or PNG (up to 5 MiB), acknowledge permission to store it, and choose **Upload report**. The server validates the filename, declared type, actual container structure and size before saving. History comes from the account's database records; **Uploaded** means stored, not medically analyzed.

Downloads are backend-mediated attachments with fresh ownership/session checks, a unique provider cache nonce, `no-store` and `nosniff`. No Storage URLs or provider tokens are returned to the browser. **Delete report** asks for confirmation. An interrupted operation can remain **Deletion pending**; refresh or retry deletion until removal is confirmed. Minimal opaque deletion manifests remain for cleanup of possible late provider writes. There is no unattended cleanup worker or production retention policy yet. Previously downloaded copies and provider edge caches cannot be retracted by deleting a database row; see the handoff's cache and retention limitations.

The optional live integration suite uploads only generated neutral files and removes them through their owners' API sessions. It tests database and Storage isolation with both dedicated accounts. Never substitute real medical reports in automated fixtures.

## Health history and manual measurements

After inspecting a report candidate against its source, confirm or correct it, then
choose **Publish to health history**. Publication is explicit and uses the latest
review revision. Supply a measurement day only if known; otherwise leave it blank.
Upload/recording times are never substituted for unknown clinical dates. Changing
or rejecting a review removes its old value from active history. An eligible new
review must be explicitly published again; earlier snapshots remain inspectable.

Open **Health history** to filter actual observations, inspect source evidence,
download the original report, or add a manual **weight (kg)** or **heart rate (bpm)**
measurement. Manual forms request an explicit UTC time. Edits retain revisions;
deletion erases the manual values. Report deletion removes its derived observations
while preserving unrelated manual measurements. Units and qualitative/comparator
values are retained exactly; no conversions or medical trend calculations run.
The dashboard uses real counts and separate recent records, with honest empty states.

Phase 6 uses the existing processing secret and development project; no new service,
credential or environment variable is required. Apply all versioned migrations in
order for a fresh installation. Manual entries have documented technical bounds and
revision/identity limits; see the handoff before using the development feature.

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

1. Start both services. Open `/` and confirm the sidebar says **Local API connected**. An account without observations shows **No health observations yet.**; populated accounts show real owned counts and records.
2. Navigate to `/reports`, `/history`, `/trends`, and `/assistant`. Reports offers private uploads and reviewed candidates; Health history shows published observations and manual entries. Trends and Assistant remain empty, without calculated trends or generated responses.
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
    pages/            auth/settings/reports pages, remaining empty destinations, not-found
    features/auth/    session lifecycle, route protection and account controls
    features/reports/ upload, extraction, review and private report history
    features/observations/ publication, provenance, revisions and owned history
    features/system/  service connection indicator
    hooks/            API request lifecycle
    lib/              public configuration validation
    services/         centralized transport, health/auth/account contracts
    types/            service and account types
    styles/           design tokens and responsive styling
backend/
  app/
    api/              health/auth/profile/settings/reports/observations/dashboard
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
- [Phase 2 handoff](docs/phase-2-handoff.md) records authentication evidence and the deferred email-flow acceptance.
- [Phase 3 plan](docs/phase-3-upload-plan.md) records the upload/lifecycle design.
- [Phase 3 handoff](docs/phase-3-handoff.md) records report storage, verification, manual checks and limits.
- [Phase 4 decision](docs/phase-4-decision.md) compares native extraction and OCR options.
- [Phase 4 handoff](docs/phase-4-handoff.md) records source text extraction, OCR quality, ownership, limits and verification.

- [Phase 5 decision](docs/phase-5-decision.md) records the deterministic candidate strategy.
- [Phase 5 handoff](docs/phase-5-handoff.md) records candidate/review architecture, evaluation, security and manual verification.
- [Phase 6 decision](docs/phase-6-decision.md) defines publication, dates and immutable observation revisions.
- [Phase 6 handoff](docs/phase-6-handoff.md) records health history, manual measurements, dashboard behavior, security and acceptance evidence.

The email-template restriction remains a documented Phase 2 limitation; public signup is not fully verified. Machine candidates never populate health history automatically or establish clinical validity.

## Phase 7 report explanations

The bounded synthetic report explanation API/UI and Gemini 3.8 Flash adapter are
implemented. Live acceptance awaits actual project RPM/TPM/RPD; the owner's setup
confirmation contained placeholders. See the [handoff](docs/phase-7-handoff.md),
[provider decision](docs/phase-7-provider-decision.md) and
[setup instructions](docs/phase-7-gemini-setup.md).

Gemini Free Tier may use submitted inputs/outputs to improve Google products,
including human review. Only generated synthetic fixtures are permitted. This is
not a production healthcare-provider decision. Billing must remain unlinked.

The server loads ignored `backend/.env.ai.gemini` with `AI_PROVIDER=gemini`,
`AI_MODEL=gemini-3.8-flash`, and locally set `AI_API_KEY`. Never put keys in `VITE_*`
variables. No SDK dependency or provider fallback was added. OpenAI retains its
separate `.env.ai` and in-memory contract tests, but all live OpenAI calls are
blocked. The historical $0.50 reservation and $5 cap remain unchanged.

Ordinary tests inject deterministic mock AI, clear live flags/credentials and
block both provider network hosts. To run the real Supabase synthetic lifecycle
with mock AI, leave `RUN_AI_INTEGRATION` unset:

```powershell
Set-Location backend
.venv/Scripts/python.exe -m tests.evaluate_explanations
```

The live Gemini command requires the process flag, `--live-gemini`, Free Tier
confirmation and numeric quota arguments documented in setup. Do not guess quota
values. No live Gemini request has occurred. The permanent Gemini counter caps
attempts at 20, including failures. No paid Gemini use is authorized. Do not reset
either ledger to retry.

The evaluator creates new synthetic PDFs, reviews/publishes through owner APIs,
enrolls only those fixtures and deletes them afterward. It accepts no arbitrary
report ID or personal file. Generation is explicit with consent; never automatic
on page load. Source corrections invalidate output; report deletion removes it.
Phase 8 trends and Phase 9 free-form assistant have not started.
