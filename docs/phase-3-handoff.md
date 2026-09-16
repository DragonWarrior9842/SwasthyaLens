# Phase 3 — Private report upload and storage

Completed for the approved development scope on **16 September 2026**. No Phase 4 work started. The original baseline was `53a8c54`; the owner committed intermediate work during implementation. No Git commit or push was performed by the implementation agent.

Real uploads, owner history, private attachment downloads and retryable deletion are implemented. Frontend checks, backend checks, hosted schema/RLS verification, both live integration suites, and desktop/mobile browser acceptance passed. This is not a production deployment or a claim of regulatory compliance. The operational limitations in section 22 remain material.

## 1. Upload/storage architecture implemented

```text
Browser — same-origin /api, HttpOnly cookies, Web Locks, signed CSRF
  ├─ POST /reports: reserve metadata with an owner-scoped idempotency UUID
  ├─ PUT /reports/{id}/file: send the original raw file bytes
  │    FastAPI verifies identity/session/Origin/CSRF before consuming bytes
  │      → bounded body + filename/MIME/container validation
  │      → SHA-256 + exclusive database upload lease
  │      → private Supabase Storage using the current user's JWT
  │      → confirm object metadata → uploaded
  ├─ GET /reports: owner-only PostgreSQL history
  ├─ GET /reports/{id}/file:
  │    owner check → fresh cacheNonce Storage read → byte/type/hash/format checks
  │      → repeat manifest/session check → no-store attachment
  └─ DELETE /reports/{id}:
       durable deletion intent → wait for active lease → Storage API removal
         → confirm absence → scrub metadata, retain minimal cleanup manifest
```

The Phase 2 backend-for-frontend identity model is preserved. No browser Supabase SDK, service-role key, database password, new application dependency, multipart parser or privileged background worker was introduced. Report bytes never become instructions, medical parameters or AI context in this phase.

## 2. Files created

Relative to the Phase 2 baseline:

| Area | Files |
|---|---|
| Backend | `backend/app/api/reports.py`, `backend/app/core/reports.py`, `backend/app/core/report_storage.py`, `backend/app/core/report_validation.py`, `backend/app/schemas/reports.py` |
| Backend verification | `backend/tests/test_reports.py`, `backend/tests/report_fixtures.py`, `backend/tests/reports_support.py`, `backend/tests/integration/test_live_reports.py` |
| Frontend | `frontend/src/features/reports/ReportUpload.tsx`, `ReportHistory.tsx`, `useReportHistory.ts`; `frontend/src/services/reports.ts`, `reports.test.ts`; `frontend/src/types/reports.ts` |
| Database | `database/migrations/20260915150720_reports_foundation.sql`, `database/verification/reports-schema.sql`, `database/verification/reports-rls-isolation.sql` |
| Documentation | `docs/phase-3-upload-plan.md`, this handoff |

Local browser acceptance runners, neutral fixtures and masked screenshots are in ignored `.cache/qa/phase3/`. They use the existing bundled Playwright/Chrome runtime; that runtime is not a new project dependency. The checked-in unit/live suites remain runnable using the documented project dependencies.

## 3. Files modified

- Backend: `.env.example`, `app/core/config.py`, `browser_security.py`, `http_security.py`, `provider.py`, `app/factory.py`, `tests/conftest.py`.
- Frontend: `src/pages/ReportsPage.tsx`, `src/services/api-client.ts`, `auth.ts`, `src/styles/index.css`.
- Documentation: root `README.md`, `database/README.md`.

Lockfiles and application dependencies did not change. The local historical browser runner was adjusted only for the new Reports heading and the now-present upload control.

## 4. Database schema changes

One file belongs to one report, so one `public.reports` table is sufficient. No speculative processing-run, medical-parameter or AI tables were created.

| Columns | Purpose |
|---|---|
| `id`, `user_id` | Server-generated report UUID and authoritative Supabase Auth owner |
| `idempotency_key` | Unique per owner; reservation retries cannot create duplicate manifests |
| `storage_path` | Unique immutable generated path, checked against owner/report IDs |
| `original_filename`, `media_type`, `size_bytes` | Validated display/file metadata; nullable only on deletion |
| `status`, `error_category` | Constrained lifecycle and allowlisted operational failure category |
| `sha256` | Expected content digest, preserved across uncertain attempts |
| `lease_token`, `upload_lease_expires_at` | Paired exclusive upload lease, normally 120 seconds |
| `created_at`, `updated_at`, `deleted_at`, `cleanup_checked_at` | Server audit/lifecycle timestamps and fair cleanup cursor |

