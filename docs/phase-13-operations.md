# Phase 13 operations and environment contract

Prepared 2026-10-03; closure updates2026-10-10. This is a release preparation runbook, not evidence of a deployment. No production domain, isolated staging project, SMTP provider, backup service or billing upgrade has been provisioned. `swasthyalens-dev` is a shared development acceptance environment, **not production-equivalent staging**. Use synthetic records and dedicated disposable users only.

## Runtime and artifacts

| Component | Classification | Contract |
|---|---|---|
| React/Vite static build | Required | Node 24.19.x (tested 24.19.0), npm 11.19.x (tested 11.19.0); `.nvmrc`, package engines, engine-strict, lockfile |
| FastAPI BFF | Required | Python 3.12.14 / 3.12 series; runtime-only `backend/requirements.lock`; dev tooling in `requirements-dev.lock` |
| Supabase Auth/Postgres/Storage | Required | Publishable key plus verified user JWT; private reports bucket; 17 ordered migrations |
| OCR | Required for extraction | Tesseract/tesserocr, Leptonica, Pillow 12.3.0, pypdfium2 5.13.0; pinned eng/hin/osd models |
| Windows native OCR | Development verification | tesserocr 2.11.0 wheel containing Tesseract 5.5.3, exact URL and SHA-256 |
| Linux native OCR | Release target prerequisite | Install system Tesseract/Leptonica development libraries; verify native versions and licenses on the chosen image |
| AI | Optional, unavailable | Existing Gemini/OpenAI adapters retained; no release AI key is loaded; no live calls approved |
| Voice | Optional, disabled in default build | Local browser speech capabilities only; explicit build flag and per-visit opt-in; physical acceptance pending |
| Playwright/Chrome | Acceptance only | Existing local Playwright runtime and installed Chrome; `PLAYWRIGHT_MODULE` can identify the installed module |
| Supabase CLI/Docker | Migration acceptance only | CLI 2.117.0 reviewed; local Docker unavailable on this host; clean replay pending |
| Static assets | Required | Self-hosted JS/CSS; system fonts; no required third-party frontend origin; no service worker |

## Explicit environments

`development`: local dotenv allowed, HTTP loopback authentication, local rate limits, insecure-named development cookies. `test`: same local transport restrictions; fixtures supply isolated settings/providers; all ordinary pytest AI transport is blocked. Neither is suitable for public hosting.

`staging` and `production`: HTTPS application origin, exact host/origin allowlists, secure cookies, non-placeholder configured credentials, absolute OCR directory, processing secret and externally enforced rate-limit mode. Both reject integration flags even when set to `0`, injected provider transports and injected AI providers. Debug and API documentation endpoints are disabled. Stored mock results fail closed.

Use `app.release:app`: it requires staging/production and reads deployment environment variables only, never a local `.env`. The default `app.main:app` remains the local development entry point. Release configuration does not load `.env.ai` or `.env.ai.gemini`; live AI remains unavailable even if an AI key is accidentally present in the environment. Do not supply those keys at all.

## Environment inventory

Blank settings use the stated default because the settings loader ignores empty values. Unknown server settings in a dotenv file are rejected. No values from populated local files belong in documentation or build artifacts.

