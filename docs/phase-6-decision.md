# Phase 6 observation decision

Recorded before implementation against clean Phase 5 commit `71f5373`.
Baseline: frontend lint/typecheck, 167 tests and build; backend Ruff/format/mypy,
251 tests (five opt-in live tests skipped), real local OCR evaluation; all eight
database verification scripts; all five live suites passed (475.49 seconds).

## Trust and publication

Publication is an explicit user action on the latest Phase 5 `confirmed` or
`corrected` revision, with a nonblank raw value. Unreviewed and rejected candidates
cannot publish. Unparsed, qualitative, ordinal, interval and titre values remain
faithful text; being in personal history does not make them numeric or clinically
validated. Unknown metric identities remain unknown.

The browser sends candidate/report identifiers for lookup, expected review revision
and an optional user-confirmed measurement date. The database locks the owned report,
derives the review, fields and evidence from stored records, and checks the latest
revision. No browser-supplied owner, value, unit or provenance is authoritative.
Candidate/review is the natural publication idempotency key. A replay with the same
date returns the existing snapshot; conflicting dates or stale reviews fail.

Each candidate has one observation identity with immutable value/date revisions.
Only lifecycle status may change. A new Phase 5 review atomically changes any active
snapshot to `superseded`, or `invalidated` on rejection. The new review requires
explicit publication before becoming active. No implicit propagation of newly
edited health values. At most one active revision exists per identity. Reprocessing
the identical page/span of the same text attempt cannot create another observation
identity. Different source text attempts are not medically deduplicated; users must
inspect provenance. Report deletion cascades through candidates and observations.

## Dates, ordering and units

Phase 5 extracts no reliable medical date. Report observations therefore have a null
measurement date unless the user explicitly supplies a calendar day (1900–2100).
Day precision is preserved; no midnight measurement timestamp is fabricated.
Manual entries require an ISO timestamp with an offset, normalized to UTC. Their
forms explicitly request UTC. Upload, publication and revision timestamps are
separate system times. Date filters use supplied report days or UTC manual days;
unknown dates are excluded by a date filter. Known measurement days sort descending;
within a day, known manual instants sort descending before day-only records,
then system creation time and identity provide deterministic ties. Unknown dates appear
last, ordered by recorded time, explicitly labeled unknown. No latest-metric card
is included because uncertain precision and units do not justify one.

The small `observations-v1` catalog retains Phase 5's five canonical identities and
adds weight and heart rate. Unspecified glucose/vitamin D identities remain
unspecified. It is not an ontology. Exact original units, decimals, comparators,
qualitative text and reference text survive unchanged. No conversions, clinical
ranges, classifications, aggregation by metric, or comparison engine is added.
Future calculations must independently establish compatible identity, units,
value type, comparator, date precision and clinical context.

## Manual scope and lifecycle

Only weight in `kg` (positive decimal, up to three fractional places) and heart
rate in `bpm` (positive integer) are accepted, each below 10000 as a technical size
bound, not a clinical reference range. Strings preserve exact decimal spelling.
An explicit offset timestamp within 1900–2100 is required. Owner identity always
comes from the authenticated session. Edits append revisions with expected-revision
checks and request idempotency keys, capped at 100 revisions. Deletion erases all
value/date revisions; an opaque owner/id/request-key deletion tombstone prevents
creation retries resurrecting deleted data. Manual identities, including tombstones,
are capped at 1000 per account for this development implementation.

## Access and presentation

Two RLS-protected tables hold observation identities and revisions. Public invoker
RPCs call narrowly scoped private functions requiring the existing processing secret
and active owner JWT. Authenticated direct table access is SELECT only. The BFF
also verifies returned ownership and requested resource identity. Writes retain
Origin/JSON/CSRF requirements. No new credential, provider or setup is needed.

History provides bounded 20-row pages and validated metric/source/date/report
filters, active-only by default with an option to inspect inactive records. Offset
pagination is deterministic for a stable dataset; concurrent changes can shift pages,
so refresh restarts browsing. Details expose retained revisions and source page/quote,
with an authorized source download. Dashboard shows real owned report, reviewed
candidate and active observation counts, plus bounded recent records. Loading,
errors and empty states are explicit. No fixtures populate normal accounts.

Current Supabase changelog and function/RLS documentation were checked. Recent
breaking changes concern unused services or the already documented email-template
limitation. No service configuration changes are required. References:
[RLS](https://supabase.com/docs/guides/database/postgres/row-level-security),
[functions](https://supabase.com/docs/guides/database/functions),
[changelog](https://supabase.com/changelog).
