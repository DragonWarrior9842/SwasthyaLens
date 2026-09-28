import { accountMutation, accountOwnedRead } from './auth'
import type { CopyKey } from '../i18n/core'

export const notificationMessages = {
  upload_completed: 'Your report upload completed.',
  extraction_completed: 'Text extraction completed. Open Reports to inspect the source text.',
  extraction_failed: 'Text extraction failed. Open Reports to review its status.',
  parameters_ready: 'Report parameters are ready for your personal review.',
  parameters_failed: 'Parameter extraction failed. Open Reports to review its status.',
} as const satisfies Record<string, CopyKey>
export interface Notification {
  id: string; user_id: string; report_id: string; event_type: keyof typeof notificationMessages
  created_at: string; read_at: string | null
}
export interface NotificationPage { user_id: string; items: Notification[]; unread_count: number; next_offset: number | null }
const uuid = (v: unknown): v is string => typeof v === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v)
const instant = (v: unknown): v is string => typeof v === 'string' && /(?:Z|[+-]\d{2}:\d{2})$/.test(v) && Number.isFinite(Date.parse(v))
export function decodeNotifications(value: unknown, owner: string): NotificationPage {
  if (!value || typeof value !== 'object') throw new Error('Invalid notifications')
  const p = value as Record<string, unknown>
  if (p.user_id !== owner || !uuid(p.user_id) || !Array.isArray(p.items) || p.items.length > 20 || !Number.isSafeInteger(p.unread_count) || Number(p.unread_count) < 0 || Number(p.unread_count) > 100 || !(p.next_offset === null || Number.isSafeInteger(p.next_offset) && Number(p.next_offset) > 0 && Number(p.next_offset) <= 100)) throw new Error('Invalid notifications')
  const seen = new Set<string>()
  const items = p.items.map((raw: unknown): Notification => {
    if (!raw || typeof raw !== 'object') throw new Error('Invalid notification')
    const row = raw as Record<string, unknown>
    if (Object.keys(row).sort().join() !== ['id','user_id','report_id','event_type','created_at','read_at'].sort().join() || !uuid(row.id) || seen.has(row.id) || row.user_id !== owner || !uuid(row.report_id) || typeof row.event_type !== 'string' || !Object.hasOwn(notificationMessages, row.event_type) || !instant(row.created_at) || !(row.read_at === null || instant(row.read_at) && Date.parse(row.read_at) >= Date.parse(row.created_at))) throw new Error('Invalid notification')
    seen.add(row.id)
    return row as unknown as Notification
  })
  return { user_id: owner, items, unread_count: Number(p.unread_count), next_offset: p.next_offset as number | null }
}
export const listNotifications = (owner: string, offset: number, signal: AbortSignal) => accountOwnedRead(`/notifications?offset=${offset}`, value => decodeNotifications(value, owner), owner, signal)
export async function changeNotification(owner: string, action: 'read' | 'read_all' | 'delete', id: string | null, signal: AbortSignal) {
  if (action !== 'read_all' && !uuid(id)) throw new Error('Invalid notification identifier')
  const result = await accountMutation(action === 'read_all' ? '/notifications/read-all' : `/notifications/${id}`, {}, value => decodeNotifications(value, owner), owner, action === 'read_all' ? 'POST' : action === 'read' ? 'PATCH' : 'DELETE', signal)
  notificationChanged()
  return result
}
const eventName = 'swasthyalens-notifications-changed'
function notificationChanged() {
  window.dispatchEvent(new Event(eventName))
  if (typeof BroadcastChannel !== 'undefined') { const channel = new BroadcastChannel(eventName); channel.postMessage('changed'); channel.close() }
}
export function onNotificationChanged(action: () => void) {
  window.addEventListener(eventName, action)
  const channel = typeof BroadcastChannel === 'undefined' ? null : new BroadcastChannel(eventName)
  if (channel) channel.onmessage = event => { if (event.data === 'changed') action() }
  return () => { window.removeEventListener(eventName, action); channel?.close() }
}
