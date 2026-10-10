# Phase 13 — staging, security hardening and release readiness

## Current closure review — updated 2026-10-10

**Not yet closed.** The [closure report](phase-13-closure.md) and [current checklist](production-readiness-checklist.md) are the authoritative current status; the dated checkpoints below preserve history. Frontend373, backend715/22 gated skips, native OCR9, Ruff/format and default production build passed. Historical Linux CI failed37 typing diagnostics in8 files; public logs initially returnedHTTP403, then the GitHub connection supplied them. Local corrections are in place with715 offline tests/24 targeted tests and9 OCR cases passing; final Linux typing verification still requires the owner-published changes. This is separate from Windows Application Control blocking local mypy, which was not bypassed. Supabase outage regression (1 failure/12 login setup errors) is retained; connectivity was restored after owner confirmation. Recovery live regression:10 passed/3 failed at manual creation409. Read-only diagnosis: A has1,000 lifetime manual identities,0 active; the owner then supplied fresh confirmed disposable A; all 13 live tests passed in 517.04s. Old tombstones/limits remain intact. All 24 SQL scripts and 147 browser groups passed (140 established + 7 default release). One initial extraction page-load timeout is retained; a clean sign-in diagnostic and explicit remaining-suite resumption passed. Final checklist: 34/49 applicable items PASS (69.4%); 1 FAIL, 5 BLOCKED, 9 PENDING and 5 NOT APPLICABLE across 54 rows. No new AI call or Phase14 work.

Phase7 Gate I and Phase9 Gate C remain bounded persisted live PASS. OpenAI3 successful authorized requests; Gemini2/20 historical503; zero automatic retries/fallbacks; AI gate unset. Internal ledger150 cents is separate from aggregate provider estimate$0.009050 and actual billing. Proposal only: isolated synthetic staging, single BFF, AI disabled, voice disabled, public email flows blocked until SMTP acceptance or an explicitly restricted Auth/UI scope. Production AI currently has no supported enable switch. Physical voice remains PENDING. Prepared [deployment instructions](../deploy/README.md) and [manual checklist](phase-13-manual-acceptance.md) do not authorize deployment.

## Historical acceptance checkpoints

