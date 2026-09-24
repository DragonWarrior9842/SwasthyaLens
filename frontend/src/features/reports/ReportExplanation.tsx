import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../../components/Button'
import { errorMessage } from '../../services/api-client'
import { generateExplanation, getExplanation } from '../../services/explanations'
import type { ExplanationView } from '../../services/explanations'
import { onReportChanged } from '../../services/report-events'

export function ReportExplanation({ reportId, ownerId, onAuthFailure }: { reportId: string; ownerId: string; onAuthFailure: (error: unknown) => void }) {
  const [open, setOpen] = useState(false), [state, setState] = useState<ExplanationView | null>(null)
  const [consent, setConsent] = useState(false), [busy, setBusy] = useState(false), [error, setError] = useState<string | null>(null)
  const operation = useRef<AbortController | null>(null), requestKey = useRef<string | null>(null)
  const lastProvider = useRef<string | null>(null)
  const authFailure = useRef(onAuthFailure)
  useEffect(() => { authFailure.current = onAuthFailure }, [onAuthFailure])
  const load = useCallback(async (generate = false) => {
    if (operation.current) return
    const controller = new AbortController(); operation.current = controller
    setBusy(true); setError(null); setState(null)
    try {
      requestKey.current ??= crypto.randomUUID()
      const result = generate ? await generateExplanation(reportId, requestKey.current, ownerId, controller.signal) : await getExplanation(reportId, ownerId, controller.signal)
      controller.signal.throwIfAborted()
      if (lastProvider.current !== result.provider) setConsent(false)
      lastProvider.current = result.provider
      setState(result)
      if (result.record && result.record.status !== 'generating') requestKey.current = null
    } catch (failure) { if (!controller.signal.aborted) { setError(errorMessage(failure)); authFailure.current(failure) } }
    finally { if (operation.current === controller) operation.current = null; if (!controller.signal.aborted) setBusy(false) }
  }, [ownerId, reportId])
  useEffect(() => {
    if (!open) return
    const clear = () => { operation.current?.abort(); operation.current = null; setState(null); setConsent(false); setBusy(false) }
    const refresh = () => { clear(); if (!document.hidden) void load() }
    const stop = onReportChanged(reportId, refresh)
    window.addEventListener('focus', refresh)
    document.addEventListener('visibilitychange', refresh)
    const timer = window.setInterval(() => { if (!document.hidden && !operation.current) void load() }, 15_000)
    return () => { stop(); clear(); window.clearInterval(timer); window.removeEventListener('focus', refresh); document.removeEventListener('visibilitychange', refresh) }
  }, [open, reportId, load])
  useEffect(() => () => { operation.current?.abort() }, [])
  const record = state?.record
  const eligible = !!state && state.eligible_count > 0 && state.eligible_count <= 20 && state.evaluation_enrolled && state.provider_available
  return <section className="report-explanation" aria-label="Report explanation">
    <Button variant="secondary" size="sm" aria-expanded={open} onClick={() => { if (!open) void load(); setOpen(!open) }}>Report explanation</Button>
    {open && <div>
      <h4>Selected reviewed findings · educational explanation</h4>
      <p>This covers published, personally reviewed findings from this report only. Personal review is not clinical verification. It may not describe the complete report.</p>
      <p>AI selects wording from a bounded educational catalog. It does not diagnose, recommend treatment or determine whether a value is above, below or within a range.</p>
      {busy && <p role="status">Checking or generating the explanation…</p>}
      {error && <p role="alert" className="form-error">{error} Refresh to check whether an earlier request completed before generating again.</p>}
      {state && <p>{state.eligible_count} eligible published finding{state.eligible_count === 1 ? '' : 's'}. {!state.evaluation_enrolled && 'This report is not enrolled in the synthetic evaluation.'} {!state.provider_available && 'Live evaluation is disabled.'}</p>}
      {record?.status === 'stale' && <p role="status">Source findings changed. The previous explanation has been removed. Review and publish the corrected findings before a new evaluation.</p>}
      {record?.status === 'failed' && <p role="alert">No verified explanation was saved ({record.error_category}). A retry is a new explicit request.</p>}
      {record?.status === 'generating' && <p role="status">A request is still in progress. Refresh its status; no automatic generation or retry will occur.</p>}
      {record?.status === 'ready' && <>
        <p>{record.provider === 'mock-test' ? 'Deterministic test result · no external AI call' : record.provider === 'gemini' ? 'Gemini 3.8 Flash · synthetic evaluation' : 'OpenAI GPT-5.6 Terra · synthetic evaluation'} · Generated {new Date(record.created_at).toLocaleString()} · Expires {new Date(record.expires_at).toLocaleString()}</p>
        <ul>{record.items.map(item => <li key={item.fact.evidence_id}>
          <h5>{item.fact.label}</h5>
          <p><strong>{item.fact.value}</strong>{item.fact.unit ? ` ${item.fact.unit}` : ' · Unit not supplied'}</p>
          <p>Report reference: {item.fact.reference ?? 'Not supplied'} · Printed flag: {item.fact.source_flag ?? 'Not supplied'}</p>
          <p>{item.explanation}</p>
          <ul>{item.notes.map(note => <li key={note}>{note}</li>)}</ul>
          <p>Source: this report, page {item.source.page_number}, review {item.source.review_revision}, observation revision {item.source.revision}. <Link to={`/history?report_id=${reportId}`}>Inspect published findings and source evidence</Link></p>
          {item.educational_source_url && <a href={item.educational_source_url} target="_blank" rel="noreferrer">General education source: MedlinePlus</a>}
        </li>)}</ul>
        <p>A healthcare professional can interpret these findings alongside your history and other results.</p>
      </>}
      {record?.status !== 'ready' && <>
        <p>Generating uses the selected finding labels, exact values, units, supplied ranges, flags and page numbers. The original file and account identifiers are excluded. This evaluation accepts synthetic reports only. Application copies expire after 30 days.</p>
        {state?.provider === 'gemini' && <p>These synthetic findings are sent to Google Gemini Free Tier. Google may use submitted data and responses to improve its products; human reviewers may process them. Request logging is disabled, but this does not remove Google's Free Tier data terms. Do not submit personal or real patient information. This is not a production healthcare provider decision.</p>}
        {state?.provider === 'openai' && <p>These findings would be sent to OpenAI, which may retain safety logs under its terms. OpenAI live evaluation is currently stopped.</p>}
        {state?.provider === 'mock-test' && <p>This deterministic test uses no external AI provider.</p>}
        <label><input type="checkbox" checked={consent} disabled={!eligible || busy} onChange={event => setConsent(event.target.checked)} /> I understand and agree to send these synthetic findings for this evaluation.</label>
        <Button size="sm" disabled={!eligible || !consent || busy || record?.status === 'generating'} onClick={() => { void load(true) }}>Generate educational explanation</Button>
      </>}
      <Button variant="ghost" size="sm" disabled={busy} onClick={() => { void load() }}>Refresh explanation status</Button>
    </div>}
  </section>
}
