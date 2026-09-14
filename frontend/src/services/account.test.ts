import { describe, expect, it, vi } from 'vitest'
import { decodeProfile, decodeSettings, saveProfile, saveSettings } from './account'

const profile = { id: 'b4d0e66a-c0d1-42dc-b495-d1a29acde1c7', display_name: null, created_at: '2026-09-14T00:00:00Z', updated_at: '2026-09-14T00:00:00Z' }
const settings = { user_id: profile.id, preferred_language: 'en', timezone: 'Asia/Kolkata', created_at: profile.created_at, updated_at: profile.updated_at }
const session = { user: { id: profile.id, email: 'owner@example.test' }, expires_at: Math.floor(Date.now() / 1000) + 3600 }

describe('account records', () => {
  it('keeps nullable display names and audit metadata', () => {
    expect(decodeProfile(profile)).toEqual(profile)
    expect(decodeSettings(settings)).toEqual(settings)
  })
  it.each([null, { ...profile, display_name: 42 }, { ...profile, updated_at: 'not a date' }])('rejects malformed profile records', (value) => {
    expect(() => decodeProfile(value)).toThrow()
  })
  it('rejects unsupported languages instead of pretending they work', () => {
    expect(() => decodeSettings({ ...settings, preferred_language: 'fr' })).toThrow()
  })
  it('writes only the editable name', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(Response.json(session)).mockResolvedValueOnce(Response.json({ csrf_token: 'test-only' })).mockResolvedValueOnce(Response.json({ ...profile, display_name: 'Chosen name' }))
    vi.stubGlobal('fetch', fetchMock)
    await saveProfile('Chosen name', profile.id)
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/api/profile', expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ display_name: 'Chosen name' }) }))
  })
  it('does not forward extra ownership/audit fields when saving preferences', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValueOnce(Response.json(session)).mockResolvedValueOnce(Response.json({ csrf_token: 'test-only' })).mockResolvedValueOnce(Response.json(settings))
    vi.stubGlobal('fetch', fetchMock)
    await saveSettings({ ...settings, preferred_language: 'hi' }, profile.id)
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/api/settings', expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ preferred_language: 'hi', timezone: settings.timezone }) }))
  })
})
