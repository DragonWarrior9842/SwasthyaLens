# Phase 13 ownership and security verification matrix

Every BFF resource below requires a verified current session. Browser navigation is a usability layer; server JWT issuer/audience/signature/expiry/nbf checks and active-session lookup remain authoritative. The eight-hour absolute session limit and owner-revision checks are unchanged. Exact Origin plus nonce-bound signed CSRF protects writes. The Phase 13 schema-enumerating regression exercises **every documented POST/PUT/PATCH/DELETE** with an authenticated cookie but no CSRF token and requires denial.

| Resource / public tables | Supported actions | Owner rule / direct API rule | Verification |
|---|---|---|---|
| Profile / `profiles` | Read, update own profile | Current user only; user ID cannot be reassigned | auth/account unit tests; live ownership; schema + rls-isolation SQL; auth browser |
| Preferences / `user_settings` | Read, update UI/assistant language, timezone, notifications | Current user only; closed language enums; no identity change | live ownership/multilingual; multilingual SQL; settings/multilingual browser |
| Report / `reports` | Reserve, upload, list, read, download, delete, bounded cleanup | Owner UUID path, durable upload lease and hash; no foreign ID mutation/download | reports units/adversarial; live reports; reports-rls-isolation SQL; report browser |
| Private Storage `reports` bucket | Upload/read/delete exact report object | Non-public, owner prefix and matching authorized report lifecycle; no public object URL | real A/B Storage tests and report SQL; bucket metadata audit |
| Extraction / `report_processing_runs`, `report_pages` | Explicit trigger, list attempts, read page output | Owner report/current source; processing writes require worker-secret RPC plus owner session | extraction units/OCR; live extraction/restart; extraction lifecycle/schema SQL; extraction browser |
| Parameters / `report_parameter_runs`, `report_parameter_candidates`, `report_parameter_reviews` | Explicit extraction, read candidates, append personal review/correction | Owner report/current source; review revision optimistic concurrency; no arbitrary source replacement | parser/review units; live parameters; parameters SQL; parameter browser |
| Observations / `health_observations`, `health_observation_revisions` | Explicit publish, manual create/list/read/update/delete | Current owner; source revision and active status; exact strings/units preserved | observations units; two live observation tests; observations SQL; history browser |
| Trends | Read bounded deterministic aggregates | Current-owner active observations only; no cross-account merge; no correlation inference | trends units/live/SQL/browser |
| Explanation / `report_explanations` | State/read; explicit synthetic generation only | Owner and current evidence snapshot; opaque IDs, exact facts and fixed versions revalidated; release rejects mock records | grounding/adversarial units; live explanations with mock provider; explanation schema/lifecycle/limits/Gemini SQL; explanation browser |
| Conversation / `assistant_conversations` | Create/list/read/delete | Owner session and UUID; deletion removes owned messages | assistant units; live assistant isolation; assistant SQL/browser |
| Message/evidence / `assistant_messages` | Explicit send, read within owned thread | Message ID never grants independent access; evidence retrieved from current owner/source, stale/deleted answer data removed | two live assistant tests; context/adversarial/language units; assistant lifecycle SQL/browser |
| Export (no persisted export table) | Explicit POST download of JSON/CSV | Current owner/current facts; optional report ID reauthorized; no retained download URL | exports units/live/SQL/browser; no-store headers |
| Notification / `notifications` | Bounded list/read/unread state, mark read, dismiss, mark all | Owner UUID; generic closed event type, no values/document text | notifications units/live; exports-notifications SQL; A/B browser |

All 14 public tables above were observed with both RLS and FORCE RLS enabled. The private explanation-attempt, budget and evaluation-enrollment tables also have forced RLS with no ordinary-user policies: deliberate default-deny. The private processing-key table is an explicit exception: RLS is not enabled, but privileges are revoked from public/anon/authenticated/service_role and access is confined to restricted definer functions; its schema is not exposed. Do not claim that every private table has RLS.

