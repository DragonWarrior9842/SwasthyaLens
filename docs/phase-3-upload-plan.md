# Phase 3 — Private reports: implementation plan

Status: implementation authorized by the owner; Phase 3 only. Baseline commit inspected: `53a8c54`. Phase 2's locked email-template limitation remains documented; no OTP workaround is part of this phase.

Before changing application source, re-read the audit, both completed phase handoffs, the authentication plan and README, then inspect the current frontend/backend/database implementation. Baseline results: frontend lint/typecheck/build passed, 76 tests passed; backend lint/format/mypy passed across 33 files, 133 tests passed, one live test intentionally skipped, two known upstream warnings. The baseline working tree was clean. Sandbox cache/temp restrictions required authorized retries; they were not application failures.

## Architecture and scope

```text
Browser (same-origin cookies, fresh CSRF, coordinated session writes)
  -> POST /api/reports: reserve owner metadata and generated immutable object path
  -> PUT /api/reports/{id}/file: raw PDF/JPEG/PNG body
       -> verify identity + active session + Origin + signed CSRF before reading bytes
       -> enforce declared and streamed size limits; validate filename/type/content
       -> acquire durable upload lease and record content hash
       -> Supabase private Storage using publishable key + user's JWT, no upsert
       -> persist uploaded status only after storage confirmation
  -> GET list/detail: verified owner repository + database RLS
  -> GET file: owner/session checks + bounded backend attachment response
  -> DELETE report: durable deletion intent, Storage API removal, scrub file metadata
       -> retain minimal cleanup manifest for uncertain/late provider operations
```

No change to the Phase 2 identity model is needed. No browser provider tokens, service-role key, database password or storage admin credential is introduced. Binary upload is a narrow extension to the transport/body limit and accepted content type for that route; Origin, signed CSRF, active session and owner checks remain mandatory. Existing JSON/auth limits stay unchanged.

Reports have one file each in this phase. Use one `reports` table instead of speculative file/job/processing tables. There is no OCR worker, extraction, analysis, processed state, trend data or AI context.

## Storage and setup

Bucket: `reports`, **private**, maximum 5 MiB (5,242,880 bytes), MIME allowlist `application/pdf`, `image/jpeg`, `image/png`. The server's `REPORT_MAX_UPLOAD_BYTES` may lower this limit; raising the bucket/schema cap requires a reviewed migration. This conservative limit bounds application memory and provider transfer time for the first implementation.

Official Supabase documentation supports creating buckets through SQL. Read-only preflight found no existing bucket or storage policies in the selected development project, so the reviewed versioned migration can configure the bucket reproducibly. No manual dashboard bucket setup is needed on this path. Apply only after the complete migration and policies are reviewable; never silently convert or repurpose an existing bucket. Actual object writes/deletes must use Storage's API, not SQL metadata deletion. [Creating buckets](https://supabase.com/docs/guides/storage/buckets/creating-buckets).

Object keys are generated from verified owner UUID, server-generated report UUID and random object UUID. Uploaded names are never used as storage keys. Storage policies require the exact registered path, owner and active provider session, plus the applicable lifecycle state. Restrict operations to the upload/read/info/delete calls actually used; no public download, signed URL creation, overwrite/upsert, copy/move or resumable-upload capability is planned.

## Minimal durable lifecycle

- `pending_upload`: owned reservation exists; bytes have not been confirmed stored.
- `uploading`: validation passed in the API and an exclusive, expiring upload lease is recorded; storage I/O may be in flight.
- `uploaded`: the object is present and metadata checks succeeded. This means stored, not OCR processed or medically validated.
- `upload_failed`: the attempt failed; preserve content hash/lease when storage completion is uncertain. Safe retries require matching content and no active competing lease.
- `deleting`: user requested deletion/cancellation; new uploads and normal downloads are denied. Keep this state when removal cannot yet be confirmed.
- `deleted`: sensitive file metadata is scrubbed and removal was confirmed at that attempt. Retain only the owner/opaque IDs, immutable cleanup path, idempotency key and relevant lifecycle timestamps for reconciliation; exclude this tombstone from ordinary history/detail.

