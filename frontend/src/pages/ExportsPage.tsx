import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { useHistoryAccount } from '../features/observations/useOwnedHistory'
import { useI18n, type Locale } from '../i18n/core'
import { accountExport } from '../services/auth'
import { errorMessage } from '../services/api-client'
import { saveReportAttachment } from '../services/reports'

export function ExportsPage() {
  const { t, copy, locale } = useI18n(), { owner, authFailure } = useHistoryAccount()
  const [params] = useSearchParams(), report = params.get('report_id')
  const [format, setFormat] = useState<'csv' | 'json'>('json')
  const [language, setLanguage] = useState<Locale | null>(null)
  const [source, setSource] = useState(report ? 'report' : '')
  const [from, setFrom] = useState(() => new Date(Date.now() - 365 * 86400000).toISOString().slice(0, 10))
  const [through, setThrough] = useState(() => new Date().toISOString().slice(0, 10))
  const [unknown, setUnknown] = useState(false)
  const [status, setStatus] = useState<'idle' | 'generating' | 'ready' | 'failed'>('idle')
  const [error, setError] = useState<string | null>(null)
  const operation = useRef<AbortController | null>(null)
  useEffect(() => () => { operation.current?.abort() }, [owner])
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (operation.current) return
    const controller = new AbortController(); operation.current = controller
    setStatus('generating'); setError(null)
    try {
      const blob = await accountExport({ format, language: language ?? locale, date_from: from, date_to: through, include_unknown: unknown, source_type: source || null, report_id: report }, format, owner, controller.signal)
      controller.signal.throwIfAborted()
      saveReportAttachment(blob, `swasthyalens-health.${format}`)
      setStatus('ready')
    } catch (failure) {
      if (!controller.signal.aborted) { setStatus('failed'); setError(errorMessage(failure)); authFailure(failure) }
    } finally { if (operation.current === controller) operation.current = null }
  }
  return <><PageHeader eyebrow={t('YOUR DATA')} title={t('Export health history')} description={t('Download current personally reviewed and published report observations and manual measurements.')} />
    <Card className="history-panel export-panel"><p>{t('Exports include exact source values, units, supplied ranges and report provenance. AI answers, unpublished candidates and deleted or inactive observations are excluded.')}</p>
      <form className="account-form" onSubmit={event => { void submit(event) }} aria-busy={status === 'generating'}>
        <fieldset disabled={status === 'generating'} className="export-controls"><legend>{t('Export selection')}</legend>
          {report && <p>{t('This export is limited to the selected report. Its ownership is checked again when you download.')}</p>}
          <div><label htmlFor="export-source">{t('Source')}</label><select id="export-source" value={source} onChange={e => setSource(e.target.value)} disabled={!!report}><option value="">{t('All sources')}</option><option value="report">{t('From report')}</option><option value="manual">{t('Manually entered')}</option></select></div>
          <label>{t('Measurement from')}<input type="date" required min="1900-01-01" max="2100-12-31" value={from} onChange={e => setFrom(e.target.value)} /></label>
          <label>{t('Measurement through')}<input type="date" required min="1900-01-01" max="2100-12-31" value={through} onChange={e => setThrough(e.target.value)} /></label>
          <label className="checkbox-label"><input type="checkbox" checked={unknown} onChange={e => setUnknown(e.target.checked)} />{t('Also include observations with an unknown measurement date')}</label>
          <div><label htmlFor="export-format">{t('File format')}</label><select id="export-format" value={format} onChange={e => setFormat(e.target.value === 'csv' ? 'csv' : 'json')}><option value="json">{t('JSON — exact machine-readable strings')}</option><option value="csv">{t('CSV — table for text-mode import')}</option></select></div>
          <div><label htmlFor="export-language">{t('Export language')}</label><select id="export-language" value={language ?? locale} onChange={e => setLanguage(e.target.value === 'hi' ? 'hi' : 'en')}><option value="en">English</option><option value="hi">हिन्दी · Hindi</option></select></div>
        </fieldset>
        <p>{t('Choose at most 366 days. Each export allows 200 observations from 20 reports and a 2 MiB file. Manual dates use UTC. Unknown dates are included only when selected, regardless of period.')}</p>
        <p>{t('For CSV, import all columns as text to keep trailing zeros and exact dates. Choose JSON for lossless string values or formula-like source text.')}</p>
        <p>{t('No export is stored on the server. Each download is generated again from current data. Keep downloaded copies secure; source deletion cannot remove files on your device.')}</p>
        <Button type="submit" disabled={status === 'generating'}>{status === 'generating' ? t('Generating export…') : t('Generate and download')}</Button>
        {status === 'generating' && <p role="status">{t('Generating export…')}</p>}
        {status === 'ready' && <p role="status">{t('Export ready. Download started; your browser controls where the file is saved.')}</p>}
        {error && <p className="form-error" role="alert">{copy(error)}</p>}
      </form>
    </Card></>
}
