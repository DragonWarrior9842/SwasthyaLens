# Phase 5 handoff — structured parameter candidates

Phase 5 adds explicit, source-grounded candidate extraction and personal review.
It does not create health observations, diagnoses, explanations, recommendations,
trends, or clinical validation. No LLM, external AI provider, new dependency,
credential, or environment variable was introduced. Stop here; Phase 6 requires a
new explicit instruction.

## Architecture and technology

The pre-implementation [decision](phase-5-decision.md) evaluated deterministic
parsing, lexical rules, layout, aliases, NLP and LLM extraction. The selected
parser is a small bounded Python grammar over persisted Phase 4 pages. It never
downloads arbitrary URLs or accepts browser-supplied machine source text.

The owner selects a completed text attempt, then explicitly requests parameter
extraction. The BFF verifies the session and ownership, loads that attempt's pages,
reserves a durable parameter attempt, parses synchronously, and atomically commits
the candidates. A parser failure publishes no partial candidates. There is no
automatic processing chain, background LLM call or medical interpretation.

Supported structure:

- Explicit pipe-separated tables with `Parameter`/`Test`/`Test name`/`Sample label`/
  `Investigation`, then `Result`/`Value`, and optional Unit, Reference and Flag
  columns. Empty cells preserve missing values rather than borrowing another row.
- Compact tables with the same supported English header grammar and a unique
  label/value/unit/reference decomposition. When a Unit column is declared,
  compact rows must contain a unit; missing units need explicit cells to be safe.
- Adjacent rows and repeated vertically separated tables. A wrapped name is joined
  only when the adjacent pieces form an exact configured alias; its original
  newline remains in the raw label and source quote.
- No fuzzy medical dictionary, general prose extraction, unrestricted table
  reconstruction, handwriting interpretation, or multi-column inference.
  Repeated side-by-side headers, ambiguous decompositions and unparseable sections
  cause abstention. Prose ends a table. Native line rectangles are linked only
  when their text uniquely matches the source quote. OCR word rectangles are not
  guessed into candidate regions.

## Data model and provenance

Two versioned migrations are applied to the existing development project:
`20260916165018_structured_parameter_candidates.sql` and
`20260917052948_parameter_source_index.sql`. CLI-generated local filenames were
aligned with the hosted migration timestamps. Existing migrations were not edited.

| Table | Purpose |
| --- | --- |
| `report_parameter_runs` | Report and source-attempt links, idempotency key, attempt number, status, extractor/rules versions, deadline, timestamps, error, candidate count and warnings |
| `report_parameter_candidates` | Immutable machine content, ordered candidate number, source run/page composite FKs, creation timestamp |
| `report_parameter_reviews` | Append-only personal action and fields snapshot, candidate FK, revision, actor, timestamp and idempotency key |

The chain is original report → Phase 4 processing attempt (including its original
source hash/configuration) → immutable page → parameter attempt → candidate →
personal revision. Candidate content includes page number, exact source quote,
zero-based Unicode codepoint offsets with an exclusive end, source method, and
matching native span indices. The original span stores its rectangle and page
coordinate system. The database rechecks quote offsets and page method against
the selected source page before insertion. Corrections cannot edit these links.

Fields preserve `original_label`, `raw_value`, `original_unit`, `raw_reference`,
optional `canonical_metric`, exact-string `numeric_value`, comparator, value kind,
qualitative result, reference bounds/inclusivity, printed flag and an always
`unknown` calculated range status. Parsing and alias versions are also recorded
inside field snapshots so later corrections remain attributable if rules change.
Older snapshots without these optional fields remain readable without inventing a
version for them. No binary floating-point measurement is persisted.

## Values, units, ranges and identity

`13.20` stays `13.20`; decimal parsing uses Python Decimal and JSON strings.
Comparators including `<`, `>`, `<=`, `>=`, `≤`, `≥` and `=` stay distinct.
`Negative`, `Reactive`, `Trace` and `Not detected` remain qualitative. Titres,
interval results and ordinal results such as `1:80`, `5–10` and `3+` are not forced
into a single number. OCR `O.5`, `l.5` and comma decimals remain unparsed in explicit
cells. Unicode minus is recognized only for a separate parsed decimal; raw text
remains intact. No missing result is inferred.

