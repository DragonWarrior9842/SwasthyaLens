# Phase 7 — grounded report explanations

Updated 24 September 2026 (Asia/Calcutta).
**Implementation verified; Gemini live-provider acceptance pending actual quotas.**
The owner confirmed the dedicated Gemini Free Tier project/key with Cloud Billing
unlinked. Their RPM/TPM/RPD entries were placeholders. No live Gemini request has
been made; no further OpenAI request is authorized or was made this turn.
Phase 7 is not declared complete. Phase 8 and Phase 9 have not started.

The earlier implementation checkpoints are `bde47ce`, `c2fad82` and `d48ff1e`;
the original provider/baseline checkpoint is `dda2176`. This working tree adds the
Gemini adapter and retains the existing OpenAI-compatible abstraction. See the
[current decision](phase-7-provider-decision.md) and
[setup/execution instructions](phase-7-gemini-setup.md).

## Architecture

An explicit authenticated POST selects current reviewed, published facts from one
owned uploaded report. The database locks the report, snapshots immutable source
revisions, checks synthetic enrollment, limits and idempotency, and reserves an
attempt. No database lock spans the provider request. The server independently
validates the response; the finish RPC rechecks the active session, ownership,
report status, enrollment and exact source snapshot before saving ready output.

The model selects enumerated educational wording and echoes exact facts. Only
server-owned catalog sentences are rendered after validation. There is no free-form
medical prose, diagnosis, treatment, triage, trend or assistant implementation.

- `backend/app/core/explanation_context.py`: facts, catalog, prompt, semantic validation.
- `backend/app/core/explanation_provider.py`: shared protocol/permit and dormant OpenAI adapter.
- `backend/app/core/gemini_explanation_provider.py`: separate Gemini REST adapter.
- `backend/app/core/explanations.py`: authorization, reservation, validation and lifecycle.
- `backend/app/schemas/explanations.py`: bounded typed contracts.
- `backend/tests/evaluate_explanations.py`: generated synthetic two-owner acceptance runner.
- `frontend/src/services/explanations.ts`: provider/model and fact/provenance checks.
- `frontend/src/features/reports/ReportExplanation.tsx`: consent, disclosure and rendering.

## Provider/model and settings

Current evaluation provider: **Gemini 3.8 Flash**, exact model `gemini-3.8-flash`,
Developer API Free Tier. This is an evaluation choice only, not a production
healthcare-provider decision. `GeminiSettings` reads ignored
`backend/.env.ai.gemini` with `AI_PROVIDER`, `AI_MODEL`, `AI_API_KEY`. The key is
passed only in `x-goog-api-key`, never URL, prompt, log, browser or artifact.
No `VITE_*` key exists. No new SDK dependency, configurable URL or fallback exists.

The historical OpenAI GPT-5.6 Terra adapter keeps its exact Responses contract,
model `gpt-5.6-terra`, separate `.env.ai` loader and in-memory contract tests.
Its real transport is blocked. `--live-openai` rejects before any network action.
The shared protocol and result type remain; permits add a default-zero Gemini
attempt ordinal, which Gemini requires to be 1–20 with zero paid reservation.

