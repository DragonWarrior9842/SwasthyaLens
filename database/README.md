# Database foundation, private reports and health observations

This directory owns the versioned Supabase PostgreSQL schema and its verification SQL. Phase 2 defines accounts; Phase 3 adds owned report metadata and a private Storage bucket; later migrations add source-preserving extraction, review and explicitly published personal observations. Files contain schema and synthetic verification fixtures, never credentials or real medical measurements. The initial migration does not modify provider-owned `auth.users` or `auth.sessions` data.

**Execution status (14 September 2026):** applied to the verified `swasthyalens-dev` project through the connected Supabase migration tool, version `20260914164833`, name `auth_foundation`. Both `schema.sql` and the complete rollback-only `rls-isolation.sql` passed on hosted PostgreSQL 17.6. No fixture users/profile/settings rows remained afterward. Supabase security and performance advisors both returned no findings. These database results do not replace live browser/API authentication acceptance.

**Phase 2 acceptance update (15 September 2026):** the real two-user FastAPI/Data API suite and production-build browser checks passed. Private-schema exposure was explicitly rejected with HTTP 406 / `PGRST106`. The security advisor reports leaked-password protection disabled; there are no table/RLS/function findings. The performance advisor remains clear. The owner confirmed that the Free/default-sender email template is locked; actual signup-email delivery and OTP-code verification remain a known Phase 2 limitation. The two Auto Confirm fixtures do not verify that flow. See the [Phase 2 handoff](../docs/phase-2-handoff.md) for details. Phase 3 was subsequently authorized separately, as recorded below.

## Phase 3 application and verification

The separately authorized Phase 3 migration was applied to the same verified development project as **20260915150720 / reports_foundation**. Its source is `migrations/20260915150720_reports_foundation.sql`. Supabase CLI 2.117.0 generated the initial filename locally; the file was renamed to the migration service's recorded timestamp without changing SQL, so repository and hosted migration history agree. The downloaded CLI was checksum-verified and kept in ignored workspace cache; no application dependency was added.

The migration creates one `public.reports` manifest table, the private `reports` bucket (5 MiB, PDF/JPEG/PNG), owner/active-session RLS, narrow lifecycle RPCs and operation-aware Storage policies. Authenticated callers can SELECT their own manifests but cannot directly INSERT/UPDATE/DELETE them. The RPCs accept no owner ID and preserve immutable generated paths. Private security-definer lifecycle functions are intentional: they enforce state transitions while public wrappers remain security-invoker. Every private entry point checks the active JWT owner. No service-role runtime client is used.

`reports.user_id` references `auth.users(id)` with RESTRICT: account deletion must first discharge file-cleanup obligations. Deleted rows retain opaque owner/report/path/idempotency metadata and timestamps; filename/type/size/hash/leases are scrubbed. There is no hard-delete API or production manifest-retention policy yet. The detailed contract is in [the Phase 3 handoff](../docs/phase-3-handoff.md).

For a **fresh** project, apply all migration files in order through the migration tooling. The report migration fails if a conflicting bucket or existing Storage policies need review; never bypass that guard or make the bucket public. Official Supabase bucket-creation SQL is used only for bucket setup. Actual object writes/deletes always use Storage's API; never delete `storage.objects` rows to remove files.

## Phase 4 extraction

The same development project has migrations `20260916153700_report_text_extraction.sql` and `20260916160036_processing_attempt_configuration.sql`. Supabase CLI generated their initial filenames; they were renamed to the migration service's recorded timestamps with SQL unchanged.

`report_processing_runs` retains source hash, attempts, lifecycle timestamps, processor/configuration and failures. `report_pages` holds ordered page text and provenance. Both have forced RLS deriving ownership through `reports`, with active-session checks and authenticated SELECT only. Private lifecycle functions require both the owner JWT and a server processing secret; its SHA-256 hash is stored in the unexposed private schema. Public wrappers are security-invoker. The configured request wrapper retains planned processor/configuration before work begins, including failed/interrupted runs. No service-role runtime access is added.

The report's `deleting` transition physically deletes runs and cascades pages in the same transaction. Completion also locks and rechecks the report, fencing late worker writes. Existing successful attempts survive later failures until the report is deleted. Restart recovery expires unacknowledged attempts after 180 seconds on an authenticated history/request call; it is not an unattended durable queue.

Run `verification/extraction-schema.sql` and the complete rollback-only `verification/extraction-lifecycle.sql`, as well as the four prior scripts. Provisioning the private processing-key hash is separate operator configuration, not hidden DDL. See [Phase 4 setup and verification](../docs/phase-4-handoff.md) for exact setup, tests, resource limits and retention boundaries.

Run these complete scripts after application:

1. `verification/schema.sql` — read-only Phase 2 assertions.
2. `verification/rls-isolation.sql` — rollback-only Phase 2 role/session fixtures.
3. `verification/reports-schema.sql` — read-only report grants, constraints, bucket and function assertions.
4. `verification/reports-rls-isolation.sql` — rollback-only report ownership, idempotency, lease, cancellation, cleanup, revocation and privilege assertions.

All four passed against hosted PostgreSQL on 16 September 2026. Real Storage HTTP authorization is tested separately by `backend/tests/integration/test_live_reports.py`; SQL fixtures do not simulate successful object uploads. Direct Storage read assertions use a fresh `cacheNonce` to test current origin/RLS permission, because a previously authorized CDN response may outlive an origin deletion. Backend downloads use the same documented cache bypass and never disclose the URL.

## Apply the initial migration

1. Open the **development** Supabase project selected for SwasthyaLens. Check the project name before opening SQL Editor.
2. In API settings, retain the public application schema as an exposed schema. Do **not** expose `auth` or `swasthyalens_private`.
3. For a new, unapplied database, open `migrations/20260914164833_auth_foundation.sql` locally. Create a new query in Supabase SQL Editor, using the project's database-owner role (`postgres`). Paste the **entire file**, including `begin` and `commit`, and run it once. Do not rerun it on the current development project; its migration is already applied.
4. If any statement fails, the transaction must not be committed. Run `rollback;` if the editor connection remains in an aborted transaction. Return the error's code and object name for review, without credentials. Do not fix errors by disabling RLS, broadening grants, deleting existing objects or skipping statements.
5. Run the entire `verification/schema.sql` file. It performs read-only assertions and returns columns, constraints, policies and grants for review. The final result should say `Phase 2 schema assertions passed; review the result sets and API exposure settings.`
6. In this development project, run the entire `verification/rls-isolation.sql` file. Read the testing boundaries below first. Its final result should say `Phase 2 database isolation assertions passed; all test fixtures are rolled back next.` The last statement is deliberately `rollback`.
7. Confirm migration application and both verification results to the implementation agent. Keep any SQL error details free of credentials. Then the agent can run authenticated API/Data API checks with separately authorized test accounts.

The publishable key cannot execute arbitrary migration SQL. The application does not need a database password or service-role key. Administrative SQL is an owner setup step, separate from the user-scoped runtime connection.

## Replay and change control

Apply migration files in filename order **once per database**. This first migration intentionally uses `create`, not `create if not exists`: an unexpected existing object must fail instead of silently hiding schema drift. Do not rerun it over an existing installation or reset a database to make it pass. A fresh local Supabase PostgreSQL instance can replay the same files after its normal `auth` schema and roles exist; a generic empty PostgreSQL instance is insufficient.

If a PostgreSQL client is already installed, use its existing secure connection mechanism (for example a configured libpq service and password file outside this repository):

```text
psql service=swasthyalens_dev -v ON_ERROR_STOP=1 -f database/migrations/20260914164833_auth_foundation.sql
psql service=swasthyalens_dev -v ON_ERROR_STOP=1 -f database/verification/schema.sql
psql service=swasthyalens_dev -v ON_ERROR_STOP=1 -f database/verification/rls-isolation.sql
```

These commands run from the repository root. SQL Editor is the supported owner workflow when no local database tooling exists. The already-authorized initial remote migration was applied through the connected migration tool and is recorded in Supabase migration history. No local CLI project was initialized. Future migrations require their phase's reviewed scope; no database reset or destructive down migration is part of this workflow. Corrections after application require a new reviewed migration rather than editing already-applied history. Do not insert migration history rows by hand.

## Schema and API contract

| Object | Data / constraints | Relationship |
|---|---|---|
| `public.profiles` | `id uuid` primary key; nullable trimmed `display_name` of 1–80 characters without control characters; server-set `created_at` and `updated_at` | `id → auth.users(id)`, delete cascade |
| `public.user_settings` | `user_id uuid` primary key; `preferred_language` is `en` (default) or `hi`; `timezone` defaults to `UTC` and must exist in the database's IANA timezone names; server-set timestamps | `user_id → auth.users(id)`, delete cascade |
| `public.session_context()` | No arguments; returns JSON `{ "active": true, "expires_at": <Unix seconds> }` or `{ "active": false, "expires_at": null }` | Current JWT subject and provider session only |

The account UUID is the authoritative Supabase Auth UUID everywhere. There is no secondary account ID, generated profile identity or profile-to-settings identity chain. The two primary-key indexes are sufficient for the current owner equality lookups and their foreign keys; no redundant indexes are added.

After authentication, FastAPI initializes missing rows with the verified subject, using that user's access JWT and the application publishable key:

- `POST /rest/v1/profiles?on_conflict=id`, body containing only the verified `id`, with `Prefer: resolution=ignore-duplicates,return=minimal`.
- `POST /rest/v1/user_settings?on_conflict=user_id`, body containing only the verified `user_id`, with the same preference.
- Read/update requests also filter the corresponding owner column. RLS remains authoritative even if a caller changes or omits a filter.
- `POST /rest/v1/rpc/session_context` with body `{}` returns the session contract. It uses the user's access JWT; anonymous callers have no execution privilege.

`ON CONFLICT DO NOTHING` does not overwrite settings and needs no identity-update privilege. Do not switch to `resolution=merge-duplicates`, which attempts an update of owner columns. Profile/settings initialization is independently retryable; a failed second insert can be safely retried without replacing the first row. No privileged signup trigger is added.

## Grants and policies

| Operation | `profiles` | `user_settings` |
|---|---|---|
| SELECT | Authenticated owner with active session | Authenticated owner with active session |
| INSERT | Only `id`, `display_name`; resulting owner must be the caller | Only `user_id`, `preferred_language`, `timezone`; resulting owner must be the caller |
| UPDATE | Only `display_name`; both existing/resulting owner checked | Only `preferred_language`, `timezone`; both existing/resulting owner checked |
| DELETE | Authenticated owner with active session | Authenticated owner with active session |
| Anonymous access | None | None |

Each operation has its own explicitly named policy. RLS is enabled and forced. Supabase's possible default table grants are revoked before column grants are applied. Neither owner IDs nor timestamps can be updated by `authenticated`; timestamps cannot even be supplied on INSERT. Defaults and the update trigger set timestamps using the database statement clock. `SELECT` and `DELETE` are ordinary table privileges, still restricted by owner/session policies. No runtime service-role privileges are granted.

Changing `auth.users` remains the authentication provider's responsibility. Profile deletion is not account deletion; a subsequent authorized initialization may recreate a profile/settings row. The application does not expose an account-delete API in Phase 2.

## Session helper boundary

Within the Phase 2 session helpers, only `swasthyalens_private.current_session_context()` is security-definer. The additional private Phase 3 lifecycle helpers are described above. The session helper has no caller-supplied identity, a fixed empty search path, fully qualified provider tables and tightly scoped execution grants. It checks:

1. The claims describe an `authenticated`, non-anonymous account.
2. `auth.uid()` is a valid subject and `session_id` is a canonical UUID; malformed/missing claims fail closed.
3. An `auth.sessions` row exists for **both** that session UUID and subject UUID.
4. Its creation timestamp is present and not in the future.
5. The current database statement time is before `created_at + 8 hours`, and before `not_after` when Supabase supplies an earlier limit.

Expired/inactive sessions return no timestamp. Refreshing a provider token does not change the original session-creation limit. Deleting the provider session revokes access on subsequent database statements even when the old JWT has not expired. This is an eight-hour application lifetime, not an inactivity timer or a claim about paid Supabase session settings. Provider-specific inactivity/single-session settings are outside the initial contract.

The boolean `swasthyalens_private.session_is_active()` used by RLS and the public JSON RPC are both **security-invoker**. `authenticated` has private-schema USAGE and execution of the required helpers, but no CREATE privilege or direct read grant on provider session tables. The schema must remain unexposed in the Data API. Helpers return no email addresses, provider tokens, raw claims or session rows. The public wrapper accepts no alternate user or session ID.

PostgREST verifies JWTs before mapping requests to a role; FastAPI independently verifies the provider signature, issuer, audience, expiry and identity. SQL tests deliberately simulate already-verified claims to test database policy behavior. They do not replace cryptographic verification.

## Verification coverage and limits

`schema.sql` checks enabled/forced RLS, exactly four authenticated policies per table, anonymous denial, owner/timestamp column privilege restrictions, RPC grants, helper execution modes/search paths and private-schema privileges. Its result sets also expose the complete constraint definitions, including `auth.users` foreign keys. Manually confirm the private schema is absent from exposed API schemas; PostgreSQL object introspection alone does not prove external API configuration.

`rls-isolation.sql` creates random identities and sessions **inside a single transaction**, changes to the real `authenticated`/`anon` roles and runs permission checks against the actual application tables. All fixtures, temporary helpers and updates are rolled back. It tests:

- A/A and B/B initialization/read/update, conflict-ignore retries and permitted owner deletion.
- A/B and B/A SELECT/list, UPDATE, DELETE and forged-owner INSERT; actual stored rows are checked after attack attempts.
- Direct owner/timestamp mass assignment; invalid display names, language, timezone and nulls.
- Provider-session/subject mismatches; missing/malformed claims; Supabase anonymous identities; direct provider-session reads.
- Eight-hour expiry, earlier provider `not_after`, replay after provider-session deletion and anonymous role denial.
- Authoritative user deletion cascading to both owned tables.

