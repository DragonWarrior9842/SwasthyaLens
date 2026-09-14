import { describe, expect, it, vi } from 'vitest'
import { ApiError, requestJson } from './api-client'
import { accountPatch, decodeSession, restoreSession, signIn, signOut, signUp, verifyEmail, withSessionLock } from './auth'

const session = () => ({ user: { id: 'b4d0e66a-c0d1-42dc-b495-d1a29acde1c7', email: 'owner@example.test' }, expires_at: Math.floor(Date.now() / 1000) + 3600 })
const csrf = { csrf_token: 'test-csrf-token' }
const unauthorized = () => Response.json({ code: 'unauthenticated', message: 'Never show raw values' }, { status: 401 })
const unavailable = () => Response.json({ code: 'service_unavailable', message: 'Never show provider credentials' }, { status: 503 })

describe('cookie account transport', () => {
  it('uses a signed CSRF header, cookies and JSON without browser provider tokens', async () => {
    const result = session()
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(Response.json(csrf)).mockResolvedValueOnce(Response.json(result))
    vi.stubGlobal('fetch', fetchMock)
    await expect(signIn('owner@example.test', 'test-only-passphrase')).resolves.toEqual(result)
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/auth/csrf', expect.objectContaining({ method: 'GET', credentials: 'include', cache: 'no-store', redirect: 'error' }))
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/auth/login', expect.objectContaining({
      method: 'POST', credentials: 'include', cache: 'no-store', redirect: 'error',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRF-Token': csrf.csrf_token },
      body: JSON.stringify({ email: 'owner@example.test', password: 'test-only-passphrase' }),
    }))
  })

  it('will not send authenticated requests to another origin', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://untrusted.example')
    vi.stubGlobal('window', { location: { origin: 'http://127.0.0.1:5173' } })
    const fetchMock = vi.fn<typeof fetch>()
    vi.stubGlobal('fetch', fetchMock)
    await expect(signIn('owner@example.test', 'test-only-passphrase')).rejects.toMatchObject({ code: 'configuration' })
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it.each([
    [{ code: 'invalid_credentials', message: 'raw provider secret' }, 'invalid_credentials', 'The email or password is incorrect.'],
    [{ code: 'csrf_failed', message: 'raw nonce' }, 'csrf_failed', 'The security check expired. Please submit the form again.'],
    [{ code: '__proto__', message: 'raw input' }, 'http', 'The local API returned an unsuccessful response.'],
  ])('renders only allowlisted local messages', async (body, code, message) => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(Response.json(body, { status: 403 })))
    await expect(requestJson('/profile', (value) => value, { credentials: 'include' })).rejects.toMatchObject({ code, message, status: 403 })
  })

  it('does not submit or replay a write when CSRF bootstrap fails', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(unavailable())
    vi.stubGlobal('fetch', fetchMock)
    await expect(accountPatch('/profile', { display_name: 'A' }, (value) => value, session().user.id)).rejects.toMatchObject({ status: 503 })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('does not replay a failed mutation', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(Response.json(session())).mockResolvedValueOnce(Response.json(csrf)).mockRejectedValueOnce(new TypeError('network'))
    vi.stubGlobal('fetch', fetchMock)
    await expect(accountPatch('/profile', { display_name: 'A' }, (value) => value, session().user.id)).rejects.toMatchObject({ code: 'network' })
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('prevents a queued profile write from following a cross-tab account switch', async () => {
    const changed = { ...session(), user: { id: '40b420cb-ebef-4526-98ad-07f55c921a24', email: 'other@example.test' } }
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(Response.json(changed))
    vi.stubGlobal('fetch', fetchMock)
    const accountSwitch = withSessionLock(() => Promise.resolve())
    const queuedWrite = accountPatch('/profile', { display_name: 'Previous account name' }, (value) => value, session().user.id)
    await accountSwitch
    await expect(queuedWrite).rejects.toMatchObject({ code: 'account_changed' })
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledWith('/api/auth/me', expect.objectContaining({ method: 'GET' }))
  })

  it('validates signup acknowledgements without displaying their text', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(Response.json(csrf)).mockResolvedValueOnce(Response.json({ message: 'Account-sensitive provider text' }))
    vi.stubGlobal('fetch', fetchMock)
    await expect(signUp('owner@example.test', 'test-only-passphrase')).resolves.toBeUndefined()
  })

  it('submits confirmation codes only in the request body', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(Response.json(csrf)).mockResolvedValueOnce(Response.json(session()))
    vi.stubGlobal('fetch', fetchMock)
    await verifyEmail('owner@example.test', '123456')
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/auth/verify-email', expect.objectContaining({ body: JSON.stringify({ email: 'owner@example.test', token: '123456' }) }))
  })
})

