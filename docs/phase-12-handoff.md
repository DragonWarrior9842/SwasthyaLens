# Phase 12 handoff — optional voice input/output

Date: 2026-09-29. Implementation and isolated voice acceptance are complete;
the final full browser regression is in progress. Physical-device acceptance is
not performed. No Phase 13 work and no live AI request.

## 1. Architecture and decision

Voice is a frontend input/output wrapper around the existing Phase 9 text assistant.
The [pre-implementation decision](phase-12-decision.md) compares browser, bundled
offline and cloud approaches, privacy, retention, English/Hindi/Hinglish, Windows,
mobile, latency, maintenance, accessibility, reliability and costs.

Select browser local-only speech. No external speech SDK or cloud provider is proposed
or added; no speech credentials, environment variables, per-call service fees or
billing change. Any future cloud proposal must stop for explicit owner approval.
The existing Gemini/OpenAI abstraction is untouched.

```text
Explicit enable -> select input language -> check installed local capability
  -> explicit Start -> native microphone permission -> bounded local recognition
  -> editable transient transcript -> explicit Use reviewed transcript
  -> existing question composer -> explicit Send -> existing owned assistant API
  -> authorized rendered text -> optional explicit local Read aloud -> Stop
```

## 2. Speech-to-text implementation

`frontend/src/features/voice/speech.ts` contains injectable browser adapters and
observable controllers; `VoiceControls.tsx` contains small input/output components.
React uses `useSyncExternalStore`; browser logic stays outside the Assistant page.
No dependency was installed. Only unprefixed `SpeechRecognition` is considered,
in a secure context. Capability checks require static `available()` with
`processLocally:true`, the selected language, and an exact `available` result.
Downloadable/downloading/unavailable/unknown states fail closed; no `install()` call.

At explicit Start, the recognizer must already expose `processLocally`; assigning a
new expando property to an old browser cannot pass this check. Set it to `true` and
verify before `start()`. Set the explicit language, final results only, one alternative,
and continuous recognition. The browser's full final-result snapshot replaces the
previous snapshot; pieces are joined with spaces, with no numeric or medical parsing.
At most 128 result segments and 2000 transcript characters; oversize/malformed output
is rejected, never silently truncated. Errors expose only generic translated copy.

## 3. Text-to-speech implementation

Each rendered authorized answer paragraph can be explicitly read aloud when voice
is enabled. The controller selects only `localService === true` and a matching
English/Hindi language prefix. It passes the exact `answer.text` to the utterance,
with that voice and language; no translation, normalization, rewriting or retrieval.
Expanded evidence tables, source links and calculations are not synthesized.
The visible text and original source remain authoritative for pronunciation ambiguity.

Start, Stop, native pause/resume and explicit replay are provided; missing voices,
interruption and synthesis failure retain readable text. A voice-list query is repeated
on each explicit start, accommodating asynchronously available OS voices. No automatic
retry, default remote voice, fallback language, or autoplay. A page-level coordinator
allows one utterance or one recognition stream at a time; starting one cancels the other.

## 4. Does audio leave the device?

Under the selected browser API contract, recognition must run locally, and selected
TTS voices must be local services. Ordinary browser recognition is **not automatically
private**; the default that permits remote recognition is deliberately unsupported.
See the cited [local-processing contract](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition/processLocally)
and [local voice distinction](https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesisVoice/localService).
Browser/OS implementation and telemetry are trust boundaries, not independently audited
by this phase. No physical/network capture certification is claimed.

SwasthyaLens never receives a raw audio buffer, calls MediaRecorder/getUserMedia,
uploads audio, or intentionally stores audio in a database, Storage, localStorage,
sessionStorage, IndexedDB, cache or logs. Native recognition handles transient audio.
Only explicitly reviewed and sent text reaches normal private assistant persistence.

## 5. Privacy and preferences

Voice defaults off. The toggle exists only in the current Assistant workspace; leaving
the route/account resets it. No browser-specific voice IDs or new settings are saved.
Recognition language defaults visibly to English in each input component and is changed
explicitly; it does not infer ethnicity/nationality or follow interface language silently.
No transcript, response or audio telemetry is added. No speech transport exists.

## 6. Language support and Hinglish

- English recognition: explicit `en-US`, only with a confirmed installed local pack.
- Hindi recognition: explicit `hi-IN`, subject to the same capability check.
- English/Hindi playback follows the frozen message language, including legacy English
  messages while the UI is Hindi. Current settings never rewrite historical answers.
- Hinglish input has no dedicated locale guarantee. Users may select English or Hindi,
  inspect and correct the transcript. Hinglish playback is explicitly unavailable.
- All new controls/status/error/privacy copy have English/Hindi entries in the existing
  typed i18n catalog. Hindi wording is locally authored, not externally certified.

