import { describe, expect, it } from 'vitest'
import { decodeExtraction, decodeHistory, decodeRun } from './extraction'

const run = { id: '22222222-2222-4222-8222-222222222222', report_id: '11111111-1111-4111-8111-111111111111', status: 'completed', attempt: 1, created_at: '2026-09-16T12:00:00Z', started_at: '2026-09-16T12:00:01Z', finished_at: '2026-09-16T12:00:03Z', deadline_at: '2026-09-16T12:03:00Z', error_category: null, processor: 'synthetic-test', page_count: 1 }
const page = { page_number: 1, text: '<script>untrusted text</script> हिंदी 13.2 mg/dL', method: 'native_text', confidence: null, warnings: ['layout_requires_review'] }
describe('extraction contracts', () => {
  it('preserves source text verbatim', () => expect(decodeExtraction({ run, pages: [page] }).pages[0]?.text).toBe(page.text))
  it.each([NaN, -1, 101, '95'])('rejects invalid OCR scores: %s', confidence => expect(() => decodeExtraction({ run, pages: [{ ...page, method: 'ocr', confidence }] })).toThrow())
  it('does not invent native confidence', () => expect(() => decodeExtraction({ run, pages: [{ ...page, confidence: 99 }] })).toThrow())
  it('rejects missing pages', () => expect(() => decodeExtraction({ run, pages: [] })).toThrow())
  it('rejects incorrect page order', () => expect(() => decodeExtraction({ run, pages: [{ ...page, page_number: 2 }] })).toThrow())
  it('rejects duplicate attempts', () => expect(() => decodeHistory({ runs: [run, run] })).toThrow())
  it('rejects false completion', () => expect(() => decodeRun({ ...run, page_count: null })).toThrow())
  it('rejects failure without a category', () => expect(() => decodeRun({ ...run, status: 'failed' })).toThrow())
  it('rejects undocumented failure categories', () => expect(() => decodeRun({ ...run, status: 'failed', error_category: 'provider_secret' })).toThrow())
  it('rejects oversized page text', () => expect(() => decodeExtraction({ run, pages: [{ ...page, text: 'a'.repeat(20001) }] })).toThrow())
  it('accepts durable queued state', () => expect(decodeRun({ ...run, status: 'queued', started_at: null, finished_at: null, processor: null, page_count: null }).status).toBe('queued'))
})
