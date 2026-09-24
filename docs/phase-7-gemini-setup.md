# Phase 7 Gemini Free Tier — manual setup gate

Checked 24 September 2026. Scope: the existing synthetic educational acceptance
tests only, using **Gemini 3.8 Flash / `gemini-3.8-flash`**. No production healthcare
provider choice is made. The adapter is implemented and tested offline; no live Gemini request has been
made. Setup is confirmed; actual numeric RPM/TPM/RPD are still required. All further OpenAI live requests are stopped by the owner.

## Why this candidate

Google lists this model with free standard input/output tokens and structured
outputs. India is an available region. Actual account access and quota remain
unverified. [Model](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash),
[pricing](https://ai.google.dev/gemini-api/docs/pricing),
[regions](https://ai.google.dev/gemini-api/docs/available-regions).

**Gemini Free Tier may use submitted data and responses to improve Google
products, including machine learning; human reviewers may process them.** Do not
submit personal, confidential or real patient data. Google prohibits clinical
practice and medical advice through these services. Our scope remains internal
synthetic fixtures and fixed informational wording, without diagnosis or treatment.
Free Tier does not establish zero retention, India-only processing or healthcare
compliance. [Terms](https://ai.google.dev/gemini-api/terms).

## Exact manual steps

1. Sign in to [Google AI Studio](https://aistudio.google.com/) with an eligible
   adult Google account and review/accept the developer terms. Do not upload a
   report or submit a Playground prompt as part of setup.
2. Use a dedicated Cloud project named, for example, `swasthyalens-phase7-synthetic`.
   In AI Studio, open **Dashboard → Projects**. A new user's default project is
   suitable if unused and unbilled; otherwise create a separate unbilled project
   in [Google Cloud](https://console.cloud.google.com/projectcreate), then use
   **Import projects** in AI Studio to select it.
3. Open **Dashboard → API Keys**, choose **Create API key**, and select that
   dedicated project. Use a newly generated AI Studio authorization key, which is
   restricted to the Generative Language API by default. Do not reuse a legacy
   standard key or give the key to the frontend.
   [Key and project instructions](https://ai.google.dev/gemini-api/docs/api-key).
4. Verify the selected project shows **Free Tier** in AI Studio's **Billing Tier**
   column and has **no linked Cloud Billing account**. Do not click **Set up
   billing**, add prepaid credit, enable auto-reload or select a paid project.
   Confirm the key belongs to this exact project. A paid project showing **No
   credits** does not meet this requirement.
   [Billing status](https://ai.google.dev/gemini-api/docs/billing).
5. In AI Studio's **Usage / Rate limits** view, select that project and locate
   `gemini-3.8-flash`. Record the displayed RPM, TPM and RPD and confirm nonzero
   access for the planned two requests. Quota is project-specific; a model listing
   is not proof your account can call it. If unavailable or billing is required,
   stop and report that state; do not upgrade or substitute another model.
   [Active-limit instructions](https://ai.google.dev/gemini-api/docs/rate-limits).
6. Save the key locally using the staging configuration below. Reply that setup
   is complete, the project is Free Tier with billing unlinked, and give only the
   displayed RPM/TPM/RPD. Never paste the key, a key-bearing screenshot or an env
   file into chat. **Do not run a live command yet.**

## Exact local environment configuration

Use **`backend/.env.ai.gemini`** (ignored by the existing `.env.*` rule).
The implemented Gemini loader reads this file separately from the dormant OpenAI
`backend/.env.ai`. The file alone never enables live requests.

```dotenv
AI_PROVIDER=gemini
AI_MODEL=gemini-3.8-flash
AI_API_KEY=
```

Enter the newly created Gemini key after `AI_API_KEY=` locally. These three
application variables are the implemented integration contract. No `VITE_*`,
`GEMINI_API_KEY`, `GOOGLE_API_KEY`, Vertex/ADC credentials or provider URL variable
is needed for this application. The adapter passes this key explicitly in the
`x-goog-api-key` header, never in a URL or prompt. Existing Supabase/backend
configuration is unchanged and is never exposed to the model.

Keep the process live flag **unset** during setup and normal testing. If a current
PowerShell session has it set, clear it without printing any credentials:

```powershell
Remove-Item Env:RUN_AI_INTEGRATION -ErrorAction SilentlyContinue
```

The evaluator requires **both** the process flag `RUN_AI_INTEGRATION=1` and
`--live-gemini`. Do not put the flag in either env file. The old `--live-openai`
command rejects before network; the dormant adapter also blocks real transport.
There is no environment setting that controls Google's billing tier.

After actual project limits are supplied and preflight safeguards are reported,
run from `backend` with the live flag scoped only to that process:

```text
python -m tests.evaluate_explanations --live-gemini --free-tier-confirmed --gemini-rpm RPM --gemini-tpm TPM --gemini-rpd RPD
```

RPM/TPM/RPD must be the displayed **integers**, not guessed values. Current
conservative minimums are 1 RPM, 57000 TPM and 2 RPD: the TPM allowance covers the
full 48-KB request, 5K framing and 4K output caps. Lower quotas require a separately
assessed smaller bound; never inflate the arguments or upgrade billing. Two fixture
requests are spaced at least 61 seconds apart and any failure stops the run.
Clear the process flag in `finally` after evaluation. No live call is authorized
by this template alone; the owner's current request authorizes the scoped test
once the required missing quota inputs and preflight are resolved.

## Controls that must pass before the first live request

- Separate Gemini adapter behind the existing provider protocol; dormant OpenAI
  adapter and `store=false` behavior retained, with no fallback to it.
- Schema-constrained output plus the unchanged strict evidence/fact validator;
  same opaque IDs, exact strings, provenance and closed educational vocabulary.
- Server-selected authorized reviewed/published facts from one newly generated
  enrolled synthetic report only. No personal files or arbitrary report IDs.
- No tools, searches, code, URL retrieval, provider file uploads, cached-content
  resources, database/storage credentials, raw pages or conversation state.
- Existing bounded context, timeouts, no automatic retries, explicit consent,
  session/RLS/CSRF/isolation, invalidation and deletion controls retained.
- Mock-only normal tests block both provider network hosts. Separate live opt-in,
  durable Gemini attempt limits and verified unbilled project configuration.
- Re-report these checks before live evaluation. Existing OpenAI reservations stay
  at $0.50 of $5; Gemini paid spend is not authorized. Quota failure stops the run.

Gemini's stateless `generateContent` API is implemented. The current API reference
documents request-level `store`; the adapter explicitly sets it to `false`. This
corrects the earlier setup note and does not remove unpaid-service data-use terms
or establish zero retention.
[API reference](https://ai.google.dev/api/generate-content).

No live Gemini call has occurred. The remaining setup input is actual quota numbers. Phase 7 acceptance stays
pending; Phase 8 has not started.
