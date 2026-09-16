# Phase 4 — source-preserving text extraction

16 September 2026. Scope: native PDF text and local scanned-PDF/JPEG/PNG OCR, owned processing history and a page inspection UI. **No medical parameter extraction, ranges, flags, interpretation, AI/LLM calls, summaries, observations, trends or assistant context were implemented.** The original uploaded file remains authoritative.

**Phase 4 is complete for the verified development scope.** Final live/browser verification is recorded below. This is a bounded single-server development implementation; it is not a production-isolated unattended job service.

## Architecture and OCR decision

The [decision recorded before installation](phase-4-decision.md) compares pypdf/pdfplumber, PDFium, PyMuPDF, Tesseract, PaddleOCR and managed Google/Azure OCR. PDFium combines native text and rendering without a second PDF parser. Tesseract keeps OCR local, supplies positioned words and engine scores, and supports English/Hindi. No paid/cloud OCR provider, external OCR credential or new OCR data recipient is used. Existing Supabase remains the authentication, private file and database provider. Public model downloads go to GitHub during operator setup, never during report processing.

Runtime: pypdfium2 5.13.0 (tested PDFium 153.0.7999.0), Pillow 12.3.0, tesserocr 2.11.0 and Windows Tesseract 5.5.3. The Windows wheel is pinned by URL and SHA-256 in both locks. Python support is now explicitly 3.12; the former 3.12–3.14 declaration cannot cover this CPython-specific wheel. Linux builds tesserocr against operator-installed Tesseract/Leptonica development packages; Windows is the locally verified platform. Linux CI is configured but was not run from this task.