Original units, including `%`, `10³/uL` and `10^3/uL`, are retained. No unit
normalization or conversion is performed. Simple report-provided numeric intervals
and one-sided comparators are parsed, as is `Up to 5`. Reversed intervals, textual,
sex-dependent and age-dependent ranges remain raw without invented bounds. No
reference range is supplied from external medical knowledge. Only the supported
printed flags H, L, High, Low and Abnormal are retained as source flags. No
calculated abnormal status is implemented.

`parameter_aliases.json` is versioned as `synthetic-aliases-v1`. Its nine exact
aliases cover hemoglobin/Hb/haemoglobin, TSH/thyrotropin/thyroid stimulating hormone,
Vitamin D, glucose and CRP. Vitamin D and glucose use explicitly unspecified
identities, without assuming a particular assay or sampling condition. Lookup
normalizes case and whitespace only; it never rewrites the original label.
Unknown and Hindi labels remain valid unmapped candidates. This dictionary is not
medically comprehensive, and no translation or language identification is claimed.

## Certainty and personal review

Every machine candidate starts as `needs_review`. Warnings identify unmapped
labels, missing/unparsed fields, OCR sources and text-only provenance. There is no
invented accuracy percentage. Where available, the original **page mean OCR word
score** is shown with an explicit statement that it is not candidate accuracy.

Users can confirm, correct four raw fields, or reject a candidate. Corrections
reparse the user's separate fields snapshot; source evidence and machine content
remain immutable. Confirming or rejecting retains the latest correction. The
server derives the actor from the verified session. An expected revision prevents
lost updates; idempotency protects retries. At most 20 revisions are retained per
candidate. The result API includes only the latest revision; the history endpoint
returns the complete bounded revision list. Personal confirmation is not clinical
validation and does not write to longitudinal history.

## APIs, security and deletion

| Method and route under `/reports/{report_id}` | Behavior |
| --- | --- |
| `POST /extract-parameters` | `{source_run_id, idempotency_key}`; explicit bounded extraction |
| `GET /parameter-processing` | Attempt history and expired-lease recovery |
| `GET /parameters?run_id=...` | Selected successful attempt, or latest successful if omitted |
| `PATCH /parameters/{candidate_id}` | Strict personal review action, expected revision, key, optional correction |
| `GET /parameters/{candidate_id}/revisions` | Complete personal revision history |

All routes use existing signature-verified owner sessions. Writes retain Origin,
CSRF and rate-limit checks; protected responses are `no-store`. Browser reads and
writes retain account-change detection, shared session coordination and aborts on
unmount. Source text renders through React text nodes, never executable HTML.

All three tables enable and force RLS, derive ownership through the report, and
require an active provider session. Authenticated users have SELECT only; direct
INSERT/UPDATE/DELETE and anonymous reads are denied. Public RPC wrappers are
security-invoker. Private definer helpers use an empty search path, explicit owner
checks and report locks. Existing server processing-secret verification supplements
the owner JWT; it never replaces ownership. No runtime service-role key is used.

The existing deletion-intent trigger removes Phase 4 runs. Foreign keys cascade
through parameter attempts, candidates and reviews in the same transaction. The
report lock fences late completion. Tests prove physical cascade as well as loss
of API/RLS access. This does not claim deletion of already-downloaded copies or
provider backups; Phase 3 retention/operational limits still apply.

## Limits, retry and operations

- At most 20 pages / 400,000 input characters, 512 characters per physical row,
  200 candidates, a five-second checked parser deadline, two in-process slots.
- Machine content is bounded to 6,000 serialized bytes per candidate and 750,000
  bytes per attempt. Oversized output fails without partial insertion.
- Three attempts per completed Phase 4 source attempt; at most nine per report.
  New keys retain prior results and versions. Replaying a key returns its attempt;
  simultaneous different requests conflict rather than creating duplicates.
- A 60-second durable lease marks an abandoned attempt interrupted on the next
  history/request operation. Late results cannot commit. This is authenticated
  recovery on access, not an unattended queue or distributed worker service.
