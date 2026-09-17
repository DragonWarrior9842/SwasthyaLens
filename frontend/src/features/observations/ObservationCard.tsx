import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../../components/Button'
import { errorMessage } from '../../services/api-client'
import { deleteObservation, getObservation, measurementLabel, saveManual } from '../../services/observations'
import type { ManualInput, Observation } from '../../services/observations'
import { downloadReport, getReport, saveReportAttachment } from '../../services/reports'

type Props = { owner: string; authFailure: (error: unknown) => void; onChange: () => void }
export function ManualForm({ owner, authFailure, onChange, observation }: Props & { observation?: Observation }) {
  const [metric, setMetric] = useState<'weight' | 'heart_rate'>(observation?.current.fields.canonical_metric === 'heart_rate' ? 'heart_rate' : 'weight')
  const [busy, setBusy] = useState(false), [error, setError] = useState<string | null>(null)
  const operation = useRef<AbortController | null>(null), pending = useRef<{ text: string; key: string } | null>(null)
  useEffect(() => () => operation.current?.abort(), [])
  return <form className="observation-form" aria-label={observation ? 'Edit manual measurement' : 'Add manual measurement'} onSubmit={event => {
    event.preventDefault(); if (operation.current) return
    const form = event.currentTarget, data = new FormData(form)
    const time = String(data.get('measured_at'))
    const enteredTime = `${time}${time.length === 16 ? ':00' : ''}Z`
    const originalTime = observation?.current.measured_at
    const measured_at = originalTime && Date.parse(originalTime) === Date.parse(enteredTime) ? originalTime : enteredTime
    const body = { metric, raw_value: String(data.get('value')), unit: metric === 'weight' ? 'kg' as const : 'bpm' as const, measured_at, ...(observation ? { expected_revision: observation.current.revision } : {}) }
    const text = JSON.stringify(body)
    if (pending.current?.text !== text) pending.current = { text, key: crypto.randomUUID() }
    const input: ManualInput = { ...body, idempotency_key: pending.current.key }
    const controller = new AbortController(); operation.current = controller; setBusy(true); setError(null)
    void saveManual(input, owner, observation?.id, controller.signal).then(() => { if (!controller.signal.aborted) { pending.current = null; form.reset(); onChange() } }).catch((failure: unknown) => { if (!controller.signal.aborted) { setError(errorMessage(failure)); authFailure(failure) } }).finally(() => { operation.current = null; if (!controller.signal.aborted) setBusy(false) })
  }}>
    <h3>{observation ? 'Correct manual measurement' : 'Add a measurement'}</h3>
    <p>Manually entered by you. Enter the actual measurement time in UTC.</p>
    <label>Measurement<select value={metric} onChange={event => setMetric(event.target.value as 'weight' | 'heart_rate')} disabled={busy}><option value="weight">Weight · kg</option><option value="heart_rate">Heart rate · bpm</option></select></label>
    <label>Measured value ({metric === 'weight' ? 'kg' : 'bpm'})<input name="value" required inputMode="decimal" maxLength={12} pattern={metric === 'weight' ? '[0-9]{1,4}([.][0-9]{1,3})?' : '[0-9]{1,4}'} defaultValue={observation?.current.fields.raw_value ?? ''} disabled={busy} /></label>
    <label>Measurement time (UTC)<input name="measured_at" type="datetime-local" step="0.001" required min="1900-01-01T00:00" max="2100-12-31T23:59:59.999" defaultValue={observation?.current.measured_at ? new Date(observation.current.measured_at).toISOString().slice(0, -1) : ''} disabled={busy} /></label>
    <Button type="submit" disabled={busy}>{busy ? 'Saving…' : observation ? 'Save measurement correction' : 'Save measurement'}</Button>
    {error && <p role="alert" className="form-error">{error}</p>}
  </form>
}

