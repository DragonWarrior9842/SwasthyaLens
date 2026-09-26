# Phase 10 language model and implementation boundary

Phase 10 only. No live AI, translation service, provider/model switch, billing
change, exports, notifications or voice work is authorized. Gemini acceptance
remains blocked by two HTTP 503 responses: 2/20 attempts used.
`RUN_AI_INTEGRATION` remains unset.

## Three independent concepts

* **Interface locale:** retain `user_settings.preferred_language` (`en`, `hi`)
  and its existing API name. It controls application copy and document `lang`.
* **Assistant response language:** add `user_settings.assistant_language`
  (`en`, `hi`, `hinglish`), default `en`. Hinglish is professional Latin-script
  Hindi, not a browser locale. Separate labeled settings controls explain scope.
* **Source language:** preserve original OCR text, source method/language metadata,
  labels, quotes and report evidence. Neither preference translates stored sources
  or claims to detect a report's original language.

Settings remain owner-scoped through the existing API, active-session RLS, CSRF
and narrowly granted editable columns. No browser storage is authoritative.

## Assistant precedence and historical integrity

A recognized, unambiguous language request in the **current** question takes
precedence over the saved assistant preference, which defaults to English.
Recognized phrases will be an explicit tested allowlist covering English,
Devanagari and Latin Hindi requests. Multiple different requested languages do
not guess a winner: use the saved preference. Message script alone does not infer
response language. Earlier messages and source text never set the preference.

Freeze the resolved response language when reserving an idempotent turn. A replay
must not re-resolve it after a preference change. New responses use versioned,
closed application wording in the chosen language; the provider receives a
normalized language requirement and must return that exact language enum along
with the exact permitted evidence IDs and explanation code. Legacy v1 English
messages remain readable and unchanged. Language changes never invalidate source
snapshots or regenerate answers; actual source changes retain Phase 9 invalidation.

## Frontend implementation choice

Use a small typed local catalog with English source keys and Hindi translations.
No new dependency or external translation call is needed. Translate explicit UI
copy at React boundaries, never by scanning or rewriting rendered DOM text.
Unknown catalog entries fall back to English; tests audit coverage and placeholders.
Only application-owned labels/errors may use dynamic catalog lookup. Source data
and historical message bodies bypass translation entirely.

Keep health values as exact strings, including precision, operators, ranges,
flags, ratios and units. Keep existing ISO/UTC and supplied-day semantics; unknown
dates remain unknown. Localized display labels must be separate from evidence.
Use system Devanagari font fallbacks, adequate line height and mobile wrapping.

## Baseline findings before feature implementation

Required handoffs, technical audit, README, settings, routing, copy, context,
schemas, provider abstraction and date handling were inspected. Offline checks:
277 frontend tests, lint/typecheck/build; 482 backend normal tests, Ruff/format/mypy;
9 explicitly enabled local synthetic OCR checks. All 18 SQL verification scripts
passed. Initial live run: 10 passed, one test assumed deleting its fixture left
no TSH observations. An unrelated owned report exists; the assertion was corrected
to require removal of the deleted fixture's evidence while preserving other data.

Browser baseline similarly revealed empty-account assumptions and ambiguous
inactive-observation selectors. Test corrections compare original account counts,
use unique fixture names and scope deleted/inactive evidence to the generated
report. No existing report or observation was deleted to force an empty state.
Final baseline results and subsequent Phase 10 results belong in the handoff.
