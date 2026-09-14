import { describe, expect, it } from 'vitest'
import { resolveApiBaseUrl } from './config'

describe('public API configuration', () => {
  it('uses the same-origin API proxy for empty configuration', () => {
    expect(resolveApiBaseUrl(undefined)).toBe('/api')
    expect(resolveApiBaseUrl('  ')).toBe('/api')
    expect(resolveApiBaseUrl('/api/')).toBe('/api')
  })

  it('preserves a configured API prefix and removes trailing slashes', () => {
    expect(resolveApiBaseUrl(' https://api.example.test/api/ ')).toBe('https://api.example.test/api')
  })

  it.each([
    '//untrusted.example',
    '/api/../other',
    'not a url',
    'javascript:alert(1)',
    'https://user:password@example.test',
    'https://api.example.test?token=value',
    'https://api.example.test/#fragment',
  ])('rejects invalid or credential-bearing configuration: %s', (url) => {
    expect(() => resolveApiBaseUrl(url)).toThrow()
  })
})
