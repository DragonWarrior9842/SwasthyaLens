# Phase 10 — multilingual interface and grounded responses

Phase 10 is implementation-complete and its offline, live Supabase, SQL and browser
acceptance checks have passed. Live-provider multilingual quality remains unverified.
No Phase 11 or Phase 12 work has started. No live AI request, provider/model switch,
billing change, external translation service, voice feature or export was introduced.

**Gemini acceptance remains externally blocked: 2/20 attempts used.** Both previously
authorized synthetic requests returned HTTP 503 UNAVAILABLE due to high demand.
No 401/403, 429, explicit quota exhaustion or quota values were returned.
`RUN_AI_INTEGRATION` remained unset throughout Phase 10. A read-only budget check
confirmed `gemini_attempts=2` and the unchanged `reserved_cents=50` ledger value.

## 1. Architecture and independent language models

| Concept | Representation | Scope |
|---|---|---|
| Interface locale | Existing `user_settings.preferred_language`: `en`, `hi` | Application labels, controls, feedback and document `lang` |
| Assistant preference | New `user_settings.assistant_language`: `en`, `hi`, `hinglish`; default `en` | New responses only |
| Frozen turn language | New `assistant_messages.response_language` | Reserved message pair, output verification and historical rendering |
| Original report language | Existing original text/source metadata | Never inferred from preferences or overwritten by translation |

The browser loads owned settings after authentication through the existing backend.
It updates presentation after a successful settings save and sends a content-free
cross-tab notification so another tab can re-read its own settings. Owner checks,
abort/revision guards and an English default prevent another account's preference
from being displayed. No preference, token, health record or conversation is stored
in localStorage. Signed-out screens default to English.

The two language controls are separate, text-labeled native selects. A language-only
save omits timezone; it does not emit the medical-history refresh event, log out,
remount the conversation, discard the draft or generate an answer.

## 2. Files created and modified

Created for Phase 10:

- `backend/app/core/assistant_language.py` — deterministic overrides and closed Hindi/Hinglish wording.
- `backend/tests/test_multilingual.py` — 100 offline language/grounding/safety cases.
- `backend/tests/integration/test_live_multilingual.py` — real two-user settings and frozen-turn checks with an injected mock.
- `backend/tests/browser_multilingual.cjs` — 14 explicit Chrome acceptance groups.
- `database/migrations/20260926182238_multilingual_preferences.sql` and `database/verification/multilingual.sql`.
- `frontend/src/i18n/core.ts`, `hindi.ts`, `LocaleProvider.tsx`, `core.test.ts`.
- `frontend/src/services/fixtures/multilingual.json` — synthetic v1/v2 mixed-history fixture.
- `docs/phase-10-decision.md` and this handoff.

Modified backend: `core/accounts.py`, `core/assistant.py`, `core/assistant_context.py`,
`core/explanation_provider.py`, `schemas/accounts.py`, `schemas/assistant.py`,
`tests/auth_support.py`, `tests/test_auth.py` and regression fixture assertions.

Modified frontend: `App.tsx`, `types/auth.ts`, `styles/index.css`; account, assistant,
observations and report services; account tests; all eight page components; application
layout; Brand/Sidebar/ErrorState/LoadingState; auth controls; observation/publication,
report/upload/extraction/review/explanation, API status, trend/chart components.
Changes are explicit application-copy calls, preference handling and strict decoding;
source fields and saved message bodies bypass translation.

Updated `README.md`, `database/README.md` and the assistant SQL lifecycle verification.
Ignored local QA scripts/screenshots/logs remain under `.cache/qa/phase10` and related
earlier-phase QA directories. No key or environment file is part of these changes.

## 3. Schema, migration and settings API

Migration **20260926182238 / multilingual_preferences** is applied to development.
Its local filename matches the hosted migration history. Fresh installations apply
it after Phase 9. It reuses `preferred_language`, adds only the independently needed
assistant preference and per-message language, and constrains all enums.

Existing messages retain their content/answer; their added language defaults to
English. Legacy prompt/schema v1 remains supported. New rows default to
`assistant-evidence-v2` / `assistant-closed-v2`. The database accepts only paired
versions; v1 must be English. No source record or historical answer is translated.

