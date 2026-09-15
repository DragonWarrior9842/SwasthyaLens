# Phase 2 — Authentication and user ownership handoff

Date: 15 September 2026.

**Verified:** real authentication for the two owner-provided, confirmed development accounts; protected APIs and application routes; persistent profiles/settings; real two-user RLS isolation; refresh/revocation; browser and Phase 1 regression checks. All final executed checks passed after fixing an intermittent provider/local-clock mismatch.

**Known Phase 2 limitation, confirmed by the owner:** the current Supabase Free project uses the built-in email sender and locks the Confirm signup template. The owner could not change it to display `{{ .Token }}`, so the implemented OTP-code flow's template requirement is unmet. Confirm email remains enabled; custom SMTP is not configured. Actual signup-email delivery and successful OTP-code verification remain unverified. The two dedicated Auto Confirm users prove the tested authentication/ownership paths only. No OTP simulation or confirmation bypass has been added. Public signup is not fully accepted, and Phase 3 remains on hold by explicit owner instruction.

## 1. Authentication architecture implemented

The existing React/TypeScript/Vite/Tailwind and FastAPI stack is retained. Supabase Auth supplies identities and PostgreSQL stores only account metadata. There is no browser Supabase SDK, service-role runtime client, custom password database or second user-ID system.

```text
Browser: React + Router
  | same-origin /api; HttpOnly cookies; JSON + signed CSRF header for writes
  v
Vite proxy locally / required reverse proxy in production
  v
FastAPI BFF
  +--> Supabase Auth: signup, code verification, password login, refresh, logout
  +--> ES256 verification using fixed project JWKS
  |      issuer + audience + expiry + typed subject/session claims
  +--> Current-user dependency and owner-scoped account repository
            | publishable application key + verified user's access JWT
            v
       Supabase Data API / PostgreSQL
            +--> session_context(): current provider session, bounded lifetime
            +--> profiles: grants + owner/session RLS
            +--> user_settings: grants + owner/session RLS

auth.users.id --1:0..1--> profiles.id
auth.users.id --1:0..1--> user_settings.user_id
```

Successful login verifies the provider token, checks the provider session in the database, initializes missing account rows with conflict-ignore inserts, and issues cookies. Subsequent profile/settings requests repeat authentication and session checks, derive ownership from the verified subject, filter queries by that owner, and run under that user's database role/JWT. Row creation can recover after partial initialization without overwriting existing preferences.

## 2. Session strategy and why

- Host-only HttpOnly cookies: `sl_access`, `sl_refresh`, `sl_csrf` locally; production uses `__Host-` names and `Secure`. All have `Path=/` and `SameSite=Lax`. No `Domain` attribute.
- Access-cookie lifetime is bounded by JWT expiry and the application session limit. The refresh-cookie lifetime ends at the earlier of original `auth.sessions.created_at + 8 hours` or provider `not_after`. Refresh does not restart the eight-hour clock.
- Every protected request and RLS operation checks that the provider session still exists and belongs to the verified subject. Logout revokes the current provider session; a previously valid JWT then loses database access. Other users' sessions remain valid.
- JWT algorithm is fixed to ES256, issuer to this project's `/auth/v1`, and audience to `authenticated`. Required claims, canonical nonzero UUIDs, account email and explicit non-anonymous identity are validated. Token-controlled key URLs are rejected.
- Live testing reproduced `ImmatureSignatureError` when the signed `iat` was only 0.098 seconds ahead of the local clock. Verification now allows at most five seconds of **issued-at-only** clock difference. JWT `exp` and `nbf` retain zero leeway; database lifetime limits are unchanged. Boundary and expired/not-before regression tests pass.
- Refresh and account mutations use Web Locks to coordinate tabs and a local request queue. An eight-second bounded backend refresh replay cache handles a dropped response for local single-worker operation. Production multiworker coordination still needs deployment validation.
- Session-change broadcasts contain no identity or credentials and immediately hide prior account content. Protected subtrees are keyed by verified user ID. Before saving a form, the client checks that the account still matches the editor's account; that comparison never supplies backend authorization.
- A provider logout outage clears local cookies but returns `logout_incomplete`; the UI distinguishes this from confirmed remote revocation. Generic provider/network errors are not represented as successful logout.