An owner-scoped idempotency key protects reservation retries. Retain it on deletion so a delayed reservation retry cannot recreate the report. Existing-object retries verify the stored bytes/hash instead of overwriting the key. Ordinary user requests cannot hard-delete the sole cleanup manifest through the Data API. Account deletion must eventually coordinate storage cleanup before deleting its authoritative user; Phase 2 does not offer an account-delete endpoint.

Storage and database changes are not one atomic transaction. Supabase can finish an already-authorized upload after its caller times out or requests cancellation. Deletion waits for known active upload leases; uncertain operations remain discoverable, and owner-authenticated cleanup retries recheck deletion manifests. A cancelled browser request alone never means the object was removed. This phase does not invent a privileged background worker; production-wide reconciliation/retention requirements must be stated in the handoff.

## API contracts

| API | Contract |
|---|---|
| GET `/reports/config` | Safe maximum byte count and MIME allowlist |
| POST `/reports` | Strict JSON filename/media type/size/idempotency UUID; no authoritative owner field |
| PUT `/reports/{id}/file` | Raw allowed file bytes, cookie authentication, exact Origin and signed CSRF; no multipart dependency needed |
| GET `/reports` | Owner-only newest-first list, stable ID tie-break and bounded cursor pagination |
| GET `/reports/{id}` | Owner metadata; missing/unrelated/deleted records share a safe not-found response |
| GET `/reports/{id}/file` | Owner-only attachment through backend; no stored/shared download URL |
| DELETE `/reports/{id}` | JSON `{}` plus CSRF; 200 `deleted` or 202 `deleting`, safely retryable |
| POST `/reports/cleanup` | CSRF-protected bounded retry of the current owner's previous deletion intents |

Public metadata includes ID, safe original filename, type, byte count, lifecycle status, timestamps and allowlisted failure category. Do not expose provider errors, storage paths, leases, content hashes or another user's existence. Downloads use attachment disposition, `nosniff`, `no-store` and sandboxing headers; no inline PDF/HTML rendering.

## Validation and user experience

Support `.pdf`, `.jpg`, `.jpeg`, `.png` only. Validate extension, declared MIME, bytes/signature, empty file, streamed size, reservation size and filename. Bound filenames to 120 characters/240 UTF-8 bytes; reject traversal/separators, absolute paths, control/bidirectional characters and unsafe platform names. Content remains untrusted even after format checks: never execute it, trust embedded instructions, extract medical text or represent format checking as malware scanning. Revalidate bytes before future OCR and do not treat a user-accessible database status as an attestation of safe content.

The Reports page replaces its existing empty-only content with a real chooser, upload/cancel feedback, owner history, private download, delete confirmation and retry states. Preserve the established shell, mobile navigation and account controls. Explain that users should upload only reports they have permission to store, files remain private until deletion, and OCR/analysis is unavailable. Use truthful indeterminate progress; no fabricated values, AI responses or processing percentages. Client validation is feedback, not authorization.

## Files and verification

New backend report schemas/routes/repository/lifecycle/storage/validation modules and focused tests; narrow changes to configuration, body/CSRF handling, factory and provider error mapping. New frontend report types/services/components/tests with shared transport extensions. New versioned database migration and schema/RLS tests. Update the server environment example, README, database instructions and `docs/phase-3-handoff.md`.

Before final handoff: run all prior lint/type/test/build checks; real two-user metadata/storage isolation; malformed/spoofed/oversize uploads; protected download and revocation; retry/cancel/delete/provider-failure paths; browser desktop/mobile report flows; secret/configuration checks. Preserve the Phase 2 email limitation. Do not declare Phase 3 complete from mocks alone. Stop after the Phase 3 handoff; do not start Phase 4.
