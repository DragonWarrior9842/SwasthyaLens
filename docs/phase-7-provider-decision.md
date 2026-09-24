# Phase 7 provider decision — Gemini synthetic evaluation

Updated 24 September 2026. **Gemini 3.8 Flash (`gemini-3.8-flash`) Free Tier is
approved for the existing bounded synthetic evaluation only.** This is not a
production healthcare-provider decision. The owner stopped all further OpenAI
requests, including probes; the historical comparison below does not authorize one.

The owner confirmed a dedicated Google AI Studio project/key, billing unlinked,
Free Tier and ignored `backend/.env.ai.gemini` populated. The live flag remains
unset. AI Studio does not display RPM/TPM/RPD. The owner explicitly authorized an attempt
using `--quota-not-displayed`, without guessed values. One request returned HTTP
503 `UNAVAILABLE` (high demand); evaluation stopped immediately. This error does
not establish zero quota. See the exact result in the handoff. Acceptance remains incomplete;
Phase 8 and Phase 9 have not started.

## Provider suitability and privacy

Google lists structured output and free standard input/output for the selected
model. This supports feasibility, not measured grounding quality or account access.
[Model](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash),
[pricing](https://ai.google.dev/gemini-api/docs/pricing).

**Gemini Free Tier may use submitted inputs and outputs to improve Google products
and machine-learning technologies; human reviewers may process them.** No real,
personal, confidential or patient data may be submitted. This remains an internal
synthetic test of fixed informational language, without diagnosis, treatment or
clinical practice. No zero-retention, residency or healthcare-compliance claim is
made. [Terms](https://ai.google.dev/gemini-api/terms).

Correction to the earlier setup note: the current `generateContent` reference
**does document `store`** as a request logging control. The adapter sends
`store: false`. This does not remove the Free Tier data-use terms.
[REST reference](https://ai.google.dev/api/generate-content).

## Implemented shared boundary

- Separate Gemini adapter behind the existing `ExplanationProvider` protocol;
  dormant OpenAI request/schema contract remains intact and its real transport is
  blocked. No provider fallback, arbitrary endpoint or new SDK dependency.
- Fixed server-only `generateContent`, one text candidate, JSON Schema output,
  `store=false`, empty tools, no files, search, code, URLs, cached-content resource,
  history or database/storage credentials. Default provider safety filters remain.
- Exact shared model output contract and independent semantic validator. Wire
  translation changes `const` to singleton enum and omits unsupported string
  pattern/length keywords; all local constraints still apply. No prompt-only JSON
  fallback. [Structured output](https://ai.google.dev/gemini-api/docs/structured-output).
- Server selects 1–20 latest reviewed/published facts from one owned report.
  Enrollment binds newly generated synthetic fixtures to the exact evidence and
  file digest. No caller-provided report/prompt/file argument is accepted by the
  evaluator. Opaque aliases and server-only provenance map remain unchanged.
- Every echoed ID, value, unit, range, flag, kind, comparator, page, definition and
  note must match. Unsupported JSON, refusal, truncation, extra/tool/thought parts,
  grounding metadata and invalid usage fail closed. No arbitrary medical prose.
- Provider/model pairs are exact in settings, service, database and frontend.
  Migration `20260924080552_gemini_synthetic_explanations.sql` is applied to the
  existing development project. Original migrations and prompt/catalog versions
  are unchanged. Model is fixed per provider, so cache identity remains exact.
- RLS/session/CSRF/isolation, explicit consent, correction invalidation, deletion,
  TTL, idempotency and existing shared limits remain intact. UI discloses Google's
  data terms and resets consent if the selected provider changes.
- 32-KiB context, 48-KB request, 128-KiB response, 4,000-token output bound. Low
  thinking, no thought text; visible plus thinking tokens must fit the bound.
  Five-second connect, forty-second I/O and forty-five-second overall timeout.
  No automatic retries, redirect following or environment proxy use.
- Normal tests inject a deterministic mock, clear live flags/credentials and
  block both OpenAI and Gemini HTTP network transports. Adapter contracts use
  in-memory transports only; mock output is labelled explicitly.

## Free Tier, quotas and budget

Free Tier belongs to the Cloud project, not an environment variable. Billing must
remain unlinked. Owner confirmation cannot be represented as an independently
verified provider-side billing guarantee. No paid Gemini use is authorized; if
free access is unavailable, stop without upgrading or substituting a model.
[Billing](https://ai.google.dev/gemini-api/docs/billing).

`RUN_AI_INTEGRATION=1`, `--live-gemini`, `--free-tier-confirmed` and numeric quota
arguments are required when project quotas are displayed. The owner also approved
explicit `--quota-not-displayed` when AI Studio exposes no numbers. This mode
rejects simultaneous numeric quota arguments, makes no quota claim and keeps all
other gates. For displayed limits the conservative minimums remain 1 RPM / 57000
TPM / 2 RPD. Any two requests are spaced at least 61 seconds apart. Any unsuccessful
case, including 429 or access errors, stops the run. The first attempt returned
503; no second case, retry, billing change or model switch followed.
[Quota instructions](https://ai.google.dev/gemini-api/docs/rate-limits).

The permanent private counter caps Gemini at **20 attempts total**, including
failures. It is reserved before invocation and never refunded on correction,
deletion, expiration or restart. Existing OpenAI reservations remain **$0.50 of
$5**, unchanged; no OpenAI live requests are permitted. Gemini attempts remain
one of twenty. The $5 paid ceiling and no-paid-Gemini restriction both remain in force.

See [setup and execution](phase-7-gemini-setup.md) for manual configuration and the
live command, and [handoff](phase-7-handoff.md) for measured tests and remaining
acceptance work. Passing mock tests does not establish Gemini live quality.

## Historical OpenAI decision — 18 September 2026

Research checked: 18 September 2026. Repository baseline: `a876e24`.
The user approved OpenAI GPT-5.6 Terra for a synthetic Phase 7 evaluation with a
cumulative maximum of $5. This is not a permanent production healthcare-provider
decision. The comparison and proposed contract below preserve the original
Section 0 decision record. Implementation and actual acceptance status are tracked
in [the Phase 7 handoff](phase-7-handoff.md); see also the unchanged
[pre-implementation baseline](phase-7-baseline.md).

## Recommendation

Approve **OpenAI GPT-5.6 Terra (`gpt-5.6-terra`)** as the first development
candidate, using a server-side, non-streaming Responses request with strict
structured output, explicit `store=false`, no tools and synthetic-only live tests.
Its schema/Pydantic integration fits this FastAPI application and its published
price is practical for a bounded explanation. This is an engineering starting
choice, not evidence that it is medically safer or more accurate than competitors.
[Model specification](https://developers.openai.com/api/docs/models/gpt-5.6-terra),
[structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

Gemini 3.8 Flash is the strongest cost-focused alternative in this comparison.
Claude Sonnet 5 is a close alternative with structured output and documented
contractual retention options. Actual grounded quality, Hindi/Hinglish quality
and latency remain unmeasured for all three. No account-specific access, quota,
credit, BAA or zero-retention entitlement has been verified.

## Capability and operational comparison

These are direct provider APIs. Google Cloud/Vertex or enterprise deployment is a
separate service/contract decision; its terms must not be inferred from the Gemini
Developer API comparison.

| Criterion | OpenAI GPT-5.6 Terra | Google Gemini 3.8 Flash | Anthropic Claude Sonnet 5 |
|---|---|---|---|
| 1. Structured output | Strict JSON Schema; Pydantic integration. | JSON Schema subset; Pydantic integration. | JSON Schema output; Pydantic integration. Built-in Citations cannot be combined with strict JSON; our opaque evidence IDs do not need that feature. |
| 2. Instruction following | Suitable evaluation candidate; no project-specific result yet. | Same; price does not establish adherence. | Same; no justified winner without identical adversarial fixtures. |
| 3. Context/output limits | 1,050,000 context; 128,000 maximum output tokens. | 1,048,576 input; 65,536 output tokens. | 1M context; 128K output tokens. |
| 4. Latency | Unmeasured here; reasoning/output budget affects completion time. | Flash is a speed-oriented candidate; no measured local p95. | Provider labels it fast; no measured local p95. |
| 5. Standard token cost | $2 input / $12 output per million. | $0.75 input / $3.75 output per million through 2026-12-31; $1.50 / $7.50 from 2027-01-01. | $2 input / $10 output per million. |
| 6. Privacy/data handling | API data is not trained on by default; retention is separate. | Paid and unpaid terms differ materially; use paid handling for any proposed sensitive-data deployment. | Commercial API data is not trained on by default; feedback/opt-in exceptions apply. |
| 7. Retention controls | Standard abuse logs up to 30 days, with exceptions; additional feature state/cache rules. Approved ZDR/MAM is separate. | Paid terms retain limited-period safety/legal logs without a fixed duration stated there; do not promise ZDR. | Standard API deletion within 30 days, with exceptions; contractual ZDR and feature eligibility must be checked. |
| 8. Healthcare implications | Applicable contract, eligible features and any required BAA must be confirmed before regulated production use. | Developer terms prohibit clinical practice/medical advice; educational scope must fit terms. Enterprise healthcare suitability requires a separate assessment. | Signed BAA and HIPAA-enabled organization/eligible API features are documented; none are established for this project. |
| 9. India availability | India is supported. Availability is not India-only processing. | India is supported; service age/use restrictions also apply. | India is supported; this does not establish Indian processing residency. |
| 10. SDK maturity | Official Python/JavaScript SDKs, typed schema workflow. | Official unified `google-genai` SDK; use current SDK rather than legacy packages. | Official Python/TypeScript SDKs and schema helpers. |
| 11. Server integration | Good fit for an async Python adapter with bounded retries and Pydantic validation. | Equally feasible behind the same internal contract; provider schema/error differences need an adapter. | Equally feasible; Messages API adapter and explicit output configuration. |
| 12. Multilingual ability | Candidate for multilingual evaluation; English is initial acceptance scope. | Candidate for multilingual evaluation; no project-specific validation. | Candidate for multilingual evaluation; no project-specific validation. |
| 13. Hindi/Hinglish | Unvalidated medical terminology, transliteration and code-switching. | Same; no evidence here that it is superior for this use case. | Same; bilingual review required before enabling. |
| 14. Grounded reliability | Schema constrains shape, not truth. Server evidence checks and evaluation remain necessary. | Same; valid JSON can contain unsupported claims. | Same; citation IDs alone do not prove that prose is supported. |
| 15. Rate limits | Tier/model/project dependent. Terra lists no free tier; published Tier 1 is 500 RPM/500K TPM, not this account's verified entitlement. | Project-based RPM/TPM/RPD and spending-tier controls; actual limits are shown in AI Studio. | Organization/model limits for requests and input/output tokens, with acceleration/spend controls. |
| 16. Free tier/credits | Do not budget for unverified promotional credits; this model has no free usage tier. | Free quota is available, but unpaid data-use terms make it synthetic-only for this work. | No guaranteed free API credit established; budget as paid. Consumer subscriptions are not API credit. |

Capability sources: [OpenAI model](https://developers.openai.com/api/docs/models/gpt-5.6-terra),
[Gemini model](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash),
[Claude models](https://platform.claude.com/docs/en/models/overview).
Schema sources: [OpenAI](https://developers.openai.com/api/docs/guides/structured-outputs),
[Gemini](https://ai.google.dev/gemini-api/docs/structured-output),
[Claude](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).
SDK sources: [OpenAI](https://developers.openai.com/api/docs/libraries),
[Google](https://ai.google.dev/gemini-api/docs/libraries),
[Anthropic](https://platform.claude.com/docs/en/cli-sdks-libraries/overview).
Availability: [OpenAI](https://developers.openai.com/api/docs/supported-countries),
[Google](https://ai.google.dev/gemini-api/docs/available-regions),
[Anthropic](https://www.anthropic.com/supported-countries).
Limits: [OpenAI model tiers](https://developers.openai.com/api/docs/models/gpt-5.6-terra),
[Google limits](https://ai.google.dev/gemini-api/docs/rate-limits),
[Anthropic limits](https://platform.claude.com/docs/en/api/rate-limits).
Privacy/healthcare sources and qualifications follow below.

### Illustrative cost

For **3,000 input + 1,000 billable output tokens per generation**, without cache
discounts, tools or batch processing:

| Candidate | One generation | 1,000 generations |
|---|---:|---:|
| GPT-5.6 Terra | $0.018 | $18 |
| Gemini 3.8 Flash, through December 2026 | $0.006 | $6 |
| Gemini 3.8 Flash, from January 2027 | $0.012 | $12 |
| Claude Sonnet 5 | $0.016 | $16 |

These are arithmetic estimates, not measured costs. Billable output includes
reasoning where applicable; 1,000 visible words/tokens does not imply 1,000 billed
output tokens. Retries, taxes, foreign exchange and special residency pricing are
excluded. Recheck prices when configuring the approved model.
[OpenAI price](https://developers.openai.com/api/docs/models/gpt-5.6-terra),
[Google price](https://ai.google.dev/gemini-api/docs/pricing),
[Anthropic price](https://platform.claude.com/docs/en/about-claude/pricing).

## Privacy and healthcare decision

**OpenAI:** use explicit `store=false` to avoid default Responses storage; this
does not mean zero retention. GPT-5.6 prompt caching can retain encrypted KV state
up to 24 hours; its TTL option controls minimum cache life, not the maximum.
ZDR/MAM requires approval and feature-specific review. India storage is offered
under additional controls, but the table does not promise Indian regional
processing. Do not describe an ordinary API key as a residency or compliance
agreement. [Data controls](https://developers.openai.com/api/docs/guides/your-data).

**Google:** unpaid services may use content for improvement and human review and
must not receive sensitive personal data. Paid services do not use prompts or
responses for product improvement, but retain safety/legal logs and can process
data internationally. Billing does not remove the medical-advice/clinical-practice
restriction. The age restrictions also require review before offering a product
likely to be accessed by under-18s. [Developer terms](https://ai.google.dev/gemini-api/terms).
For a regulated production deployment, assess the exact covered Google Cloud
service, model, region, BAA and retention exceptions separately.
[Google Cloud HIPAA information](https://cloud.google.com/security/compliance/hipaa).

**Anthropic:** default commercial training exclusion is separate from standard
retention and legal/safety exceptions.
[Training policy](https://privacy.claude.com/en/articles/7996868-is-my-data-used-for-model-training),
[retention policy](https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data).
Sonnet's eligible API features and organization-level ZDR/BAA arrangements need
confirmation; a structured-output feature's retention statement is not evidence
that this project's organization has an agreement. Compiled schemas may be cached;
keep health information out of schema property names, enums and constants.
[API data retention](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention),
[structured output privacy](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).

For **any provider**, a US HIPAA covered entity/business associate generally needs
a compliant BAA with a cloud provider processing its ePHI. A BAA alone is
insufficient; deployment safeguards and risk assessment still apply. A personal
health app is not automatically a HIPAA covered entity.
[HHS cloud guidance](https://www.hhs.gov/hipaa/for-professionals/special-topics/health-information-technology/cloud-computing/index.html).
India/GDPR applicability, consent, processor agreements, cross-border processing,
retention and deletion obligations require a deployment-specific assessment.
No HIPAA, GDPR, Indian-law or other automatic compliance is claimed.

Recommendation for this approval: implement and evaluate with synthetic data.
Real production healthcare use remains conditional on the applicable agreements,
privacy notice, retention decision and operational safeguards. Approval of a model
is not a finding that the current application is production compliant.

## Exactly what would leave this server

Proposed first implementation: explain **selected, active, explicitly published
report observations from one authorized report**. Latest review must still be
confirmed/corrected. Exclude manual entries, unreviewed/rejected candidates,
superseded observations, and all other reports. Empty eligible evidence means no
provider call. Publication means user-reviewed data, not clinical verification.

The provider receives a fixed versioned instruction/schema, requested output
language (initially English), and at most 20 structured items with:

- A request-local opaque evidence alias, such as `e1`.
- Reviewed parameter label and available canonical parameter identity.
- Exact raw reported value, its value kind and comparator where present.
- Supplied unit, raw report reference range and printed source flag, including
  explicit missing values rather than inferred replacements.
- Source page number and `calculated_range_status: "unknown"`.

No original PDF/image, complete OCR text, source quote, report date, filename,
patient name, email, DOB, account/report/candidate UUID, storage path, credential,
symptom, medication or unrelated history is needed for this initial scope.
Provenance UUIDs and source spans remain in a server-only alias map; the UI can
resolve authorized source links locally.

Structured authorized context is sufficient for the proposed flow. Raw text or a
source quote would require a separately designed, bounded authorization path;
there is no default fallback that sends the whole report. Field allowlists,
length limits and identifier detection reduce accidental disclosure, but free-text
labels/values can still contain identifying material. This is **data minimization,
not guaranteed anonymization**. Explain the third-party transmission before the
user's explicit Generate action.

The current parser/publication set may represent only part of a report. Label the
result “selected reviewed findings,” not a complete report summary. Current
`ParameterFields.calculated_range_status` permits only `unknown`; preserve
printed flags as attributed source facts and forbid model-computed high/low/normal
claims. No range engine is added under this decision.

## Proposed implementation contract after approval

1. Keep FastAPI session verification, ownership/RLS and JSON/Origin/CSRF checks.
   The server selects evidence; the model gets no SQL, storage, tools or credentials.
2. Build a deterministic bounded snapshot and alias map. Treat all report-derived
   strings as untrusted data, separated from server instructions.
3. Use a fixed health-data-free JSON schema. Return bounded educational items
   referencing aliases and bounded limitations; avoid an unconstrained global
   summary or treatment field. Render source values/ranges from server facts.
4. Reject malformed/incomplete/refused output, unknown or duplicate evidence
   references, and unsupported numeric/source assertions. Validate with Pydantic
   and application rules; do not render provider JSON/errors directly.
   Validation and diagnostic-language checks cannot guarantee prose safety.
5. Revalidate session, report lifecycle and exact evidence revisions after network
   completion and before saving/serving. Never hold report database locks while
   waiting on the provider. Correction/rejection/deletion during generation must
   prevent a stale result becoming current.
6. Prefer one owned explanation-generation record plus bounded evidence references,
   rather than a chat schema. Record provider/model, prompt/schema versions,
   timestamps, evidence revisions, status and operational token/duration metadata.
   Use forced RLS and guarded server writes consistent with Phases 4–6.
7. Propose a maximum 30-day application TTL, at most 20 retained generation records
   per report, immediate invalidation on source change and physical removal with
   report deletion. Expired/stale content must not be served; cleanup must be
   verified before this retention policy is claimed as implemented. App deletion
   cannot retract provider safety logs or override provider retention.
8. Explicit generation only; no dashboard/page-load calls. Reuse only for identical
   owner/evidence revisions/language/provider/model/prompt/schema. Bound concurrent
   duplicate requests with an idempotency key. Do not promise provider exactly-once
   billing after an ambiguous network failure.
9. Proposed initial bounds: 20 facts, 32 KiB serialized context, 4,000 billable
   output-token cap plus stricter response field limits; one in-flight/user and two
   globally, 3 generations/minute/user and 20/day/user. Persist cost-control counters
   across restarts; deployment across workers needs shared enforcement.
10. Start with a 5-second connection and 45-second total budget, at most one clearly
    safe transient retry within that budget. Disable implicit SDK retries; avoid
    automatic retry after uncertain acceptance. Schema/auth/refusal errors do not
    trigger blind paid retries. Log categories/counts/timing, never health prompts,
    responses, values, keys or tokens.

These are reviewable proposals, not existing APIs/tables or proven acceptance
results. Exact schema and lifecycle SQL will be designed and tested after approval.
No Phase 8 trend analysis, Phase 9 chat, streaming or Phase 10 translation UI.

## Server-only environment proposal

After approval, document manual account/project creation, restricted key creation,
budget alerts/limits, retention controls and local secret storage. Do not paste a
key into chat. Do not put it in any `VITE_*` setting.

| Variable | Proposed OpenAI value/purpose |
|---|---|
| `AI_PROVIDER` | `openai`; server allowlist |
| `AI_MODEL` | `gpt-5.6-terra`; server allowlist |
| `AI_API_KEY` | Secret in ignored backend environment or deployment secret store |
| `RUN_AI_INTEGRATION` | Opt-in `1` only for synthetic live evaluation; off by default |

Do not expose a browser-configurable provider URL/model or implement automatic
cross-provider fallback. Gemini/Anthropic selection would change the server adapter
and model value, with the same secret boundary. A Google Cloud alternative would
instead require its own project/location/IAM configuration. Pin SDK versions only
after selection and dependency review. No environment example has been changed yet.

## Evaluation and approval boundary

After approval, implement deterministic mock-only unit tests and opt-in live
synthetic evaluation. Use reproducible cases for decimals, comparators, qualitative
values, titres, missing units/ranges, printed flags and ambiguous labels. Include
13.2/132, 18/80, 2.4/24, <5, >10, 0.4–4.0 and 30–100 corruption traps and malicious
embedded instructions. Record model/prompt/schema versions and outcomes.

Require schema/evidence and exact fact checks, explicit refusal/failure behavior,
plain-English review and human review for unsupported diagnoses, treatment,
alarmism or false certainty. Zero critical errors in the acceptance set is a
release requirement, not proof of zero future risk. Hindi/Hinglish requires a
separate bilingual evaluation; no quality claim is made now.

Test live two-user isolation, revoked sessions, CSRF, concurrent correction,
staleness/regeneration, report deletion and expiry; rerun the Phase 1–6 suites.
Measure real tokens and p50/p95 latency rather than treating marketing labels as
measurements. Use an initial synthetic evaluation budget of at most $5 if approved,
with application-enforced limits in addition to provider budget notifications.

**Requested decision:** approve OpenAI GPT-5.6 Terra, the minimized one-report
context and synthetic-only live evaluation described here, or select an alternative.
Then provide exact manual setup instructions and proceed with Phase 7 implementation.
The user's Section 0 explicitly requires approval before installing/configuring
a provider. Phase 7 remains incomplete until that approval and all implementation
acceptance checks; the final `phase-7-handoff.md` belongs at that later point.
