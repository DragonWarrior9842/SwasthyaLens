# OpenAI acceptance record

Latest preparation checkpoint — **Gate H, 2026-10-04: FULL OFFLINE PHASE7 LIFECYCLE PASSED.** Deletion/manual preservation, both directions of user isolation and final provider preflight passed. Ready for one separately authorized Phase7 live OpenAI request; **no live request made or authorized by this preparation**. Migration `20261004130141_explanation_model_metadata` remains applied. OpenAI **2 total**, Gemini **2/20**, gate unset. See [Gate H](#gate-h--full-offline-phase-7-lifecycle-passed); Gate G's failed harness run and all earlier outcomes remain preserved below.

Latest Phase 7 checkpoint, 2026-10-04: **Gate D stopped at offline model-metadata preflight, before any provider request.** Minimal local compatibility fixes and targeted regression are complete; the new migration is **prepared, not applied**. OpenAI count remains **2**; Phase 9 Gate C PASS is unchanged. See [Gate D](#gate-d--phase-7-offline-preflight-stop).

Latest outcome, 2026-10-04: **Gate C passed the authorized single-turn persisted Phase 9 acceptance**, including readback and two-user isolation. One new OpenAI request; **2 total**. Full Phase 7 persisted report-explanation acceptance and production enablement remain pending. The dated A/B entries below remain historical records; see the complete [Gate C result](#gate-c--authorized-persisted-phase-9-rerun-passed).

Historical checkpoint before Gate C, 2026-10-04 (Asia/Calcutta): **total at that checkpoint: one OpenAI network request.** The earlier isolated adapter check passed. The later persisted Phase 9 run stopped before provider dispatch; its separate result is recorded below. No automatic retry was performed.

## Gate 1 — isolated adapter result, preserved

2026-10-03, 23:04 Asia/Calcutta (17:34 UTC). **PASS for one Phase 7 educational explanation fixture.** OpenAI / `gpt-6.1-sol` is now live-verified within this narrow scope. This is not a completed Phase 7 persisted application acceptance, a Phase 9 assistant acceptance, or production enablement.

| Requested check | Observed result |
|---|---|
| Wiring corrections | Added the explicitly selected model to `AISettings`; request and response model checks now use that setting unchanged. Selected-model reasoning is `low`; its optional reasoning response item is supported while tools/extra messages remain rejected. |
| Provider selection | The isolated acceptance factory requires `AI_PROVIDER=openai` and `AI_MODEL=gpt-6.1-sol` and constructs the actual OpenAI adapter. No mock or Gemini path exists in this runner. Normal app factory/defaults remain unchanged and unavailable for live generation. |
| Endpoint/structured contract | Exactly one POST to `https://api.openai.com/v1/responses`; strict JSON schema, existing closed educational vocabulary and exact-evidence validator retained; `store=false`, no tools, background work or streaming output. This is not a zero-retention claim. |
| Offline verification | Targeted adapter/Gemini/assistant/release tests: 165 passed. Full backend: 675 passed, 22 gated skips, two existing upstream warnings, 35.84s. Ruff/format and mypy passed, including the new CLI runner. |
| Network count / HTTP result | **1 provider request; HTTP 200; 0 retries; 0 fallback requests.** No model-list or token-count API call. |
| Confirmed provider/model | OpenAI / **`gpt-6.1-sol`**, response model matched exactly. |
| Synthetic fixture | One invented Vitamin D finding; `18`, `ng/mL`, `30–100`. Existing parameter-field parser, `SourceEvidence`, `facts()` and opaque `e1` serialization used in memory. Private source UUIDs were excluded from the prompt. |
| Schema validation | PASS using existing `ModelExplanation` and closed enumerated fields. |
| Evidence validation | PASS; exact fact equality, supported ID and item count, code and note membership. No unsupported evidence. |
| Safety / grounding | PASS; value `18`, unit `ng/mL` and range `30–100` preserved exactly. Educational scope, selected-findings limitation, professional-context follow-up and unknown comparison preserved. Only reviewed catalog wording can render; no free-form diagnosis, medication advice or fabricated medical facts. |
| Database / Storage / personal data | No database or Storage access, no user session/server, no real report upload/download, no personal health data. This deliberately excludes persisted enrollment/reservation/lifecycle and UI acceptance. |
| Cost | 6,540-byte request; 1,536 maximum output tokens; conservative preflight bound $0.06. Actual usage 1,242 input + 122 output tokens; standard uncached-price estimate **$0.003704**, not a billing-receipt claim. |
| OpenAI attempt count | **1 authorized live acceptance attempt**, successful. Exclusive local marker created before dispatch and retained. The old DB budget bookkeeping was neither read nor changed; it is not the new live-attempt counter. |
| Gemini history | **2/20 attempts used, 18 remaining**; both HTTP 503 UNAVAILABLE. No Gemini request, reset or ledger change. |
| Live gate / cleanup | `RUN_AI_INTEGRATION` was set only inside the isolated child process and removed in `finally`; parent shell remains unset. Runner exited; process inventory confirmed zero remaining acceptance processes. HTTP transport closed. |
| Secrets | Key loaded only server-side from private configuration; never placed in request body, command arguments, response metadata or console output. HTTP logging disabled. Result artifact compared privately against the key before saving/printing. `backend/.env.ai` remains ignored/untracked and unchanged. |
| Phase 7 completion | **Single-fixture live adapter acceptance PASS. Full Phase 7 live application acceptance remains PENDING** because persisted enrollment, API/UI, source revalidation and cleanup were intentionally not exercised with OpenAI. Earlier deterministic acceptance remains valid within its scope. |
| Phase 9 completion | **NOT COMPLETE**. No `generate_assistant` call was made; the separate live capability remains locked. A report explanation permit cannot be repurposed for conversations. |
| Remaining AI release blockers | Broader Phase 7 and separately authorized Phase 9 acceptance; any production provider/persistence/frontend model wiring and enablement must be reviewed separately. No real-data suitability or clinical validation claimed. Phase 14 not started. |

Implementation files changed for this attempt:

- `backend/app/core/ai_config.py`: accepts the owner's explicit model while retaining existing defaults.
- `backend/app/core/explanation_provider.py`: configured model, bounded output, reasoning compatibility and allowlisted error metadata; ordinary live transport remains locked.
- `backend/app/core/openai_acceptance.py`: explicit OpenAI factory and one-use transport with endpoint/model/tool/cost checks, zero retries and exclusive durable marker.
- `backend/scripts/accept_openai_once.py`: fixed synthetic in-memory fixture, offline preflight, temporary gate, validation and sanitized result.
- `backend/tests/test_openai_acceptance.py`: ten offline cases covering success, failures, unchanged live locks, wrong settings, key privacy and repeat-attempt rejection.

The existing DB-backed `evaluate_explanations.py --live-openai` remains stopped because this authorization forbids database/Storage access. The application factory, Gemini settings, persistent model metadata and schemas, frontend defaults, private configuration and historical ledgers were not changed for this attempt.

Local audit artifacts: `.cache/phase13/openai-acceptance-1/attempt-reserved.json` and `result.json`. They contain only reservation/outcome metadata; no prompt, raw provider response, credentials or authorization headers. Preserve the marker. Do not rerun `--live`, reset the marker, retry automatically or send further requests without fresh explicit authorization. Ordinary regression remains offline with `RUN_AI_INTEGRATION` unset.

Final read-only secret audit: **zero findings** across nonignored working files, 679 reachable Git blobs and 21 bundle files, using six privately compared configured values; three previously reviewed public-alphabet false positives remain exempted. A separate private comparison checked both ignored acceptance JSON artifacts: **zero key/authorization-header findings**. No matched secret or header was printed. Process inventory required sandbox escalation and then positively confirmed zero acceptance runners; no live command was rerun for cleanup.

API compatibility and cost basis were verified against [OpenAI's model documentation](https://developers.openai.com/api/docs/models/gpt-6.1-sol) and [Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs): Responses and structured output support, supported `low` reasoning, and standard $2 input / $10 output per million tokens. Conservative preflight costing also allowed cache-write pricing and a regional margin; it is not a provider-enforced account spending limit.

## Gate 2 — persisted Phase 9 flow stopped before OpenAI

Run started 2026-10-03 at 23:41:59 Asia/Calcutta (18:11:59 UTC); result saved at 23:42. Cleanup/status review completed 2026-10-04. **FAIL / NOT COMPLETE: synthetic report workflow stopped before context selection, conversation creation or provider invocation.** The original sanitized result is preserved at `.cache/phase13/openai-persisted-assistant-2/result.json`; no provider-dispatch marker exists for this gate.

| Requested check | Actual result |
|---|---|
| Preflight | Offline configuration and schema/RLS checks passed. Runtime preparation stopped at `synthetic_report_workflow`; full preflight did not complete. |
| New OpenAI request count | **0**. The authorized one-request goal was not reached; no provider HTTP result exists for this gate. |
| Intended provider/model | OpenAI / `gpt-6.1-sol`; not reconfirmed live in Gate 2. Gate 1's exact-model HTTP 200 remains valid separately. |
| Failure category | Recorded category **`local_or_provider_failure`**, stage **`synthetic_report_workflow`**. The saved audit intentionally contains no raw exception/body and did not retain an exception location. |
| Offline-identified harness defect | The runner read `observation["user_id"]`, but the public `Observation` DTO deliberately omits that field. This causes a `KeyError` when reached and is consistent with the recorded stage; the generic saved error does not prove the exact runtime exception. Corrected offline to verify the published observation through the authenticated owner's RLS-scoped Data API, selecting only `id,user_id`. The public DTO and RLS remain unchanged. |
| Usage/cost | No OpenAI request: no provider-reported input/output/total tokens, **$0 new OpenAI usage** for this gate. No billing lookup was made. Gate 1 estimate remains $0.003704. |
| Context authorization / minimization | **NOT REACHED**. Guard code was prepared to inspect the unchanged real `ContextBuilder` output, one current owned report observation, exact facts/date, empty history, opaque `e1` and absence of private identifiers. Not claimed live-verified. |
| Phase 8 deterministic result | Not applicable to the selected one-report explanation; no trend request made. |
| Structured output / evidence / facts / safety | **NOT REACHED** for Gate 2. No model response exists; do not copy Gate 1 passes into this result. |
| Conversation / user message / assistant message persistence | **NOT REACHED**. The failure occurred before the conversation step. |
| Evidence associations / provider-model metadata / frozen language | **NOT REACHED** in a generated message. Exact OpenAI metadata support was added and tested offline/at schema level only. |
| Reload/readback / additional calls | **NOT REACHED**. Zero additional AI calls occurred, but no successful persisted reload is claimed. |
| Two-user safety | Dedicated A/B login stage completed; metadata checks confirmed forced RLS and unchanged grants. Runtime conversation/message/evidence denial checks were **NOT REACHED**, so full two-user acceptance remains pending. |
| Retry/fallback | **0 / 0**. The isolated adapter runner was not rerun. |
| Cleanup | Recorded synthetic cleanup and preference restoration **PASS**. `RUN_AI_INTEGRATION` is **unset**; read-only process inventory on continuation confirmed **zero persisted-acceptance Python processes**. Existing synthetic lifecycle cleanup was used. |
| Secrets | `.env.ai` remains ignored/untracked; keys/session tokens never printed or included in request bodies or artifacts. Application/provider logging was disabled. See final audit below. |
| Total OpenAI live requests | **1 total**, the earlier Gate 1 request; Gate 2 added zero. |
| Gemini | **2/20**, both historical HTTP 503 UNAVAILABLE; no request or ledger reset. |
| Phase 7 | Direct one-fixture adapter acceptance remains **PASS**. Full persisted report-explanation acceptance remains pending; this failed Phase 9 preparation cannot complete it. |
| Phase 9 | **NOT COMPLETE**. The actual persisted assistant request, readback and A/B isolation remain unverified. |
| Remaining AI release blockers | Successful separately authorized persisted acceptance; ordinary production enablement remains disabled. Backend mypy currently cannot load its compiled module because Windows Application Control blocks it; no bypass attempted. No Phase 14 work. |

Minimum wiring/persistence changes prepared for Gate 2:

- `backend/app/core/assistant.py` and `backend/app/schemas/assistant.py`: allow and verify the exact OpenAI model pair; retain existing Gemini/mock/rules pairs.
- `backend/app/core/openai_assistant_acceptance.py`: explicit single-use Phase 9 provider requiring the live flag and a verified context digest; fixed Responses endpoint, no tools/retries/fallback, 10,000-byte input-body bound and 1,536 output-token limit.
- `backend/app/core/openai_acceptance.py`: neutral reservation marker wording; prior marker retained untouched.
- `backend/scripts/accept_persisted_assistant_once.py`: authenticated real FastAPI routes with actual Supabase transport, normal upload/extract/review/publish workflow and normal assistant context/validation/persistence. A read-only context guard must authorize the real builder output before dispatch. No mock provider or direct adapter bypass. Owner-check defect subsequently corrected offline; the saved result now prevents restarting this run even though zero AI requests occurred.
- `backend/tests/test_openai_assistant_acceptance.py`, `frontend/src/services/assistant.ts` and its test: offline provider/evidence/privacy/gate tests and persisted-metadata decoding.
- `database/migrations/20261003180952_assistant_openai_acceptance.sql`: applied to the existing development project; adds only `openai` / `gpt-6.1-sol` to message CHECK constraints. Local filename matches recorded remote version; now 16 migrations. No policy, grant, RPC, historic migration or unrelated data changed.
- `database/verification/assistant-openai.sql`: exact provider/model pair and retained RLS/grant checks.

Verification before the failed runtime preparation: **685 backend tests passed, 22 gated skips; 372 frontend tests passed; frontend lint/types/build PASS; targeted backend 207 PASS; backend Ruff/format PASS.** After the offline ownership correction and recorded-run lock: **212 targeted tests PASS**, including foreign/empty/wrong-owner observation rejection, with two existing upstream warnings. Backend mypy could not start due to the Windows Application Control error; no type-check pass is claimed for these changes.

Applied migration and rollback SQL checks `assistant-openai.sql` and `assistant-schema.sql` passed. Advisors remained at three intentional private-table default-deny INFO findings and the existing leaked-password-protection WARN; no new RLS exposure was reported. [Default-deny guidance](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy), [password-protection remediation](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).

The user's failure rule requires stopping and reporting rather than automatically repeating the flow. Preserve both result directories and all history. A new live run requires fresh explicit authorization; do not delete the recorded result or marker to retry.

Final Gate 2 audit on 2026-10-04: **zero secret findings** across nonignored working files, 696 reachable Git blobs and 21 bundle files (six configured secret values compared privately; three existing reviewed public-alphabet exemptions). Separate private comparison of all three acceptance JSON artifacts found **zero key or authorization-header exposures**. `backend/.env.ai` was again confirmed ignored/untracked and `RUN_AI_INTEGRATION` unset. Neither saved result was overwritten and no additional live process was launched.

## Gate C — authorized persisted Phase 9 rerun passed

2026-10-04, started 12:19:58 Asia/Calcutta (06:49:58 UTC). **PASS for the explicitly authorized single synthetic persisted assistant turn.** The user's new authorization permitted one rerun after an offline harness rehearsal; it did not reset either previous result or authorize further cases. Audit correlation: `f3dafc01-6f6e-4684-a7ef-71eea1564fea`. Immutable result and dispatch marker: `.cache/phase13/openai-persisted-assistant-3/result.json` and `attempt-reserved.json`.

| # | Requested result | Observed outcome |
|---|---|---|
| 1 | Harness preflight | PASS. Exact private OpenAI configuration, dedicated development accounts and unused authorization checked. Ordinary regression: **692 passed, 22 gated skips**, two existing upstream warnings; Ruff/format PASS. |
| 2 | Ownership fix | PASS. The public Observation DTO still excludes `user_id`; the runner independently verifies `id,user_id` through the authenticated owner's RLS-scoped Data API. Wrong-owner offline rehearsal stops before provider dispatch. No bypass introduced. |
| 3 | Workflow reached provider boundary | PASS offline and live. Offline rehearsal executes the actual runner with mocked HTTP application/database/storage boundaries, real generated PDF extraction/parsing, review-field parsing, Observation validation and production ContextBuilder. It is a harness rehearsal, not proof of remote RLS. The live run uses real API services and Supabase: reserve → upload → extract → parse → review → publish → conversation → real context retrieval. No observation or prompt was injected into live context. |
| 4 | New OpenAI requests | **Exactly 1**, exclusive dispatch marker retained. No model-list, token-count, billing or second-case API request. |
| 5 | HTTP result | Provider **200**; persisted application endpoint **200**. |
| 6 | Provider/model | **OpenAI / `gpt-6.1-sol`**, exact response model verified. Real one-use adapter and exact transport type; no mock selector or fallback. |
| 7 | Tokens | **551 input + 54 output = 605 total**, provider reported. |
| 8 | Estimated cost | **$0.001642** at the previously verified standard $2 input / $10 output per million tokens; not a billing receipt. Conservative preflight cap estimate $0.06. Combined A+C standard estimate **$0.005346**; B cost $0. |
| 9 | Context authorization | PASS before setting `RUN_AI_INTEGRATION=1`. Authenticated owner, current observation revision 1, expected report/candidate and review revision 1 verified by the real builder and guard. Existing active/current-source selection and server authorization retained. |
| 10 | Minimization | PASS. One latest-report evidence item (`e1`), one expected metric, zero history, no trend/calculation. Exact expected source excludes unrelated/other-user findings; active/current evidence excludes stale/deleted items. Private source UUIDs and session token absent from model input. No credentials or DB/storage tools supplied; tools empty. This single fixture is not a new adversarial stale/delete test matrix. |
| 11 | Structured output | PASS. Strict multilingual assistant schema; real application service validates the returned structure. |
| 12 | Evidence validation | PASS. Exact permitted answer and authorized opaque evidence ID; no unsupported evidence. |
| 13 | Fact preservation | PASS. Invented `18`, `ng/mL`, `30–100`, and declared fixture date `2026-10-03` preserved exactly. No fabricated date/fact. |
| 14 | Safety | PASS within the closed educational contract. Model selects validated enumerations; server-owned wording/facts render the answer. No free-form diagnosis, medication advice or unsupported certainty. |
| 15 | User-message persistence | PASS. Owner-scoped database read contains the question and correct conversation. |
| 16 | Assistant-message persistence | PASS. Ready answer, exact OpenAI/model metadata and frozen `en` language persisted and read back. |
| 17 | Evidence-association persistence | PASS. Stored answer contains expected observation/report association, opaque evidence ID and exact facts; owner database read equals returned answer. |
| 18 | Reload/readback | PASS. Normal conversation GET returns identical messages/answer. |
| 19 | Reload calls | **0 additional OpenAI calls**. |
| 20 | Two-user isolation | PASS. Second dedicated account cannot list the new conversation, read its thread/messages/evidence or send into it. Direct user-scoped table reads are empty; foreign thread read/send return 404. No additional AI call. |
| 21 | Retries/fallbacks | **0 / 0**. No model/provider changes. |
| 22 | Cleanup | PASS. Conversation/report deleted through normal owner APIs, preference restored, sessions closed, transport closed; runner exited normally. Process inventory verifies no remaining acceptance Python process. |
| 23 | Final live gate | **Unset**, in runner cleanup and parent shell. Normal startup remains locked; ordinary tests remain offline. |
| 24 | Secret audit | PASS. `.env.ai` ignored/untracked; result privately compared against configured secrets/session tokens. Final working/history/bundle and ignored-artifact checks recorded below; no private value, header, cookie, prompt, health payload or full output was logged. |
| 25 | Total OpenAI requests | **2**: A=1, B=0, C=1. Both dispatched requests succeeded. |
| 26 | Gemini history | **2/20**, both HTTP 503 UNAVAILABLE; unchanged, no Gemini request. |
| 27 | Phase 7 | Direct single-fixture adapter PASS from A remains valid. **Full persisted Phase 7 report-explanation acceptance still PENDING**; this assistant flow does not exercise that separate lifecycle. |
| 28 | Phase 9 | **Single-turn persisted live acceptance PASS** for this synthetic English latest-report case, including storage/reload/isolation. No claim that every conversational, language, trend or production case is accepted. |
| 29 | Remaining AI release blockers | Full Phase 7 persisted explanation lifecycle; broader release-scope multilingual/trend/adversarial acceptance and separately reviewed production provider/persistence/frontend enablement. Normal AI remains unavailable. General Phase 13 staging/security/operational gates remain open. No Phase 14. |
| 30 | Mypy / Windows Application Control | **BLOCKED**, retained from B. No security-policy changes, bypass, alternate-environment verification or new typing PASS claimed. |

The applied development migration `20261003180952` and exact model CHECK were reverified read-only before this run. Conversation/message/observation RLS remains enabled and forced; authenticated direct writes and anonymous reads remain denied. The exposed assistant RPC retains invoker security and restricted execution grants; owner-consistent cascading parent keys remain present. This run made no schema, grant, policy or RPC changes.

Harness-only hardening for C: a fresh audit directory, delayed gate activation until real context validation succeeds, a random correlation ID, allowlisted exception type/category and stage, provider-dispatch-started flag, and an explicit foreign conversation-list assertion. No raw exceptions or payloads are retained. The two new offline rehearsal cases use no private configuration and forbid external transport. An initial sandbox cache/temp denial was resolved with authorized local filesystem access; no Windows Application Control settings were changed.

The rerun authorization is consumed. **STOP: no more provider requests, retries, provider/model changes or Phase 14 work.** Preserve all three result directories and both dispatch markers.

Final Gate C audit: **zero findings** across nonignored working files, **696 reachable Git blobs**, **21 release bundle files**, and six configured secret values compared privately (three previously reviewed public-alphabet exemptions). A separate private scan of **all five ignored acceptance JSON artifacts** found zero secret/header exposures. SHA-256 comparisons confirmed A's result/marker and B's result are byte-for-byte unchanged. Read-only process inventory confirmed **zero acceptance Python processes**. `.env.ai` remains ignored/untracked and the parent `RUN_AI_INTEGRATION` flag is unset. `git diff --check` passed. No commit, push, deployment or additional provider request was performed.

## Gate D — Phase 7 offline preflight stop

2026-10-04, recorded 12:36:37 Asia/Calcutta (07:06:37 UTC). **STOPPED BEFORE OPENAI**, following the user's rule: “If any offline lifecycle stage fails: STOP BEFORE OPENAI. Fix only the minimum issue and run targeted offline regression.” No live acceptance runner, report upload, session, reservation or model request was started. The attempted acceptance is incomplete; passing repair tests does not reopen this stopped run.

Failure stage: `offline_model_metadata_preflight`; category: `persisted_model_contract_mismatch`; provider invocation: **false**. Correlation ID: `61bcd2b0-f606-403f-a2a7-4f070e6ca551`. Sanitized immutable result: `.cache/phase13/openai-persisted-explanation-4/result.json`; there is no dispatch marker.

Preflight found three matching legacy assumptions: the applied `explanation_provider_model_check` allows only `openai/gpt-5.6-terra`; the reservation RPC hardcodes that model; backend and frontend readers reject an OpenAI `gpt-6.1-sol` record. Read-only schema inspection confirmed the applied constraint. The configured adapter itself resolves to OpenAI / `gpt-6.1-sol`, with private key present. Sending through the old contract could mislabel a new-model result, so no call was made.

Minimum repair prepared:

- The explanation provider exposes its configured model. The service sends that model with the reservation and rejects any mismatched reservation **before invocation**, including reused records.
- Readers accept the exact selected OpenAI pair and retain historical OpenAI/Gemini/mock pairs without relabeling old records. Defaults, private config and normal live locks remain unchanged.
- CLI-generated migration `database/migrations/20261004070111_explanation_model_metadata.sql` adds the selected pair and binds reservation, idempotency and ready-record reuse to the requested model. The existing owner/session/report locks, evidence snapshot, enrollment, budget, stale invalidation and cleanup logic are preserved. **This migration is local and unapplied; no schema/policy/grant/RPC change occurred remotely.** Its rollback verification is prepared at `database/verification/explanations-openai-model.sql` and has not been executed against a migrated database.
- Targeted regression: **120 backend tests PASS**, including old-reservation rejection with zero calls, selected-model mock persistence/readback, stale items hidden, historical metadata readability and existing evidence/provider/security tests. **18 frontend tests PASS**, lint/typecheck PASS; backend Ruff PASS. These are isolated tests, not a completed full report-to-deletion rehearsal. The full offline lifecycle remains required after migration verification. No full regression or new mypy result is claimed.

| # | Requested result | Actual outcome |
|---|---|---|
| 1 | Offline Phase 7 lifecycle preflight | **FAILED compatibility preflight**, stopped before full workflow. Targeted repair regression passed; full lifecycle not yet proved. |
| 2 | Synthetic report workflow | NOT STARTED; no remote synthetic artifact created. |
| 3 | New OpenAI requests | **0**. |
| 4 | HTTP/provider/model | No HTTP result. Locally configured **OpenAI / `gpt-6.1-sol`** verified without key output. |
| 5 | Tokens | No provider usage; no request. |
| 6 | Estimated cost | **$0 new provider cost**. Prior combined A+C estimate $0.005346 unchanged. |
| 7 | Context/evidence authorization | NOT REACHED in this acceptance. Existing owner/current-source logic unchanged; full lifecycle preflight still required. |
| 8 | Structured output | NOT REACHED live; existing targeted offline tests passed. |
| 9 | Evidence validation | NOT REACHED live; no live evidence supplied. |
| 10 | Exact facts | NOT REACHED; no generated result exists. |
| 11 | Safety | NOT REACHED live; no provider output or health payload logged. |
| 12 | Explanation persistence | NOT REACHED live. Selected-model persistence exercised only in mocked repository test. |
| 13 | Reload/readback | NOT REACHED live; mocked repository readback passed. |
| 14 | Reload provider requests | **0**, because no live generation/reload occurred; not a live reload PASS. |
| 15 | Source correction | NOT REACHED. |
| 16 | Stale invalidation | NOT REACHED live. Existing logic unchanged; stored stale content remains hidden in targeted mock tests. |
| 17 | Superseded-evidence exclusion | NOT REACHED in full workflow. |
| 18 | Report deletion | NOT APPLICABLE this run; no report created. |
| 19 | Deleted-evidence exclusion | NOT REACHED in full workflow. |
| 20 | Two-user isolation | NOT REACHED in this Phase 7 run; Phase 9's separate PASS is not substituted. |
| 21 | Retry/fallback | **0 / 0**. No alternate provider/model or isolated runner used. |
| 22 | Live gate | **Unset throughout**; no live process started. |
| 23 | Secrets/cleanup | No report/session to clean up; `.env.ai` remains ignored/untracked. Final audit recorded below. |
| 24 | Total OpenAI live requests | **2**: A=1, B=0, C=1, D=0. |
| 25 | Gemini | **2/20**, both historical HTTP 503; unchanged. |
| 26 | Phase 7 | Direct adapter PASS preserved; **full persisted lifecycle acceptance remains PENDING**. |
| 27 | Phase 9 | Gate C **PASS for one persisted synthetic English case**, unchanged. |
| 28 | Another live request required? | The first Phase 7 persisted live generation is still needed after verified migration and complete offline preflight. **No need established for a second post-correction generation**: the existing evaluator verifies correction→stale and deletion without regenerating. Do not send either automatically after this stop. |
| 29 | Remaining AI release blockers | Apply/verify the prepared metadata migration; complete offline report/review/evidence/persistence/correction/deletion/isolation rehearsal; obtain successful bounded persisted Phase 7 acceptance; broader release-scope and production enablement gates remain. |
| 30 | Windows Application Control / mypy | **Existing BLOCKED status preserved**. No invocation, host-security change, bypass or new typing PASS. |

Supabase function-security guidance was checked while preparing the migration: existing invoker/definer roles, restricted grants and empty search path are retained, not broadened. [Official function documentation](https://supabase.com/docs/guides/database/functions). No billing, schema application, deployment, commit/push or Phase 14 work was performed.

Final Gate D audit: **zero findings** across nonignored working files, **703 reachable Git blobs**, **21 existing release-bundle files**, and six privately compared configured values (three existing reviewed public-alphabet exemptions). Separate inspection of **all six ignored acceptance JSON artifacts** found zero secret/header exposures. No acceptance Python process remains. `.env.ai` remains ignored/untracked, `RUN_AI_INTEGRATION` unset and `git diff --check` clean. A/B/C results and dispatch markers were not edited. Stop remains in effect; no provider invocation occurred.

## Gate E — preparation stopped on database baseline timeout

2026-10-04, recorded 17:36:12 Asia/Calcutta (12:06:12 UTC). The user authorized migration review/application and complete mock lifecycle preparation, explicitly requiring a stop before live AI even if all checks passed, and an immediate stop if anything failed. **Preparation stopped during the read-only pre-migration database baseline.** Supabase returned a connection-timeout error; no query results were obtained. This is an infrastructure failure, not evidence that a security assertion failed.

Stage: `migration_review_readonly_baseline`; sanitized category: `database_connection_timeout`; migration applied: **false**; database mutations issued: **0**; provider invocation: **false**. Correlation ID: `ff28b1cb-06fe-4310-8229-11ff2c5303ed`. Result: `.cache/phase13/phase7-preparation-5/result.json`. No retry of the failed database query was made.

Local migration review found only the intended model CHECK expansion and replacement of the private explanation RPC to carry the explicit model through reservation/reuse. It contains no historical-row UPDATE/DELETE outside the unchanged runtime function body, nor any RLS/policy/grant change. Existing default-model compatibility, owner/session/report checks, enrollment, source snapshot, budget and stale/delete branches remain in the proposed migration. However, comparison with the currently deployed RPC and before/after historical-data/security fingerprints could not be completed, so overall migration review is **incomplete**, not an application approval.

| # | Requested result | Actual outcome |
|---|---|---|
| 1 | Migration review | Local source inspection satisfactory within stated scope; deployed baseline comparison **BLOCKED** by timeout. |
| 2 | Migration applied | **NO**. No apply-migration call or database mutation issued. |
| 3 | Migration identifier | Prepared local `20261004070111_explanation_model_metadata`; still unapplied. |
| 4 | Existing-data preservation | No mutations issued by this run. Baseline fingerprints unavailable; no post-application preservation claim. |
| 5 | RLS/grants/RPC | No changes issued. Current security verification **NOT REACHED**. Proposed RPC behavior change is explicit model selection; authorization/grants are retained in source. |
| 6 | Correct model reservation | Previous Gate D mocked service test PASS; database verification not reached in E. |
| 7 | Deliberate mismatch rejection | Previous Gate D zero-invocation regression PASS; not rerun in E. |
| 8 | Historical metadata compatibility | Previous Gate D backend/frontend reader tests PASS. Applied-row compatibility not verified in E. |
| 9 | Full offline lifecycle | **NOT RUN** after the pre-migration stop. |
| 10 | Correction/stale invalidation | **NOT RUN** in E. |
| 11 | Report deletion | **NOT RUN**; no synthetic report created. |
| 12 | Two-user isolation | **NOT RUN** in E; prior Phase 9 evidence remains separate. |
| 13 | Provider-boundary preflight | **INCOMPLETE**, no provider boundary crossed. |
| 14 | Backend regression | No new run in E. Previous targeted result: **120 PASS**, Ruff PASS. |
| 15 | Frontend regression | No new run in E. Previous result: **18 PASS**, lint/typecheck PASS. |
| 16 | SQL verification | **NOT RUN**. Initial read-only metadata query timed out before producing results; migration/security scripts were not executed. |
| 17 | Mypy / Windows Application Control | Existing **BLOCKED** state preserved; no invocation, policy change, bypass or new PASS. |
| 18 | Final live gate | **Unset throughout**. No acceptance process or remote test artifacts created. |
| 19 | OpenAI count | **2 total**, zero new requests. |
| 20 | Gemini history | **2/20**, both historical HTTP 503; unchanged. |
| 21 | Ready for one Phase 7 live request? | **NO — NOT READY.** Restore database connectivity, repeat the read-only baseline, then apply/verify the migration and complete the authorized preparation gates. No live request is authorized by this preparation instruction. |

Minimum safe correction: restore access to the development Supabase database and rerun the read-only baseline before any mutation. No application-code or schema correction is indicated by a connection timeout. Do not weaken RLS or retry with another provider. No live request, Phase 14 work, commit, push or deployment occurred. Prior A–D result artifacts remain unchanged.

Final Gate E audit: **zero findings** across nonignored working files, **714 reachable Git blobs**, **21 existing bundle files**, six privately compared configured values (three previously reviewed public-alphabet exemptions), and a separate scan of **all seven acceptance/preparation JSON artifacts**. `.env.ai` remains ignored/untracked, the live gate is unset and `git diff --check` passed. No acceptance runner was launched and no synthetic cleanup was needed.

## Gate F — resumed database read-only baseline passed

2026-10-04, after the user resumed Supabase. API health returned HTTP200 and the read-only database query succeeded. All16 applied migrations matched the repository; the prepared `20261004070111_explanation_model_metadata` remained unapplied at this checkpoint. Four Phase7 tables/31 columns and eight relevant function definitions matched expected source. Forced RLS, grants, owner scope, data and ledger fingerprints were unchanged; no unexpected drift in the reviewed Phase7 scope. Zero explanation rows existed. Artifact: `.cache/phase13/phase7-recovery-baseline-6/result.json`.

This checkpoint stopped at **DATABASE CONNECTIVITY RESTORED / READ-ONLY MIGRATION BASELINE PASSED / SAFE TO PROCEED TO MIGRATION APPLICATION**. No mutation or AI dispatch occurred; OpenAI2, Gemini2/20, gate unset, Phase14 unstarted. It did not establish full Phase7 acceptance.

## Gate G — migration applied, mock lifecycle stopped

2026-10-04 18:40:57 Asia/Calcutta (13:10:57 UTC). The user authorized migration application, verification and the full mock preparation workflow, expressly requiring a stop on any failure and no live AI request. The unchanged prepared SQL was applied through the project's established Supabase migration service. That service recorded `20261004130141_explanation_model_metadata`; the prepared filename `20261004070111_explanation_model_metadata.sql` was aligned to this assigned version. Seventeen applied migrations now match the repository. No unrelated migration was edited.

**MIGRATION APPLIED AND VERIFIED. Full mock lifecycle FAILED; NOT READY for one Phase7 live OpenAI request.** Stage `deletion_and_manual_preservation`; sanitized category `deleted_observations_http_404`; exception `CheckFailed`. The harness expected HTTP200 with empty observations for a deleted report. The existing observation RPC rejects a report that is no longer uploaded/owned, and the application returns404. This is a harness expectation defect; the observed response fails closed. No repair/rerun followed this stop. Artifact: `.cache/phase13/phase7-mock-lifecycle-7/result.json`; correlation `e4ae4788-8b75-4075-9cd3-9662dd6db6a9`.

The rehearsal used the real application, authenticated synthetic users, Storage, extraction, review/publication and persisted reservations. Only generation was replaced by an explicitly injected deterministic stand-in carrying the selected provider/model metadata. It never contacted OpenAI. HTTP transport allowed only the development Supabase host; asynchronous outbound transport was blocked. The one-use live candidate remained locked, recorded zero calls and created no dispatch marker. The fixture was synthetic VitaminD18ng/mL with range30–100, plus rejected/unreviewed candidates to test exclusion; evidence came from normal publication, not direct prompt injection.

The failure artifact intentionally remains immutable and contains the stop category rather than per-step success results. The partial results below follow from the ordered assertions completed before that failure; they are not a full workflow PASS. In particular, owner A's post-deletion observations check failed before the loop reached the other user's post-deletion checks, the manual-preservation assertion, or owner B's lifecycle.

| # | Requested result | Actual outcome |
|---|---|---|
| 1 | Migration application | **PASS**, unchanged prepared SQL applied through versioned migration service. |
| 2 | Migration identifier | Applied `20261004130141_explanation_model_metadata`; prepared `20261004070111`, local filename aligned. |
| 3 | Schema verification | **PASS**, intended pair CHECK/RPC model binding verified; seven rollback scripts passed. |
| 4 | RLS | **PASS**, forced/enabled flags and policy fingerprints unchanged before/after and at final cleanup audit. |
| 5 | Grants | **PASS**, table/function security fingerprints unchanged; no privilege expansion. |
| 6 | RPC/functions | **PASS**, intended private explanation RPC matches prepared body; owner/session/evidence/budget guards retained; final body unchanged from verified migration. |
| 7 | Historical metadata | **PASS within available scope**: zero preexisting Phase7 explanation rows; all data/ledger/enrollment fingerprints unchanged immediately after migration. Historical pair reader regressions passed; no historical rewrite. |
| 8 | Correct-model reservation | **PASS for first owner**, real application persisted `openai` / `gpt-6.1-sol`; matching reservation continued through deterministic generation and reload. |
| 9 | Mismatch rejection | **PASS in offline service regression**, deliberate legacy-model reservation rejected with zero provider invocations; SQL verifies model-bound idempotency/reuse. No production mismatch injected. |
| 10 | Full offline lifecycle | **FAIL**, stopped on deleted-report observations HTTP404 expectation; no rerun. Generation offline, application/DB/Storage real. |
| 11 | Structured/evidence validation | **PASS for first owner**, real validation/persistence/readback; exact synthetic value/unit/range, reviewed published evidence only; rejected/unreviewed excluded. |
| 12 | Correction/stale invalidation | **PASS for first owner**, normal revision to19, old explanation stale with output hidden; no regeneration. |
| 13 | Superseded exclusion | **PASS for first owner**, old fact superseded, empty context before republication, only revision2 afterward; old explanation stayed stale. |
| 14 | Report deletion | **PASS for first owner**, owner workflow returned200. Unrelated manual-preservation assertion **NOT REACHED**. Cleanup of synthetic manual entry passed. |
| 15 | Deleted evidence | **PARTIAL**, owner's explanation/detail returned404, state RPC refused, explanation rows absent. Observations returned404; explicit facts-absence assertion and other-user post-deletion checks incomplete. |
| 16 | Two-user isolation | **PARTIAL**, B denied A's report/reservation/explanation reads and relevant mutations before deletion. Reverse lifecycle and B's post-deletion loop not reached. Separate rollback SQL ownership checks passed. |
| 17 | Final provider boundary | **INCOMPLETE overall**. First boundary checked owner/current source, exact pair/permit, minimized opaque evidence, credential exclusion, no tools/store, locked real transport and zero dispatch. Final deleted-evidence/two-user gates incomplete. Mock live-mode rejection passed offline; no retries/fallback. |
| 18 | Backend counts | **265 passed, 2 explicitly gated OCR skips**, two existing warnings. Includes five new preparation-boundary tests and relevant model/service/persistence/stale/deletion/security tests. |
| 19 | Frontend counts | **18 explanation service tests passed**. Browser explanation UI suite **NOT RUN** after acceptance stop. |
| 20 | SQL verification | **7/7 rollback scripts PASS**: explanations-openai-model, explanations-schema, explanations-lifecycle, explanations-limits, explanations-gemini, observations-schema, observations-lifecycle. |
| 21 | Ruff/format/lint/typecheck | **PASS** backend Ruff and formatting (121 files), frontend lint and typecheck. |
| 22 | Mypy / Windows Application Control | Existing **BLOCKED** status retained; not rerun, no bypass or typing PASS. |
| 23 | OpenAI requests | **2 total**, zero new requests; A1+B0+C1+D0+E0+F0+G0. Zero new provider spend. |
| 24 | Gemini history | **2/20**, both historical HTTP503; unchanged. |
| 25 | RUN_AI_INTEGRATION | **Unset**, including final check; no live dispatch marker. |
| 26 | Ready for one Phase7 live request? | **NO — NOT READY**. Full mock lifecycle and remaining UI/preflight gates are incomplete. No live request authorized. |

Minimum safe correction: change the rehearsal's deleted-report observations expectation to404, independently verify no report-derived observation rows remain through owner-scoped Data API access, and retain the unrelated-manual equality assertion. Preserve application authorization and immutable failed-run evidence. After explicit continuation, complete both owner cases and the remaining frontend/provider-boundary checks; no live request is implied. No correction was implemented after this failed gate.

Cleanup passed through normal owner deletion workflows and session closure. Final read-only audit finds zero explanation and synthetic-enrollment rows, unchanged RLS/policies/grants/RPC body. The real reservation with mocked generation incremented internal OpenAI budget bookkeeping by25 cents to75 cents; this is not provider spending or a live request. The attempt ledger was retained, not reset/refunded. SQL fixture changes rolled back. The Gemini counter remains2. Existing advisor findings remain unchanged: three informational private default-deny RLS/no-policy notices and the existing disabled leaked-password-protection warning; neither is a new regression.

No real personal health data, live AI request, provider/model switch, automatic retry, commit/push, deployment or Phase14 work occurred. Prior A–F outcomes and dispatch artifacts remain preserved.

Final Gate G audit: zero findings in nonignored working files,714 reachable Git blobs,21 existing release-bundle files and six privately compared configured values (three reviewed public-alphabet exemptions). All nine ignored acceptance/preparation JSON artifacts separately passed the secret/token/header scan. No acceptance Python process remains. `.env.ai` is ignored/untracked; `RUN_AI_INTEGRATION` is unset; `git diff --check` passed. The failed Gate G artifact remains unchanged.

## Gate H — full offline Phase 7 lifecycle passed

2026-10-04. Fresh user authorization covered only the harness correction and offline acceptance, explicitly prohibiting AI dispatch. The real application/Supabase rehearsal started at17:06:03 UTC (22:36:03 Asia/Calcutta). Artifact: `.cache/phase13/phase7-mock-lifecycle-8/result.json`; correlation `c199dcf4-6fad-45a3-ab2f-3accf767b0e0`. Gate G's failed artifact was not overwritten. No application, authorization, migration, provider selection or configuration change was made in H.

The harness now requires404 for deleted-report observation reads. It then separately queries authenticated owner-scoped observation rows by report and observation ID, and revision rows by observation ID, requiring all to be empty. Five new offline guard cases ensure neither a misleading200 nor retained fact/revision rows can pass. Both users additionally get404 for deleted report/file/explanation/observation access and are denied regeneration and republication using deleted IDs. The explanation state RPC rejects the deleted report; persisted explanation rows are absent. Read-only privileged aggregate verification after cleanup independently found zero fact/revision rows for deleted reports, so deletion is not inferred solely from endpoint denial or RLS filtering.

Both owner cases completed the normal upload→extraction→candidate→review→publish→reservation→bounded deterministic generation→validation→persist/reload→correction→stale/superseded→delete workflow. Before and after each report deletion, the entire unrelated synthetic manual observation representation was identical. Both directions of foreign report/reservation/explanation/evidence read and applicable mutation denial passed. Source value18, unitng/mL and range30–100 were preserved; correction to19 produced only revision2 as current evidence. No prompt evidence was seeded. Generation alone was replaced by the explicit deterministic stand-in; real application, Auth, DB and Storage paths were used.

Final boundary review followed successful full lifecycle completion and retained the existing selected-model one-shot transport: exact owner and model reservation, only reviewed/current evidence, exclusion of unreviewed/rejected/superseded/deleted sources, opaque `e1` references, no credentials/internal IDs in model context, no tools, `store=false`, bounded request, no fallback/retry. Each model context was2577 UTF-8 bytes, with one fact; the request guard permits at most10000 bytes and1536 output tokens. Real transport stayed locked, call count0 and no dispatch marker; both HTTP transports prevented AI egress. Mock activation with a live gate set is rejected by offline tests. Production/staging application construction rejects injected mock providers. No provider or model was automatically changed.

| # | Requested report | Outcome |
|---|---|---|
| 1 | Harness correction | **PASS**, expected404 plus independent fact/revision assertions; application unchanged. |
| 2 | Deleted-report404 | **PASS**, both owners and foreign users; report/file/observation/explanation reads denied. |
| 3 | Deleted facts | **PASS**, direct owner-scoped rows/revisions empty; final DB aggregate confirms physical absence for deleted reports. |
| 4 | Deleted evidence/context | **PASS**, state unavailable, explanation rows absent, generation and republication with deleted IDs denied. |
| 5 | Manual preservation | **PASS**, unrelated observation unchanged before/after each report deletion; later explicit test cleanup passed. |
| 6 | Two-user isolation | **PASS**, both owner directions, report/reservation/explanation/evidence read and mutation paths. |
| 7 | Full offline lifecycle | **PASS**, two complete real application/Supabase workflows with deterministic generation only. |
| 8 | Structured/evidence validation | **PASS**, exact source facts and validated persisted output/readback; two deterministic generations. |
| 9 | Correction/stale behavior | **PASS**, stale output hidden, prior revision superseded/excluded, corrected revision current; no regeneration. |
| 10 | Final provider boundary | **PASS**, full completed source lifecycle plus locked exact-model one-shot configuration and mock/live separation. |
| 11 | Internal budget | **PASS as designed**,75→125 cents, two25-cent permanent reservations; actual new provider spend0, no reset/refund. |
| 12 | Backend regression | **270 passed,2 gated OCR skips**, two existing dependency deprecation warnings. |
| 13 | Frontend regression | **111 service tests passed** across explanations/observations/reports; **13 browser UI groups passed**, including confirmed deletion removes explanation and generation controls. |
| 14 | SQL verification | **6/6 rollback scripts passed**: explanations-openai-model, explanations-schema, explanations-lifecycle, explanations-limits, observations-schema, observations-lifecycle. |
| 15 | Ruff/format/lint/typecheck | **PASS**, backend Ruff/121-file format check, frontend lint/typecheck. |
| 16 | Mypy blocker | Existing Windows Application Control **BLOCKED** retained; not rerun or bypassed. |
| 17 | OpenAI count | **2 total**, zero new requests. |
| 18 | Gemini history | **2/20**, both historical HTTP503; unchanged. |
| 19 | RUN_AI_INTEGRATION | **Unset**, no live dispatch marker. |
| 20 | Ready for one Phase7 live OpenAI request | **YES, awaiting separate explicit authorization.** Actual persisted live acceptance is still pending. |

Budget interpretation: `reserved_cents` is a conservative permanent authorization cap, not actual billed usage. Even abandoned/failed requests consume capacity; cleanup, expiry and deletion intentionally do not refund. The mock rehearsal exercised this real reservation path for metadata acceptance and is explicitly labeled deterministic in the immutable artifact, with two mock generations,50 internal cents and zero provider spend. The remaining375 cents of internal cap is not a claim about the OpenAI account balance. Production controls continue to cap reservations conservatively and do not compute provider billing from these values; injected providers are prohibited in release environments. The historical ledger was never manually reset/refunded. SQL cap/nonrefund fixtures rolled back fully. Gemini's permanent counter remained2.

Final cleanup DB check: zero explanation rows, zero enrollment rows, zero facts/revisions attached to deleted reports. Synthetic manual observations were explicitly deleted only after proving preservation. Browser sign-out passed. The browser artifact `.cache/qa/phase7/browser-results.json` records13 passed groups and0 AI calls; its report/AI responses are routed fixtures with real test-user authentication, not a live AI/UI claim. No retry/fallback, live AI request, commit/push/deployment or Phase14 work occurred. Earlier gates remain historical evidence.

Final H audit: zero findings across nonignored working files,716 reachable Git blobs,21 bundle files and six privately compared configured values (three reviewed public-alphabet exemptions). Ten acceptance/preparation JSON artifacts plus the browser result passed the separate secret/header/token scan. The live dispatch marker does not exist. No acceptance runner or temporary API/frontend server remains. `.env.ai` remains ignored/untracked, the live gate unset and `git diff --check` clean. This is readiness for a separately authorized live attempt, not completed live Phase7 acceptance.
