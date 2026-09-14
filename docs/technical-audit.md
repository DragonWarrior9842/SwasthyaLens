# SwasthyaLens — Technical Audit and Development Plan

Audit date: 13 September 2026. Workspace: `P:\Projects\SwasthyAlens`.

> Historical baseline: this audit records the workspace before application implementation. Phase 1 was subsequently authorized on 14 September 2026. See [the Phase 1 handoff](phase-1-handoff.md) for the current implementation and validation status. The original findings and proposed roadmap below are retained for traceability.

Evidence labels used throughout: **Observed** means directly inspected; **Reference** means content in the supplied designs; **Proposed** means future architecture or work, not existing functionality.

## 1. Executive Summary

**Observed: this project starts from an empty workspace.** A recursive inspection including hidden items returned zero files and zero subdirectories. Git reported `fatal: not a git repository (or any of the parent directories): .git`. There was no source code to audit, no manifest to identify versions, no API to trace, and no database schema or build to test.

The owner subsequently confirmed that they will create the Git repository later and push the local files themselves. This removes Git hosting as a prerequisite. It does not change the original analysis-only boundary: this deliverable creates documentation only.

The supplied Keynote deck contains eight slides. Its proposed stack is React, Vite, Tailwind CSS, FastAPI/Python, Supabase PostgreSQL and Storage, unspecified OCR/PDF and LLM integrations, and Vercel/Render hosting. These are **design proposals**, not installed technologies. No versions, authentication implementation, AI model, OCR provider, service credentials, schema, or deployed application were established.

The requested product requires a complete implementation. The most important architectural dependency is trustworthy user-owned structured health data: reports must retain original values, units, dates, source locations, and report-specific ranges before summaries, trends, or chat can rely on them.

No exploitable application vulnerability was confirmed because no application exists in the inspected workspace. This is not a security clearance. External account configuration and any source/history outside the provided workspace remain unassessed.

This report includes an evidence-based inventory of the absence of implementation and a proposed architecture and roadmap. It is not a code-level audit of an existing system. No framework or external provider has been installed or configured.

## 2. Repository Structure

### Baseline inspected

```text
P:\Projects\SwasthyAlens\
└── empty: 0 files, 0 subdirectories, including hidden entries
```

Read-only checks included `rg --files --hidden`, Git status/tracked-file inspection, a forced recursive PowerShell enumeration, the immediate parent directory inventory to rule out an obvious spelling variant, and checks for parent/project `AGENTS.md` files. The recursive enumeration completed successfully. No parent instructions were found at the checked locations.

There were no `package.json`, lockfiles, `pyproject.toml`, requirements files, TypeScript/build/lint configuration, `src`, `app`, `pages`, components, hooks, services, API/server/backend directories, migrations, Prisma/Supabase/Firebase configuration, middleware, auth files, public assets, styles, environment files, Docker/deployment configuration, tests, scripts, README, or GitHub workflows. Consequently there were no source bodies available for deeper code searches.

### Reference material inspected outside the workspace

| Evidence | Inspection and scope |
|---|---|
| `C:\Users\aasbl\Downloads\ppt\SwasthyaLens.key` | 1,360,988-byte Keynote archive; archive inventory, readable slide text, and all eight embedded slide thumbnails inspected. No application source or HTML prototypes found inside. Native Keynote rendering was not performed. |
| `Screenshot 2026-09-13 at 9.36.36 PM.png` | Report-analysis target. Actual filename contains a narrow space before PM. |
| `Screenshot 2026-09-13 at 9.37.10 PM.png` | Trends target. |
| `Screenshot 2026-09-13 at 9.37.01 PM.png` | Same trends design in Chrome on a different machine. |
| `Screenshot 2026-09-13 at 9.38.58 PM.png` | Assistant target. |

The Chrome screenshot shows `/Users/aaminahasan/.verdent/verdent-projects/create-slide-1-swasthyalens/prototypes/ui3_trends.html`. This is a reference to a local file on another machine, not an available Windows source file or deployed URL.

The eight deck slides are: SwasthyaLens; AI-Powered Community Health Intelligence; The Problem & Our Objectives; How SwasthyaLens Works; Key Features — From Health Data to Action; AI Health Intelligence & Community Insights; Technology & Prototype; Impact & Future Scope. Dashboard concepts appear on slides 5 and 7.

### Files produced by this analysis

```text
P:\Projects\SwasthyAlens\
├── README.md
└── docs\
    └── technical-audit.md
```

These new documents must not be mistaken for pre-existing repository content. Temporary reference previews were extracted outside the project into the permitted visualization directory. Original attachments were not changed.

## 3. Current Tech Stack

**There is no implemented technology stack or identifiable dependency version.** Tools installed on the workstation do not establish project dependencies.

| Layer | Current verified state | Reference proposal / unresolved choice |
|---|---|---|
| Frontend framework/language | No code | React proposed; TypeScript recommended for later implementation |
| Build/rendering | No build configuration or rendering behavior | Vite proposed; client-rendered SPA is a candidate |
| Routing | None | Select router during foundation phase |
| Styling/components | None | Tailwind proposed; component library undecided |
| Charts | None | Select a maintained library when real metrics are available |
| State/forms/validation | None | Local UI state plus typed API boundary; form library not yet justified |
| Backend | None | FastAPI/Python and REST/JSON proposed |
| API routes/actions/middleware | None | Explicit backend endpoints; no existing server actions |
| Background jobs | None | Durable report-processing worker needed |
| Database | No configuration or schema | Supabase/PostgreSQL proposed |
| ORM/query/migrations/RLS | None | Query path and migration tooling need selection; isolation policies required |
| Authentication | None | Provider, session integration, and recovery flows unselected |
| Storage | None | Supabase Storage proposed; private report/export storage required |
| AI | No SDK, model, prompts, context, or embeddings | Deck names an unspecified LLM API; selection deferred |
| Analysis/ML | None | Deck mentions Python/scikit-learn; a dependency is not yet justified |
| OCR/PDF/images | No extraction implementation | Provider/library unselected |
| Voice | No STT, TTS, or browser-audio code | Future capability only |
| Localization | No locale files or translation library | English/Hindi initially; Hinglish response behavior required |
| Deployment | No manifests, projects, URLs, or secrets configuration | Vercel frontend + Render backend proposed; not configured |
| Testing | No unit, integration, E2E, coverage, or CI setup | Tooling and acceptance fixtures to establish |

Slide 7, archive member `Index/Slide-824-2.iwa`, is the evidence for the proposed technologies. It labels the interface “PROPOSED PRODUCT INTERFACE” and “Illustrative UI — proposed prototype.”

## 4. Current Architecture

No running client, authentication boundary, server, database, or service integration exists in the workspace. There is no architectural implementation to preserve or replace.

Current assets describe the intended interaction between Dashboard, Reports, Trends, and AI Assistant. Their links, buttons, charts, upload indicators, language selectors, and typing states cannot execute from screenshots or slide shapes.

