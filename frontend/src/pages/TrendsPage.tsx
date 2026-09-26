import { useI18n } from '../i18n/core'
import { useCallback, useState } from 'react'
import { ButtonLink } from '../components/Button'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { useHistoryAccount, useOwnedHistory } from '../features/observations/useOwnedHistory'
import { TrendView } from '../features/trends/TrendView'
import { getTrendCatalog } from '../services/trends'
import { metrics } from '../services/observations'

export function TrendsPage() {
  const { t, copy } = useI18n()
  const { owner, authFailure } = useHistoryAccount()
  const load = useCallback((signal: AbortSignal) => getTrendCatalog(owner, signal), [owner])
  const catalog = useOwnedHistory(load, authFailure)
  const [selection, setSelection] = useState(''), [period, setPeriod] = useState<'7d' | '30d'>('7d'), [end, setEnd] = useState('')
  const series = catalog.data?.series ?? []
  const selected = series.find(s => JSON.stringify([s.metric, s.unit]) === selection && s.supported_unit) ?? series.find(s => s.supported_unit)
  return <><PageHeader eyebrow={t("HEALTH TRENDS")} title={t("The picture over time")} description={t("Dated measurements, exact units and deterministic comparisons from your trusted health history.")} />
    <Card className="history-panel"><h2>{t("Your health trends")}</h2>
      {catalog.loading && <p role="status">{t("Loading available metrics…")}</p>}{catalog.error && <p role="alert" className="form-error">{copy(catalog.error)} <button type="button" onClick={catalog.refresh}>{t("Retry loading metrics")}</button></p>}
      {catalog.data && (series.length === 0 ? <><h3>{t("Every trend starts with observations.")}</h3><p>{t("No supported metrics are available yet. Add a manual measurement or explicitly publish a reviewed report value.")}</p></> : <>
        <div className="observation-filters trend-controls"><label><span id="trend-metric-label">{t("Metric and unit")}</span><select aria-labelledby="trend-metric-label" value={selected ? JSON.stringify([selected.metric, selected.unit]) : ''} onChange={event => setSelection(event.target.value)}><option value="" disabled>{t("Choose a supported metric and unit")}</option>{series.map(s => <option key={JSON.stringify([s.metric, s.unit])} value={JSON.stringify([s.metric, s.unit])} disabled={!s.supported_unit}>{copy(metrics.find(([key]) => key === s.metric)?.[1] ?? s.metric)} · {s.unit ?? t("Unit missing")}{!s.supported_unit && t(" (not supported)")}</option>)}</select></label>
          <label><span id="trend-period-label">{t("Period")}</span><select aria-labelledby="trend-period-label" value={period} onChange={event => setPeriod(event.target.value === '30d' ? '30d' : '7d')}><option value="7d">{t("7 days")}</option><option value="30d">{t("30 days")}</option></select></label>
          <label>{t("Period ending (blank for today)")}<input type="date" min="1901-01-01" max={catalog.data.period_end} value={end} onChange={event => setEnd(event.target.value)} /></label></div>
        <p>{"" + t("Manual measurements use your saved timezone:") + " "}{catalog.data.timezone}{t(". Report dates keep their supplied calendar day.")}</p>
        {series.some(s => !s.supported_unit) && <p>{t("Some measurements have missing or unsupported units. They remain unchanged in health history and are excluded from numerical analysis.")}</p>}
      </>)}
      <div className="parameter-actions"><ButtonLink to="/history">{t("Open health history")}</ButtonLink><ButtonLink to="/reports" variant="secondary">{t("Open reports")}</ButtonLink></div>
    </Card>
    {selected?.unit && <TrendView metric={selected.metric} unit={selected.unit} period={period} end={end} />}
    <Card className="history-panel"><h2>{t("Correlations")}</h2><p>{t("No supported correlation pairs are available in the current metric catalog. Sleep and activity are not tracked here, so no pair or association is invented.")}</p><p>{t("Correlation describes an association in the available measurements and does not establish cause and effect.")}</p><p className="form-hint">{t("The bounded method requires at least 14 paired observed days. No correlation is calculated for your current metrics.")}</p></Card>
  </>
}