Constraints enforce valid metadata, state, digest, lease pairing, generated path and tombstone scrubbing. Indexes support owner history ordered by `created_at DESC, id DESC`, cleanup candidates, unique object paths and owner/idempotency lookup. The user foreign key uses **ON DELETE RESTRICT**: future account deletion must clean storage and retained manifests first. The current application has no account-deletion endpoint.

Applied migration: **`20260915150720 / reports_foundation`**, after `20260914164833 / auth_foundation`. Supabase CLI 2.117.0 generated the source filename; it was aligned with the migration service's recorded timestamp without altering the applied SQL. Do not replay this migration on the already configured project.

## 5. Storage bucket/policies

- Bucket ID/name: **`reports`**, private.
- Maximum: **5,242,880 bytes**; allowed MIME types: `application/pdf`, `image/jpeg`, `image/png`.
- Key: `<verified-owner-uuid>/<server-report-uuid>/<random-object-uuid>.<canonical-extension>`.
- Original filenames are display metadata, never object keys.
- Policies permit the exact registered owner path and supported lifecycle/operation only: standard upload, authenticated retrieval/info, and delete-many cleanup.
- No overwrite/upsert, public download, signed URL creation, list, copy/move or resumable-upload permission is granted.

The migration creates bucket configuration through documented Supabase SQL. Actual file mutations always use Storage's API, never direct writes/deletes of `storage.objects`. Unexpected existing buckets or overlapping policies cause migration failure for review.

## 6. RLS policies

RLS is enabled and forced on reports. Four explicitly scoped table policies require `auth.uid() = user_id` and the Phase 2 active-session helper. Direct authenticated table access is **SELECT only**; lifecycle mutations use narrow RPCs. Anonymous callers cannot read reports or invoke the lifecycle API.

Public RPC wrappers are security-invoker. Their private security-definer implementations use an empty search path, fully qualified objects, revoked default PUBLIC privileges, and explicit current-user/active-session checks. This protects immutable/state columns without granting ordinary callers arbitrary table writes. No RPC accepts an authoritative owner ID or an arbitrary object path.

RPCs: `report_reserve`, `report_begin_upload`, `report_finish_upload`, `report_fail_upload`, `report_begin_delete`, `report_finish_delete`, `report_cleanup_candidates`, `report_touch_cleanup`. Internal metadata returned by these owner-only RPCs stays behind FastAPI; the browser receives only public report fields.

## 7. API endpoints

Every route requires a verified active user. Browser routes use the `/api` prefix; FastAPI routes below do not. Every mutation also requires exact Origin and signed CSRF.

| Method / route | Input | Output |
|---|---|---|
| GET `/reports/config` | None | Allowed MIME types and server byte limit |
| POST `/reports` | Strict JSON filename, MIME, byte count, idempotency UUID | 201 public metadata |
| PUT `/reports/{id}/file` | Raw file bytes, exact declared MIME | 200 confirmed uploaded metadata |
| GET `/reports` | Optional validated opaque cursor | Up to 20 owner records, next cursor |
| GET `/reports/{id}` | Report UUID | Owner metadata; unrelated/missing/deleted → 404 |
| GET `/reports/{id}/file` | Report UUID | Bounded attachment with safe headers |
| DELETE `/reports/{id}` | JSON `{}` | 200 `deleted` or 202 `deleting` |
| POST `/reports/cleanup` | JSON `{}` | Counts from up to ten eligible owner cleanup attempts |

Public metadata contains report ID, filename/type/size, status, timestamps and allowlisted error category. It excludes owner IDs, storage paths, hashes, leases, provider errors and credentials. Ordinary authentication JSON retains its 16 KiB request cap; only the exact binary upload route receives the file limit.

## 8. File validation rules

- Reject empty/oversized bodies, reservation/body size mismatches, unsupported MIME types, extension/type disagreement and unexpected request fields.
- Normalize filenames to NFC; cap at 120 characters and 240 UTF-8 bytes. Reject paths, separators, control/bidi characters, `..`, unsafe punctuation, leading/trailing dots/spaces and reserved Windows names.
- PDF: supported header, object marker, terminal EOF/startxref and an in-bounds cross-reference table/stream target.
- PNG: signature, bounded chunks, checksums, valid IHDR, image-data/end chunks and bounded dimensions.
- JPEG: SOI/EOI, bounded marker/segment/frame/scan structure and bounded dimensions.
- Image dimensions are capped at 40 million pixels; these checks do not decompress or interpret medical content.
- Downloads recheck filename/container structure and stored hash/type/length. A matching owner-supplied digest or uploaded status cannot alone establish trustworthy content.

