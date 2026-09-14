import { describe, expect, it } from 'vitest'
import { safeReturnTo } from './redirect'

describe('post-login destinations', () => {
  it.each(['/', '/reports', '/trends', '/assistant', '/settings'])('preserves allowed destination %s', (path) => {
    expect(safeReturnTo(path)).toBe(path)
  })
  it.each([null, undefined, {}, 'https://untrusted.example', '//untrusted.example', '/\\untrusted.example', '/reports?token=secret', '/auth/sign-in', '/%2f%2funtrusted.example', 'javascript:alert(1)'])('rejects arbitrary redirect %s', (path) => {
    expect(safeReturnTo(path)).toBe('/')
  })
})
