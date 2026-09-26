import { useI18n } from '../../i18n/core'
import { lazy, Suspense, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import type { TrendResult, Metric, Period } from '../../services/trends'
import { useTrend } from './useTrend'

const TrendChart = lazy(() => import('./TrendChart'))
const reasons = {
  available: 'Both periods meet the observed-day requirement.',
  no_numeric_observations: 'No eligible numeric observations in this period.',
  current_coverage: 'Not enough observed days in this period to calculate a trend.',
  previous_coverage: 'Not enough observed days in the preceding period to compare.',
  occasional_metric: 'Occasional lab measurements use dated history and latest-versus-previous comparison. No daily tracking or period trend is inferred.',
}
const patterns = {
  consistent_increase: 'Every adjacent observed-day median increased beyond the stated tolerance.',
  consistent_decrease: 'Every adjacent observed-day median decreased beyond the stated tolerance.',
  stable_sequence: 'The observed-day medians stayed within the stated mathematical tolerance.',
  no_clear_pattern: 'No clear consistent direction in these observed-day medians.',
  insufficient_data: 'Not enough observed days to check for a sequence pattern.',
  not_applicable: 'Sequence patterns are not applied to this occasional lab metric.',
}
export function TrendSummary({ result }: { result: TrendResult }) {
  const { t, copy } = useI18n()
  return <><p className="trend-status">{result.status === 'insufficient_data' ? t("Insufficient data for a period trend") : copy(result.status[0]!.toUpperCase() + result.status.slice(1))}</p><p>{copy(reasons[result.reason])}</p>
    {result.change && <p>{"" + t("Period median change:") + " "}<strong>{result.change.absolute} {result.unit}</strong>{result.change.percent !== null && ` (${result.change.percent}%)`}{"" + t(". Classification tolerance:") + " "}{result.tolerance} {result.unit}.</p>}
  </>
}
function PeriodCounts({ period: p, label, unit }: { period: Period; label: string; unit: string }) {
  const { t } = useI18n()
  return <div><dt>{label}: {p.start} – {p.end}</dt><dd>{p.sample_count}{" " + t("measurements ·") + " "}{p.observed_days}{" " + t("observed days")}</dd>{p.coverage_percent !== null && <dd>{p.coverage_percent}{t("% observed-day coverage; no assumed measurements on missing days")}</dd>}{p.median !== null && <dd>{"" + t("Median of daily medians:") + " "}{p.median} {unit}</dd>}{p.first_day && <dd>{"" + t("First / last observed day:") + " "}{p.first_day} / {p.last_day}</dd>}{p.observed_range !== null && <dd>{"" + t("Observed range (max − min):") + " "}{p.observed_range} {unit}</dd>}{p.excluded_count > 0 && <dd>{p.excluded_count}{" " + t("non-scalar measurements excluded")}</dd>}</div>
}
export function TrendView({ metric, unit, period, end }: { metric: Metric; unit: string; period: '7d' | '30d'; end: string }) {
  const { t, copy } = useI18n()
  const state = useTrend(metric, unit, period, end)
  const result = state.data
  const points = useMemo(() => result?.points.filter(p => p.day >= result.current.start && p.day <= result.current.end) ?? [], [result])
  const latest = result?.latest_comparison
  return <Card className="history-panel"><div className="card-heading"><h2>{t("Measurement changes")}</h2><Button variant="ghost" size="sm" onClick={state.refresh}>{t("Refresh trends")}</Button></div>
    {state.loading && <p role="status">{t("Loading your trends…")}</p>}{state.error && <p role="alert" className="form-error">{copy(state.error)}</p>}
    {result && <div aria-label={t("Trend results")}><p>{result.current.start}{" " + t("through") + " "}{result.current.end} · {result.timezone}{result.partial_end_day && t(" · Today includes measurements so far")}</p><TrendSummary result={result} />
      <dl className="trend-counts"><PeriodCounts period={result.current} label={t("Current period")} unit={unit} /><PeriodCounts period={result.previous} label={t("Previous period")} unit={unit} /></dl>
      {result.mode === 'frequent' && <p>{"" + t("Period comparisons need at least") + " "}{result.minimum_days}{" " + t("observed days in each period. Each day contributes its median; the period summary is the median of those daily medians.")}</p>}
      {points.length ? <><Suspense fallback={<p role="status">{t("Loading measurement chart…")}</p>}><TrendChart points={points} unit={unit} start={result.current.start} end={result.current.end} /></Suspense><p className="form-hint">{t("Only actual observations are plotted, grouped by calendar day. Same-day points can overlap; every point remains in the table. No connecting line, interpolation or outlier removal.")}</p></> : <p>{t("No dated numeric measurements to plot in this period.")}</p>}
      <h3>{t("Latest versus previous measurement")}</h3>
      {latest?.latest && <p>{"" + t("Latest:") + " "}<strong>{latest.latest.raw_value} {unit}</strong> · {latest.latest.day}</p>}
      {latest?.previous && <p>{"" + t("Previous:") + " "}<strong>{latest.previous.raw_value} {unit}</strong> · {latest.previous.day}</p>}
      {latest?.change && <p>{"" + t("Change:") + " "}{latest.change.absolute} {unit}{latest.change.percent !== null ? ` (${latest.change.percent}%)` : t(". Percentage is unavailable for a nonpositive previous value.")}</p>}
      {latest?.reason === 'no_dated_numeric_data' && <p>{t("No dated numeric measurements in the bounded history.")}</p>}
      {latest?.reason === 'fewer_than_two_days' && <p>{t("At least two distinct measurement days are needed for this comparison.")}</p>}
      {latest?.reason === 'ambiguous_same_day' && <p>{t("Multiple measurements on a latest or previous day make the comparison ambiguous. All observations are retained; none is chosen arbitrarily.")}</p>}
      <p>{"" + t("Latest comparison uses") + " "}{result.history_start}{" " + t("through") + " "}{result.current.end}{"" + t(". Older history remains available in") + " "}<Link to={`/history?metric=${metric}`}>{t("health history")}</Link>.</p>
      <h3>{t("Observed sequence")}</h3><p>{copy(patterns[result.pattern])}</p>
      <p>{result.unknown_date_count}{" " + t("measurements with unknown dates are excluded.") + " "}{result.excluded_history_count}{" " + t("non-scalar measurements are excluded from the bounded numeric history.")}</p>
      <details className="trend-data"><summary>{t("Exact measurement table (")}{result.points.length}{" " + t("observations)")}</summary><div className="trend-table-scroll" tabIndex={0} role="region" aria-label={t("Scrollable exact measurement table")}><table><caption>{"" + t("Active dated observations only ·") + " "}{result.history_start}{" " + t("to") + " "}{result.current.end} · {result.timezone}</caption><thead><tr><th scope="col">{t("Measurement day / time")}</th><th scope="col">{t("Value")}</th><th scope="col">{t("Source")}</th><th scope="col">{t("Revision")}</th></tr></thead><tbody>{result.points.map(p => <tr key={p.observation_id}><td>{p.day}<br />{p.measured_at ? new Intl.DateTimeFormat('en-GB', { timeZone: result.timezone, hour: '2-digit', minute: '2-digit', second: '2-digit', timeZoneName: 'short' }).format(new Date(p.measured_at)) : t("Day only, supplied by you")}</td><td>{p.raw_value} {p.unit}</td><td><Link to={`/history?metric=${metric}${p.report_id ? `&report_id=${p.report_id}` : '&source_type=manual'}`}>{p.source_type === 'report' ? t("Published report") : t("Manual entry")}</Link><br /><small>{"" + t("Observation") + " "}{p.observation_id}</small></td><td>{p.revision}{p.review_revision !== null && t(" · review {p0}", { p0: p.review_revision })}</td></tr>)}</tbody></table></div></details>
      <p className="form-hint">{"" + t("Mathematical summaries only. Stable does not mean healthy, normal or safe; increasing and decreasing do not imply worsening or improvement. Measurement conditions and lab assays may differ. Percentages are derived and rounded to six decimal places. Rules:") + " "}{result.rules_version}.</p>
    </div>}
  </Card>
}
export function DashboardTrend() {
  const { t } = useI18n()
  const state = useTrend('weight', 'kg', '7d', '')
  if (!state.data || state.data.status === 'insufficient_data') return null
  return <Card className="history-panel"><h2>{t("Weight · seven-day comparison")}</h2><TrendSummary result={state.data} /><p>{state.data.current.sample_count}{" " + t("current measurements and") + " "}{state.data.previous.sample_count}{" " + t("preceding measurements. These are mathematical changes, not medical judgments.")}</p><Link to="/trends">{t("Explore measurements and calculation rules")}</Link></Card>
}