| Name | Component / classification | Secret? | Environments, default and absence behavior |
|---|---|---|---|
| `ENVIRONMENT` | Backend required release selector | No | All; defaults development; release entry point rejects that default |
| `APP_ORIGIN` | Backend exact browser origin | No | All; local default `http://127.0.0.1:5173`; staging/prod require chosen HTTPS origin |
| `ALLOWED_HOSTS` | Backend exact hostnames, JSON array | No | All; defaults localhost/127.0.0.1/testserver; explicit public allowlist required in staging/prod; no ports/wildcards |
| `CORS_ALLOWED_ORIGINS` | Backend JSON array | No | All; two loopback defaults; authenticated origins must be a subset of the single APP_ORIGIN; `[]` disables cross-origin reads |
| `SUPABASE_URL` | Backend required project origin | No | All; exact HTTPS origin; authentication disabled locally only if all auth settings absent; release fails |
| `SUPABASE_PUBLISHABLE_KEY` | Backend required Auth/Data API config | Public-capability key, kept server-side | All; must start `sb_publishable_`; partial/placeholder release config fails; service-role key prohibited |
| `CSRF_SIGNING_KEY` | Backend required CSRF HMAC key | Yes | All authenticated environments; at least 43 characters from 32 random bytes; absent/weak configuration fails |
| `AUTH_RATE_LIMIT_MODE` | Backend local/edge | No | Defaults local; staging/prod require edge; this setting does not install or verify a gateway |
| `REPORT_PROCESSING_KEY` | Backend processing/RPC capability | Yes | Optional locally (features unavailable without it), required in staging/prod; provision SHA-256 hash separately into the private processing configuration |
| `REPORT_MAX_UPLOAD_BYTES` | Backend upload cap | No | All; default/max 5,242,880 bytes, may only lower; invalid values fail |
| `REPORT_PROCESSING_MAX_PAGES` | Backend OCR cap | No | All; default/max 20; invalid values fail |
| `REPORT_PROCESSING_TIMEOUT_SECONDS` | Backend OCR deadline | No | All; default/max 120, minimum 5; invalid values fail |
| `OCR_TESSDATA_DIR` | Backend OCR model path | No | Optional locally; required absolute directory in staging/prod; verify files/hashes separately before release; directory syntax alone does not prove model availability |
| `VITE_API_BASE_URL` | Public frontend build | No | Default `/api`; release build rejects any different value; same-origin reverse proxy required |
| `VITE_ENABLE_VOICE` | Public frontend build | No | Default false; only literal true/false accepted; true requires explicit acceptance/enablement decision; no browser runtime override |
| `AI_PROVIDER`, `AI_MODEL` | Backend evaluation config | No | Owner-selected `openai` / `gpt-6.1-sol` passed one isolated synthetic adapter request. Normal application defaults are unchanged; see scoped result below. Not release feature enablement |
| `AI_API_KEY` | Backend evaluation config | Yes | Development evaluation only in ignored separate provider files; missing key disables provider; never VITE/public/browser |
| `RUN_AI_INTEGRATION` | Live evaluation gate | No | Must remain **absent for normal development and Phase 13 regression**. No live acceptance currently authorized; any future opt-in requires explicit authorization for that separate run. Release rejects presence; normal pytest removes it and blocks both provider hosts |
| `RUN_SUPABASE_INTEGRATION` | Explicit synthetic acceptance gate | No | Test process only, exactly `1`; absent skips live tests; release rejects presence |
| `RUN_OCR_EVALUATION` | Local native OCR test gate | No | Test only, exactly `1`; absent skips nine OCR evaluations; release rejects presence |
| `OCR_EVALUATION_MODELS` | Native OCR test asset path | No | Test only; points to verified models; missing assets cause gated checks to fail/skip as described by test |
| `DISPOSABLE_TEST_ACCOUNTS_CONFIRMED` | Local acceptance-file acknowledgement | No | Test only, exactly `1`; otherwise harness refuses; never load integration dotenv into server |
| `TEST_API_BASE_URL`, `TEST_APP_ORIGIN` | Acceptance endpoints | No | Test only; default loopback 8000/5173; live API harness rejects non-loopback endpoints |
| `TEST_USER_A_EMAIL`, `TEST_USER_B_EMAIL` | Dedicated account identifiers | Private | Test only; required and distinct; never production users or bundle contents |
| `TEST_USER_A_PASSWORD`, `TEST_USER_B_PASSWORD` | Dedicated account credentials | Yes | Test only; required from ignored `backend/.env.integration`; never printed |
| `PLAYWRIGHT_MODULE` | Browser QA tooling | No | Test only; explicit installed module path or default `playwright` |
| `QA_PYTHON` | Browser QA interpreter | No | Test only; optional; defaults to platform-specific backend virtualenv interpreter |
| `SYSTEMROOT`, `WINDIR`, `PATH`, `TEMP`, `TMP`, `LANG` | OS/runtime environment | May reveal paths | Required as applicable to platform; only these inherited by OCR child; ensure private temp volume and controlled executable path |
| `OMP_THREAD_LIMIT`, `PYTHONIOENCODING` | OCR child controls | No | Set internally to 1 and utf-8; no operator override passed through |

`backend/.env.example`, root `.env.example`, `backend/tests/integration/.env.example`, and `deploy/.env.example` are sanitized templates. The frontend build permits only the two listed `VITE_` names; unapproved public names fail without printing their values. Environment variables belonging solely to shell/tooling are not application configuration.

## AI provider status and acceptance controls

