# Phase 11 decisions and verified baseline

28 September 2026. Scope: exports, useful account controls and operational in-app
notifications only. No AI request, external delivery, account deletion or voice.

## Baseline before implementation

Read technical audit, Phase 6–10 handoffs and README. Reinspected history, report
lifecycle, dashboard, settings, assistant, i18n, private downloads and RLS.
Frontend lint/typecheck/build and 296 tests pass. Backend Ruff/format/mypy and 585
tests pass (21 explicitly gated skips); nine local synthetic OCR cases pass.
All 12 live Supabase tests pass in 489.46 seconds. All 19 rollback SQL scripts and
105 browser groups pass. Existing bundle-size/dependency warnings remain.
Security advisors retain the three intentional private default-deny table notices
and leaked-password warning; performance advisors are clear.

The Gemini ledger is 2/20; paid reservations remain 50 cents. RUN_AI_INTEGRATION is
unset. Phase 7 live acceptance remains externally blocked by the two prior 503s.

## Export decision

Use explicit POST /exports for a direct private attachment. A single owner/RLS
database snapshot selects current active manual observations and personally
reviewed, explicitly published report observations. Server validation precedes
serialization. No queue, durable job, Storage object, public URL or retained export
exists. Every repeat download regenerates current data. There is consequently no
artifact ID, historical download, expiry state or artifact-delete endpoint to fake.
Downloaded device copies cannot be recalled; explain this in the UI.

Support CSV and JSON, English/Hindi labels, source selection, a required inclusive
measurement period of at most 366 days, optional unknown-date inclusion and an
optional owned report filter. UTC defines manual measurement days, consistent with
Health history; report days retain day precision. Unknown dates are never replaced
by upload time. Limit 200 observations, 20 contributing reports and 2 MiB output;
reject excess rather than truncate. Bound request time, concurrent generation and
per-owner requests. Do not log source fields or artifact contents.

Preserve exact raw values, units, comparators, qualitative results, supplied ranges
and flags. Include report filename/page/source method, review action/revision and
observation revision/status. Avoid owner/database IDs, internal provider/parser
metadata and source text outside the selected finding. JSON uses stable keys and
localized field labels; numbers stay strings and absent facts stay null. CSV uses
UTF-8 with BOM and translated headers. Reject spreadsheet-formula-leading cells
and offer JSON instead of changing source values to escape them. Explain text-mode
CSV import: spreadsheet automatic conversion can remove zeros despite exact bytes.

Report-only metadata, unpublished reviewed candidates, historical revisions,
selected-row batches, trend calculations and narrative summaries are deferred:
they need different trust/date/schema semantics and are not necessary for a useful
first export. Reports already have private original-file downloads. The exported
observations include the source data used by trends. PDF adds font/layout machinery
without a current requirement; no PDF library or remote rendering is justified.

## Settings and notification decision

Keep display name, interface language, assistant language and timezone. Add one
boolean preference for future in-app operational notifications, plus a data
management area linking exports and the existing report/manual/conversation
deletion controls. Disabling future notifications does not erase existing notices.
Do not collect demographics or implement partial full-account deletion.

Persist generic event keys, owner, report pointer, event identity, created/read
times. No report names, values, medical text, translated prose or error payloads.
Database AFTER UPDATE triggers create events in the successful lifecycle
transaction: upload completed; text extraction completed/failed; nonempty parameter
extraction ready for review; parameter extraction failed. No events at job start,
no backfill and no medical alerts. Unique event identity plus transition checks
prevent replay duplication. Parameter review remains personal, not clinical.

Owner/active-session RLS, narrow grants, private worker-gated mutations and typed
API validation protect list/read/dismiss operations. Retain at most 100 events per
owner and 30 days, with expiry filtering on every access and scheduled cleanup.
Report deletion intent removes its notices. Paginate 20 rows, show unread text/count,
mark one/all read and dismiss. Translate closed keys with Phase 10 dictionaries;
locale changes never rewrite event rows. Refresh/focus/visible polling supplies
freshness, without external push/email/SMS or SMTP setup.

## Acceptance plan

Synthetic exact-string CSV/JSON round trips, formula handling, strict limits,
foreign/invalid source responses, CSRF/revocation, owner isolation and source
correction/deletion regeneration. SQL proves real event transitions, idempotency,
retention, read state and ownership. Live A/B workflows use genuine Supabase sessions
and generated synthetic reports only. English/Hindi browser acceptance includes
download bytes, validation, notifications, refresh/logout, keyboard and mobile.
Rerun previous frontend/backend/live/SQL/browser regressions and both advisors.
No live AI call is part of any check. End with the Phase 11 handoff and stop.
