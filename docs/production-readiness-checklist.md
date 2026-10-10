# Production readiness checklist — Phase 13

2026-10-10. **Phase 13 closure is BLOCKED by unresolved code verification. Production release is BLOCKED; Phase 14 remains unstarted.** No deployment or additional provider request is authorized. See the [closure report](phase-13-closure.md), [security matrix](phase-13-security-matrix.md), [operations contract](phase-13-operations.md) and [prepared deployment instructions](../deploy/README.md).

Each status is exactly PASS, FAIL, BLOCKED, PENDING or NOT APPLICABLE. PASS is limited to its stated evidence. FAIL records an observed failure; BLOCKED identifies a dependency preventing acceptance; PENDING is unperformed; NOT APPLICABLE is excluded from the proposed release scope. Historical results stay in the handoff; they do not substitute for current final checks. Final checklist: **34 PASS, 1 FAIL, 5 BLOCKED, 9 PENDING, 5 NOT APPLICABLE** (54 rows). Completion is **34/49 applicable items = 69.4%**; 34/54 of all rows are PASS. This measures checklist acceptance, not implementation progress or production readiness.

| Item | Status | Evidence / remaining gate |
|---|---|---|
| Release configuration and mock separation | PASS | Staging/production fail closed, reject test flags/injected providers/stored mocks; no dotenv/key loading |
| Local session/cookie security contract | PASS | Offline signature/expiry/current-session/revocation coverage; HttpOnly, environment-correct Secure, host-only, SameSite=Lax |
| CSRF coverage | PASS | Authenticated missing-token denial enumerates every mutation; exact Origin and signed nonce binding |
| CORS/Host configuration | PASS | Explicit production allowlists; no credentialed wildcard or spoofed forwarding trust |
| Local frontend headers and failure recovery | PASS | Default release7 groups passed: actual CSP/headers/no local HSTS, failures/recovery and logout |
| Deployed HTTPS/HSTS/cookies/edge limits | PENDING | No deployed URL; localhost checks cannot establish this |
| Final owned-resource and Storage isolation | PASS | All 13 real A/B integration tests and 24 whole SQL verification scripts passed; private Storage and owner-scoped RPC/Data API checks |
| Upload/OCR hardening | PASS | MIME/magic/size/page/pixel/time/attempt limits, adversarial tests and native OCR9 |
| Source facts, correction and deletion contracts | PASS | Offline deterministic checks plus preserved bounded Phase7/9 live acceptance |
| Export/notification privacy contract | PASS | Current-data owner exports, no-store/nonpersistent; generic notices, idempotency and bounded retention |
| Application log privacy | PASS | Coarse categories/IDs/routes/timing; sanitized failure tests; actual host/proxy logs separately pending |
| Environment and secret scan | PASS | 736 reachable blobs, six private known values, 21 bundle files, zero findings and zero alphabet matches; .env.ai ignored/untracked. Earlier false-positive review preserved in closure history |
| Disposable test credential hygiene | PENDING | Owner replaced account A privately; original account preserved. Strong unique credentials for both disposable accounts remain an operator hygiene check; credentials never displayed |
| Frontend final regression | PASS | Lint/types/build;373 tests/16 files; Node24.19.0/npm11.19.0 |
| Backend final offline regression | PASS | 715 passed,22 gated skips; two existing upstream deprecation warnings |
| Backend Ruff/format | PASS | Ruff clean;123 files formatted |
| Native OCR final acceptance | PASS | Nine exact cases with hash-verified best models; wrong-cache failure and selector error preserved in report |
| Windows mypy | BLOCKED | Application Control blocks compiled module; no security bypass |
| Existing Linux CI mypy | BLOCKED | Historical run37219802610 failed37 errors/8 files; diagnostics retrieved and local corrections tested offline. Final Linux typing rerun awaits owner-published changes; no typing PASS claimed |
| Final real Supabase integration | PASS | 13 passed in 517.04s with fresh owner-provided A. Earlier outage (1 failed/12 errors) and exhausted-account run (10 passed/3 failed) retained; no quota/history reset |
| Final SQL verification | PASS | All24 whole scripts passed;14 public tables forced RLS; private reports bucket; reservation150 preserved |
| Final browser regression | PASS | 140 groups across all 11 established suites + 7 default release groups = 147. One initial extraction launch timeout is preserved; remaining nine suites passed on explicit resumption |
| Deterministic dependency/runtime install | PASS | Pinned locks; runtime-only Python3.12.14 venv pip check; current Linux CI hash install and frontend npm ci passed |
| Package advisory audit | PASS | npm249 entries and OSV42 Python pairs; zero known findings; no blind upgrades |
| Engineering license inventory | PASS | MIT/BSD/Apache/MPL/LGPL/native obligations recorded; not legal certification |
| Production native image/worker isolation | PENDING | Image-specific vulnerability/license review, low privilege, private temp and filesystem/egress/crash cleanup before real PHI |
| CI configuration | PASS | Immutable actions, runtime pins, offline synthetic execution without live/production secrets |
| Required branch protections | FAIL | Read-only GitHub branch metadata reports main unprotected and required status checks off; owner configuration/acceptance is required before release |
| Applied migration history consistency | PASS | All17 versions/names match; latest20261004130141; no historical rewrite |
| Fresh complete migration replay | BLOCKED | No approved usable Docker/WSL/Postgres here;17 migrations and24 SQL scripts must run on an empty approved target |
| Isolated staging | BLOCKED | Shared dev is not production-equivalent; no separate target provisioned |
| Backup/restore exercise | PENDING | DB, private objects and configuration recovery documented; no paid backup/PITR or successful drill claimed |
| Public signup/recovery SMTP | BLOCKED | Default/dev sender and confirmation-template limitation; no owned domain/custom SMTP or reliable email acceptance |
| Leaked-password protection | PENDING | Provider advisor reports disabled; operator must assess supported plan/control |
| Managed Postgres maintenance | PENDING | Review provider-supported security maintenance before release; no upgrade authorized |
| Single-instance deployment contract | PASS | One BFF process; distributed refresh/rate coordination unsupported and not proposed |
| OpenAI adapter acceptance | PASS | Gate A: one authorized synthetic English request, exact model/schema/evidence/safety |
| Phase7 persisted live lifecycle | PASS | Gate I: structured/fact/evidence validation, persistence/readback, zero-call reload, stale/correction/deletion/manual preservation and two-user isolation |
| Phase9 bounded persisted live turn | PASS | Gate C: authorized context, facts/evidence/model metadata, persistence/reload and two-user isolation |
| Provider history and no-call regression policy | PASS | OpenAI3 successful authorized requests, no retry/fallback; Gemini2/20 historical503; AI gate unset |
| Internal reservation bookkeeping | PASS | Read150 cents; permanent25-cent reservations toward500; separate from $0.009050 provider estimate; no reset/refund |
| Production AI disabled behavior | PASS | Truthful unavailable, no mock fallback, key loading or provider dispatch |
| Production AI enablement | NOT APPLICABLE | Proposed release keeps AI disabled; no supported production enable switch exists; future enabled scope requires reviewed implementation/policy |
| Broader live multilingual/provider evaluation | NOT APPLICABLE | Disabled-AI proposal only; bounded English live evidence does not establish broad quality; no more requests authorized |
| Voice implementation/simulation | PASS | 48 unit tests and final 20 browser simulation groups passed; no physical-device result inferred |
| Windows Chrome physical voice | PENDING | No user/device results; exact manual checklist prepared |
| Windows Edge physical voice | PENDING | No user/device results; no inference from Chrome or simulation |
| Android Chrome physical voice | NOT APPLICABLE | Optional device extension not required for the proposed voice-disabled scope |
| Default voice release state | PASS | Build defaults disabled; acceptance artifact is separate |
| Targeted accessibility/browser review | PASS | Final route/landmark/label/keyboard/focus/error/status/Hindi/mobile and simulated voice checks passed. Physical screen-reader/device review remains manual; no formal WCAG claim |
| Hosting logs/alerts/incident ownership | PENDING | Code logging is sanitized; actual host configuration and operational drill not performed |
| Deployment/staging artifacts | PASS | Runtime pins, environment template, build/start/health/origin/cookie/feature/rollback instructions prepared |
| HSTS preload | NOT APPLICABLE | No owned production domain or preload decision |
| Phase14 execution/production deployment | NOT APPLICABLE | Explicitly outside authorized Phase13 closure work |