These are conservative container checks, **not complete PDF/image parsers or malware scanning**. Future extraction must revalidate files and use resource-isolated parsing. No files are executed or rendered inline.

## 9. Supported formats and size limit

PDF (`.pdf`), JPEG (`.jpg`, `.jpeg`) and PNG (`.png`), up to **5 MiB per file**. The conservative cap bounds transfer/memory costs. `REPORT_MAX_UPLOAD_BYTES` can lower the API cap; increasing the database/bucket cap requires a separately reviewed migration. No configurable arbitrary bucket or unrestricted upload mode exists.

## 10. Report lifecycle/status model

`pending_upload → uploading → uploaded`, with `upload_failed` for failed attempts. Cancellation/deletion uses `deleting → deleted`.

Reservations precede byte transfer. Lease acquisition serializes attempts; retries must match the recorded hash. If Storage completes before its response is lost, the backend can recover only an exact immutable byte/type/hash match. Uncertain failures keep the lease/hash and a durable manifest; retry after the lease expires. No status says processed, analyzed or explained.

## 11. Frontend report flow

The Reports page includes a chooser/dropzone, format/size guidance, permission acknowledgment, selected-file state, indeterminate progress, cancel/retry, confirmed success, real history, attachment download and explicit delete confirmation. It handles empty/loading/network/auth/error states without fake data. History refresh preserves a selected upload form; account changes abort/discard stale work through the existing session boundary.

Web Locks coordinate account-sensitive operations with login/logout/refresh. The editor's expected account is rechecked before actions, but never sent as backend authorization. Browser storage holds no provider tokens or report persistence substitute. A failed write is not automatically replayed.

## 12. Delete behavior

Deletion first commits owner-scoped intent and closes normal read/new-upload access. It waits for an active upload lease rather than claiming that a browser abort stopped provider I/O. Storage removal is followed by a database check that the object metadata is absent. Failure returns a truthful pending state and can be retried.

After confirmed removal, filename/type/size/hash/lease/error metadata is scrubbed. A minimal opaque tombstone retains the original cleanup path and idempotency key: Supabase can complete an already-authorized in-flight write after its caller disconnects. Reconciliation revisits these manifests through owner-authenticated cleanup and rotates attempts so failed candidates do not monopolize a batch. Freshly checked candidates have a five-minute cooldown. Deleted tombstones are excluded from normal history/detail.

This does not retract downloaded copies or promise immediate erasure from provider caches/backups. There is no scheduled global reconciler, account deletion or tombstone purge in this phase.

## 13. Environment variables added

Only **`REPORT_MAX_UPLOAD_BYTES`**, server-side in `backend/.env`, optional; blank defaults to 5,242,880. Its name and bounds are documented in `backend/.env.example`. Existing Supabase/CSRF settings are reused. No new secret, storage admin key or `VITE_*` variable is required.

## 14. Manual Supabase setup performed by the owner

The owner previously created the development project, supplied server configuration locally and created two dedicated Auto Confirm integration users. Those existing resources were reused. **No additional manual Phase 3 bucket/table/policy setup was needed**: the reviewed versioned migration configured them together through the connected migration tool.

Custom SMTP is still absent; confirm email remains enabled. The Free/default-sender Confirm signup template is locked. Actual signup email delivery and OTP verification remain unverified, as explicitly requested by the owner; no workaround was fabricated.

## 15. Security decisions

Preserved HttpOnly/host-only cookies, production Secure settings, exact Origin, signed CSRF, verified JWT identity and provider-session revocation. Ownership is enforced independently by API filtering/checks, database policies/RPCs and Storage policies. Cross-user and missing IDs share safe not-found behavior. No service-role runtime shortcut exists.

Uploads/downloads are bounded; upload and download concurrency each have four slots. Development report limits are per-user/method (60/minute) with cleanup limited to 5/minute. Production needs shared edge limits, request timeouts, quotas and abuse monitoring; the in-process limiter is not distributed protection. Logs contain allowlisted operational event names, not filenames, file bytes, credentials, cookies or raw provider errors.

