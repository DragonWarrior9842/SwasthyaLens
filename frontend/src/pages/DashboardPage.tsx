import { useI18n } from '../i18n/core'
import { useCallback } from 'react'
import { Link } from 'react-router-dom'
import { Button, ButtonLink } from '../components/Button'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { useHistoryAccount, useOwnedHistory } from '../features/observations/useOwnedHistory'
import { getDashboard, measurementLabel } from '../services/observations'
import { DashboardTrend } from '../features/trends/TrendView'

export function DashboardPage() {
  const { t, copy, locale } = useI18n()
  const { owner, authFailure } = useHistoryAccount()
  const load = useCallback((signal: AbortSignal) => getDashboard(owner, signal), [owner])
  const overview = useOwnedHistory(load, authFailure)
  return <><PageHeader eyebrow={t("YOUR HEALTH, IN CONTEXT")} title={t("Your health overview")} description={t("Your private reports and personally reviewed health history.")} />
    <Card className="history-panel"><div className="card-heading"><h2>{t("My health at a glance")}</h2><Button variant="ghost" size="sm" onClick={overview.refresh}>{t("Refresh overview")}</Button></div>
      {overview.loading && <p role="status">{t("Loading your overview…")}</p>}{overview.error && <p role="alert" className="form-error">{copy(overview.error)}</p>}
      {overview.data && <><dl className="overview-counts"><div><dt>{t("Uploaded reports")}</dt><dd>{overview.data.uploaded_reports}</dd></div><div><dt>{t("Reviewed parameters")}</dt><dd>{overview.data.reviewed_parameters}</dd></div><div><dt>{t("Active observations")}</dt><dd>{overview.data.active_observations}</dd></div></dl>
        {overview.data.active_observations === 0 ? <div className="history-empty"><h3>{t("No health observations yet.")}</h3><p>{t("Upload a report or add a supported measurement. Report values enter history only after personal review and explicit publication.")}</p></div> : <><h3>{t("Recent health observations")}</h3><p>{t("Known measurement days first; unknown dates follow by time recorded. Each value retains its own unit.")}</p><ul className="overview-records">{overview.data.observations.map(o => <li key={o.id}><strong>{o.current.fields.original_label}: {o.current.fields.raw_value} {o.current.fields.original_unit ?? t("Unit not reported")}</strong><br />{measurementLabel(o.current, locale)}<br /><span className="source-badge">{o.source_type === 'report' ? t("From report") : t("Manually entered")}</span></li>)}</ul></>}
        <h3>{t("Recent reports")}</h3>{overview.data.reports.length === 0 ? <p>{t("No reports uploaded yet.")}</p> : <ul className="overview-records">{overview.data.reports.map(r => <li key={r.id}><Link to="/reports">{r.original_filename}</Link><br />{"" + t("Report record created") + " "}{new Date(r.created_at).toISOString()}</li>)}</ul>}
      </>}
      <div className="parameter-actions"><ButtonLink to="/history">{t("Open health history")}</ButtonLink><ButtonLink to="/reports" variant="secondary">{t("Open reports")}</ButtonLink></div>
    </Card><DashboardTrend /></>
}
