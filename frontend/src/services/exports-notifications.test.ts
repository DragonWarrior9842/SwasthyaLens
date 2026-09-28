import { afterEach, describe, expect, it, vi } from 'vitest'
import { requestExportBlob } from './api-client'
import { accountExport } from './auth'
import { decodeNotifications, notificationMessages } from './notifications'
import { decodeSettings } from './account'
import { hindi } from '../i18n/hindi'

const owner = '11111111-1111-4111-8111-111111111111', foreign = '22222222-2222-4222-8222-222222222222'
const event = { id: foreign, user_id: owner, report_id: owner, event_type: 'upload_completed', created_at: '2026-09-27T00:00:00Z', read_at: null }
const page = { user_id: owner, items: [event], unread_count: 1, next_offset: null }
const bytes = new TextEncoder().encode('"Original value"\r\n"13.20"\r\n')
const options = { method: 'POST' as const, body: { format: 'csv' }, csrfToken: 'synthetic', credentials: 'include' as const }
function response(headers: Record<string, string> = {}, data: Uint8Array<ArrayBuffer> = bytes) {
  return new Response(data, { headers: { 'Content-Type': 'text/csv; charset=utf-8', 'Content-Length': String(bytes.length), 'Content-Disposition': 'attachment; filename="swasthyalens-health.csv"', 'Cache-Control': 'no-store', ...headers } })
}
afterEach(() => vi.unstubAllGlobals())

describe('private export byte boundary', () => {
  it('uses explicit POST and preserves exact bytes', async () => {
    const fetch = vi.fn().mockResolvedValue(response()); vi.stubGlobal('fetch', fetch)
    const blob = await requestExportBlob('csv', options)
    expect(await blob.text()).toBe(new TextDecoder().decode(bytes))
    expect(fetch).toHaveBeenCalledWith('/api/exports', expect.objectContaining({ method: 'POST', credentials: 'include', cache: 'no-store', redirect: 'error', headers: expect.objectContaining({ 'X-CSRF-Token': 'synthetic' }) }))
  })
  it.each([{ 'Content-Type': 'text/html' }, { 'Content-Length': '99999999' }, { 'Content-Length': '0' }, { 'Content-Length': '1' }, { 'Content-Disposition': 'inline' }, { 'Cache-Control': 'public' }])('rejects malformed or unsafe attachment headers %j', async headers => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(headers)))
    await expect(requestExportBlob('csv', options)).rejects.toMatchObject({ code: 'invalid-response' })
  })
  it('rejects incomplete streams and private-data transport misconfiguration', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({}, bytes.slice(0, 2))))
    await expect(requestExportBlob('csv', options)).rejects.toMatchObject({ code: 'invalid-response' })
    await expect(requestExportBlob('csv', { ...options, method: 'GET' })).rejects.toMatchObject({ code: 'configuration' })
    await expect(requestExportBlob('csv', { ...options, csrfToken: '' })).rejects.toMatchObject({ code: 'configuration' })
  })
  it('rejects account changes before generating any file', async () => {
    const fetch = vi.fn().mockResolvedValue(Response.json({ user: { id: foreign, email: 'synthetic@example.invalid' }, expires_at: 2000000000 })); vi.stubGlobal('fetch', fetch)
    await expect(accountExport({}, 'csv', owner, new AbortController().signal)).rejects.toMatchObject({ code: 'account_changed' })
    expect(fetch).toHaveBeenCalledTimes(1)
  })
  it('uses current account and CSRF checks without automatic retries', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(Response.json({ user: { id: owner, email: 'synthetic@example.invalid' }, expires_at: 2000000000 })).mockResolvedValueOnce(Response.json({ csrf_token: 'synthetic' })).mockResolvedValueOnce(Response.json({ code: 'export_capacity' }, { status: 422 })); vi.stubGlobal('fetch', fetch)
    await expect(accountExport({}, 'csv', owner, new AbortController().signal)).rejects.toMatchObject({ code: 'export_capacity' })
    expect(fetch).toHaveBeenCalledTimes(3)
  })
})

describe('closed owner-scoped localized notifications', () => {
  it('decodes generic notices without adding clinical data', () => { expect(decodeNotifications(page, owner)).toEqual(page) })
  it.each([{ user_id: foreign }, { unread_count: -1 }, { unread_count: 101 }, { unread_count: true }, { next_offset: 101 }, { items: [event, event] }, { items: [{ ...event, user_id: foreign }] }, { items: [{ ...event, event_type: 'urgent_medical_alert' }] }, { items: [{ ...event, event_type: 'constructor' }] }, { items: [{ ...event, value: '18 ng/mL' }] }, { items: [{ ...event, read_at: '2020-01-01T00:00:00Z' }] }])('rejects malformed notifications %j', change => {
    expect(() => decodeNotifications({ ...page, ...change }, owner)).toThrow()
  })
  it('localizes every stored event type without changing the source event', () => {
    for (const message of Object.values(notificationMessages)) expect(hindi[message].trim()).not.toBe('')
    expect(event.event_type).toBe('upload_completed')
  })
  it.each([undefined, null, 'true', 1])('rejects malformed notification preference %j', value => {
    expect(() => decodeSettings({ user_id: owner, preferred_language: 'en', assistant_language: 'en', timezone: 'UTC', in_app_notifications: value, created_at: event.created_at, updated_at: event.created_at })).toThrow()
  })
})