Downloads use attachment disposition, `nosniff`, `no-store`, CSP sandbox, fresh provider cache nonce and a second manifest check after I/O. Browser code never receives a Storage URL or JWT. Files/embedded instructions remain untrusted through future phases.

Credential checks found no populated environment file tracked and no exact configured credential values of 12+ characters in tracked/unignored project files. This bounded check is not a claim of an exhaustive historical secret scan. `git diff --check` passed. No secret values were printed.

## 16. Live two-user storage/database isolation results

**Passed: both real integration suites** (`tests/integration`, 2 tests, 45.65 seconds on the final run). They cover:

- Each real account reserves/uploads PDF, PNG and JPEG, lists its own history, reads its own metadata and downloads exact bytes.
- Cross-user metadata/download/delete/upload denial in both directions; unfiltered/targeted Data API RLS isolation.
- Direct table mutation and manifest hard-delete denial, forged ownership rejection and cross-owner lifecycle denial.
- Direct Storage cross-user read/overwrite/delete denial; upload denial to the other owner's currently valid leased path, with a successful owner positive control.
- Public download and signed URL creation denied; repeated reservation/upload safe; owner deletion and cancellation scrub metadata and hide history.
- Revoked JWT denied at current Storage origin/RLS and Data API; reauthenticated owner can still retrieve the same live file before cleanup. The unrelated account remains signed in.

All four database verification scripts passed. Rollback-only SQL fixtures left no accounts behind. After live/browser cleanup, administrative counts showed **zero active report manifests and zero Storage objects** in the development bucket; minimal deleted manifests intentionally remain.