Community aggregation, area-level signals, symptoms, wearables, and low-bandwidth access appear in the deck. They are additional concepts, not permission to expand this implementation roadmap. Community-data use especially needs a separate product/privacy decision.

## 5. Architecture/Data Flow Diagram

### Actual state

```text
Owner's requirements + Keynote + screenshots
                    |
                    v
            Product reference material

Selected workspace at audit start: empty
Client -> Auth -> API -> Business logic -> Database -> AI/OCR/Storage
  ALL APPLICATION LAYERS ABOVE ARE ABSENT
```

### Target report flow — proposed, no stage implemented

```text
Authenticated browser
  -> API derives identity from verified session
  -> validate upload request; reserve owned report/file record
  -> private quarantine upload
  -> verify actual content, size, type, pages/pixels
  -> durable processing job
  -> PDF text extraction and/or page/image OCR
  -> extracted text with page/source provenance
  -> structured parameter candidates
  -> validate values, units, dates, ranges; review uncertainty
  -> validated health observations in database
  -> deterministic report-range comparison
  -> grounded educational AI explanation
  -> report detail + history + dashboard
  -> compatible observations feed trends
  -> authorized facts/calculations feed assistant context
```

Failure at any stage must retain its actual state and allow an appropriate retry or review. Processing must be idempotent: retries cannot create duplicate observations. Successful OCR does not by itself mean a report is validated or explained.

## 6. Feature Audit

Status meanings: IMPLEMENTED = working code path verified; PARTIALLY IMPLEMENTED = some executable stages verified; UI ONLY / MOCKED = executable presentation or mock without real backing; BROKEN = an existing path fails; NOT IMPLEMENTED = absent from this project; UNKNOWN = insufficient evidence about an external state.

Every application feature below is **NOT IMPLEMENTED** in this workspace. Where a design exists, it is identified separately; a reference screenshot is not a working UI-only implementation.

| Feature | Status | Available evidence / missing path |
|---|---|---|
| Authentication | NOT IMPLEMENTED | No identity provider or auth code |
| User accounts/profiles | NOT IMPLEMENTED | No users or profile model |
| Dashboard | NOT IMPLEMENTED | Slides 5/7 illustrate My Health Overview |
| Report upload | NOT IMPLEMENTED | Screenshot contains an upload area only |
| PDF upload | NOT IMPLEMENTED | PDF accepted in design copy only |
| Image upload | NOT IMPLEMENTED | JPG/PNG named in design only |
| File validation | NOT IMPLEMENTED | No limits, signature checks, parser policy |
| OCR | NOT IMPLEMENTED | OCR-complete label is illustrative |
| Medical parameter extraction | NOT IMPLEMENTED | Fixed parameter table in screenshot |
| Reference ranges | NOT IMPLEMENTED | Fixed reference intervals in screenshot |
| Report summaries | NOT IMPLEMENTED | Fixed summary text |
| Report history | NOT IMPLEMENTED | Four illustrative history cards |
| Database persistence | NOT IMPLEMENTED | No schema or query code |
| Health trends | NOT IMPLEMENTED | Illustrative line charts only |
| 7-day trends | NOT IMPLEMENTED | Toggle and dashboard design only |
| 30-day trends | NOT IMPLEMENTED | Toggle and selected design only |
| Glucose | NOT IMPLEMENTED | Illustrative curve, no observations |
| Sleep | NOT IMPLEMENTED | Fixed summary and mini-chart |
| Activity/steps | NOT IMPLEMENTED | Fixed count and mini-chart |
| Weight | NOT IMPLEMENTED | Fixed stable label/mini-chart |
| Heart rate | NOT IMPLEMENTED | Metric concept/tab only |
| Hemoglobin | NOT IMPLEMENTED | One sample report row |
| Vitamin D | NOT IMPLEMENTED | One sample report row |
| TSH | NOT IMPLEMENTED | One sample report row |
| Pattern detection | NOT IMPLEMENTED | Fixed increasing/flagged messages |
| Correlation detection | NOT IMPLEMENTED | Fixed sleep/glucose association claim |
| Suggested next steps | NOT IMPLEMENTED | Fixed informational copy |
| AI assistant | NOT IMPLEMENTED | Illustrated conversation only |
| Report-aware chat | NOT IMPLEMENTED | No retrieval or report ownership check |
| History-aware chat | NOT IMPLEMENTED | No history/context mechanism |
| Multilingual chat | NOT IMPLEMENTED | Language controls and Hinglish copy only |
| Hindi | NOT IMPLEMENTED | Hindi language option only |
| English | NOT IMPLEMENTED | English reference copy, no application |
| Hinglish | NOT IMPLEMENTED | Fixed Romanized-Hindi conversation |
| Voice input | NOT IMPLEMENTED | Voice labels/icons only |
| Voice output | NOT IMPLEMENTED | No synthesis/playback code |
| Export | NOT IMPLEMENTED | Button only |
| Notifications | NOT IMPLEMENTED | No delivery, unread state, or preferences |
| Loading states | NOT IMPLEMENTED | Typing indicator illustration only |
| Error handling | NOT IMPLEMENTED | No exceptions, boundaries, retry handling |
| Responsive design | NOT IMPLEMENTED | Desktop references; no CSS to inspect |
| Mobile support | NOT IMPLEMENTED | No executable layout or device test |

There is no evidence supporting an IMPLEMENTED, PARTIALLY IMPLEMENTED, or BROKEN application status. Existing external accounts/deployments are UNKNOWN, rather than presumed absent everywhere.

## 7. Mock/Hardcoded Data Audit

**Source-code findings: none, because there was no source.** There are no inspectable TODO/FIXME markers, fake API calls, demo identities, temporary IDs, timers, sample JSON files, localStorage, or sessionStorage usage. This is an absence-of-code result, not a successful scan of a historical repository.

The following fixed values are in the supplied references:

| Location | Illustrative data | Required replacement |
|---|---|---|
| Reports screenshot, parameter table | Hemoglobin 13.2 g/dL; reference 12–15 | Verified source value/unit and report-supplied range |
| Same table | Vitamin D 18 ng/mL; reference 30–100 | Verified source value/unit and applicable source range |
| Same table | TSH 2.4 mIU/L; reference 0.4–4.0 | Verified source value/unit and applicable source range |
| Reports screenshot, upload/status | `blood_report_may.pdf`, two pages, OCR complete/processed | Actual private file metadata and processing state |
| Reports screenshot, history | Blood Report—May, Lipid Profile—Feb, Prescription—Apr, X-Ray Scan—Jan | Owner-scoped database records and actual statuses |
| Reports screenshot, summary | Fixed interpretation of three sample parameters | Educational explanation grounded in validated parameters |
| Trends screenshot/dashboard slides | Sleep 7h 10m; activity 6,240 steps; stable weight | Actual dated measurements and defined aggregations |
| Trends screenshot | Rising glucose curve and increasing classification | Real observations and documented trend calculations |
| Trends screenshot | Shorter sleep followed by higher next-day readings | Computed association with adequate paired data and uncertainty |
| Assistant screenshot/slide 7 | Fixed Hinglish dialogue and glucose chart | Authenticated conversation, authorized context, grounded response |
| Slide 5 | “Unusual readings: 2 flagged” | A defined, tested flagging method applied to real records |