On 2026-10-03 the owner selected **OpenAI / `gpt-6.1-sol`**, reporting approximately **$5 API credit** and private `backend/.env.ai` configuration. The initial status was NOT YET LIVE-VERIFIED. A later explicit one-request authorization was executed at 23:04 Asia/Calcutta: **HTTP 200; exact model/schema/evidence/safety PASS for one synthetic Vitamin D fixture**. Usage 1,242 input / 122 output tokens; estimated standard cost $0.003704. The authorization is consumed; no further request is authorized. See the [complete report](openai-acceptance-2026-10-03.md). The private file remains ignored/untracked; never print its contents, copy its key into artifacts or commit it.

**Previous provider evaluation remains historical evidence:** Gemini used **2/20 attempts**, both HTTP **503 UNAVAILABLE**; 18 remain. Gemini live acceptance was externally blocked. Preserve its ledgers and failure records; OpenAI selection does not reset them or authorize another Gemini attempt.

That initial run was followed by separately authorized Gate C (persisted Phase 9 assistant) and Gate I (full persisted Phase 7 explanation lifecycle). **Three OpenAI requests total, all successful, zero retries/fallbacks.** Provider/model metadata migrations are applied; schema/evidence/fact validation, persistence/readback, zero-call reload, stale/correction/deletion behavior and two-user isolation passed within bounded synthetic English cases. Broader multilingual/adversarial live quality is not claimed. Production AI remains disabled; release startup rejects all integration flags and does not load a key. There is currently no supported production AI enable switch. Enabling it requires a separately reviewed implementation and release-policy decision, not setting `RUN_AI_INTEGRATION` in production.

The internal ledger is **150 cents reserved**, distinct from aggregate estimated OpenAI usage **$0.009050** and from the provider's actual invoice. Each charged reservation permanently consumes 25 cents toward a 500-cent cap, including abandoned or completed attempts; completion does not refund it. Ordinary mock-test reservations do not represent provider spend. Earlier dedicated acceptance rehearsals consumed bookkeeping reservations without provider calls. Preserve the ledger; never reset it to make the number resemble billing. SQL limit tests use rollback-only temporary state. Operators must separately monitor actual provider usage and any provider-side budget controls.

The isolated runner is `backend/scripts/accept_openai_once.py`; default execution is offline preflight and `--live` is the consumed one-request capability. Preserve `.cache/phase13/openai-acceptance-1/attempt-reserved.json`; do not reset it or rerun live without fresh authorization. Its transport permits one POST to the fixed OpenAI Responses endpoint, zero retries, a maximum 10,000-byte body and 1,536 output tokens. The conservative cost bound was $0.06 including input framing/cache-write/regional margin. Normal app startup cannot select this transport. The live gate was cleared, HTTP transport closed and process exit verified.

Acceptance controls:

- Keep `RUN_AI_INTEGRATION` unset for normal development and all Phase 13 regression. Ordinary automated tests use offline mocks; pytest blocks both provider hosts. Do not run a live evaluation command as a regression step.
- Require fresh explicit authorization for any further live acceptance test. Use only explicitly authorized synthetic fixtures; never real personal health data. In-memory adapter acceptance must not be represented as persisted enrollment/lifecycle acceptance.
- Before that run, define a very small explicit spending ceiling and bounded request/input/output limits against the reported $5 balance. The legacy `RESERVATION_CENTS=25` is bookkeeping, not verified pricing or a provider-enforced spending limit for the selected model. Funding does not authorize spending the balance.
- No automatic retries, provider fallback, model changes or billing changes. Stop on failure and record only sanitized outcome/cost metadata. A failure does not authorize another request.
- Record acceptance only within observed scope: adapter, persisted Phase 7 lifecycle and bounded Phase 9 turn passed; broader live multilingual/provider evaluation is not verified. Mock passes, funding and local configuration alone are insufficient. Production enablement remains a separate gate.

## Reproducible builds

Use the pinned runtimes before executing commands. The baseline shell had Node 26.7.0; final frontend checks deliberately use Node 24.19.0. Do not bypass engine-strict.

```powershell
# From frontend, with Node 24.19.0 and npm 11.19.0 on PATH:
npm ci
npm run lint
npm run typecheck
npm test
npm run build
# Deliver frontend/dist only; never dist-acceptance or source fixtures.
```

```powershell
# From backend, Python 3.12.14:
python -m venv .venv
./.venv/Scripts/python.exe -m pip install --require-hashes -r requirements.lock
./.venv/Scripts/python.exe -m pip check
# Linux equivalents use .venv/bin/python; first install native Tesseract/Leptonica.
# Development/test installations use requirements-dev.lock instead.
./.venv/Scripts/python.exe scripts/setup_ocr_models.py <absolute-private-model-directory>
```