`GET/PATCH /settings` retains its existing contract and adds `assistant_language`.
Unsupported values, explicit null, ownership/audit-field injection and invalid
interface `hinglish` values are rejected. Existing profile/timezone behavior remains.
There is no redundant language endpoint and no browser-selected owner/evidence list.

## 4. Exact precedence and version strategy

An unambiguous supported language request in the **current question** overrides the
saved assistant preference; otherwise the saved preference applies, defaulting to `en`.
Recognized phrases are case-insensitive:

| Result | Supported requests |
|---|---|
| English | `in English`, `English mein/me`, `अंग्रेज़ी में`, `अंग्रेजी में` |
| Hindi | `in Hindi`, `Hindi mein/me`, `हिंदी में`, `हिन्दी में` |
| Hinglish | `in Hinglish`, `Hinglish mein/me`, `हिंग्लिश में` |

Requests naming multiple different languages fall back to the saved preference.
Script alone is not language detection. Earlier questions, report content and source
labels do not set response language. No sensitive attribute is inferred.

The existing worker-gated reservation RPC reads the owned settings row under a lock
and freezes the selected language for both rows of a new turn. Idempotent replay
returns the original turn without re-reading preferences or calling a provider.
Finishing a v2 turn with a different/missing returned language is rejected. Backend
and browser also reject inconsistent version/language metadata.

The model's strict structured output adds required `response_language` to the existing
educational scope, exact ordered evidence IDs, closed explanation code, limitation and
follow-up enums. Returned language must equal the context language. Prompt/schema v2
is explicit; v1 answer text remains byte-for-byte unchanged. Future wording revisions
must retain the corresponding historical v1/v2 catalogs rather than editing saved text.

## 5. Frontend i18n and coverage

A typed local dictionary contains **669 application-copy entries**, with English
source keys and Unicode Hindi values. No new translation library/service is needed.
`t()` accepts catalog keys and interpolates exact string parameters. `copy()` is
restricted to application-owned dynamic labels/errors and structured transient
messages. Unknown entries deterministically fall back to readable English. Tests
audit static calls, visible JSX, central dynamic catalogs, placeholders and nonblank
translations. Source labels, filenames, OCR text, flags, values and saved answers
are never passed through dynamic translation.

English and Hindi cover navigation, dashboard, reports, uploads, extraction/processing,
parameter review, publication/history, trends, account settings, assistant controls,
errors, loading/empty states and educational/safety copy. Metric display labels and
closed status labels are separate from original report labels. Transient upload or
deletion messages retain structured parameters so switching locale can redraw them
without rewriting filenames or errors into stored medical data.

Hinglish is a professional Latin-script Hindi response mode, not a fake UI locale.
Fixed wording keeps recognizable parameter names and medical units. It avoids slang,
diagnostic interpretation and automatic transliteration of source text.

The small catalog is local and requires no API call when switching. One settings read
per authenticated provider mount and one read per cross-tab settings notification are
used; changes in the same tab consume the successful PATCH response. Existing periodic
conversation reads remain independent of language changes. No automatic generation occurs.

## 6. Exact medical facts, provenance, dates and numbers

The Phase 9 context builder still retrieves only current authorized reviewed/published
observations or supported manual measurements. There are at most five facts for a metric,
20 for one report, four prior user questions (500 characters each) and 24,000 UTF-8 bytes
of serialized input. Normalized language metadata does not broaden retrieval. Source
text and dialogue remain untrusted; previous generated prose is never evidence.

Opaque `e1`–`e20` and optional `t1` IDs remain request-local. Every returned ID, order,
code, enum and output field is validated; additions, omissions, duplicates, foreign IDs,
unsupported claims and malformed language are rejected. Facts are rendered from server
data, not provider-authored measurements. Provenance/revision/page links remain intact.

Across all three response modes, tests preserve `13.20`, `18`, `2.4`, `<5`, `>10`,
`0.4–4.0`, `30–100`, `1:80` and exact units `mg/dL`, `g/dL`, `ng/mL`, `mIU/L`, `kg`,
`bpm`. Structural edge-case fixtures are synthetic, not clinical interpretations.
The same Vitamin D evidence remains **18 ng/mL, reference 30–100**, with an unknown
measurement date. No locale formatter parses or rounds source strings.

UTC timestamps keep their instant semantics; supplied report dates remain day-only.
Unknown dates are explicitly labeled unknown in every supported mode. Existing date
presentation is intentionally conservative (ISO/UTC or the existing date formatting);
language does not change timezone, substitute upload time or fabricate a clinical date.
OCR language/source metadata and original Unicode text remain unchanged.

