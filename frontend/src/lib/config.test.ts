import { describe, expect, it } from 'vitest'
import { resolveApiBaseUrl } from './config'

describe('public API configuration', () => {
  it('uses a loopback-only default for empty configuration', () => {
    expect(resolveApiBaseUrl(undefined)).toBe('http://127.0.0.1:8000')
    expect(resolveApiBaseUrl('  ')).toBe('http://127.0.0.1:8000')
  })

  it('preserves a configured API prefix and removes trailing slashes', () => {
    expect(resolveApiBaseUrl(' https://api.example.test/api/ ')).toBe('https://api.example.test/api')
  })

  it.each([
    '/api',
    'not a url',
    'javascript:alert(1)',
    'https://user:password@example.test',
    'https://api.example.test?token=value',
    'https://api.example.test/#fragment',
  ])('rejects invalid or credential-bearing configuration: %s', (url) => {
    expect(() => resolveApiBaseUrl(url)).toThrow()
  })
})
