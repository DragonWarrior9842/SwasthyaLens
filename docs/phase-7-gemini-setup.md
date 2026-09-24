# Phase 7 Gemini Free Tier — manual setup gate

Checked 24 September 2026. Scope: the existing synthetic educational acceptance
tests only, using **Gemini 3.8 Flash / `gemini-3.8-flash`**. No production healthcare
provider choice is made. No Gemini adapter is installed yet and no live Gemini
request has been made. All further OpenAI live requests are stopped by the owner.

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

Prepare **`backend/.env.ai.gemini`** in your editor (ignored by the existing
`.env.*` rule). This separate staging file prevents the current OpenAI-only
settings loader from receiving unsupported Gemini values. Leave the existing
`backend/.env.ai` unchanged for now. The future Gemini adapter will explicitly
load the staged settings after implementation and validation; the file alone
does not enable anything today.

```dotenv
AI_PROVIDER=gemini
AI_MODEL=gemini-3.8-flash
AI_API_KEY=
```

Enter the newly created Gemini key after `AI_API_KEY=` locally. These three
application variables are the proposed integration contract. No `VITE_*`,
`GEMINI_API_KEY`, `GOOGLE_API_KEY`, Vertex/ADC credentials or provider URL variable
is needed for this application. The adapter will pass this key explicitly in the
`x-goog-api-key` header, never in a URL or prompt. Existing Supabase/backend
configuration is unchanged and is never exposed to the model.

Keep the process live flag **unset** during setup and normal testing. If a current
PowerShell session has it set, clear it without printing any credentials:

```powershell
Remove-Item Env:RUN_AI_INTEGRATION -ErrorAction SilentlyContinue
```

Later, the evaluator will require **both** the process variable
`RUN_AI_INTEGRATION=1` and an explicit Gemini-only live command. Do not put the flag
in either env file. The new command is not implemented yet, so no executable live
command is provided at this setup gate. The old `--live-openai` command must not
be used. There is no `FREE_TIER=true` key or setting that controls Google's
billing tier: that belongs to the selected Cloud project.

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

Gemini's stateless `generateContent` API is the proposed transport. Its request
contract has no documented `store=false` equivalent; no zero-retention claim is
made and Google's unpaid data terms still apply.
[API reference](https://ai.google.dev/api/generate-content).

This is the requested stop before any live Gemini call. Phase 7 acceptance stays
pending; Phase 8 has not started.
