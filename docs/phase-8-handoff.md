# Phase 8 — deterministic measurement trends

25 September 2026. **Phase 8 implementation and acceptance complete.** Phase 9 is unstarted.
Phase 7 remains implementation-complete with live acceptance externally blocked by Gemini
503 availability; its 2/20 attempt ledger and disabled live-integration gate are unchanged.
No AI request, billing change, provider switch or AI credit spend occurred in Phase 8.

## 1. Architecture and trusted input

Authenticated GET → stable owner/RLS-scoped observation RPC → defensive validation →
pure Decimal analysis → structured response → strict frontend decoder → real-point chart,
exact table and neutral summaries. No trend tables, persisted snapshots, ORM, worker,
machine-learning package or generated explanation input was added.

`trend_rules.py` is independently testable without HTTP or database dependencies.
`trends.py` is the authenticated query adapter. Only active Phase 6 snapshots belonging
to the caller are accepted. Existing RLS also requires an uploaded parent report.
Raw OCR/candidates and reviews without explicit publication never enter calculations.
The app returns observation/revision/report/candidate/review provenance with each point.

The [pre-implementation rules](phase-8-rules.md) specify exact formulas, units and limits.
Versions are `trends-v1` and `correlations-v1`.

## 2–4. Files and database changes

Created:

- Backend `app/api/trends.py`, `app/core/trends.py`, `app/core/trend_rules.py`,
  `app/schemas/trends.py`; `tests/trend_fixtures.py`, `test_trends.py`,
  `test_trend_service.py`, `integration/test_live_trends.py`, `browser_trends.cjs`.
- Frontend `services/trends.ts`, `trends.test.ts`, `fixtures/trend.json`,
  `history-events.ts`; `features/trends/useTrend.ts`, `TrendView.tsx`, `TrendChart.tsx`.
- `database/migrations/20260924185746_deterministic_trends.sql`,
  `database/verification/trends-schema.sql`, `trends-lifecycle.sql`.
- This handoff and `docs/phase-8-rules.md`.

Modified: backend factory/router registration and bounded provider response handling;
frontend Trends/Dashboard pages, exact pinned package manifest/lock, styles,
observation/settings/report invalidation and owned-history hook; README/database README.
The existing observation browser harness has finer safe failure-stage diagnostics.

Migration `20260924185746` is applied to the existing development project. It adds two
partial indexes on active revision metric/unit + measurement date or instant and an
invoker `trend_context` RPC/private helper. Existing owner and unique-active indexes
remain. No existing migration was rewritten and no new table or credential was needed.
The CLI-created file was renamed to the actual hosted migration version.

## 5–7. Eligibility, dates, timezone and units

Supported canonical metrics: weight, heart rate, hemoglobin, TSH, unspecified Vitamin D,
unspecified glucose and CRP. A scalar must have numeric type, no comparator (including
`=`), no qualitative result and matching bounded finite decimal/raw representations.
Comparators, qualitative/titre/interval/ordinal/unparsed/missing values are excluded
from math and retained in health history. Supported exact unit spellings are listed in
the rules document. No conversion, guessed unit or implicit assay equivalence exists.

Manual UTC instants are assigned calendar days using the saved IANA account timezone.
Report measurement dates retain their supplied day; no midnight instant is invented.
Created/uploaded/inserted timestamps never substitute for measurement time. Unknown
dates have a separate count. Future instants and future end dates are excluded/rejected.
DST boundaries use local calendar midnights, not fixed 24-hour subtraction.

## 8–10. Seven/thirty-day and sparse behavior

For end day E, window W is [E-W+1,E], preceding window [E-2W+1,E-W]. Today includes
measurements so far and is labeled partial. Users can select a historical end date.
The API captures one request timestamp. Manual instant boundaries are half-open.

Weight/heart-rate reads cover exactly the two windows. Occasional labs use at most
366 calendar days ending at E for chronological/latest comparison; the chart still
shows only real points in the selected 7/30-day period. A January/April lab pair does
not become a daily trend, period aggregate or daily-coverage percentage.

