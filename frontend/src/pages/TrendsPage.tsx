import { useCallback, useState } from 'react'
import { ButtonLink } from '../components/Button'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { useHistoryAccount, useOwnedHistory } from '../features/observations/useOwnedHistory'
import { TrendView } from '../features/trends/TrendView'
import { getTrendCatalog } from '../services/trends'
import { metrics } from '../services/observations'

export function TrendsPage() {
  const { owner, authFailure } = useHistoryAccount()
  const load = useCallback((signal: AbortSignal) => getTrendCatalog(owner, signal), [owner])
  const catalog = useOwnedHistory(load, authFailure)
  const [selection, setSelection] = useState(''), [period, setPeriod] = useState<'7d' | '30d'>('7d'), [end, setEnd] = useState('')
  const series = catalog.data?.series ?? []
  const selected = series.find(s => JSON.stringify([s.metric, s.unit]) === selection && s.supported_unit) ?? series.find(s => s.supported_unit)
  return <><PageHeader eyebrow="HEALTH TRENDS" title="The picture over time" description="Dated measurements, exact units and deterministic comparisons from your trusted health history." />
    <Card className="history-panel"><h2>Your health trends</h2>
      {catalog.loading && <p role="status">Loading available metrics…</p>}{catalog.error && <p role="alert" className="form-error">{catalog.error} <button type="button" onClick={catalog.refresh}>Retry loading metrics</button></p>}
      {catalog.data && (series.length === 0 ? <><h3>Every trend starts with observations.</h3><p>No supported metrics are available yet. Add a manual measurement or explicitly publish a reviewed report value.</p></> : <>
        <div className="observation-filters trend-controls"><label>Metric and unit<select value={selected ? JSON.stringify([selected.metric, selected.unit]) : ''} onChange={event => setSelection(event.target.value)}><option value="" disabled>Choose a supported metric and unit</option>{series.map(s => <option key={JSON.stringify([s.metric, s.unit])} value={JSON.stringify([s.metric, s.unit])} disabled={!s.supported_unit}>{metrics.find(([key]) => key === s.metric)?.[1]} · {s.unit ?? 'Unit missing'}{!s.supported_unit && ' (not supported)'}</option>)}</select></label>
          <label>Period<select value={period} onChange={event => setPeriod(event.target.value === '30d' ? '30d' : '7d')}><option value="7d">7 days</option><option value="30d">30 days</option></select></label>
          <label>Period ending (blank for today)<input type="date" min="1901-01-01" max={catalog.data.period_end} value={end} onChange={event => setEnd(event.target.value)} /></label></div>
        <p>Manual measurements use your saved timezone: {catalog.data.timezone}. Report dates keep their supplied calendar day.</p>
        {series.some(s => !s.supported_unit) && <p>Some measurements have missing or unsupported units. They remain unchanged in health history and are excluded from numerical analysis.</p>}
      </>)}
      <div className="parameter-actions"><ButtonLink to="/history">Open health history</ButtonLink><ButtonLink to="/reports" variant="secondary">Open reports</ButtonLink></div>
    </Card>
    {selected?.unit && <TrendView metric={selected.metric} unit={selected.unit} period={period} end={end} />}
    <Card className="history-panel"><h2>Correlations</h2><p>No supported correlation pairs are available in the current metric catalog. Sleep and activity are not tracked here, so no pair or association is invented.</p><p>Correlation describes an association in the available measurements and does not establish cause and effect.</p><p className="form-hint">The bounded method requires at least 14 paired observed days. No correlation is calculated for your current metrics.</p></Card>
  </>
}
