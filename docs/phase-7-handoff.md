# Phase 7 — grounded report explanations

Status: **implementation checkpoint; Gemini Free Tier manual setup pending**.
Updated 24 September 2026 (Asia/Calcutta); resumed verification ran 23–24 September. The user committed the implementation checkpoint as
`bde47ce` and its documentation as `c2fad82`; the original provider-decision/baseline
checkpoint is `dda2176`.
Phase 7 is not declared complete. Phase 8 and Phase 9 have not started.

On 24 September the owner stated that funded OpenAI access is unavailable and
stopped all further OpenAI live requests, including probes. Only the live-provider
evaluation decision was reopened. Gemini 3.8 Flash Free Tier is the recommended
synthetic-only candidate, pending [manual setup](phase-7-gemini-setup.md) and the
separate adapter work in the [current provider decision](phase-7-provider-decision.md).
No Gemini call, adapter change or migration has occurred. The implementation and
test evidence below describe the existing OpenAI-compatible checkpoint; they do
not establish Gemini acceptance or authorize another OpenAI request.

## Architecture

An explicit authenticated POST selects active, reviewed, published observations
from one owned uploaded report. PostgreSQL snapshots their immutable revisions,
checks synthetic enrollment, enforces rate/concurrency limits and reserves cost
before the server invokes a provider. No database lock spans the network request.
The server validates the result against the exact snapshot and finishes through
an RPC that rechecks the session, report status and current source revisions.

The model selects from a closed educational vocabulary and echoes source facts.
The application renders fixed catalog sentences only after validating every echo,
code and note. There is no unrestricted medical prose, diagnosis, treatment,
triage, trend calculation, chat or free-form prompt input. This deliberately
bounded design provides enforceable output limits; it is not evidence of broad
medical reasoning ability or clinical validation.

Main implementation files:

- `backend/app/core/explanation_context.py`: context, catalog, prompt and semantic validation.
- `backend/app/core/explanation_provider.py`: fixed OpenAI Responses adapter.
- `backend/app/core/explanations.py`: authorization, reservation and generation lifecycle.
- `backend/app/schemas/explanations.py`: bounded typed input/output contracts.
- `backend/app/api/explanations.py`: authenticated API routes.
- `frontend/src/services/explanations.ts`: browser response/provenance validation.
- `frontend/src/features/reports/ReportExplanation.tsx`: explicit consent and explanation UI.
- `database/migrations/20260918051920_grounded_explanations.sql`: applied development migration.

## Provider/model and configuration

Implemented evaluation adapter: **OpenAI GPT-5.6 Terra**, API model
`gpt-5.6-terra`. This is an evaluation choice only, not a permanent production
healthcare-provider decision. The server uses existing pinned `httpx==0.28.1`;
there is no new SDK dependency, provider fallback or browser-selectable endpoint.

`backend/.env.ai` contains `AI_PROVIDER`, `AI_MODEL` and `AI_API_KEY`. It is ignored
by Git; `backend/.env.ai.example` contains only names and an empty key. The AI
settings loader is separate from the existing backend settings. Secrets stay
server-side and are never sent to the model or copied into browser configuration.
**No `VITE_*` variable contains or requires an API key.**

The process environment must have `RUN_AI_INTEGRATION=1` for the real adapter to
be available. The standalone evaluator additionally requires `--live-openai`.
Tests with explicit application settings never load the real `.env.ai` file.
The mock exists only in test code and is injected explicitly; the product never
substitutes a mock explanation while claiming a real OpenAI result.

A valid existing OpenAI key with the necessary project/model/Responses access can
work. A dedicated restricted SwasthyaLens project key remains preferable for
separate permissions, billing and revocation. Account/project access and provider
spending settings are not established merely by storing a key locally.

## Context builder

The server selects 1–20 active report observations with the latest confirmed or
corrected review and a completed parameter extraction. Unreviewed, rejected,
superseded, manual, foreign-owner and other-report observations are excluded.
Review alone is insufficient: explicit publication is required. Empty or oversized
evidence produces no model call.

Each fact has a request-local opaque ID `e1` through `e20`, its exact reviewed
label/value/unit/reference/printed flag, value kind/comparator, canonical metric,
page number and `calculated_range_status: "unknown"`. Input strings are never
instructions. All supplied spelling, trailing zeros and missing values are kept.