HttpOnly cookies prevent JavaScript from reading provider tokens. They do not remove the need for XSS defenses, CSRF checks or authorization.

## 3. Files created during Phase 2

Paths below are relative to the repository root; earlier work in this phase may already be committed by the owner.

| Area | Files |
|---|---|
| Frontend auth | `frontend/src/features/auth/AccountMenu.tsx`, `AuthProvider.tsx`, `auth-context.ts`, `SessionGate.tsx`, `redirect.ts`, `redirect.test.ts`, `session-timing.ts`, `session-timing.test.ts` |
| Frontend account UI/contracts | `frontend/src/pages/AuthPage.tsx`, `SettingsPage.tsx`; `frontend/src/types/auth.ts`; `frontend/src/services/auth.ts`, `auth.test.ts`, `account.ts`, `account.test.ts` |
| Backend API/contracts | `backend/app/api/auth.py`, `accounts.py`, `dependencies.py`; `backend/app/schemas/accounts.py` |
| Backend security/provider/repository | `backend/app/core/accounts.py`, `auth_service.py`, `browser_security.py`, `errors.py`, `http_security.py`, `identity.py`, `provider.py`, `rate_limit.py` |
| Backend tests | `backend/tests/__init__.py`, `auth_support.py`, `test_auth.py`, `test_auth_config.py`, `test_identity.py`, `test_auth_regressions.py`, `test_provider.py`; `backend/tests/integration/__init__.py`, `test_live_ownership.py`, `.env.example` |
| Database | `database/migrations/20260914164833_auth_foundation.sql`, `database/verification/schema.sql`, `database/verification/rls-isolation.sql`, `database/README.md` |
| Documentation | `docs/phase-2-auth-plan.md`, this handoff |

Ignored local acceptance artifacts live under `.cache/qa/phase2/`: the Chrome smoke script, named-check results and screenshots with account email masked. They are not shipped application code or a new installed dependency. Populated environment files remain ignored.

## 4. Files modified during Phase 2

- Frontend routing/layout: `frontend/src/App.tsx`, `layouts/AppLayout.tsx`, `components/Sidebar.tsx`, `styles/index.css`.
- Frontend transport/configuration: `frontend/src/services/api-client.ts`, `lib/config.ts`, `lib/config.test.ts`, `vite-env.d.ts`, `frontend/vite.config.ts`, root `.env.example`.
- Backend composition/configuration: `backend/app/factory.py`, `core/config.py`, `tests/conftest.py`, `backend/.env.example`, `pyproject.toml`, `requirements.lock`, `requirements-dev.lock`.
- Project documentation and protection: `README.md`, `.gitignore`.

No report, OCR, AI, medical metric or storage implementation was added. The existing four health pages and their empty-state contracts remain intact. No Git commit or push was made by the implementation agent.

## 5. Database schema

| Table | Fields and validation | Ownership |
|---|---|---|
| `public.profiles` | `id uuid` PK; nullable trimmed `display_name` of 1–80 characters without control characters; server-controlled `created_at`, `updated_at` | `id` FK to `auth.users(id) ON DELETE CASCADE` |
| `public.user_settings` | `user_id uuid` PK; `preferred_language` restricted to `en`/`hi`, default `en`; PostgreSQL timezone catalog validation, default `UTC`; server-controlled timestamps | `user_id` FK to `auth.users(id) ON DELETE CASCADE` |

Two owner primary-key indexes, three named CHECK constraints, two timestamp triggers, eight policies and five helper/RPC functions. Only the private current-session lookup is security-definer, justified because normal users cannot read provider-owned session tables. Its search path is empty, table references are qualified, and it takes no caller-supplied identity. The public `session_context()` wrapper is security-invoker and returns only active status and Unix expiry.

The migration is already recorded on `swasthyalens-dev` as `20260914164833 / auth_foundation`. Do not rerun it there. Schema and rollback-only RLS verification passed on hosted PostgreSQL 17.6. Fresh installations must apply the entire migration once; later changes require a new reviewed migration. See [database instructions](../database/README.md).

## 6. RLS policies

Both tables enable and force RLS. Separate SELECT/INSERT/UPDATE/DELETE policies require `auth.uid()` to match the owner and the provider session to be active. UPDATE checks both existing and resulting ownership.

