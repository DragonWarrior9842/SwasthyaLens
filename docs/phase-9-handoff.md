# Phase 9 handoff — context-aware assistant

Phase 9 implements persisted private conversations and a bounded, grounded assistant
contract. Evidence-bearing generation is evaluated through an explicitly injected
deterministic mock. **Live provider acceptance remains externally blocked.** The normal
application reports unavailable AI answers; it does not substitute the mock.

Phase 7 remains **IMPLEMENTATION COMPLETE / LIVE GEMINI ACCEPTANCE BLOCKED BY PROVIDER
AVAILABILITY / GEMINI ATTEMPTS USED: 2/20**. No Gemini/OpenAI request, model switch,
billing change or retry was made for Phase 9. `RUN_AI_INTEGRATION` remains unset.
Phase 10 and voice remain unstarted. Final regression completion is recorded below.

## 1. Architecture

Authenticated active session → owned conversation reservation → deterministic routing
→ bounded current observations or Phase 8 calculation → minimized `AssistantRequest`
→ provider interface → closed-schema/evidence validation → server-rendered facts and
wording → atomic source-version check and persistence → frontend contract validation.

The model receives no client-selected owner/report identifiers and cannot perform
retrieval. No database, Storage, filesystem, HTTP, shell, search or code tools exist.
The server retains the opaque-ID-to-source map. No additional SDK/package was needed.

## 2. Files created

- `backend/app/api/assistant.py`, `core/assistant.py`, `core/assistant_context.py`,
  `schemas/assistant.py`.
- `backend/tests/assistant_fixtures.py`, `test_assistant.py`,
  `integration/test_live_assistant.py`, `browser_assistant.cjs`.
- `frontend/src/services/assistant.ts`, `assistant.test.ts`, `fixtures/assistant.json`.
- `database/migrations/20260925192022_assistant_conversations.sql`;
  `database/verification/assistant-schema.sql`, `assistant-lifecycle.sql`.
- This handoff.

## 3. Files modified

Backend factory registers the assistant service/router and permits explicit test-only
provider injection. Existing `explanation_provider.py` gains the assistant interface,
minimized request and locked live capability; the Gemini adapter shares that capability.
The original Phase 7 generation contracts, gates, transports and budgets remain intact.
`core/provider.py` adds bounded RPC response handling and safe assistant error categories.

Frontend `AssistantPage.tsx` replaces the placeholder; `styles/index.css` adds responsive
chat styles. Root/database READMEs describe setup and the acceptance boundary.
`browser_trends.cjs` waits for the existing 30-reads/minute window before its final dense
fixture reload. That harness change does not raise the product limit. An ignored baseline
auth harness also disambiguates duplicate existing report headings without changing its
actual owned-row count assertion.

## 4. Database changes

Migration **20260925192022 / assistant_conversations** is applied to the existing
development project. The CLI generated the migration, and its filename matches the
hosted recorded version. No earlier applied migration was rewritten.

Two tables have forced RLS and explicit authenticated SELECT-only grants. The public
`assistant_call` is security-invoker; its private lifecycle implementation uses the
existing processing-secret plus active owner-JWT pattern, explicit owner predicates,
restricted execute grants and an empty search path. Client table writes are denied.

## 5. Conversation/message model

`assistant_conversations` stores owner, opaque UUID, creation/update times, request key
and a source version. A generic dated UI label avoids storing an unnecessary generated
health title. Deletion is physical; no redundant active/deleted column is required.

`assistant_messages` stores separate user/assistant rows, role, status, bounded question,
validated answer JSON, timestamps, request key, source version, prompt/schema versions,
provider/model and coarse failure category. Statuses are received, generating, ready,
failed and stale. A composite owner/conversation foreign key prevents reassignment.
Message pairs have a unique conversation/key/role identity. Evidence is embedded inside
the bounded verified answer and shares its RLS and deletion lifecycle; no third table.

## 6. Context builder

Reuses Phase 7's strict schema/provider-boundary conventions and the established owned
observation services. Reuses Phase 8's `TrendService` for calculations. A report question
selects the latest uploaded owned report, then only its current explicitly published
findings. Confirmed-but-unpublished, unreviewed, superseded and deleted values are excluded.

A metric question filters the authorized observation list before selecting at most five
recent entries. A second owned source read supplies page provenance and rechecks the
selected scope. Known measurement days sort before unknown dates. This is not a claim
that upload order or an unknown-date record establishes clinical recency.

