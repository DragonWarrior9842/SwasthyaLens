import { useEffect, useRef, useState } from 'react'
import { Button } from '../../components/Button'
import { errorMessage } from '../../services/api-client'
import { getExtraction, getProcessing, processReport } from '../../services/extraction'
import type { ExtractionResult, ProcessingRun } from '../../services/extraction'

const labels = { queued: 'Text extraction queued', processing: 'Extracting text', completed: 'Text extraction complete', failed: 'Text extraction failed' }
const failures: Record<string, string> = {
  encrypted_document: 'Password-protected PDFs are not supported. Use an unencrypted copy you are permitted to upload.',
  corrupt_document: 'The document could not be read. Try a valid copy of the original.',
  unsupported_document: 'This document format is not supported for extraction.',
  page_limit_exceeded: 'The document exceeds the configured page limit (maximum 20 pages).',
  resource_limit_exceeded: 'The document exceeds safe processing limits. Try a smaller document or image.',
  ocr_unavailable: 'The local OCR engine is unavailable. Retry after the server OCR setup is fixed.',
  ocr_failure: 'OCR could not read this document. Inspect the original before retrying.',
  extractor_failure: 'Text extraction could not finish. You can retry.',
  timeout: 'Text extraction exceeded its time limit. You can retry with a smaller document.',
  interrupted: 'The attempt was interrupted or lost authorization. You can retry while signed in.',
  source_unavailable: 'The original file could not be obtained. You can retry.',
}

export function ReportExtraction({ reportId, ownerId, onAuthFailure }: { reportId: string; ownerId: string; onAuthFailure: (error: unknown) => void }) {
  const [open, setOpen] = useState(false)
  const [runs, setRuns] = useState<ProcessingRun[] | null>(null)
  const [result, setResult] = useState<ExtractionResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [revision, setRevision] = useState(0)
  const operation = useRef<AbortController | null>(null)
  const requestKey = useRef<string | null>(null)
  useEffect(() => () => operation.current?.abort(), [])
  useEffect(() => {
    if (!open) return
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout> | undefined
    async function load() {
      try {
        const history = await getProcessing(reportId, ownerId, controller.signal)
        if (controller.signal.aborted) return
        setRuns(history)
        setError(null)
        if (history.some(run => run.status === 'queued' || run.status === 'processing')) timer = setTimeout(() => { void load() }, 6000)
      } catch (failure) {
        if (!controller.signal.aborted) { setError(errorMessage(failure)); onAuthFailure(failure) }
      }
    }
    void load()
    return () => { controller.abort(); clearTimeout(timer) }
  }, [open, reportId, ownerId, onAuthFailure, revision])

  async function start() {
    if (operation.current) return
    const controller = new AbortController()
    operation.current = controller
    requestKey.current ??= crypto.randomUUID()
    setBusy(true); setError(null)
    try {
      const run = await processReport(reportId, requestKey.current, ownerId, controller.signal)
      if (!controller.signal.aborted) { requestKey.current = null; setRuns(previous => [run, ...(previous ?? []).filter(item => item.id !== run.id)]); setRevision(value => value + 1) }
    } catch (failure) {
      if (!controller.signal.aborted) { setError(errorMessage(failure)); onAuthFailure(failure) }
    } finally { operation.current = null; if (!controller.signal.aborted) setBusy(false) }
  }
  async function inspect(runId: string) {
    if (operation.current) return
    const controller = new AbortController(); operation.current = controller
    setBusy(true); setError(null); setResult(null)
    try {
      const extraction = await getExtraction(reportId, runId, ownerId, controller.signal)
      if (!controller.signal.aborted) setResult(extraction)
    } catch (failure) {
      if (!controller.signal.aborted) { setError(errorMessage(failure)); onAuthFailure(failure) }
    } finally { operation.current = null; if (!controller.signal.aborted) setBusy(false) }
  }
  const active = runs?.some(run => run.status === 'queued' || run.status === 'processing')
  return <div className="report-extraction">
    <Button variant="ghost" size="sm" aria-expanded={open} onClick={() => { setOpen(value => !value); setResult(null) }}>{open ? 'Hide text extraction' : 'Text extraction'}</Button>
    {open && <div className="report-extraction__content">
      <p>The original report is the source of truth. Extracted text may contain errors and is not medical interpretation.</p>
      {runs === null && !error && <p role="status">Loading extraction status…</p>}
      {runs && <>
        <p role="status">{runs[0] ? labels[runs[0].status] : 'Uploaded · Text has not been extracted.'}</p>
        <Button size="sm" variant="secondary" disabled={busy || active || runs.length >= 3} onClick={() => { void start() }}>{runs.length === 0 ? 'Extract text' : runs[0]?.status === 'failed' ? 'Retry text extraction' : 'Extract again'}</Button>
        {runs.length >= 3 && <p>Three extraction attempts have been used for this report.</p>}
        <ol className="extraction-attempts">{runs.map(run => <li key={run.id}>
          <span>Attempt {run.attempt} · {labels[run.status]}</span>
          {run.error_category && <p>{failures[run.error_category]}</p>}
          {run.status === 'completed' && <Button size="sm" variant="ghost" disabled={busy} onClick={() => { void inspect(run.id) }}>View extracted text · Attempt {run.attempt}</Button>}
        </li>)}</ol>
      </>}
      {error && <div role="alert"><p className="form-error">{error}</p><Button size="sm" variant="ghost" onClick={() => setRevision(value => value + 1)}>Refresh extraction status</Button></div>}
      {result && <section aria-label="Extracted text">
        <h4>Extracted text · Attempt {result.run.attempt}</h4>
        <p className="subtle-label">{result.run.processor}</p>
        {result.pages.map(page => <section className="extracted-page" key={page.page_number}>
          <h4>Page {page.page_number} · {page.method === 'native_text' ? 'Native PDF text' : 'OCR'}</h4>
          {page.confidence !== null && <p>Mean OCR word score: {page.confidence.toFixed(1)}/100. This is an engine score, not a guarantee of accuracy.</p>}
          {page.warnings.includes('orientation_uncertain') && <p>Page orientation could not be confirmed.</p>}
          <p>Compare columns, numbers and units with the original file.</p>
          <pre>{page.text || 'No text was recovered on this page.'}</pre>
        </section>)}
      </section>}
    </div>}
  </div>
}