export function ObservationCard({ observation, owner, authFailure, onChange }: Props & { observation: Observation }) {
  const [detail, setDetail] = useState<Observation | null>(null), [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false), [edit, setEdit] = useState(false), [confirmDelete, setConfirmDelete] = useState(false)
  const operation = useRef<AbortController | null>(null)
  useEffect(() => () => operation.current?.abort(), [])
  const record = detail ?? observation, value = record.current
  async function perform(task: (signal: AbortSignal) => Promise<void>) {
    if (operation.current) return
    const controller = new AbortController(); operation.current = controller; setBusy(true); setError(null)
    try { await task(controller.signal) } catch (failure) { if (!controller.signal.aborted) { setError(errorMessage(failure)); authFailure(failure) } }
    finally { operation.current = null; if (!controller.signal.aborted) setBusy(false) }
  }
  return <article className="observation-card" aria-label={`Observation ${value.fields.original_label}`}>
    <div className="card-heading"><h3>{value.fields.original_label}</h3><span className="source-badge">{record.source_type === 'report' ? 'From report' : 'Manually entered'}</span></div>
    <p className="observation-value">{value.fields.raw_value} <span>{value.fields.original_unit ?? 'Unit not reported'}</span></p>
    <p>{measurementLabel(value)}</p><p>Status: {value.status} · Revision {value.revision}{value.review_revision ? ` · Personal review ${value.review_revision}` : ''}</p>
    {value.status !== 'active' && <p>This value is excluded from active history. Review the source and explicitly publish the latest eligible revision.</p>}
    {!value.fields.canonical_metric && <p>Unmapped parameter · original label retained.</p>}
    <Button variant="ghost" size="sm" disabled={busy} onClick={() => { void perform(async signal => { const result = await getObservation(record.id, owner, signal); if (!signal.aborted) setDetail(result) }) }}>Inspect provenance and revisions</Button>
    {detail && <section aria-label="Observation provenance">
      <p>Recorded in history: {new Date(detail.created_at).toISOString()} (system time)</p>
      {detail.evidence && <><h4>{detail.evidence.report_name}</h4><p>Page {detail.evidence.content.page_number} · {detail.evidence.content.source_method === 'ocr' ? 'OCR text' : 'Native PDF text'}</p><pre>{detail.evidence.content.source_text}</pre><p>Original machine value: {detail.evidence.content.fields.raw_value ?? 'Not reported'} {detail.evidence.content.fields.original_unit}</p><p>Report record created: {new Date(detail.evidence.report_created_at).toISOString()} (not a measurement date)</p>
        <Button size="sm" variant="secondary" disabled={busy} onClick={() => { void perform(async signal => { if (!detail.report_id) return; const report = await getReport(detail.report_id, owner, signal); const blob = await downloadReport(report, owner, signal); signal.throwIfAborted(); saveReportAttachment(blob, report.original_filename) }) }}>Download source report</Button>{' '}
        <Link to={`/history?report_id=${detail.report_id}`}>History from this report</Link>{' · '}<Link to="/reports">Review report candidates</Link></>}
      <ol aria-label="Observation revisions">{detail.revisions.map(r => <li key={r.revision}>Revision {r.revision} · {r.status} · {r.fields.original_label}: {r.fields.raw_value} {r.fields.original_unit}<br />{measurementLabel(r)}<br />Saved {new Date(r.created_at).toISOString()}{r.review_revision ? ` · Review ${r.review_revision}` : ''}{r.fields.raw_reference ? ` · Source reference: ${r.fields.raw_reference}` : ''}</li>)}</ol>
    </section>}
    {record.source_type === 'manual' && <div className="parameter-actions"><Button size="sm" variant="secondary" disabled={busy || value.revision >= 100} onClick={() => setEdit(v => !v)}>Edit measurement</Button><Button size="sm" variant="ghost" disabled={busy} onClick={() => setConfirmDelete(true)}>Delete measurement</Button></div>}
    {edit && <ManualForm owner={owner} authFailure={authFailure} observation={record} onChange={() => { setEdit(false); setDetail(null); onChange() }} />}
    {confirmDelete && <div role="group" aria-label="Confirm measurement deletion"><p>Delete this manual measurement and all its revisions?</p><Button size="sm" disabled={busy} onClick={() => { void perform(async signal => { await deleteObservation(record.id, value.revision, owner, signal); if (!signal.aborted) onChange() }) }}>Confirm delete measurement</Button><Button size="sm" variant="ghost" disabled={busy} onClick={() => setConfirmDelete(false)}>Keep measurement</Button></div>}
    {error && <p className="form-error" role="alert">{error}</p>}
  </article>
}
