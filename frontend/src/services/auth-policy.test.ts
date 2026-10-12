import { describe, expect, it, vi } from 'vitest'
import { decodeAuthPolicy, readAuthPolicy, signUp } from './auth'

describe('server-controlled public auth policy', () => {
  it.each([false, true])('reads the explicit signup policy %s without caching', async enabled => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(Response.json({ public_signup_enabled: enabled, public_recovery_enabled: false }))
    vi.stubGlobal('fetch', fetchMock)
    await expect(readAuthPolicy()).resolves.toEqual({ publicSignupEnabled: enabled, publicRecoveryEnabled: false })
    expect(fetchMock).toHaveBeenCalledWith('/api/auth/policy', expect.objectContaining({ method: 'GET', cache: 'no-store', credentials: 'include' }))
  })

  it.each([null, {}, { public_signup_enabled: 'true', public_recovery_enabled: false }, { public_signup_enabled: true }, { public_signup_enabled: true, public_recovery_enabled: true }])('rejects missing or unexpected policy rather than enabling flows', payload => {
    expect(() => decodeAuthPolicy(payload)).toThrow('Invalid account policy')
  })

  it('does not retry an unavailable policy', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 503 }))
    vi.stubGlobal('fetch', fetchMock)
    await expect(readAuthPolicy()).rejects.toThrow()
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('displays a safe registration denial even for a stale client', async () => {
    const fetchMock = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(Response.json({ csrf_token: 'synthetic-csrf' }))
      .mockResolvedValueOnce(Response.json({ code: 'public_auth_disabled', message: 'must-not-render' }, { status: 403 }))
    vi.stubGlobal('fetch', fetchMock)
    await expect(signUp('synthetic@example.test', 'test-only-passphrase')).rejects.toThrow('Public registration is unavailable. Contact the administrator.')
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})