Latest-versus-previous requires unambiguous observations on two separate latest days.
Multiple observations on either day produce an ambiguity reason; all points remain.
No earlier ambiguous day is skipped to manufacture a convenient pair. Percentage
change is omitted when the previous value is zero/negative. Older history remains
accessible through the existing paginated health-history view.

## 11–13. Aggregation, classification and insufficiency

For frequent metrics, each observed day's median contributes equally to the median
of daily medians. Missing days are not filled. Both periods require 4 observed days
for W=7, or 15 for W=30. Sample count, observed-day count and coverage are distinct.

Tolerance = max(1% × absolute previous period median, floor), with floors 0.1 kg / 1 bpm.
Delta within or equal to tolerance is stable; greater positive/negative delta is
increasing/decreasing. These are mathematical display rules, not clinical thresholds.
UI states that stable does not mean healthy/normal/safe and direction does not imply
improvement/worsening. No reference-range dataset or medical interpretation was added.

No numeric observations, insufficient current coverage, insufficient preceding coverage
and occasional-metric behavior are explicit reasons. Null summaries are never shown as
zero measurements. Input decimal spelling is preserved; differences/medians use exact
Decimal arithmetic. Derived percentages are half-even rounded to six decimal places.

## 14–18. Charts, patterns and correlations

