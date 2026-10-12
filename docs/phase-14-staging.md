# Phase 14 — isolated synthetic staging preparation

## Current status — 2026-10-12, Gate D1

Phase 13 is **COMPLETE within its formally accepted scope**. Phase 14 repository
deployment preparation is complete; no public deployment occurred. Phase 14A's
read-only alternative-hosting assessment is complete: **NO-GO for approving
Vercel + Render + Supabase under the assessed constraints**, not a finding of
technical impossibility. Phase 14B planning and its **CI-only Linux verification
sub-scope are complete**. Full local Linux runtime validation, hosted staging
acceptance and production acceptance are **NOT complete**.

The reference architecture remains one Ubuntu 24.04 LTS VM, native systemd,
Nginx serving the React/Vite build and same-origin `/api/`, one FastAPI process
on `127.0.0.1:8000`, Python 3.12.14, local PDFium/Tesseract OCR and dedicated
Supabase staging. This is a reference design, not an approved purchase.

Current policy: **strict ₹0 additional spending, no payment card requirement,
no trials, no automatic paid upgrades, no feature removal or security weakening**.
Public deployment is deferred: no suitable permanent, free, no-card, full-featured
public Linux host has been verified. DigitalOcean provisioning was paused; no
Droplet was purchased and no paid VM was created. Historical planning listed a
$24/month base VM and a $30/month ceiling including taxes. Those figures remain
historical estimates/authorization context, not current pricing evidence or
permission to spend; the ₹0 policy replaces that ceiling for future decisions.

The owner previously confirmed creation of `swasthyalens-staging`, project ref
`afbpscbdgvezrbwehsdv`, Singapore `ap-southeast-1`, Free plan at last confirmation
($0/month). This documentation gate did not query the project. No staging
migrations or application deployment occurred; Auth configuration, RLS, private
Storage and integration acceptance remain pending. Project existence is not
acceptance evidence. The development project must remain untouched; never copy
development credentials, identities, reports or objects into staging.

### Verified CI and retained failure history