The OCR setup script verifies fixed revision/hash assets and is explicit operator setup, never an upload-time download. For lock regeneration use the existing uv compile header commands for runtime and dev locks, then `python scripts/normalize_windows_ocr_lock.py`. uv universal resolution merged PyPI hashes into the same-version direct Windows wheel entry; the normalizer preserves **only that direct artifact's original URL-fragment SHA-256**. Review the resulting diff; do not broaden accepted hashes or perform blanket upgrades.

The checked-in CI pins checkout/setup actions to immutable reviewed commit IDs, installs npm 11.19.0, and runs FE lint/types/tests/build plus BE Ruff/format/mypy/tests with native OCR. It uses synthetic fixtures and no project credentials or live AI. Existing [Linux run 37219802610](https://github.com/DragonWarrior9842/SwasthyaLens/actions/runs/37219802610) for commit `b7d0c287051dc94467748cc87108321dd3614f2b` passed the frontend job and backend dependency installation/Ruff/format, but **failed mypy**; later backend OCR/tests were skipped. Initial public logs returnedHTTP403. The newly available GitHub connection retrieved37 errors in8 files; local platform guards, protocol and harness annotations have been corrected. Intermediate run38064996724 at228eac6 reduced the failure to3 Windows-platform errors. Final [run38065434615](https://github.com/DragonWarrior9842/SwasthyaLens/actions/runs/38065434615) at `e867260158143d9606765f5536242f844d9ea800` passed both jobs: backend114251994354, frontend114251994513. Mypy found no issues in113 source files; backend pytest724 passed/13 skipped/2 warnings, including OCR. Linux CI is authoritative. Local Windows mypy remained constrained by Application Control; no bypass or local PASS is claimed. Phase13 is complete for its supported scope; follow the [single Phase14 prerequisite list](../deploy/README.md#phase-14-prerequisites) before later release acceptance. Read-only GitHub metadata on2026-10-10 reports main unprotected and required status checks off. Configure and verify the intended required checks through a separately approved owner action before release. Live Supabase/browser acceptance remains an explicit operator job, not PR code supplied with production secrets.

## Local acceptance commands

Start local BFF on 8000 with `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log`. Start the built frontend on 5173 with `npm run preview -- --host 127.0.0.1 --port 5173`. Run the default build's `browser_release.cjs` first.

```powershell
# Repository root; dedicated synthetic accounts already configured locally.
if (Test-Path Env:RUN_AI_INTEGRATION) { throw 'AI integration must remain absent' }
$env:RUN_SUPABASE_INTEGRATION='1'
try {
  backend/.venv/Scripts/python.exe -X utf8 backend/scripts/run_browser_regression.py backend/tests/browser_release.cjs
} finally { Remove-Item Env:RUN_SUPABASE_INTEGRATION -ErrorAction SilentlyContinue }
```

For the established voice simulation suite only, explicitly build `VITE_ENABLE_VOICE=true` into **dist-acceptance** using `npm run build -- --outDir dist-acceptance`, then unset the flag. Preview that directory on 5173. The tracked runner with no script arguments executes all eleven established suites (140 expected groups after the Phase 7 addition; actual results are recorded in the closure report). It temporarily selects English for the two owned accounts, restores their original preferences, and signs out its sessions even on failure. Use the same explicit Supabase gate and `finally` cleanup. Never ship that acceptance artifact as the default release.

Run `pytest -q tests/integration` with the same Supabase gate separately from browsers/SQL; these suites share disposable accounts and must not overlap. Run local OCR with `RUN_OCR_EVALUATION=1` and verified `OCR_EVALUATION_MODELS`, then unset both. Execute each whole `database/verification/*.sql` script with its own existing BEGIN/ROLLBACK wrapper. Do not strip rollback statements.

## HTTPS gateway and process contract (not deployed)

- Serve static `dist` and proxy `/api` to FastAPI on the **same HTTPS origin**, stripping `/api`. Preserve the intended allowlisted Host. Do not accept a client-selected forwarding host or trust arbitrary forwarding headers.
- Install `dist/security-headers.json` as actual HTTP response headers. JSON is an artifact, not an automatic hosting configuration. CSP allows self-hosted scripts/styles/fonts/images and same-origin API calls; no unsafe-eval/unsafe-inline, external frames, objects or base URL. Permissions deny camera/geolocation/payment; local speech is self-only and remains product-disabled by default.
- Add HSTS only after actual HTTPS is working: `max-age=31536000`, no preload or includeSubDomains assumption. Backend emits it only for staging/prod requests whose ASGI scheme is HTTPS. An HTTP internal proxy hop needs the header at the trusted HTTPS edge; do not fake it with an untrusted `X-Forwarded-Proto`.
- HTML shell: revalidate/no-cache. Content-hashed static JS/CSS: long immutable cache is safe. Every sensitive API/download/export already has `Cache-Control: no-store`; disable proxy/CDN caching there. Never cache signed-in HTML/data in a service worker.
- Enforce body-size cap 5 MiB on uploads and smaller JSON routes, header/read deadlines, connection concurrency and per-IP auth throttling at the edge. BFF body deadlines are 60 seconds upload / 30 seconds JSON total read time. Application account limits remain in place.
- Initial supported release topology is **one BFF process/instance**. In-memory refresh coordination, semaphores and local limiters are not distributed guarantees. Do not scale horizontally until shared rate/refresh coordination and load tests are complete.
- Suggested server command, inside the configured private runtime: `python -m uvicorn app.release:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log --no-proxy-headers --no-server-header`. Adapt private binding only to the chosen host's network model; never expose a bypass around the gateway.
- Run without privileged OS access. OCR subprocesses have resource bounds and sanitized inherited environment, but **share the OS identity/filesystem**; they are not a security sandbox. Before accepting real PHI, configure a low-privilege worker/container boundary, private encrypted ephemeral storage, no unnecessary egress, and read-only application/models. Verify that uploads cannot access secrets through the runtime filesystem. This is an outstanding deployment gate.
- `/health` is bounded public **liveness**, not proof that Auth/DB/Storage/OCR/SMTP are ready. It does not call providers or reveal credentials/dependency versions. Use synthetic owner operations privately for readiness after rollout. Do not put tokens/health records in a public readiness endpoint.

## Migrations and operational exceptions

There are 17 immutable ordered migrations under `database/migrations`, from `20260914164833_auth_foundation` through `20261004130141_explanation_model_metadata`, including `20261003180952_assistant_openai_acceptance`. Their versions match the development database. The latest version was assigned by the migration service to the unchanged prepared `20261004070111` SQL; its local filename was aligned at application. No historical migration rewrite is authorized. Lifecycle/policy changes and constraint replacement are intentional; data migrations/retention deletes are not a rollback mechanism.

Fresh replay remains **BLOCKED**: no usable Docker/Postgres/WSL environment exists on this workstation. On an approved Docker-equipped machine create an empty temporary working directory, verify CLI help for the installed version, run Supabase CLI 2.117.0 `init` there, copy the 17 migrations into its `supabase/migrations`, and run `supabase start --workdir <that-directory>`, then `supabase db reset --local --no-seed --workdir <that-directory>`. Verify all 24 whole SQL scripts against that local database, retaining their transaction/rollback wrappers. Capture migration names/check results only. Stop the local stack after acceptance. **Never use --linked or an existing remote DB URL for this reset.** Matching current migration history and passing SQL checks do not prove fresh-chain replay. No new cloud project is authorized.

Documented provisioning beyond DDL: securely generate the processing secret and provision its SHA-256 hash into the restricted private processing configuration using the established Phase 4 procedure; configure Auth site/redirect URLs, confirmed synthetic users, sender/template settings and Storage limits. SQL owns RLS, private-bucket creation and scheduled retention jobs. Do not enroll production reports in synthetic AI evaluation.

Current hosted Postgres reports 17.6. Supabase announced 17.11/15.19 security maintenance with compatibility caveats; an operator must assess the project's supported upgrade before real-data release. No upgrade was performed. [Official release notes](https://supabase.com/changelog/postgres-15-19-17-11-breaking-changes).

## Backup, restore and rollback

**No backup schedule, paid PITR or restore exercise is claimed configured.** Before real data, approve RPO/RTO and retention, schedule encrypted restricted logical database exports appropriate to the plan, and separately back up private Storage objects and their manifest/checksums. Back up versioned code/migrations, deployment settings and secret-store recovery separately; never put credentials into a public export. Supabase database backups do not contain the Storage objects themselves. Free-plan guidance recommends operator-managed exports. Paid retention/PITR options require a separate decision; do not enable billing. [Supabase backups](https://supabase.com/docs/guides/platform/backups).

Restore into an explicitly approved isolated environment: restore roles/schema/data with correct ownership, upload private objects, restore configuration/hash capabilities securely, and verify migration versions, Auth/session revocation behavior, forced RLS, bucket privacy, checksums, source links, exact values, tombstones, stale invalidation, notifications and two-user denial. Run the complete acceptance suite with synthetic fixtures first. Do not reconnect restored evaluation enrollments or expired explanations to live generation. Measure actual recovery time and document losses against RPO before marking PASS.

Retain the previous reviewed frontend/runtime artifacts for application rollback. Roll back code only when compatible with current schema. For destructive schema/data changes, use an approved recovery plan/forward correction; never reset production or assume down migrations exist. Restore deletion state and purge old backups per documented retention so erased data is not inadvertently reintroduced. Legal/retention policy and full account deletion are outside this implementation.

## Deletion, cleanup, logs and incident handling

Report deletion fences reads and derivations before deleting the private object; confirmed absence permits metadata scrubbing. Extraction pages/runs, parameters, report observations/revisions, explanations and report-linked notifications are removed/invalidated through established cascades. Assistant derived answer facts/links disappear when source evidence changes or is deleted; the user's historical question remains until conversation deletion. Manual observation deletion removes values while retaining opaque lifecycle metadata. Deleting a conversation removes its messages. Downloaded client exports cannot be recalled.

Reports have explicit bounded cleanup; no universal background report sweeper is claimed. Interrupted extraction is fenced by durable deadlines and later reconciliation. Notifications retain at most 100/account for 30 days with hourly cleanup at minute 27; explanations retain 30 days and synthetic enrollment expires after 24 hours. Verify cron execution operationally after migration/restore. Normal parser temp directories are removed in finally cleanup; abrupt host death can leave files. After confirming no active worker, an operator must purge **only** expired `swasthyalens-extraction-*` directories in the dedicated private temp root. Never run a broad recursive cleanup of a computed system directory.

Application HTTP logs contain generated request IDs, method, application-owned route template, status and elapsed milliseconds. Unexpected exception messages/tracebacks are not logged or returned. Existing parser/provider logs use coarse categories/counts/timing, not document text or prompts. Configure host/proxy logs to omit query strings, headers, cookies, body, token-bearing URLs, raw paths with personal filenames, and medical contents. Do not enable verbose httpx/provider logging or add third-party telemetry without approval.

Monitor aggregate 401/403/429/5xx counts, latency, upload interruptions, extraction outcomes/duration, provider-unavailable counts and export failures. `/health` failure indicates process trouble only. No monitoring dashboard or external alerting service has been installed. For an incident: restrict traffic, preserve sanitized operational evidence, revoke affected sessions/credentials through an approved operator action, investigate ownership boundaries, restore only through the tested procedure, and rerun synthetic isolation acceptance before reopening. Never paste credentials or health records into incident tickets.

## Auth and email release checklist

After an actual HTTPS URL exists, set Supabase Site URL and exact allowed redirects; align APP_ORIGIN/CORS/Host and secure cookie behavior. Confirm email confirmation remains required, OTP/template behavior works, session expiration/revocation and the eight-hour BFF absolute-session boundary hold. Existing development default sender has recipient restrictions and is not production SMTP acceptance. Keep the current confirmation template limitation explicit; do not disable confirmation to bypass missing delivery. Select/configure SMTP only with user approval and verify deliverability, sender identity and abuse limits. Review the currently disabled leaked-password protection setting/plan support before release. [Supabase production checklist](https://supabase.com/docs/guides/deployment/going-into-prod), [password security](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).



## Acceptance account capacity

The manual-observation cap counts lifetime identities, including deleted tombstones, not only active values. On2026-10-10 the original disposable A had1,000 manual identities/0 active and B214/0 active; three October5 integration cases correctly received409. Do not delete tombstones, raise quotas or reset history to force a green suite. The owner supplied fresh confirmed disposable A through private `.env.integration`; preserve the old account/history. Keep all credentials out of logs/reports and never reuse acceptance accounts for production. Run shared-account integration, SQL and browser suites sequentially.

October10 development security patches: source-map-js1.2.2 and uv0.12.18. `requirements.lock` production runtime pins are unchanged; dev wheel hashes came from PyPI metadata and installation required hashes. The pinned Node archive may be held in ignored workspace cache; verify official SHASUMS and invoke npm11.19.0 explicitly if bundled/global runtimes drift. Do not disable engine-strict.
