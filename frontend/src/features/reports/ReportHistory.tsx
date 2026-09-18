import { useEffect, useRef, useState } from 'react'
import { Badge } from '../../components/Badge'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { EmptyState } from '../../components/EmptyState'
import { Icon } from '../../components/Icon'
import { errorMessage } from '../../services/api-client'
import { deleteReport, downloadReport, formatBytes, saveReportAttachment } from '../../services/reports'
import type { Report, ReportPage, ReportStatus } from '../../types/reports'
import { ReportExtraction } from './ReportExtraction'
import { ReportParameters } from './ReportParameters'
import { ReportExplanation } from './ReportExplanation'

const labels: Record<ReportStatus, string> = { pending_upload: 'Awaiting file', uploading: 'Upload in progress', uploaded: 'Uploaded', upload_failed: 'Upload incomplete', deleting: 'Deletion pending' }
const descriptions: Record<ReportStatus, string> = {
  pending_upload: 'The file upload has not completed. Retry from the selected file, or delete this record.',
  uploading: 'Upload completion is not yet confirmed. Refresh to check its status.',
  uploaded: 'Stored privately. Text extraction is available below; medical analysis is not included.',
  upload_failed: 'Upload did not complete. Retry from the selected file, or delete this record.',
  deleting: 'Deletion has been requested. The record remains until private file cleanup is confirmed.',
}

interface Props {
  ownerId: string
  page: ReportPage
  notice: string | null
  refreshError: string | null
  refreshing: boolean
  loadingMore: boolean
  moreError: string | null
  onRefresh: () => void
  onLoadMore: () => Promise<void>
  onAuthFailure: (error: unknown) => void
}

export function ReportHistory({ ownerId, page, notice, refreshError, refreshing, loadingMore, moreError, onRefresh, onLoadMore, onAuthFailure }: Props) {
  return (
    <Card className="report-history">
      <div className="card-heading"><div><h2>Report history</h2><p className="subtle-label">Your files, newest first</p></div><Button variant="ghost" size="sm" disabled={refreshing} onClick={onRefresh}><Icon name="retry" />{refreshing ? 'Refreshing…' : 'Refresh'}</Button></div>
      {notice && <p className="form-notice report-history__notice" role="status">{notice}</p>}
      {refreshError && <p className="form-error report-history__notice" role="alert">{refreshError} This list may be out of date. Refresh to try again.</p>}
      {page.reports.length === 0 ? <EmptyState icon="report" title="No reports uploaded yet." description="Choose a PDF or image above to store your first report privately." /> : <ul className="report-list">{page.reports.map((report) => <ReportRow key={`${report.id}-${report.updated_at}-${report.status}`} report={report} ownerId={ownerId} onChange={onRefresh} onAuthFailure={onAuthFailure} />)}</ul>}
      {moreError && <p className="form-error report-history__notice" role="alert">{moreError}</p>}
      {page.next_cursor && <div className="report-history__more"><Button variant="secondary" disabled={loadingMore || refreshing} onClick={() => { void onLoadMore() }}>{loadingMore ? 'Loading more…' : 'Load more reports'}</Button></div>}
    </Card>
  )
}

function ReportRow({ report, ownerId, onChange, onAuthFailure }: { report: Report; ownerId: string; onChange: () => void; onAuthFailure: (error: unknown) => void }) {
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [busy, setBusy] = useState<'download' | 'delete' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const operation = useRef<AbortController | null>(null)
  useEffect(() => () => { operation.current?.abort() }, [])

  async function download() {
    if (operation.current) return
    const controller = new AbortController()
    operation.current = controller
    setBusy('download')
    setError(null)
    setNotice(null)
    try {
      const blob = await downloadReport(report, ownerId, controller.signal)
      controller.signal.throwIfAborted()
      saveReportAttachment(blob, report.original_filename)
      setNotice('Download started. Keep downloaded copies secure on your device.')
    } catch (failure) {
      if (!controller.signal.aborted) { setError(errorMessage(failure)); onAuthFailure(failure) }
    } finally {
      if (!controller.signal.aborted) setBusy(null)
      if (operation.current === controller) operation.current = null
    }
  }

  async function remove() {
    if (operation.current) return
    const controller = new AbortController()
    operation.current = controller
    setBusy('delete')
    setError(null)
    setNotice(null)
    try {
      const result = await deleteReport(report.id, ownerId, controller.signal)
      controller.signal.throwIfAborted()
      setConfirmDelete(false)
      setNotice(result.status === 'deleted' ? 'Report and stored file deleted.' : 'Deletion is pending. Refresh to check cleanup; the report has not been confirmed deleted.')
      onChange()
    } catch (failure) {
      if (!controller.signal.aborted) { setError(`${errorMessage(failure)} Deletion has not been confirmed.`); onAuthFailure(failure) }
    } finally {
      if (!controller.signal.aborted) setBusy(null)
      if (operation.current === controller) operation.current = null
    }
  }

  return (
    <li className="report-row">
      <div className="report-row__summary"><span className="report-row__icon"><Icon name="report" /></span><div className="report-row__details"><h3>{report.original_filename}</h3><p className="report-row__metadata"><span>{report.media_type === 'application/pdf' ? 'PDF' : report.media_type === 'image/jpeg' ? 'JPEG' : 'PNG'}</span><span>{formatBytes(report.size_bytes)}</span><time dateTime={report.created_at}>{new Intl.DateTimeFormat('en', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(report.created_at))}</time></p><p className="report-row__description">{descriptions[report.status]}</p></div><Badge tone={report.status === 'uploaded' ? 'teal' : report.status === 'pending_upload' ? 'neutral' : 'amber'}>{labels[report.status]}</Badge></div>
      <div className="report-row__actions">{report.status === 'uploaded' && <Button variant="secondary" size="sm" disabled={busy !== null} onClick={() => { void download() }}>{busy === 'download' ? 'Downloading…' : 'Download'}</Button>}<Button variant="ghost" size="sm" disabled={busy !== null} onClick={() => { setConfirmDelete(true); setError(null); setNotice(null) }}>{report.status === 'deleting' ? 'Retry deletion' : 'Delete report'}</Button></div>
      {confirmDelete && <div className="report-delete" role="group" aria-label={`Confirm deletion of ${report.original_filename}`}><p>Delete <strong>{report.original_filename}</strong> and its private stored file? This cannot be undone. Copies already downloaded to a device remain there.</p><div><Button size="sm" className="button--danger" disabled={busy !== null} onClick={() => { void remove() }}>{busy === 'delete' ? 'Deleting…' : 'Confirm delete'}</Button><Button size="sm" variant="ghost" disabled={busy !== null} onClick={() => setConfirmDelete(false)}>Keep report</Button></div></div>}
      {error && <p className="form-error" role="alert">{error}</p>}
      {notice && <p className="form-notice" role="status">{notice}</p>}
      {report.status === 'uploaded' && <ReportExtraction reportId={report.id} ownerId={ownerId} onAuthFailure={onAuthFailure} />}
      {report.status === 'uploaded' && <ReportParameters reportId={report.id} ownerId={ownerId} onAuthFailure={onAuthFailure} />}
      {report.status === 'uploaded' && <ReportExplanation reportId={report.id} ownerId={ownerId} onAuthFailure={onAuthFailure} />}
    </li>
  )
}