## Four blocker groups and release proposal

**CODE BLOCKERS:** Linux CI typing corrections await a green run of the final changes; historical37 errors/8 files are documented. No runtime/security P0/P1 failure was found in passing checks, but code verification is not complete. AI-enabled production and multi-instance operation require additional implementation if selected; neither is proposed.

**EXTERNAL BLOCKERS:** fresh disposable account A supplied and all 13 live tests passed; old exhausted account preserved; isolated staging/hosting/URLs, public email SMTP, an approved fresh-replay environment, managed provider/security-control review. Historical Gemini503 remains recorded without authorizing retries.

**MANUAL ACCEPTANCE BLOCKERS:** physical Chrome/Edge voice if enabled; Windows mypy tooling (use safe CI); fresh replay, backup/restore, actual HTTPS/gateway/logs, native OCR isolation/license review and incident operations.

**NON-BLOCKING LIMITATIONS:** within synthetic single-instance staging with AI/voice disabled, bounded English live evidence, physical voice pending, OCR/speech platform limits, two upstream warnings, no clinical/formal WCAG/legal/security certification and incomplete native/managed coverage of package scans.

Proposed Phase14 feature state: isolated synthetic staging, one BFF, AI disabled, voice disabled. Public signup/recovery requires reliable SMTP acceptance or an explicitly restricted Auth/UI scope; the current dev project was not reconfigured. Before Phase14: explicit authorization, resolve mypy/green CI, fresh17-migration/24-script replay, approved target/URLs/secrets, configured and verified gateway/runtime/logs, recovery drill and conditional email/voice/AI gates. [Detailed prerequisites](../deploy/README.md). Phase13 is not marked complete while current code verification remains unresolved.