- Anonymous table access is denied.
- Authenticated INSERT allows owner ID and editable fields only, with RLS checking the resulting owner.
- Authenticated UPDATE allows only `display_name`, or language/timezone. Owner IDs and audit timestamps cannot be supplied on UPDATE; timestamps cannot be supplied on INSERT either.
- SELECT and DELETE require owner/session predicates. There is no application account-delete endpoint in Phase 2.
- The private helper schema is not exposed through the Data API: the live check returned HTTP 406 / `PGRST106` when it was requested explicitly.
- Backend query scoping remains in place in addition to RLS. Normal requests never use a service-role credential.

The SQL helper treats a missing `is_anonymous` claim as false, while FastAPI requires explicit false. Missing/malformed subject/session claims and mismatched provider sessions fail closed. SQL role fixtures assume claims have already been verified by PostgREST; real provider-issued JWT tests separately verified the external path.

## 7. API endpoints

Browser routes have `/api` prefixed; FastAPI routes below do not. All mutations require trusted Origin, JSON and signed CSRF. Errors contain safe `{code, message}` fields; validation output omits submitted values.

| Method / route | Input | Output | Authentication / provider and tables |
|---|---|---|---|
| GET `/health` | None | Existing `{status, service}` liveness contract | Public; no provider/database call |
| GET `/auth/csrf` | None | `{csrf_token}` plus HttpOnly nonce cookie | Public; bounded local rate limit |
| POST `/auth/signup` | Email, password 12–128 chars | 202 generic confirmation message | Public + CSRF; Supabase signup; actual email delivery pending acceptance |
| POST `/auth/resend-verification` | Email | 202 generic message | Public + CSRF; Supabase resend |
| POST `/auth/verify-email` | Email, six-digit code | `{user:{id,email}, expires_at}` + cookies | Public + CSRF; provider integration exists, but successful live OTP verification is unverified under the locked-template limitation |
| POST `/auth/login` | Email, password | Same public session response + cookies | Public + CSRF; Supabase password grant, verification and account initialization |
| POST `/auth/refresh` | `{}` | Same public session response + renewed cookies | Refresh cookie + CSRF; provider refresh and active-session check |
| POST `/auth/logout` | `{}` | Safe sign-out message, cleared cookies | CSRF; current provider session revocation; already anonymous request is idempotent |
| GET `/auth/me` | None | Public user and bounded expiry | Verified active session; session RPC |
| GET `/profile` | None | Owner profile | Verified active session; `profiles` |
| PATCH `/profile` | Optional nullable `display_name` only | Updated owner profile | Verified active session + CSRF; `profiles` |
| GET `/settings` | None | Owner preferences | Verified active session; `user_settings` |
| PATCH `/settings` | Optional `preferred_language`, `timezone`; supplied null rejected | Updated owner settings | Verified active session + CSRF; `user_settings` |

Unknown writable fields, including `id`, `user_id` and timestamps, are rejected. No endpoint accepts a caller-selected owner. Provider tokens are carried only inside the server/provider boundary and HttpOnly cookies, never in session JSON.

## 8. Frontend authentication flow

Public routes are `/auth/sign-in`, `/auth/sign-up`, `/auth/verify-email`. Dashboard, Reports, Trends, AI Assistant, settings and the application not-found route require a verified session. Internal return destinations are allowlisted. Session restoration handles refresh, unavailability and terminal authentication failure separately.

Passwords/codes are cleared from forms on submission and route changes. Pending email stays only in memory. Account settings save a real optional display name, English/Hindi preference and IANA timezone. The interface remains English; saving Hindi does not claim that translations or multilingual AI exist.

Modern secure-context Web Locks are required for authenticated browser operation. Unsupported browsers show a configuration error instead of silently removing tab coordination. Loopback HTTP is allowed for development; deployment requires HTTPS.

## 9. Environment variables added

Examples contain names and blank values. Populate files locally; never paste credentials into source or chat.

