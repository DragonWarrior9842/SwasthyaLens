# Phase 6 — Personal health observations and real history

This phase implements deterministic personal history and an owner-backed dashboard.
It adds no AI, trends, diagnoses, reference classifications, recommendations, voice,
notifications, external credentials or service dependencies. Personal review is not
clinical validation. The pre-implementation decision is [phase-6-decision.md](phase-6-decision.md).

## 1. Architecture

An observation is a stable owned identity with append-only value/date revisions.
Report identities point to a Phase 5 candidate; manual identities have no report
relationship. PostgreSQL performs atomic publication and lifecycle transitions.
FastAPI validates input, passes the verified user's JWT, checks returned ownership
and resource identity, and returns bounded typed contracts. React uses the existing
account-checked transport and session lock; no health data enters browser storage.

## 2. Promotion eligibility

The latest candidate review must be `confirmed` or `corrected`, with a nonblank raw
value. Publication is a separate explicit action with its expected review revision.
Unreviewed machine candidates, missing values, rejected reviews and stale revisions
cannot publish. The database derives the value, unit, metric, report, candidate and
review from stored owner-scoped evidence. Browser input contains only lookup IDs,
expected revision and an optional user-confirmed calendar day.

## 3. Trusted versus machine-derived boundary

Extraction alone and review alone create no observation. A published value means
the user chose to include that reviewed snapshot in personal history. Unmapped,
unparsed and qualitative results remain faithful text; publication confers neither
clinical certainty nor eligibility for numeric calculations. Original machine fields
and source text remain separate and visible. There is no automatic extraction →
review → publication pipeline and no backfill of earlier reviews.

## 4. Database schema and migration ordering

Apply all earlier migrations first, then these recorded development migrations:

1. `20260917103144_health_observations.sql` — identities, revisions, forced RLS,
   lifecycle functions, review invalidation and public invoker wrapper.
2. `20260917105520_observation_query_aliases.sql` — disambiguates SQL aliases from
   PL/pgSQL row variables. Found by live dashboard validation.
3. `20260917165418_observation_measurement_order.sql` — orders known instants within
   each measurement day before records with day-only precision.

Each filename originated with `supabase migration new`; final timestamps match the
hosted migration service. Applied SQL was not rewritten. The existing development
project is `swasthyalens-dev` (`rbmpfgndidpzdssiicyf`). No reset or other project was used.

`health_observations` holds ID, owner, source type, optional report/candidate/source
run/page/span identity, manual creation request key, creation time and deletion
tombstone time. The evidence tuple is unique within a report and text attempt.
`health_observation_revisions` holds observation/revision identity, status, complete
Phase 5 fields snapshot, catalog version, optional calendar day or manual instant,
source candidate/review revision, manual request key, creation and status-change times.
The partial unique index permits only one active revision per observation. A trigger
rejects snapshot updates; only an active revision's lifecycle metadata may transition.

## 5. Provenance

Observation revision → exact Phase 5 review revision → immutable candidate → parameter
attempt → Phase 4 text attempt and page/span → original owned report. Foreign keys
retain this chain until deletion. Detail responses include the report name, report
record creation time, original candidate fields, page number, source text/method,
offsets and version-bearing Phase 5 fields. The UI exposes the useful evidence and
authorized download without displaying UUIDs. Full IDs remain in API contracts for
machine-verifiable references. Snapshot values/dates are never silently updated.

## 6. Sources

Only `report` and `manual` exist. UI badges say **From report** and **Manually entered**.
Manual snapshots have no laboratory report, candidate, review or extraction provenance.
Changing a manual value to another supported metric preserves its earlier revisions.
Report observations must be changed through their candidate's review workflow.

## 7. Date semantics and ordering

Phase 5 extracts no reliable clinical date. Report publication therefore defaults to
an unknown date. Users may explicitly supply a day between 1900-01-01 and 2100-12-31.
The stored SQL `date` retains day precision; no midnight measurement is invented.
Manual entries require an offset-bearing ISO timestamp in the supported UTC year
range, stored as `timestamptz`; forms and display explicitly use UTC. Account timezone
preferences are not applied to this phase's history view. Publication/creation,
report reservation and measurement times remain separately labeled.

Ordering: measurement day descending (manual instants use their UTC day), then actual
manual instant descending, then observation creation time and UUID descending as
stable ties. Day-only records follow known instants on the same day. Unknown dates
come last, ordered by recording time. Date filters exclude unknown dates; date bounds
are inclusive. There is no latest-metric card or clinical inference from record age.

## 8. Metric definitions

