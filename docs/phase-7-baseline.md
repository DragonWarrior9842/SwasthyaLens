# Phase 7 pre-implementation baseline

Verified 17–18 September 2026 against committed Phase 6 baseline `a876e24`.
The maintained working tree was clean before verification. Read the technical audit,
Phase 1–6 handoffs and README; re-inspected application code, migrations,
observation/review provenance and authorization boundaries before implementation.

## Results

| Check | Result |
|---|---|
| Frontend ESLint | Passed, zero warnings |
| Frontend TypeScript | Passed |
| Frontend Vitest | 199 tests passed across 10 files |
| Frontend production build | Passed |
| Backend Ruff | Passed for app/tests and whole backend |
| Backend format check | Passed; 68 files checked in whole-backend check |
| Backend mypy | Passed; 65 source files |
| Backend tests including opt-in real OCR evaluation | 300 passed; 7 live tests skipped in this separate run |
| Dependency consistency | `pip check` passed |
| Live Supabase integration | 7 passed in 383.39 seconds |
| SQL verification | All 10 complete rollback-only scripts passed |
| Migration parity | All 9 applied versions match repository migrations |
| Browser regression | 53 groups passed: auth 15, reports 11, extraction 7, parameters 8, observations 12; reruns noted below |

Backend tests emitted two existing deprecation warnings from Starlette's test-client
httpx integration and AnyIO BlockingPortal alias. They did not fail checks.
Real outbound verification-email delivery remains unverified, as documented in
the earlier authentication handoff; browser form checks do not establish delivery.
The live suite used dedicated disposable test accounts and synthetic files, including
its deliberate worker-restart/recovery checks. An earlier live process was interrupted
when the task resumed; it is not counted as a pass. The complete rerun above is the
recorded result.

SQL scripts: `schema.sql`, `rls-isolation.sql`,
`reports-schema.sql`, `reports-rls-isolation.sql`,
`extraction-schema.sql`, `extraction-lifecycle.sql`,
`parameters-schema.sql`, `parameters-lifecycle.sql`,
`observations-schema.sql`, `observations-lifecycle.sql`.
Each ran against the existing development project as a complete transaction ending
in rollback; no migration or provider configuration was changed.

The Supabase security advisor still reports the previously documented
**leaked-password protection disabled** warning. No new security advisory appeared.
This is not a claim of production security/compliance readiness.
[Supabase password protection](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).

## Browser execution notes

Auth and reports passed on their first completed run. Extraction initially timed
out locating a sign-in field before any extraction assertion; the anonymous page
was then confirmed reachable and the unchanged suite passed all 7 groups.
Parameters passed all 8 groups. Observations initially failed at “two-tab: reload
first candidate”; a rerun with diagnostic logging and unchanged assertions passed
all 12 groups. No application or tracked test fix was made. The initial failures'
root causes were not established, so this is a passed baseline with observed
intermittent browser failures, not a claim of a completely clean first run.

The observation diagnostic wrapper only added sanitized HTTP status/path and error
logging. It observed the expected stale-publication 409, bounded opportunistic
report-cleanup 429s, and anonymous/post-logout 401s. All acceptance assertions still
passed. These observations do not establish the cause of the earlier failures.
The wrapper is ignored under `.cache/qa/phase7`.

The suites used local FastAPI at port 8000 and Vite production preview at port 5173,
Chrome headless, real development Supabase and synthetic fixtures. Live integration
and browser runners ran sequentially to avoid conflicting fixture-account sessions.
Existing fixture cleanup remained enabled. Screenshots/results stay in ignored
`.cache/qa/phase2` through `phase6`; run logs are in ignored `.cache/qa/phase7`.

## Reproduction

From `frontend`:

```powershell
npm run lint
npm run typecheck
npm test
npm run build
```

From `backend`, with the existing development environment and OCR models:

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:RUN_OCR_EVALUATION='1'
$env:OCR_EVALUATION_MODELS='P:/Projects/SwasthyaLens/.cache/phase4/models-best'
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m mypy app tests
.venv/Scripts/python.exe -m pytest
.venv/Scripts/python.exe -m pip check
$env:RUN_SUPABASE_INTEGRATION='1'
try { .venv/Scripts/python.exe -m pytest tests/integration -q --tb=short }
finally { Remove-Item Env:RUN_SUPABASE_INTEGRATION -ErrorAction SilentlyContinue }
```

Run all `database/verification/*.sql` files as complete rollback transactions.
With both local servers running, run these browser scripts sequentially from the
repository root:

```powershell
$env:PLAYWRIGHT_MODULE='C:/Users/aasbl/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
node .cache/qa/phase2/browser-auth-smoke.cjs
node .cache/qa/phase3/browser-reports-smoke.cjs
node .cache/qa/phase4/browser-extraction.cjs
node backend/tests/browser_parameters.cjs
node backend/tests/browser_observations.cjs
```

The ignored Phase 2–4 browser harnesses are local acceptance artifacts, not newly
committed dependencies. The tracked Phase 5–6 harnesses remain unchanged.

## Boundaries confirmed for the provider decision

- Only authenticated, owned report data can be selected. Browser credentials remain
  HttpOnly, writes retain Origin/JSON/CSRF checks, and revoked sessions fail.
- Private report storage, forced RLS and guarded processing RPCs remain in place;
  the AI must never receive database/storage access or a service-role key.
- Published observations reference immutable machine evidence and exact review
  revisions. A review change invalidates the current published snapshot until
  explicit republication.
- Report deletion removes derived extraction, candidate/review and observation data.
  AI lifecycle work must attach to these existing correction/deletion boundaries.
- Exact strings, comparators, units, report ranges and flags must be preserved.
  Calculated range status is currently always `unknown`.
- Manual history is distinct from report evidence; missing dates remain missing.
- No provider code/configuration existed before or was added during this gate.

Only the provider decision and this baseline note are intended repository changes.
No final Phase 7 handoff or completion claim is made. See the
[provider decision](phase-7-provider-decision.md) for the explicit approval boundary.