## 7. Trends, correlation and assistant behavior

Increasing/decreasing describe deterministic mathematical comparisons. Stable remains
within mathematical tolerance and never implies healthy, normal or safe. Insufficient
data never produces an invented trend. Unsupported correlation remains unsupported,
with explicit wording that association does not establish cause and effect. The
existing six-decimal computed-statistic rules and exact-value table are unchanged.

The provider-neutral request carries normalized language and the v2 strict schema.
The deterministic mock returns the permitted structured selection for testing only.
Production/development has no mock switch or test-module import; the real assistant
capability remains locked. Rules-based clarification, safety, emergency and unsupported
responses work in all three languages. Evidence-bearing real questions persist with
an honest unavailable state; suggestions/reuse only populate the composer.

Source corrections/deletions retain existing invalidation, clear derived answers and
links, and prevent stale in-flight commits. Language-only changes do not stale answers.
Conversations can contain legacy English, Hindi and Hinglish replies simultaneously.
Saved answer prose is never retranslated when either preference changes.

## 8. Safety, adversarial tests and provider boundary

The 100 multilingual backend cases include 18 exact-fact/language combinations,
four equivalent question forms, override/ambiguity checks, 36 Hindi/Hinglish
adversarial/language combinations, six obvious emergency phrases, 15 closed-semantics
cases, malformed-output checks, invalid settings, catalog consistency and mixed-history
validation. Examples include ignoring instructions, another user's reports, API keys,
changing 18 to 80, claiming cancer and changing medication. Safety queries never retrieve
records; injected labels/history do not change the authorized evidence or language.

No tools, web/file search, code execution, database/storage access or external data
are provided to a model. The existing provider request still explicitly has
`store=false` and empty tools. Normal pytest clears AI environment variables and
blocks real OpenAI/Gemini HTTP transports, including live Supabase tests. No API key
is exposed to the browser, logs, fixtures or handoff.

Provider/model selection remains **Gemini `gemini-3.8-flash` for the previously bounded
synthetic evaluation only**, with no production healthcare-provider decision.
Free Tier may use submitted data to improve Google products. No real health data was
submitted; no live multilingual model behavior has been verified. A later provider
test requires new explicit authorization, one synthetic request, the explicit integration
gate, no automatic retry/model/billing change, immediate stop on provider error and
unsetting the flag afterward. Phase 10 does not authorize that request.

## 9. RLS, sessions, limits and accessibility

Forced owner/active-session RLS, CSRF/origin validation, server authorization, revoked
session checks, private helper schema and narrow column grants remain. The public RPC
is still an invoker wrapper; its private writer still requires the server worker secret
and owner JWT. No service-role key or broadly exposed security definer was added.

Limits are unchanged: 20 conversations, 25 pairs each, one pending generation per owner,
two globally, six new messages/minute and 100/day over retained messages; 60 API requests
per minute per owner at the process boundary. Context/generation has a 60-second deadline,
the existing provider deadline is 45 seconds, browser send timeout 75 seconds, and pending
turns expire after 90 seconds on the next owned operation. No retry was added. These
development limits are not a durable production paid-provider quota; see Phase 9.

Document `lang` follows `en`/`hi`. Saved reply paragraphs use `en`, `hi` or `hi-Latn`
according to their frozen language. Native selects have visible labels and keyboard
focus; flags are not used as language controls. System fallbacks include Nirmala UI,
Mangal and Noto Sans Devanagari without downloading fonts. Hindi line height/wrapping
and mobile selects were checked at 375px. Inspected screenshots show readable glyphs,
mixed Latin units and no horizontal overflow. This is targeted accessibility acceptance,
not a comprehensive screen-reader or WCAG certification.

## 10. Verification results

| Check | Result |
|---|---|
| Phase 9 frontend baseline | 277 tests; lint/typecheck/build passed |
| Phase 9 backend baseline | 482 normal tests; Ruff/format/mypy passed |
| Baseline live/SQL/browser | All 11 live checks covered after one fixture correction; 18 SQL scripts; 91 browser groups passed |
| Phase 10 frontend | 296 tests in 14 files; lint/typecheck/build passed |
| Phase 10 backend | 585 passed, 21 explicitly gated skips; Ruff/format/mypy passed (96 typed source files) |
| Local synthetic OCR | 9 passed, explicitly opted in separately |
| Live Supabase | 12/12 passed in one run, including multilingual A/B isolation; injected mock, zero live AI |
| SQL | All 19 verification scripts passed sequentially, rollback-only |
| New multilingual browser | 14/14 groups; zero runtime errors, zero AI requests, zero generation sends |
| Established browser regression | 91/91 groups passed; 105 total including multilingual |