## 7. Permission and recording flow

Enabling voice and checking availability never starts the microphone. Start is a native,
keyboard-accessible explicit button; the browser prompts if it needs permission.
Already-granted permission may not prompt again. Starting/listening/stopping states
are visible and announced, including a textual active-microphone indicator. Stop and
Cancel remain available while waiting/listening. Denial/dismissal never trigger a retry
or prevent typing; browser permission settings remain under the user's control.

Bounds: local capability query 10 seconds; permission/startup 15 seconds; listening
30 seconds from recognition start; finalization after Stop 3 seconds; playback 120 seconds
including pauses. Timers request native stop/abort/cancel and invalidate late callbacks.
Native hardware teardown ultimately depends on the browser. No microphone quality,
physical permission-dialog or OS-output claim is inferred from mocks.

## 8. Transcript editing and send

Finalized speech enters a separate labeled editable textarea. Review wording explicitly
requires checking numbers, words and units. Nothing is submitted when speech ends.
Use reviewed transcript appends the exact edited text to an existing typed draft with
one separating newline, then focuses the normal question field. The combined 2000-character
limit rejects overflow without replacing/truncating the draft. The user must separately
press Send. Routine conversation refresh preserves the pending review and input language;
copy/start actions are disabled until the current thread read is valid.

Cancel discards pending audio and the unsubmitted voice transcript. It does not erase
ordinary typed text or text already explicitly copied to the composer. No automatic
fixing of 18/80, decimal points, TSH, Vitamin D, units or ranges occurs.

## 9. Assistant integration, grounding and safety

The same `sendMessage` service sends only `{content,idempotency_key}` through the
existing account-owned mutation and CSRF path. No voice endpoint or special trust bit.
Server-selected bounded evidence, strict schema/evidence checks, current-account
verification, session revocation checks, ownership, RLS, idempotency, timeouts and rate
limits remain unchanged. The assistant API retains 60 requests/minute/user, with the
existing durable conversation/generation controls. STT itself is local and duration-bounded.

Spoken/transcribed measurements never create observations, reports, history or profile
facts. Emergency/injection phrases use the existing deterministic Phase 9 route, including
Hindi. That phrase screen remains deliberately narrow; voice adds no medical triage or
diagnostic promise. Normal providers remain mock/locked and consume no live AI credits.

## 10. Playback privacy and cancellation

Playback requires a separate click per response; enabling voice, opening a chat, sending
a question or receiving an answer never speaks. The UI asks users to consider their
surroundings. TTS gets only the already-rendered answer paragraph, not database/storage
access, report bodies or a new context query.

Disable voice, leave the page/conversation/account, hide the document, receive a session
change or source-change signal: active speech stops and transient input is discarded.
Pending callbacks are detached and guarded; cancellation never sends. Source-refresh
unmount removes stale playback controls; malformed answer contracts remain rejected.
Existing polling/focus/event freshness limits remain: there is no new instant remote
revocation or remote source-change push guarantee beyond the existing assistant behavior.

## 11. Accessibility and mobile

Labeled native buttons/selects/textarea, live status text, visible Stop/Cancel, keyboard
operation and 44px voice button minimum heights. No icon/color-only recording state.
Transcript review and playback completion have explicit status announcements. Controls
wrap at 375px without horizontal overflow; all text remains available. Native permission
dialogs, screen reader hardware, onscreen keyboards and real audio output need manual
checks. Voice is an enhancement, never an accessibility replacement.

## 12. Browser compatibility and capability probe

