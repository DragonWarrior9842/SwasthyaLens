import { useEffect, useRef, useState, type DragEvent, type FormEvent } from 'react'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { Icon } from '../../components/Icon'
import { ApiError, errorMessage } from '../../services/api-client'
import { deleteReport, formatBytes, reserveReport, uploadReport, validateReportFile } from '../../services/reports'
import type { Report, ReportConfig } from '../../types/reports'

interface UploadTask { file: File; key: string; report: Report | null; reservationAttempted: boolean }
type UploadPhase = 'idle' | 'selected' | 'reserving' | 'uploading' | 'uploaded' | 'failed' | 'cancelling' | 'deleting'
interface Props { ownerId: string; config: ReportConfig; onChange: () => void; onAuthFailure: (error: unknown) => void }

export function ReportUpload({ ownerId, config, onChange, onAuthFailure }: Props) {
  const [task, setTask] = useState<UploadTask | null>(null)
  const [phase, setPhase] = useState<UploadPhase>('idle')
  const [permission, setPermission] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const input = useRef<HTMLInputElement>(null)
  const active = useRef(true)
  const operation = useRef<AbortController | null>(null)
  const currentTask = useRef<UploadTask | null>(null)
  const cancelRequested = useRef(false)
  const busy = ['reserving', 'uploading', 'cancelling'].includes(phase)
  const lockedSelection = busy || phase === 'failed'

  useEffect(() => {
    active.current = true
    return () => { active.current = false; operation.current?.abort() }
  }, [])

  function selectFiles(files: FileList | File[]) {
    if (lockedSelection) return
    setError(null)
    setNotice(null)
    if (files.length !== 1 || !files[0]) { setError('Choose one report at a time.'); return }
    const file = files[0]
    const validation = validateReportFile(file, config)
    if (validation) { setError(validation); return }
    const selected: UploadTask = { file, key: crypto.randomUUID(), report: null, reservationAttempted: false }
    currentTask.current = selected
    setTask(selected)
    setPhase('selected')
  }

  function drop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setDragging(false)
    selectFiles(event.dataTransfer.files)
  }

  async function completeCancellation(selected: UploadTask) {
    const controller = new AbortController()
    operation.current = controller
    setPhase('cancelling')
    setError(null)
    try {
      // Resolve an uncertain reservation using the same key before deleting it.
      const reserved = selected.report ?? (selected.reservationAttempted ? await reserveReport(selected.file, selected.key, ownerId, controller.signal) : null)
      if (reserved) {
        selected = { ...selected, report: reserved }
        currentTask.current = selected
        if (active.current) setTask(selected)
        const result = await deleteReport(reserved.id, ownerId, controller.signal)
        if (!active.current) return
        setPhase(result.status === 'deleted' ? 'idle' : 'deleting')
        setNotice(result.status === 'deleted' ? 'The upload was cancelled and its stored data was deleted.' : 'Cancellation was requested. Deletion is still pending; check report history for confirmation.')
      } else {
        if (!active.current) return
        setPhase('idle')
        setNotice('File selection cleared. Nothing was uploaded.')
      }
      currentTask.current = null
      setTask(null)
      if (input.current) input.current.value = ''
      onChange()
    } catch (failure) {
      if (!active.current) return
      setPhase('failed')
      setError(`${errorMessage(failure)} Cancellation has not been confirmed. Retry cancellation or delete the report from its history.`)
      onAuthFailure(failure)
      onChange()
    } finally { if (operation.current === controller) operation.current = null }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const selected = currentTask.current
    if (!selected || operation.current || !permission) return
    const validation = validateReportFile(selected.file, config)
    if (validation) { setError(validation); return }
    const controller = new AbortController()
    operation.current = controller
    cancelRequested.current = false
    setError(null)
    setNotice(null)
    setPhase('reserving')
    try {
      let reserved = selected.report
      if (!reserved) {
        const attempted = { ...selected, reservationAttempted: true }
        currentTask.current = attempted
        setTask(attempted)
        reserved = await reserveReport(selected.file, selected.key, ownerId, controller.signal)
        const next = { ...attempted, report: reserved }
        currentTask.current = next
        if (active.current) setTask(next)
      }
      controller.signal.throwIfAborted()
      if (reserved.status === 'deleting') throw new ApiError('report_conflict', 'Deletion of this report is pending. Clear this selection after cancellation completes.')
      if (reserved.status !== 'uploaded') {
        setPhase('uploading')
        const uploaded = await uploadReport(reserved.id, selected.file, ownerId, controller.signal)
        if (uploaded.id !== reserved.id || uploaded.status !== 'uploaded') throw new Error('Unexpected upload acknowledgement')
        currentTask.current = { ...selected, report: uploaded, reservationAttempted: true }
      }
      controller.signal.throwIfAborted()
      if (!active.current) return
      setPhase('uploaded')
      setNotice(`${selected.file.name} was uploaded privately. Open Text extraction in report history to extract its text.`)
      setTask(currentTask.current)
      onChange()
    } catch (failure) {
      if (!active.current) return
      if (cancelRequested.current && currentTask.current) {
        await completeCancellation(currentTask.current)
      } else {
        setPhase('failed')
        setError(`${errorMessage(failure)} The upload was not confirmed. Retry the same file or cancel it; report history shows the stored status.`)
        onAuthFailure(failure)
        onChange()
      }
    } finally { if (operation.current === controller) operation.current = null }
  }

  function cancel() {
    if (phase === 'cancelling') return
    const selected = currentTask.current
    if (!selected) return
    if (operation.current) {
      cancelRequested.current = true
      setPhase('cancelling')
      operation.current.abort()
    } else { void completeCancellation(selected) }
  }

  return (
    <Card className="report-upload">
      <div className="card-heading"><h2>Upload a report</h2><span className="subtle-label">Private to your account</span></div>
      <form onSubmit={(event) => { void submit(event) }} className="report-upload__body" aria-busy={busy}>
        <div className={`report-dropzone ${dragging && !lockedSelection ? 'report-dropzone--active' : ''}`} onDragOver={(event) => { event.preventDefault(); if (!lockedSelection) setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={drop}>
          <span className="report-upload__icon"><Icon name="report" /></span>
          <div><h3>{task ? task.file.name : 'Keep your reports together'}</h3><p>{task ? `${formatBytes(task.file.size)} · ${task.file.type === 'application/pdf' ? 'PDF document' : task.file.type === 'image/jpeg' ? 'JPEG image' : 'PNG image'}` : 'Drag one report here, or choose a file from your device.'}</p></div>
          <Button variant="secondary" disabled={lockedSelection} onClick={() => input.current?.click()}>{task ? 'Choose another file' : 'Choose a file'}</Button>
          <input ref={input} id="report-file" type="file" aria-label="Report file" accept={config.allowed_media_types.join(',')} hidden disabled={lockedSelection} onChange={(event) => { if (event.target.files) selectFiles(event.target.files); event.target.value = '' }} />
        </div>
        <p className="report-upload__guidance">PDF, JPEG or PNG · Up to {formatBytes(config.max_upload_bytes)} per file. File contents are validated on upload.</p>
        <label className="report-permission"><input type="checkbox" checked={permission} onChange={(event) => setPermission(event.target.checked)} disabled={busy} /><span>I have permission to store and extract text from this report. Files and derived text are private to my account and remain stored until I delete the report. Medical analysis is not included.</span></label>
        {error && <div className="form-error" role="alert">{error}</div>}
        {notice && <div className={phase === 'deleting' ? 'form-notice' : 'form-success'} role="status">{notice}</div>}
        {busy && <p className="report-progress" role="status"><span className="loading-spinner" aria-hidden="true" />{phase === 'reserving' ? 'Preparing your private upload…' : phase === 'cancelling' ? 'Confirming cancellation and cleanup…' : 'Uploading and validating your report…'}</p>}
        {task && phase !== 'uploaded' && <div className="report-upload__actions"><Button type="submit" disabled={busy || !permission}>{phase === 'failed' ? 'Retry upload' : 'Upload report'}</Button><Button variant="ghost" disabled={phase === 'cancelling'} onClick={cancel}>{phase === 'failed' ? 'Retry cancellation' : busy ? 'Cancel upload' : 'Clear selection'}</Button></div>}
      </form>
    </Card>
  )
}
