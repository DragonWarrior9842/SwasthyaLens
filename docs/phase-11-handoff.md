# Phase 11 — private exports, account controls and operational notifications

28 September 2026. **Phase 11 is complete.** Implementation, synthetic acceptance,
live Supabase checks and established regressions pass.
Scope is Phase 11 only. No voice, deployment, AI request, billing/provider change,
external notification delivery or full-account deletion was implemented.

The pre-change analysis and verified Phase 10 baseline are in
[phase-11-decision.md](phase-11-decision.md). This phase preserves the Phase 7 live
provider blocker; it does not depend on successful live model output.

## 1. Export architecture

An explicit authenticated, CSRF-protected `POST /exports` selects a bounded owner
snapshot through the invoker `export_context` RPC. RLS and an active-session check
apply inside PostgreSQL. The server validates a closed source DTO, verifies every
row's owner/provenance/scope, then deterministically serializes a direct attachment.
It rechecks the session before delivering bytes. No model or document parser is
involved in export generation.

There is no export job, queue, artifact table, export ID, bucket, signed URL,
public URL or server filesystem output. The browser receives bounded bytes and
starts a fixed-name download via a temporary Blob URL, which is revoked afterward.
This is sufficient for the supported small synchronous export.

## 2. Formats and bounds

CSV: UTF-8 BOM, fully quoted cells, CRLF records, localized headers/status labels.
JSON: UTF-8, `health-export-v1`, stable machine keys, localized `labels` and `codes`,
snapshot `as_of`, UTC date basis, requested period and observations. Source numeric
representations remain strings; unknown facts remain null. PDF is deferred because
the source table formats meet this scope without another rendering/font pipeline.

| Bound | Contract |
|---|---|
| Measurement interval | Required YYYY-MM-DD endpoints; 1900–2100; at most 366 inclusive days |
| Observations | At most 200; reject excess, never silently truncate |
| Contributing reports | At most 20 |
| Attachment | At most 2 MiB; bounded provider response and browser stream |
| Requests | 6 per minute per owner, using the existing development limiter |
| Generation concurrency | 2 per API process |
| Runtime | 15-second service elapsed-time check; 20-second HTTP deadline |
| Browser | 25-second transfer timeout; no mutation replay or automatic generation retry |

A timed-out worker retains its concurrency slot until its upstream work ends.
Existing finite provider I/O timeouts remain in effect. Limits are development
process-local safeguards, not a claim of production distributed rate limiting.

## 3. Exported scope and content model

Current active manual observations and personally reviewed, explicitly published
report observations only. The report must still be owned and uploaded; its linked
review must be confirmed/corrected, field-equal to the published revision and still
the newest review. Rejected, superseded, deleted, unpublished and unreviewed data,
stale AI answers, conversation text and raw document pages are excluded.

Users choose all/manual/report sources, a measurement period and whether unknown
dates are also included. Health history can supply one report filter; its ownership
is checked again at download time. Other history filters are not implicitly copied.
Unknown dates are included only by explicit selection, regardless of period.

Columns/keys: source type, original label/value/unit/reference/flag, comparator,
qualitative result, value kind, measurement day/time, date precision, active status,
observation revision, report filename/record-created time, source page/method,
personal review action and revision. Exported files omit database/owner IDs,
credentials, storage keys, provider metadata and internal extraction rules.

Selected-row batches, metadata-only reports, unpublished reviews, historical
revisions, computed trends and narrative summaries were evaluated and deferred.
The selected observations are the underlying facts used by trends; no trend
calculation or medical interpretation is added to an export. Original reports
retain their existing private download flow.

## 4. Fact preservation

The serializer copies original source strings; it does not round, coerce decimal
strings to binary floats, convert units, supply missing ranges, infer flags,
translate evidence, infer measurement dates or invent clinical conclusions.
Synthetic acceptance covers `13.20`, `<5`, `>10`, `Negative`, `Trace`, `1:80`,
`30–100`, Unicode, quotes/newlines, supplied units/ranges/flags and unknown dates.
Report dates preserve day precision. Manual instants are represented in UTC and
filtered by UTC calendar day; report upload time never substitutes for measurement.