Local recognition is experimental; runtime capabilities and installed packs decide,
not user-agent sniffing. Current [MDN compatibility data](https://github.com/mdn/browser-compat-data/blob/main/api/SpeechRecognition.json)
shows desktop Chromium support with Android/Safari gaps. Unsupported browsers show
translated typing fallback. TTS additionally needs installed local matching-language voices.

Microphone-free headless checks on this machine:

| Browser | API / local property | en-US / hi-IN pack | Local TTS voices |
|---|---|---|---|
| Chrome 153.0.8010.53 | Exposed | downloadable / downloadable | none returned |
| Edge 154.0.4258.37 | Exposed | unavailable / unavailable | none returned |

No packs were downloaded and no mic/playback was activated. These results do not prove
the same inventory in a normal desktop profile. Android/other physical devices were
not available for acceptance. English/Hindi accuracy and pronunciation are unmeasured.

## 13. Deterministic voice test results

48 new frontend speech tests passed without hardware or network: explicit start;
no prefixed/insecure fallback; local-setting enforcement; pack availability and timeout;
permission dismissal/denial, capture errors, no speech, language/network failure;
final versus interim snapshot handling; malformed/oversize rejection; 30-second stop,
3-second finalization, cancellation and late callbacks; local voice language filtering;
no remote/Hinglish fallback; exact text, replay/pause/stop, failure and output deadline;
microphone/playback mutual exclusion. Every test asserts no fetch call.

Literal synthetic strings preserved: `13.2`, `18`, `80`, `2.4`, `0.4`, `30–100`,
`TSH`, `Vitamin D`, `mg/dL`, `ng/mL`, `bpm`, `kg`, Hindi text and injection text.
TTS also preserves `<5` and `≥10`. This verifies transport/control behavior, **not ASR
recognition accuracy or audible numeric pronunciation**.

## 14. Automated browser acceptance

`backend/tests/browser_voice.cjs`: 19 groups passed in the isolated run, using deterministic
speech constructors and real A/B sessions/CSRF/assistant API. No physical microphone,
speech output or model request. Covers default off/no auto-send; keyboard Start;
numeric edit/review/refresh/send; draft append/overflow; Stop/Cancel/late events;
permission denial/pending cancellation; missing packs/API; mic/no-speech errors;
English/Hindi emergency and injection rules; two-user and CSRF boundaries; exact local
TTS/pause/replay/stop/remote rejection/errors; frozen legacy/English/Hindi/Hinglish;
375px Hindi UI; source invalidation; hidden document/disable; logout cleanup.

The first run exposed a harness fixture index error (the multilingual fixture contains
both legacy English and v2 English before Hindi). Corrected the test indices and reran
successfully. No provider/model switch or weakening of assertions. Mobile screenshot
review found no horizontal overflow; account identity is masked. Generated artifacts
are ignored under `.cache/qa/phase12/`. Final full regression status is recorded below.

## 15. Physical-device verification status and checklist

**Not performed.** All speech success cases are simulations. Before claiming actual
voice support, test synthetic phrases only in desktop Chrome and Edge; Android Chrome
and other target browsers if available. Keep live AI disabled.

1. Start backend/frontend using README commands. Sign in; type/read normally without
   enabling voice. Verify no microphone prompt on page load/login/chat/answer arrival.
2. Enable voice; choose English explicitly and check local availability. If unavailable
   or downloadable, verify truthful text fallback. Do not enable remote recognition.
   This phase provides no pack-install workflow; use a browser with installed local
   support for hardware acceptance. Do not assume API presence means a usable pack.
3. Start, allow native permission and confirm browser and app microphone indicators.
   Speak the synthetic numeric/unit list above; Stop. Compare transcript to what was
   spoken; edit mistakes manually. Use reviewed transcript, inspect composer, then Send.
4. Repeat for Hindi with `hi-IN` when available. Deliberately mix Hindi/English and
   record inaccuracies; do not infer reliable Hinglish support. UI and response-language
   preferences must remain independent of this selector.
5. Deny/dismiss permission, disconnect/unavailable mic, say nothing, cancel during
   permission/listening/review, exceed 30 seconds, switch tabs/hide, disable voice and
   leave the route. Verify capture stops, no late transcript/send and typing still works.
6. Try two 1999+ character draft/transcript combinations; overflow must retain both for
   editing. Verify 18/80 are never silently changed. Refresh a conversation during review.
7. Explicitly read English/Hindi frozen responses using available local voices. Confirm
   sound only on click, Stop, pause/resume (OS-dependent), replay and no overlapping mic.
   Compare audible values/units to displayed text; report pronunciation defects.
8. Test absent/remote-only voices and Hinglish: readable fallback, never remote synthesis.
   Correct/delete a synthetic source in another tab, switch conversation/account and
   sign out while speaking; controls and audio should stop on existing invalidation.
9. On a physical mobile device, verify permission dialogs, onscreen keyboard, editable
   transcript scrolling, reachable Stop/Cancel, long answers, tab order and screen-reader
   announcements. A desktop viewport simulation does not verify these hardware behaviors.

## 16. Security and live two-user results

No backend, database, policy, session or provider implementation changed. Before edits,
all 13 live Supabase tests passed, including ownership/revocation, report/storage, OCR
and worker recovery, parameters, observations, explanations with mocks, trends,
assistant/multilingual, exports and notifications. The new browser suite additionally
verified B cannot read or submit to A's conversation (404), missing CSRF rejects (403),
logout protects reads (401), and voice questions do not increase trusted observation count.
No keys, credentials, personal reports or real patient data were exposed or added.

Unchanged advisors: three intentionally default-deny Phase 7 private tables have
[RLS without policies](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy);
[leaked-password protection is disabled](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).
Performance advisors had no findings. No billing/security configuration changed here.

## 17. Regression results

| Check | Result |
|---|---|
| Pre-change Phase 11 baseline | All requested suites passed; details in the decision |
| Frontend lint/typecheck | Passed after voice implementation |
| Frontend unit/contract tests | 371 passed, 16 files (48 new speech tests) |
| Production build | Passed; main 547.76 kB / 155.48 kB gzip, CSS 37.69 / 8.96 kB; existing >500 kB warning remains |
| Backend Ruff/format/mypy | Passed; 107 formatted files, 104 typed source files |
| Backend tests | Final rerun: 635 passed / 22 opt-in skips in 34.33 seconds |
| Local OCR evaluation | 9 passed before edits; OCR code unchanged |
| Live Supabase regression | 13 passed / 665.04 seconds before edits; backend/schema unchanged |
| SQL | All 22 rollback verification scripts passed before edits; no schema/RLS changes |
| Established browser regression | Baseline 119 groups passed; final rerun in progress |
| Voice browser simulations | 19 groups passed in isolated run; included in final rerun |
| Physical speech/device tests | Not performed |

Existing backend Starlette/httpx/anyio deprecation warnings remain. The initial sandbox
mypy/cache write limitation was resolved with the approved normal cache access; no
dependency upgrades or assertion relaxations. Local OCR's sandbox pytest cache warning
did not affect its nine passing results.

## 18. Reproduction

Normal frontend: `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build`
from `frontend`. Normal backend: `.venv/Scripts/python.exe -m ruff check .`,
`-m ruff format --check .`, `-m mypy`, `-m pytest -q` from `backend`.
Keep `RUN_AI_INTEGRATION` absent. No API credits, mic or speech models are required.

For synthetic browser acceptance, start the usual backend/preview, configure only
the existing ignored `.env.integration` with confirmed disposable A/B accounts, and
ensure their interface preference is English at entry (restore it afterward). Set
`PLAYWRIGHT_MODULE` to the installed Playwright module when needed, then run
`node backend/tests/browser_voice.cjs` from the repo root. The harness restores its
temporary Hindi preference, deletes its synthetic conversation and signs out both
contexts in cleanup. The existing ignored Phase 10 wrapper used for this run also
sets/restores both accounts' English regression preferences.

Do not commit credentials, generated screenshots/logs or private browser profiles.
The harness logs generic stage names, not question contents, raw errors or credentials.

## 19. Gemini blocker

Gemini remains externally blocked at **2/20 attempts** after two previously authorized
synthetic HTTP 503 UNAVAILABLE responses. No prior authentication failure or explicit
quota exhaustion/value was returned. No new live AI request, automatic retry, provider
switch, billing upgrade or funding change occurred. `RUN_AI_INTEGRATION` remains unset.
The pre-change ledger was 2 attempts / 50 reserved cents; final read-only confirmation
will be recorded after regression. API keys remain private. Voice does not reopen Phase 7.

## 20. Files created/modified and schema

Created for this phase:

- `frontend/src/features/voice/speech.ts`
- `frontend/src/features/voice/VoiceControls.tsx`
- `frontend/src/features/voice/speech.test.ts`
- `backend/tests/browser_voice.cjs`
- `docs/phase-12-decision.md`, `docs/phase-12-handoff.md`

Modified: `frontend/src/pages/AssistantPage.tsx`, `frontend/src/i18n/hindi.ts`,
`frontend/src/styles/index.css`, and `README.md` (also corrects its stale pre-Phase-11
intro). No database/schema migration, backend runtime change, new package, env file,
audio storage, provider key or permissions/billing configuration change.

## 21. Known limitations

Optional local-only recognition can be unavailable on many devices; this installation's
headless profiles had no ready packs/voices. No automatic/manual pack installer is
included. Browser native permission and synthesis behavior varies; stop is the reliable
UI alternative to platform-dependent pause/resume. Browser timers and teardown cannot
certify faulty browser/OS behavior. Existing session/source freshness is event/poll based.
One active speech operation per page, no cross-device preference or audio export/history.
Review can still miss an ASR mistake; no acoustic/numeric/medical accuracy claim.
No reliable Hinglish voice claim, physical hardware certification, production availability
or clinical validation. Text and source evidence remain primary. Live AI acceptance remains
blocked independently; deterministic safety/clarification responses remain usable.

## 22. Suggested commit

The owner committed the first implementation as `48d8642` (`Success`) during acceptance.
This handoff covers the entire phase, including subsequent refresh/accessibility fixes,
harness verification and documentation. No agent commit or push.

Suggested complete-phase message: `feat: add optional local voice input and read-aloud`.
Remaining closure message: `test: verify Phase 12 voice safety and browser regressions`.

## 23. Phase 13 prerequisites — preview only

Phase 13 remains **unstarted**. A later explicitly authorized scope should decide release
inclusion of optional voice, conduct physical-device and accessibility acceptance, resolve
the independent live-AI blocker if desired, and define staging/production privacy,
availability, operations and hardening requirements. No infrastructure rollout, production
credential, external speech provider or hardening change was started here. Stop after this
phase and wait for the owner's next explicit authorization.