| Variable | Location | Role |
|---|---|---|
| `VITE_API_BASE_URL` | Root `.env.local` | Existing frontend-safe setting now defaults to `/api`; authenticated transport must stay same-origin |
| `SUPABASE_URL` | `backend/.env` | Public project origin used by the backend |
| `SUPABASE_PUBLISHABLE_KEY` | `backend/.env` | Public application identifier used with each user's JWT; no service-role replacement |
| `CSRF_SIGNING_KEY` | `backend/.env` | Server-only random secret; generated locally |
| `ENVIRONMENT` | `backend/.env` | `development` or `production`; enforces cookie/origin constraints |
| `APP_ORIGIN` | `backend/.env` | Exact browser origin; local `http://127.0.0.1:5173` |
| `CORS_ALLOWED_ORIGINS` | `backend/.env` | Existing setting; exact origin or empty array, never wildcard |
| `AUTH_RATE_LIMIT_MODE` | `backend/.env` | `local` for current single worker; `edge` only with separately configured production controls |
| `TEST_USER_A_EMAIL`, `TEST_USER_A_PASSWORD`, `TEST_USER_B_EMAIL`, `TEST_USER_B_PASSWORD` | `backend/.env.integration` | Dedicated live test credentials; never runtime configuration |
| `TEST_API_BASE_URL`, `TEST_APP_ORIGIN`, `DISPOSABLE_TEST_ACCOUNTS_CONFIRMED` | `backend/.env.integration` | Loopback test endpoints and explicit fixture opt-in |
| `RUN_SUPABASE_INTEGRATION` | Process environment | Must be `1` to execute the live pytest harness |

`backend/.env.phase2` is the owner's ignored setup input, not a runtime source. The actual integration file was verified at `backend/.env.integration`. `.gitignore` also protects the alternative root `backend.env.integration` spelling mentioned during setup.

## 10. Manual setup performed by the owner

The owner created/configured the development Supabase project, supplied project values locally, explicitly selected the built-in sender for development, and created two distinct dedicated auto-confirmed test users. Both credential pairs and the disposable-account opt-in were supplied in the ignored integration file. The implementation applied the reviewed migration through the connected Supabase tool and generated the server CSRF secret locally.

Production SMTP, sending-domain verification, deployment origins, reverse proxy and distributed/edge rate limits have not been configured. No new external provider, paid plan, storage bucket or medical schema is needed merely to rerun the confirmed-account acceptance tests.

The owner has now confirmed the email setup:

| Item | Confirmed status |
|---|---|
| Supabase plan / sender | Free project, built-in email sender |
| Confirm email | Enabled |
| Confirm signup template | Editing locked; cannot add `{{ .Token }}` |
| Custom SMTP | Not configured |
| Dedicated integration users | Two distinct users created with Auto Confirm for authentication/isolation testing |
| Actual signup-email delivery and OTP-code verification | Unverified; retained as a known Phase 2 limitation |

The owner requested documentation of this limitation and no fake OTP flow. No further setup action is requested in this handoff update. Keep confirmation enabled and retain the passed confirmed-account results without treating them as email-flow evidence. A future supported confirmation-link flow or SMTP/code-template configuration would require separately agreed implementation/setup and real signup-mailbox acceptance; neither has been started.

