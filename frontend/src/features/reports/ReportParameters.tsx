import { useEffect, useRef, useState } from 'react'
import { Button } from '../../components/Button'
import { PublishObservation } from '../observations/PublishObservation'
import { errorMessage } from '../../services/api-client'
import { getExtraction, getProcessing } from '../../services/extraction'
import type { ProcessingRun } from '../../services/extraction'
import { extractParameters, getParameters, parameterHistory, parameterReviews, reviewParameter } from '../../services/parameters'
import type { Candidate, ParameterResult, ParameterRun, RawFields, Review, ReviewInput } from '../../services/parameters'

type Props = { reportId: string; ownerId: string; onAuthFailure: (error: unknown) => void }
const reviewLabel = { confirmed: 'Confirmed by you', corrected: 'Corrected by you', rejected: 'Rejected by you' }

export function ReportParameters({ reportId, ownerId, onAuthFailure }: Props) {
  const [open, setOpen] = useState(false)
  const [sources, setSources] = useState<ProcessingRun[]>([])
  const [source, setSource] = useState('')
  const [runs, setRuns] = useState<ParameterRun[]>([])
  const [result, setResult] = useState<ParameterResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [refresh, setRefresh] = useState(0)
  const operation = useRef<AbortController | null>(null)
  const requestKey = useRef<string | null>(null)
  useEffect(() => () => operation.current?.abort(), [])
  useEffect(() => {
    if (!open) return
    const controller = new AbortController()
    async function load() {
      try {
        const [textRuns, parameters] = await Promise.all([getProcessing(reportId, ownerId, controller.signal), parameterHistory(reportId, ownerId, controller.signal)])
        if (controller.signal.aborted) return
        const completed = textRuns.filter(r => r.status === 'completed')
        setSources(completed); setRuns(parameters); setSource(current => completed.some(r => r.id === current) ? current : completed[0]?.id ?? ''); setError(null)
      } catch (failure) { if (!controller.signal.aborted) { setError(errorMessage(failure)); onAuthFailure(failure) } }
    }
    void load()
    return () => controller.abort()
  }, [open, reportId, ownerId, onAuthFailure, refresh])

  async function perform(task: (signal: AbortSignal) => Promise<void>) {
    if (operation.current) return
    const controller = new AbortController(); operation.current = controller; setBusy(true); setError(null)
    try { await task(controller.signal) } catch (failure) { if (!controller.signal.aborted) { setError(errorMessage(failure)); onAuthFailure(failure) } }
    finally { operation.current = null; if (!controller.signal.aborted) setBusy(false) }
  }
  async function inspect(runId: string, signal: AbortSignal) {
    const value = await getParameters(reportId, runId, ownerId, signal)
    if (!signal.aborted) setResult(value)
  }
  async function start(signal: AbortSignal) {
    requestKey.current ??= crypto.randomUUID()
    const run = await extractParameters(reportId, source, requestKey.current, ownerId, signal)
    if (signal.aborted) return
    requestKey.current = null; setRefresh(value => value + 1)
    if (run.status === 'completed') await inspect(run.id, signal)
  }
  return <div className="report-extraction">
    <Button variant="ghost" size="sm" aria-expanded={open} onClick={() => setOpen(value => !value)}>{open ? 'Hide parameter candidates' : 'Parameter candidates'}</Button>
    {open && <section className="report-extraction__content" aria-label="Parameter candidates">
      <h4>Extracted parameter candidates</h4>
      <p>Compare every candidate with the original report. Personal review does not establish clinical validity. After review, explicitly publish eligible values to add them to health history.</p>
      <Button size="sm" variant="ghost" disabled={busy} onClick={() => { setRefresh(value => value + 1); setResult(null) }}>Refresh parameter status</Button>
      {sources.length === 0 ? <p>Complete text extraction first, then refresh parameter status.</p> : <>
        <label className="parameter-source">Source text attempt<select value={source} disabled={busy} onChange={event => { setSource(event.target.value); requestKey.current = null }}>
          {sources.map(run => <option key={run.id} value={run.id}>Text attempt {run.attempt}</option>)}
        </select></label>
        <Button size="sm" variant="secondary" disabled={busy || !source || runs.some(r => r.status === 'processing') || runs.filter(r => r.source_run_id === source).length >= 3} onClick={() => { void perform(start) }}>{busy ? 'Loading candidates…' : 'Extract parameters'}</Button>
        <p>Up to three parameter attempts per text attempt. Prior results are retained.</p>
      </>}
      <ol className="extraction-attempts">{runs.map(run => <li key={run.id}>
        <span>Parameter attempt {run.attempt} · Text attempt {sources.find(s => s.id === run.source_run_id)?.attempt ?? 'unavailable'} · {run.status === 'completed' ? `Parameters extracted (${run.candidate_count})` : run.status === 'processing' ? 'Extracting parameters · Refresh to check' : `Extraction failed (${run.error_category})`}</span>
        {run.status === 'completed' && <Button size="sm" variant="ghost" disabled={busy} onClick={() => { void perform(signal => inspect(run.id, signal)) }}>Inspect parameter attempt {run.attempt}</Button>}
      </li>)}</ol>
      {error && <p className="form-error" role="alert">{error}</p>}
      {result && <section aria-label="Extracted candidates">
        <p>{result.run.extractor_version} · {result.run.rules_version}</p>
        {result.run.warnings.includes('unparsed_rows') && <p>Some rows could not be parsed reliably. Inspect the source for missing parameters.</p>}
        {result.candidates.length === 0 && <p>Unable to reliably extract parameter candidates from this text.</p>}
        {result.candidates.map(candidate => <CandidateReview key={`${result.run.id}-${candidate.id}-${candidate.reviews[0]?.revision ?? 0}`} candidate={candidate} reportId={reportId} ownerId={ownerId} sourceRun={result.run.source_run_id} onAuthFailure={onAuthFailure} />)}
      </section>}
    </section>}
  </div>
}