- Existing 10-second provider I/O timeouts remain. Only the new parameter-result
  RPC gets a 2 MB response budget for candidates plus latest reviews; every prior
  route retains its original 1 MB limit. This has a streaming-boundary test.
- Logs contain operation/status labels, not medical fields, source text, tokens
  or credentials. Malformed provider responses map to generic public errors.

## Evaluation and verification

The [machine-readable evaluation](phase-5-evaluation.json) is reproducible with
`python -m tests.evaluate_parameters`. Expected rows are explicit in
`backend/tests/parameter_fixtures.py`. The field numerator counts exact raw label,
value, unit, reference and expected page matches; missing rows count against every
field denominator. Incorrect synthetic label/page keys count as unexpected and
missing rows. These small fixtures do not estimate general medical accuracy.

| Fixture scope | Name/value/unit/range/page correct | False positives | False negatives |
| --- | --- | --- | --- |
| 32 explicit-cell rows across two synthetic Phase 4-shaped pages | 32/32 each | 0 | 0 |
| Real native PDF → Phase 4 → Phase 5, five rows | 5/5 each | 0 | 0 |
| Real scanned PDF → local OCR → Phase 5, five rows | 4/5 each | 0 | 1 |
| Five intentionally unsupported prose/false-pairing/multi-column documents | Zero candidates, as expected | 0 | Not applicable |

The OCR miss is deliberate abstention after Phase 4 read the final row as
`CRP>10mg/LUptob`. It is not repaired or fabricated. The 32-cell set includes Hindi,
0/O, 1/l, decimal precision, signs, comparators, dash variants, superscripts,
percent, missing fields, unknown units/labels, qualitative values, titres and
contextual ranges. Separate tests cover aliases, wrapped names, adjacent rows,
multiple tables, false row pairing, deadlines, capacity and API input/security.
Hindi Phase 5 label preservation is tested on text fixtures; a broad Hindi medical
OCR table evaluation is **not** established. Phase 4's real mixed Hindi OCR
regression remains enabled.

Verified locally on Windows / Python 3.12 / the existing pinned OCR models:

- Frontend lint, typecheck, **167 tests in nine files**, production build: passed.
  Production output: 63 modules; JS 339.12 kB (104.24 kB gzip), CSS 30.18 kB
  (7.41 kB gzip).
- Backend: **251 tests passed** with real OCR enabled; five opt-in live tests are
  run separately. Existing Starlette/AnyIO deprecation warnings remain.
  Ruff, format check (61 files), and strict mypy (60 source files) passed.
- Phase 5 real two-user test passed: upload/text/parameters for both accounts,
  selected/prior attempts, idempotency, corrections/confirmation/rejection,
  cross-user API and RLS denial, forged writes/worker denial, CSRF, revocation,
  bounded retries, deletion and cleanup.
  A final focused run also passed persisted parser/rules-version assertions and
  explicit rejection of a genuinely failed Phase 4 source (30.98 seconds).
- Rollback-only database schema/lifecycle checks passed: quote validation,
  immutable output, RLS, 20-revision cap, expired leases, late-result fencing,
  corrected-value retention and physical deletion cascades. Fixtures and temporary
  worker-key changes are entirely rolled back, with no Storage mutations.
- Chrome Phase 5 browser smoke: **eight groups passed**, including sign-in, upload,
  real text/parameter extraction, provenance, correction/confirmation/history,
  375-pixel mobile layout, refresh, rejection, deletion and logout. No page errors.
  Screenshots/results are ignored under `.cache/qa/phase5`.
- Supabase security advisor: only the pre-existing leaked-password-protection
  warning. The missing composite FK index was fixed. Performance advisor now has
  only informational unused-index notices for new FK-supporting indexes.

All five live suites passed together in 305.27 seconds, covering authentication,
profile/settings, upload/download/delete, Phase 4 extraction, actual worker death
and restart recovery, and Phase 5 isolation/reviews. Hosted CI and production
deployment are not claimed.

Previous browser regressions also passed: Phase 2 **15 groups**, Phase 3 **11
groups**, Phase 4 **seven groups**. The first chained Phase 4 browser setup did not
complete; its independent rerun after the final API restart passed all seven
groups. SQL cleanup checks found zero active reports, parameter rows/reviews or
rollback-fixture users. A scan of changed/new files found no configured secret
values. No Git commit or push was performed by this agent.