The server-only source map links each alias to observation/review revisions,
candidate, parameter/source run and page offsets. No account/report/observation
UUID, patient identifier, filename, file bytes, raw OCR page, source quote,
measurement date, symptom, medication, history, credential or storage path is
included in model context. Authorized provenance is returned to the owning UI.
Free-text fields could contain identifying material, so this is minimization,
not guaranteed anonymization; this phase therefore permits only synthetic fixtures.

## Structured output schema and evidence validation

`ModelExplanation` requires `scope: educational`, 1–20 items,
`limitation: selected_findings_only` and `follow_up: professional_context`.
Each item requires one complete `ModelFact`, an enumerated `explanation_code`,
and a bounded list of enumerated note codes. Extra properties are forbidden.
The request specifies strict JSON-schema structured output.

Validation requires every fact exactly once in the same order, the exact expected
opaque evidence ID and exact equality of every echoed field. Unknown, duplicate,
missing or foreign IDs fail. A definition code must match the fact's authorized
canonical metric. Notes must be exactly the required unique set: supplied/missing
range, missing unit, source flag, comparator and nonnumeric-result cautions as
applicable. A valid JSON shape alone does not pass these semantic checks.

Only five supported general definitions (hemoglobin, TSH, vitamin D, glucose and
CRP) have catalog wording. Unknown/ambiguous labels get an explicit unsupported
definition notice. General definitions were checked against the linked NLM
MedlinePlus pages; this is engineering review of educational wording, not a
clinician's review of a patient's result. The model cannot add a measurement,
range, medication, symptom, diagnosis, history or arbitrary explanation sentence.

Refusals, incomplete output, additional tool messages, malformed responses,
unsupported codes, oversized bodies and incorrect usage metadata fail closed.
Persisted ready output is validated again against current evidence before serving.
The frontend also checks fact/source equality, IDs, revisions and a strict
allowlist of MedlinePlus links. React renders untrusted labels as escaped text.

## Prompt/version strategy

Versions are `report-education-v1` (prompt), `closed-education-v1` (schema), and
`education-en-v1` (wording catalog). Each record stores all three plus provider and
model. Instructions are server-owned; report fields are explicitly untrusted data.
The fixed prompt forbids diagnosis, treatment, tools, searches, inferred history,
new measurements and range calculations. English is the only accepted language.

Changing any contract/catalog/model requires an explicit version/migration and
fresh acceptance evaluation. Current SQL constraints and response checks require
these exact versions. Reuse requires the same owner, report snapshot and provider;
model, language and versions are fixed for this phase.

## Safety controls and budget

Every generation explicitly sends `store=false`, `stream=false`,
`background=false`, `tools: []`, `tool_choice: none`,
`parallel_tool_calls: false`, default service tier and no reasoning effort.
There is no runtime web search, file search, code execution, model tool, database
access or storage access. The endpoint is fixed to OpenAI Responses; redirects,
environment proxy configuration, automatic retries and fallback are disabled.

Before the first real request, all six required safeguards were verified and
reported to the user. The applied private database ledger started at zero and
permanently reserves **$0.25 before each OpenAI attempt**, with a cumulative
**$5 hard cap**. Reservations are never refunded by failure, deletion, expiry or
restart. At most 20 real attempts can pass this phase's ledger. The rollback-only
SQL limit test verified rejection at 500 cents without changing the live balance.