function CandidateReview({ candidate, reportId, ownerId, sourceRun, onAuthFailure }: Props & { candidate: Candidate; sourceRun: string }) {
  const [reviews, setReviews] = useState(candidate.reviews)
  const [edit, setEdit] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [sourceText, setSourceText] = useState<string | null>(null)
  const [showHistory, setShowHistory] = useState(false)
  const operation = useRef<AbortController | null>(null)
  const pending = useRef<{ payload: string; key: string } | null>(null)
  useEffect(() => () => operation.current?.abort(), [])
  const latest = reviews[0]
  const value = latest?.fields ?? candidate.content.fields
  async function perform(task: (signal: AbortSignal) => Promise<void>) {
    if (operation.current) return
    const controller = new AbortController(); operation.current = controller; setBusy(true); setError(null)
    try { await task(controller.signal) } catch (failure) { if (!controller.signal.aborted) { setError(errorMessage(failure)); onAuthFailure(failure) } }
    finally { operation.current = null; if (!controller.signal.aborted) setBusy(false) }
  }
  async function save(action: Review['action'], signal: AbortSignal, correction?: RawFields) {
    const payload = JSON.stringify({ action, correction, expected_revision: latest?.revision ?? 0 })
    if (pending.current?.payload !== payload) pending.current = { payload, key: crypto.randomUUID() }
    const body: ReviewInput = { action, ...(correction ? { correction } : {}), expected_revision: latest?.revision ?? 0, idempotency_key: pending.current.key }
    const review = await reviewParameter(reportId, candidate.id, body, ownerId, signal)
    if (!signal.aborted) { setReviews([review, ...reviews.filter(r => r.revision !== review.revision)]); setEdit(false); pending.current = null }
  }
  return <article className="parameter-candidate" aria-label={`Candidate ${candidate.content.fields.original_label}`}>
    <h4>{value.original_label}</h4>
    <dl className="parameter-fields"><div><dt>Value</dt><dd>{value.raw_value ?? 'Not reported'}</dd></div><div><dt>Unit</dt><dd>{value.original_unit ?? 'Not reported'}</dd></div><div><dt>Reference</dt><dd>{value.raw_reference ?? 'Not reported'}</dd></div><div><dt>Source page</dt><dd>{candidate.content.page_number}</dd></div><div><dt>Review status</dt><dd>{latest ? reviewLabel[latest.action] : 'Needs review'}</dd></div></dl>
    <p>{value.canonical_metric ? `Mapped identity: ${value.canonical_metric}` : 'Unmapped parameter · original label retained'}{value.source_flag ? ` · Printed flag: ${value.source_flag}` : ''}</p>
    <details><summary>Inspect source and machine result</summary>
      <p>Source text attempt: {sourceRun} · Page {candidate.content.page_number} · {candidate.content.source_method === 'ocr' ? 'OCR text' : 'Native PDF text'}</p>
      <pre>{candidate.content.source_text}</pre>
      <p>Machine result: {candidate.content.fields.original_label} · {candidate.content.fields.raw_value ?? 'Not reported'} · {candidate.content.fields.original_unit ?? 'No unit'} · {candidate.content.fields.raw_reference ?? 'No reference'}</p>
      <p>Source offsets: {candidate.content.source_start}–{candidate.content.source_end} (Unicode characters, end excluded).</p>
      {candidate.content.ocr_confidence !== null && <p>Source page mean OCR word score: {candidate.content.ocr_confidence.toFixed(1)}/100. This is not candidate accuracy.</p>}
      <p>{candidate.content.warnings.map(w => w.replaceAll('_', ' ')).join(' · ')}</p>
      <Button size="sm" variant="ghost" disabled={busy} onClick={() => { void perform(async signal => { const source = await getExtraction(reportId, sourceRun, ownerId, signal); if (!signal.aborted) setSourceText(source.pages.find(p => p.page_number === candidate.content.page_number)?.text ?? '') }) }}>View source page text</Button>
      {sourceText !== null && <pre>{sourceText}</pre>}
    </details>
    <div className="parameter-actions">
      <Button size="sm" variant="secondary" disabled={busy || (latest?.revision ?? 0) >= 20} onClick={() => { void perform(signal => save('confirmed', signal)) }}>Confirm reviewed</Button>
      <Button size="sm" variant="ghost" disabled={busy || (latest?.revision ?? 0) >= 20} onClick={() => setEdit(v => !v)}>Correct fields</Button>
      <Button size="sm" variant="ghost" disabled={busy || (latest?.revision ?? 0) >= 20} onClick={() => { void perform(signal => save('rejected', signal)) }}>Reject candidate</Button>
      <Button size="sm" variant="ghost" disabled={busy} onClick={() => { void perform(async signal => { const history = await parameterReviews(reportId, candidate.id, ownerId, signal); if (!signal.aborted) { setReviews(history); setShowHistory(true) } }) }}>Review history</Button>
    </div>
    {latest && <PublishObservation key={latest.revision} reportId={reportId} candidateId={candidate.id} ownerId={ownerId} review={latest} onAuthFailure={onAuthFailure} />}
    {edit && <form className="parameter-correction" onSubmit={event => {
      event.preventDefault(); const form = new FormData(event.currentTarget)
      const correction: RawFields = { original_label: String(form.get('original_label') ?? ''), raw_value: String(form.get('raw_value') ?? '') || null, original_unit: String(form.get('original_unit') ?? '') || null, raw_reference: String(form.get('raw_reference') ?? '') || null }
      void perform(signal => save('corrected', signal, correction))
    }}>
      <p>Correction creates a separate revision. The machine result and source stay available.</p>
      {([['original_label', 'Parameter', 160], ['raw_value', 'Value', 100], ['original_unit', 'Unit', 60], ['raw_reference', 'Reference', 160]] as const).map(([name, label, length]) => <label key={name}>{label}<input name={name} maxLength={length} required={name === 'original_label'} defaultValue={value[name] ?? ''} /></label>)}
      <Button size="sm" type="submit" disabled={busy}>Save correction</Button>
    </form>}
    {showHistory && <ol aria-label="Review revisions">{reviews.map(review => <li key={review.revision}>Revision {review.revision} · {reviewLabel[review.action]} · {new Date(review.created_at).toLocaleString()} · {review.fields.original_label} · {review.fields.raw_value ?? 'Not reported'} · {review.fields.original_unit ?? 'No unit'} · {review.fields.raw_reference ?? 'No reference'}<br />Reviewer: {review.actor_id}</li>)}{reviews.length === 0 && <li>No personal reviews yet.</li>}</ol>}
    {error && <p className="form-error" role="alert">{error}</p>}
  </article>
}