Gemini Free Tier may use submitted inputs and outputs to improve Google products
and machine-learning technologies, including human review. Only synthetic fixtures
are permitted. No patient data, zero-retention, residency or healthcare compliance
claim is made. The UI discloses these terms before consent.
[Google terms](https://ai.google.dev/gemini-api/terms).

## Context builder

Select 1–20 active report observations with a completed parameter run and latest
confirmed/corrected review. Explicit publication is required. Exclude unreviewed,
rejected, superseded, manual, foreign-owner and other-report facts. Empty or
oversized evidence never invokes a provider. Context is at most 32 KiB.

Each model fact has an opaque request-local alias `e1`–`e20`, exact label/value,
unit, supplied reference/flag, kind/comparator, canonical metric, page number and
`calculated_range_status: unknown`. Trailing zeros and missing values are preserved.
Source fields are untrusted data. The server-only map holds observation/review
revisions, candidate/run IDs and page spans. Account/report/observation UUIDs,
filenames, raw files/OCR pages, storage paths, symptoms, medication and history are
not in model context. Free-text labels are not guaranteed anonymized, which is why
this remains synthetic-only.

## Structured output and evidence validation

`ModelExplanation` requires `scope=educational`, 1–20 items,
`limitation=selected_findings_only`, `follow_up=professional_context`. Each item
contains a complete strict `ModelFact`, an enumerated explanation code and a
bounded note-code list. Extra properties are forbidden.

Gemini requests JSON Schema output. Its wire translator changes `const` to a
singleton enum and omits unsupported string pattern/length keywords; local strict
types, lengths, patterns and all semantic checks remain unchanged. There is no
prompt-only JSON fallback. Every fact must appear exactly once in order, with the
expected evidence ID and exact equality of every field. Definition code must match
the canonical metric; notes must be exactly the required unique set. Unknown,
missing, duplicate or foreign IDs, fabricated fields, ranges or measurements fail.

Only five general definitions (hemoglobin, TSH, vitamin D, glucose, CRP) have fixed
English wording and allowlisted MedlinePlus links. Unknown labels receive an
unsupported-definition notice. The application does not classify a value as
normal/abnormal; supplied flags are presented as source flags only.

Refusal, blocked/truncated output, multiple candidates, tool/code/file/thought
parts, grounding/URL metadata, wrong model version, malformed/oversized responses
and invalid usage are rejected. Ready records are validated again against current
source evidence before serving. Frontend validation rechecks facts, provenance,
versions and exact provider/model pairs; React escapes untrusted text.

## Prompt/version strategy

The unchanged semantic contract is `report-education-v1`, `closed-education-v1`,
`education-en-v1`. Every record stores these versions, provider and model. The
prompt is server-owned, marks document fields untrusted and forbids diagnosis,
new facts, searches and tools. Gemini transport/schema translation is adapter
code, not a relaxation of the shared semantic version. Each provider has one
allowed model; database constraints reject mismatched pairs. Cache reuse requires
owner/report/snapshot/provider, with model and all versions fixed by constraints.
Any future semantic/catalog/model change requires explicit versioning, migration
and fresh acceptance.

## Safety controls, live gates and budget

Gemini sends one text-only `generateContent` request with **`store=false` and
`tools=[]`**, no conversation history, explicit cached content, search, URL context,
provider file uploads, code execution or database/storage access. Current REST docs
document `store` as a logging control; this corrects the earlier setup note and
does not override Google's Free Tier data terms. Default safety filters remain.
[Request reference](https://ai.google.dev/api/generate-content).

`RUN_AI_INTEGRATION=1` is required by the adapter. The standalone runner also
requires `--live-gemini`, `--free-tier-confirmed` and actual numeric project quotas.
The current conservative minimum is 1 RPM / 57000 TPM / 2 RPD. Two case requests
are at least 61 seconds apart; any unsuccessful case stops the run. No model-access
probe or token-count call is made. Billing-unlinked status is owner-confirmed;
the application cannot independently guarantee the Cloud project's billing state.
No paid Gemini usage is authorized. Do not guess quotas or enable billing.

The applied forward migration `20260924080552_gemini_synthetic_explanations.sql`
adds an exact Gemini model pair and permanent private `gemini_attempts` counter.
It reserves before invocation and caps all Gemini attempts at 20, including
failures; deletion, invalidation, expiration and restarts never refund it. The
existing paid ledger remains 50 cents reserved of the $5 cap. It is not reset.
Gemini attempts remain **0**; zero new live-provider requests occurred this turn.

Normal pytest clears AI credentials/live flags and blocks both provider hosts at
the HTTP transport layer. Mock is the default standalone evaluation provider;
tests inject it explicitly. Application construction with explicit test settings
does not load either secret env file. Adapter tests use `httpx.MockTransport`.
The product never presents a mock as a live model result.

Before the first future Gemini request, report all six safeguards again: explicit
store=false, required live flag/CLI, active permanent attempt/paid safeguards,
only generated synthetic fixtures, no tools, and mock network isolation.

## Stale/invalidation and retention

Source review/observation changes atomically remove ready/generating output and
its stored evidence, mark stale, and remove enrollment. A late response is rejected
if the snapshot changed. Report deletion removes explanations/enrollment with the
existing cascade/deletion-intent handling. Ready application copies expire after
30 days; enrollment after 24 hours; interrupted generation after 90 seconds. The
hourly cleanup remains active. Application TTL makes no provider-retention promise.
The browser clears displayed output/consent on source events, focus and visibility
changes; refresh reads never generate. Provider changes also clear consent.

## API/UI

Authenticated GET `/reports/{report}/explanations` and GET with explanation ID
return only owned state. POST accepts the bounded idempotency/consent body;
callers cannot inject prompts, evidence or tools. The response includes the active
provider for accurate disclosure and stored provider/model metadata for results.
An explicit checkbox and Generate action are required. Expanding/polling/refreshing
the section only reads state; there is no automatic generation or retry.

UI shows eligible/unenrolled/disabled/generating/failed/stale states, exact values,
units, supplied references/flags and page/review/revision provenance. General
education links are allowlisted. Gemini results and deterministic mock results have
distinct correct labels. No health output enters browser persistent storage.

## Rate limits, timeouts, retries

Existing shared limits remain one active generation/user, two globally, three
new requests/minute/user and twenty/day/user. Report/global locks serialize
reservation, idempotency and concurrency across workers. Retained report records
are bounded to 20; cache/idempotency retention is finite. No lock spans network I/O.

Serialized request <=48000 bytes; response <=131072 bytes; maxOutputTokens=4000.
Gemini uses LOW thinking without thought text. Reported visible plus thinking
tokens must total <=4000 and are stored together as output usage; prompt tokens
<=53000 and total usage must reconcile. Five-second connect, forty-second I/O,
forty-five-second total provider timeout; browser generation timeout 65 seconds.
No automatic retries, redirects, proxy inheritance or provider fallback. Only
safe categories/counts/timing are logged; no prompts, raw responses or secrets.

## RLS/security

Only the existing `swasthyalens-dev` project (`rbmpfgndidpzdssiicyf`) changed. The
new migration was CLI-generated, applied through Supabase and renamed to its
hosted version. Eleven local/hosted migrations now match. No reset, new project or
service-role key was used; original migrations remain unchanged.

Forced owner/active-session/report RLS and authenticated SELECT-only grants remain.
Writes use the public invoker wrapper and private definer with empty search path,
worker-secret validation and explicit caller ownership. Budget/enrollment/attempt
tables stay private, forced RLS, no client privileges. CSRF, Origin/JSON protection,
HttpOnly cookies, revocation and two-user isolation remain enforced.

Security advisor has the existing
[leaked-password protection warning](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection)
and three intentional private default-deny
[no-policy informational notices](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy).
No new grants or relaxed RLS were introduced.

## Grounding, numeric preservation and adversarial results

The shared deterministic set covers 31 nonmissing observations including trailing
zeros, decimal/integer traps, comparators, qualitative values, titres, intervals,
ordinals, missing units/ranges, ambiguous OCR, unusual units, contextual ranges,
negative/zero values and injection strings. Exact echo checks reject altered
values/units/ranges/flags/IDs and invented diagnoses/history or unsupported codes.
Gemini mock-transport tests additionally reject blocked/truncated/multiple/tool/
code/file/thought output, grounding, wrong model and invalid token accounting.

The real two-owner **mock-AI** evaluation passed 15 synthetic findings and 18
security/lifecycle checks with zero critical grounding errors. Cases cover
13.20/132, 18/80, 2.4/24, <5, >10, 0.0050, supplied ranges/flags, qualitative/titre,
missing data and embedded instructions. Fixtures and derived records were deleted.
Existing unrelated uploaded reports were untouched and never enrolled.

**Live Gemini grounding, numeric fidelity, adversarial behavior, usage and latency
remain unmeasured.** Passing mock/SQL/browser checks does not establish live-model
acceptance. Gemini key presence/model selection were checked without exposing the
key; RUN_AI_INTEGRATION is unset and the runtime reports unavailable as intended.

Historically, two OpenAI attempts on 18/23 September failed authentication with no
accepted output or returned usage. Their $0.50 reservations remain conservative
reservations, not measured billing. OpenAI is now stopped; no further probes.

## Frontend/backend and regression results

Fresh verification of this Gemini implementation on 24 September:

- Focused backend explanation/provider/service suite: **70 passed**.
- Full backend with local OCR: **370 passed, 8 integration tests skipped**, 46.40s.
- Ruff, formatting (81 files), mypy (78 source files) and pip consistency passed.
- Frontend: **216 tests across 11 files passed**, ESLint/typecheck/build passed.
- Dedicated real Supabase two-user Phase 7 mock test: **1 passed**, 86.40s; includes
  both cases/15 facts/18 checks above. Both live AI hosts remained blocked.
- All **four Phase 7 SQL scripts passed** in rollback transactions: schema,
  lifecycle, limits and new Gemini limits. These prove the 20-attempt stop, replay,
  failure/deletion/cleanup nonrefund, model-pair constraint, paid-ledger preservation
  and no client counter reset. Test changes were rolled back.
- Phase 7 browser suite: **12 groups passed**, real authentication with synthetic
  routed responses and zero AI calls. Covers no page-load generation, consent,
  exact values/provenance, escaping/mobile layout, invalidation, malformed output,
  no retry, Gemini terms/provider-change consent reset and correct Gemini label.
- Final database check: zero explanation rows and zero enrollments; Gemini attempts
  zero and paid reservations unchanged at 50 cents. Both local test servers stopped.
- Git diff whitespace check passed; both provider env files remain ignored.
  Tracked-file secret-pattern scan found no matches; no key was printed or copied.
- Historical pre-Gemini baseline: 8 live Supabase integration tests, 13 SQL scripts
  and 63 browser groups passed on 23–24 September. Those complete older suites
  were not all rerun for this adapter change; the fresh scoped results are above.

Initial sandbox runs hit filesystem/application-control restrictions (pytest temp,
Vite/Ruff caches, mypy compiled module) and Supabase network denial. The authorized
outside-sandbox reruns passed. The new Gemini browser label assertion initially
failed because the rendered label still said OpenAI; the label was fixed and the
full twelve-group rerun passed. Existing Starlette/httpx/AnyIO deprecations remain.

## Reproduction and remaining live acceptance

Normal checks follow README. OCR evaluation uses RUN_OCR_EVALUATION=1 and the
baseline local `OCR_EVALUATION_MODELS` path. RUN_SUPABASE_INTEGRATION=1 enables
real backend integration tests with mocked AI. `python -m tests.evaluate_explanations`
from backend runs the synthetic flow with mock AI. Do not set the live flag for
normal tests. Browser checks use the local API/production preview and documented
Playwright module path. SQL verification scripts must run as complete transactions.
Sanitized result artifacts are in ignored `.cache/phase7` and `.cache/qa/phase7`.

Remaining input: **actual RPM, TPM and RPD from AI Studio for the dedicated project**.
Then re-report the six safeguards, run only the bounded Gemini synthetic evaluator,
stop on failure and update this handoff with measured acceptance results. The
owner has already authorized that scoped run; no additional general permission is
needed. If quotas/model access are insufficient, keep acceptance pending without
paid fallback or OpenAI retry. The key must remain local and must never be pasted.

## Known limitations

Live Gemini acceptance is pending. English and five fixed definitions are the
entire educational scope. No clinician-reviewed, production, real-patient,
multilingual or broader medical reasoning claim is made. Source flags/ranges do
not establish normality. Partial publication may not cover a whole report. Twenty
facts may exceed the output cap and fail safely; they are never silently truncated.
Project billing status depends on the owner's configuration. Provider-reported
model/version/usage must match strictly or the result fails closed. Existing
outbound-auth-email testing limitations and leaked-password warning remain.

## Suggested commit and Phase 8 preview

Suggested checkpoint commit:
`feat: add gated Gemini synthetic report explanation adapter`.
Do not describe this checkpoint as completed live acceptance.

Phase 8 would separately assess deterministic same-metric/unit/date-compatible
trends, preserving source revisions and showing insufficient/incompatible data.
That requires its own instruction and checks. **No Phase 8 work has started.**