The 48,000-byte request cap plus a conservative 5,000-token framing allowance,
input priced at $2.50/M including cache-write premium, and 4,000 output tokens at
$12/M gives a conservative token-cost estimate below $0.181 per request, under
the $0.25 reservation. Prices were rechecked on 23 September against the
[model specification](https://developers.openai.com/api/docs/models/gpt-5.6-terra).
The limit concerns evaluation model usage; taxes/FX/account-wide unrelated usage
are not measured by this application. Recheck pricing before extending evaluation.
Do not reset the ledger to obtain additional attempts.

Provider project spending enforcement is additional protection; its configuration
was not independently verified. `store=false` does not promise zero provider
retention, residency, a BAA or healthcare compliance. Standard safety logs and
feature caching have separate policies described in the
[provider data controls](https://developers.openai.com/api/docs/guides/your-data).

## Staleness, deletion and retention

Changes to observation revisions atomically invalidate generating/ready report
explanations, erase their output and evidence snapshot, and revoke enrollment.
Corrections/rejections therefore cannot leave old model content readable through
the Data API. Republication requires a new matching synthetic enrollment before a
new evaluation. Finishing a request rechecks the source fingerprint and cannot
resurrect a result invalidated while the network request was in flight.

Report deletion intent physically removes explanations and enrollment immediately,
including when original-file cleanup remains pending. Report/account foreign keys
also cascade derived records. The global spending ledger survives deletion.

Records are invisible after a 30-day TTL and physically removed by an hourly
`pg_cron` job; physical expiry may lag the TTL by up to an hour. At most 20 records
are retained per report. Synthetic enrollment expires after 24 hours. Abandoned
generations become failed after their 90-second deadline on access or cleanup.
Rate-attempt metadata is pruned after 25 hours. Cleanup was verified directly in
rollback tests, and the scheduled job was observed succeeding on 18 September at
10:17 UTC. A missing scheduler must be treated as a retention incident.

The browser clears/refetches on same-tab and cross-tab source-change notifications,
focus/visibility changes, and 15-second status refreshes while expanded. No model
generation is triggered by these reads. Already rendered content cannot be
retroactively removed from a disconnected device; the server remains authoritative.

## API/UI implementation

- `GET /reports/{report_id}/explanations`: current eligibility/latest record.
- `GET /reports/{report_id}/explanations/{id}`: a specific owned record.
- `POST /reports/{report_id}/explanations`: explicit `consent: true` and nonzero
  UUID idempotency key. No prompt, facts, owner, model or provider is accepted.

There is no HTTP route for synthetic enrollment. Only the trusted evaluator can
call the worker-guarded RPC with its newly generated file digest and independently
assembled exact published evidence snapshot. The runner accepts no arbitrary file,
report ID or model argument. Storing a key alone cannot enable ordinary reports.

The Reports accordion starts closed and does not fetch or generate on page load.
It explains the third-party transmission and educational scope before a consent
checkbox and explicit Generate action. Empty/unpublished/unenrolled/disabled,
in-progress, failed and stale states are distinct. Saved results show exact values,
supplied references/flags, page/review/observation provenance, authorized history
links, general education sources, provider and timestamps. Mock results are clearly
labelled as tests. Original facts remain authoritative and unchanged.

## Rate limits, timeouts and retries

The shared database enforces one active generation per user, two globally,
three new generations/minute/user and twenty/day/user, across server workers.
An atomic report lock and global reservation lock serialize cache/idempotency,
rate and cost decisions. Existing authentication/report limits remain in force.
Identical request keys and unchanged ready snapshots return existing records.
Retained-record eviction/TTL bounds idempotency retention; it is not permanent.

Context is capped at 32 KiB; serialized provider request at 48 KB; output at 4,000
tokens and 128 KiB response bytes. Connect timeout is five seconds; provider I/O
timeout forty seconds; overall generation forty-five seconds. The browser allows
65 seconds for the generation response. There are **zero automatic paid retries**.
Network ambiguity is recorded conservatively; it is not claimed to be exactly-once
provider billing. A user explicitly retries after a failed generation.

Only safe categories, counts, provider/status and timing are logged. Provider error
bodies, prompts, responses, health values, credentials and access tokens are not
logged. Local evaluation accounting contains safe synthetic-case metadata only.

## RLS/security

The migration was generated with the Supabase CLI and applied only to the existing
`swasthyalens-dev` project (`rbmpfgndidpzdssiicyf`). Its filename matches hosted
migration history. No reset, new project or service-role key was used.

`report_explanations` uses forced owner/session/report-lifecycle RLS and SELECT-only
authenticated grants. All writes pass through a public invoker wrapper into a
private definer function with empty search path, verified active JWT session,
worker secret and explicit report ownership. Budget/enrollment/rate tables are
private, forced RLS and default-deny, with no client table privileges. The model
never sees any of these credentials or objects.

CSRF, Origin/JSON protection, HttpOnly cookies, session revocation and two-user
isolation remain enforced. Browser requests keep account checks and the existing
cross-tab session lock. No health result enters browser persistent storage.

The advisor retains the existing
[leaked-password protection warning](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).
Three new private tables produce informational no-policy notices intentionally:
they are default-deny and only accessed by guarded definer code. New indexes can
also appear as unused during development. No production compliance claim is made.

## Grounding, numeric preservation and adversarial results

The deterministic fixture set covers 31 nonmissing observations: decimal/trailing
zero and integer traps, comparator results, qualitative values, titres, intervals,
ordinals, missing units/ranges, unknown labels, ambiguous OCR characters, unusual
units, contextual ranges and negative/zero values. All echoed values, units,
references and provenance were preserved in focused tests. Corrupted values,
units, ranges, flags, labels, metrics, pages, comparisons and IDs were rejected.

Prompt-injection strings remained source data. Tests reject invented diagnoses,
additional history, wrong definition codes/notes, duplicate/missing/foreign evidence,
refusal, incomplete output, tool messages, malformed/oversized responses and timeout.
These results establish deterministic guard behavior, not live-model quality.
The two-user mock evaluation additionally used 15 synthetic findings, including
13.20/132, 18/80, 2.4/24, <5, >10, 0.4–4.0/30–100, source flags, qualitative/titre,
missing-unit/range and embedded instruction cases. No critical grounding error
occurred in the accepted mock results.

## Live OpenAI result and remaining acceptance gate

Two real Responses attempts have been made after their six-safeguard reports,
on 18 and 23 September 2026. Each failed with the safe `authentication` category;
no explanation was saved. Each synthetic case contained eight findings. The
first server round trip was 4,016 ms and the resumed attempt was 1,140 ms; no
usage tokens were returned. On 23 September, a non-generating model-metadata
check again returned **HTTP 401, `invalid_api_key`**. The effective key matched
`backend/.env.ai`, with no process override or surrounding whitespace. No key
or raw error body was printed, logged or copied. No blind generation retry was
made; the second fixture was not sent after the first fixture failed.

The two failed attempts retain **$0.50 cumulative reservations out of $5**. This
is reserved budget, not measured billing; the ledger was not reset. Successful
live grounding, numeric fidelity, prompt-injection behavior, model access and
token-cost/latency distribution remain **unmeasured**. Failed authentication
round trips are not model latency; no p50/p95 or live quality success is claimed.
OpenAI live work is now stopped by the owner. The replacement Gemini setup,
adapter validation and synthetic live acceptance must be completed before Phase 7
can be signed off. Do not retry OpenAI to satisfy this gate.

## Test and regression results

Fresh verification on 23–24 September 2026 against implementation `c2fad82`,
with a final Reports-page copy correction:

- 39 focused backend explanation/adapter/service tests passed.
- Full backend regression with local OCR: **339 passed, 8 live tests skipped**,
  40.61 seconds. The skipped tests were run separately below.
- Backend Ruff and formatting passed (79 files); strict mypy passed (76 source
  files); dependency consistency passed.
- Frontend: **215 tests across 11 files passed**; ESLint, TypeScript and production
  build passed. Lint/build were repeated successfully after the copy correction.
- Real Supabase integration: **8 passed in 422.79 seconds**, including the Phase 7
  deterministic mock evaluation, ownership/session revocation, private storage,
  worker-death recovery, extraction, review, publication and observation lifecycle.
- Phase 7 mock evaluator: two real owners, 15 synthetic findings and **18
  security/lifecycle checks** passed with zero critical grounding errors and zero
  OpenAI usage. Created reports and derived explanations were deleted afterward.
- **All 13 SQL verification scripts passed** as complete rollback transactions.
  Ten local migration versions match hosted migration history. The retention job
  is active and its latest observed run succeeded. The final database check found
  zero explanation rows and zero synthetic enrollments; the budget remains 50 cents.
- Browser regression: **63 groups passed** against the final production build:
  authentication/foundation 15, reports 11, extraction 7, parameters 8,
  observations 12, explanations 10. Suites ran sequentially with live AI disabled.
  The Phase 7 suite uses synthetic routed contracts with real authentication and
  verifies consent, no page-load generation, gates, exact values/provenance,
  HTML escaping, mobile overflow, invalidation, rejected output and failure states.
- Tracked-file secret-pattern checks printed no matches; the frontend contains no
  `AI_API_KEY` reference, `backend/.env.ai` remains ignored, and `git diff --check`
  passed. No credential value was printed or copied into an artifact.

The first resumed integration run started before the required loopback API was
ready: four tests passed and four failed setup with connection refusal. After
starting the API, the full eight-test run above passed without test/application
changes. This setup mistake is not counted as an application failure or a clean
first run.

The original ignored authentication browser harness timed out twice because it
assumed Reports must be empty. The dedicated account has one pre-existing uploaded
report. It was left untouched and was never enrolled or sent to OpenAI. An ignored
wrapper, `.cache/qa/phase2/browser-auth-owned-state.cjs`, now compares report row
counts and headings against the owning API response, requires the empty message
only when that response is empty, and preserves all other auth/isolation checks.
Its complete 15-group rerun passed. The fixture-aware assertion change is not
claimed as a pass of the original empty-only assertion.

The Reports page and README previously said AI explanations were unimplemented.
Their copy now accurately describes the bounded synthetic-only feature and its
pending live acceptance. No model, schema, migration or safety boundary changed.

The earlier 18 September OCR run initially omitted `OCR_EVALUATION_MODELS`; its
corrected 61-test rerun passed. Existing Starlette/httpx/AnyIO deprecation warnings
remain. The Supabase leaked-password warning and three intentional private-table
no-policy informational notices are unchanged. Live OpenAI quality remains blocked
as described above; passing mock, SQL and browser checks does not replace it.

## Reproduction

Use the usual frontend and backend checks in the README. OCR opt-in additionally
requires `RUN_OCR_EVALUATION=1` and the baseline
`OCR_EVALUATION_MODELS=P:/Projects/SwasthyaLens/.cache/phase4/models-best`.
`RUN_SUPABASE_INTEGRATION=1` enables the real two-user database/API suites, with
the Phase 7 provider still mocked and OpenAI transports blocked by pytest.

Run `python -m tests.evaluate_explanations` from `backend` for the mock synthetic
flow. The historical `--live-openai` runner remains in source behind the persisted
reservation path, but its execution is no longer authorized. Gemini's live command
does not exist yet; follow the manual setup gate rather than running either live
provider. The normal pytest
fixture clears AI credentials/live flags and blocks real OpenAI HTTP transports.
Provider adapter tests use in-memory `httpx.MockTransport` only.

Run all `database/verification/*.sql` as complete rollback transactions. Run
`backend/tests/browser_explanations.cjs` with the documented Playwright module and
local API/preview servers. The Phase 1–6 browser commands are in the baseline;
use the owned-state authentication wrapper described above when the dedicated
account has existing reports. Start both servers before the live HTTP suites.
Sanitized local result artifacts are under
`.cache/phase7` and `.cache/qa/phase7`; no credentials are committed.

## Known limitations

Live provider acceptance is pending the Gemini setup gate described above. English and five fixed
general definitions are the entire initial educational scope. No clinical,
multilingual, patient-report or production-provider validation is claimed. A
20-fact request may reach the output-token cap and fail safely; it is never
silently truncated. Classification remains unknown even when a source range or
flag is available. Publication can cover only part of a report.

The active synthetic-only gate is intentional; ordinary user reports cannot be
sent to OpenAI. Production use requires a separately authorized provider/privacy,
contract, retention and safety decision. The earlier outbound-auth-email testing
limitation and leaked-password-protection warning remain unresolved.

## Suggested commit and Phase 8 preview

Suggested commit for this resumed checkpoint:
`fix: align Phase 7 copy and refresh acceptance evidence`.
After successful live acceptance, the overall feature commit can use
`feat: add grounded synthetic report explanations`.
Do not label this checkpoint as completed live OpenAI acceptance.

Phase 8 would separately define deterministic same-metric/unit/date-compatible
trends, preserve source revisions, distinguish manual/report origins and surface
insufficient or incompatible data without inventing classifications. That design
requires its own instruction and checks. **No Phase 8 implementation was started.**