Live results cover auth, profile/settings, reports/storage, OCR and worker interruption,
parameters, observations, trends, assistant grounding/correction/deletion/revocation and
multilingual settings/history. A's Hindi/Hinglish preferences do not affect B's English
preferences. Cross-owner settings reads/updates and conversations are denied, CSRF/null/
unsupported values are rejected, exact `13.20 kg` remains across response modes, history
survives preference changes and replay freezes language. Original test preferences and
test-created data are restored/removed by the fixtures.

The 14 multilingual browser groups cover English controls; independent language saves;
refresh and logout/login persistence; B's isolation; keyboard/font/mobile layout; validation;
dashboard/history/reports/trends empty states; loading/error/upload feedback; exact original
report text and review fields; charts/non-causation; mixed-language historical answers;
cross-tab changes preserving the draft/history; and suggestions without generation.

Regression test corrections preserve unrelated account data rather than assuming empty
accounts. The assistant SQL invalidation assertion is scoped to its synthetic owners.
Established English browser suites run with temporary English preferences and restore
the accounts' original preferences afterward. No existing report is deleted to force
an empty state. A synthetic browser route-matcher error was corrected before acceptance.
An extraction harness startup timeout passed on the isolated continuation; no product
change was required. The final established groups were auth 15, reports 11, extraction 7,
parameters 8, observations 12, explanations 12, trends 13 and assistant 13.

Current security advisors show the existing intentional policy-less private evaluation
tables (deny by default) and the existing leaked-password-protection warning. No language
RLS advisory was introduced. See [Supabase password protection](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection)
and [the private-table advisory](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy).

## 11. Manual checks and limitations

1. Start the normal backend and frontend preview with `RUN_AI_INTEGRATION` unset.
2. Sign in, open Account settings, select Hindi for interface and Hinglish for assistant,
   and save. Refresh, then sign out/in: both preferences should persist.
3. Sign into B in a separate browser profile and leave English selected; A's changes
   must not affect B. Navigate Hindi dashboard, reports, history, trends and assistant.
4. Use only synthetic reports for evaluation. Compare source text, `13.20 g/dL`, units,
   flags, references and unknown dates with their original stored evidence.
5. Create a conversation explicitly. A clarification or obvious safety question yields
   labeled deterministic guidance in the saved response language. Add `in Hindi` or
   `in English` to exercise the current-message override. An evidence-bearing question
   should show provider unavailable; do not expect a fake model answer.
6. Change language in another tab with an unsent draft present. The interface updates;
   the draft and existing message prose remain unchanged, with no generation request.
7. For successful synthetic evidence-answer rendering, run the explicit multilingual
   browser harness or gated Supabase test with its injected mock. The normal UI has no
   mock toggle. Check 375px layout and keyboard navigation.

Limits: deterministic phrase matching is a bounded allowlist, not comprehensive language
understanding or symptom triage. Hindi/Hinglish wording is locally authored; no external
professional linguistic/clinical certification is claimed. Live model multilingual quality
remains unverified. Signed-out UI defaults to English; no third UI locale or report
translation is implemented. Historical generated text deliberately stays in its original
language. Existing dependency deprecation warnings remain. Vite reports the main bundle
at about 504 kB minified / 144 kB gzip, above its 500 kB advisory; the chart remains lazy.
No production deployment or comprehensive accessibility certification was performed.

## 12. Suggested commit and Phase 11 preview

Suggested commit: `feat: add English/Hindi UI and grounded multilingual assistant preferences`

Git publishing remains with the project owner. Phase 11 may address separately authorized
exports, notifications and related settings. Its prerequisites are this verified language
contract, explicit export/retention/consent requirements, exact source-value/provenance
preservation, owner isolation and translated user-facing messages. Live AI activation is
a separate blocked decision. No export, notification, unrelated setting or voice feature
has been implemented. Stop here until a new explicit phase authorization.