## Reproduce and manually test

Keep the existing Phase 4 OCR setup, provider project and private processing key.
Apply both Phase 5 migrations in order. No additional environment configuration is
needed. Start the API and frontend as documented in the repository README.

1. Sign in and upload an actual permitted PDF/image. Extract text first and inspect
   its numbers, column relationships and page order.
2. Open **Parameter candidates**, select the successful text attempt and choose
   **Extract parameters**. Unsupported structure may return no candidates.
3. Check Value, Unit, Reference, Source page and Needs review. Expand **Inspect
   source and machine result**, then **View source page text**; compare the original
   download when reviewing OCR or column ambiguity.
4. Use **Correct fields**, save a correction, then **Confirm reviewed** or **Reject
   candidate**. Open **Review history** and verify the machine source stays intact.
5. Refresh, inspect the saved attempt, and verify the personal revision persists.
   New extraction attempts preserve earlier results. Deleting the report removes
   its text and candidate/review access.

From `backend`:

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:RUN_OCR_EVALUATION='1'
$env:OCR_EVALUATION_MODELS='P:/Projects/SwasthyaLens/.cache/phase4/models-best'
.venv/Scripts/python.exe -m ruff check app tests
.venv/Scripts/python.exe -m ruff format --check app tests
.venv/Scripts/python.exe -m mypy app tests
.venv/Scripts/python.exe -m pytest
.venv/Scripts/python.exe -m tests.evaluate_parameters --models $env:OCR_EVALUATION_MODELS --output ../.cache/qa/phase5/evaluation.json
$env:RUN_SUPABASE_INTEGRATION='1'
.venv/Scripts/python.exe -m pytest tests/integration
```

Live tests require the existing ignored `.env.integration` and explicit disposable
account flag. They clean synthetic reports through normal APIs. Run database
verification files as complete transactions, never committing their fixtures.
`backend/tests/browser_parameters.cjs` is an opt-in QA harness using installed
Chrome and an available Playwright module (`PLAYWRIGHT_MODULE` may name the bundled
module path). It is not a new application dependency and reads only the dedicated
test-account configuration. Frontend checks remain `npm run lint`,
`npm run typecheck`, `npm test`, and `npm run build` from `frontend`.

## File inventory and remaining limits

Created during Phase 5:

- Backend `app/api/parameters.py`, `app/core/{parameter_parser.py,parameters.py,
  parameter_aliases.json}`, `app/schemas/parameters.py`.
- Backend tests `parameter_fixtures.py`, `test_parameters.py`,
  `evaluate_parameters.py`, `browser_parameters.cjs`,
  `integration/test_live_parameters.py`.
- Frontend `features/reports/ReportParameters.tsx`, `services/parameters.ts`,
  `services/parameters.test.ts`.
- The two migrations, `database/verification/parameters-{schema,lifecycle}.sql`,
  `docs/phase-5-decision.md`, `docs/phase-5-evaluation.json`, and this handoff.

Modified: backend app factory and provider boundary/tests; frontend report history,
safe error messages and styles; repository/database README. Removed the generated
CLI `.temp/cli-latest` marker from tracked files. Dependency locks are unchanged.

The parser intentionally covers a narrow grammar. Missing/unknown compact columns,
OCR-merged words, numeric labels without explicit cells, sideways/complex layouts,
non-English headers and general prose may be missed. It is possible for malformed
source text that resembles a supported row to produce a wrong candidate; personal
inspection remains necessary. There is no calibrated extraction confidence,
general medical dictionary, whole-document completeness guarantee, unit conversion
or clinical-validation workflow. Attempt/revision caps have no administrative reset.
Phase 1–4 deployment, signup-email, worker isolation, backup/retention and OCR
limitations remain as documented in their handoffs.

Suggested commit message: `feat: add source-grounded parameter candidates and personal review`.

Phase 6 prerequisites: explicitly define which reviewed revisions may become
observations; retain source/review/version links; define withdrawal and correction
propagation, duplicate handling, unit compatibility, and ownership/deletion rules.
Expand independent real-report and Hindi/layout evaluation before broad use.
No Phase 6 implementation has begun.
