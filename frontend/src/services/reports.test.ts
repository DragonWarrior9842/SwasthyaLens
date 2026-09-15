import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Report, ReportConfig } from '../types/reports'
import { requestReportBlob, requestReportUpload } from './api-client'
import { withSessionLock } from './auth'
import { cleanupReports, decodeDeletion, decodeReport, decodeReportConfig, decodeReportPage, deleteReport, downloadReport, filenameError, getReport, listReports, reserveReport, saveReportAttachment, uploadReport, validateReportFile } from './reports'

// Neutral transport fixtures only. Production records always come from the authenticated API.
const owner = 'b4d0e66a-c0d1-42dc-b495-d1a29acde1c7'
const report: Report = { id: '62fdbbd0-91a1-4e2b-9b5c-5e1bde61edce', original_filename: 'report.pdf', media_type: 'application/pdf', size_bytes: 5, status: 'uploaded', created_at: '2026-09-15T00:00:00Z', updated_at: '2026-09-15T00:00:00Z', error_category: null }
const config: ReportConfig = { max_upload_bytes: 5 * 1024 * 1024, allowed_media_types: ['application/pdf', 'image/jpeg', 'image/png'] }
const session = { user: { id: owner, email: 'owner@example.test' }, expires_at: Math.floor(Date.now() / 1000) + 3600 }
const csrf = { csrf_token: 'test-only-nonce' }
const file = () => new File(['%PDF-'], 'report.pdf', { type: 'application/pdf' })
const filePath = `/reports/${report.id}/file`

function signedMutation(response: Response) {
  const mock = vi.fn<typeof fetch>().mockResolvedValueOnce(Response.json(session)).mockResolvedValueOnce(Response.json(csrf)).mockResolvedValueOnce(response)
  vi.stubGlobal('fetch', mock)
  return mock
}

function attachment(body = '%PDF-', headers: Record<string, string> = {}) {
  return new Response(body, { headers: { 'Content-Type': 'application/pdf', 'Content-Disposition': 'attachment; filename="report.pdf"', ...headers } })
}

afterEach(() => { vi.useRealTimers() })

describe('report metadata response boundaries', () => {
  it('keeps only public metadata and excludes storage paths, hashes and leases', () => {
    expect(decodeReport({ ...report, user_id: owner, storage_path: 'private/provider/path', sha256: 'private-hash', lease_token: 'private-lease' })).toEqual(report)
  })

  it.each([
    null, [], { ...report, id: '../other' }, { ...report, size_bytes: 0 },
    { ...report, size_bytes: 5 * 1024 * 1024 + 1 }, { ...report, original_filename: '../report.pdf' },
    { ...report, media_type: 'text/html' }, { ...report, original_filename: 'report.png' },
    { ...report, status: 'processed' }, { ...report, status: 'deleted' },
    { ...report, created_at: '123' }, { ...report, error_category: 'provider-secret-detail' },
  ])('rejects malformed or unsupported metadata', (value) => { expect(() => decodeReport(value)).toThrow() })

  it('accepts real pending states without claiming processing exists', () => {
    expect(decodeReport({ ...report, status: 'upload_failed', error_category: 'storage_unavailable' }).status).toBe('upload_failed')
    expect(decodeReport({ ...report, status: 'deleting' }).status).toBe('deleting')
    expect(decodeDeletion({ report_id: report.id, status: 'deleting' }).status).toBe('deleting')
  })

  it('validates bounded pages, duplicate identities and advancing cursor contracts', () => {
    expect(decodeReportPage({ reports: [report], next_cursor: 'opaque-cursor' })).toEqual({ reports: [report], next_cursor: 'opaque-cursor' })
    expect(() => decodeReportPage({ reports: [report, report], next_cursor: null })).toThrow()
    expect(() => decodeReportPage({ reports: Array.from({ length: 21 }, () => report), next_cursor: null })).toThrow()
    expect(() => decodeReportPage({ reports: [], next_cursor: '' })).toThrow()
  })

  it('cannot raise server limits beyond the bucket cap or allow other content types', () => {
    expect(decodeReportConfig({ ...config, max_upload_bytes: 1024 })).toEqual({ ...config, max_upload_bytes: 1024 })
    expect(() => decodeReportConfig({ ...config, max_upload_bytes: config.max_upload_bytes + 1 })).toThrow()
    expect(() => decodeReportConfig({ ...config, allowed_media_types: ['image/svg+xml'] })).toThrow()
    expect(() => decodeReportConfig({ ...config, allowed_media_types: ['image/png', 'image/png'] })).toThrow()
  })
})