The audit found no service-role credential or shortcut in ordinary application flows. The backend uses the publishable key plus the verified user's JWT. Definer functions use constrained search paths, explicit ownership/current-session checks and, where appropriate, the private processing capability. Admin verification tools have privileges independent of the product; they are not shipped to the client.

## Negative and adversarial coverage

- Anonymous/expired/revoked/inactive sessions, malformed identifiers, foreign report/observation/conversation/message/notification IDs, unauthorized direct Data API and Storage access, and cross-tab account changes.
- Missing/wrong CSRF token, foreign/missing Origin, credentialed CORS wildcard rejection, invalid Host, spoofed forwarded headers, release provider injection, accidental integration flags and placeholder configuration.
- Malformed JSON/schema, unsupported enums/extra fields, excessive text, invalid dates/ranges/pagination, oversized files, MIME/extension/magic mismatch, damaged/encrypted/excess-page PDFs, invalid/huge images and parser failures.
- Source correction/delete invalidation, optimistic revision conflicts, explanation/conversation stale evidence, export regeneration after deletion, generic notification isolation.
- English/Hindi/Hinglish prompt injection, secret/foreign-data demands, diagnosis fabrication, changed values/units/ranges, unknown/duplicate evidence IDs, unsupported structured output and history treated as a factual source use deterministic synthetic providers. Separately, **one explicitly authorized OpenAI / `gpt-6.1-sol` synthetic adapter request passed HTTP 200/schema/evidence/safety**, with no database/Storage access or retries; it does not establish live adversarial, multilingual, persisted Phase 7 or Phase 9 acceptance. Historical Gemini remains blocked by two HTTP 503 responses (2/20). See the [attempt report](openai-acceptance-2026-10-03.md).
- Release safety tests verify safe 500 payload/log output without raw paths/query/exception contents, total body-read deadlines, failed-upload cleanup and released capacity, secure cookies/headers, disabled AI and rejection of stored mock output.

## Capacity and retry inventory

| Boundary | Existing or hardened limit |
|---|---|
| Auth | In-process 15/min peer/endpoint (email-related 3/min); CSRF issuance 120/min; external edge enforcement required for release |
| Request body | JSON 16 KiB / total read deadline 30s; exact upload route <=5 MiB / total read deadline 60s; four upload slots |
| Reports | 60/min owner/method; cleanup 5/min with at most ten candidates and cooldown; private bucket 5 MiB PDF/JPEG/PNG only |
| OCR | 20 pages; PDF side 1,440pt; source image 40M pixels; rendered page 12M pixels/10,000px side; child memory 768 MiB; 64 MiB temp; 120s process/30s OCR; two workers; three attempts/report; ten triggers/min; bounded page text/spans/output |
| Parameters | Five-second parser, two slots, 20 pages/400k source characters/512 rows/200 candidates; three attempts/source and nine/report; bounded reviews |
| Observations | 1,000 lifetime identities/account, 100 revisions; list page 20 and bounded offset; dashboard only recent owned entries |
| Trends | Fail closed on 501st row or 51st group; bounded periods; 30 reads/min; exact Decimal calculations; unsupported correlations remain unavailable |
| Explanations | 20 facts, 32 KiB context, 48k request/128k response, 4k output tokens; 3 new/min, 20/day, one/user and two global; 45s provider; permanent 20 Gemini attempts |
| Assistant | 24k context, four historical excerpts <=500 chars, bounded current facts; 20 conversations/25 pairs; one pending/user and two global; 6 new/min, 100/day over retained messages; 45s provider/60s service/90s pending fence |
| Export | <=366 days, 200 observations/20 reports/2 MiB, 6/min, two slots; 15s elapsed/20s request/25s browser timeout; explicit regeneration, no retained artifact |
| Notifications | Page20/max100 offset; <=100 rows/account, 30-day retention; 60/min; generic copy |
| Voice | Explicit local-only capability check; bounded listening/start/stop/playback; <=2,000-char input, <=1,000-char playback; no audio upload/storage; no automatic send/download of packs |