Chart.js 4.5.1 is pinned. Only scatter/point/linear/tooltip modules are imported in a lazy
chart chunk (50.24 kB gzip in the measured build). No React wrapper/date adapter or full
visualization framework was added. The main bundle is approximately 117.36 kB gzip.
The [library requires an accessible canvas alternative](https://www.chartjs.org/docs/latest/general/accessibility.html);
the UI supplies an accessible name, text summary and keyboard-focusable exact table.
Chart positioning uses JavaScript numbers; authoritative arithmetic/text stays decimal.
Points share a calendar-day axis and may overlap; every original point stays in the table.
There is no connecting/interpolated line, fabricated day, hidden outlier or clinical band.

With sufficient days, consistent direction requires EVERY adjacent daily median to
exceed its tolerance in that direction. Stable sequence requires the entire daily-median
range to fit the tolerance; otherwise no clear pattern. Exact observed max-minus-min is
available with two values, without a medical/high-variability label.

No approved pair has both metrics in this catalog: sleep/activity do not exist. Product
correlations therefore return `unsupported_catalog`, no pairs and no invented numerical
association. The dimensionless primitive is tested with same-day median inputs, an inner
date join, at least 14 paired days spanning 14 calendar days, and Decimal Pearson:

`r = (N Σxy − Σx Σy) / sqrt((N Σx² − (Σx)²)(N Σy² − (Σy)²))`.

Constant series and insufficient pairs return explicit reasons. No lag/pair scanning,
missing-data imputation or strength/clinical labels exist. The UI places the association-
does-not-establish-causation disclaimer beside the unavailable correlation scope.
Enabling a real pair requires explicit product approval and compatible catalog support.

## 19–20. API, limits and security

| Route | Behavior |
| --- | --- |
| `GET /trends/catalog` | Current owned metric/exact-unit groups, saved timezone, correlation scope. |
| `GET /trends/{metric}?unit=kg&window=7d&end=YYYY-MM-DD` | Optional end day; strict 7d/30d, canonical metric and exact unit. |
| `GET /trends/correlations` | Explicit unsupported catalog and minimum/method/version metadata. |

Unknown query fields, including `user_id`, are rejected. All routes require verified
active sessions and a per-account 30 requests/minute process-local limit. No writes were
added; existing CSRF/Origin checks protect source mutations. Invoker RPCs retain RLS,
explicit owner scoping, active-session checks, empty search paths and restricted grants.
Anonymous/service-role execute grants are absent. No privileged API key is used.

Queries return at most 501 snapshots; the 501st causes an error rather than partial
statistics. Catalog groups are capped at 50. History is bounded to 14/60 days for frequent
metrics, 366 days for labs; no unbounded date-range API exists. The gateway caps this
RPC's response at 2.5 MB, uses the existing 10-second HTTP/5-second connect timeout and
no automatic retries. The browser's existing owned-read boundary applies its timeout
and session lock. No values, medical text or credentials are logged.

## 21–27. Verification and correction/deletion results

Before implementation: frontend 216 tests and all checks/build; backend 376 tests with
local OCR, Ruff/format/mypy; eight live Supabase tests; fourteen SQL scripts; all 65
established browser groups passed. Initial extraction startup and final observation
browser timeouts passed on isolated reruns; they were not counted as first-pass success.

Current verified results:

- Frontend lint/typecheck, **247 tests**, production build passed.
- Backend Ruff/format (**89 files**), mypy (**86 files**), **431 tests passed** with
  local OCR; nine opt-in live tests skipped only in that normal invocation. Two existing
  Starlette/AnyIO deprecation warnings remain.
- **All sixteen SQL verification scripts passed**, including invoker grants, exact unit
  and timezone bounds, A/B isolation, active-revision replacement, deletion and revocation.
- Fifty-five focused trend tests cover known 7/30-day results, increasing/decreasing,
  stability/noise, no/single values, sparse January/April labs, units, excluded scalar
  forms, duplicates, DST, extreme decimals, zero/negative denominators, correction and
  deletion, malformed/cross-owner responses, and positive/negative/zero/constant/missing
  paired synthetic statistics.
- New live acceptance verified distinct A/B results, 7/30-day behavior, only current
  revisions after edits, deletion, unreviewed/unpublished exclusion, report correction
  requiring republication, report deletion preserving unrelated manuals and revoked app
  reads. Its last direct-RPC assertion initially expected 401; Supabase returned the
  correct denied **403 / SQLSTATE 28000**. The test expectation was corrected.
- All **65 established browser regression groups passed**: auth/owned-state 15,
  reports 11, extraction 7, parameters 8, observations 12, mock explanations 12.
  Extraction again needed an isolated rerun after a startup sign-in timeout. The
  observation harness now awaits successful deletion and refreshed empty history before
  dashboard navigation; a mistyped harness empty-state assertion was corrected during
  verification. Final observation and explanation runs passed in full.
- Final full live integration acceptance: **9 passed in 468.53 seconds**, with two
  existing upstream deprecation warnings. This covers mock explanations, extraction,
  worker interruption/recovery, observation pagination and lifecycle, two-user
  authentication/profile/settings ownership, parameters, report storage, and trends.
  Trend acceptance confirms distinct A/B results, 7/30-day behavior, cross-owner denial,
  correction/republication, deletion preserving unrelated manual records, and revoked
  session denial through both the application and direct RPC.
- Earlier live invocations were interrupted by work pauses or encountered a stopped
  local API; they were not counted as successful runs. The final run started after
  verifying API health and completed with exit code 0. Its log is retained locally in
  ignored `.cache/qa/phase8/live-acceptance.log`. Integration flags are unset afterward.

Representative synthetic assertions (all passed):

| Fixture | Deterministic result |
| --- | --- |
| 7 prior days at 70.250 kg, 7 current days at 72.750 kg | Medians 70.250 / 72.750; delta 2.500 kg; 7/7 counts, 100.000000% coverage each; increasing. |
| Equivalent adjacent 30-day fixture | 30/30 counts and exact 30-day boundaries; same medians, delta and classification. |
| 100 followed by 101, tolerance 1 | Stable at the inclusive boundary; 101.000000000001 is increasing. |
| Sparse labs and same-day duplicates | Latest comparison only; duplicate latest/prior day is ambiguous, with all points retained. |
| Previous value zero or negative | Exact absolute change; percentage omitted. |
| Extreme supported decimal inputs | Exact difference 99999999999999999999.999999999998, without binary-float arithmetic. |
| Fourteen paired linear / inverse days | Pearson 1.000000 / -1.000000. |
| Symmetric nonlinear / constant / misaligned pairs | 0.000000 / constant-series reason / zero paired days. |

Phase 8 browser acceptance passed all **13 groups**, with synthetic source fixtures,
real authentication/API/OCR, cross-tab propagation, exact tables, 375px mobile layout,
read-error recovery, logout and zero AI requests. It exposed an ambiguous selector label
and a missing report-deletion invalidation signal; both were corrected before the full
passing run. The mobile harness now waits for responsive canvas resizing before checking
overflow. Desktop/mobile screenshots were visually reviewed in ignored QA artifacts.

Advisors found no new Phase 8 security issue. Existing findings are the
[leaked-password protection warning](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection),
three intentionally policy-free, nonexposed private Phase 7 tables (default deny), and
an informational [unused existing review-actor index](https://supabase.com/docs/guides/database/database-linter?lint=0005_unused_index).
The Phase 8 indexes are not flagged. No security setting was weakened to clear an advisor.

## 28. Manual acceptance

1. Start the API and production preview/development frontend using README. Leave
   `RUN_AI_INTEGRATION` unset. Open Trends after signing in.
2. In Health history add weight or heart-rate measurements with real measurement times;
   use synthetic values for evaluation. With only one day, expect insufficient data.
3. Add at least four observed days in each adjacent seven-day period; select the exact
   metric/unit and end day. Compare counts, medians and exact table against your entries.
4. Switch to thirty days: it requires fifteen observed days in each period, not fourteen
   measurements concentrated in fewer days. Missing dates are never plotted.
5. Review and explicitly publish a synthetic report value with a confirmed measurement
   day. Lab views show dated points and latest comparison without daily-coverage claims.
6. Correct a manual entry in another tab, then delete it. Correct a report review, confirm
   stale publication disappears, and explicitly republish. Delete the synthetic report;
   its points disappear while unrelated manual entries remain.
7. Inspect the exact table by keyboard and at 375px width. Refresh, change timezone in
   Settings, and sign out; protected data must clear. Correlations remain explicitly
   unavailable for the current catalog.

## 29. Known limitations and freshness

No enabled product correlation pair exists. Weight and heart-rate aggregation describes
submitted measurements only; timing/conditions/assay comparability is not established.
Lab history for latest comparison is limited to 366 days. Same-day ambiguity deliberately
withholds latest comparison even when some manual instants could be ordered more finely.
Capacity excess fails closed; there is no paginated partial aggregate or unit conversion.

Results are on-demand and no-store, held only in React memory. Local/BroadcastChannel
mutation signals clear data and cancel old reads. Focus, visible-tab reentry, manual
refresh and a 60-second visible-tab refresh handle other changes/day rollover. This is
not a server-push subscription: a change made outside the application can remain visible
until the next refresh, and a hidden tab rechecks when shown. There is no durable trend
cache. A request represents the transaction snapshot at its captured `as_of` time.

Rate limits are process-local; production needs shared enforcement and operational
monitoring. Existing authentication-email, OCR sandbox/quality, retention/storage-cache
and Phase 7 live-provider limitations remain. No production deployment/compliance or
hosted CI execution is claimed.

## 30–31. Suggested commit and Phase 9 preview

`feat(trends): add grounded deterministic metric history and bounded period comparisons`

Git staging/commits/publishing remain with the owner. Exclude populated env files,
credentials, generated builds and ignored QA artifacts.

Phase 9 would require a separately approved free-form assistant scope, provider/data-
handling decision and budget, bounded authorized context, evidence validation and an
adversarial evaluation plan. The Phase 7 external availability blocker remains unresolved.
No assistant implementation or live-provider retry is authorized by Phase 8.

**STOP after Phase 8 acceptance. Phase 9 requires an explicit new instruction.**