The intentionally narrow `observations-v1` catalog includes the Phase 5 identities
`hemoglobin`, `tsh`, `vitamin_d_unspecified`, `glucose_unspecified`, `crp`, plus manual
`weight` and `heart_rate`. It provides labels and allowed manual units. It is a
versioned code catalog, not a medical ontology or clinical comparability registry.
The API exposes it through `/observations/catalog`; the UI's matching filter list
is static for this version. Unknown report identities remain null and visible.

## 9. Units

Every report unit is preserved exactly, including unknown/missing units. No alias
normalization, conversion or merging occurs in the history list or dashboard.
`mg/dL` and `mmol/L` remain separate observations even under the same canonical ID.
The manual API accepts only the exact metric/unit pairs weight/kg and heart_rate/bpm.
Future calculations must independently establish compatible units and clinical
context; catalog identity alone is insufficient, especially for unspecified metrics.

## 10. Numeric and qualitative values

Raw value, exact numeric string, comparator, qualitative result, value kind, reference
text/bounds and printed flags survive in the complete snapshot. `Negative`, `Positive`,
`Trace`, `1:80`, `<5` and `>10` are not coerced into ordinary floats. Values travel as
strings; manual validation uses Python `Decimal` and PostgreSQL `numeric` only for
technical bounds. Display uses the raw spelling. Calculated range status stays
`unknown`; neither frontend nor database adds a medical classification.

## 11. Report observation lifecycle and idempotency

Candidate + review revision is the publication idempotency identity. Repeating the
same eligible revision/date returns the same observation and snapshot. A different
date under the same revision conflicts. To correct a report observation's date,
create a new personal review revision and explicitly publish it with the corrected day.
The latest-review check precedes replay so an old request cannot resurrect rejected
or superseded history. A second parameter attempt over the identical text-attempt
page/span cannot create another observation identity. Different text attempts and
different reports are not automatically medically deduplicated.

## 12. Corrections and rejection

Every new review atomically removes the previous active snapshot: `superseded` for
confirmation/correction, `invalidated` for rejection. The new eligible review becomes
active only after explicit publication. Old values remain inspectable through the
observation revision list and the optional inactive-history filter. Rejection never
leaves a contradictory active value. Report deletion, review writes and publication
take the same owned-report lock; stale expected revisions fail instead of overwriting.

## 13. Manual-entry scope, editing and deletion

Weight/kg accepts positive decimal strings with up to three fractional places;
heart_rate/bpm accepts positive integers. Both must be below 10000, a technical input
bound rather than a clinical range. Scientific notation, signs, separators, NaN,
infinity, comparators and mismatched units are rejected. Measurement time is required.
No arbitrary laboratory, glucose, sleep or activity entry form is implemented.

Creation has an owner-scoped UUID request key; edit has a request key and expected
revision. Edits append and supersede atomically, capped at 100 revisions. There are
1000 lifetime manual identities per account, including deletion tombstones, as a
development resource bound. Deletion erases all value/date revisions and retains
only opaque owner/identity/request-key/system-time metadata so creation retries cannot
resurrect deleted health data. Repeated deletion is safe; stale live edits/deletes fail.

## 14. API

All routes below require a verified active account. Writes additionally require the
existing exact Origin, JSON and signed CSRF protections.

| Method / route | Contract |
| --- | --- |
| `GET /observations/catalog` | Version and small metric/manual-unit catalog |
| `GET /observations` | At most 20 current snapshots, `next_offset` or null |
| `GET /observations/{id}` | Current snapshot, retained revisions and evidence |
| `POST /reports/{report_id}/parameters/{candidate_id}/publish` | Expected review revision and optional date |
| `POST /observations/manual` | Request key, metric, exact raw value/unit, aware timestamp |
| `PATCH /observations/{id}` | Manual correction plus expected revision/request key |
| `DELETE /observations/{id}` | Manual deletion plus expected revision |
| `GET /dashboard` | Owned counts, up to five observations and three recent reports |

Filters are metric, `source_type`, `date_from`, `date_to`, owned `report_id`,
`include_inactive` and bounded offset 0–10000. Lists use an extra row to determine the
next page. Offset pages are deterministic for a stable dataset; concurrent changes
may shift page boundaries. Refresh restarts browsing. No query language or bulk export
is added. `/health` retains its exact unauthenticated Phase 1 liveness response.

## 15. Dashboard

Shows counts of uploaded reports, candidates whose current review is confirmed or
corrected, and active observations. Reviewed-parameter count is not a publication
count. Recent observation cards retain separate values, units, source and dates.
Recent reports are sorted by report-record creation time, explicitly labeled as such.
No hardcoded personal numbers, seeded values, trends, arrows or latest-metric claims.
The zero-data state says **No health observations yet.** Loading and failures are
distinct from empty history. Navigation and explicit refresh load current owner data.

## 16. Health-history UI