Provider/Storage HTTP calls have finite deadlines and bounded responses. There is no automatic live-AI retry or provider fallback. Browser refresh is bounded and synchronized; writes are not automatically replayed after network failure. Durable idempotency keys handle explicit retries where supported. These local limits do not claim distributed enforcement or volumetric DDoS protection.

## Dependency and license review

The 2026-10-03 baseline public advisory audit covered 42 locked Python entries and the npm lock. Two fixable findings were addressed:

| Finding | Exposure/classification | Change |
|---|---|---|
| PyJWT 2.14.0, GHSA-42vr-xj54-vc7v (PYSEC-2026-4141 alias) | Runtime transitive/direct dependency; nested JSON can cause request-level RecursionError; app does not use the advisory's unverified-payload/PyJWKClient path; defense-in-depth P2, no auth bypass claimed | PyJWT 2.15.0 only, new verified hashes; full auth/regression acceptance |
| brace-expansion 5.0.9 advisories GHSA-q2hr-2g5m-vwhr, GHSA-qhr7-859c-m2p7, GHSA-6j4f-fj2g-mc7p | Development-only transitive ESLint/minimatch dependency, provider-rated moderate/high resource exhaustion; not browser runtime exposure; P2 | Compatible 5.0.12; no major/framework upgrades |

[PyJWT advisory](https://github.com/jpadilla/pyjwt/security/advisories/GHSA-42vr-xj54-vc7v), [PyJWT release](https://github.com/jpadilla/pyjwt/releases/tag/2.15.0), [brace-expansion advisory](https://github.com/juliangruber/brace-expansion/security/advisories/GHSA-q2hr-2g5m-vwhr).

Final npm full-lock audit reports zero known findings (249 dependencies including optional platform entries). Apart from the two version changes, npm added metadata for already bundled optional WASM dependencies; runtime versions did not change. Python locks differ only in the three PyJWT version/hash lines each after preserving the Windows OCR hash. Native OS/browser/managed-provider packages require separate deployment-image vulnerability maintenance; package-registry scans are not a penetration test or proof of absence of vulnerabilities.

Engineering license inventory (not legal certification):

| Material components | Declared licenses / action |
|---|---|
| React, React DOM, React Router, Chart.js, @kurkle/color, scheduler, cookie, set-cookie-parser | MIT; retain notices with distributed assets |
| FastAPI, Pydantic/core/settings, anyio, annotated-doc/types, h11, PyJWT, tesserocr, typing-inspection | MIT |
| cffi | MIT-0 |
| HTTPX/httpcore, Starlette, Uvicorn, click, idna, pycparser, python-dotenv | BSD-3-Clause |
| cryptography | Apache-2.0 OR BSD-3-Clause; preserve bundled/native notices |
| email-validator, dnspython | Unlicense, ISC respectively |
| Pillow | MIT-CMU plus bundled native notices |
| certifi | MPL-2.0; preserve file-level license/source obligations on redistribution |
| typing_extensions / Python; tzdata | PSF-2.0 / PSF; Apache-2.0 data packaging |
| pypdfium2 / PDFium | BSD-3-Clause, Apache-2.0 and dependency licenses; retain the complete packaged notice set |
| Tesseract / Leptonica / OCR models | Apache-2.0 / BSD family / upstream model notices; record exact native artifacts in deployment image |
| cysignals 1.12.6 (Linux-only tesserocr dependency) | LGPLv3; review source/relinking/notice obligations if distributing a runtime/container; not present in the Windows runtime install |
| TypeScript, Vite, ESLint, Tailwind, Vitest and build transitives | Primarily MIT/Apache/BSD/ISC; lock also includes MPL-2.0, BlueOak-1.0.0 and CC-BY-4.0 metadata; preserve package notices |
| pytest, Ruff, mypy, uv and test tooling | Development-only; preserve their upstream notices if distributing the development environment |

No licensing acceptance for a future distributed production image is implied. Native artifacts and any future additions require another inventory at release time.