describe('session restoration and rotation', () => {
  it('keeps a valid session without rotating it unnecessarily', async () => {
    const current = session()
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(Response.json(current))
    vi.stubGlobal('fetch', fetchMock)
    await expect(restoreSession()).resolves.toEqual(current)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('refreshes an expired access cookie once with CSRF protection', async () => {
    const next = session()
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(unauthorized()).mockResolvedValueOnce(Response.json(csrf)).mockResolvedValueOnce(Response.json(next))
    vi.stubGlobal('fetch', fetchMock)
    await expect(restoreSession()).resolves.toEqual(next)
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/api/auth/refresh', expect.objectContaining({ method: 'POST', body: '{}' }))
  })

  it('rotates a token before its expiry', async () => {
    const next = session()
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(Response.json({ ...next, expires_at: Math.floor(Date.now() / 1000) + 10 })).mockResolvedValueOnce(Response.json(csrf)).mockResolvedValueOnce(Response.json(next))
    vi.stubGlobal('fetch', fetchMock)
    await expect(restoreSession()).resolves.toEqual(next)
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('shares simultaneous refresh attempts within the tab', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(unauthorized()).mockResolvedValueOnce(Response.json(csrf)).mockResolvedValueOnce(Response.json(session()))
    vi.stubGlobal('fetch', fetchMock)
    const first = restoreSession()
    const second = restoreSession()
    expect(first).toBe(second)
    await Promise.all([first, second])
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('ends an expired refresh session without a retry loop', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(unauthorized()).mockResolvedValueOnce(Response.json(csrf)).mockResolvedValueOnce(unauthorized())
    vi.stubGlobal('fetch', fetchMock)
    await expect(restoreSession()).resolves.toBeNull()
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('distinguishes provider outages from signed-out sessions', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(unavailable())
    vi.stubGlobal('fetch', fetchMock)
    await expect(restoreSession()).rejects.toMatchObject({ code: 'service_unavailable', status: 503 })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('does not turn refresh network failure into anonymous state', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValueOnce(unauthorized()).mockResolvedValueOnce(Response.json(csrf)).mockRejectedValueOnce(new TypeError('Offline')))
    await expect(restoreSession()).rejects.toBeInstanceOf(ApiError)
  })

  it('coordinates session operations through the cross-tab Web Lock', async () => {
    const request = vi.fn((_name: string, operation: () => Promise<string>) => operation())
    vi.stubGlobal('navigator', { locks: { request } })
    await expect(withSessionLock(() => Promise.resolve('done'))).resolves.toBe('done')
    expect(request).toHaveBeenCalledWith('swasthyalens-session', expect.any(Function))
  })

  it('keeps logout after an in-flight operation even if that operation rejects', async () => {
    const order: string[] = []
    const first = withSessionLock(async () => { order.push('first'); throw new Error('fail') }).catch(() => undefined)
    const second = withSessionLock(async () => { order.push('second') })
    await Promise.all([first, second])
    expect(order).toEqual(['first', 'second'])
  })
})

describe('logout guarantees', () => {
  it('reports revoked only after a valid logout acknowledgement', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValueOnce(Response.json(csrf)).mockResolvedValueOnce(Response.json({ message: 'Signed out' })))
    await expect(signOut()).resolves.toBe('revoked')
  })

  it('distinguishes the logout response that clears cookies during an outage', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValueOnce(Response.json(csrf)).mockResolvedValueOnce(Response.json({ code: 'logout_incomplete', message: 'Only safe local text is shown' }, { status: 503 })))
    await expect(signOut()).resolves.toBe('local-only')
  })

  it('does not assume a proxy or configuration 503 cleared any cookie', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValueOnce(Response.json(csrf)).mockResolvedValueOnce(unavailable()))
    await expect(signOut()).rejects.toMatchObject({ code: 'service_unavailable', status: 503 })
  })

  it('cannot claim cookie removal when the preliminary CSRF call is unavailable', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(unavailable())
    vi.stubGlobal('fetch', fetchMock)
    await expect(signOut()).rejects.toMatchObject({ status: 503 })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('cannot claim logout after a dropped response', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValueOnce(Response.json(csrf)).mockRejectedValueOnce(new TypeError('Offline')))
    await expect(signOut()).rejects.toMatchObject({ code: 'network' })
  })
})

describe('session response validation', () => {
  it('retains only the minimal identity contract', () => {
    const value = session()
    expect(decodeSession({ ...value, access_token: 'should-not-be-used', user: { ...value.user, role: 'admin' } })).toEqual(value)
  })

  it.each([null, {}, { user: { id: 'editable-user-id', email: 'x' }, expires_at: 1 }, { ...session(), expires_at: 'tomorrow' }, { ...session(), expires_at: -1 }])('rejects malformed identity or expiry', (payload) => {
    expect(() => decodeSession(payload)).toThrow()
  })
})