describe('local file selection feedback', () => {
  it.each(['../report.pdf', 'C:\\report.pdf', 'a/b.pdf', '.hidden.pdf', 'report..pdf', 'report.pdf ', 'nul.pdf', 'LPT1.report.pdf', 'report\u202epdf.png', 'bad\u0000.pdf', `${'a'.repeat(121)}.pdf`, `${'क'.repeat(80)}.pdf`, 'private\ue000.pdf'])('rejects unsafe filenames', (name) => {
    expect(filenameError(name)).not.toBeNull()
  })

  it('accepts ordinary Unicode names, normalized combining marks and duplicate filenames', () => {
    expect(filenameError('जाँच रिपोर्ट.pdf')).toBeNull()
    expect(filenameError('Re\u0301sultats.pdf')).toBeNull()
    expect(validateReportFile(file(), config)).toBeNull()
    expect(validateReportFile(file(), config)).toBeNull()
  })

  it.each([
    [new File([], 'empty.pdf', { type: 'application/pdf' }), 'empty'],
    [new File(['x'], 'file.svg', { type: 'image/svg+xml' }), 'matching'],
    [new File(['x'], 'file.pdf', { type: 'image/png' }), 'matching'],
    [new File(['x'], 'pdf', { type: 'application/pdf' }), 'matching'],
    [new File(['x'], 'file.pdf'), 'matching'],
    [new File([new Uint8Array(1025)], 'large.pdf', { type: 'application/pdf' }), 'limit'],
  ])('rejects invalid selection before reservation', (selected, message) => {
    expect(validateReportFile(selected, { ...config, max_upload_bytes: 1024 })).toContain(message)
  })

  it('accepts only configured formats and leaves byte inspection to the API', () => {
    expect(validateReportFile(new File(['neutral test bytes'], 'report.JPEG', { type: 'image/jpeg' }), config)).toBeNull()
    expect(validateReportFile(new File(['neutral test bytes'], 'report.png', { type: 'image/png' }), config)).toBeNull()
    expect(validateReportFile(file(), { ...config, allowed_media_types: ['image/png'] })).not.toBeNull()
  })
})