`/history` adds manual entry, source/metric/date filters, selected-report filtering,
bounded page navigation and an inactive-record option. Cards show faithful raw value,
unit, measurement date/UTC time, status, personal review revision and source badge.
Details expose source report/page/quote, original machine value, retained revisions,
download and links back to reports. The report candidate panel provides explicit
publication after review, an optional confirmed day and a clear unknown-date choice.
Stale-publication errors instruct the user to refresh the latest review. Loading a
new filter clears the old filter's results; aborted/unmounted reads cannot repopulate
another account's UI. Focus refresh rechecks history rather than keeping stale data.

## 17. RLS and server security

Both tables have forced RLS, active-session checks and owner-derived SELECT policies.
No authenticated direct INSERT/UPDATE/DELETE is granted. Public RPC is an invoker
wrapper; private lifecycle code requires the existing worker secret and current owner
JWT, with an empty search path. Internal formatting and trigger helpers are not
callable by authenticated users. The BFF never uses service-role/admin credentials.
It checks explicit returned owner/resource relationships in addition to SQL owner
checks. Requests preserve rate, response-size, CSRF, no-store and HttpOnly boundaries.
No medical fields, source quotes, cookies, tokens or credentials are logged.

The existing Supabase [leaked-password-protection warning](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection)
remains. No new security-advisor findings were introduced. An unused Phase 5 actor
index is informational; it supports a foreign key and was retained.

## 18. Deletion and retention

Report deletion intent erases Phase 4 runs/pages and cascades Phase 5 candidates,
reviews, observation identities and snapshots in the same transaction. Deleted
derived data is inaccessible even if Storage cleanup remains pending. Manual data
survives deletion of unrelated reports. Manual deletion erases its snapshots without
affecting reports. Downloaded copies, provider backups and existing Phase 3 storage
cache/manifest limits remain outside immediate row deletion. Production retention,
backup erasure and legal requirements remain product/operator decisions; no regulatory
compliance claim is made.

## 19. Live two-user verification

The dedicated disposable accounts exercised actual upload → native extraction →
parameter extraction → review → publication. The final combined integration run
passed all seven tests in 399.74 seconds. It covers owner/cross-owner API and direct RLS access,
forged owner/value payloads, CSRF, duplicate concurrent publication, correction,
rejection, stale manual edits, exact units/qualitative values, UTC day boundaries,
dashboard count changes, report/manual cleanup and revoked sessions. Additional
regression includes concurrent review versus publication and 22 manual records
inserted in reverse measurement order to verify ordering and two bounded pages.
Fixtures contain only generated synthetic data and are cleaned up by owner APIs.
The dense observation suite waits for the existing 60-second account rate window
before later suites; no production rate limits were changed or reset.

## 20. Regression evidence

Baseline was verified before implementation: frontend 167 tests and build; backend
251 tests with real OCR evaluation; eight SQL scripts; five live suites.
Final local backend: **300 passed, seven opt-in live tests skipped, 34.64 seconds**;
Ruff, formatting (68 files) and mypy (65 source files) passed. The same two existing
Starlette/AnyIO deprecation warnings remain. All **ten SQL verification scripts**
passed after the final ordering migration, including duplicate source-evidence
publication and immutable snapshot checks. Frontend lint, typecheck, **199 tests
across ten files**, and the production build passed. The build contains 68 modules;
JavaScript is 358.82 kB (108.98 kB gzip), CSS 32.28 kB (7.83 kB gzip). The final
malformed-owner fail-closed guard also passed all 49 focused observation tests and
Ruff/format/mypy checks. All seven opt-in live tests passed separately, as above.

The Phase 6 Chrome acceptance script passed **12 groups**: explicit publication,
dashboard/history reload, evidence download, manual creation/correction, revisions,
desktop/mobile layout, correction/republication, stale two-tab publication,
report/manual deletion and logout. Desktop and 375-pixel mobile screenshots were
visually inspected; no horizontal overflow or JavaScript runtime errors occurred.
All earlier browser suites passed against this final build: Phase 2 authentication
and foundation navigation **15 groups**, Phase 3 private reports **11 groups**,
Phase 4 native extraction/real OCR **seven groups**, and Phase 5 candidate review
and provenance **eight groups**. Together with Phase 6, **53 browser groups passed**.
The prior checks cover access-cookie refresh, independent users, cross-tab logout,
private downloads, cancellation, encrypted-document retry and source-linked deletion.
No health fixtures remain from these successful runs. Migration filenames were
rechecked against the hosted migration history, and `git diff --check` passed.

## 21. Limits

- This is personal curation, not medical verification or a complete clinical record.
- No automatic date extraction, time inference, unit conversion, compatibility
  calculation, range evaluation, trend engine or AI context selection.