The final language models are `tessdata_best` English/Hindi, revision `e12c65a915945e4c28e237a9b52bc4a8f39a0cec`; orientation uses `tessdata_fast` OSD revision `87416418657359cb625c412a48b6e1d6d41c29bd`. `scripts/setup_ocr_models.py` pins and verifies each SHA-256. Successful runs record the actual model hashes and engine version. The higher-accuracy models replaced the initial fast models after the latter confused `mIU/L` in image fixtures. See [upstream model documentation](https://github.com/tesseract-ocr/tessdata_best) and [Tesseract quality limitations](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html).

Flow:

1. An authenticated user explicitly chooses **Extract text** for an uploaded report.
2. FastAPI verifies identity/session, CSRF and Origin, reserves an idempotent durable attempt with planned processor/configuration, and returns HTTP 202.
3. One of two local worker slots claims the attempt. The worker obtains the private source through the existing owner-JWT report service, which verifies source integrity and report state.
4. A separate child process parses/renders/OCRs the source under memory, runtime and output limits. Its environment excludes application/provider/session credentials.
5. A database transaction rechecks the active owner session, report state, source hash, deadline and attempt state, then writes ordered pages and marks completion. A failure stores a safe category and leaves the original and prior successes intact.

No private Storage URL, user token or worker credential is returned by the extraction API. The worker retains its initiating user's access token in memory only. It cannot finish after session revocation, deletion or deadline expiry.

## Native PDF and OCR behavior

Each PDF page is examined separately. Native text is usable with at least 24 alphanumeric characters and at most roughly 1% replacement characters. A page with raster image coverage above 50% and fewer than 200 alphanumeric characters falls back to OCR, preventing a short header from hiding a large scan. This is a documented heuristic, not a guarantee that every mixed-content page is detected.

Usable native text keeps PDFium text rectangles, page dimensions, PDF rotation and `pdf_points_bottom_left` coordinates. Native confidence is null. Scanned pages render at 250 DPI without forms or annotations and use OCR. A mixed PDF can therefore have `native_text` on page 1 and `ocr` on page 2. If any page fails, the attempt fails atomically; partial pages are not presented as a completed document.

PNG/JPEG are decoded as a single image. EXIF orientation is applied and transparency is composited onto white. Images of at most 3 million pixels are enlarged 2× with bicubic resampling, remaining within the 12-million-pixel cap. This improved the measured image decimal/unit recovery. Larger images are not enlarged. No contrast manipulation, deskew, translation, medical spelling correction or value/unit rewriting is performed.

Tesseract uses `eng+hin`, LSTM-only recognition and automatic page segmentation. OSD orientations scoring at least 8 are applied; scores below 15 still produce an orientation warning. Those thresholds recovered the evaluated 90-degree image, but uncertain rotations require inspection. OCR stores word boxes in `oriented_pixels_top_left`, transformed page dimensions and clockwise applied rotation. Run configuration records image scale/resampling and EXIF normalization. Boxes refer to the processed page; consult its scale/rotation and the original to map them back. Arbitrary skew, perspective correction and handwriting are outside the verified scope.

Text normalization converts CRLF/CR to LF, applies NFC and removes control/surrogate artifacts except tabs/newlines. It preserves source language, case, decimals and units as returned. OCR words are grouped by engine line identifiers. Native rectangles and OCR word boxes remain available in the result. Tables are positioned text, not semantic cells or interpreted measurements. The UI wraps text for mobile readability; it does not promise original table alignment.

English and mixed Latin/Devanagari are supported by the model configuration. The shaped Hindi sample was recovered exactly. This does not establish broad Hindi, Hinglish, handwriting, font or hospital-layout accuracy. No translation occurs.

## Data model, lifecycle and APIs

Two public tables are sufficient:

| Table | Purpose |
| --- | --- |
| `report_processing_runs` | Report FK, immutable source SHA-256, idempotency key, attempt number, status, created/started/finished/deadline timestamps, processor, configuration, failure and page count. |
| `report_pages` | Run FK, ordered one-based page number, text, method, dimensions, coordinates, rotation, warnings, boxes and available confidence. |

Ownership derives through the existing report. No independently writable owner column is introduced. Machine results have no client update/delete privilege; future corrections must be separate records linked to the immutable machine attempt/page.

States are `queued → processing → completed` or `failed`. These describe text extraction only. Exactly one active attempt per report is allowed; the same idempotency key returns the same attempt, and a different key while work is active returns that active attempt. There are at most three total attempts per report, including successful attempts. A retry uses a new key; earlier successful results remain selectable. Retrying the old key never creates another attempt. No automatic retry consumes an attempt.

The durable deadline is 180 seconds from reservation. An authenticated history/request call converts overdue unacknowledged runs to `failed/interrupted`. A late worker cannot commit. After API death or loss of authorization, sign in, inspect status after the deadline and explicitly retry. There is no Redis/Celery service, persisted user token, background restart resumption or claim that queued work runs unattended. Graceful shutdown waits for admitted work; abrupt termination is recovered through the deadline.

| API route (browser adds `/api`) | Contract |
| --- | --- |
| `POST /reports/{id}/process` | Strict `{ "idempotency_key": "UUID" }`, CSRF/Origin/session required, returns run with 202. |
| `GET /reports/{id}/processing` | Owner-only ordered attempt history; also expires that report's stale attempts. |
| `GET /reports/{id}/extraction?run_id=UUID` | Owner-only completed result. Without `run_id`, returns the latest successful attempt, even after a later failure. |

Public results omit the server secret, internal paths and deployment configuration. Source digest/configuration are retained in the protected database; the public result gives report/run IDs, processor and page provenance. Existing download and deletion routes remain authoritative for original files.

Failures distinguish corrupt/zero-page documents, encrypted PDFs, unsupported documents, page limits, resource limits, parser failure, unavailable OCR, OCR failure, timeout, interruption and unavailable source. Password-protected/encrypted PDFs are explicitly rejected; there is no password collection flow. Malformed OCR TSV, non-finite/out-of-range scores and out-of-bounds word boxes fail validation. A hard process-memory kill can surface as generic `extractor_failure` rather than an exact allocation diagnosis. No stack trace is exposed.

## Limits, security and privacy

| Limit | Behavior |
| --- | --- |
| Upload | Existing 5 MiB maximum; private PDF/JPEG/PNG originals. |
| Pages | Default/hard cap 20, configurable downward to 1. |
| PDF dimensions | Maximum 1,440 points per side (20 inches). |
| Decoded/rendered image | 12 million pixels, maximum 10,000 pixels per side; checked before full decode/render. |
| Parser memory | 768 MiB Windows Job limit or Linux address-space limit; core dumps disabled on Linux. |
| Runtime | Default/hard cap 120 seconds per document, configurable down to 5; 30-second recognition call timeout. OSD is bounded by the document supervisor. |
| Output | 20,000 characters and 2,000 spans per page; 750,000-byte serialized result; bounded temporary output checks. |
| Concurrency | Two admitted jobs per API process; busy returns 429. |
| Attempts/rate | Three total attempts per report; process trigger 10/user/minute plus existing report limits. |
| Temporary files | Supervisor checks a 64 MiB directory budget; all normal/failure exits remove the attempt directory. |

The child receives generated local paths as an argument list with no shell. It does not follow embedded URLs, initialize active forms, execute PDF scripts/attachments or trust filenames/metadata as commands. Pillow decompression warnings become explicit failures. Parser/native-library patches and dependency provenance remain operational responsibilities.

This child is **resource containment, not a security sandbox**: it runs as the same OS user and can potentially access that user's filesystem/network if a native library is exploited. Production requires a separate low-privilege worker/container, no network egress, read-only runtime/model mounts, isolated temporary storage, global quotas/admission control and deployment-specific kill/cleanup validation. Do not advertise this local design as production-isolated health-data processing.

Both derived tables have enabled and forced RLS, owner/session SELECT and no anonymous/client machine-output writes. Public RPC wrappers are invoker; private definer functions have empty search paths and require both verified owner/session and the server worker secret. Only its one-way hash resides in the unexposed private schema. It supplements owner authorization; it never substitutes for it. No service-role key is used.

Deleting a report atomically erases runs and cascades pages when the Phase 3 status first becomes `deleting`. Completion locks the same report and checks status, so a late write cannot resurrect derived text. Phase 3 continues the private Storage deletion/tombstone lifecycle. This removes active application records; it is not a claim about immediate provider backup erasure.

No report text, values, tokens, cookies, credentials, document bytes or signed URLs are logged. Operational event names cover request/start/native completion/OCR/completion/failure/unconfirmed outcome. Child stdout/stderr are suppressed. The browser uses in-memory state and clears the protected view on logout/account change; extraction is not stored in localStorage.

Report bytes and derived text temporarily exist in `swasthyalens-extraction-*` directories under the OS temporary directory. Normal completion/failure removes them. An abrupt host crash can leave them: production must use private encrypted ephemeral storage and an operator cleanup policy for expired directories after confirming no worker is active. No persistent report OCR cache is introduced. Downloaded models contain no reports. Synthetic QA artifacts in ignored `.cache/qa/phase4` contain no personal records. No compliance certification is claimed.

## Fixtures and measured quality

`tests/extraction_fixtures.py` reproducibly generates native, scanned, mixed, multipage, blank, corrupt, zero-page, 21-page, English PNG/JPEG and rotated fixtures. A checked-in synthetic encrypted PDF exercises password rejection. A checked-in Hindi/English raster uses proper browser Devanagari shaping; its generator and provenance are in `tests/fixtures`. A Pillow build without RAQM must not be used to judge an incorrectly shaped Hindi fixture.

`python -m tests.evaluate_extraction` measures Levenshtein character/word error after whitespace normalization, page method/order, rotation, and exact presence of `13.2`, `18`, `2.4`, `mg/dL`, `g/dL`, `ng/mL`, `mIU/L`. Numeric checks are fixture string fidelity assertions, not application medical extraction. The gate is all target tokens plus character error ≤5% and word error ≤10%; original text and page coordinates are retained for inspection.

Final evaluation on the verified Windows runtime:

| Fixture | Result |
| --- | --- |
| Native PDF; two-page native PDF | Native method only, correct order, zero character/word error. |
| Scanned PDF | OCR, zero character/word error. |
| Mixed PDF | Native page 1, OCR page 2, correct order, zero error. |
| English PNG and JPEG | OCR, every decimal/unit retained, zero error. |
| 90-degree PNG | OCR with recorded 90-degree correction, every token retained, zero error. |
| Blank PDF | Empty text, `no_text` warning, no invented confidence. |
| Hindi/English PNG | Both scripts and target numbers/units retained, zero error. |

All nine documents passed. These are clean printed synthetic examples, with repeated English content across formats. They are a reproducible regression gate, not a representative clinical benchmark or an accuracy percentage for arbitrary reports. OCR confidence is the actual engine word score; the displayed mean is not calibrated probability of correctness. Orientation below 15 still warns. Table positions remain inspectable, but column/semantic reconstruction is unverified.

Initial fast-model runs misread `mIU/L`, and the initial rotation threshold missed the rotated sample. Higher-accuracy models, bounded 2× image enlargement with bicubic resampling and the evaluated OSD threshold fixed these cases. Lanczos enlargement lost a JPEG decimal and was rejected; no textual correction was used. Preserve this evidence when expanding the dataset to independent fonts, lower-quality scans and layouts.

## Verification results

Before edits, frontend lint/typecheck/137 tests/build and backend Ruff/format/mypy/189 tests passed. Both existing live suites passed. Initial sandbox cache/network errors were rerun with authorized access rather than counted as successful checks.

- Frontend: lint, typecheck, **151 tests across 8 files**, production build passed. Tests cover strict extraction decoding and prior auth/account/report contracts.
- Backend: Ruff, format (**55 files**), mypy (**52 source files**), dependency consistency passed. **215 tests passed**, including all seven real OCR cases; four opt-in live tests are skipped only in the local test invocation. Two existing upstream Starlette/AnyIO deprecation warnings remain.
- Database: all six Phase 2–4 schema/RLS/lifecycle verification scripts passed. The final extraction scripts were rerun after the configuration migration. They cover both owners, forged worker denial, direct-write denial, duplicate claims, immutable completion, previous success retention, deadline expiry, late completion rejection, deletion while queued and revocation with existing pages.
- Live: **all four suites passed in 283.06 seconds**. They cover authentication, profile/settings, real Storage upload/list/private download/delete, two-way extraction isolation, real image OCR fidelity, idempotency, bounded failure/retry, direct-write denial and revocation with existing pages. A separate session proved revoked access while another active owner session still read those pages. Killing a disposable API after its durable claim produced `failed/interrupted` after the real 180-second deadline; retry through the surviving API completed as attempt 2.
- Browser: prior Phase 1/2 suite (15 groups), Phase 3 suite (11 groups) and final Phase 4 suite (**7 groups**) passed. Phase 4 covers accepted processing surviving refresh, two-page text/method/source warning, 375-pixel mobile layout, real image OCR text/confidence, encrypted failure with retry history, deletion and logout. Masked desktop/mobile screenshots were visually inspected; no browser runtime errors were observed.
- Final post-migration advisors: no performance finding and no new table/RLS/function security finding. The pre-existing [leaked-password protection warning](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection) remains. After all live/browser cleanup, administrative counts confirmed **zero processing runs, extracted pages, active reports and report Storage objects**. The diff whitespace check and scan for configured credentials in tracked/untracked source passed. Nothing was committed or pushed.

The first browser refresh test reloaded before the process POST was acknowledged, aborting the test's own request. It was corrected to wait for durable HTTP 202 acceptance before refreshing. No hidden successful OCR result was substituted when earlier engine execution or quality checks failed.

## Setup and manual test

Existing local setup already has the four migrations, server processing secret/hash and the verified models under `.cache/phase4/models-best`. No user credentials were added to source control. The second migration preserves planned attempt configuration; hosted versions match filenames `20260916153700` and `20260916160036`.

For a fresh development installation:

1. Install the Python 3.12 hashed lock as in README. On Linux install Tesseract/Leptonica development packages first. Apply all `database/migrations` in filename order to the intended Supabase development project; keep the private schema unexposed and the reports bucket private.
2. From `backend`, run `python scripts/configure_processing.py` with the venv interpreter. It writes a random `REPORT_PROCESSING_KEY` to ignored `.env` and prints **only its SHA-256 hash**. Provision that hash through an administrative connection:

   ```sql
   insert into swasthyalens_private.processing_key(singleton,sha256)
   values(true,'REPLACE_WITH_GENERATED_SHA256')
   on conflict(singleton) do update set sha256=excluded.sha256;
   ```

   The raw secret stays server-only. Rotation requires updating the server secret and database hash together while work is stopped. No `VITE_*` OCR secret exists.
3. Download and verify models, then set `OCR_TESSDATA_DIR` in ignored `.env` to the absolute directory:

   ```powershell
   .\.venv\Scripts\python.exe scripts/setup_ocr_models.py ../.cache/phase4/models-best
   ```

4. Optional server settings are `REPORT_PROCESSING_MAX_PAGES=20` and `REPORT_PROCESSING_TIMEOUT_SECONDS=120`; both may only lower their hard caps. Start/restart the API and frontend using README.
5. Sign in, upload a permitted PDF/PNG/JPEG, expand **Text extraction**, select **Extract text**, then **View extracted text · Attempt 1**. Compare each page/method and text with the original download. Refresh after the request is accepted and confirm status/results persist.
6. Use the synthetic encrypted fixture to see the clear failure; retry and confirm separate attempts. Delete the report and confirm its text view disappears. Sign out and confirm protected content disappears. Check a 375-pixel-wide viewport.

Reproduce local quality and tests from `backend`:

```powershell
$env:RUN_OCR_EVALUATION='1'
$env:OCR_EVALUATION_MODELS='P:/Projects/SwasthyaLens/.cache/phase4/models-best'
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m tests.evaluate_extraction ../.cache/qa/phase4/evaluation-final --models $env:OCR_EVALUATION_MODELS
```

The evaluation command exits nonzero on a failure and writes synthetic per-page output plus `quality-results.json`. Ordinary tests skip real OCR unless explicitly enabled. CI now downloads the pinned public models and enables those tests; hosted CI execution remains separate from local evidence. Regenerate locks with the project's pinned `uv`: `uv pip compile pyproject.toml --universal --generate-hashes --output-file requirements.lock --cache-dir .cache/uv`, then the same command with `--extra dev --output-file requirements-dev.lock`.

Live tests require the existing ignored `.env.integration`, the explicit disposable-account flag, running API and `RUN_SUPABASE_INTEGRATION=1`. Run `python -m pytest tests/integration`. They upload only synthetic records and clean them through the normal APIs. The worker-death test deliberately starts and kills its own disposable loopback API, waits about three minutes for the real durable deadline, then retries through the surviving API. Do not run against real user accounts.

Windows initially cancelled the standalone installer, and Application Control initially blocked the portable DLL even outside the sandbox. A later authorized run of the installed pinned wheel succeeded; no policy was disabled or bypassed and the cause of the environment change was not established. Subsequent real OCR tests/evaluation passed. On another controlled device, use the device's normal approval process if the runtime is blocked; do not switch to cloud OCR without approval.

## File inventory

Created:

- `backend/app/api/extraction.py`; `backend/app/core/extraction.py`, `extraction_process.py`, `extraction_limits.py`; `backend/app/schemas/extraction.py`.
- `backend/scripts/configure_processing.py`, `setup_ocr_models.py`.
- `backend/tests/test_extraction.py`, `extraction_fixtures.py`, `evaluate_extraction.py`; `backend/tests/fixtures/{README.md,encrypted.pdf,hindi-mixed.png,render-hindi.cjs}`; `backend/tests/integration/test_live_extraction.py`, `test_live_extraction_restart.py`.
- `database/migrations/20260916153700_report_text_extraction.sql`, `20260916160036_processing_attempt_configuration.sql`; `database/verification/extraction-schema.sql`, `extraction-lifecycle.sql`.
- `frontend/src/features/reports/ReportExtraction.tsx`; `frontend/src/services/extraction.ts`, `extraction.test.ts`.
- `docs/phase-4-decision.md` and this handoff. Ignored browser harness/screenshots/evaluation outputs are in `.cache/qa/phase4`.

Modified: README, database README, CI workflow; backend `.env.example`, configuration, provider error mapping, app factory, dependency manifest/locks and test environment isolation; frontend report history/upload/page copy, safe error mapping and extraction styles. The original Phase 3 file lifecycle and Storage policies were retained.

## Limitations and Phase 5 prerequisites

- Small synthetic quality coverage; general printed-report, Hindi/Hinglish, low-quality photo, complex-table and handwriting accuracy is not established. Native-text quality detection may miss scanned regions on a page with substantial native text. Embedded native text can itself be wrong; the original remains the source of truth.
- One development API process; no distributed admission control, unattended token-free job continuation, resumable pages or real-time cancellation of an already-running parser on deletion. Deletion/revocation fences persistence; bounded computation may finish before its commit is rejected.
- Resource-limited same-user child, not production security isolation. Temporary crash residue, backup retention, deployment quotas and isolated worker operations require production work.
- Three lifetime attempts can be exhausted; no administrative reset/reprocessing policy or correction UI exists. Machine attempts remain immutable until source deletion.
- Python 3.12-only Windows wheel; other Python versions, Linux behavior and hosted CI need their own acceptance. Model/runtime distribution must retain upstream licensing notices.
- Phase 2's owner-confirmed locked signup-email template and unverified email OTP flow remain unchanged. Existing password-protection advisor and upstream test warnings remain documented.

Suggested commit message: `feat: add private source-preserving report text extraction and local OCR`.

Phase 5 may later introduce separately versioned structured extraction linked to report/run/page/box provenance, with validation and user corrections distinct from immutable machine text. It must first expand independent OCR quality evidence and define error handling for ambiguous values/units. Nothing in this phase labels a value high/low/normal or generates medical insight. **Stop after Phase 4; Phase 5 requires a new explicit instruction.**