Slide 5 explicitly states that its UI example is not real medical data. Do not turn any reference numbers, patient identity, ranges, classifications, or AI wording into default user records. Synthetic test fixtures must be clearly identified and confined to testing.

## 8. Frontend Analysis

No component tree, routes, forms, state store, styles, chart code, localization files, or browser persistence exists.

The target navigation is coherent: Dashboard provides an overview; Reports owns upload, review, explanation and history; Trends exposes measured changes; Assistant explains selected evidence. Reusable future components should include application navigation, metric selectors, date filters, report status, parameter tables, evidence references, and genuine empty/error/loading states.

The desktop sidebar, multi-column report layout, wide charts, and assistant conversation need mobile equivalents. Verify keyboard operation, focus handling, labeled upload controls, screen-reader announcements, sufficient contrast, chart text/table alternatives, Hindi font rendering, and layouts with long filenames and translations.

Do not render personalized health content in shared/public caches. Avoid persistent health data in browser storage by default. A design may initially show an empty feature page, but it must not claim OCR, AI, voice, or export works before the real path exists.

Proposed frontend choices: React with TypeScript, Vite, and Tailwind following the deck; a small router; component-local state first; schema-validated API responses where needed. Select forms, charting, and server-state libraries for concrete needs rather than installing a broad collection in advance.

## 9. Backend Analysis

No backend exists: there are no HTTP handlers, server actions, business services, middleware, jobs, webhooks, validation, or error mappings.