Current checkpoint — **Gate I, 2026-10-04: bounded persisted Phase7 live lifecycle PASS.** Exactly one authorized OpenAI / `gpt-6.1-sol` request returnedHTTP200;1242 input/122 output tokens, estimated$0.003704. Structured/source/safety checks, persistence/evidence/model/version metadata, identical reload with0 requests, correction/stale/superseded exclusion, deletion/manual preservation and second-user isolation all passed. Total OpenAI**3**, Gemini**2/20** historical503. Cleanup passed; gate unset; process exited; authorization consumed. Internal reservations150 cents, no refund/reset. No further AI request or Phase14 work. Phase9 Gate C PASS retained. [Gate I report](openai-acceptance-2026-10-03.md#gate-i--one-live-persisted-phase-7-lifecycle-passed).

**Ready for Phase13 final closure work, not yet closed or production-ready.** Reconcile remaining full regression and operational/release gates from the readiness checklist. Broader AI scope, production enablement, deployment controls, staging/restore/SMTP/HTTPS and the Windows Application Control/mypy blocker remain separate. Fresh runner verification:100 targeted backend tests, Ruff/format PASS; prior H frontend/UI/SQL evidence retained. No application defaults, RLS, grants, migrations, billing or model selection changed in I. Earlier checkpoints below are historical.

Current checkpoint — **Gate H, 2026-10-04: full offline Phase7 lifecycle, deletion/manual preservation, two-user isolation and final provider preflight PASSED. Ready for one separately authorized Phase7 live OpenAI request; none made.** Only acceptance harnesses/tests changed. Both real application/Supabase workflows used deterministic generation, verified deleted facts independently and preserved unrelated manual data. Backend270/2 gated skips, frontend111 service tests and13 browser UI groups, six rollback SQL scripts, Ruff/format/lint/typecheck passed. Mypy remains blocked/not rerun. Migration `20261004130141_explanation_model_metadata` remains applied; security intact. Internal reservation75→125 cents, zero provider spend, no reset/refund. OpenAI2, Gemini2/20 historical503, gate unset, Phase14 unstarted. [Gate H complete evidence](openai-acceptance-2026-10-03.md#gate-h--full-offline-phase-7-lifecycle-passed). Earlier outcomes below remain historical; actual persisted Phase7 live acceptance remains pending.

Current preparation checkpoint, 2026-10-04 18:40 Asia/Calcutta: **Gate G migration PASS; full mock lifecycle FAILED; NOT READY for live Phase 7.** The unchanged prepared SQL is applied as `20261004130141_explanation_model_metadata` (service-assigned version; local filename aligned). Application-time data fingerprints preserved; forced RLS, grants and RPC security unchanged; seven rollback SQL checks passed. Backend265/2 gated skips and frontend18 passed, Ruff/format/lint/types passed. Mypy blocker remains; browser UI checks not reached.

The real application/Supabase rehearsal with deterministic generation passed reservation/persistence/reload/correction/stale/superseded checks for the first owner, then stopped at `deletion_and_manual_preservation` / `deleted_observations_http_404`: the harness expected 200, while the existing owner-scoped deleted-report API returns 404. Manual preservation and reverse-user lifecycle remain incomplete. Cleanup passed; no rerun or provider dispatch. Minimum correction is the harness expectation plus an independent owner-scoped deleted-facts absence assertion. OpenAI **2**, Gemini **2/20** historical 503s, gate unset, zero new provider cost. Internal mock reservation bookkeeping is 75 cents, with no ledger refund/reset. Phase 9 bounded PASS retained; Phase 14 unstarted. [Gate F recovery and Gate G detailed evidence](openai-acceptance-2026-10-03.md#gate-g--migration-applied-mock-lifecycle-stopped). Earlier follow-ups below retain their historical state.

Latest preparation follow-up, 2026-10-04 17:36 Asia/Calcutta: **Gate E stopped on a read-only Supabase connection timeout before migration application.** No database mutation, synthetic artifact or provider call; pending migration `20261004070111_explanation_model_metadata` remains unapplied. Deployed review, security SQL, full mock lifecycle and new regression were not reached. Phase 7 is **NOT READY** for a live request; OpenAI **2 total**, Gemini **2/20** unchanged. Gate unset; Phase 9 bounded PASS and Windows Application Control/mypy blocker preserved. [Gate E evidence and minimum recovery](openai-acceptance-2026-10-03.md#gate-e--preparation-stopped-on-database-baseline-timeout). No automatic retry or Phase 14.

Latest Phase 7 follow-up, 2026-10-04: **Gate D stopped before OpenAI** on the legacy persisted explanation model contract. Minimum local repair binds configured model to reservations/readback and rejects mismatches before dispatch; historical records remain readable. **120 targeted backend /18 frontend tests PASS**, Ruff/frontend lint/typecheck PASS. Migration `20261004070111_explanation_model_metadata` is **prepared, not applied**; full offline lifecycle and live Phase 7 acceptance remain pending. No remote synthetic fixture or provider call; OpenAI total **2**, Gemini **2/20** unchanged; gate unset. Phase 9 Gate C PASS retained. Windows Application Control/mypy remains BLOCKED without security changes. [Gate D report](openai-acceptance-2026-10-03.md#gate-d--phase-7-offline-preflight-stop). No Phase 14 or automatic live retry.

Latest follow-up, 2026-10-04: **the freshly authorized persisted Phase 9 rerun PASSED** for one synthetic English report turn. Offline harness rehearsal reached the provider boundary; a wrong-owner case stopped before it. Backend regression **692 passed, 22 gated skips**; Ruff/format PASS. Real workflow then used exactly one OpenAI / `gpt-6.1-sol` request (HTTP 200; 551 input + 54 output tokens; estimated $0.001642), persisted validated answer/evidence/metadata, reloaded identically with zero extra calls, and passed two-user isolation. Cleanup passed, process exited, gate unset. Total OpenAI calls **2**; Gemini **2/20**, both historical 503s. Full Phase 7 persisted explanation acceptance, broader release gates and the Windows Application Control mypy blocker remain open. No security policy change or normal live enablement. [Gate C record](openai-acceptance-2026-10-03.md#gate-c--authorized-persisted-phase-9-rerun-passed). All earlier dated checkpoints below remain historical; no Phase 14 work.

Follow-up 2026-10-04: the authorized persisted Phase 9 acceptance run **stopped before OpenAI**, during synthetic report preparation. No new AI request, token usage or retry occurred; total OpenAI requests remain 1, Gemini 2/20. The ownership-check harness defect was corrected offline; 212 targeted tests passed afterward. Earlier full regression for this change passed 685 backend tests (22 gated skips) and 372 frontend tests; frontend lint/types/build passed. Backend mypy is currently blocked by Windows Application Control. Additive development migration `20261003180952_assistant_openai_acceptance` adds the exact OpenAI message metadata pair; RLS/grants/RPC unchanged, two SQL verifications passed. Cleanup passed, live flag unset and no acceptance process remains. Full Phase 7/9 application acceptance and release gates remain open. [Complete Gate 2 result](openai-acceptance-2026-10-03.md#gate-2--persisted-phase-9-flow-stopped-before-openai). The earlier checkpoint below remains historical evidence.

Date: 2026-10-03. **Hardening implemented; final established browser regression IN PROGRESS. Production release remains BLOCKED by the explicitly listed operational/external gates.** One separately authorized synthetic OpenAI request subsequently passed; see section 18. No production deployment, Phase14 implementation, new Supabase project, billing change, normal-app provider switch, Git commit or push was performed.

This handoff supersedes release assumptions in earlier phase notes without changing their historical results. Preserve Phase1–12 development completion, historical Gemini failures, pending full Phase7/9 live application acceptance, and physical voice PENDING. The pre-existing uncommitted Phase12 closure update was retained.

## 1. Baseline state

Read the technical audit, README and all Phase2–12 handoffs before changes. Inspected the actual runtime, source, settings, DB/Storage policies, CI, migrations and dependencies. All required baseline suites completed before the first Phase13 edit:

| Baseline | Result |
|---|---|
| Frontend | Lint/types/build PASS; 371 tests in16 files |
| Backend | Ruff PASS;107 files formatted; mypy104 files;635 passed,22 gated skips |
| Native OCR | 9 passed |
| Real Supabase | 13 passed in1187.81s; dedicated synthetic accounts |
| SQL | All22 whole rollback verification scripts passed |
| Browser | All139 groups passed:15 auth,11 reports,7 extraction,8 parameters,12 observations,12 explanations,13 trends,13 assistant,14 multilingual,14 exports/notifications,20 voice |

No pre-existing test failure was hidden. Baseline frontend used the shell's Node26.7.0; final checks explicitly used the pinned Node24.19.0. Two upstream Starlette/httpx/anyio test-client deprecation warnings remain. A sandbox cache-write warning on an early local run was resolved by authorized cache access, not by weakening checks.

## 2. Hardening architecture

The same-origin React frontend still uses a FastAPI BFF and Supabase's user-scoped Auth/Data/Storage APIs. Added explicit secure release configuration, exact Host validation, production injection guards, bounded body reads, safe unexpected-error responses and coarse request metadata. Existing authorization, schemas, exact-value evidence validation and provider abstraction remain in place.

Frontend routes now load separately; a translated root error boundary clears failed private UI and offers explicit reload. Vite preview applies a tested CSP and emits a portable security-header artifact. Default build voice is disabled. Public configuration is allowlisted and release API origin fixed to `/api`. No new product capability or complex flag platform was introduced.

## 3. Runtime inventory

See the complete required/optional/development/test/release inventory in [operations](phase-13-operations.md#runtime-and-artifacts). Verified runtime-only Python install includes FastAPI0.141.1, Python3.12.14, PyJWT2.15.0, pypdfium2 5.13.0, Pillow12.3.0 and tesserocr2.11.0. Native Linux image verification remains a deployment prerequisite. React19.3.0, Router7.18.3, Chart.js4.5.1 and Vite8.3.0 are unchanged.

## 4. Environment model

`development`, `test`, `staging`, `production` are explicit. Development/test use local HTTP and isolated fixtures; staging/production use HTTPS, exact public hosts, secure cookies and release credential checks. `app.release:app` never loads local dotenv files and refuses a local environment. Secure startup refuses integration flags, injected transports/providers and absent/placeholder processing/auth configuration.

## 5. Environment variable inventory

The [complete inventory](phase-13-operations.md#environment-inventory) states each name, component, secrecy, allowed environments, default and absence/failure behavior. Updated root/backend examples and added `deploy/.env.example`; all use blanks or public defaults. Release templates intentionally fail until configured. No real credentials were copied into docs or artifacts.

## 6. Secret audit

The repeatable read-only `backend/scripts/audit_release_secrets.py` inspects tracked/nonignored working files, reachable Git blobs and the actual default bundle. Final scan: **665 reachable blobs, six locally configured secret values compared privately, 21 bundle files, zero actual findings**. Token/private-key/service-role-JWT patterns supplement known-value matching.

A short dedicated test password produced three substring matches inside public hexadecimal alphabets (working/history CSRF code and bundled Chart.js). Verified they are not credential literals or assignments; the scanner exempts only matches wholly inside the two canonical public alphabets and reports the exception count. No matched value was printed. Test credentials must not be reused for production. No rotation or history rewrite was performed. This finite scan and manual review are not a guarantee against all possible secret formats.

## 7. Frontend secret/bundle audit

No service-role key, backend signing/processing key, AI key or credential literal was found in `frontend/dist`. Public build configuration permits only `VITE_API_BASE_URL` and `VITE_ENABLE_VOICE`; three negative build probes reject an unapproved public name, a foreign API origin and an invalid voice flag without printing values. No application mocks, seeded users or fake medical data are imported into the product UI. Browser test speech mocks remain in test files.

## 8. Auth hardening

Retained signature/issuer/audience/expiry checks, current-session lookup, eight-hour absolute session boundary, bounded synchronized refresh, explicit logout and cross-tab private-state clearing. Ordinary flows have no service-role bypass. Final thirteen real Supabase tests passed, including two-user ownership/lifecycle checks; the final browser auth closure is pending in the table below.

## 9. Cookie policy

Staging/production use host-only `__Host-sl_access`, refresh and CSRF nonce cookies with Secure, HttpOnly, SameSite=Lax, Path=/ and no Domain. Development uses `sl_` names and local HTTP. Logout invalidates access/refresh cookies with matching attributes. Unit tests verify release cookie attributes directly because production factories now reject test transport injection. Actual deployed HTTPS/proxy behavior remains unverified.

## 10. CSRF audit

Every state-changing endpoint remains under signed nonce-bound token and exact-Origin validation, including profile/settings, reports/files/reviews/publication, observations, conversations/messages, exports and notifications. A new schema-enumerating test signs in and requires403 for every documented POST/PUT/PATCH/DELETE without CSRF. Binary uploads retain their dedicated MIME-aware guard. Client data cannot select the current owner.

## 11. CORS/origin policy

Credentialed origins must match APP_ORIGIN exactly; wildcard/path/credential-bearing origins fail validation. New ALLOWED_HOSTS accepts exact lowercase hostnames and rejects wildcard/port forms; release requires the chosen public host. Arbitrary Host and spoofed forwarded headers are tested. No production domain was invented or external redirect URL changed.

## 12. Security headers

API replies carry no-store, nosniff, no-referrer, DENY, restrictive CSP/Permissions-Policy and server-generated request IDs; file download sandbox CSP is preserved. Staging/prod HSTS is emitted only for actual ASGI HTTPS, never inferred from an untrusted forwarded header. Frontend CSP allows only real self-hosted resources and same-origin APIs; no unsafe-eval/unsafe-inline. Seven real Chrome groups passed, covering assets/API/labels/mobile/keyboard/default voice/error recovery. The emitted JSON must be installed at the real HTTPS gateway; a local preview is not a production deployment.

## 13. Storage/RLS audit

All14 public tables have RLS and FORCE RLS enabled. The reports bucket is private,5MiB,PDF/JPEG/PNG only. Private AI bookkeeping tables intentionally have forced RLS with no ordinary-user policies. The processing-key table uses revoked ACLs/restricted private definer access rather than RLS; this exception is explicit. All22 final SQL verification scripts passed. Final advisors: three intentional default-deny INFO findings, leaked-password-protection WARN, no performance findings. [Default-deny advisor explanation](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy), [password protection remediation](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).

## 14. Authorization matrix

[Security matrix](phase-13-security-matrix.md) enumerates each resource, supported action, server/direct-API ownership rule and its unit/live/SQL/browser coverage. It includes all phases' tables and the Storage/private-table exceptions. Ordinary API access uses a publishable key and verified user JWT, not service role.

## 15. IDOR tests

Real A/B tests cover foreign report upload/read/download/delete, extracted/parameter/observation data, conversation/message evidence and notifications, plus direct Data API and Storage denial. User-controlled IDs cannot change evidence owner. Live thirteen-test and SQL22 final runs passed; complete browser139 final run remains in progress. Anonymous, invalid/expired/revoked-session, malformed ID and optimistic revision tests remain in local regression.

## 16. Upload/OCR hardening

Retained MIME/magic/container/image/PDF/size/page/memory/pixel/output/attempt bounds. Added total body-read deadlines (60s upload,30s JSON), including trickled chunks; interrupted upload cleanup and semaphore release are regression-tested. Native OCR9 passed after hardening. OCR children have sanitized environment and resource bounds, but share OS identity/filesystem; private low-privilege/no-egress/ephemeral-storage isolation is a real-data deployment gate, not a completed sandbox claim.

## 17. Rate limits

The [capacity/retry inventory](phase-13-security-matrix.md#capacity-and-retry-inventory) records auth, uploads, processing, assistant/explanations, exports, notifications and pagination limits. No cap was increased. One BFF process is the supported initial release topology; external edge controls are required, and multi-instance coordination is not implemented. The `edge` setting is a validation requirement, not evidence that infrastructure exists.

## 18. AI security/fail-closed behavior

AI implementation COMPLETE; deterministic mock/synthetic acceptance COMPLETE; live acceptance **NOT COMPLETE**. Release factories reject injected mock providers, do not load an AI key, refuse live flags and reject persisted mock records. Normal pytest blocks both provider hosts. Exact-value/units/ranges/provenance, opaque evidence IDs, schema rejection, current-owner selected context, tool-free/store-false requests and English/Hindi/Hinglish adversarial tests remain intact.

Provider status update, 2026-10-03:

| Evaluation | Status |
|---|---|
| Previous provider: Gemini | **BLOCKED** by two HTTP 503 UNAVAILABLE responses. Historical attempts remain **2/20 used, 18 remaining**; retain both failures and all ledgers. |
| OpenAI / `gpt-6.1-sol`: authorized single-fixture adapter acceptance | **PASS / LIVE-VERIFIED within this scope**: 1 request, HTTP 200, exact model, schema/evidence/safety PASS, no retry. 1,242 input / 122 output tokens; estimated $0.003704. |
| Full Phase 7 / Phase 9 live application acceptance | **PENDING / NOT COMPLETE**. The successful request used the Phase 7 in-memory fact/validation pipeline, with no DB/Storage or API/UI lifecycle. Phase 9 live capability remains locked. |

The initial status-only update recorded owner-selected `AI_PROVIDER=openai` / `AI_MODEL=gpt-6.1-sol` as NOT YET LIVE-VERIFIED. Subsequent explicit authorization permitted exactly one request. Corrected only the isolated acceptance path: allow the selected model, pass it unchanged, use supported low reasoning, accept the optional reasoning envelope item, and create a one-use OpenAI transport. Retained strict educational/evidence validation and all ordinary app/assistant live locks. The key was loaded only server-side; never printed, logged or committed. Private `backend/.env.ai` remains ignored/untracked. See the [complete result and changed files](openai-acceptance-2026-10-03.md) and [acceptance controls](phase-13-operations.md#ai-provider-status-and-acceptance-controls).

The fixed synthetic fixture preserved Vitamin D `18`, `ng/mL`, `30–100` and opaque `e1`; no diagnosis, medication advice, fabricated evidence or real personal health data. A 6,540-byte request and 1,536 output-token cap stayed within the conservative $0.06 preflight bound. The durable local one-use marker is retained; Gemini remains 2/20. `RUN_AI_INTEGRATION` was removed in finally and is unset; the process exited and the transport closed. Any further live request requires fresh explicit authorization. Ordinary development/regression remains offline/mock-based with no retries, fallback or automatic provider/model changes. Production enablement remains separate.

## 19. Export/notification privacy

Exports are explicit, bounded, current-owner/current-data, in-memory JSON/CSV downloads with no server artifact/URL retention; CSV formula protection and exact strings remain covered. Notifications use generic closed copy, bounded owner-only lists and retention. Source deletion removes report-linked derived information; downloaded client files remain outside server control. Final real integration and SQL checks passed.

## 20. Voice release status

Implementation COMPLETE;48 local voice cases and20 baseline browser simulations passed. Physical Windows Chrome/Edge and optional Android Chrome testing is **PENDING**. Default release shows a typed fallback with voice disabled; only the separate synthetic acceptance artifact opts in. No microphone/audio recording or browser language-pack download was performed. See the executable physical matrix in [readiness checklist](production-readiness-checklist.md#physical-voice-matrix--all-unperformed).

## 21. Accessibility audit

Targeted review covered auth, dashboard, reports/extraction/review, history, trends, assistant, settings, exports and notifications. New Chrome checks verify one main landmark/heading, labeled controls, keyboard skip navigation and375px layouts across main routes; generic auth/export errors now have form associations. Existing extraction/review/trend/voice keyboard and Hindi/mobile groups remain part of browser139. Contrast calculations for representative tokens: body9.82:1, muted5.52:1, primary-button4.82:1, active-nav4.53:1, sidebar-label5.22:1, focus4.12:1. Inline delete confirmations are labeled groups rather than modal dialogs. No formal WCAG or screen-reader certification is claimed.

## 22. Multilingual regression

English/Hindi UI and independent English/Hindi/Hinglish assistant preference remain unchanged. Added Hindi recovery/disabled-voice text; catalog parity tests pass. Source facts, decimal strings, units and frozen saved answer languages are not translated/reformatted. Baseline14 multilingual browser groups passed; final run includes all14 and CSP checks alongside real-chart/voice checks.

## 23. Dependency/security audit

Upgraded only PyJWT2.14.0→2.15.0 and development-only brace-expansion5.0.9→5.0.12. See [advisories, exposure classification and licenses](phase-13-security-matrix.md#dependency-and-license-review). Final npm full-lock audit:0 findings/249 dependencies. Baseline PyPI audit covered42 locked entries; only PyJWT changed, and its final2.15.0 metadata reports0 advisories. Hash locks verified; direct Windows OCR hash preserved. License review is an engineering inventory, including Linux-only cysignals LGPLv3 and MPL/native obligations, not legal certification.

## 24. Runtime/version policy

Node24.19.0/npm11.19.0 and Python3.12.14 are pinned/documented consistently; engine-strict retained. Fresh npm ci/build passed. A new isolated runtime-only Python venv installed all hashed dependencies; pip check and FastAPI/JWT/Tesseract/PDFium imports passed. No broad package update was performed. Deployment Linux/native image verification remains pending.

## 25. CI

Checkout/setup actions pinned to reviewed immutable commits; exact runtime/npm setup; lint/types/tests/build and native OCR remain required source workflow steps. No live AI, real health data or production credentials are required. Live Supabase/browser tests are separately gated. Three previously ignored early browser harnesses and a portable runner are now tracked, use generated/tracked synthetic fixtures, and restore owned preferences. Hosted workflow execution and branch protection have not been verified because no push was authorized.

## 26. Migration reproducibility

Fifteen ordered immutable migration versions match the existing development database. All22 final rollback SQL scripts pass against it. **Fresh clean replay remains BLOCKED/PENDING**, because Docker/Postgres is unavailable here; historical correctness is not proof of clean bootstrap. Exact local-only replay steps and manual Auth/processing-key provisioning exceptions are in [operations](phase-13-operations.md#migrations-and-operational-exceptions). No new project, destructive reset or schema rewrite occurred.

## 27. Backup/restore plan

No backup schedule or restore drill is claimed configured. The [runbook](phase-13-operations.md#backup-restore-and-rollback) separates DB exports, private Storage objects/manifests, configuration/migrations and secret-store recovery. It requires an approved isolated restore with RLS, source/invalidation/deletion and two-user acceptance, measured RPO/RTO, and deletion-aware retention. Paid PITR is documented as a later decision only. Supabase DB backups alone do not contain Storage file bytes.

## 28. Deletion behavior

Reviewed report fencing/object removal/scrubbing, derived extraction/parameter/observation/explanation cascades, stale assistant answer invalidation, conversation/message deletion and notification removal. User-authored questions persist until conversation deletion; manual observations can leave opaque lifecycle metadata; exported client downloads cannot be recalled. No full account deletion was implemented. Interrupted worker/temp cleanup and retention limitations are documented without claiming a universal sweeper.

## 29. Logging/observability

HTTP diagnostics use random request ID, coarse method/route-template/status/time; unexpected exception bodies/tracebacks, raw paths, query strings and health content are excluded. Existing provider/parser categories remain coarse. Unit tests assert private synthetic exception/input contents do not reach response or application logs. Enable only the `swasthyalens` logger at INFO at deployment, keep provider libraries quiet and enforce proxy/host redaction. No third-party telemetry, external monitoring or on-call drill was added/claimed.

## 30. Health/startup behavior

`/health` remains cheap public liveness with no dependency/credential detail, not comprehensive readiness. Release startup validates secure configuration and blocks debug/docs/test injection; missing model files/provider readiness still require explicit private preflight. Lifespan now closes extraction resources in finally. OCR/process/HTTP deadlines bound work; graceful shutdown must allow the120s worker deadline plus termination margin. Deployment termination/host-restart drill remains pending.

## 31. Performance findings

Route splitting removes the500kB main-chunk warning. Baseline main547.76kB/gzip155.48; final entry295.05/gzip92.90 plus shared JSX/runtime chunk122.10/gzip29.75 (initial total417.15/gzip122.65). Largest optional chart chunk143.50/gzip50.33 remains lazy; CSS37.69/gzip8.96 unchanged. This is bundle evidence, not a production latency benchmark. Bounded/indexed owner/source query paths and empty performance advisor did not justify new indexes; no speculative indexes or unlimited history loading were added.

## 32. Staging plan

Existing `swasthyalens-dev` is explicitly nonisolated development acceptance with synthetic fixtures only. A separately authorized clean staging environment, secure gateway, native worker isolation and restore acceptance are required before real-data release. No new cloud project or paid host was created. Existing hosting candidates are not a deployment decision.

## 33. Deployment artifact readiness

Prepared default voice-disabled `frontend/dist`, emitted header contract, hashed Python runtime lock, exact runtime pins, `app.release:app`, blank deployment template, and operational commands. `dist-acceptance` is separate and must not be delivered as the default release. A custom domain is optional; initial provider-hosted HTTPS URL is supported once actually selected/configured. No HTTPS or production availability is claimed now.

## 34. Supabase production checklist

Before deployment: choose actual Site URL/redirects and exact app origins; verify confirmation/session/JWT settings, private bucket/RLS, processing hash, cron retention, SMTP/delivery, edge limits and two-user denial. Review current Postgres17.6 against provider17.11 security maintenance and leaked-password protection. Do not auto-upgrade, enable billing or alter URLs without the deployment decision. See the linked official guidance and [runbook](phase-13-operations.md#auth-and-email-release-checklist).

## 35. SMTP status

BLOCKED for public signup readiness: development sender recipient/template restrictions remain; real signup email/OTP acceptance has not been verified. Confirmation was not disabled. No SMTP service was purchased/configured. A closed release with pre-provisioned confirmed accounts would need an explicit scope decision, not a claim that email is ready.

## 36. Gemini blocker

Two previous explicit synthetic requests reached Gemini and returned503 UNAVAILABLE/high demand; no401/403/429/quota numbers were returned. Ledger rechecked after final SQL: **2/20 attempts used,18 preserved**, historical reserved_cents50 unchanged. RUN_AI_INTEGRATION remains absent. Gemini Free Tier may use submitted data to improve Google products; only synthetic data is approved. The evaluation provider is not a permanent healthcare production decision. Any future retry requires separate user authorization and the existing one-request/no-retry/no-switch/no-billing protocol.

## 37. Feature flags

AI stays unavailable in secure release environments with no enable flag introduced. Optional voice uses strict `VITE_ENABLE_VOICE=false` by default plus explicit per-visit consent when an approved build enables it. No runtime browser flag can turn on a server provider or bypass evidence/ownership. Product messages state unavailable/disabled truthfully.

## 38. Release blockers

The [status/severity checklist](production-readiness-checklist.md) separates code verification, external, manual/operational and non-blocking limitations. No P0 finding is identified. P1 gates include isolated staging/clean migration replay/restore, actual TLS/edge/private worker controls, managed DB maintenance decision and public-signup SMTP. AI/voice may remain unavailable/disabled; their pending acceptance must never become PASS by implication. Multi-instance operation is unsupported. Final browser verification is still pending at this checkpoint.

## 39. Full regression results

| Final verification | Result |
|---|---|
| Frontend lint / types / tests / build | PASS;371 tests/16 files; Node24.19.0/npm11.19.0 |
| Backend Ruff / format / mypy | PASS;112 files formatted;106 checked |
| Backend local tests | PASS;665 passed,22 explicitly gated skips,2 upstream warnings |
| Added local security tests | 30 additional cases within665; stored assistant mock rejection also strengthens an existing case |
| Native OCR | PASS;9 in24.93s |
| Live Supabase | PASS;13 in1544.01s (25:44); no AI calls |
| SQL | PASS;22 scripts, original transactions rolled back |
| New release-browser groups | PASS;7; default release artifact |
| Negative build configurations | PASS;3 rejected as intended |
| Established browser suite | IN PROGRESS; must close139/139 before final handoff |
| Secret scan | PASS;665 history blobs/6 private comparisons/21 bundle files;0 real findings;3 reviewed alphabet matches |
| Clean installs | PASS; frontend lock install/build and separate backend runtime-only venv/imports/pip check |

Early new-test failures were test-harness defects (Windows timer granularity, actual upload_failed enum, FastAPI nested-route enumeration, and wrong session endpoint/error-element selector); each was corrected and rerun. No application regression was waived or hidden. These runs are local/dev acceptance, not a penetration test, formal certification or production load test.

Provider-status follow-up, 2026-10-03: full offline backend regression rerun **PASS: 665 passed, 22 gated skips, two existing upstream warnings (18.85s)**. `RUN_AI_INTEGRATION`, `RUN_SUPABASE_INTEGRATION` and `RUN_OCR_EVALUATION` were absent at invocation. The initial sandbox run had two temp-directory fixture permission errors and cache warnings; rerunning with authorized temp/cache access resolved them. No provider request was made, no API credit was spent, and no secret file or provider/model code was changed. This rerun does not close the separate established-browser or live-AI acceptance gates.

Later authorized OpenAI follow-up: **675 passed, 22 gated skips, two existing upstream warnings (35.84s)** before the live request; targeted suites 165 passed; Ruff/format/mypy passed. Ten new offline cases cover the single-use boundary and sanitized failures. The subsequent **one** live request is recorded separately in section 18; it was not part of regression and does not close the established-browser, full persisted Phase 7 or Phase 9 gates.

## 40. Manual release-readiness checklist

Follow the eleven-step [developer smoke procedure](production-readiness-checklist.md#exact-developer-manual-smoke-procedure) and physical voice matrix. It covers sign-in/revocation/expiration, A/B isolation, upload/download/delete, source invalidation, AI unavailable, export/notification privacy, language, network failure, voice fallback and logout. Use only synthetic data and clean up only test-created resources.

## 41. Known limitations and changed files

Operational/manual/external gates remain open; no hidden claim of clean DB replay, restored backup, isolated staging, public SMTP, live model correctness, physical voice quality, clinical validation, formal WCAG/legal compliance, distributed coordination or full native-image scanning. See checklist for owners/actions and severity.

Created: `.python-version`; `backend/app/release.py`; release-security tests; tracked auth/report/extraction/release browser harnesses; browser runner; direct-wheel lock normalizer; private-value secret scanner; `frontend/src/components/AppErrorBoundary.tsx`; deployment env template; this handoff, operations, security matrix and readiness checklist.

Modified: server settings/factory/security middleware/upload and stored explanation/assistant validation; focused auth/report/explanation/multilingual fixtures; browser gating/portable Python/CSP checks; Python dependency/locks; frontend routes/root/voice/error associations/Hindi/environment types/Vite config; frontend package/lock/ignored acceptance build; environment examples, CI, README. Preserved the owner's prior Phase12 document change. No migration was changed. The original hardening checkpoint did not change a provider adapter; the later authorized OpenAI follow-up changed only the isolated acceptance path as listed in the [attempt report](openai-acceptance-2026-10-03.md). No commit/push was made.

Suggested commit: `chore: harden Phase 13 release configuration and verify security readiness`

## 42. Phase 14 prerequisites

Explicit user authorization; close final Phase13 regression; choose actual hosting/HTTPS URL and single-instance topology; approve isolated synthetic staging; clean migration replay and verified DB+Storage restore; private worker/temp/egress controls; deploy/verify headers, cookies, edge limits and log redaction; production Auth/SMTP and managed Postgres maintenance acceptance; hosted CI green. Keep AI and voice disabled until their separate gates are completed and enablement approved. **STOP after Phase13. Do not deploy or start Phase14.**
