import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../../components/Button'
import { errorMessage } from '../../services/api-client'
import { publishObservation } from '../../services/observations'
import type { Review } from '../../services/parameters'

export function PublishObservation({ reportId, candidateId, ownerId, review, onAuthFailure }: { reportId: string; candidateId: string; ownerId: string; review: Review; onAuthFailure: (error: unknown) => void }) {
  const [date, setDate] = useState(''), [busy, setBusy] = useState(false), [published, setPublished] = useState(false), [error, setError] = useState<string | null>(null)
  const operation = useRef<AbortController | null>(null)
  useEffect(() => () => operation.current?.abort(), [])
  if (review.action === 'rejected' || !review.fields.raw_value?.trim()) return null
  return <form className="observation-publish" onSubmit={event => {
    event.preventDefault(); if (operation.current) return
    const controller = new AbortController(); operation.current = controller; setBusy(true); setError(null)
    void publishObservation(reportId, candidateId, review.revision, date || null, ownerId, controller.signal).then(() => { if (!controller.signal.aborted) setPublished(true) }).catch((failure: unknown) => { if (!controller.signal.aborted) { setError(errorMessage(failure)); onAuthFailure(failure) } }).finally(() => { operation.current = null; if (!controller.signal.aborted) setBusy(false) })
  }}>
    <p>Publish this personally reviewed revision to health history. A later review change removes it from active history until you publish again.</p>
    <label>Measurement date (optional, confirmed by you)<input type="date" min="1900-01-01" max="2100-12-31" value={date} disabled={busy || published} onChange={event => setDate(event.target.value)} /></label>
    <p>Leave blank if unknown. Upload time will not be used as a measurement date.</p>
    <Button size="sm" type="submit" disabled={busy || published}>{busy ? 'Publishing…' : published ? 'Published to health history' : 'Publish to health history'}</Button>{' '}<Link to={`/history?report_id=${reportId}`}>View report observations</Link>
    {published && <p role="status">Published this review revision. To change its date later, create a new review revision and publish again.</p>}
    {error && <p className="form-error" role="alert">{error}</p>}
  </form>
}
