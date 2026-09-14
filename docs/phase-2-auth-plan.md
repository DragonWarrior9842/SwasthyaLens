# Phase 2 — Authentication plan and external setup gate

Date: 14 September 2026. Status: **preflight complete; implementation has not started**.

This document records the intended design before implementation, as requested in the owner's Phase 2 instructions. It is not an implementation handoff or evidence that authentication works. Work pauses for the owner to configure Supabase and confirm setup. Reports, storage, OCR, health metrics, AI, trends, voice, exports and notifications remain outside this phase.

## 1. Verified starting point

Re-read the technical audit, Phase 1 handoff and README, then re-inspected application routes, transport, configuration, tests and dependencies. The original audit describes the historical empty workspace; the current code contains the Phase 1 foundation.

| Baseline check | Result on 14 September 2026 |
|---|---|
| Frontend `npm run lint` | Passed, zero warnings |
| Frontend `npm run typecheck` | Passed |
| Frontend `npm test` | 19 passed in two files |
| Backend `python -m ruff check .` | Passed |
| Backend `python -m ruff format --check .` | 12 files already formatted |
| Backend `python -m mypy` | Passed across 12 source/test files |
| Backend `python -m pytest` | 28 passed, two existing upstream deprecation warnings |

The warnings concern Starlette's HTTPX test transport and the AnyIO BlockingPortal alias. The first frontend typecheck attempt could not update generated cache files under the sandbox; the authorized retry passed. These checks used the existing Node 24.19.0 and Python 3.12.14 environments. No dependencies were installed or upgraded.

No local Supabase configuration files or relevant process environment variable names were found. Only blank `.env.example` files exist. Source has no authentication/database integration, browser credential storage or unsafe HTML rendering sinks. API transport is GET-only with credentials omitted; backend CORS is noncredentialed and GET-only. The only application endpoint is public `GET /health`.

A Git directory now exists, unlike the historical Phase 1 snapshot. `git status --short` lists the maintained files as untracked. No Git configuration, staging, commits or remotes were changed.

## 2. Intended architecture

Keep React/TypeScript/Vite/Tailwind and FastAPI. Use Supabase Auth and PostgreSQL through a backend-for-frontend boundary: React calls FastAPI, and FastAPI owns provider communication and session verification.

```text
Browser / React
  | same-origin /api requests; HttpOnly cookies sent by browser
  | JSON mutations also require an Origin check and CSRF header
  v
FastAPI
  +--> Supabase Auth: signup, email verification, password login,
  |                  refresh and current-session logout
  |
  +--> Verify JWT signature against this project's public JWKS
  |      validate algorithm, issuer, audience, expiry and UUID claims
  |      verify that the session is still active
  |      derive typed current user from verified sub
  |
  +--> Owner-scoped repository
           | publishable API key + this user's access JWT
           v
       Supabase Data API / PostgreSQL
           | grants + owner RLS + active-session checks
           +--> profiles
           +--> user_settings
```

The browser will not initialize a Supabase client or receive provider tokens in JSON. Shared HTTP connections are acceptable; mutable provider-client session state shared between users is not. The publishable key identifies the application; the individual user's JWT supplies database identity. No service-role key is needed for ordinary requests. [Supabase API keys](https://supabase.com/docs/guides/getting-started/api-keys).

Ownership never comes from request JSON, query parameters, local storage or editable user metadata. Future resource IDs select a requested record; they never establish authorization.

## 3. Session and browser security

