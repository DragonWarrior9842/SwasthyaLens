import { describe, expect, it } from 'vitest'
import { sessionCheckDelay } from './session-timing'

describe('session check scheduling', () => {
  const now = Date.UTC(2026, 8, 15)
  it('checks a normal access token before expiry', () => {
    expect(sessionCheckDelay(now / 1000 + 3600, now)).toBe(3_555_000)
  })
  it('does not repeatedly refresh in the last minute of the absolute session lifetime', () => {
    expect(sessionCheckDelay(now / 1000 + 45, now)).toBe(46_000)
  })
  it('schedules a prompt check for an already expired session', () => {
    expect(sessionCheckDelay(now / 1000 - 1, now)).toBe(1_000)
  })
})