Accepted code baseline: [commit 5db0a16df6547f479afec717b7110756dfa446ad](https://github.com/DragonWarrior9842/SwasthyaLens/commit/5db0a16df6547f479afec717b7110756dfa446ad).
[Workflow 38258935511](https://github.com/DragonWarrior9842/SwasthyaLens/actions/runs/38258935511)
completed successfully on attempt 1. These are existing results, not reruns in D1.

| Verified evidence | Result |
|---|---|
| [Backend job 114844155949](https://github.com/DragonWarrior9842/SwasthyaLens/actions/runs/38258935511/job/114844155949) | PASS — 749 passed, 13 skipped, 2 warnings |
| [Frontend job 114844155502](https://github.com/DragonWarrior9842/SwasthyaLens/actions/runs/38258935511/job/114844155502) | PASS — 382 tests across 17 files; lint, typecheck and build |
| Backend Ruff/format and Linux mypy | PASS — 115 source files typed |
| Nginx configuration and systemd syntax | PASS — configuration verification only |
| Synthetic loopback gateway | PASS — Host/SNI and malformed-Host rejection, zero upstream dispatch for rejected hosts, routing, headers, upload boundaries and mutation-dispatch checks |
| Native OCR model setup and backend tests | PASS — includes synthetic native extraction/OCR; not measured two-slot hosting capacity |

The two backend warnings are dependency deprecations involving Starlette/httpx
and AnyIO's `BlockingPortal` alias. Skipped tests are not accepted integrations.
Synthetic gateway stubs do not establish Supabase integration or public HTTPS;
systemd syntax/policy checks do not establish runtime enforcement.

Preserved **FAIL**: [CI-2 workflow 38251514825](https://github.com/DragonWarrior9842/SwasthyaLens/actions/runs/38251514825),
commit `7a3321cb898bcfb705fd594918043fc4b71462dd`, backend job `114818759796`,
failed at `deploy/verify_linux.py:171` with
`AssertionError: Unexpected Host was not rejected with a closed connection`.
Frontend passed 382 tests and Linux mypy passed 115 files; OCR model setup and
backend pytest were skipped after failure. CI-3A diagnosed incomplete HTTP-level
Host rejection in the default HTTPS server. CI-3B added `return 444;` alongside
the retained `ssl_reject_handshake on;`, preserved the named-server Host check,
and added focused synthetic regressions. The accepted commit/run above verifies
that correction; it does not change the failed run's outcome.

### Outstanding gates and evidence limits

**PASS** means verified evidence; **FAIL** means a confirmed unmet requirement;
**BLOCKED** means required infrastructure is unavailable; **NOT RUN** means the
acceptance was not executed. A blocked runtime requirement can also be not run.

| Gate | Current status / required evidence |
|---|---|
| Local Linux environment | BLOCKED — WSL access denied, Docker Linux engine unavailable, no usable existing Ubuntu host identified; no Windows security-policy changes authorized |
| Native systemd runtime | NOT RUN; target infrastructure BLOCKED — identity/permissions, cgroups, filesystem protections, loopback listener, restart and shutdown enforcement |
| Two-slot OCR capacity and containment | NOT RUN — measured CPU/RAM/temp storage, filesystem/network containment and process-tree cleanup; shared Unix identity/network namespace is not complete hostile-document isolation |
| Fresh isolated database acceptance | NOT RUN — all 17 migrations, all 24 whole SQL verification scripts, grants/RLS, private Storage and two-user isolation on the approved target |
| Restricted direct Supabase Auth | NOT RUN — app-level signup/recovery restrictions do not establish direct provider settings or exact Auth redirects |
| Public HTTPS and secure cookies | NOT RUN; hosting BLOCKED — DNS/certificates, exact origins, Secure/HttpOnly/SameSite cookies, CSRF and session revocation |
| Backup and isolated restoration | NOT RUN — approved destination/target, RPO/RTO, database/object/configuration recovery and verification |
| Privacy-safe deployed logs and operational ownership | NOT RUN — host/provider logging, alerts, incident and maintenance responsibilities |
| GitHub main branch protection | FAIL — GitHub reported `protected: false` on 2026-10-12; owner configuration and verification remain required |
| Hosted availability, recovery and compatible artifact rollback | NOT RUN; hosting BLOCKED |

AI OFF; voice OFF; restricted signup/recovery; synthetic data only; no production
promotion or live AI-provider requests. `RUN_AI_INTEGRATION` remains unset.
OpenAI history remains **3 authorized successful requests**; Gemini remains
**2/20 historical attempts, both HTTP 503**. All detailed release prerequisites
below remain in force. D1 changes documentation only and grants no execution or
resource-creation authority. Commit/push and automatic CI require a separate gate.

## Historical preparation baseline — 2026-10-11 to 2026-10-12

The following baseline and its original evidence are retained as history; the
current-status section above supersedes its provisioning and CI status.

2026-10-11. **Repository preparation only. No cloud provisioning or deployment.**
Final pre-commit review resumed2026-10-12; staged-state secret scan also passed
(771 reachable blobs,6 private comparisons,21 bundle files,zero findings).
Baseline: `main`, clean, `636a5fd5f55d48eecaff9685d30f5fe83060cd8c`.
Phase 13 remains complete for its supported scope. Baseline post-documentation
workflow38066043924 passed both jobs (backend114253781024/frontend114253781187).
This record supersedes “Phase14 unstarted” as a current status, without changing
the dated Phase13 history. Preparation does not establish operational acceptance.

## Approved preparation and feature scope

One Ubuntu24.04 LTS VM; Nginx serves only `frontend/dist` and forwards same-origin
`/api/` to one FastAPI process on `127.0.0.1:8000`. Native systemd was selected to
keep process ownership, resource controls and OS package maintenance explicit,
without Docker orchestration. The dedicated staging project has since been
created as recorded above; its configuration and acceptance remain pending.
The shared development Auth/DB/Storage project is not an isolated target.

Core confirmed-user login, reports, local OCR, review/publish, history, trends,
exports and notifications are candidates for synthetic deployed acceptance.
AI explanations/assistant remain OFF, with truthful unavailability and no mock
fallback. Voice remains OFF. Public signup, verification/resend and password
recovery remain unavailable in the restricted release scope.

OpenAI history: **3 successful authorized requests**. Gemini history: **2/20,
both HTTP503**. No new request, automatic retry, provider/model change or spend.
`RUN_AI_INTEGRATION` and other integration flags must be absent from the service.
Only disposable synthetic identities and documents may be used.

## Prepared artifacts and responsibilities

| Artifact | Purpose |
|---|---|
| `deploy/systemd/swasthyalens.service` | Non-root, one-process release entry point; bounded service resources/temp storage |
| `deploy/nginx/staging.conf.template` | Exact hostname/TLS placeholders, static SPA and gateway limits |
| `deploy/nginx/security-headers.conf` | Frontend release policy, HSTS and no-store, including errors |
| `deploy/nginx/api-location.conf` | Prefix removal, minimal request headers, strict API response policy, no retries/buffering |
| `deploy/staging.env.example` | Blank secret/identifier slots, staging values and feature restrictions |
| `deploy/verify_linux.py` | Disposable offline syntax and loopback gateway verification; never installs a service |

No provisioner, deployment workflow, paid integration, DNS automation or migration
runner was added. GitHub CI verifies templates against a local synthetic stub;
that is not staging deployment or deployed acceptance.

## Installation model and directories — PENDING on target VM

Installation is an operator action after separate provisioning approval. Nothing
in this section has been run against a VM. Use reviewed immutable release IDs,
verify the commit and build checksums, and retain the previous compatible release.
Never copy a development working directory, private dotenv files, caches or test
credentials to the VM.

| Location | Owner/access and purpose |
|---|---|
| `/opt/swasthyalens/releases/RELEASE_ID/` | Root-owned, application read-only; selected backend runtime code/locks, frontend dist, notices, templates |
| `/opt/swasthyalens/current` | Root-managed symlink to one reviewed release |
| `.../backend/.venv/` | Root-built Python environment, service read/execute only |
| `.../ocr-models/` | Root-owned verified eng/hin/osd models, read-only; configured by absolute path |
| `/opt/swasthyalens/python/` | Root-owned pinned managed Python installation |
| `/etc/swasthyalens/staging.env` | Root:root0600 under0700 directory; PID1 loads it, service filesystem cannot read it |
| `/tmp` inside service | Private256MiB tmpfs; per-attempt0700 directories; only application writable data area |
| `/var/tmp` inside service | Read-only private mount; no persistent report temporary files |
| Nginx PID/runtime directories | Package-managed, separate from app; no report persistence or application code writes |

Create a dedicated `swasthyalens` system group/user with no login shell, no sudo,
no home, and no access to another application's secrets. Nginx workers use the
distribution's unprivileged `www-data` identity. Use root:swasthyalens0750 for
backend/model directories and root:www-data0750 for frontend directories; files
are group-readable, executable files group-executable, never group-writable.
Parent release directories permit traversal. This excludes Nginx from the
backend/model tree. Root performs installation; neither the API nor OCR runs as root.
Do not make `/opt/swasthyalens` writable by either service user.

### Build and native packages

Build frontend on a reviewed build machine using Node24.19.0/npm11.19.0,
`npm ci`, `VITE_API_BASE_URL=/api`, `VITE_ENABLE_VOICE=false`, and `npm run build`.
Copy only `frontend/dist`, never `dist-acceptance`. No Node runtime is needed to
serve the resulting files. Check `dist/security-headers.json` against the gateway.

Ubuntu build/runtime packages: `ca-certificates`, `nginx`, `python3.12`,
`python3.12-venv`, `build-essential`, `pkg-config`, `libtesseract-dev`,
`libleptonica-dev`. The development packages provide the native headers/libraries
needed by the locked Linux tesserocr build (runtime libraries include
`libtesseract5` and `liblept5`). Record installed distro package versions and apply
reviewed security updates. Do not claim that a moving apt repository is a fully
reproducible OS snapshot. The separate Tesseract command-line executable and
distribution language-model packages are not required by this in-process binding.

Use the repository-pinned Python3.12.14, not an unreviewed patch substituted by
the host. One supported preparation path is the existing hash-locked `uv` tool
from `backend/requirements-dev.lock`: bootstrap it in a separate build-tools
venv using the distribution Python3.12, then use its managed Python installation:

```sh
# Future operator/build commands only, from the verified release source.
python3.12 -m venv /opt/swasthyalens/build-tools
/opt/swasthyalens/build-tools/bin/python -m pip install --require-hashes -r backend/requirements-dev.lock
export UV_PYTHON_INSTALL_DIR=/opt/swasthyalens/python
/opt/swasthyalens/build-tools/bin/uv python install 3.12.14
/opt/swasthyalens/build-tools/bin/uv venv --managed-python --python 3.12.14 backend/.venv
/opt/swasthyalens/build-tools/bin/uv pip install --python backend/.venv/bin/python --require-hashes -r backend/requirements.lock
```

For the actual reviewed model setup, from the `backend` directory:

```sh
.venv/bin/python scripts/setup_ocr_models.py /opt/swasthyalens/releases/RELEASE_ID/ocr-models
```

The existing script downloads only its fixed upstream revisions and verifies
SHA256 for English, Hindi and orientation models. It is never invoked on an
upload or application startup. `pypdfium2` supplies the platform PDFium binary
through the hash-locked Python package; no separate arbitrary PDFium download.
Verify `python --version`, dependency consistency (`uv pip check --python ...`),
native imports, model hashes and native license notices before activation.
Build-tool downloads and native linking remain target-installation checks; no
such downloads are authorized against cloud resources in this preparation turn.

### Process, files and isolation

The unit invokes exactly:

```text
/opt/swasthyalens/current/backend/.venv/bin/python -m uvicorn app.release:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log --no-proxy-headers --no-server-header
```

`app.release` reads deployment environment only, never local dotenv files.
No reload/debug, alternative listener or extra application workers. Systemd
restarts a failed process with a bounded restart policy; it does not retry an
API mutation or provider request. `KillMode=control-group` and a135s stop deadline
include OCR descendants. The service ceiling is2560MiB/200%CPU/64tasks on the
proposed4GiB host. These are starting controls, not measured capacity evidence.

Existing extraction behavior is unchanged: two slots; at most120s per process;
768MiB address-space cap per parser;64MiB per-attempt file watchdog; bounded page,
pixel and output sizes; credential-stripped child environment; kill/wait on
timeout; normal/failure cleanup. A private256MiB tmpfs adds a hard aggregate
storage ceiling and disappears when the service mount namespace exits. Test
SIGTERM/SIGKILL/restart cleanup and resource failure on the actual VM.

Systemd protects the application filesystem, home and kernel interfaces, removes
capabilities and prevents privilege escalation. It is **not** a complete hostile
parser sandbox: parent and child still share a Unix identity/network namespace.
Do not claim child egress isolation or inaccessible parent memory from these
settings. Actual VM firewall/egress and OCR containment acceptance remain PENDING;
stop if the required isolation cannot be demonstrated. Never accept real data
on the strength of these templates.

## Gateway — PENDING on target VM

Render `STAGING_HOSTNAME` in both gateway files to the approved exact hostname.
Replace `TLS_CERTIFICATE_FILE` and `TLS_PRIVATE_KEY_FILE` with the real reviewed
certificate paths; they are placeholders, not fabricated certificates. Obtain
and renew certificates only through the separately approved TLS/DNS process.
Do not enable this HTTPS template without valid certificates. Remove the default
site only after operator review, then install the http-context template under
`/etc/nginx/conf.d/` and the two includes under their named snippets paths.
Run `nginx -t` before any approved reload.

Only `/api/` is proxied, with prefix removal. Unknown hosts are rejected. HTTP
redirects only to the canonical HTTPS root, discarding query/path information.
The frontend uses a safe SPA fallback; missing assets/API routes never fall back
to HTML. Dotfiles, sensitive extensions, maps and the header metadata file are
not served. Static content and errors retain the release CSP/headers. API errors
retain stricter API CSP. All responses are no-store initially; no sensitive
caching, CORS relaxation, HSTS preload or includeSubDomains assumption.

Gateway body limit: **6MiB (6,291,456bytes)**, a bounded allowance above the exact
5MiB application limit. Uploads are currently raw PUT bodies (no multipart size
inflation); the app still rejects files above5,242,880bytes and unrelated JSON
bodies above16KiB. Nginx does not replace those checks. Request/response buffering
and upstream retries are off for API traffic. Connect/send/read timeouts5/65/130s;
the app's upload read/processing deadlines remain authoritative.

Connection caps10 per TCP peer/40 per virtual server; general rate10r/s with
burst20; auth POSTs6r/min with burst10. These conservative pilot settings require
synthetic verification/tuning without removing limits. The backend intentionally
sees loopback and retains its local limits, so confirmed-user load is initially
small. No client-supplied forwarded address is trusted. Nginx forwards only
canonical Host, Accept, Content-Type, Cookie, Origin and X-CSRF-Token plus required
HTTP body framing. TLS is terminated by Nginx, secure cookie settings derive
from staging configuration, and HSTS is set at that actual HTTPS edge.

Nginx access logging is off and request-bearing error logs go to `/dev/null`.
No raw request URI/query/header/body is added to logs. This deliberately reduces
diagnostics until privacy-preserving telemetry is accepted. The backend uses its
existing sanitized logging and disables Uvicorn access logging; operator-only
journal retention/permissions and hosting logs require deployed review. Do not
enable debug logging or paste raw logs into documentation.

## Environment inventory

All required identifier/secret slots in `deploy/staging.env.example` are blank.
Populate only the root-owned target environment file through private operator
access; a native VM has no managed application environment-variable dashboard.
Never put secrets in a cloud-init/user-data field, shell history, process arguments
or VITE variables. Systemd's root manager reads the0600 file. Missing required
values fail startup. JSON tuples such as `ALLOWED_HOSTS='["actual.host"]'` and
`CORS_ALLOWED_ORIGINS='["https://actual.host"]'` need the exact approved hostname.

| Category | Variables / intended values |
|---|---|
| PUBLIC | `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` (non-secret identifiers, still used only by this BFF); frontend `VITE_API_BASE_URL=/api` |
| SERVER CONFIG | `ENVIRONMENT=staging`, exact `APP_ORIGIN`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `AUTH_RATE_LIMIT_MODE=edge`, absolute `OCR_TESSDATA_DIR`, `REPORT_MAX_UPLOAD_BYTES=5242880`, `REPORT_PROCESSING_MAX_PAGES=20`, `REPORT_PROCESSING_TIMEOUT_SECONDS=120` |
| SECRET | `CSRF_SIGNING_KEY`, `REPORT_PROCESSING_KEY`: independently generated strong staging values, never copied from development |
| FEATURE GATE | `PUBLIC_SIGNUP_ENABLED=false`; frontend build `VITE_ENABLE_VOICE=false`; AI has no supported release enable switch |
| ABSENT | `AI_API_KEY`, `AI_PROVIDER`, `AI_MODEL`, `RUN_AI_INTEGRATION`, `RUN_SUPABASE_INTEGRATION`, `RUN_OCR_EVALUATION`, `DISPOSABLE_TEST_ACCOUNTS_CONFIRMED`, test account credentials, service-role/secret Supabase credentials |
| SERVICE INTERNAL | `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`, `TMPDIR=/tmp`, `TEMP=/tmp`, `TMP=/tmp`; parser `OMP_THREAD_LIMIT=1` is already set by application code |

The database administrator password/SSH private key are provisioning secrets,
not runtime application variables. Keep them in private credential storage.
Normal requests continue using the publishable key and owner JWT, never a
service-role shortcut. Provision the existing processing capability privately
only after the dedicated database/migrations are approved.

## Restricted auth and network model

`PUBLIC_SIGNUP_ENABLED` defaults false. Staging/production reject true at startup
until a separately reviewed email policy exists. Development email-flow testing
can explicitly opt in; the existing synthetic auth fixture does so. No existing
development Supabase setting was changed.

The backend blocks signup, resend and verification with403 after existing CSRF
checks, before provider dispatch. `GET /auth/policy` returns only capability
booleans, no network calls/secrets. Recovery routes/UI do not exist and remain
unavailable. The UI reads policy without caching, starts restricted and remains
restricted on errors/malformed responses; direct registration URLs show a truthful
unavailable message. Confirmed login, refresh, session validation and logout keep
their existing security protections.

This app gate does not disable Supabase's direct public Auth API. **Before any
staging access**, the operator must separately disable new signups in the dedicated
project and approve the direct Auth/email restrictions and exact site/redirect
URLs. Only operator-created, confirmed disposable staging accounts are allowed.
Recovery has no global claim of being disabled on Supabase: verify the approved
project/provider settings before exposure. No Auth dashboard settings were changed.

Inbound plan:80/443 to Nginx, SSH only from approved administrator IP; no public
8000 or database port. Runtime outbound needs DNS to the approved resolver and
HTTPS to the dedicated Supabase project (Auth, REST/JWKS, private Storage).
OS time/update/certificate renewal services are separate operator needs; build
steps need approved package registries and the existing pinned OCR model hosts.
There is no AI-provider runtime allowance. No VM/cloud firewall or DNS change has
been performed, and egress isolation is not yet implemented or accepted.

## Health, migration, recovery and rollback gates

Liveness: Nginx exposes `/api/health`, stripping the prefix to `/health`.
It returns only `status=ok` and `service=swasthyalens-api`. Future local operator
check: `curl --fail --header 'Host: APPROVED_HOSTNAME' http://127.0.0.1:8000/health`.
Future external check: approved HTTPS `/api/health` with normal certificate
validation. Neither checks DB/Storage/OCR or calls AI. Dependency acceptance is
separate and synthetic; never add provider probes to health checks.

Replay all17 migrations on an empty isolated project, including
`20261004130141_explanation_model_metadata`; run all24 whole SQL verification
scripts with their rollback wrappers. Stop on failure. No historical migration
was edited and no migration was applied during preparation.

Rollback: stop new admissions at Nginx; stop the API and verify its cgroup has no
remaining OCR child; select the previous reviewed artifact compatible with the
current schema; switch the root-owned `current` symlink; validate unit/config,
restart once and run liveness plus approved synthetic acceptance before reopening.
Release, model, environment and frontend/backend versions must stay aligned.
Never run a down migration, database reset or destructive restore as code rollback.

Backup mechanism/destination, secret-store recovery and isolated restore target
remain PENDING. Include DB data, private report objects/checksums, configuration,
migration versions and deletion/tombstone/stale-evidence state. No managed backup,
PITR, RPO or RTO is claimed. Restore only after that mechanism is approved.

## Historical preparation verification and manual gates

This is the original preparation snapshot, not the current acceptance table.
In particular, its CI-pending and resource-creation statuses are superseded by
the dated current-status section above; original counts and failures are retained.

| Gate | Status |
|---|---|
| Baseline matches Phase13 closure | PASS |
| Local offline config/auth/release and header-contract checks | PASS —112 tests,2 existing deprecation warnings; Ruff/format PASS |
| Frontend lint/types/tests/build | PASS —382 tests/17 files; production build with same-origin API and voice off |
| Offline release-build browser auth policy checks | PASS —12 checks; every API mocked; no external requests |
| Local Linux nginx/systemd execution | BLOCKED — Nginx/systemd unavailable; Docker engine absent; WSL access denied; no bypass |
| Local Windows mypy | PASS —115 source files; normal tool execution, no security-policy changes |
| Linux CI typing/template/gateway checks | PENDING — authoritative new workflow required |
| Secret audit | PASS — zero findings;747 reachable blobs,6 privately compared known values,21 bundle files; private env files ignored |
| Complete diff review | PASS — only the24 intended preparation/config/auth/test/documentation files; no migrations, private values or generated artifacts |
| Resource creation, TLS/DNS, branch protection, Auth settings | PENDING — manual only, not performed |
| Fresh migrations/RLS/grants/private storage verification | PENDING |
| Actual VM isolation/logging/security/OCR/lifecycle acceptance | PENDING |
| Backup/restore and managed-service review | PENDING |
| AI/voice enablement and production promotion | NOT APPLICABLE to this authorization |

Local verification history: sandboxed Vitest initially failed to read temporary
cache files; the authorized normal-access rerun passed. Sandboxed pytest stalled
in the Windows asyncio socket-pair setup before serving requests; the two stalled
runs were stopped and the same offline cases passed outside the sandbox. No
Windows protections were weakened. The browser harness's first launch failed
before checks; using the installed Chrome channel, as existing harnesses do,
passed all12 cases. Linux CI now explicitly targets Ubuntu24.04 for the backend
and adds syntax plus synthetic loopback gateway checks. Actual systemd runtime,
TLS certificates, native installation and cloud controls remain unverified.

### Historical proposed provisioning order

The following was the preparation-era proposal, not a current instruction.
The empty Supabase project was subsequently created; no VM was purchased.
The current ₹0/no-card policy and separate authorization gates take precedence.

After focused commit and green CI, STOP at manual isolated-resource creation.
Before that action confirm provider, current price/budget and region. Proposed
names remain `swasthyalens-staging` (project), `swasthyalens-staging-01` (VM),
`swasthyalens-staging-fw` (firewall), `swasthyalens-staging` (Supabase).
The first resource gate is a new empty Supabase staging project in a Free
organization with available quota, specific Singapore `ap-southeast-1`; stop on
any paid requirement. Hostname is deliberately still a placeholder. Creating
resources, editing Auth/branch protections, deploying, spending money and later
production promotion each require their stated manual/authorization gates.

Reference behavior: [Ubuntu24.04 systemd execution controls](https://manpages.ubuntu.com/manpages/noble/man5/systemd.exec.5.html),
[Nginx proxy controls](https://nginx.org/en/docs/http/ngx_http_proxy_module.html),
[Nginx header inheritance](https://nginx.org/en/docs/http/ngx_http_headers_module.html),
[uv managed Python](https://docs.astral.sh/uv/guides/install-python/).