- Manual forms/display use UTC; calendar-only report dates retain their precision.
- Explicit republication is required after any review change, even a reconfirmation.
- Correcting a published report date requires a new review revision.
- Reprocessing across different text attempts/reports may create separately published
  records; there is no broad medical deduplication.
- Offset pagination can shift under concurrent writes; filters have a 10000 offset cap.
- Phase 5's 20-review cap and manual 100-revision/1000-identity caps have no reset UI.
- Phase 1–5 email delivery, OCR quality, development worker isolation, deployment,
  backup and retention limits remain documented in their original handoffs.

## 22. Phase 7 prerequisites and stopping point

Phase 7 is grounded educational report explanations. Before implementation, choose
the provider/model and approve data handling, evidence selection, quotas, failure
states and correction/deletion invalidation. Treat report text as untrusted input,
ground outputs in eligible observation/review snapshots, and evaluate abstention and
unsupported medical claims. No provider or Phase 7 code was added. Phase 8 remains
the separate deterministic trend phase. Stop after this handoff until a new explicit
instruction authorizes Phase 7.

## Manual acceptance

1. Start FastAPI and the Vite production preview using the README. Sign in with a
   confirmed development account. An empty account has real zero counts and no values.
2. Upload a permitted report. Extract text and parameters; inspect source evidence.
   Unreviewed candidates have no publication form and do not enter history.
3. Confirm or correct one candidate. Publish it, leaving the date blank unless known.
   Inspect the dashboard and Health history, refresh, and inspect its source/revisions.
4. Correct that review again. The old snapshot leaves active history; enable inactive
   history to inspect it. Publish the latest review and confirm one active replacement.
   Reject it and verify that it is excluded again.
5. Add a weight or heart-rate measurement with an explicit UTC time. Edit it and
   inspect both revisions. Try a stale edit from another tab: refresh after conflict.
6. Delete the report and verify derived history disappears while the manual entry
   remains. Delete the manual entry and verify counts/history update.
7. Check the same flows at a narrow viewport, then sign out. Another account cannot
   read, publish, edit or delete the first account's data.

## Reproducing the checks

From `frontend`, run `npm run lint`, `npm run typecheck`, `npm test` and
`npm run build`. From `backend`, using the existing environment and pinned OCR models:

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:RUN_OCR_EVALUATION='1'
$env:OCR_EVALUATION_MODELS='P:/Projects/SwasthyaLens/.cache/phase4/models-best'
.venv/Scripts/python.exe -m ruff check app tests
.venv/Scripts/python.exe -m ruff format --check app tests
.venv/Scripts/python.exe -m mypy app tests
.venv/Scripts/python.exe -m pytest
$env:RUN_SUPABASE_INTEGRATION='1'
try { .venv/Scripts/python.exe -m pytest tests/integration -q }
finally { Remove-Item Env:RUN_SUPABASE_INTEGRATION -ErrorAction SilentlyContinue }
```

The live suite requires both local servers and the existing ignored
`.env.integration` with dedicated disposable accounts. Run it alone. Execute all
ten `database/verification/*.sql` files as their complete rollback-only transactions.
From the repository root, run `node backend/tests/browser_observations.cjs` with
`PLAYWRIGHT_MODULE` pointing to the available Playwright module and Chrome installed.
The existing Phase 2–4 harnesses under ignored `.cache/qa` and
`backend/tests/browser_parameters.cjs` run sequentially against the production
preview. No application dependency was added for browser acceptance. Browser result
JSON and masked synthetic screenshots remain under ignored `.cache/qa/phase6`.

## File inventory

Created:

- `backend/app/{api,core,schemas}/observations.py`.
- `backend/tests/test_observations.py`, `backend/tests/integration/test_live_observations.py`,
  `backend/tests/browser_observations.cjs`.
- The three Phase 6 migrations and `database/verification/observations-{schema,lifecycle}.sql`.
- `frontend/src/features/observations/{ObservationCard,PublishObservation}.tsx`,
  `frontend/src/features/observations/useOwnedHistory.ts`, `frontend/src/pages/HistoryPage.tsx`,
  `frontend/src/services/observations.ts`, `frontend/src/services/observations.test.ts`.
- `docs/phase-6-decision.md` and this handoff.

Modified: backend app factory/provider safe errors; frontend routing/sidebar/safe
return destinations, candidate review/publication panel, dashboard, transport safe
errors and styles; root/database README and the generated-CLI cache ignore rule. Generated CLI temporary metadata was removed;
dependency manifests and locks are unchanged. Earlier browser harnesses stay in
ignored `.cache/qa`; their existing empty-dashboard assertion is updated to Phase 6's
real empty text, with the remaining assertions retained.

Suggested commit: `feat: add reviewed health observations, manual history and real dashboard`.