An initial live test exposed provider CDN reuse after deletion. Diagnostics showed a cached 200 for a previously authorized URL despite `no-store`, while a fresh `cacheNonce` denied access and origin object count was zero. The backend now uses fresh nonces, and live direct-Storage authorization assertions explicitly test origin/RLS with fresh nonces. This distinction is documented; the provider-cache limitation was not relabeled as an immediate erasure guarantee. See [Supabase's documented cache bypass](https://supabase.com/docs/guides/storage/cdn/smart-cdn#bypassing-cache).

## 17. Malicious/invalid upload test results

Passed local and live cases for unsupported extensions/MIME, MIME/extension and body mismatches, synthetic executable/fake-PDF content, invalid xref, empty/oversized input, traversal/absolute/control/bidi/reserved/long filenames, forged owner fields, anonymous access, missing/wrong CSRF and foreign Origin. Fixtures contain no malware or patient information.

Fault tests cover storage failure, timeout after commit, metadata completion failure, duplicate/idempotent retry, active leases, deletion failure/retry and a late storage artifact reconciled from a tombstone. Download tests cover tampering, matching-hash invalid format, valid JPEG and distinct cache nonces. Container validation is intentionally narrower than full document validity or malware detection.

## 18. Frontend test/build results

- ESLint: passed, zero warnings.
- TypeScript: passed.
- Vitest: **137 passed**, seven files (76 prior tests plus 61 report tests).
- Production build: passed, 59 modules; JS 316.32 kB / 98.29 kB gzip; CSS 28.16 kB / 6.97 kB gzip.
- Real Chrome report acceptance: **11 groups passed**: login/navigation; byte-identical PDF download; PNG/JPEG; persistence/two-user isolation; invalid uploads; selection clear; transfer cancellation; preserved selection/mobile layout; confirmed deletion; credential/runtime boundaries; logout protection.
- Desktop and 375-pixel mobile screenshots were inspected; no horizontal overflow. Screenshots mask account identity.

## 19. Backend test/typecheck/lint results

- Ruff lint and format: passed; 42 files formatted correctly.
- Strict mypy: passed, 42 files.
- Unit/regression suite: **189 passed**, two opt-in live tests skipped in the ordinary run.
- Live suites: **2 passed** separately, with dedicated account credentials read only from ignored local configuration.
- `pip check`: passed; import/lifespan/startup and `/health` verified.
- Two existing upstream Starlette/AnyIO deprecation warnings remain. No dependency upgrade was introduced to suppress them.

## 20. Regression results

All prior frontend/backend tests remain passing. The **15-group Phase 1/2 real-browser suite** passed after updating obsolete Reports-only expectations for the new page. Coverage includes protected routes, signup/code *form validation only*, real invalid/valid login, cookies, profile/settings persistence, two users, navigation/remaining empty states, health failure/retry, mobile menus, real refresh after access-cookie removal, session outage recovery and cross-tab logout.

Phase 2 schema and role/session isolation scripts passed again. Security advisor: only the pre-existing **leaked password protection disabled** warning; no report/table/RLS/function findings. Performance advisor: no findings. [Provider guidance for the remaining password-protection warning](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).

The interrupted tool runs were not acceptance passes: usage limits temporarily blocked commands, then checks resumed. An initial browser rerun failed because servers had stopped; they were restarted. The old regression's assumption that Reports had no file input was updated to the explicitly authorized functionality. No unrelated regression assertion was removed.

## 21. Manual Phase 3 testing

1. Start the API and frontend using the root README. Open `http://127.0.0.1:5173` and sign in with a confirmed development account.
2. Open Reports. With a new account, confirm truthful empty history. Choose a harmless PDF smaller than 5 MiB, acknowledge permission, and upload.
3. Confirm **Uploaded**, filename/type/size/date and the explicit absence of OCR/analysis. Reload; the same report should remain.
4. Upload PNG/JPEG, then download and compare to the original. The browser should download an attachment, not embed a report viewer.
5. Try empty, oversized and unsupported files; try harmless text renamed to `.pdf`. Validation should fail without fake success.
6. Choose a file and clear it. For an active upload, cancel; if cleanup is pending, refresh or retry deletion after the lease expires. Do not interpret network cancellation alone as deletion.
7. Delete a report, review confirmation, then confirm. The row disappears only after confirmed cleanup. Reload and verify it stays absent.
8. In another browser profile sign in as a second account. It must not list or retrieve the first account's report; the API returns 404 for another owner's ID.
9. Check mobile navigation, keyboard focus, refresh, sign-out and cross-tab sign-out. Dashboard/Trends/Assistant must retain their honest empty states.

Run lint/typecheck/tests/build using README commands. The live suite requires the existing ignored `backend/.env.integration`, `DISPOSABLE_TEST_ACCOUNTS_CONFIRMED=1`, both local services, and explicit `RUN_SUPABASE_INTEGRATION=1`. Do not run multiple acceptance runners against the same fixture users simultaneously.

## 22. Known limitations

1. **Email:** public signup delivery and OTP-code verification remain unverified under the locked template; Auto Confirm test accounts do not prove that flow.
2. **Provider caches:** origin deletion and app access revocation work, but previously authorized direct Storage CDN URLs can temporarily return cached bytes. Fresh nonces prevent app reuse; no provider URL/token is disclosed by the app. Production retention/cache-purge guarantees need explicit provider/product review. Previously downloaded copies cannot be recalled.
3. **Reconciliation/retention:** cleanup is owner-triggered and bounded, not scheduled globally. An absent user, provider outage or late write can leave cleanup obligations until another attempt. Minimal tombstones have no purge schedule. A production worker, account-deletion orchestration and legally reviewed retention/backup policy remain future work.
4. **Validation:** checks are conservative and may reject unusual valid containers; they are not antivirus or full parser validation. Direct authorized Storage clients can submit their own bytes; RLS proves ownership, not medical validity. The BFF and future OCR must revalidate. No OCR/extraction/AI/trends/voice/export exists.
5. **Scale:** 5 MiB per file, no aggregate account quota, no resumable or multi-file batches. Byte buffering and local concurrency/rate limits suit this development phase; production needs edge deadlines, shared limits, monitoring and quota decisions.
6. **Deployment:** no production deployment, SMTP/domain configuration, compliance certification, durable job system or unattended backup/restore exercise was performed.

## 23. Suggested Git commit message

`feat(reports): add private uploads, owner history and durable deletion`

The owner controls staging, commits and publishing. Include the versioned migration, verification scripts, tests and docs; exclude populated env files, cache artifacts and generated build output.

## 24. Phase 4 preview

Next, agree on PDF text extraction and OCR requirements/provider before implementation. Evaluate digital versus scanned PDFs, language support, file/page limits, parser isolation, retention/consent and an auditable extraction schema. Reuse the original bytes, verified owner manifest and private access boundary; do not infer safety or medical meaning from `uploaded`.

Any required cloud/OCR account or credentials must be configured by the owner with exact instructions and confirmation at that phase's setup gate. Do not add an OCR provider, queue, processing state, extracted value, medical range or AI summary until the next phase is explicitly authorized.

**STOP — Phase 4 has not started.**
