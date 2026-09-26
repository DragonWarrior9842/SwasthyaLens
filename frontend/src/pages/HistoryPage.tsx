import { useI18n } from '../i18n/core'
import { useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Button, ButtonLink } from '../components/Button'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { ManualForm, ObservationCard } from '../features/observations/ObservationCard'
import { useHistoryAccount, useOwnedHistory } from '../features/observations/useOwnedHistory'
import { listObservations, metrics } from '../services/observations'

export function HistoryPage() {
  const { t, copy } = useI18n()
  const { owner, authFailure } = useHistoryAccount()
  const [params, setParams] = useSearchParams(), query = params.toString()
  const load = useCallback((signal: AbortSignal) => listObservations(query, owner, signal), [query, owner])
  const history = useOwnedHistory(load, authFailure)
  return <><PageHeader eyebrow={t("HEALTH HISTORY")} title={t("Your health history")} description={t("Measurements you entered and report values you explicitly published after personal review.")} />
    <div className="history-workspace"><Card className="history-panel"><ManualForm owner={owner} authFailure={authFailure} onChange={history.refresh} /></Card><Card className="history-panel">
      <div className="card-heading"><h2>{t("Observations")}</h2><Button variant="ghost" size="sm" onClick={history.refresh}>{t("Refresh history")}</Button></div>
      <p>{t("Known measurement days appear first, newest day first. Entries without a measurement date follow, ordered by time recorded. Times are shown in UTC; values and units are never combined.")}</p>
      <form key={query} className="observation-filters" onSubmit={event => { event.preventDefault(); const data = new FormData(event.currentTarget), next = new URLSearchParams(); for (const [key, value] of data) if (String(value)) next.set(key, String(value)); if (params.get('report_id')) next.set('report_id', params.get('report_id')!); setParams(next) }}>
        <label>{t("Metric")}<select name="metric" defaultValue={params.get('metric') ?? ''}><option value="">{t("All metrics, including unmapped")}</option>{metrics.map(([id, label]) => <option key={id} value={id}>{copy(label)}</option>)}</select></label>
        <label>{t("Source")}<select name="source_type" defaultValue={params.get('source_type') ?? ''}><option value="">{t("All sources")}</option><option value="report">{t("From report")}</option><option value="manual">{t("Manually entered")}</option></select></label>
        <label>{t("Measurement from")}<input type="date" name="date_from" defaultValue={params.get('date_from') ?? ''} /></label><label>{t("Measurement through")}<input type="date" name="date_to" defaultValue={params.get('date_to') ?? ''} /></label>
        <label><input type="checkbox" name="include_inactive" value="true" defaultChecked={params.get('include_inactive') === 'true'} />{" " + t("Include inactive observations")}</label><Button size="sm" type="submit">{t("Apply filters")}</Button><Button size="sm" variant="ghost" onClick={() => setParams({})}>{t("Clear filters")}</Button>
      </form>
      {params.has('report_id') && <p>{t("Showing observations linked to the selected report.")}</p>}
      {history.loading && <p role="status">{t("Loading health history…")}</p>}{history.error && <p role="alert" className="form-error">{copy(history.error)}</p>}
      {history.data?.items.length === 0 && <p>{t("No observations match this view. Upload and review a report or add a supported measurement.")}</p>}
      {history.data?.items.map(observation => <ObservationCard key={`${observation.id}-${observation.current.revision}-${observation.current.status}`} observation={observation} owner={owner} authFailure={authFailure} onChange={history.refresh} />)}
      <div className="parameter-actions">{params.has('offset') && <Button variant="ghost" onClick={() => { const next = new URLSearchParams(params); next.delete('offset'); setParams(next) }}>{t("First page")}</Button>}{history.data?.next_offset != null && <Button variant="secondary" onClick={() => { const next = new URLSearchParams(params); next.set('offset', String(history.data!.next_offset)); setParams(next) }}>{t("Next observations")}</Button>}</div>
      <ButtonLink to="/reports" variant="ghost">{t("Open reports")}</ButtonLink>
    </Card></div></>
}