The owner-reported restriction matches [Supabase's Free/default-sender template restriction](https://supabase.com/changelog/46599-changes-to-email-template-customisation-on-free-tier). [Default sender recipient and quota limits](https://supabase.com/docs/guides/auth/auth-smtp) also remain relevant to any future development email test.

## 11. Security decisions and findings

- HMAC-signed CSRF token is bound to an HttpOnly nonce; exact Origin, JSON and a custom header are required for every write, including login/logout. Unicode/malformed signatures fail safely. No wildcard credentialed CORS.
- Requests are capped at 16 KiB. Provider responses are streamed with a 1 MB cap, bounded connection/read timeouts, no redirects and no inherited shared cookies. Provider exceptions are mapped to safe public errors.
- No user metadata, browser-supplied UUID or unverified JWT establishes authorization. Private session helpers expose no raw sessions or alternate-user lookup.
- Auth responses use `no-store`, `nosniff` and `no-referrer`. Frontend renders text and uses no unsafe HTML sinks. Production host headers/CSP still require deployment configuration.
- Known local credential values were checked against tracked source, built assets and reachable Git history. No embedded credential assignment or credential-bearing built asset was found. A short test-password substring coincided with an existing validation character alphabet; it was a non-credential constant, not a committed secret. Credential file contents were never printed.
- The latest Supabase security advisor returned **one warning: leaked-password protection is disabled**. This supersedes the earlier clean advisor snapshot. Review and enable it where supported before public release; the backend does not implement its own breached-password database. [Supabase password security](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).
- The latest performance advisor returned no findings. No RLS/table/function advisor finding was returned. Advisor results are point-in-time checks, not a security certification.

## 12. Tests executed

| Layer | Final evidence |
|---|---|
| Backend isolated suite | **133 passed**, live integration skipped by default; includes all 28 Phase 1 cases |
| Frontend Vitest | **76 passed in six files**, including Phase 1 contracts |
| Real Supabase/API suite | **1 comprehensive live integration test passed**, containing both-direction ownership, persistence, CSRF, anonymous, private-schema and revocation assertions |
| Hosted PostgreSQL | Schema assertions and complete rollback-only RLS test passed; migration history verified |
| Browser | **15 named acceptance groups passed** on installed headless Chrome against the production Vite build and real local API; 0 runtime errors and 0 direct browser Supabase requests |
| Credential boundaries | HttpOnly/Lax cookie flags; no JavaScript-readable credentials or local/session storage; ignored local files; source/build/history review |

Browser coverage: five anonymous protected-route redirects; signup/verification form constraints; real incorrect-password rejection; real sign-in and return destination; cookie boundaries; profile/preferences after reload; independent browser users; four Phase 1 empty states and navigation; health status failure/retry; 390 px mobile menu/Escape/overflow; real refresh after removing only the access cookie; simulated provider/session outage and retry; original-data restoration; cross-tab logout with the second user's session unaffected.

Successful browser signup and actual mailbox/code delivery were **not** exercised. The browser outage case intentionally injects a 503; authentication successes are genuine provider calls. Eight-hour/`not_after` boundaries use deterministic unit/SQL tests rather than an eight-hour browser wait. Test fixtures change and restore editable account fields; server audit timestamps naturally record those writes. Final database inspection found zero leftover test display-name markers.

Two existing upstream deprecation warnings remain: Starlette's HTTPX TestClient transport and AnyIO's BlockingPortal alias. They do not fail the tests. No unrelated dependency change was made merely to silence them.

## 13. Two-user isolation results

| Attempt | Result |
|---|---|
| A reads/updates A; B reads/updates B | Allowed and persisted; correct verified owner returned |
| A reads B; B reads A through Data API | Empty results |
| A updates/deletes B; B updates/deletes A | Empty results; actual other-user rows remained unchanged |
| Insert while claiming the other user's owner UUID | HTTP 403 / database permission-RLS rejection |
| Change own owner UUID or audit timestamp directly | HTTP 403 |
| Submit owner UUID to FastAPI profile/settings PATCH | HTTP 422 |
| Anonymous protected API/table access | HTTP 401 |
| Missing CSRF / foreign Origin on live PATCH | HTTP 403 |
| Select private helper schema through Data API | HTTP 406 / `PGRST106` |
| Replay A's old valid JWT after provider logout | No profile rows; session RPC reports inactive |
| B's session after A logs out | Still valid |

No test used a service-role key to simulate ordinary user access. SQL fixtures test actual database roles and roll back their generated users/sessions; real tests use the two explicitly authorized provider accounts.

## 14. Build, typecheck and lint results

Frontend `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`: passed. Final bundle: 55 modules, JS 296.21 kB / 92.71 kB gzip, CSS 24.33 kB / 6.26 kB gzip. The production build, rather than only the development renderer, was used for browser acceptance.

Backend `ruff check .`, `ruff format --check .`, strict mypy across 33 files, pytest and `pip check`: passed. Application import/startup and real Uvicorn requests passed. Mypy used an explicit local cache path after sandbox cache-write restrictions. Node 24.19.0 and Python 3.12.14 were used. GitHub Actions has not been executed remotely by this work.

Runtime additions are pinned HTTPX 0.28.1, PyJWT/crypto 2.14.0, email-validator 2.3.0 and tzdata 2026.4 with hashed lockfiles; HTTPX moved from development-only to runtime. No frontend dependency was added. Rebuild Python locks from `backend` with the pinned uv tool:

```powershell
.\.venv\Scripts\python.exe -m uv pip compile pyproject.toml --universal --generate-hashes --output-file requirements.lock
.\.venv\Scripts\python.exe -m uv pip compile pyproject.toml --extra dev --universal --generate-hashes --output-file requirements-dev.lock
```

Inspect proposed lock changes before installation; regeneration can select newer permitted transitive versions.

## 15. How to manually test Phase 2

1. Start FastAPI and Vite using the [README commands](../README.md). Use `127.0.0.1` consistently. The current local preview may already be listening on 5173 and API on 8000; do not start duplicate listeners.
2. Open `/reports` in a fresh browser context. Confirm redirection to sign-in. Sign in with a dedicated confirmed test account; expect to return to Reports.
3. Check all four destinations. Each retains its honest empty state; the sidebar shows API connectivity. No medical data is fabricated.
4. Open Account settings, change the display name, language preference and timezone, save, then reload. Values should persist. Hindi changes the saved preference only.
5. Open another browser profile/incognito context for the other account. It must see its own name/settings. For actual policy checks, run the live harness below rather than relying on the UI.
6. In browser developer tools, inspect cookie flags without copying token values. `document.cookie`, localStorage and sessionStorage should contain no provider credentials. Removing just `sl_access` and reloading should restore the session using its refresh cookie.
7. Open two tabs sharing the first account. Sign out in one; both should return to sign-in. The second account in its independent browser context should remain signed in.
8. At 390 px width, test menu open, Escape, navigation close, form usability and no horizontal scrolling. Test service outage/retry separately; protected data must not appear while session verification is unavailable.
9. Treat signup-email delivery and OTP-code verification as unverified under the confirmed limitation in section 10. Do not attempt to bypass confirmation or use Auto Confirm as evidence that the public signup flow works. Revisit email acceptance only after separately agreed work establishes a supported flow.

Run automated checks using the README. For real isolation, keep only one acceptance runner active against these two fixture accounts at a time:

```powershell
Set-Location P:\Projects\SwasthyAlens\backend
$env:RUN_SUPABASE_INTEGRATION='1'
try { .\.venv\Scripts\python.exe -m pytest tests/integration -q --tb=short }
finally { Remove-Item Env:RUN_SUPABASE_INTEGRATION -ErrorAction SilentlyContinue }
```

Never enable `--showlocals`, HTTP wire logging or credential-bearing traces. The optional harness needs the locally populated ignored file and a running API; no email is sent by it.

## 16. Known limitations

1. **Owner-confirmed limitation:** template editing is locked on the current Supabase Free project using the built-in sender; `{{ .Token }}` could not be added. Confirm email stays enabled and custom SMTP is absent. Actual signup-email delivery and OTP-code verification remain unverified. Auto-confirmed fixtures test confirmed-account authentication/ownership only; no fake OTP flow or confirmation bypass has been implemented.
2. Production SMTP and a verified sending domain are absent. The built-in sender has recipient/quota restrictions and is for development only.
3. Leaked-password protection is currently disabled according to the latest advisor. Review the project's supported settings before public release.
4. Local limiting and the refresh replay cache are single-process aids. Production needs a correctly configured same-origin HTTPS reverse proxy, trusted client-IP handling, edge/distributed limits, multiworker refresh validation, security headers and deployment checks. Setting `AUTH_RATE_LIMIT_MODE=edge` does not provision these controls.
5. Password recovery, email change, MFA, OAuth, account deletion and a session-management UI are not implemented. No browser automation against Safari/Firefox or deployed HTTPS was performed.
6. The private session check intentionally depends on the hosted `auth.sessions` contract. Migration preflight validates required columns; provider schema changes require review.
7. There are no health-data tables, storage/upload pipeline, OCR, AI, trends, voice, exports, translations or notifications yet. No claim of production health-data readiness is made.

## 17. Suggested Git commit message

```text
feat(auth): add Supabase sessions and verified user ownership
```

If the owner already committed the base Phase 2 implementation, the current acceptance/fix follow-up can instead use:

```text
fix(auth): verify live isolation and harden session edge cases
```

Review the diff and ignored environment files before staging. Publishing remains with the owner.

## 18. Phase 3 preview

**Phase 3 is on hold by the owner's explicit instruction.** Recording the known email limitation does not authorize moving to another phase. A future proposal can use the audit roadmap and verified owner/session foundation once the owner authorizes further work. Private report records and upload/storage boundaries will need a reviewed schema, validation limits and explicit external configuration; OCR, extraction and AI retain their own later integration decisions. **No Phase 3 files, buckets, tables or endpoints have been created.**
