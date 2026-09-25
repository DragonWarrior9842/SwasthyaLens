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
  return <><p className="trend-status">{result.status === 'insufficient_data' ? 'Insufficient data for a period trend' : result.status[0]!.toUpperCase() + result.status.slice(1)}</p><p>{reasons[result.reason]}</p>
    {result.change && <p>Period median change: <strong>{result.change.absolute} {result.unit}</strong>{result.change.percent !== null && ` (${result.change.percent}%)`}. Classification tolerance: {result.tolerance} {result.unit}.</p>}
  </>
}
function PeriodCounts({ period: p, label, unit }: { period: Period; label: string; unit: string }) {
  return <div><dt>{label}: {p.start} – {p.end}</dt><dd>{p.sample_count} measurements · {p.observed_days} observed days</dd>{p.coverage_percent !== null && <dd>{p.coverage_percent}% observed-day coverage; no assumed measurements on missing days</dd>}{p.median !== null && <dd>Median of daily medians: {p.median} {unit}</dd>}{p.first_day && <dd>First / last observed day: {p.first_day} / {p.last_day}</dd>}{p.observed_range !== null && <dd>Observed range (max − min): {p.observed_range} {unit}</dd>}{p.excluded_count > 0 && <dd>{p.excluded_count} non-scalar measurements excluded</dd>}</div>
}
export function TrendView({ metric, unit, period, end }: { metric: Metric; unit: string; period: '7d' | '30d'; end: string }) {
  const state = useTrend(metric, unit, period, end)
  const result = state.data
  const points = useMemo(() => result?.points.filter(p => p.day >= result.current.start && p.day <= result.current.end) ?? [], [result])
  const latest = result?.latest_comparison
  return <Card className="history-panel"><div className="card-heading"><h2>Measurement changes</h2><Button variant="ghost" size="sm" onClick={state.refresh}>Refresh trends</Button></div>
    {state.loading && <p role="status">Loading your trends…</p>}{state.error && <p role="alert" className="form-error">{state.error}</p>}
    {result && <div aria-label="Trend results"><p>{result.current.start} through {result.current.end} · {result.timezone}{result.partial_end_day && ' · Today includes measurements so far'}</p><TrendSummary result={result} />
      <dl className="trend-counts"><PeriodCounts period={result.current} label="Current period" unit={unit} /><PeriodCounts period={result.previous} label="Previous period" unit={unit} /></dl>
      {result.mode === 'frequent' && <p>Period comparisons need at least {result.minimum_days} observed days in each period. Each day contributes its median; the period summary is the median of those daily medians.</p>}
      {points.length ? <><Suspense fallback={<p role="status">Loading measurement chart…</p>}><TrendChart points={points} unit={unit} start={result.current.start} end={result.current.end} /></Suspense><p className="form-hint">Only actual observations are plotted, grouped by calendar day. Same-day points can overlap; every point remains in the table. No connecting line, interpolation or outlier removal.</p></> : <p>No dated numeric measurements to plot in this period.</p>}
      <h3>Latest versus previous measurement</h3>
      {latest?.latest && <p>Latest: <strong>{latest.latest.raw_value} {unit}</strong> · {latest.latest.day}</p>}
      {latest?.previous && <p>Previous: <strong>{latest.previous.raw_value} {unit}</strong> · {latest.previous.day}</p>}
      {latest?.change && <p>Change: {latest.change.absolute} {unit}{latest.change.percent !== null ? ` (${latest.change.percent}%)` : '. Percentage is unavailable for a nonpositive previous value.'}</p>}
      {latest?.reason === 'no_dated_numeric_data' && <p>No dated numeric measurements in the bounded history.</p>}
      {latest?.reason === 'fewer_than_two_days' && <p>At least two distinct measurement days are needed for this comparison.</p>}
      {latest?.reason === 'ambiguous_same_day' && <p>Multiple measurements on a latest or previous day make the comparison ambiguous. All observations are retained; none is chosen arbitrarily.</p>}
      <p>Latest comparison uses {result.history_start} through {result.current.end}. Older history remains available in <Link to={`/history?metric=${metric}`}>health history</Link>.</p>
      <h3>Observed sequence</h3><p>{patterns[result.pattern]}</p>
      <p>{result.unknown_date_count} measurements with unknown dates are excluded. {result.excluded_history_count} non-scalar measurements are excluded from the bounded numeric history.</p>
      <details className="trend-data"><summary>Exact measurement table ({result.points.length} observations)</summary><div className="trend-table-scroll" tabIndex={0} role="region" aria-label="Scrollable exact measurement table"><table><caption>Active dated observations only · {result.history_start} to {result.current.end} · {result.timezone}</caption><thead><tr><th scope="col">Measurement day / time</th><th scope="col">Value</th><th scope="col">Source</th><th scope="col">Revision</th></tr></thead><tbody>{result.points.map(p => <tr key={p.observation_id}><td>{p.day}<br />{p.measured_at ? new Intl.DateTimeFormat('en-GB', { timeZone: result.timezone, hour: '2-digit', minute: '2-digit', second: '2-digit', timeZoneName: 'short' }).format(new Date(p.measured_at)) : 'Day only, supplied by you'}</td><td>{p.raw_value} {p.unit}</td><td><Link to={`/history?metric=${metric}${p.report_id ? `&report_id=${p.report_id}` : '&source_type=manual'}`}>{p.source_type === 'report' ? 'Published report' : 'Manual entry'}</Link><br /><small>Observation {p.observation_id}</small></td><td>{p.revision}{p.review_revision !== null && ` · review ${p.review_revision}`}</td></tr>)}</tbody></table></div></details>
      <p className="form-hint">Mathematical summaries only. Stable does not mean healthy, normal or safe; increasing and decreasing do not imply worsening or improvement. Measurement conditions and lab assays may differ. Percentages are derived and rounded to six decimal places. Rules: {result.rules_version}.</p>
    </div>}
  </Card>
}
export function DashboardTrend() {
  const state = useTrend('weight', 'kg', '7d', '')
  if (!state.data || state.data.status === 'insufficient_data') return null
  return <Card className="history-panel"><h2>Weight · seven-day comparison</h2><TrendSummary result={state.data} /><p>{state.data.current.sample_count} current measurements and {state.data.previous.sample_count} preceding measurements. These are mathematical changes, not medical judgments.</p><Link to="/trends">Explore measurements and calculation rules</Link></Card>
}
