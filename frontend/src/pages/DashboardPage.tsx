import { useCallback } from 'react'
import { Link } from 'react-router-dom'
import { Button, ButtonLink } from '../components/Button'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { useHistoryAccount, useOwnedHistory } from '../features/observations/useOwnedHistory'
import { getDashboard, measurementLabel } from '../services/observations'

export function DashboardPage() {
  const { owner, authFailure } = useHistoryAccount()
  const load = useCallback((signal: AbortSignal) => getDashboard(owner, signal), [owner])
  const overview = useOwnedHistory(load, authFailure)
  return <><PageHeader eyebrow="YOUR HEALTH, IN CONTEXT" title="Your health overview" description="Your private reports and personally reviewed health history." />
    <Card className="history-panel"><div className="card-heading"><h2>My health at a glance</h2><Button variant="ghost" size="sm" onClick={overview.refresh}>Refresh overview</Button></div>
      {overview.loading && <p role="status">Loading your overview…</p>}{overview.error && <p role="alert" className="form-error">{overview.error}</p>}
      {overview.data && <><dl className="overview-counts"><div><dt>Uploaded reports</dt><dd>{overview.data.uploaded_reports}</dd></div><div><dt>Reviewed parameters</dt><dd>{overview.data.reviewed_parameters}</dd></div><div><dt>Active observations</dt><dd>{overview.data.active_observations}</dd></div></dl>
        {overview.data.active_observations === 0 ? <div className="history-empty"><h3>No health observations yet.</h3><p>Upload a report or add a supported measurement. Report values enter history only after personal review and explicit publication.</p></div> : <><h3>Recent health observations</h3><p>Known measurement days first; unknown dates follow by time recorded. Each value retains its own unit.</p><ul className="overview-records">{overview.data.observations.map(o => <li key={o.id}><strong>{o.current.fields.original_label}: {o.current.fields.raw_value} {o.current.fields.original_unit ?? 'Unit not reported'}</strong><br />{measurementLabel(o.current)}<br /><span className="source-badge">{o.source_type === 'report' ? 'From report' : 'Manually entered'}</span></li>)}</ul></>}
        <h3>Recent reports</h3>{overview.data.reports.length === 0 ? <p>No reports uploaded yet.</p> : <ul className="overview-records">{overview.data.reports.map(r => <li key={r.id}><Link to="/reports">{r.original_filename}</Link><br />Report record created {new Date(r.created_at).toISOString()}</li>)}</ul>}
      </>}
      <div className="parameter-actions"><ButtonLink to="/history">Open health history</ButtonLink><ButtonLink to="/reports" variant="secondary">Open reports</ButtonLink></div>
    </Card></>
}