No raw OCR, filename, source quote or previous generated explanation is sent. Metadata
inspection is a Python test/debug method returning counts, selection and metric IDs;
there is no production endpoint exposing questions, prompts or health values.

## 7. Evidence hierarchy

Current published/manual observations supply source facts. Phase 8 supplies deterministic
calculations. Model output supplies only a permitted explanatory code and current opaque
citations. The server supplies the final wording and exact evidence cards. Conversation
prose and Phase 7 generated explanations are never primary evidence. There is currently
no source-wording retrieval path or general medical-reference retrieval.

## 8. Routing

Small testable English phrase rules handle latest report, seven canonical metrics,
7/30-day trend/comparison questions, limited follow-ups, unsupported correlations,
clarification, safety and urgent user messages. Ambiguous/multiple metrics ask for one
metric rather than loading unrelated records. A recognized short follow-up may reuse
one metric name from the same conversation's last four user questions.

## 9. Context/history bounds

| Boundary | Limit |
| --- | --- |
| Question | 1–2,000 characters; nonblank; invalid controls rejected |
| Saved conversations | 20 per owner |
| Saved turns | 25 question/answer pairs per conversation |
| Dialogue sent | Last four user questions, each truncated to 500 characters |
| Source facts | Five for a metric; at most 20 for a report |
| Calculation | One minimized Phase 8 summary, opaque `t1` |
| Serialized model input | 24,000 UTF-8 bytes, otherwise reject |
| Model output | 4,096 serialized bytes, closed schema |
| Persisted answer | 60,000 bytes; bounded conversation RPC response 2 MB |

No conversation summary or unbounded memory exists. Prior assistant messages are omitted
from model input. Current evidence is rebuilt on every explicit new send.

## 10. Trends

The assistant copies the Phase 8 result: metric, exact unit, rules version, as-of time,
timezone, period boundaries, sample/day counts, coverage, exact decimal medians/change,
latest/prior values/days and insufficiency reasons. The model sees no raw series and
performs no arithmetic. The UI separates this calculation from source facts.

The increasing synthetic weight fixture preserves **70.250 → 72.750**, **2.500 kg**
period change and the Phase 8 increasing classification. Sparse Vitamin D over thirty
days remains `insufficient_data`; an available latest comparison does not manufacture
a sustained trend. Unknown dates stay unknown. Multiple incompatible unit groups fail
closed without conversion. Calculation provenance includes version/selection/as-of and
a current Trends link, not an archived per-point download.

## 11. Correlations

Phase 8 has **no enabled product correlation pair** in the current metric catalog.
The assistant therefore returns an explicit unsupported response and the non-causation
limitation. It does not invoke the statistical primitive with an invented pair. A live
supported-pair assistant case is not applicable until product/catalog support is approved.
The existing deterministic correlation primitive remains covered by Phase 8 regressions.

## 12. Structured output and versions

`ModelAnswer` contains `scope=educational`, an ordered list of opaque evidence IDs,
an enumerated explanation code, fixed `bounded_current_evidence_not_diagnosis` limitation
and `professional_context` follow-up. Additional fields are forbidden. The provider
request carries this JSON schema, the system instructions, `store=false` and an empty
tools tuple. No model-supplied prose, numbers, unit transformations or diagnoses are
accepted. This deliberately conservative first version uses server-authored wording.

Versions are **assistant-evidence-v1**, **assistant-closed-v1**, and **trends-v1**.
They are persisted and checked by the API/browser. Changing the contract requires a
coordinated schema/prompt/UI migration and regression evaluation, not silent reinterpretation.

## 13. Evidence validation

The output must exactly match the server's permitted code, limitation, follow-up and
complete ordered evidence list. IDs `e1`–`e20` and optional `t1` are request-local aliases.
Unknown, omitted, repeated, reordered or substituted IDs and unsupported fields fail
closed. Real observation/report/candidate UUIDs never cross the model boundary.

Rendering copies exact trusted strings. Before persistence, SQL checks current owned
active source revision, fields, report/candidate/review identity and report availability.
A source-version mismatch discards in-flight output. Reads revalidate stored wording,
choice and fact/provenance equality; the frontend independently checks the response
contract before rendering. Neither provider output nor a submitted ID grants authorization.

## 14. Safety

No diagnosis, prescribing, dose changes, treatment cessation, inferred symptoms/history,
clinical urgency from lab values, guessed ranges or causal claims. Source flags and
ranges remain supplied text; calculated range status remains unknown. Educational
limitations accompany evidence. General medical encyclopedia answers are not implemented.

