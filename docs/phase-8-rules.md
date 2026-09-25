# Phase 8 deterministic analysis decision

25 September 2026. This decision precedes implementation of the calculations.
Phase 8 is independent of Phase 7. Its external Gemini availability blocker,
2/20 attempt ledger, disabled integration flag and provider configuration are unchanged.
No AI, ML, external medical reference data or new health metrics are part of this phase.

## Inputs and eligibility

Only the current active Phase 6 observation revision is an input. Report observations
must still belong to an uploaded report owned by the authenticated account. No OCR,
candidate, review text or generated explanation is an analysis input. Provenance points
to observation/revision and report/candidate IDs; history retains the complete source.

An eligible scalar has `value_kind=numeric`, no comparator (including `=`), no qualitative
result, a bounded finite decimal string, and a matching scalar raw value. Qualitative,
titre, interval, ordinal, unparsed, missing and comparator values remain in history.
Unknown measurement dates are counted separately and never assigned an upload/creation date.

The versioned allowlist is deliberately small:

| Metric | Exact supported unit spellings, kept separate | Analysis |
| --- | --- | --- |
| weight | kg | Frequent measurements |
| heart_rate | bpm | Frequent measurements; measurement conditions remain unspecified |
| hemoglobin | g/dL, g/L | Occasional laboratory history |
| tsh | mIU/L, uIU/mL, µIU/mL | Occasional laboratory history |
| vitamin_d_unspecified | ng/mL, nmol/L | Occasional laboratory history; assay unspecified |
| glucose_unspecified | mg/dL, mmol/L | Occasional laboratory history; timing/conditions unspecified |
| crp | mg/L, mg/dL | Occasional laboratory history |

Exact unit equality is required. No unit conversion, case folding, unit substitution,
assay equivalence or clinical comparability is inferred. Missing/other units are not
numerically analyzed. These are technical grouping rules, not medical interpretation.

## Dates, periods and duplicates

The saved IANA account timezone determines manual measurement calendar days. A report's
explicit day stays that day, with no invented instant. The default period ends on today's
local day, includes measurements so far, and is marked as a partial current day. An
explicit historical end day is supported; future end days are rejected.

For end day E and W=7 or 30, current dates are [E-W+1, E], and preceding dates are
[E-2W+1, E-W]. For manual instants, local midnight boundaries are converted to UTC;
intervals are half-open and additionally capped at the captured request time. Thus DST
days need not be 24 hours. Unknown dates and future instants do not enter these windows.

All distinct observations are retained, including identical values/timestamps. Sorting
uses measurement day, actual instant where available, then opaque observation ID only
for deterministic display. An ID tie-break never establishes a latest measurement.
Latest-versus-previous requires two unambiguous measurement times on separate days;
same-day duplicates or day-only timing ambiguity at either selected day return a reason
instead of an arbitrary comparison. Earlier ambiguous days are not skipped to find a
more convenient comparison.

## Aggregates, thresholds and patterns

For weight and heart rate, compute each observed day's median, then the median of
those daily medians. Days receive equal weight; missing days are not filled. These
are descriptive summaries of submitted measurements, not daily monitoring or resting
heart-rate estimates. Both periods need at least ceil(W/2) observed days: 4 for seven
days, 15 for thirty days. Counts and observed-day coverage are distinct.

The classification compares current and previous period medians. The absolute
tolerance is max(1% of the absolute previous median, technical floor). Floors are
0.1 kg and 1 bpm. Absolute delta within or equal to tolerance is `stable`; a larger
positive/negative delta is `increasing`/`decreasing`. These deliberately conservative
display tolerances are mathematical, not clinical thresholds. Stable does not mean
healthy, normal or safe; increasing/decreasing does not mean worse/better.

With sufficient current observed days, a sequence is consistently increasing/decreasing
only if EVERY adjacent daily median exceeds its corresponding tolerance in that
direction. A sequence is stable only if its entire range fits the tolerance around
its median. Otherwise return `no_clear_pattern`. Below minimum coverage return
`insufficient_data`. Report the exact observed scalar range (max minus min) when at
least two observations exist; give it no medical/high-variability label. No outliers
are deleted, no smoothing/interpolation is performed and no lag search is used.

Laboratory metrics have counts and dated points in each window, but no daily-coverage
percentage, period median or period trend classification. Their latest-versus-previous
comparison looks back at most 366 calendar days ending at E. It shows dates, exact
values, absolute delta and percentage only when the previous value is positive.
It does not manufacture a seven/thirty-day trend from tests months apart.

Input values and differences use Decimal. Medians are exact; percentages are rounded
to six decimal places using half-even rounding and labeled as derived values. Input
decimal spelling, units and provenance remain intact. Binary numbers are used only
for chart positioning, never for authoritative calculations or exact-value text.

## Correlation boundary

The existing catalog has no sleep or activity metric. None of the proposed pairs
(sleep/glucose, activity/glucose, weight/activity) is available. The enabled pair
registry is therefore empty; the product reports `unsupported_catalog` and displays
no invented association, score or pair. Adding a pair requires a later explicit
product decision and compatible catalog support.

The bounded statistical primitive may be tested with dimensionless synthetic fixtures:
same-calendar-day medians, inner join on dates, at least 14 paired days spanning at
least 14 calendar days, Pearson correlation, no missing-value imputation or lag scan.
Constant series return `constant_series`; fewer pairs return `insufficient_data`.
No strength/clinical label is assigned. This primitive does not enable a product pair.
The UI states: “Correlation describes an association in the available measurements
and does not establish cause and effect.”

## Query, UI and freshness decisions

Compute on demand with a reusable pure analysis service. Add no derived tables or
snapshots. A stable invoker RPC reads saved timezone and active owned observations
under existing RLS/session controls. There is no authoritative client user ID.
Read only the selected metric and exact unit: at most two windows for frequent metrics,
or the explicit 366-day laboratory history. At most 500 observations; a 501st row
causes a truthful capacity error, never partial statistics. Catalog groups are bounded.

The Trends page provides metric/unit selection, seven/thirty-day windows, historical
end date, sample counts, earliest/latest dates, exact-value table, source links, neutral
summaries and loading/empty/insufficient/error/session states. Dashboard indicators use
the same engine and appear only with sufficient period coverage.

No chart package existed. Choose pinned Chart.js 4.5.1 with only scatter controller,
point element, linear scales and tooltip, loaded for the Trends view. Do not import
the full automatic registry or a React wrapper. Real points only; overlapping points
remain separate table rows. Canvas has an accessible name and an adjacent text/table
alternative, as required by [Chart.js accessibility](https://www.chartjs.org/docs/latest/general/accessibility.html).
[Selective imports](https://www.chartjs.org/docs/latest/getting-started/integration.html)
limit the bundle; no additional date adapter is needed for a calendar-day axis.

Responses are no-store and health data stays in React memory. Source mutation events
invalidate local and other-tab views; request cancellation and identity binding discard
old responses. Focus/visibility/explicit refresh and periodic refresh handle external
changes and day rollover. No generated explanation or AI endpoint is involved.

## Baseline gate

Before application changes: frontend lint/typecheck/216 tests/build; backend Ruff,
format (81 files), mypy (78 files), 376 tests with real local OCR (eight opt-in live
tests skipped in that invocation); eight real Supabase integration tests (424.47 s);
all fourteen rollback SQL verification scripts passed. Two upstream deprecation
warnings remain. Sandbox cache/runtime checks were rerun with authorized access.
Browser verification is being completed; failures/retries will be recorded in the handoff.