The proposed FastAPI service should own authentication verification, authorization, validated request/response models, report lifecycle, deterministic health calculations, and provider integrations. Keep route handlers thin and isolate database access, storage, OCR, and AI behind explicit service interfaces. FastAPI supports a typed validation/OpenAPI foundation; it is a candidate from the deck, not an installed dependency. [FastAPI features](https://fastapi.tiangolo.com/features/).

Expensive OCR/extraction should use durable jobs that survive a request or process restart. Start with one API service and one worker role from the same backend codebase. A database job table may be sufficient initially; choose queue infrastructure based on hosting limits and workload. Do not assume an in-process background callback is durable.

Use request IDs, safe error codes, explicit timeouts, bounded retries, idempotency keys, user quotas, and stage-specific statuses. Return sanitized errors; keep raw provider responses and report content out of ordinary logs.

## 10. Database Analysis

**Current database:** none configured in source. There are zero schema files, migrations, query definitions, constraints, relationships, or policies to inspect. Existence/configuration of external databases is unverified.

### Proposed logical schema — not a migration

| Entity | Purpose / important fields | Relationships and security |
|---|---|---|
| `users` / identity mapping | Stable internal ID mapped to verified provider identity | Session determines account identity |
| `profiles` | Optional display name and necessary demographic context | One per user; minimize sensitive fields |
| `user_settings` | UI locale, response language, timezone, consent/preferences | One per user; private |
| `reports` | Owner, title, report/collection date, source, lifecycle state | Parent for report-owned records |
| `report_files` | Private object key, original name, verified type, bytes, checksum, pages | Owned report; private storage reference |
| `processing_runs` | Stage, attempt, state, versions, idempotency key, timestamps, safe error | Report/file owner consistency; bounded retries |
| `extraction_pages` or equivalent | Extracted text, page, source locations, extraction method/version | Sensitive report-owned content; controlled retention |
| `report_parameters` | Candidate label, raw value, numeric/qualitative result, comparator, unit, range, source location, confidence, review state | Report + processing run; retain revisions |
| `metric_definitions` | Stable metric identity, dimensions, compatible units and aggregation rules | Shared curated catalog, not user health data |
| `metric_mappings` | Reviewed aliases and conversion/mapping versions | Ambiguous source labels remain unresolved |
| `health_observations` | Validated original/normalized value, units, date precision, context, source, quality | Owner + metric; optional source parameter; manual sources distinguished |
| `conversations` | Owner, title, language, timestamps | Every access checks owner |
| `messages` | Role, content, state, language, generation metadata | Owned conversation; browser cannot assign privileged roles |
| `ai_insights` | Educational output, language, prompt/model version, input version, freshness | Owner-scoped generated content |
| `insight_evidence` / `message_evidence` | Statement-to-source links and source versions | Referenced sources must share ownership |
| `audit_events` | Actor, action, resource, timestamp, outcome | Restricted; no raw health text or secrets |
| `export_jobs` | Owner, scope, format, state, private artifact, expiry | Verify ownership at request, generation, download |
| `trend_snapshots` (optional) | Window, algorithm/data versions, statistics and evidence | Add only when reproducibility/performance warrants persistence |
| `notifications` (later) | Owner, category, safe message, read/delivery state | No detailed health content in external notifications by default |

### Required modeling rules

1. Every private resource has enforceable ownership. Use owner-consistent parent/child keys or equivalent constraints to prevent one user's child record referencing another user's report/conversation.
2. Report parameters are extraction candidates; validated observations are trend inputs. Do not let uncertain OCR silently become measured health history.
3. Preserve original label, value text, unit, reference-range text, date text, page and source coordinates/text span. Normalization supplements originals.
4. Support qualitative and censored results such as `<5`; preserve the comparator. Use decimal/numeric representations suitable for source precision.
5. Distinguish measurement/collection date, report issue date, upload time, timezone, and date precision. A date-only result is not an exact timestamp.
6. Keep fasting/nonfasting or other measurement context when stated. Incompatible contexts/units cannot be merged silently.
7. Source-report intervals take precedence. Missing/ambiguous ranges remain unavailable or require review. Any later fallback needs an approved, versioned source and applicability rules.
8. Corrections retain source/revision history and invalidate affected observations, trends, summaries, and chat evidence. Define deletion propagation and retention before collecting real data.
9. Index owner/date/metric and owner/report access paths; enforce idempotency and provenance uniqueness to avoid duplicate imports.
10. Server authorization and database policies must both be tested. Privileged service roles may bypass RLS; do not assume a backend database connection automatically carries end-user identity. PostgreSQL documents role-specific RLS bypass behavior. [PostgreSQL row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html).

## 11. Authentication Analysis

No authentication provider, password handling, session storage, callback, protected route, or authorization model exists. The deck does not establish an authentication implementation.

A managed identity provider is a reasonable candidate. If the Supabase proposal is accepted, evaluate its Auth service alongside the database/storage choice; Auth is an additional recommendation, not a capability found in the project. [Supabase Auth](https://supabase.com/docs/guides/auth).

Prefer an established provider integration with a backend-managed secure session where feasible, using HttpOnly/Secure cookies, appropriate SameSite settings, expiration/revocation, and CSRF protection for cookie-authenticated mutations. Final session design must fit the selected origins/hosting and avoid a homemade password/JWT system.

The API must obtain identity from validated session credentials, never from request `userId`. Check report, parameter, observation, conversation, message, file, export, and job ownership on every operation. UI route guards alone do not authorize API access. Start with private single-user accounts; clinician, family, administrator, and community sharing require separately designed permissions.

## 12. API Inventory

**Existing backend endpoints: 0.** No route can be traced or executed.

| Method | Route | Purpose | Auth required? | Input | Output | Tables | External services | Status | Security concerns |
|---|---|---|---|---|---|---|---|---|---|
| N/A | No routes present | N/A | No mechanism exists | N/A | N/A | None | None configured | NOT IMPLEMENTED | No endpoint available for assessment |

Potential future API areas are authentication/session, profile/settings, report upload/list/detail/delete, file download authorization, processing status/retry, parameter review, observations, trends, insights, conversations/messages, and exports. Route names and request contracts will be finalized in their phases; they are not current endpoints.

All user-resource APIs need server-derived identity, schemas, bounded pagination, owner checks, safe errors, quotas, and appropriate cache controls. A report ID submitted for chat is a requested reference, never proof of authorization. Background jobs must preserve the same ownership constraints.

## 13. Report/OCR Pipeline Analysis

| Stage | Current status | Acceptance requirement before claiming it works |
|---|---|---|
| PDF/image selection | NOT IMPLEMENTED | Real browser file selection/drop interaction |
| Upload transport | NOT IMPLEMENTED | Authenticated transfer, progress, interrupted-transfer handling |
| File validation | NOT IMPLEMENTED | Server type/signature, bytes, page/pixel limits; filename safety |
| Private storage | NOT IMPLEMENTED | Owned private objects, retention and authorized access |
| Processing state/jobs | NOT IMPLEMENTED | Durable state, retry limits, idempotency, actual errors |
| PDF text extraction | NOT IMPLEMENTED | Readable PDFs preserve page/text provenance |
| OCR | NOT IMPLEMENTED | Scanned pages/images produce traceable text; provider undecided |
| Parameter/value/unit extraction | NOT IMPLEMENTED | Schema-valid candidates, qualifiers and uncertainty preserved |
| Range handling | NOT IMPLEMENTED | Source ranges captured and deterministically compared |
| Database write | NOT IMPLEMENTED | Transactional owned records without duplication |
| Simplified explanation | NOT IMPLEMENTED | Facts/calculations distinguished from AI narrative |
| History/trends/chat integration | NOT IMPLEMENTED | Only authorized, validated records used |

Provider evaluation must cover typed versus scanned PDFs, mixed pages, table/column layout, JPEG/PNG quality, rotation, English/Hindi text, provenance/confidence, latency, cost, data retention, deployment constraints, and encrypted/corrupt documents. OCR and PDF text extraction are different capabilities; do not send every readable PDF through OCR unnecessarily.

No OCR provider is selected in this analysis. Use representative synthetic or properly consented fixtures to choose and validate the integration later. A scan described as an X-ray in the reference does not authorize radiological image interpretation; define supported document classes explicitly.

## 14. AI Architecture Analysis

Current provider/model/SDK/prompts/structured outputs/embeddings/RAG/tools/context/memory/token controls/safety checks: **none implemented**. No evidence shows health data being sent to an AI provider.

Proposed uses should be separate: structured extraction where useful; report explanation from validated parameters; explanation of deterministic trend results; and contextual question answering. Do not make an LLM the authoritative source of measurements, ranges, or arithmetic.

Store versioned prompt templates server-side. For each generation retain model/prompt version, language, authorized evidence IDs/versions, relevant processing metadata and safe failure status. Validate structured output with strict schemas and verify that cited IDs belong to the permitted evidence set.

The server selects bounded report facts and calculated summaries from the authenticated user's data. Start with explicit structured queries for latest report, metric history, and period comparison. Embeddings/vector search are not prerequisites for these questions; add them only for demonstrated retrieval needs with the same ownership filters.

Conversation memory needs owned persisted messages, a bounded recent-message window, and evidence-aware summaries if context grows. Apply input/output limits, model context budgets, timeouts and spending quotas. Avoid carrying unrelated reports into every prompt.

Uploaded report text, filenames, prior messages and retrieved fragments are untrusted data. They cannot redefine system instructions, choose another user, authorize new tools, or request arbitrary SQL/files/URLs. Limit tools to typed, owner-scoped operations; prompt wording alone is not an access-control boundary. [OWASP prompt injection prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html).

Health-safety controls belong in prompts, schemas, retrieval, post-validation, UI copy and evaluation: educational explanations; no unsupported diagnosis or treatment claims; explicit uncertainty/missing-data handling; source citations; distinction between extracted values, calculations, generated explanation and professional-consultation suggestions. A disclaimer cannot repair fabricated evidence.

## 15. Trends Architecture Analysis

Current charts have no underlying code or database data. Curves and classifications in references are illustrative. There is no time-series representation, comparison algorithm, anomaly detector, or correlation engine.

Use validated observations with owner, metric identity, original/normalized units, context, source and observation date. Glucose, hemoglobin, Vitamin D, TSH, weight, heart rate, sleep and steps have different sampling patterns and aggregation semantics. Occasional laboratory tests should not be presented as daily readings.

For 7-day/30-day windows, define the user's timezone, inclusive/exclusive boundaries, current-day treatment and immediately preceding equal-length period. Return actual points, sample count, coverage and missingness. Use documented metric-specific aggregation when multiple observations occur in one day; for example, daily step totals and multiple laboratory readings are not interchangeable aggregation problems.

Calculate mean/min/max/change only when inputs support them. Define a zero-baseline policy for percentage change. Preserve gaps; do not manufacture readings or display interpolation as measurement. Insufficient history must produce “insufficient data,” not stable/increasing by default.

Direction classification requires a documented method, sufficient observations and explicit thresholds per metric/context. Mathematical direction does not establish clinical significance. Pattern/flag detection must state its rule and evidence; do not invent universal abnormal thresholds from the design.

Cross-metric correlation needs matched dates, defined aggregation/lag, enough paired observations, explicit missing-data handling, method/version and uncertainty. Address confounding and multiple comparisons before generating confident claims. Present association rather than causation; an LLM may explain a computed result but must not generate the underlying statistic.

Begin with deterministic calculations in the Python backend. The deck's scikit-learn proposal does not require installing ML tooling before a concrete algorithm warrants it. Compute trends from canonical observations first; add versioned snapshots only if needed for caching or reproducible evidence.

## 16. Multilingual/Voice Analysis

English reference copy, a Hindi selector, and fixed Hinglish dialogue exist in the designs. No working English/Hindi/Hinglish interaction, i18n library, other-language support, speech recognition, recording, speech synthesis or audio permissions exist.

Use locale keys from the frontend foundation, then add complete English/Hindi translations and locale-aware date/number formatting. Keep UI locale, preferred response language and original report language separate. Preserve original values/units/source text; translations must not overwrite source records. Evaluate Hindi and Hinglish answers for preserved numbers, units, uncertainty, evidence and health-information scope.

Future voice flow:

```text
Explicit microphone action -> consent/permission -> audio capture
  -> selected speech-to-text adapter -> editable transcript
  -> existing authorized assistant API -> response text
  -> optional selected text-to-speech adapter -> playback controls
```

Provider/browser API selection remains open. Evaluate language accuracy, browser coverage, network behavior, retention, cancellation, costs and accessibility later. Avoid retaining raw recordings by default. Voice must reuse the same authorization/context controls and always provide a text fallback.

## 17. Security & Privacy Findings

**Observed findings:** no confirmed exploitable vulnerability or exposed application credential. With no source/history/configuration, authentication, authorization, IDOR, secrets committed to Git, RLS, XSS, CSRF, SQL injection, upload security, redirects, logging and provider privacy cannot be audited as implemented controls. External account permissions are UNKNOWN.

The table below is a **prospective release-risk register**. Severities apply if the described condition exists in a future implementation; they are not claims of current exploitable defects.

| Severity | Conditional risk | Required control and verification |
|---|---|---|
| CRITICAL | Cross-user reports, files, metrics, messages or exports accessible | Verified server identity; ownership on all paths; two-user + anonymous tests, including nested IDs and jobs |
| CRITICAL | Live service/database keys in source or browser bundle | Server-only secrets, ignored local env, secret/build/history scans; revoke/rotate any actual exposure |
| HIGH | Public report/export storage or unchecked download access | Private objects; authorize each access; scoped short-lived delivery where used |
| HIGH | Spoofed, oversized, malformed or resource-exhausting uploads | Layered server validation, quarantine, bounded parsers/jobs, page/pixel/time limits |
| HIGH | Prompt injection expands data/tool access | Untrusted-source boundaries; typed tools; owner-scoped retrieval; output/evidence validation |
| HIGH | Fabricated values/ranges, unsupported diagnoses or correlations | Source preservation, uncertainty review, deterministic calculations and grounded explanations |
| HIGH | Session theft/CSRF/XSS/SQL injection | Established session design, mutation defenses, safe text rendering/links, parameterized queries |
| HIGH | Health data/secrets leak through logs, telemetry, browser caches or providers | Minimized context, redaction, controlled retention, provider handling review, private cache policy |
| MEDIUM | Cost/availability abuse through AI/OCR/jobs | Per-user quotas/rate limits, concurrency limits, timeouts and bounded idempotent retries |
| MEDIUM | Deleted/corrected data persists in derived outputs unexpectedly | Defined deletion/retention/invalidation behavior including queued jobs, exports and backups |
| LOW | UI labels falsely imply working integrations | Truthful empty/unavailable/status copy backed by execution |

Controls should follow deny-by-default authorization and ownership checks on every request. [OWASP Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html). Upload type/content validation and nonpublic storage require multiple checks rather than trusting browser MIME or extension alone. [OWASP File Upload](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html). Logging must exclude sensitive payloads and credentials. [OWASP Logging](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html).

Additional acceptance cases: expired/revoked sessions; logout; open-redirect attempts; strict origin/CORS configuration; malicious report names and Markdown links/images; swapped owner/parent IDs; unauthorized storage paths; SQL-shaped inputs; interrupted/deleted jobs; retries after provider outages; source corrections; credential rotation; data restoration and deletion. Error telemetry must not include report bodies or complete prompts.

Community aggregation/anonymization is outside the initial scope. The deck's use of the word anonymization is not evidence of privacy protection. No legal/regulatory compliance certification is claimed by this technical plan.

## 18. Code Quality Findings

No components, functions, imports, type annotations, abstractions or client/server boundaries exist. Duplicate/dead code, large components, `any`, unused imports, performance problems and test coverage cannot be assessed from screenshots.

The actionable foundation gap is reproducibility: establish manifests/lockfiles, supported runtimes, TypeScript strictness, Python typing/validation, linting, meaningful tests, API contracts, env documentation and CI before product features grow.

Recommended boundaries: UI components do not call AI/OCR directly; API routes call domain services; domain calculations are testable without network services; persistence/provider adapters enforce explicit contracts; processing state is separate from visual progress. Do not create generic abstraction frameworks or install optional dependencies without a demonstrated use.

## 19. Build/Test Status

| Check | Result |
|---|---|
| Root inventory including hidden entries | Completed successfully: zero initial entries |
| Git status/tracked files | Failed because no Git repository exists; not an application build error |
| Manifest/lock/config/source discovery | None present |
| Reference inspection | Eight-slide deck and four screenshots inspected; native Keynote rendering not performed |
| Install | Not run; no manifest or selected versions |
| Development server | Not run; no executable application |
| Production build | NOT RUN / unavailable; no build script |
| Lint/typecheck | NOT RUN / unavailable; no code/config |
| Unit/integration/E2E tests | NOT RUN / unavailable; no test suite |
| Coverage | Unavailable, not a measured 0% result |
| Database setup/migrations | Not run; no schema, database config or tooling |

There are no correct current install/dev/build/lint/typecheck/test/migration commands to report. Commands such as `npm run build` would currently be invented rather than project-defined. Phase 1 will establish and document frontend/backend commands and lockfiles; migration commands follow the selected database tooling in Phase 2. No dependency installation, application process, migration, destructive operation or deployment was performed during analysis.

## 20. Manual Setup Required From Me

No external setup is required to read these documents or begin a local foundation phase. No provider account is assumed to exist. Values below are **proposed configuration names**, not variables currently read by an application. Exact names will be finalized for each selected integration, with blank examples and startup validation.

| Requirement | Why / when | What the owner creates or decides | Value eventually configured | Proposed env destination |
|---|---|---|---|---|
| Stack confirmation | Before Phase 1 scaffolding | Confirm deck-based stack or discuss changes | Decision only | No secret/env |
| Database project | Durable owned history; Phase 2 | If approved, Supabase project/region and isolated development environment | Database connection URL, project URL | Backend `DATABASE_URL`, `SUPABASE_URL` |
| Identity configuration | Real accounts; Phase 2 | Selected auth setup, redirect URLs and recovery/verification policy | Provider public config and server session configuration | Backend `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` if chosen; `AUTH_SESSION_SECRET` only if integration requires it |
| Private object storage | Reports; Phase 3 | Approved private bucket and access policies | Bucket name; backend storage credentials if needed | Backend `REPORTS_BUCKET`; `SUPABASE_SECRET_KEY` only if needed for privileged worker/server tasks |
| Worker execution | Durable processing; Phase 3 locally, production later | Approve worker hosting; queue service only if needed | Deployment/runtime configuration | `DATABASE_URL`; `QUEUE_URL` only if an external queue is selected |
| OCR/PDF integration | Real scanned/image extraction; Phase 4 | Select local library or external provider after evaluation; external account only if required | Provider identifier/key/region or model files as appropriate | Backend/worker `OCR_PROVIDER`, `OCR_API_KEY`, `OCR_REGION` only where applicable |
| LLM provider/model | Explanations; Phase 7, or Phase 5 if extraction needs it | Select provider/model, budget and health-data handling; create API project/key | Provider key and model identifier | Backend `AI_PROVIDER`, `AI_MODEL`, `AI_API_KEY`; adapt to selected SDK |
| Email delivery | Verification/recovery when required; Phase 2 or before public release | Configure selected transactional email/SMTP service and sender domain if auth provider needs it | SMTP/provider config; sender identity | Backend `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM`, only if applicable |
| Speech services | Optional voice; Phase 12 | Choose browser/local/external STT/TTS; provider accounts only if needed | Provider/model/voice config and any keys | Backend `STT_PROVIDER`, `STT_API_KEY`, `TTS_PROVIDER`, `TTS_API_KEY` as applicable |
| Hosting | Staging at the start of Phase 13; production in Phase 14 | If approved, Vercel frontend and Render API/worker; confirm runtime limits and budget | Deployment URLs and environment configuration | Frontend public `VITE_API_BASE_URL`; backend `APP_ORIGIN`, `API_PUBLIC_URL`, `ALLOWED_ORIGINS` |
| Domain/DNS | Stable app/API origins; Phase 14 | Optional domain and DNS records, authenticated callback origins | Public domain/URLs | Public URL/origin variables above |
| Retention/consent/operations | Before real health data or public release | Decide supported users, processing consent, retention, deletion, provider use, backup and incident ownership | Written settings/policies | Versioned configuration; no invented credential |
| Git repository | Owner-managed later | Create remote and push manually | Remote URL if relevant later | Git configuration, no application env |

Do not configure both alternatives indiscriminately. No `.env.example` has been fabricated in this phase because no executable configuration contract exists. Phase 1 will add it with names and blank values only, plus ignore rules. Secret values belong in ignored local environment files or the hosting secret store; no secret belongs in source, documentation, browser variables, or chat messages.

Any `VITE_` configuration is intended for the client and must be public information. Database, AI, OCR, session and privileged storage credentials remain server-side. Supabase service credentials can bypass storage access controls, so a privileged key is not a substitute for ownership enforcement. [Supabase Storage access control](https://supabase.com/docs/guides/storage/security/access-control).

At each external-integration gate I will give exact setup steps for the chosen service, pause dependent work, and wait for your confirmation. There is no request to create those accounts now.

## 21. Current vs Target Gap Analysis

| Area | Current state | Target state |
|---|---|---|
| Architecture | Empty workspace + references | Defined frontend/API/worker boundaries and contracts |
| Frontend | Screenshots/slide shapes | Accessible responsive working routes and actual state |
| Backend | None | Authenticated validated API and durable processing |
| Database | None configured | Versioned schema, provenance, ownership, indexes, retention |
| Authentication | None | Verified identities, safe sessions, recovery and authorization |
| Reports | Illustrated table/history | Private upload, processing/review, real history and summaries |
| OCR | Label only | Evaluated PDF/image extraction with failure handling |
| AI | Fixed reference dialogue/copy | Selected provider, bounded grounded generation and evidence |
| Trends | Illustrative curves | Real dated observations and deterministic comparisons |
| Voice | Icons/claims only | Consented transcription/playback with text fallback |
| Multilingual | Reference copy/options | English/Hindi UI and evaluated Hindi/Hinglish responses |
| Security | No implementation to assess | Verified user isolation, private storage, input/AI controls |
| Testing | None | Unit, integration, E2E, isolation and AI evaluation gates |
| Deployment | Deck proposal only | Configured staging/prod, monitoring, backups and rollback |

## 22. Recommended Final Architecture

Use the deck's technology proposal as the **candidate**, subject to confirmation before implementation:

- React + TypeScript, Vite and Tailwind for the frontend. Vite supports a React/TypeScript starting point and production static assets. [Vite guide](https://vite.dev/guide/).
- FastAPI/Python for the authenticated API and reusable domain services; Python worker for extraction and longer jobs.
- Supabase PostgreSQL and private Storage if approved. Evaluate Supabase Auth for a coherent identity solution, with a deliberately designed session boundary.
- Provider-specific OCR and AI adapters selected only after accuracy, data handling, operational and cost evaluation. No model/provider decision is made here.
- Deterministic range/trend calculations before ML. No initial requirement for scikit-learn, embeddings, a vector database, Redis, or microservices.
- Vercel/Render as the hosting candidates named in the deck. Validate cookie/origin routing, upload limits and worker support before production configuration.

```text
Browser: React + TypeScript + Vite + Tailwind [proposed]
   |
   | HTTPS; public configuration only
   v
FastAPI: established session integration + schema validation
   |
   +--> Authorization / domain services / typed data access
   |       +--> PostgreSQL: owned facts, history, jobs, conversations
   |       +--> Private Storage: original reports and expiring exports
   |
   +--> Durable job worker
   |       +--> PDF/OCR adapter -> source-preserving candidates
   |       +--> Validation/review -> canonical observations
   |
   +--> Deterministic reference and trend services
   |
   +--> Authorized evidence selection -> AI adapter -> validated output

Locale handling surrounds UI + explanations
Optional voice surrounds the same assistant API
Audit/quotas/retention/monitoring apply across boundaries
```

Prefer a same-origin API surface where practical to simplify browser session handling. If origins differ, explicitly configure credentials, CORS, CSRF and cookie behavior. Select one primary database query path and prove how end-user identity reaches RLS; privileged worker paths need additional explicit scope enforcement.

Proposed future layout, with no directories below created yet:

```text
frontend/
  src/app/                 routing and application shell
  src/components/          reusable accessible UI
  src/features/            auth, dashboard, reports, trends, assistant
  src/lib/                 API/config/error utilities
  src/locales/              en/hi resources
backend/
  app/api/                  routes and request/response models
  app/core/                 settings, session/security, safe errors
  app/domain/               report/metric/trend rules
  app/services/             orchestration
  app/repositories/         scoped persistence
  app/integrations/         storage, OCR, AI, optional voice
  app/workers/              durable processing
  tests/
database/migrations/        authoritative schema/policy changes
tests/e2e/                  full user flows and isolation
docs/                       decisions, setup, operations and evaluation
```

This is not a framework replacement: no current framework exists. The cost is creating and operating a frontend plus Python backend/worker, including API contracts and deployment configuration. That complexity is justified by the deck's Python processing direction, but should be confirmed in Phase 1. Do not silently switch to Next.js, Firebase, a different database or a selected OCR/LLM vendor.

## 23. Phased Implementation Roadmap

Phase 0 is this analysis and documentation. It installs nothing and implements no application. Every phase below ends with a summary, manual test steps, actual validation results, a secret check, a suggested commit message, and a stop until you say `continue`. Security, provenance and meaningful tests are part of each phase, not postponed to a final audit.

All paths below are proposed paths under the workspace, not existing files. Database/API work means only what the named phase adds. Each external setup gate requires your confirmed setup before dependent work continues.

### Phase 1 — Establish the local foundation

- **Goal:** Confirm the deck-based stack, create reproducible frontend/backend foundations and truthful empty navigation pages.
- **Files likely affected:** Root/frontend manifests and lockfiles, `frontend/src/app`, styles/locales, `backend/pyproject.toml`, backend entry point/config, `.gitignore`, blank `.env.example`, tests, CI configuration and README.
- **Database changes:** None; no provider/project required.
- **API changes:** Real health/readiness contract for the local service; no fake health-data endpoints.
- **External services:** None. Approve framework/tooling choices before installation.
- **Dependencies:** This analysis and the owner's `continue` instruction.
- **Testing criteria:** Documented clean install, dev startup, frontend build/lint/strict typecheck, backend lint/type checks, health-endpoint test, navigation smoke and basic mobile/keyboard checks.
- **Definition of done:** Reproducible local app with honest unavailable features, pinned dependencies and safe config; no sample personal health records or provider integrations presented as working.

### Phase 2 — Identity and core ownership schema

- **Goal:** Real user accounts and enforceable user isolation before storing health data.
- **Files likely affected:** Auth UI, backend security/session/repositories, settings models, `database/migrations`, env template, integration tests and setup docs.
- **Database changes:** Identity mapping, profiles/settings, ownership conventions and initial policies.
- **API changes:** Selected provider's sign-in/out/session/recovery integration; protected profile/settings operations.
- **External services:** Approved database/auth project; email configuration if required. Stop for setup.
- **Dependencies:** Phase 1.
- **Testing criteria:** Two users + anonymous access, expired/revoked sessions, submitted `userId`, cookie/CSRF behavior, logout/recovery, policy tests and idempotent profile creation.
- **Definition of done:** Server derives identity and unauthorized access fails at API and applicable database boundaries.

### Phase 3 — Private report upload and durable processing lifecycle

- **Goal:** Store actual PDF/JPG/PNG reports privately with validated files and truthful status.
- **Files likely affected:** Reports/consent UI, upload/file routes, storage integration, worker/job service, minimum retention/deletion service, migrations and upload/privacy tests.
- **Database changes:** Reports, report files, processing runs/jobs, consent/policy-version metadata, deletion state and owner-consistent constraints.
- **API changes:** Upload reservation/transfer finalization, list/detail, authorized download, delete and job status/retry contracts.
- **External services:** Approved private storage; local worker initially, external queue only if justified. Stop for needed setup.
- **Dependencies:** Phase 2; approved processing consent and minimum retention/deletion policy before accepting real health data.
- **Testing criteria:** Real valid files, MIME/signature spoofing, size/page/pixel limits, unauthorized IDs/paths, interrupted upload, duplicate finalize, restart/retry, orphan cleanup, consent handling, file/metadata deletion, deletion during processing and queued-job cancellation.
- **Definition of done:** Owned uploads persist and remain private; minimum consent, retention and deletion behavior works before real health data is accepted; unsupported/failed processing never reports OCR success. Each later phase extends deletion and invalidation to its new derived records.

### Phase 4 — Evaluate and integrate PDF text extraction/OCR

- **Goal:** Extract traceable text from supported typed/scanned reports and images.
- **Files likely affected:** OCR/PDF adapters, worker stages, report progress/review UI, fixtures and provider setup docs.
- **Database changes:** Page/text provenance, extraction metadata/version and safe failure states.
- **API changes:** Extraction status/result access and controlled retry.
- **External services:** Provider/library chosen together using evaluation results. External account/key only if needed; stop for setup.
- **Dependencies:** Phase 3.
- **Testing criteria:** Typed/scanned/mixed PDFs, rotated/low-quality images, table layouts, Hindi/English text, corrupt/encrypted files, timeouts and provenance preservation against reviewed fixtures.
- **Definition of done:** Measured extraction behavior with documented supported inputs and review/failure paths; no fabricated text.

### Phase 5 — Structured parameters, reference ranges and review

- **Goal:** Convert extracted candidates into trustworthy health observations.
- **Files likely affected:** Domain schemas/parser/mappings, review UI, parameter/observation routes, migrations and correctness fixtures.
- **Database changes:** Parameters/revisions, metric definitions/mappings, observations, source links and range fields.
- **API changes:** Get/review/correct parameter candidates; record validated observations.
- **External services:** None necessarily; selected AI configuration only if extraction evaluation justifies its use. Stop if needed.
- **Dependencies:** Phase 4.
- **Testing criteria:** Exact values/units, decimals, comparators, qualitative results, dates, source ranges, missing/ambiguous fields, incompatible conversions, corrections and duplicate retries.
- **Definition of done:** Original evidence survives normalization; only validated observations enter history/trends; missing ranges remain unknown.

### Phase 6 — Real history, metric entry and dashboard

- **Goal:** Browse actual reports and dated health data; support defined manual metrics for sleep/activity/weight/heart rate and other approved inputs.
- **Files likely affected:** Dashboard/history/metric forms, observation services/routes, migrations and E2E tests.
- **Database changes:** Manual-source metadata, quality/context fields and owner/date/metric indexes as needed.
- **API changes:** Paginated history, measurement CRUD with provenance, dashboard aggregates.
- **External services:** Existing database only; no assumed wearables connection.
- **Dependencies:** Phase 5; Phase 2 ownership rules.
- **Testing criteria:** Multiple reports/dates/units, sparse/empty history, timezone boundaries, corrections/deletion, manual versus extracted source labeling and user isolation.
- **Definition of done:** Dashboard and history derive every personalized value from owned records; no reference values appear as user data.

### Phase 7 — Grounded report explanations

- **Goal:** Generate understandable educational explanations from validated facts and source ranges.
- **Files likely affected:** AI adapter, versioned prompts/schemas, insight/evidence service, report summary UI and safety evaluation fixtures.
- **Database changes:** Insights, evidence links, generation/input versions and stale/failed state.
- **API changes:** Authorized generate/read explanation operations with quota/status handling.
- **External services:** Selected LLM provider/model and approved data handling; stop for setup if not already configured.
- **Dependencies:** Phase 5, with Phase 6 navigation/history available.
- **Testing criteria:** Known/missing/uncertain parameters, evidence ID checks, no invented values/ranges, unsafe instructions, unsupported diagnosis requests, provider failure and source correction invalidation.
- **Definition of done:** Explanations have traceable evidence and distinguish facts, calculations and AI narrative; unavailable provider remains an honest failure state.

### Phase 8 — Deterministic trends and supported pattern/correlation insights

- **Goal:** Real 7/30-day views, previous-period comparisons and evidence-backed patterns.
- **Files likely affected:** Trend domain/service/API, charts/tables, metric filters and algorithm tests.
- **Database changes:** Indexes; optional versioned snapshots only if needed.
- **API changes:** Metric/window trend response with points, statistics, counts, missingness, method and evidence; correlation results only when supported.
- **External services:** None for calculations; reuse approved AI only for optional explanation.
- **Dependencies:** Phase 6; Phase 7 for generated narrative.
- **Testing criteria:** Boundary dates, current/prior sparse periods, zero baselines, duplicate/incompatible readings, irregular lab sampling, constant series, known increasing/decreasing cases, inadequate paired correlation data and corrections.
- **Definition of done:** Charts use actual observations; deterministic output is reproducible; insufficient evidence suppresses unsupported classifications and correlation claims.

### Phase 9 — Context-aware health assistant

- **Goal:** Answer questions about latest reports, changes, metrics and prior conversation using controlled user context.
- **Files likely affected:** Assistant UI, conversations/messages routes, retrieval/tool schemas, prompts, token budgeting, migrations and adversarial tests.
- **Database changes:** Conversations, messages, evidence/context versions and generation status.
- **API changes:** Conversation list/create/detail/delete and message submission/response contracts; no unrestricted SQL or arbitrary retrieval tool.
- **External services:** Approved LLM integration already configured.
- **Dependencies:** Phases 7 and 8 plus verified authorization.
- **Testing criteria:** The user's example questions, explicit/latest-report selection, missing history, bounded context, source citations, cross-user IDs, hostile report/message instructions, cancellation/outages and duplicate submissions.
- **Definition of done:** Responses use authorized report/metric/trend facts, retain evidence and conversation history, and remain within educational scope.

### Phase 10 — Complete English/Hindi and Hinglish behavior

- **Goal:** Full English/Hindi interface and reliable language-aware explanations/chat.
- **Files likely affected:** Locale resources, settings UI/API, formatting utilities, language prompts and multilingual evaluation fixtures.
- **Database changes:** Language preferences if additional fields are needed; original report language remains distinct.
- **API changes:** Validated locale/response-language options without changing ownership.
- **External services:** Existing AI provider must meet language quality needs; no translation provider assumed.
- **Dependencies:** Phase 9; locale-ready foundation from Phase 1.
- **Testing criteria:** Hindi/Hinglish questions, preserved numbers/units/evidence, language switching, mixed-language reports, long translations, fonts and keyboard/mobile access.
- **Definition of done:** Supported workflows function in both initial languages; other languages are not labeled supported without evaluation.

### Phase 11 — Export, settings and in-app notifications

- **Goal:** Export authorized records with provenance and deliver genuine processing notifications.
- **Files likely affected:** Export jobs/templates/download routes, settings/notification UI, retention service, migrations and export tests.
- **Database changes:** Export jobs/artifact expiry, notification state/preferences and retention metadata.
- **API changes:** Export request/status/download and notification read/settings operations.
- **External services:** Existing private storage; external email/push only by separate approved requirement.
- **Dependencies:** Phases 6–10 for the exported content.
- **Testing criteria:** Report/trend scope, ownership during generation/download, bilingual fonts, exact values/source labels, artifact expiry/deletion, duplicate notifications and failure states.
- **Definition of done:** Exported files faithfully reflect owned records and explanations; notifications come from actual events.

### Phase 12 — Optional voice input/output

- **Goal:** Add consented voice as an adapter around the existing assistant.
- **Files likely affected:** Audio controls, transcription/synthesis adapters/routes, language preferences and browser/voice tests.
- **Database changes:** Optional voice preferences; no default raw audio retention.
- **API changes:** Bounded transcription/synthesis operations only if server services are selected.
- **External services:** Choose STT/TTS or browser capability after evaluation; stop for external setup if required.
- **Dependencies:** Phase 10 and stable assistant behavior.
- **Testing criteria:** English/Hindi/Hinglish transcription, transcript correction, denied permission, cancellation, unsupported browser, latency, quota and privacy behavior.
- **Definition of done:** Text fallback always works; voice claims reflect verified supported capabilities. May remain a later release by owner decision.

### Phase 13 — Production readiness and independent security verification

- **Goal:** Configure and deploy staging first, then validate the assembled system, resolve defects and document operations.
- **Files likely affected:** Staging hosting/worker configuration, relevant source fixes, security/E2E/load tests, CI, redaction/monitoring, retention and operational runbooks.
- **Database changes:** Measured index/policy fixes through reviewed migrations; backup/restore and retention configuration.
- **API changes:** Fix verified validation/auth/rate-limit gaps; keep contracts compatible where possible.
- **External services:** Provision approved staging hosting, database/storage/auth and provider configuration at this phase's start; add backup and monitoring configuration. Stop for owner setup before staging deployment and dependent tests.
- **Dependencies:** Implemented release scope from prior phases; optional voice may be excluded explicitly.
- **Testing criteria:** Full two-user isolation matrix, secret/build checks, provider failures, restart/retry, deletion/invalidation, restore, accessibility, representative load and AI safety evaluations.
- **Definition of done:** Required suites pass with evidence; no unresolved critical/high release risks; recovery/incident procedures and limitations documented.

### Phase 14 — Production deployment

- **Goal:** Promote the staging-verified release to production with owned configuration, monitoring and rollback.
- **Files likely affected:** Hosting/worker configuration, deployment workflow, env documentation, health checks and deployment runbook.
- **Database changes:** Apply reviewed production migrations with backup/rollback planning; no destructive reset.
- **API changes:** Production origins/session/callback settings and health/readiness endpoints; no unreviewed feature expansion.
- **External services:** Owner-configured hosting/database/storage/auth/AI/OCR, optional domain/DNS; stop for exact setup and required deployment confirmation.
- **Dependencies:** Phase 13 and successful staging verification.
- **Testing criteria:** Reconfirm the approved staging release, then production smoke, login, real private upload/extraction, evidence-based report/trend/chat, isolation, cookies/CORS, provider failures, backup and rollback rehearsal.
- **Definition of done:** Working deployed scope with confirmed operations, secrets outside source, documented URLs and reproducible deployment. Then stop.

## 24. Phase 1 Proposal

**Proposed next work: create the local engineering foundation only.** There is no existing application to stabilize or rewrite. The candidate stack comes from the supplied deck: React/TypeScript + Vite + Tailwind frontend and FastAPI/Python backend.

Your `continue` instruction accepting this proposal is sufficient confirmation of the local foundation choices; external provider choices and account setup remain separate gates. Then define exact compatible versions and minimal tooling, create manifests/lockfiles and commands, implement a real local health endpoint, establish the four navigation destinations with honest empty/unavailable states, and add strict configuration and validation conventions. Do not add sample health measurements, a fake login, fake OCR/AI responses, placeholder success APIs, or cloud integrations.

Expected changes: the Phase 1 file groups listed above, plus updates to these documents. Database/API impact: no database; only a local service health contract. External setup: none for this phase. Git hosting can wait and will remain owner-managed.

Validation will include install/start/build/lint/type checks, the real health endpoint, navigation, responsive/keyboard checks, and verification that no secrets or invented user health values are present. The implementation summary will include exact commands and manual test steps after they exist.

Suggested future Phase 1 commit message: `chore: establish SwasthyaLens frontend and API foundations`.

No Phase 1 implementation has started. Continue only when the owner says `continue`; stop again after Phase 1 verification and handoff.

READY FOR PHASE 1