A narrow current-message screen for severe chest pain, difficulty breathing,
unconsciousness/loss of consciousness and uncontrolled bleeding returns concise guidance
to seek immediate emergency help. It is labeled application guidance, uses no provider
or lab-based triage, and is not a comprehensive emergency classifier.

## 15. Prompt-injection evaluation

The required six adversarial instructions (ignore instructions, reveal all reports,
another user's data, reveal API key, change Vitamin D 18 to 80, assert cancer) are tested
as user instructions and as source/history text. User safety routes retrieve no records.
Source/history strings cannot change the closed answer, exact value 18, range 30–100
or current evidence IDs. Invalid diagnostic prose/extra facts/foreign IDs are rejected.
Raw report text is omitted. React renders source/question text as text, not HTML.

These are deterministic routing, context, mock and validation tests. They establish the
application boundary, **not measured adversarial performance of a live Gemini model**.

## 16. Provider unavailable, limits and timeouts

The existing evaluation selection remains Gemini / `gemini-3.8-flash`. Both real provider
classes expose a locked assistant capability; no environment flag or browser input can
unlock it. Phase 7's single-report synthetic permit is not valid for multi-source chat.
There is no Phase 9 live HTTP transport/admission path enabled. Future live acceptance
requires separately approved synthetic conversation enrollment/budget handling and
activation of that capability; merely retrying Phase 7 does not enable chat.

Evidence questions persist a failed/unavailable assistant message without a fabricated
answer. Clarification/no-data/unsupported/safety replies are deterministic and labeled.
Tests inject `MockAssistantProvider` only through the Python app factory; there is no
mock environment variable, UI selector or product import of test code.

All assistant routes share a 60-requests/minute process-local owner limit. SQL enforces
one pending generation per owner, two globally, six new messages/minute and 100/day
over retained messages. Owner/global advisory locks serialize reservations. Message-rate
history is removed when a conversation is deleted; these are development controls,
not a durable paid-provider quota. A durable non-content rate ledger/shared enforcement
is required before enabling paid/production generation.

Context plus generation deadline is 60 seconds; provider deadline 45 seconds; browser
send timeout 75 seconds. Existing gateway HTTP/connect limits remain 10/5 seconds with
no retry. Pending turns expire after 90 seconds on the next owned operation. A timed-out
background retrieval may finish its bounded read but cannot commit an answer afterward.
No automatic generation retry occurs. Same-key replay returns the existing pair;
changed content with the same key conflicts. Explicit new sends use a new key.

## 17. API endpoints

| Route | Behavior |
| --- | --- |
| `GET /assistant/conversations` | Owned bounded list and availability |
| `POST /assistant/conversations` | Idempotent empty conversation |
| `GET /assistant/conversations/{id}` | Verified owned thread |
| `POST /assistant/conversations/{id}/messages` | Explicit reserved send and safe result |
| `DELETE /assistant/conversations/{id}` | Owned conversation/message cascade |

The browser uses the same-origin `/api` proxy. Existing session, JSON, CSRF, Origin,
no-store and account-change protections apply. Browser-supplied owners/evidence fields
and unknown read query fields are rejected. Foreign conversation operations return 404.

## 18. Frontend UX

Real list/New chat/thread/composer/send, honest empty state, loading announcements,
unavailable/invalid/timeout states, explicit retry, source details and confirmed deletion.
Suggestions and **Use question again** only fill the composer. Page load, refresh and
conversation selection never generate an answer. Network retry keeps its request key.

Source facts retain exact value/unit/range/flag and report page/review provenance,
manual UTC instant or supplied report day/unknown date. Calculation cards identify
Phase 8 rules and counts. Evidence links lead through current authenticated History or
Trends, not provider URLs or permanently downloadable snapshots. Mock renders explicitly
say **Deterministic mock · testing only**. Messages have understandable roles, the
composer has a separate accessible label, and chat selection focuses the composer.

Responsive layout was checked at 375px with open evidence and no horizontal overflow.
Sensitive state stays in React memory and clears on account changes/unmount. No chat
localStorage, microphone, speech or translation infrastructure was introduced.

## 19. RLS/security

Both tables enforce owner plus current active session, including direct Data API reads.
Anonymous/client mutations and forged owner/parent assignments are denied. The runtime
uses no service-role key. Credentials remain server-side and are never included in
requests to a model, browser responses or test logs. No health-question/prompt/response
logging was added. Generic error categories avoid provider payload or secret disclosure.

Post-migration advisors introduced no new relevant issue. Existing findings remain:
leaked-password protection disabled, three intentionally policy-free/nonexposed Phase 7
private tables, and an unused existing review-actor index. No unrelated security setting
was changed to make advisory output empty. Production edge limits and retention policies
remain separate operational requirements.

## 20. Correction/stale behavior

Observation/revision/report changes and timezone changes increment owned conversation
source versions and atomically clear every ready or generating derived answer and its
source links. This intentionally conservative owner-wide invalidation covers new data,
no-data results and trends as well as directly cited facts. It can clear unrelated
answers; correctness is preferred over fine-grained dependency tracking in this version.

Historical user questions and message status remain until conversation deletion;
previous answer facts/prose are removed rather than presented as current truth. A new
send rebuilds context from current active revisions. Report review correction requires
explicit republication before V2 becomes eligible.

## 21. Deletion/freshness

Report/manual deletion excludes the source from future context and clears derived
answers/links. Conversation deletion cascades all its messages and embedded evidence;
another owner cannot delete it. Deleting a source does not erase a user's independently
typed question, which is clearly historical and remains until conversation deletion.

Owned-history mutation signals, focus, visible-tab reentry, manual refresh and a
60-second visible-tab refresh clear stale browser snapshots. External changes may remain
visible until refresh; this is not server push. A user can retain previously viewed or
copied text. Source links always recheck current authorization/availability.

## 22. Real two-user results

Both new synthetic Supabase tests passed individually and in the final full-suite run
through their completion points. A/B and B/A list/read/send/delete and direct evidence
isolation are verified. Revoked access fails through the API and RLS. Genuine Supabase
auth, persistence and source lifecycle are exercised with an injected offline AI mock.

Manual V1 → correction 73.125/revision 2 → new context uses V2; deleted manuals disappear.
Synthetic PDF → extract → review still yields no data until publication → exact values
13.20/18/2.4/<70/>10 → corrected TSH 2.5 requires republication → report deletion clears
answers and future context. Unknown TSH date remains unknown. Fixtures are cleaned up
through their owners; no personal health information is used.

## 23. Mock evaluation

**60 focused assistant tests passed**: routing, bounds, same-conversation follow-up,
medical/urgent safety, unsupported correlations, exact numbers/comparators/qualitative
forms, dates, current-only evidence, source/history injection, strict output rejection,
trend reuse, sparse Vitamin D and incompatible units. Normal tests clear live flags
and credentials and block both AI network hosts at HTTP transport level. The locked
assistant capability remains unavailable even if a test sets the live environment flag.

Exact synthetic strings include **13.20**, **18**, **2.4**, **<5**, **0.4–4.0**,
**30–100**, **Negative**, **1:80** and **73.125**. They are copied, not model-rewritten.
Known report day, unknown day and manual UTC timestamp are kept distinct. No live-model
grounding score, token latency or acceptance result is claimed.

## 24. Frontend checks/build

Lint, TypeScript, **277 tests in 13 files**, and production build passed. Main JavaScript
is 404.00 kB / 121.39 kB gzip; the existing lazy chart chunk is 50.24 kB gzip. Thirty
assistant contract tests reject malformed/cross-parent/altered source responses. A browser
test exposed the nested textarea label issue; separating label/control fixed it before
the complete passing run.

## 25. Backend checks

Ruff, format (96 files) and mypy (93 files) passed. Final normal-suite result is recorded
after the last added injection cases; the earlier complete run passed 476 tests. Nine
explicit local OCR regression tests passed separately. Existing Starlette/AnyIO
deprecation warnings remain. A sandbox cache failure required an unrestricted local
check rerun; no dependency change or validation suppression was used.

## 26. SQL/live regressions

All **18 SQL verification scripts passed** after the Phase 9 migration, including prior
auth/report/extraction/parameter/observation/explanation/trend scripts and new assistant
schema/lifecycle checks. Lifecycle fixtures rolled back. They cover forced RLS/grants,
request replay, concurrency denial, cross-owner operations, version invalidation,
owner/parent integrity, session revocation and cascade deletion.

The final full **11-test live Supabase regression** is tracked in ignored
`.cache/qa/phase9/live-acceptance.log`; completion status will be finalized before handoff.
It covers all prior phases plus two new assistant scenarios. No SQL verification or
browser fixture runner runs concurrently with that suite. No live AI test is included.

## 27. Browser regression results

The **13 new assistant groups passed**, including real saved conversations and normal
provider-unavailable behavior, explicit suggestions/sends, safety/emergency/correlation,
test-labeled exact evidence, malformed response rejection, stale cleanup, mobile layout,
deletion and logout, with zero AI requests/runtime errors. Synthetic screenshots were
visually reviewed. Result JSON/screenshots are ignored local QA artifacts.

The established 78 groups passed at baseline; final post-change rerun completion is
recorded before handoff: auth 15, reports 11, extraction 7, parameters 8, observations 12,
mock explanations 12, trends 13. A baseline trend harness exhausted its intended read
window; its final reload now waits for that existing limit. No app limit was weakened.

## 28. Gemini blocker

Two previously authorized synthetic requests reached Gemini and returned HTTP **503
UNAVAILABLE** due to high demand. No 401/403, 429, explicit quota exhaustion or quota
values were returned. No additional request was made here. Attempts remain **2/20**,
18 preserved; historical OpenAI paid reservations remain $0.50 under the unchanged $5
cap. Gemini billing remains unlinked per owner confirmation; no billing action was taken.

Gemini Free Tier may use submitted data to improve Google products, including human
review. This is a synthetic evaluation choice, not a production healthcare-provider
decision. Keys remain private/server-side. Future retry requires explicit authorization,
one synthetic request, integration gating, no automatic retry/model/billing change and
unset flag afterward, as specified in the Phase 7 handoff.

## 29. Manual checks

1. Start backend and frontend using README. Keep `RUN_AI_INTEGRATION` unset. Sign in
   with a dedicated synthetic test account and open **AI Assistant**.
2. Choose **New chat**. The conversation is empty. Click a suggestion and verify it
   only fills the composer. Enter a question and choose **Send**.
3. With a synthetic published/manual matching observation, expect a saved question and
   honest unavailable-AI status. Reload/select the conversation to confirm persistence.
   The normal app cannot show a mock-generated evidence answer.
4. Ask an ambiguous question, an unsupported correlation, or a synthetic safety phrase;
   expect labeled application guidance. Do not rely on this development chat in an emergency.
5. Use **Use question again** and verify no request occurs until Send. Delete a chat,
   cancel once, then confirm. Its messages must disappear.
6. Use Tab/Enter and a narrow viewport. Sign out or switch accounts; previous conversation
   data must clear. A second owner cannot open the first owner's conversation URL/API ID.
7. For generated evidence/correction/deletion evaluation, use the automated synthetic
   suite with explicit `RUN_SUPABASE_INTEGRATION=1`, never a live AI flag. Run it alone
   against the disposable accounts; the harness injects the mock and cleans fixtures.

## 30. Known limitations

- Live Gemini assistant output is untested and disabled; activation needs a separately
  approved conversation admission/transport path. Phase 7 availability is still blocked.
- English phrase routing and fixed explanatory wording are intentionally limited;
  there is no unrestricted medical reasoning, general search or enabled correlation pair.
- Emergency phrase matching can miss paraphrases and overmatch negation/quoted examples.
- Latest uploaded report differs from latest clinical report. Unknown dates and bounded
  recent context cannot establish comprehensive chronology. No unit/assay conversion.
- Owner-wide invalidation, refresh-based visibility, and retained historical questions
  follow the explicit behavior above. No retention TTL, export or conversation renaming.
- Development rate counters depend on retained messages, and route limits are process-local.
  Production/live-cost enforcement must be durable and shared before activation.
- Previous email-verification, OCR quality/runtime, storage cleanup/cache/retention and
  production deployment/compliance limitations remain. Hosted CI was not run.

## 31. Suggested Git commit

`feat(assistant): add private grounded conversations with bounded context and mock acceptance`

No staging, commit or push was performed. Exclude populated env files, keys, generated
builds and ignored QA artifacts.

## 32. Phase 10 preview — not started

A separately authorized phase could design English/Hindi/Hinglish preferences, translate
only approved explanatory wording, preserve exact evidence/dates/units, and evaluate
multilingual routing, safety and accessibility. It needs its own acceptance criteria and
must preserve the provider blocker and synthetic-only live authorization boundary.
No translation or voice infrastructure was implemented.

**STOP after Phase 9. Do not begin Phase 10 without the owner's next authorization.**
