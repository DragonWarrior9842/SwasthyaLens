# Deployment preparation — not authorization to deploy

2026-10-10. **Phase 13 code/security release-readiness is complete; Phase 14 remains unstarted.** No host, paid service, production domain or staging project has been selected or provisioned. The proposed first target is an **isolated synthetic staging environment**, one backend process, **AI disabled and voice disabled**. Public signup/recovery requires reliable SMTP/email acceptance. Until then, the proposed closed pilot must explicitly restrict the Auth/UI scope and make those public flows unavailable. This proposal does not itself disable public signup in the existing development project.

## Artifacts and environment

Use Node 24.19.0/npm 11.19.0 and Python 3.12.14. Build from the reviewed lockfiles: `npm ci` then `npm run build` in `frontend`; deliver only `frontend/dist`, never `dist-acceptance`. Leave `VITE_ENABLE_VOICE` unset/false. Install backend runtime dependencies with `python -m pip install --require-hashes -r requirements.lock` and `python -m pip check`; Linux also needs reviewed Tesseract/Leptonica libraries and the hash-verified OCR models. Preserve native license notices.

Supply [the server template](.env.example) through an approved secret store. Set `ENVIRONMENT=staging` for isolated acceptance, later `production` only after approval. Set the exact HTTPS `APP_ORIGIN`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, Supabase URL/publishable key, strong CSRF/processing keys and absolute private OCR model directory. `AUTH_RATE_LIMIT_MODE=edge` declares a requirement; the gateway must actually enforce it. Never supply service-role credentials to the browser. Never set AI keys, `RUN_AI_INTEGRATION`, other test gates or development dotenv files in the release process.

Start from `backend`:

```text
python -m uvicorn app.release:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log --no-proxy-headers --no-server-header
```

Use the chosen host's private binding as appropriate. Do not expose an alternative path around the HTTPS gateway. Production AI currently fails closed with truthful unavailable UI and no mock fallback; there is no supported enable flag. Future enablement requires separately reviewed code/configuration and a release policy. Voice can remain disabled until the [physical checklist](../docs/phase-13-manual-acceptance.md) passes.

## Gateway and verification

Serve the static build and proxy same-origin `/api` to the backend, stripping `/api`. Enforce exact hosts/origins, TLS, body/read/concurrency limits and auth abuse controls. Install `dist/security-headers.json` as actual response headers. Preserve API/download/export `no-store`; use immutable caching only for hashed public assets. Secure HttpOnly host-only SameSite=Lax cookies are required. Install HSTS at the trusted HTTPS edge after verification; no preload/includeSubDomains assumption or client-controlled forwarded-header trust.

`GET /health` is liveness only and makes no provider request. Separately verify synthetic Auth/DB/private Storage/OCR operations, error-response headers, session revocation and two-user isolation. Configure host/gateway logging to exclude bodies, query strings, credentials, cookies, raw filenames and medical content. Validate low-privilege OCR execution, private ephemeral storage, restricted filesystem/egress and crash cleanup before any real personal data.

## Database, staging and rollback

Replay all **17 ordered migrations** on an approved fresh local/isolated target and run all **24 whole SQL verification scripts**, preserving rollback wrappers. The latest migration is `20261004130141_explanation_model_metadata`; do not rewrite historical migrations. Provision the private processing capability securely and set exact Supabase Auth site/redirect URLs to the selected frontend URL. Development history matching is not fresh replay evidence. Never reset the shared development or production database.

Before rollout, approve RPO/RTO and separately back up database data, private report objects/manifests/checksums, migrations/configuration and secret-store recovery. No paid backup/PITR or restore drill is claimed enabled. Restore into an approved isolated target and verify ownership, object checksums, deletion/tombstone state, stale evidence, migration versions and synthetic lifecycle tests. Retain previous reviewed frontend/backend artifacts; code rollback must remain compatible with current schema. Use approved forward corrections/recovery for schema/data changes, never a remote reset.

## Phase 14 prerequisites

This is the single authoritative prerequisite list. Closing Phase 13 grants no authority to execute it. Items1–4 establish authorization and scope; remaining setup/acceptance gates must be satisfied on the approved staging candidate before promoting the affected scope. Unverified controls stay open.

1. Obtain explicit user authorization to begin Phase 14 and agree the feature/authentication scope. Use synthetic data only; real health data needs a separate acceptance decision.
2. Approve hosting target(s), runtime and the initial single-backend-process topology; do not provision paid infrastructure without approval.
3. Approve/provision isolated staging and exact frontend/backend HTTPS URLs; shared development is not equivalent staging.
4. Resolve the branch-protection/required-checks decision and configure/verify required checks before release. Successful CI does not configure enforcement.
5. Place staging/production secrets privately in an approved secret store; validate fail-closed configuration, processing capability and pinned native models. Never ship private dotenv files or service-role secrets to the browser.
6. Replay all17 migrations on an approved empty target, including `20261004130141_explanation_model_metadata`, then run all24 whole SQL verification scripts. Preserve history; never reset the shared database.
7. Configure exact Supabase Auth site/redirect URLs and frontend/backend origin/host settings for the approved URLs.
8. Accept reliable production SMTP/email signup/recovery, OR explicitly restrict pilot Auth/UI with unrestricted public signup/recovery unavailable. Auth/security tests do not establish email reliability.
9. Complete managed-service/security assessments, including supported PostgreSQL maintenance and leaked-password protection; record operator decisions and required controls.
10. Exercise recovery of database data, private report objects and configuration/secret placement into an isolated target; verify ownership, checksums, migration state and deletion/stale-evidence behavior. Approve recovery objectives and rollback compatibility.
11. Verify deployed HTTPS, security/error-response headers, HSTS policy and sensitive cache behavior; do not infer these from localhost tests.
12. Verify deployed CORS/origin/host enforcement, secure cookies, session revocation, two-user isolation and edge rate/body/concurrency limits.
13. Verify hosting/gateway logging privacy, alerts, incident ownership and operational acceptance without health content, credentials or raw audio in logs.
14. Accept the OCR deployment image, native licenses/security, least-privilege execution, private ephemeral storage, filesystem/egress limits and crash cleanup before accepting that scope.
15. Run approved synthetic staging lifecycles for the core authenticated application, reports/OCR/history/trends and exports/notifications. They are eligible for staging acceptance, not already deployed/accepted.
16. Keep AI OFF and `RUN_AI_INTEGRATION` unset. No currently approved supported production AI enablement path exists; future enablement requires separate implementation/policy review and explicit authorization. No silent production mock fallback.
17. Keep voice OFF. Enable only after the applicable [physical checklist](../docs/phase-13-manual-acceptance.md) passes and the operator explicitly approves the feature.

No item above was performed by this documentation closure. No deployment, feature enablement or provider request is authorized here.
