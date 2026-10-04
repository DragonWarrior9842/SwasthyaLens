# Production readiness checklist — Phase 13

2026-10-03. **Production release is BLOCKED. No deployment is authorized or performed.** Phase 13 hardening verification is in progress; pending rows must not be treated as PASS. See [handoff](phase-13-handoff.md), [operations/environment contract](phase-13-operations.md), and [security matrix](phase-13-security-matrix.md).

PASS means observed within the stated scope. FAIL means a verification actually failed. BLOCKED means an identified dependency prevents acceptance. PENDING means not yet performed. NOT APPLICABLE means deliberately outside this release scope. P0 critical; P1 serious release gate; P2 should resolve or explicitly scope out before release; P3 improvement. Severity applies to unresolved release exposure, not simply a vendor advisory label.

| Area | Status | Priority / evidence / remaining action |
|---|---|---|
| Pre-change complete baseline | PASS | FE371, BE635, OCR9, live13, SQL22, browser139 |
| Release config, test/mock separation | PASS | Explicit environments/hosts; placeholder and integration flag rejection; injected and stored mocks rejected; AI disabled |
| Local secure cookie/Origin/CSRF/Host contract | PASS | HttpOnly, Secure, host-only, Lax; every mutation rejects missing CSRF; deployment HTTPS verification remains separate |
| Auth/session refresh/revocation and two-user isolation | PENDING | Full final live/browser regressions still running; baseline and local suites passed |
| Private Storage and forced public-table RLS | PASS | Read-only metadata audit plus baseline real A/B and SQL tests; private processing-key ACL exception documented |
| Final live Supabase + SQL regression | PENDING | Must finish all 13 live tests and 22 rollback scripts |
| Upload/OCR bounds | PASS | Final OCR9; adversarial units; new total read deadline and upload capacity cleanup |
| Numeric/source grounding and stale/delete behavior | PASS | Deterministic local regression; final live/browser closure tracked separately |
| Export and notification privacy | PASS | Existing owner-bound nonpersistent exports/generic notices; local tests pass; final live/browser closure tracked separately |
| Actual local frontend CSP/header behavior | PASS | Seven new Chrome groups; no unsafe-eval/unsafe-inline; no localhost HSTS; no third-party requests |
| Route failure/network recovery | PASS | Missing lazy chunk and blocked actual session endpoint fail visibly and recover explicitly |
| FE final lint/types/tests/build | PASS | 371/16; pinned Node24.19.0/npm11.19.0; default voice-disabled build |
| BE final local tests | PASS | 665 passed, 22 explicitly gated skips; 30 new local security cases |
| BE final lint/format/types | PENDING | Recheck after final audit-script formatting |
| Established browser139 final regression | PENDING | Acceptance artifact explicitly enables voice simulation; default release remains disabled |
| Fresh frontend install | PASS | npm ci from reviewed lock on supported Node; no known full-lock audit findings |
| Fresh backend runtime-only install | PASS | Separate Python3.12.14 venv, hash-verified runtime lock, pip check and native/runtime imports |
| Package advisory fixes | PASS | PyJWT2.15.0 and brace-expansion5.0.12; no bulk/major upgrades; native image scan remains separate |
| Secret/history/bundle audit | PASS | 665 reachable blobs, six local values compared privately, 21 bundle files; three reviewed public-alphabet false positives; no actual findings |
| Test account credential hygiene | P2 / PENDING | Use strong unique disposable credentials; a short test credential required false-positive triage. Do not promote/reuse test accounts for production. No rotation performed |
| License inventory | PASS | Engineering inventory only; LGPL/MPL/native redistribution obligations need image-specific review |
| CI source configuration | PASS | Immutable action references, runtime pins, no live AI or production credentials |
| Hosted CI/branch protections | PENDING | P2; no push or remote workflow execution performed |
| Migration versions/history review | PASS | Fifteen ordered local versions match dev DB; no history rewrite |
| Fresh complete migration replay | BLOCKED | P1; no Docker/Postgres here; isolated local replay and all22 SQL checks required; never reset shared dev |
| Isolated staging | BLOCKED | P1; no separate environment authorized/provisioned; dev acceptance is not production-equivalent |
| Backup + restore exercise | PENDING | P1; no scheduled backup/restore test claimed; DB and Storage objects need separate recovery |
| HTTPS gateway/origins/edge limits | PENDING | P1; no actual release URL/host; install and verify headers, TLS, no-store, body/time/concurrency limits |
| Production OCR isolation/private temp storage | PENDING | P1 before real PHI; subprocess bounds are not an OS sandbox; validate low privilege, filesystem/egress boundaries and crash cleanup |
| Supported single-instance topology | PASS (design only) | One BFF process; distributed refresh/rate coordination not implemented; multi-instance release unsupported |
| Managed Postgres security maintenance | PENDING | P1 review before release; observed17.6, provider17.11 announcement; no upgrade performed |
| Supabase production Auth/SMTP | BLOCKED | P1 for public signup; actual email delivery/OTP acceptance unverified; default development sender insufficient; no SMTP purchase/configuration |
| Leaked-password protection review | PENDING | P2; provider advisor reports disabled; confirm plan/support and intended launch control |
| AI implementation | PASS | COMPLETE; adapters/schema/evidence/safety controls preserved |
| AI mock/synthetic acceptance | PASS | COMPLETE within deterministic tests |
| Previous AI provider evaluation: Gemini | BLOCKED (historical) | Two HTTP 503 UNAVAILABLE responses; 2/20 used,18 remain; preserve attempts and ledgers |
| OpenAI / `gpt-6.1-sol` single-fixture live adapter acceptance | PASS (bounded scope) | One explicitly authorized request, HTTP 200; exact model/schema/evidence/safety passed; no retry; estimated $0.003704; no DB/Storage access. [Attempt report](openai-acceptance-2026-10-03.md) |
| Full Phase 7 persisted live application acceptance | PENDING | Single-fixture adapter success does not verify OpenAI enrollment/persistence/API/UI/lifecycle; separate authorization and integration required |
| Phase 9 live assistant acceptance | NOT COMPLETE / preparation failed | Authorized persisted run stopped during synthetic report preparation before OpenAI; zero new AI calls, no persisted assistant/readback/isolation result. Harness owner-check defect corrected offline; no automatic rerun. [Gate 2 result](openai-acceptance-2026-10-03.md#gate-2--persisted-phase-9-flow-stopped-before-openai) |
| OpenAI persisted metadata support | PASS (code/schema only) | Exact `openai` / `gpt-6.1-sol` pair in backend/frontend and migration `20261003180952`; forced RLS/grants unchanged; two SQL checks passed. Does not imply generated-message acceptance |
| Latest offline regression / backend typing | PASS / type check BLOCKED | Before runtime: BE685 with22 skips; FE372/lint/types/build. After harness fix:212 targeted PASS. Windows Application Control blocks mypy's compiled module; no bypass or typing PASS claimed |
| AI default production behavior | PASS | Explicit unavailable; no release key load or mock fallback. Enabling later requires separate acceptance/approval |
| Voice implementation/simulated acceptance | PASS (baseline) | COMPLETE implementation; established20 browser/48 unit simulation baseline; final suite pending |
| Physical voice: Windows Chrome | PENDING | P2 optional feature gate; user/device acceptance required before enabling |
| Physical voice: Windows Edge | PENDING | Same; do not infer from simulation |
| Physical voice: Android Chrome | PENDING | If device available; not claimed tested |
| Voice default release state | PASS | Build flag false and visible typed fallback; separate acceptance artifact only |
| Accessibility/English/Hindi | PASS (targeted) | Landmarks, headings, labels, keyboard, mobile, contrast review; baseline language suite passed; full final regression pending; no WCAG certification |
| Observability / sanitized exceptions | PASS (code) | Coarse request/category/timing logs; no third-party monitoring installed; deployment log policy still requires configuration |
| Operations alerts/SLO/on-call drill | PENDING | P2; configure controlled logs/aggregates and incident owner at deployment |
| HSTS preload/custom-domain ownership | NOT APPLICABLE | No domain or deployment selected; no preload/includeSubDomains assumptions |
| Full account deletion / Phase14 deployment | NOT APPLICABLE | Not authorized in Phase13 |

## Release blockers, separated

**Code verification blockers:** none identified in the already-passing runtime/security tests; final full regression and audit-script checks are still pending. Multi-instance deployment is unsupported and must not be selected without further implementation. Native parser isolation must be satisfied by the chosen runtime boundary before real-data release.

**External blockers:** production SMTP/email acceptance, isolated staging/runtime infrastructure and managed Postgres upgrade assessment. Historical Gemini evaluation remains blocked by two HTTP 503 responses (2/20). OpenAI / `gpt-6.1-sol` now passed one explicitly authorized synthetic adapter request; its authentication/model-access blocker is resolved for that attempt. Full Phase 7 and Phase 9 live application acceptance and production enablement remain open; normal AI stays unavailable. The one-request authorization is consumed; no further request, automatic provider/model change, billing action, new project or SMTP purchase is authorized. See [acceptance controls](phase-13-operations.md#ai-provider-status-and-acceptance-controls).

**Manual/operational acceptance blockers:** clean migration replay, backup/restore drill, deployed HTTPS/proxy/edge limits and log privacy, OS parser/temp isolation, Auth production URLs/settings, hosted CI, physical voice before optional enablement. Phase13 does not claim these performed.

**Non-blocking limitations within the disabled-feature/single-instance scope:** no live AI results, voice hardware pending, OCR accuracy limitations from Phase4/5, no diagnostic/clinical validation, no formal accessibility/legal/security certification, two upstream test-client deprecation warnings, registry scans do not cover every native/managed component.

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
