import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useHistoryAccount, useOwnedHistory } from '../observations/useOwnedHistory'
import { listNotifications, changeNotification, notificationMessages, onNotificationChanged } from '../../services/notifications'
import { errorMessage } from '../../services/api-client'
import { useI18n } from '../../i18n/core'
import { Button, ButtonLink } from '../../components/Button'
import { Card } from '../../components/Card'
import { PageHeader } from '../../components/PageHeader'

function useNotifications(offset: number) {
  const { owner, authFailure } = useHistoryAccount()
  const load = useCallback((signal: AbortSignal) => listNotifications(owner, offset, signal), [owner, offset])
  const result = useOwnedHistory(load, authFailure)
  const refreshResult = result.refresh
  useEffect(() => {
    const refresh = () => { if (document.visibilityState === 'visible') refreshResult() }
    const interval = setInterval(refresh, 60_000)
    document.addEventListener('visibilitychange', refresh)
    const unsubscribe = onNotificationChanged(refreshResult)
    return () => { clearInterval(interval); document.removeEventListener('visibilitychange', refresh); unsubscribe() }
  }, [refreshResult])
  return { ...result, owner, authFailure }
}

export function NotificationLink() {
  const { t } = useI18n(), result = useNotifications(0)
  return <Link to="/notifications" className="text-link notification-link">{result.data ? t('Notifications · {count} unread', { count: result.data.unread_count }) : t('Notifications')}</Link>
}

export function NotificationsPage() {
  const { t, copy } = useI18n()
  const [offset, setOffset] = useState(0), result = useNotifications(offset)
  const [busy, setBusy] = useState(false), [error, setError] = useState<string | null>(null)
  const operation = useRef<AbortController | null>(null)
  useEffect(() => () => { operation.current?.abort() }, [result.owner])
  async function change(action: 'read' | 'read_all' | 'delete', id: string | null = null) {
    if (operation.current) return
    const controller = new AbortController(); operation.current = controller
    setBusy(true); setError(null)
    try { await changeNotification(result.owner, action, id, controller.signal); controller.signal.throwIfAborted(); setOffset(0); result.refresh() }
    catch (failure) { if (!controller.signal.aborted) { setError(errorMessage(failure)); result.authFailure(failure) } }
    finally { if (!controller.signal.aborted) setBusy(false); if (operation.current === controller) operation.current = null }
  }
  return <><PageHeader eyebrow={t('YOUR WORKSPACE')} title={t('Notifications')} description={t('Operational updates about your reports. These are not medical alerts.')} />
    <Card className="history-panel"><p>{t('Notifications are kept for up to 30 days, with at most 100 recent notices. Deleting a report removes its notices. Updates refresh while this page is visible.')}</p>
      <div className="parameter-actions"><Button variant="secondary" onClick={result.refresh} disabled={busy}>{t('Refresh notifications')}</Button><Button onClick={() => { void change('read_all') }} disabled={busy || !result.data?.unread_count}>{t('Mark all read')}</Button><ButtonLink to="/settings" variant="ghost">{t('Notification preferences')}</ButtonLink></div>
      {result.loading && <p role="status">{t('Loading notifications…')}</p>}
      {(error || result.error) && <p role="alert" className="form-error">{copy(error || result.error || '')}</p>}
      {result.data && <><p role="status">{t('{count} unread notifications', { count: result.data.unread_count })}</p>
        {!result.data.items.length && <p>{t('No notifications in this view.')}</p>}
        <ul className="notification-list">{result.data.items.map(n => <li key={n.id} className="notification-item">
          <p><strong>{t(notificationMessages[n.event_type])}</strong></p>
          <p><span>{n.read_at ? t('Read') : t('Unread')}</span>{' · '}<time dateTime={n.created_at}>{new Date(n.created_at).toISOString()}</time></p>
          <div className="parameter-actions"><ButtonLink to="/reports" variant="ghost">{t('Open reports')}</ButtonLink>{!n.read_at && <Button size="sm" disabled={busy} onClick={() => { void change('read', n.id) }}>{t('Mark read')}</Button>}<Button size="sm" variant="ghost" disabled={busy} onClick={() => { void change('delete', n.id) }}>{t('Dismiss')}</Button></div>
        </li>)}</ul>
        <div className="parameter-actions">{offset > 0 && <Button variant="ghost" onClick={() => setOffset(0)}>{t('First page')}</Button>}{result.data.next_offset !== null && <Button onClick={() => setOffset(result.data!.next_offset!)}>{t('Older notifications')}</Button>}</div>
      </>}
    </Card></>
}
