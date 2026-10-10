# Phase 7 — grounded report explanations

## Current live acceptance — Gate I, 2026-10-04

**PASS: one persisted synthetic Phase7 lifecycle through OpenAI / `gpt-6.1-sol`.** One expressly authorized request returnedHTTP200 with the exact model confirmed:1242 input +122 output =1364 tokens, estimated$0.003704. The real report upload/extraction/review/publication and reservation supplied the minimized evidence; no prompt facts were manually seeded. Structured/evidence/safety validation, owner/report/reservation/evidence/version persistence and identical reload passed. Reload caused0 requests. Normal correction made the source superseded and the explanation stale; deletion, direct fact/revision absence, unrelated manual preservation and foreign-user read/mutation denials passed without regeneration.

The fixture supplied no clinical date; none was fabricated. Phase7 language metadata is the fixed English catalog `education-en-v1`, preserved with prompt/schema versions; no separate multilingual acceptance is claimed. Exactly1 new OpenAI request, total**3**. Gemini remains**2/20**, both historical503. Retries0, fallbacknone; gate unset, acceptance process exited, cleanup passed. Internal reservations125→150 cents, with no refund/reset; this is not provider billing. Final DB counts:0 explanations/enrollments and0 facts/revisions for deleted reports. The one-request authorization is consumed. No further call, normal AI enablement or Phase14 work is authorized.

Fresh pre-dispatch regression:100 targeted backend tests passed; Ruff/123-file formatting passed; existing Windows Application Control/mypy blocker unchanged. Gate H's full offline/UI/SQL results remain evidence, not rerun results. [Full Gate I report](openai-acceptance-2026-10-03.md#gate-i--one-live-persisted-phase-7-lifecycle-passed). This completes the bounded synthetic English live lifecycle gate, not production/broader release-scope acceptance. Phase13 can proceed to final closure work, with existing release blockers recorded separately.

## Historical preparation outcome — Gate H, 2026-10-04

**Full offline Phase 7 lifecycle PASSED; ready for one separately authorized live OpenAI request. No live request was made.** The harness now expects404 for deleted-report observation reads and independently checks fact/revision rows through authenticated owner-scoped Data API access. Application/API behavior was not changed. Both owner cases completed upload/extraction/review/publication, exact selected-model reservation, bounded deterministic generation, validation/persistence/reload, correction/stale/superseded exclusion, deletion, direct deleted-fact/evidence checks and unchanged unrelated manual observations. Both directions of read/mutation isolation passed. Deleted source IDs cannot regenerate or republish.

Backend **270 passed / 2 gated OCR skips**; frontend **111 service tests plus 13 browser UI groups passed**, including explanation removal after deletion. Six rollback SQL scripts passed, including RLS/ownership/deletion/nonrefund checks. Ruff/format/frontend lint/typecheck passed; mypy remains blocked by Windows Application Control and was not rerun. Final provider boundary passed: correct owner/current reviewed facts, exact `openai` / `gpt-6.1-sol`, opaque minimized context, no credentials/tools/retries/fallback, mock blocked when live gate set, real transport locked with zero dispatches.