describe('authenticated report operations', () => {
  it('reserves metadata with a stable idempotency key, fresh CSRF and no authoritative owner field', async () => {
    const key = '0a05c72b-9855-4db5-9f0b-8b4709bb0737'
    const mock = signedMutation(Response.json({ ...report, status: 'pending_upload' }))
    await reserveReport(file(), key, owner)
    expect(mock).toHaveBeenNthCalledWith(1, '/api/auth/me', expect.objectContaining({ credentials: 'include' }))
    expect(mock).toHaveBeenNthCalledWith(3, '/api/reports', expect.objectContaining({ method: 'POST', credentials: 'include', cache: 'no-store', redirect: 'error', headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRF-Token': csrf.csrf_token }, body: JSON.stringify({ original_filename: 'report.pdf', media_type: 'application/pdf', size_bytes: 5, idempotency_key: key }) }))
  })

  it('uploads the raw file with exact MIME, cookies and fresh CSRF inside session coordination', async () => {
    const selected = file()
    const mock = signedMutation(Response.json(report))
    await expect(uploadReport(report.id, selected, owner)).resolves.toEqual(report)
    expect(mock).toHaveBeenNthCalledWith(3, `/api${filePath}`, expect.objectContaining({ method: 'PUT', credentials: 'include', body: selected, headers: { Accept: 'application/json', 'Content-Type': 'application/pdf', 'X-CSRF-Token': csrf.csrf_token }, cache: 'no-store', redirect: 'error' }))
  })

  it.each(['upload', 'delete', 'list', 'download'] as const)('blocks %s when the current account differs from the mounted owner', async (operation) => {
    const mock = vi.fn<typeof fetch>().mockResolvedValue(Response.json({ ...session, user: { id: 'f4208c2c-91db-4a7c-8c1a-e3f23ad671df', email: 'other@example.test' } }))
    vi.stubGlobal('fetch', mock)
    const attempt = operation === 'upload' ? uploadReport(report.id, file(), owner) : operation === 'delete' ? deleteReport(report.id, owner) : operation === 'list' ? listReports(owner) : downloadReport(report, owner)
    await expect(attempt).rejects.toMatchObject({ code: 'account_changed' })
    expect(mock).toHaveBeenCalledTimes(1)
  })

  it('never automatically replays an uncertain file transfer', async () => {
    const mock = signedMutation(Response.json(report))
    mock.mockReset().mockResolvedValueOnce(Response.json(session)).mockResolvedValueOnce(Response.json(csrf)).mockRejectedValueOnce(new TypeError('Connection lost'))
    await expect(uploadReport(report.id, file(), owner)).rejects.toMatchObject({ code: 'network' })
    expect(mock).toHaveBeenCalledTimes(3)
  })

  it('does not send a cancelled operation after it has waited for the session lock', async () => {
    const controller = new AbortController()
    const mock = vi.fn<typeof fetch>()
    vi.stubGlobal('fetch', mock)
    let release: () => void = () => undefined
    const gate = new Promise<void>((resolve) => { release = resolve })
    const earlier = withSessionLock(() => gate)
    const queued = uploadReport(report.id, file(), owner, controller.signal)
    const assertion = expect(queued).rejects.toMatchObject({ name: 'AbortError' })
    controller.abort()
    release()
    await earlier
    await assertion
    expect(mock).not.toHaveBeenCalled()
  })

  it('uses JSON plus CSRF for deletion and preserves a pending acknowledgement', async () => {
    const mock = signedMutation(Response.json({ report_id: report.id, status: 'deleting' }, { status: 202 }))
    await expect(deleteReport(report.id, owner)).resolves.toEqual({ report_id: report.id, status: 'deleting' })
    expect(mock).toHaveBeenNthCalledWith(3, `/api/reports/${report.id}`, expect.objectContaining({ method: 'DELETE', body: '{}', headers: expect.objectContaining({ 'Content-Type': 'application/json', 'X-CSRF-Token': csrf.csrf_token }) }))
  })

  it('rejects deletion acknowledgement for an unrelated report', async () => {
    signedMutation(Response.json({ report_id: owner, status: 'deleted' }))
    await expect(deleteReport(report.id, owner)).rejects.toThrow('Mismatched deletion acknowledgement')
  })

  it('requests only owner-scoped cleanup and validates its outcome', async () => {
    const mock = signedMutation(Response.json({ pending: 1, cleaned: 2 }))
    await expect(cleanupReports(owner)).resolves.toEqual({ pending: 1, cleaned: 2 })
    expect(mock).toHaveBeenNthCalledWith(3, '/api/reports/cleanup', expect.objectContaining({ method: 'POST', body: '{}' }))
  })

  it('uses an encoded list cursor and validates detail identifiers before a request', async () => {
    const mock = vi.fn<typeof fetch>().mockResolvedValueOnce(Response.json(session)).mockResolvedValueOnce(Response.json({ reports: [report], next_cursor: null }))
    vi.stubGlobal('fetch', mock)
    await listReports(owner, 'cursor&owner=someone-else')
    expect(mock).toHaveBeenNthCalledWith(2, '/api/reports?cursor=cursor%26owner%3Dsomeone-else', expect.objectContaining({ method: 'GET' }))
    expect(() => getReport('../other', owner)).toThrow('Invalid report identifier')
  })

  it('does not display provider details, filenames or raw validation input in failures', async () => {
    signedMutation(Response.json({ code: 'invalid_file', message: 'private report contents', detail: 'provider path' }, { status: 422 }))
    await expect(uploadReport(report.id, file(), owner)).rejects.toMatchObject({ code: 'invalid_file', message: 'This file could not be accepted. Choose a valid PDF, JPEG or PNG report.' })
  })
})

describe('raw transport and private attachments', () => {
  it('cannot use the binary transport to bypass JSON-only auth or omit CSRF/cookies', async () => {
    const mock = vi.fn<typeof fetch>()
    vi.stubGlobal('fetch', mock)
    await expect(requestReportUpload('/auth/login', file(), decodeReport, { credentials: 'include', csrfToken: 'test' })).rejects.toMatchObject({ code: 'configuration' })
    await expect(requestReportUpload(filePath, file(), decodeReport, { credentials: 'include' })).rejects.toMatchObject({ code: 'configuration' })
    await expect(requestReportUpload(filePath, file(), decodeReport, { csrfToken: 'test' })).rejects.toMatchObject({ code: 'configuration' })
    expect(mock).not.toHaveBeenCalled()
  })

  it('rejects authenticated file transport to a different origin before transmission', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://untrusted.example')
    vi.stubGlobal('window', { location: { origin: 'http://127.0.0.1:5173' } })
    const mock = vi.fn<typeof fetch>()
    vi.stubGlobal('fetch', mock)
    await expect(requestReportUpload(filePath, file(), decodeReport, { credentials: 'include', csrfToken: 'test' })).rejects.toMatchObject({ code: 'configuration' })
    await expect(requestReportBlob(filePath, report.media_type, report.size_bytes, { credentials: 'include' })).rejects.toMatchObject({ code: 'configuration' })
    expect(mock).not.toHaveBeenCalled()
  })

  it('downloads bytes only after an owner recheck with bounded attachment headers', async () => {
    const mock = vi.fn<typeof fetch>().mockResolvedValueOnce(Response.json(session)).mockResolvedValueOnce(attachment('%PDF-', { 'Content-Length': '5' }))
    vi.stubGlobal('fetch', mock)
    const blob = await downloadReport(report, owner)
    expect(await blob.text()).toBe('%PDF-')
    expect(mock).toHaveBeenNthCalledWith(2, `/api${filePath}`, expect.objectContaining({ method: 'GET', credentials: 'include', cache: 'no-store', redirect: 'error', headers: { Accept: 'application/pdf' } }))
  })

  it.each([
    ['%PDF-', { 'Content-Type': 'text/html' }],
    ['%PDF-', { 'Content-Disposition': 'inline' }],
    ['%PDF-', { 'Content-Length': '6' }],
    ['%PDF-', { 'Content-Length': '-5' }],
    ['%PDF-excess', {}],
    ['%PDF', {}],
  ] as [string, Record<string, string>][])('rejects unsafe, oversized or incomplete download responses', async (body, headers) => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(attachment(body, headers)))
    await expect(requestReportBlob(filePath, report.media_type, report.size_bytes, { credentials: 'include' })).rejects.toMatchObject({ code: 'invalid-response' })
  })

  it('bounds stalled binary requests without replay', async () => {
    vi.useFakeTimers()
    const mock = vi.fn<typeof fetch>().mockImplementation((_path, init) => new Promise((_resolve, reject) => {
      init?.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true })
    }))
    vi.stubGlobal('fetch', mock)
    const assertion = expect(requestReportUpload(filePath, file(), decodeReport, { credentials: 'include', csrfToken: 'test', timeoutMs: 100 })).rejects.toMatchObject({ code: 'timeout' })
    await vi.advanceTimersByTimeAsync(100)
    await assertion
    expect(mock).toHaveBeenCalledTimes(1)
  })

  it('forces an attachment download and releases its temporary object URL', () => {
    vi.useFakeTimers()
    const create = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:test-only')
    const revoke = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined)
    const link = { href: '', download: '', rel: '', click: vi.fn(), remove: vi.fn() }
    const append = vi.fn()
    vi.stubGlobal('document', { createElement: vi.fn(() => link), body: { append } })
    vi.stubGlobal('window', { setTimeout })
    saveReportAttachment(new Blob(['%PDF-']), 'report.pdf')
    expect(create).toHaveBeenCalledTimes(1)
    expect(link.download).toBe('report.pdf')
    expect(link.href).toBe('blob:test-only')
    expect(link.click).toHaveBeenCalledTimes(1)
    expect(link.remove).toHaveBeenCalledTimes(1)
    expect(revoke).not.toHaveBeenCalled()
    vi.advanceTimersByTime(1000)
    expect(revoke).toHaveBeenCalledWith('blob:test-only')
  })
})