It does **not** send email, create usable passwords, issue signed access/refresh tokens or exercise FastAPI/browser flows. Its `.invalid` fixture email addresses are generated at runtime and never used for sign-in. No pre-existing account is selected or changed. Do not run fragments or change the final `rollback` to `commit`. If execution fails, the transaction is aborted; roll it back before doing anything else.

The separate live two-user harness has now proved FastAPI and direct Data API behavior using real opted-in test accounts and genuine provider-issued tokens. Browser login/refresh/logout, CSRF, HttpOnly cookies and account persistence also passed. Actual signup-email delivery and OTP-code verification remain unverified under the owner-confirmed locked-template limitation. A SQL fixture pass or Auto Confirm account does not establish email-flow acceptance.

Timezone validation uses the database's installed timezone catalog, including valid IANA aliases. After a future timezone-data upgrade, inspect stored timezone validity before changing/removing supported names. The backend's timezone package and database catalog should be kept compatible.

## Design references

Phase 5 adds `report_parameter_runs`, immutable `report_parameter_candidates`, and
append-only `report_parameter_reviews` through migrations
`20260916165018_structured_parameter_candidates.sql` and
`20260917052948_parameter_source_index.sql`. Apply these after Phase 4. There are
no new credentials or observations tables. All three tables have forced owner /
active-session RLS and authenticated SELECT-only grants. Mutation RPCs require the
existing server processing secret plus the owner JWT. Existing deletion-intent
cleanup cascades through all parameter data. Run
`verification/parameters-schema.sql` and the complete rollback-only
`verification/parameters-lifecycle.sql`; the latter uses temporary synthetic
identities and restores all fixture/key changes on rollback. See the
[Phase 5 handoff](../docs/phase-5-handoff.md) for contracts, limits and live evidence.

## Phase 6 observations

The same development project has, in order,
`20260917103144_health_observations.sql`,
`20260917105520_observation_query_aliases.sql` and
`20260917165418_observation_measurement_order.sql`. Apply them after all Phase 5
migrations on a fresh installation. These are already recorded on the development
project; do not rerun them there. Corrections use additional migrations rather than
rewriting applied history.

`health_observations` holds owned source identities and opaque manual deletion
tombstones; `health_observation_revisions` holds immutable fields/date snapshots.
Both have forced active-session/owner RLS and authenticated SELECT-only grants.
The private lifecycle function, reached through a public invoker wrapper, requires
the existing processing secret and owner JWT. It never accepts an authoritative
browser owner or report-derived value. A partial unique index enforces one active
revision, and review changes atomically supersede/invalidate publication. Existing
report deletion cascades through all derived observations. Manual deletion erases
value revisions and preserves only a minimal request-identity tombstone.

Run `verification/observations-schema.sql` and the complete rollback-only
`verification/observations-lifecycle.sql`, plus all eight earlier scripts. All ten
passed after the final Phase 6 migration. Live HTTP tests additionally cover two-user
isolation, concurrency, pagination, dates, units, revocation and deletion. See the
[Phase 6 handoff](../docs/phase-6-handoff.md). No new credentials or setup are needed.

## Phase 8 deterministic trends

Migration `20260924185746_deterministic_trends.sql` is applied to the same development
project. It adds two partial active-revision metric/unit/date indexes and an invoker
`trend_context` RPC with its invoker private helper. It creates no tables or persisted
trend snapshots and requires no processing secret. All reads retain owner/active-session
RLS, use the saved timezone, and accept no caller-supplied owner ID.

Requested series have exact units and bounded history: two 7/30-day windows for frequent
metrics, or 366 days for occasional labs. A 501st row or 51st metric/unit group causes
the application to fail closed instead of returning a partial statistic. The RPC reads
only active observation snapshots; no raw OCR or candidate values enter calculations.

Run the complete `verification/trends-schema.sql` and rollback-only
`verification/trends-lifecycle.sql` with the fourteen earlier verification scripts.
All sixteen passed. No new security-advisor finding was introduced; existing findings
and live two-user results are documented in [the Phase 8 handoff](../docs/phase-8-handoff.md).
Phase 7 provider availability and its permanent attempt ledger are unchanged.

## Reference links

- [Supabase RLS and grants](https://supabase.com/docs/guides/database/postgres/row-level-security) explains their combined effect and anonymous-role behavior.
- [Supabase session lifecycle](https://supabase.com/docs/guides/auth/sessions) documents JWT `session_id`, delayed expiry cleanup and session removal on logout.
- [PostgreSQL column privileges](https://www.postgresql.org/docs/current/ddl-priv.html) documents limiting INSERT/UPDATE assignments by column.
- [PostgreSQL function security](https://www.postgresql.org/docs/current/sql-createfunction.html) documents invoker/definer execution and default function privileges.
- [PostgreSQL timezone names](https://www.postgresql.org/docs/current/view-pg-timezone-names.html) documents the timezone catalog used by validation.