CSV quoting does not prevent spreadsheet formula execution. Cells beginning with
formula characters (`=`, `+`, `-`, `@`, including after whitespace) or leading
tab/newline controls cause a safe 422 offering JSON, rather than altering a source
string. Spreadsheet auto-conversion can still remove zeros: the UI instructs users
to import every column as text. JSON is the lossless string-preserving interchange.

## 5. Multilingual export

English and Hindi export labels/status descriptions are independent of source
evidence. UI locale supplies the default; the form can override export language.
JSON machine keys/codes remain stable and include the chosen localized dictionary.
CSV translates column headers and controlled metadata labels. Original labels,
values, units, ranges, flags and report filenames remain unchanged. No translation
service, remote font, external document renderer or Hinglish export was added.

## 6. Export security and private download

Session cookies remain HttpOnly; existing origin/CSRF protection covers the POST.
The request has no owner field and rejects extra fields/query parameters. Owner
identity comes from the verified session. Both invoker RPC and table policies
enforce ownership/active sessions; Python also rejects foreign/duplicate/malformed
rows and incoherent provenance. A supplied foreign/deleted report is unavailable.

Responses use `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, fixed
`Content-Disposition`, and a sandboxed CSP. The client checks type, filename,
declared size and actual stream length before starting a download. Account changes
and unmount abort work. No medical bytes or credentials are logged by new code.

## 7. Lifecycle and invalidation

Idle → generating → ready/download started, or an explicit safe error. Ready means
the attachment was generated and handed to the browser; it does not claim that the
user saved it to disk. Page load never generates an export. Retrying is explicit.

Each new request reads current trusted data. Review changes/rejections, supersession
and report/manual deletion remove stale facts from subsequent generation. There is
no historical export route to retrieve an earlier result; such GETs return 404.
A consistent database snapshot defines the request's contents. Deletion after the
snapshot cannot retract a response already in flight or a downloaded device copy.

## 8. Retention and cleanup

Exports have zero durable server retention. There is no export expiry/delete UI or
endpoint because there is no retained artifact to expire or delete. The browser
revokes its temporary Blob URL. Users manage downloaded device copies themselves;
the UI says source deletion cannot remove those files. Export lifecycle tests verify
the absence of a stored download endpoint and current-data regeneration after deletion.

## 9. Account/settings changes

Existing display name, interface language, assistant response language and timezone
remain. Added only the strictly boolean `in_app_notifications` preference (default
true), applying to future report events. Turning it off leaves current notices
until dismissal/expiry. Settings retain owner/active-session RLS and narrow column
grants; null, strings and numeric substitutes for the boolean are rejected.

The data-management area links exports and existing reports/history/assistant
sections for individual report, manual observation and conversation deletion. No
new sensitive profile fields, full-account deletion, notification delivery address
or external service setup is required.

## 10. Notification architecture

`public.notifications`: generated UUID, owner, report reference, closed event type,
event identity, created timestamp and nullable read timestamp. Three database AFTER
UPDATE transition triggers share a private function and emit five event types in the same
transaction as successful state changes. No success notice is written on insert,
job start, failed upload or backfill.

Unique `(event_type,event_key)` plus status-transition guards prevents replay
duplication. The source report/run identity determines the event identity. A new
actual retry run can produce its own legitimate outcome. Owner-scoped advisory
locking serializes event creation/retention and notification mutation. The client
cannot submit event text or fabricate notices.

## 11. Actual event types

| Event | Trigger |
|---|---|
| `upload_completed` | Report becomes uploaded after successful storage completion |
| `extraction_completed` | Text-processing run actually completes |
| `extraction_failed` | Text-processing run actually fails |
| `parameters_ready` | Parameter run completes with at least one candidate |
| `parameters_failed` | Parameter run actually fails |

Zero-candidate completion does not say there is something to review. No export-ready
notice is persisted: the synchronous export UI already presents the actual result.
There are no diagnostic, urgency, worsening-health or invented medical alerts.

## 12. Notification localization

The server returns typed event keys, not stored translated prose. The existing
Phase 10 dictionary renders all five events and controls in English/Hindi. Language
changes alter the UI without changing stored events/read state. Timestamps currently
use explicit ISO UTC strings; no locale-dependent ambiguous date parsing is needed.

## 13. Notification privacy and retention

Global count and previews contain generic operational copy only: no report filename,
measurements, symptoms, medication, document text, exception body or provider output.
Opening reports uses the existing protected data flow. No email/SMS/push/SMTP,
delivery analytics or external notification provider was added.

At most 100 notices per owner, at most 30 days. Lists return 20 rows with bounded
offset pagination and an unread count. Owner-history, report and expiration indexes
support these operations. RLS hides expired notices immediately. Read/list/event
operations prune expired/unavailable notices; hourly cron at minute 27 physically
cleans expiration. Report deletion intent removes associated notices. Physical
expiration can lag the 30-day visibility cutoff by up to the scheduled interval.

## 14. RLS and database security

Migration `20260928125713_exports_notifications.sql` is applied and agrees with hosted
history (15 migrations). Notification RLS is enabled and forced. Authenticated table
access is SELECT-only and checks owner, active session, expiry and available parent;
anonymous/direct writes are denied. Read/dismiss changes use the existing worker
secret plus owner JWT through a public invoker/private definer boundary with empty
search paths and explicit grants. Private trigger/cleanup functions have no client
execute grant. No service-role key is exposed to the frontend.

Post-migration security/performance advisors were run. Performance is clear; no
Phase 11 advisory was introduced. Existing notices remain: three intentionally
policy-less private evaluation tables (default deny) and leaked-password protection
disabled. See [private-table lint](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy)
and [password protection](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).
Production account/security configuration remains a separate later-phase concern.

## 15. APIs

| Route | Behavior |
|---|---|
| `POST /exports` | Closed format/language/date/unknown/source/report selection → direct private attachment |
| `GET /notifications?offset=0` | Owner page, unread count, next offset |
| `PATCH /notifications/{id}` | Mark an owned available notice read; first read timestamp is stable |
| `POST /notifications/read-all` | Mark current owned unread notices read |
| `DELETE /notifications/{id}` | Dismiss an owned available notice |
| `GET/PATCH /settings` | Existing contract plus boolean `in_app_notifications` |

Notification writes require empty closed JSON bodies and CSRF. Foreign, dismissed
or expired identifiers return 404. Lists/mutations share a 60/minute owner limiter;
offsets are bounded 0–100. Export source/size/format errors are safe public codes.
Provider bodies, submitted evidence and credentials never become UI error copy.

## 16. Frontend UX and accessibility

Export selection is available from history and settings. Native labeled source,
date, format, language and unknown-date controls work by keyboard. Generating and
download-started statuses use live status semantics; safe failures use alerts.
Controls disable during the request. Limits, CSV text-import and device-copy
retention are explained before download.

The account bar shows a textual unread count and links to the notification center.
The center supports refresh, one/all read, dismiss, older/first page and settings.
Unread state is text, not color alone. Visibility polling is every 60 seconds;
focus, visibility, history changes and content-free cross-tab notice signals refresh
state. The center and header currently make separate bounded reads. Protected
components clear on logout/account switch. English desktop and Hindi 375px mobile
views were inspected; this is not a formal WCAG certification.

## 17. Live two-user acceptance

The new gated live test passed with real dedicated A/B Supabase sessions and
generated synthetic PDFs/manual values. It verifies actual upload/text/parameter
transitions and idempotent replay; each owner gets only their events/data. A/B
foreign export/report/notification access fails; direct RLS reads are empty.
Missing CSRF, forged owner input, source rejection/deletion and revoked sessions
are exercised. Fixtures are removed and preference changes restored.

Full final live regression: **13 passed in 501.71 seconds**. This includes auth,
reports/private Storage, extraction and worker-death recovery, parameters,
observations, trends, mock explanations/assistant, multilingual settings, exports,
notifications, correction/deletion, revocation and two-user isolation. Output is
retained locally in ignored `.cache/qa/phase11/live-regression.log`.

## 18. Export validation results

50 new focused backend cases pass, including English/Hindi CSV/JSON exact-string
round trips, unknown dates, provenance, formula rejection with unchanged JSON,
Unicode/quotes/newlines, invalid/foreign/inactive/incoherent rows, duplicate rows,
200-row/20-report/size bounds, UTC midnight behavior and elapsed-time rejection.
Live acceptance preserves all seven requested synthetic values in both formats,
excludes a newly rejected source and excludes deleted reports/manual observations.
Browser acceptance checks actual downloaded bytes, A/B separation, explicit
generation, error state, no historical artifact URL and deletion regeneration.

## 19. Notification validation results

SQL lifecycle/limit/schema tests pass for pending-versus-completed transitions,
success/failure events, zero-candidate suppression, replay, opt-out of future events,
100-row/30-day retention, idempotent read state, dismiss, ownership, direct-write
denial, active-session revocation and report-deletion cleanup. Closed backend/client
DTOs reject unknown/medical payloads, foreign owners, malformed IDs/events/timestamps,
duplicates and invalid pagination/counts. Browser acceptance covers real events,
unread text/count, keyboard mark-read, mark-all, dismiss, refresh and language switch.

## 20. Frontend and browser results

Final frontend lint/typecheck/build pass. Vitest: **323 passed in 15 files** (27 new
service tests); translation-catalog parity remains checked. Final production assets:
main 527.64 kB / 149.95 kB gzip, CSS 37.13 kB / 8.85 kB gzip; lazy chart 143.49 kB /
50.33 kB gzip. The existing Vite 500 kB advisory remains; no dependency was added.

New real synthetic Phase 11 browser acceptance: **14 groups passed**, zero browser
runtime errors, zero AI calls and exactly five explicit export POSTs (one deliberately
invalid). The harness uses two real accounts and actual API-generated artifacts;
only a delayed request is intercepted to observe generating status.
Screenshots/results are in ignored `.cache/qa/phase11/` with account identities masked.
All **105 established browser groups** pass: auth 15, reports 11, extraction 7,
parameters 8, observations 12, explanations 12, trends 13, assistant 13 and
multilingual 14. Together with Phase 11 this is **119 passing browser groups**.
The final regression log is `.cache/qa/phase11/browser-regression.log`; it retains
the extraction startup failure and subsequent passing continuation described below.

## 21. Backend, SQL and regression results

Ruff check and format pass (107 Python files); mypy passes (104 source files).
Normal deterministic pytest: **635 passed, 22 gated skips**. Nine explicitly gated
local synthetic OCR cases also pass. Existing Starlette/httpx/AnyIO deprecations
remain. Tests needed normal cache permissions; no dependency upgrade was introduced.
All **22** rollback SQL verification scripts pass, including the three new Phase 11
scripts. SQL/live/browser fixture work is serialized to avoid shared-account races.

Baseline before changes: frontend 296, backend 585, OCR 9, live Supabase 12, SQL 19,
established browser 105 groups all passed. Initial browser selector/test-route/logout
assertions were corrected; an interrupted test's identified synthetic fixtures were
removed through the owned API. No existing user report was deleted to force a test.
The older local auth harness now targets the preferences section by its accessible
heading instead of assuming it is the last settings card. The regression runner uses
UTF-8 output for Hindi diagnostics; these are test-harness compatibility corrections.
The existing extraction browser harness had one pre-login startup timeout (also
observed in the Phase 10 baseline); all seven extraction groups passed on the
isolated continuation. No application change or weakened limit was used for it.

## 22. Gemini and AI state

No Phase 11 live OpenAI/Gemini call. `RUN_AI_INTEGRATION` remains unset. Gemini remains
**2/20** after the two previously authorized synthetic HTTP 503 UNAVAILABLE responses.
No prior 401/403 or 429/quota exhaustion was returned; no quota values are invented.
Live provider acceptance remains externally blocked. The existing paid reservation
ledger is unchanged at 50 cents. Provider/model abstraction, keys and billing remain
unchanged/private. Ordinary tests use deterministic mocks; synthetic live Supabase
acceptance never enables a model provider.

## 23. Known limitations and manual checks

Limits intentionally require splitting large histories into smaller periods/scopes.
Unknown dates are opt-in and can fill capacity independently of the chosen period.
CSV may be unsuitable for formula-like/negative-leading source strings; JSON remains
available. No PDF, whole-account archive, computed trend export or selected-row batch
is provided. No export download history or device-file recall is possible.
Notification refresh is polling/focus based, not push; notifications are operational
history, not clinical alerts. Read state, not delivery analytics, is stored. Full
account deletion, email/push and production infrastructure remain out of scope.
Hindi copy is locally authored, without external linguistic/clinical certification.
Production accessibility/load testing and distributed enforcement are not claimed.

Manual checks (synthetic data only):

1. Start the usual backend and frontend with `RUN_AI_INTEGRATION` unset. Sign in to A.
2. Add a synthetic manual observation or upload/review/publish a synthetic report.
3. Open settings → Export health history. Choose an appropriate measurement period,
   JSON, and optional unknown dates; explicitly generate. Compare exact stored facts.
4. Repeat as Hindi CSV. Import every column as text; verify trailing zeros and units.
   Try a period longer than 366 days and verify an honest failure.
5. Delete a synthetic source and generate again: removed facts must be absent.
   A selected deleted report fails. Previously saved device files remain yours to delete.
6. Upload and process a synthetic report. Open Notifications; verify generic real
   outcomes, unread count, mark read/all, dismiss and refresh. Switch interface language.
7. Disable future in-app notices in settings, save, and perform another synthetic
   report event; previous notices remain, but the new notice is not created.
8. Sign in to B separately. A's facts/events must be unavailable. Sign out A and
   revisit protected export/notification pages; sign-in must be required.
9. Check native labels/tab navigation and a 375px viewport. No voice permission,
   email/SMS/push setup or live AI request should occur.

## 24. Files, suggested commit and Phase 12 prerequisites

Created:

- `backend/app/{api,core,schemas}/{exports,notifications}.py`
- `backend/tests/test_exports_notifications.py`
- `backend/tests/integration/test_live_exports_notifications.py`
- `backend/tests/browser_exports_notifications.cjs`
- `database/migrations/20260928125713_exports_notifications.sql`
- `database/verification/exports-notifications-{schema,lifecycle,limits}.sql`
- `frontend/src/pages/ExportsPage.tsx`
- `frontend/src/features/system/Notifications.tsx`
- `frontend/src/services/{notifications.ts,exports-notifications.test.ts}`
- `docs/phase-11-decision.md` and this handoff

Modified:

- Backend factory, core accounts/provider, account schemas and auth test fixture
- Frontend App routes, account menu/redirect, history/settings pages, auth types,
  account/auth/API services and related tests, Hindi dictionary/catalog test, styles
- README, database README and `.gitignore` (exclude generated root Supabase CLI cache)

No new package/runtime dependency. The user committed the main implementation as
`2eebb2e` during acceptance; this handoff documents the whole phase, including the
remaining validation/documentation changes. No commit or push was made by the agent.
Suggested phase commit: `feat: add private exact-value exports and operational notifications`.
For the remaining closure changes: `test: verify Phase 11 exports and notifications`.

Phase 12 is **unstarted**. A later explicit authorization must define optional voice
input/output, provider/privacy/cost choices, consent, permission handling, language
coverage, text alternatives, retention and synthetic acceptance before implementation.
The external Gemini blocker remains a separate unresolved decision. No microphone,
speech-to-text, text-to-speech, audio upload or voice assistant code was added here.