Internal reservation bookkeeping moved75→125 cents for two mock generations; actual provider spend was0. Reservations permanently consume conservative cap capacity and are not measured billing; deletion/cleanup deliberately do not refund. Release environments reject injected providers. No ledger reset or refund occurred. Cleanup passed; no explanation/enrollment rows or facts/revisions for deleted reports remain. OpenAI **2 total**, Gemini **2/20** historical503, `RUN_AI_INTEGRATION` unset, Phase14 unstarted. Actual persisted Phase7 live acceptance is still pending explicit authorization. [Gate H evidence](openai-acceptance-2026-10-03.md#gate-h--full-offline-phase-7-lifecycle-passed).

## Historical preparation outcome — 2026-10-04 18:40 Asia/Calcutta

**Migration applied and verified; full mock lifecycle FAILED; NOT READY for a live request.** After Gate F restored the read-only baseline, the unchanged prepared migration was applied through the normal Supabase migration service. Its assigned version is `20261004130141_explanation_model_metadata` (prepared as `20261004070111`); the local filename is aligned. Data fingerprints were preserved at application, forced RLS/grants/security fingerprints are unchanged, and all seven relevant rollback SQL scripts passed.

Gate G's real application/Storage/DB workflow with deterministic generation reached exact `openai` / `gpt-6.1-sol` reservation, validated persistence/readback, correction, stale invalidation, superseded exclusion and owner report deletion. It then stopped at `deletion_and_manual_preservation` / `deleted_observations_http_404`: the harness expected an empty 200 response where the existing deleted-report contract requires 404. Manual-data preservation and the reverse owner case were not reached; full two-user/deleted-evidence acceptance is incomplete. Minimum correction: fix the harness expectation, independently check absence of report-derived rows using owner-scoped access, retain the manual-preservation assertion, and rerun only after continuation. No application authorization weakening is indicated; no correction or rerun followed the stop.

Backend **265 passed / 2 gated OCR skips**, frontend **18 explanation service tests passed**, Ruff/format/frontend lint/typecheck passed; browser UI checks were not reached. Mypy remains blocked by Windows Application Control, not rerun. Cleanup passed; zero explanation/enrollment rows remain. The mock reservation consumed 25 cents of internal reservation bookkeeping (now 75 cents), **zero provider spend**; ledgers were not reset/refunded. OpenAI **2**, Gemini **2/20** historical 503s, gate unset, Phase 14 unstarted. [Full Gate G report](openai-acceptance-2026-10-03.md#gate-g--migration-applied-mock-lifecycle-stopped). Earlier dated checkpoints below describe their historical state.

## Historical preparation outcome — 2026-10-04 17:36 Asia/Calcutta

**STOPPED / NOT READY FOR LIVE REQUEST.** Gate E's read-only Supabase baseline timed out at `migration_review_readonly_baseline` (`database_connection_timeout`). Local migration inspection found the intended metadata-only compatibility changes, but deployed RPC/security/data comparison could not complete. No migration application or database mutation was issued; `20261004070111_explanation_model_metadata` remains unapplied. Full mock lifecycle, security SQL and post-migration regression were not reached. Previous Gate D BE120/FE18 results remain historical, not new verification. OpenAI total **2**, Gemini **2/20** unchanged; gate unset. Mypy blocker preserved. Restore database connectivity and repeat baseline before continuing preparation; no AI request is authorized. [Gate E report](openai-acceptance-2026-10-03.md#gate-e--preparation-stopped-on-database-baseline-timeout). Phase 7 full lifecycle remains pending; Phase 9's bounded PASS remains unchanged.

## Latest Phase 7 preflight stop — 2026-10-04

**Full persisted live lifecycle remains PENDING.** The newly authorized run stopped before OpenAI at model-metadata preflight: Phase 7's applied database reservation/constraint and readers still assumed `gpt-5.6-terra`, incompatible with the selected `gpt-6.1-sol`. No synthetic report/session/provider request was started. Per the user's offline-failure rule, only the minimal local repair and targeted tests were completed: configured model carried into reservation; mismatched reservation rejected before invocation; selected and historical exact model pairs retained in readers. **120 backend and 18 frontend tests passed**, backend Ruff and frontend lint/typecheck PASS. Full report-to-deletion preflight has not yet been completed.

Migration `20261004070111_explanation_model_metadata.sql` and rollback verification are **prepared, not applied/executed**. Existing remote RLS/grants/RPCs and ledgers are unchanged. OpenAI total **2**, Gemini **2/20** (both 503), no new cost, gate unset. Phase 9 Gate C PASS remains valid. Mypy remains blocked by Windows Application Control. No post-correction second call is currently required by the existing evaluator; the first persisted Phase 7 generation remains outstanding. See [Gate D's complete result](openai-acceptance-2026-10-03.md#gate-d--phase-7-offline-preflight-stop). Earlier dated records below remain historical. No automatic continuation into live acceptance or Phase 14.

## Latest persisted assistant result — 2026-10-04

The newly authorized **Phase 9** rerun passed one real persisted synthetic turn, readback and A/B isolation: OpenAI / `gpt-6.1-sol`, HTTP 200, 551 input + 54 output tokens, estimated $0.001642. Total OpenAI requests are now **2** (A=1, B=0, C=1); Gemini remains **2/20**, both 503. Phase 7's isolated adapter PASS is unchanged; **full persisted Phase 7 report-explanation acceptance remains pending** because it is a separate lifecycle. Cleanup passed and the live gate is unset. Earlier dated entries below are preserved history. See [Gate C](openai-acceptance-2026-10-03.md#gate-c--authorized-persisted-phase-9-rerun-passed).

## Persisted-gate follow-up — 2026-10-04

The separately authorized Phase 9 persisted run stopped during synthetic report preparation on 2026-10-03 at 23:42 Asia/Calcutta, **before any new OpenAI request**. Gate 1's direct adapter PASS below is unchanged. Total OpenAI requests remain **1**; Gemini remains **2/20**. Full persisted Phase 7 acceptance is still pending. Cleanup passed, the live flag is unset and no acceptance process remains. A public-observation ownership-check defect was identified and corrected offline; no automatic rerun occurred. See the [separate Gate 2 record](openai-acceptance-2026-10-03.md#gate-2--persisted-phase-9-flow-stopped-before-openai).

## Current OpenAI acceptance update — 2026-10-03

**One explicitly authorized synthetic OpenAI / `gpt-6.1-sol` request PASSED (HTTP 200).** Exact response model, strict schema, opaque evidence ID, `18`, `ng/mL`, `30–100`, and the closed educational safety contract all passed. OpenAI live acceptance attempts: **1**; retries: **0**. Usage: 1,242 input / 122 output tokens; estimated standard cost $0.003704.

This verifies the Phase 7 adapter for one in-memory synthetic fixture using the existing fact/validation pipeline. **Full persisted Phase 7 live application acceptance remains PENDING**: no database/Storage, enrolled report lifecycle, API/UI or source invalidation was exercised in this authorized run. Phase 9 remains locked and unverified. Normal defaults remain unchanged; `RUN_AI_INTEGRATION` is unset, no acceptance process remains, and the key remains private/ignored/untracked. Offline regression: 675 passed, 22 gated skips. See the [complete attempt report](openai-acceptance-2026-10-03.md) for wiring fixes, tests, cost controls and cleanup evidence.

**Historical Gemini status is unchanged: 2/20 attempts, both HTTP 503 UNAVAILABLE.** No Gemini request or ledger reset occurred. The September checkpoint below is preserved as historical evidence, including its then-current provider and phase scope; it is superseded by this update only for current OpenAI status.

## Historical September checkpoint

Updated 24 September 2026 (Asia/Calcutta).
**Phase 7 implementation-complete; live-provider acceptance blocked by external
Gemini availability (HTTP 503 UNAVAILABLE).**
The owner confirmed the dedicated Free Tier project/key with Cloud Billing unlinked
and that AI Studio does not display quotas. They explicitly authorized the bounded
attempt without inventing RPM/TPM/RPD. The first request returned HTTP 503
`UNAVAILABLE` at 13:27:30 UTC. The owner then explicitly authorized exactly one
retry, which returned the same HTTP 503 at 16:36:05 UTC (22:06:05 Asia/Calcutta).
The retry used one generated synthetic fixture and stopped immediately on failure.
Gemini attempts are **2/20**. No automatic retry, OpenAI call, billing change or
model switch occurred. Exact errors and cleanup evidence are recorded below.
Implementation completion is supported by the mock/synthetic, security and
regression evidence below; it is not a claim of successful live-provider acceptance.
Phase 8 must remain unstarted. Phase 9 has not started.

## Current acceptance blocker and preserved budget

Exactly two explicitly authorized synthetic requests reached Gemini. Both returned
HTTP 503 `UNAVAILABLE`, reporting temporary high demand. Neither returned a
401/403 authentication failure, 429, explicit quota exhaustion or quota values.
The observed blocker is external provider availability; no quota or authentication
failure is inferred from it. Live grounding and quality acceptance remain unverified.

The permanent attempt ledger is **2/20 used, 18 remaining**. Failed attempts remain
counted; preserve the ledger without resetting or consuming further attempts now.
The OpenAI reservation remains $0.50/$5. RUN_AI_INTEGRATION is unset again, the API
key remains private and server-side, and synthetic cleanup has been verified.
No further Gemini request, automatic retry, model switch or billing change is
authorized now. No retry is scheduled. This status update makes no live request.

The earlier implementation checkpoints are `bde47ce`, `c2fad82`, `d48ff1e` and `dcb11d4`;
the original provider/baseline checkpoint is `dda2176`. The Gemini adapter retains the existing OpenAI-compatible abstraction. This update
adds explicit undisplayed-quota opt-in and redacted evaluator-only error diagnostics. See the
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
requires `--live-gemini`, `--free-tier-confirmed` and either actual displayed
numeric quotas or explicit `--quota-not-displayed`. The latter was authorized by
the owner because AI Studio does not expose the values; it accepts no invented or
simultaneously supplied numeric quota arguments. It does not infer quota or bypass
the permanent attempt cap. For displayed limits, the existing conservative
minimum remains 1 RPM / 57000 TPM / 2 RPD. Any two case requests are at least 61
seconds apart; any unsuccessful case stops the run. No model-access
probe or token-count call is made. Billing-unlinked status is owner-confirmed;
the application cannot independently guarantee the Cloud project's billing state.
No paid Gemini usage is authorized. Do not guess quotas or enable billing.

The applied forward migration `20260924080552_gemini_synthetic_explanations.sql`
adds an exact Gemini model pair and permanent private `gemini_attempts` counter.
It reserves before invocation and caps all Gemini attempts at 20, including
failures; deletion, invalidation, expiration and restarts never refund it. The
existing paid ledger remains 50 cents reserved of the $5 cap. It is not reset.
Gemini attempts are **2/20**, including both failed live requests; paid reservations
remain **$0.50/$5**. The counters were not reset or refunded.

Normal pytest clears AI credentials/live flags and blocks both provider hosts at
the HTTP transport layer. Mock is the default standalone evaluation provider;
tests inject it explicitly. Application construction with explicit test settings
does not load either secret env file. Adapter tests use `httpx.MockTransport`.
The product never presents a mock as a live model result.

Before the first Gemini request, all safeguards were verified and reported:
required RUN_AI_INTEGRATION=1 and CLI opt-in, only synthetic fixtures, server-side
key, owner-confirmed Free Tier/billing unlinked, immediate stop on quota/access
errors, store=false, no tools, permanent limit and mock network isolation. The
process flag was scoped to the evaluator command and removed in `finally`.

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
safe categories/counts/timing reach application logs; no prompts, raw responses
or secrets. Only the explicitly invoked evaluator receives bounded provider error
diagnostics: HTTP status, code/status/message and allowlisted quota/retry/reason
fields. Known API keys are redacted; headers and arbitrary metadata are excluded.
These diagnostics do not enter API/UI responses or model context. They are saved
in ignored `.cache/phase7/live-gemini-errors.jsonl` for the requested exact error
report. Provider retry advice is reported as data and never triggers a retry.

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
key. RUN_AI_INTEGRATION is unset again after the bounded attempt.

## Live Gemini attempts — 24 September 2026

### Initial attempt

Exactly one request was made for the first generated synthetic case (eight reviewed,
published findings from one authorized report). The provider returned:

```text
HTTP 503
code: 503
status: UNAVAILABLE
message: This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.
```

No explicit quota metric, quota value, rate limit or retry interval was returned.
This is evidence of provider-reported unavailability, **not evidence of zero Free
Tier quota or successful model acceptance**. No RPM/TPM/RPD was invented.
The response is authoritative for this attempt; no additional provider probe ran.

The application recorded safe category `provider_failure`, no explanation output
and no input/output token counts. The complete application generation round trip
was 4406 ms; this is not successful inference latency. The evaluator stopped on
case 1 and did not send the adversarial second case. No automatic retry, model
fallback, paid-tier configuration or billing upgrade occurred. No personal report
was enrolled or transmitted. Live grounding/numeric/injection acceptance remains
unmeasured, so Phase 7 is not signed off.

Pre-generation checks for foreign-owner read/generation denial, CSRF and rejected
caller-selected evidence passed before the provider request. These are not a pass
of the full two-case live acceptance suite. The generated fixture was deleted in
`finally`; database verification found zero explanation rows and zero enrollment
rows. After the initial attempt, Gemini's ledger was 1/20 and the OpenAI reserved
ledger was unchanged at 50 cents. The process live flag was cleared. The later
retry below was separately and explicitly requested by the owner.

Safe local accounting is in `.cache/phase7/live-gemini-attempts.jsonl` and
`.cache/phase7/live-gemini-errors.jsonl`; no key or raw request is stored there.

### Exactly one authorized retry — attempt 2/20

On 24 September at 16:36:05.944801 UTC, the one authorized retry returned:

```text
HTTP 503
code: 503
status: UNAVAILABLE
message: This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.
```

The command required RUN_AI_INTEGRATION=1 and used `--live-gemini
--free-tier-confirmed --quota-not-displayed --single-fixture 1`. Exactly one
newly generated synthetic fixture with eight reviewed/published findings was
selected. A new evaluator-only wrapper caps provider invocations at one for this
mode, including failure; unexpected duplicate calls are rejected before reaching
the provider. Tests prove the cap after both success and failure. The shared
provider, grounding/evidence/schema validators and permanent 20-attempt ledger
are unchanged. The key stayed server-side and was not printed or copied.

Exactly one live request occurred in this retry run. The evaluator stopped at the
503; no second fixture, automatic retry, model switch, billing change or OpenAI
call followed. Google returned no quota/rate-limit details, authentication error,
usage tokens or accepted output. Zero Free Tier quota therefore remains unproven.
The failed application's generation round trip was 2735 ms; it is not successful
model latency. Live grounding/schema/evidence acceptance cannot be claimed without
an output. No further live acceptance work was run after the failure.

The pre-generation foreign-owner/CSRF/caller-evidence checks passed. The runner
removed its created fixture in `finally`; verification found zero explanation rows
and zero synthetic enrollments. Gemini's permanent ledger is now **2/20**, and the
OpenAI reserved ledger remains **$0.50/$5**. RUN_AI_INTEGRATION was removed in the
command's `finally` and independently verified unset afterward. No further request
is scheduled. Safe attempt/error audit records are appended to the same ignored
JSONL artifacts above. Phase 7 live acceptance remains incomplete.

Historically, two OpenAI attempts on 18/23 September failed authentication with no
accepted output or returned usage. Their $0.50 reservations remain conservative
reservations, not measured billing. OpenAI is now stopped; no further probes.

## Frontend/backend and regression results

Fresh verification of this Gemini implementation on 24 September:

- One-request retry safeguard: **76 focused tests passed**, including single-fixture
  selection and second-call rejection after both successful and failed provider
  responses. Ruff, formatting and mypy (78 source files) passed. A pytest cache
  permission warning accompanied the passing sandbox test run; existing dependency
  deprecation warnings remain. No normal test sent a live AI request.

- After the undisplayed-quota/error-reporting change: **73 focused backend tests
  passed**; Ruff/format checks and mypy (78 source files) passed. Tests verify the
  explicit new opt-in preserves other gates, rejects mixed numeric/unknown quotas,
  retains provider quota details, redacts keys and never retries an access failure.
- The following broad results are the adapter checkpoint before this runner-only
  update; they were not all rerun after the three added tests.
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
- Final database check after the live attempt: zero explanation rows and zero
  enrollments; Gemini attempts two and paid reservations unchanged at 50 cents. Both local test servers stopped.
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

The initial attempt and separately authorized one-request retry both stopped on
HTTP 503 as recorded above. Quota values remain undisplayed and must not be
invented. Implementation is complete; the outstanding acceptance gate is a
successful, validated live-provider result once external availability permits it.

Only after the owner explicitly authorizes another retry:

1. Require process `RUN_AI_INTEGRATION=1`, `--live-gemini`, existing Free Tier/
   undisplayed-quota gates and `--single-fixture 1` (unless another built-in
   synthetic fixture is explicitly selected). Keep the key server-side.
2. Perform exactly **one synthetic live request**, preserving the one-call wrapper,
   permanent 20-attempt ceiling and all grounding/evidence/schema validation.
3. Make no automatic retry, model switch or billing change. Stop immediately on
   **any provider error** and report the provider response with secrets redacted.
4. Remove RUN_AI_INTEGRATION in `finally`, clean up the created synthetic fixture,
   verify the attempt ledger, and update this handoff with the result.

These are rules for a future authorized retry, not current authorization to run it.
Phase 8 remains unstarted until separately authorized.

## Known limitations

Implementation is complete, but live Gemini acceptance is externally blocked by
the two HTTP 503 responses. English and five fixed definitions are the
entire educational scope. No clinician-reviewed, production, real-patient,
multilingual or broader medical reasoning claim is made. Source flags/ranges do
not establish normality. Partial publication may not cover a whole report. Twenty
facts may exceed the output cap and fail safely; they are never silently truncated.
Project billing status depends on the owner's configuration. Provider-reported
model/version/usage must match strictly or the result fails closed. Existing
outbound-auth-email testing limitations and leaked-password warning remain.

## Suggested commit and Phase 8 preview

Suggested checkpoint commit:
`docs: mark Phase 7 implementation complete with external acceptance blocker`.
Do not describe this checkpoint as completed live acceptance.

Phase 8 would separately assess deterministic same-metric/unit/date-compatible
trends, preserving source revisions and showing insufficient/incompatible data.
That requires its own instruction and checks. **No Phase 8 work has started.**