- Separate host-only HttpOnly access/refresh cookies, `SameSite=Lax`, no `Domain` attribute. HTTPS production uses `Secure` and `__Host-` cookie names; insecure cookies are permitted only by explicit loopback development configuration.
- Use a Vite `/api` proxy locally and require a same-origin API route at production deployment. Keep the direct backend `/health` contract. Credentialed cross-origin support, if retained, uses exact configured origins, methods and headers.
- Protect every mutation, including login, signup, verification, resend, refresh and logout. Require JSON, an exact trusted Origin and a signed CSRF token bound to an HttpOnly nonce cookie. Return the CSRF token through a no-store endpoint and retain it only in frontend memory. Validate signatures and compare secrets in constant time. CORS alone is insufficient. [OWASP CSRF guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).
- Verify JWTs with a maintained cryptographic library, a fixed ES256 algorithm allowlist, configured issuer and `authenticated` audience, required expiry and valid UUID `sub`/`session_id`. Reject anonymous users. Never follow token-supplied key URLs. Bound JWKS caching and unknown-key retries. The public keys verify signatures without giving this application signing authority. [Supabase signing keys](https://supabase.com/docs/guides/auth/signing-keys).
- Explicit refresh endpoint; serialize refresh attempts within the frontend and coordinate tabs. Do not automatically replay arbitrary writes after a timeout. Test refresh concurrency, dropped responses and logout races; an in-process server lock alone is not a multiworker solution.
- Logout explicitly revokes the current provider session and clears cookies. A provider outage must not be presented as successful remote revocation. Supabase access JWTs can otherwise survive logout until expiry, so verify the session against `auth.sessions` at the API and RLS boundaries. Session existence alone does not enforce timeouts. [Supabase sessions](https://supabase.com/docs/guides/auth/sessions).
- Proposed application session limit: eight hours from the provider session's original creation, enforced by the database session predicate and API, with refresh cookies bounded to the remaining lifetime. Token refresh must not restart that clock. Also honor any provider `not_after` limit. This is an application policy to implement and test, not an existing Supabase dashboard setting or a claim of paid-plan inactivity enforcement.
- Auth/profile/settings responses use `Cache-Control: no-store`. Passwords are forwarded to Supabase and promptly cleared from forms; this application never stores or hashes them. Validation errors must omit submitted inputs, including FastAPI's default input details. Logs exclude credentials, cookies, authorization headers and provider response bodies.

HttpOnly cookies reduce JavaScript access to credentials; they do not make XSS harmless. Preserve React text rendering, avoid unsafe HTML, restrict post-login return destinations to application paths, and test credential leakage. The design deliberately moves refresh and all provider data access into FastAPI rather than following a browser-managed Supabase session example.

## 4. Minimum schema and ownership

| Table | Fields | Relationship |
|---|---|---|
| `public.profiles` | `id` UUID primary key, nullable bounded `display_name`, server-controlled `created_at` / `updated_at` | `id` references `auth.users(id)` with delete cascade |
| `public.user_settings` | `user_id` UUID primary key, `preferred_language` constrained to `en` / `hi`, validated IANA `timezone`, server-controlled timestamps | `user_id` references `auth.users(id)` with delete cascade |

Both tables share the authoritative Supabase user UUID. No second user-ID system or medical fields are needed. A settings row does not require a separate identity through the profile row. Owner primary keys already index the initial lookups.

Create missing rows idempotently using the authenticated user's database scope after successful authentication. Keep partial initialization recoverable. A timestamp trigger is justified; a privileged signup trigger is not initially necessary. Enforce valid timezone values at the database boundary as well as in FastAPI, because the Data API can be called directly.

RLS policies will separately cover SELECT, INSERT, UPDATE and DELETE. Each requires the owner to equal `auth.uid()` and a valid active session. UPDATE checks both the existing and resulting owner. Revoke anonymous/default access and limit writable columns so direct Data API clients cannot change ownership or audit timestamps. These are policies to implement, not existing controls. [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security).

A narrowly scoped session-check function is justified to reject logged-out sessions and enforce the application lifetime. Put privileged logic in an unexposed private schema, with fixed empty search path, fully qualified objects, no caller-supplied identity, minimal grants and a boolean result. A public RPC wrapper, if needed by FastAPI, must be security-invoker. Do not expose `auth.sessions` rows or grant broad access to the auth schema. Review and test this function as privileged code.

All objects, grants, policies and functions will be in versioned migration files under `database/migrations`. The owner can apply the exact reviewed migration through Supabase SQL Editor; no database password needs to enter the application. That later step requires the actual migration file and an application receipt/check, not hand-created tables. Local/remote replay instructions and policy verification will accompany the migration. No SQL should be applied at this initial setup gate.

## 5. Planned API and UI

Route names below are the intended backend contracts, not currently registered endpoints. Through the proposed proxy, the browser prefixes them with `/api`.

| Method | Route | Purpose |
|---|---|---|
| GET | `/health` | Preserve existing public service-liveness response |
| GET | `/auth/csrf` | Bootstrap a short-lived signed CSRF token; no-store |
| POST | `/auth/signup` | Validated email/password registration; generic safe result |
| POST | `/auth/verify-email` | Verify email and six-digit code; set provider session cookies |
| POST | `/auth/resend-verification` | Bounded verification resend; avoid account enumeration |
| POST | `/auth/login` | Password authentication and session cookies |
| POST | `/auth/refresh` | Rotate provider tokens; reject revoked/expired sessions |
| POST | `/auth/logout` | Revoke current session and clear cookies |
| GET | `/auth/me` | Verified minimal identity, no provider tokens |
| GET / PATCH | `/profile` | Read/update current user's allowed profile fields |
| GET / PATCH | `/settings` | Read/update current user's allowed preferences |

All mutations use the CSRF protections above; user-resource routes additionally require verified identity. Schemas reject unknown fields and ownership/audit fields. Repository calls always use that verified owner. Database errors remain server-side; public responses distinguish invalid credentials, expired session, validation, rate limiting and temporary provider unavailability without disclosing internals.

Frontend changes will add public signup/signin/verification pages, session bootstrap and protected routing, logout and minimal profile/settings editing. Session state must distinguish checking, authenticated, anonymous and unavailable; provider outages are not equivalent to logout. Preserve the four honest empty-state pages, mobile navigation, focus behavior and API status indicator.

Likely existing files affected: `frontend/src/App.tsx`, `main.tsx`, `layouts/AppLayout.tsx`, `components/Sidebar.tsx`, `services/api-client.ts`, `lib/config.ts`, `vite-env.d.ts`, `styles/index.css`, `vite.config.ts`; backend `app/factory.py`, `app/core/config.py`, manifests/locks, tests; both environment examples, README and CI. New auth features, provider/repository/security modules, schemas, migrations and tests will be added only where needed. The completed phase will have a separate `docs/phase-2-handoff.md`.

## 6. Manual setup required now

### A. Create a development project

1. Open the [Supabase dashboard](https://supabase.com/dashboard), sign in and create/select an organization you control.
2. Choose **New project**, name it `swasthyalens-dev`, and generate a strong database password. Save the password in your password manager; do not send it in chat or put it in this repository.
3. For the initial India-focused development project, choose the specific **South Asia (Mumbai), `ap-south-1`** region if available. A general APAC choice may place data in Singapore. Region is a hosting decision, not a compliance certification. [Supabase regions](https://supabase.com/docs/guides/platform/regions).
4. Use a development plan appropriate to your account; no paid add-on is required by this design. Wait for provisioning. Keep the normal Data API available, with only the intended public application schema exposed; never expose `auth` or the planned private helper schema. Do not create application tables or storage buckets yet.

### B. Configure authentication

1. Under **Authentication**, open the user signup / sign-in provider settings. Enable email/password signup and **Confirm email**. Keep anonymous sign-in and unused providers disabled. Configure a minimum password length of 12; the application will match this policy. [General configuration](https://supabase.com/docs/guides/auth/general-configuration), [password controls](https://supabase.com/docs/guides/auth/password-security).
2. Under **Authentication → URL Configuration**, set **Site URL** to `http://127.0.0.1:5173`. The proposed code-entry flow needs no callback redirect entry. Leave additional redirects empty for this new project; do not add wildcards. A future recovery/OAuth flow will define its own exact URLs before implementation. [Redirect configuration](https://supabase.com/docs/guides/auth/redirect-urls).
3. Open **JWT Signing Keys** and check that the current signing algorithm is **ES256**. If this new, unused development project is on the legacy secret, use **Migrate JWT secret**, then **Rotate keys** to activate the generated ES256 standby key. Do not copy private signing material. Do not rotate an unrelated existing production project's keys for this setup. [Signing-key configuration](https://supabase.com/docs/guides/auth/signing-keys).
4. Keep refresh-token rotation/reuse detection enabled and its default 10-second reuse interval. Keep the default one-hour access-token expiry for initial integration; application session lifetime is a separate control described above. Paid-plan session settings are not assumed. [Session configuration](https://supabase.com/docs/guides/auth/sessions).
5. Under **Authentication → Email Templates → Confirm signup**, set subject to `Confirm your SwasthyaLens email` and use this body:

```html
<h2>Confirm your email</h2>
<p>Enter this one-time code in SwasthyaLens:</p>
<p><strong>{{ .Token }}</strong></p>
<p>If you did not request this account, ignore this email.</p>
```

`{{ .Token }}` is Supabase's email-template variable, not a secret to replace by hand. This sends a code for the future verification form and avoids putting authentication tokens in application URLs. [Email templates](https://supabase.com/docs/guides/auth/auth-email-templates).

### C. Arrange verification email delivery

The built-in sender currently accepts only organization-team email addresses and has a two-message-per-hour limit; it is not production delivery. Do not add people as project administrators to bypass that restriction. [Supabase SMTP requirements](https://supabase.com/docs/guides/auth/auth-smtp).

For delivery to two normal test accounts, use an SMTP service you control. In its dashboard obtain the authenticated sender address, host, TLS port, username and password, and complete its sender/domain verification. In **Supabase Authentication → Email → SMTP Settings**, enable custom SMTP and enter those values, with sender name `SwasthyaLens`. Keep mail-provider tracking disabled for auth mail and retain provider rate limits.

SMTP credentials belong in Supabase's configuration, not SwasthyaLens `.env` or frontend code. No email vendor has been selected or purchased here. If you do not already have SMTP, report that explicitly when replying; provider-specific signup/DNS instructions require that choice. Built-in delivery can support limited development with existing eligible addresses, but Phase 2 cannot be declared complete without the required real two-user and email-flow evidence.

### D. Save only the two application connection values

1. Open the project's **Connect** dialog and copy its **Project URL**.
2. Open **Settings → API Keys** or Connect and copy the **publishable** key (the key type beginning `sb_publishable_`). Do not select a secret/service-role key. [Finding the keys](https://supabase.com/docs/guides/getting-started/api-keys).
3. In a local editor create `P:\Projects\SwasthyAlens\backend\.env.phase2` containing the following variable names, then fill them with the actual two copied values:

```dotenv
SUPABASE_URL=
SUPABASE_PUBLISHABLE_KEY=
```

This staging file is ignored by the existing `.gitignore` and is not loaded by the Phase 1 server. **Do not put these new names in `backend/.env` yet**: the existing strict Settings model rejects unknown variables and would fail startup. After setup confirmation, implementation will add validated settings and transfer these values to their final backend-only environment file without printing them.

| Value | Treatment / eventual location |
|---|---|
| `SUPABASE_URL` | Public project identifier; staged above, eventually `backend/.env` |
| `SUPABASE_PUBLISHABLE_KEY` | Public low-privilege key; staged above, eventually `backend/.env`; application keeps provider calls on the server |
| `APP_ORIGIN` | Public origin used by server validation; later `backend/.env`, local value `http://127.0.0.1:5173` |
| `CORS_ALLOWED_ORIGINS` | Existing server configuration; later explicitly matches approved origins |
| `CSRF_SIGNING_KEY` | Server-only secret generated locally during implementation; never a `VITE_` value |
| Environment/cookie mode | Validated backend configuration to add during implementation; HTTPS required in production |
| `VITE_API_BASE_URL` | Existing frontend-safe API address only; later targets same-origin `/api` |
| Database password, secret/service-role key, private JWT key | Not requested; no runtime requirement for this design |
| SMTP password | Configure only in Supabase's SMTP settings |

No Supabase value needs to be put in a `VITE_` variable. Do not share passwords, email codes or keys in chat. Confirm the file is saved, the region/signing algorithm and whether SMTP is ready. No account password or test-user identity should be committed to fixtures.

## 7. Work after confirmation and evidence required

After the owner confirms setup, verify the real project's public configuration, implement only Phase 2, and create reproducible migrations. Before requiring SQL Editor execution, provide the exact migration file and instructions; wait for its application confirmation before dependent live checks. Do not silently replace this with unrestricted runtime credentials.

Required evidence includes:

- Cryptographic negative tests: missing/malformed/expired tokens, wrong signature/algorithm/issuer/audience, invalid UUIDs, anonymous/revoked sessions, key changes and provider failures.
- Browser/session tests: signup, email confirmation, login, refresh, logout, expired session, rejected CSRF/origin, protected direct route refresh, sanitized validation/errors, mobile navigation and unchanged empty pages.
- Real Supabase two-user tests through both FastAPI and the Data API: A/A and B/B access succeeds; A/B and B/A reads, updates, deletes and forged-owner inserts fail. Check stored results rather than treating an empty update response as proof. Test direct owner/timestamp mass assignment, unauthenticated calls and replay after logout.
- Migration replay/schema/policy inspection and the privileged session helper's boundaries. Test timezones, language constraints, timestamp immutability, idempotent initialization and session lifetime.
- Re-run all Phase 1 tests, frontend lint/typecheck/tests/build, backend lint/format/mypy/tests/startup, credential scans, and browser cookie/storage checks. Remote tests use separately opted-in real test accounts; unit tests must not consume local secrets or accidentally call Supabase.

Current live-auth, migration, email and two-user results: **NOT RUN; external setup is pending**. No application source, environment example, lockfile or schema was changed during this preflight. Only this plan was added. Phase 2 is not complete, and Phase 3 has not started.
