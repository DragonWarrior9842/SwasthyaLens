# Phase 12 voice decision — 2026-09-29

Select optional browser speech with mandatory local processing; text remains the
guaranteed interface. No external speech SDK/provider, credentials, paid service,
new server endpoint, schema, audio storage or language-pack download is added.
This is a bounded development choice, not production speech acceptance.

## Alternatives evaluated before implementation

| Concern | Browser local-only (selected) | Bundled offline engine | Cloud STT/TTS (not proposed) |
|---|---|---|---|
| Desktop/mobile | Experimental recognition; runtime checks required on Chrome/Edge. Mobile can fall back to text. Local TTS voice availability varies. | WASM/native runtime and models need packaging, device memory/performance testing and maintenance. | Audio upload can broaden client coverage, but adds service/network dependency. |
| English/Hindi | Separate en-US/hi-IN pack checks and language-matched local voices. Accuracy and pronunciation are unmeasured. | Multilingual engines exist; English/Hindi medical accuracy would require evaluation. | Provider-specific quality requires evaluation; no quality or free-tier claim. |
| Hinglish | No reliable dedicated locale selected; editable English/Hindi recognition, no Hinglish TTS. | Mixed-language quality unverified. | Mixed-language quality unverified. |
| Privacy/retention | Require local processing contract; no app audio capture, upload, logging or persistence. Browser handles transient audio. | Could be fully local with controlled model assets; app would own more audio processing and disposal code. | Audio and/or response text leaves the device; retention/training terms require review and explicit approval. |
| Cost/credentials | No application API fee or credentials; existing browser/OS resources only. | No per-call cloud fee; model distribution, CPU/RAM and maintenance costs. | Pricing, free tier, credentials and retention must be established for a named provider before approval. None selected. |
| Latency/reliability | No speech network dependency once local assets exist; actual latency unmeasured. Unsupported capabilities fail closed. | Device-dependent model load and inference latency; unmeasured. | Network/service latency, access/quota failures and separate rate limits. |
| Accessibility/complexity | Native labeled buttons, status, editable transcript and text fallback; small adapters. | Same UI obligations plus audio/model runtime lifecycle. | Same UI obligations plus authenticated bounded transport, privacy consent and provider operations. |

Browser-native alone is **not** a privacy guarantee. The normal recognition default
allows remote processing. This implementation accepts only the unprefixed API with
`available({langs:[language], processLocally:true}) === 'available'`, and an existing
`processLocally` property set and verified as `true` before `start()`. No legacy or
remote fallback and no `install()` call. See [MDN local processing](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition/processLocally),
[availability](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition/available_static)
and the [Web Speech specification](https://webaudio.github.io/web-speech-api/).

TTS accepts only matching-language voices with `localService === true`, as defined
by [MDN localService](https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesisVoice/localService).
The browser/OS remains a trust boundary: these are API-contract guarantees, not an
independent audit of installed browser binaries, OS telemetry or physical devices.
The app sends no audio to its backend; only a reviewed, explicitly sent question
enters ordinary private assistant-message persistence.

[MDN compatibility data](https://github.com/mdn/browser-compat-data/blob/main/api/SpeechRecognition.json)
reports desktop Chromium local APIs from 139, with Android/Safari gaps. Version alone
does not establish available language packs. A microphone-free headless probe here
found Chrome 153.0.8010.53: en-US/hi-IN `downloadable`; Edge 154.0.4258.37:
both `unavailable`. Both exposed the API but no local TTS voices in that headless
session. No microphone, playback or pack download was attempted. This is capability
inspection, not physical-device acceptance.

[whisper.cpp's WASM example](https://github.com/ggml-org/whisper.cpp/tree/master/examples/whisper.wasm)
demonstrates a maintainable upstream offline alternative, but bundling and validating
it would substantially expand this phase. No model/runtime is installed. Cloud speech
is unnecessary for a truthful optional enhancement. Any future proposal must stop
for the user's explicit provider/pricing/privacy/credential approval.

## Baseline before code changes

At commit `46508f7`: frontend lint/typecheck, 323 tests/15 files and production build
passed (existing >500 kB main-chunk warning). Backend Ruff, 107 formatted files,
mypy 104 source files, 635 tests passed/22 gated skips; nine local OCR evaluations
passed. Initial sandbox mypy cache failure resolved by the approved unrestricted
check; no code fix required. All 13 live Supabase tests passed in 665.04 seconds;
all 22 rollback SQL verification scripts and all 119 established browser groups
passed. Logs: ignored `.cache/qa/phase12-baseline-{live,browser}.log`.
Security advisors unchanged: three intentionally default-deny private Phase 7
tables and disabled leaked-password protection; performance advisors clear.
Gemini ledger remains 2 attempts and 50 reserved cents; live AI flag unset.

## Implementation constraints

- Voice off by default for each Assistant visit/account; no portable browser voice ID preference.
- Recognition language selected independently of interface and response language.
- Explicit Start, permission status, 30-second listening limit, Stop/Cancel and bounded startup/finalization.
- Final transcript remains transient and editable; explicit use in composer, then normal Send. No medical normalization.
- Playback reads the frozen rendered answer paragraph unchanged, never source retrieval or automatic generation.
- Cancel on hiding/leaving, conversation/account changes, disabling voice and source invalidation. No automatic restart.
- Synthetic API mocks test logic; physical speech quality, hardware, permission dialogs and OS output remain manual checks.
- Gemini/OpenAI remain untouched; no Phase 13 work.
