# OpenAI acceptance record

Updated 2026-10-04 (Asia/Calcutta). **Current total: one OpenAI network request.** The earlier isolated adapter check passed. The later persisted Phase 9 run stopped before provider dispatch; its separate result is recorded below. No automatic retry was performed.

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