[Exact physical voice checklist](phase-13-manual-acceptance.md). All previous provider failures and consumed authorizations remain in the [acceptance history](openai-acceptance-2026-10-03.md).

## Exact developer manual smoke procedure

Use two confirmed disposable accounts A and B in separate browser profiles. Use only a generated synthetic PDF/PNG or the repository's fixtures. Keep developer tools from recording/exporting credentials and never paste cookies/tokens into a ticket.

1. On the intended HTTPS candidate, verify certificate and same-origin `/api`, exact allowlisted Host, the emitted CSP/frame/nosniff/referrer/permissions headers, no-store on authenticated APIs/downloads, secure `__Host-` cookies with HttpOnly/Lax/Path=/ and no Domain. Check headers on an error response too. Verify local HTTP does not receive HSTS.
2. Sign in as A. Reload, navigate all main routes, and use keyboard/skip navigation. Sign in as B separately and verify independent preferences/data. An unsigned browser must not open protected content.
3. Upload a synthetic report as A. Download and compare bytes; run extraction, review and explicitly publish a synthetic fact. Copy only its opaque report ID into B's corresponding URL; GET/download and a deliberate mutation must be denied. Repeat with observation and conversation IDs. Use normal developer tooling, never a service-role request.
4. From an authenticated test session submit a mutation without its CSRF header, and from a foreign Origin; both must fail. Return to normal UI and confirm legitimate writes still succeed. Do not weaken protection to make a tool work.
5. Correct the source fact. History/trends/explanations/assistant evidence must discard stale results until explicit republication where required. Delete the report; confirm private download and derived pages/data are inaccessible from both profiles. Delete the manual observation and conversation used by the test.
6. Open Assistant. Verify the unavailable notice; no generation on page load, no fake answer, and no provider request. A typed question may persist privately and return the established unavailable/safety/clarification behavior. Do not set RUN_AI_INTEGRATION.
7. Export A's bounded synthetic history as JSON/CSV. Confirm exact strings/units/ranges and owner exclusion; change/delete source then regenerate. No persistent download link may exist. Keep/remove the downloaded synthetic copy deliberately.
8. Open notifications. Verify generic messages, mark read/dismiss with keyboard, and confirm B cannot read or mutate A's event. Switch English/Hindi settings, reload, and check labels, Devanagari wrapping and unchanged source strings/numbers. Assistant response-language preference remains independent.
9. Test network loss by blocking `/api/auth/me` in browser request blocking and reloading; require a safe unavailable state, then unblock and explicitly retry. Interrupt a synthetic upload; verify no usable partial file and explicit recoverability. Record no health values in screenshots/logs.
10. Revoke only A's test session through the approved development account/session control, or use a controlled expired-session fixture; the next protected read must clear content and require sign-in. Check two-tab logout/account change clears private UI. Do not change global token lifetime or unrelated users to simulate expiration.
11. Default release must show voice disabled and retain typing. For a separately approved voice-enabled acceptance build, execute the physical matrix below. Finish by signing out both accounts, confirming protected pages clear, deleting only created fixtures, and restoring preferences.

## Physical voice matrix — all unperformed

| Device/browser | Local capability + pack | Mic permission/Start/Stop/Cancel | Editable exact transcript/no auto-send | English/Hindi | Local TTS start/pause/stop | Route/logout cancellation | Result |
|---|---|---|---|---|---|---|---|
| Windows / Chrome | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| Windows / Edge | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| Android / Chrome, if available | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |

Record device/browser/OS version and whether an already installed local language pack exists. With a synthetic empty chat, enable voice for this visit, check capability before granting microphone permission, start and speak an invented short sentence containing a decimal/unit, stop, edit the transcript, then explicitly append to the draft. Confirm nothing is sent until Send. Cancel another capture; late results must disappear. Deny permission once and test unsupported/missing-pack state without cloud fallback or automatic pack download. Repeat Hindi only if a local pack is already present; mark unsupported truthfully otherwise. Play only a synthetic authorized answer with a local voice; verify pause/stop and cancel on route change, hidden tab, source invalidation and logout. No raw audio should appear in network requests/storage. Never claim speech quality or physical privacy verified from an API mock.

## Phase 14 prerequisites

Explicit user authorization; a selected hosting/HTTPS topology and URL; approved isolated synthetic staging; clean migration replay plus successful restore drill; hardened private worker/temp environment; tested edge rate limits and cookie/header/Origin behavior; managed Postgres maintenance decision; verified production Auth/email configuration; hosted CI green; final Phase13 regressions closed. Keep live AI and voice disabled unless their separate acceptance gates and explicit enablement decisions are completed. A custom domain is optional. Do not deploy or begin Phase14 from this checklist.
