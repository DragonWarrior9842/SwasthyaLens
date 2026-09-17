import { describe, expect, it } from 'vitest'
import { decodeFields, decodeParameterResult, decodeParameterRun, decodeReviews } from './parameters'

const id = '11111111-1111-4111-8111-111111111111'
const fields = { original_label: 'Hemoglobin', raw_value: '13.20', original_unit: 'g/dL', raw_reference: '12–15', canonical_metric: 'hemoglobin', numeric_value: '13.20', comparator: null, value_kind: 'numeric', source_flag: null, calculated_range_status: 'unknown' }
const run = { id, report_id: id, source_run_id: id, attempt: 1, status: 'completed', extractor_version: 'v1', rules_version: 'v1', created_at: '2026-09-16T12:00:00Z', finished_at: '2026-09-16T12:00:01Z', deadline_at: '2026-09-16T12:01:00Z', error_category: null, candidate_count: 1, warnings: [] }
const content = { fields, page_number: 1, source_text: 'Hemoglobin 13.20 g/dL', source_start: 0, source_end: 21, source_method: 'native_text', certainty: 'needs_review', warnings: [], ocr_confidence: null }
const candidate = { id, run_id: id, ordinal: 1, content, reviews: [] }
describe('parameter evidence boundary', () => {
  it('preserves exact decimal strings, label, unit and reference', () => expect(decodeFields(fields)).toEqual(fields))
  it.each([13.2, NaN, Infinity, '1e3'])('rejects unsafe numeric representation %s', numeric_value => expect(() => decodeFields({ ...fields, numeric_value })).toThrow())
  it('does not accept calculated clinical status', () => expect(() => decodeFields({ ...fields, calculated_range_status: 'above' })).toThrow())
  it('accepts source-grounded candidate', () => expect(decodeParameterResult({ run, candidates: [candidate] }).candidates[0]?.content.source_text).toBe(content.source_text))
  it('rejects a different run', () => expect(() => decodeParameterResult({ run, candidates: [{ ...candidate, run_id: '22222222-2222-4222-8222-222222222222' }] })).toThrow())
  it('rejects missing candidates', () => expect(() => decodeParameterResult({ run, candidates: [] })).toThrow())
  it('rejects duplicate candidates', () => expect(() => decodeParameterResult({ run: { ...run, candidate_count: 2 }, candidates: [candidate, candidate] })).toThrow())
  it('rejects bad source offsets', () => expect(() => decodeParameterResult({ run, candidates: [{ ...candidate, content: { ...content, source_end: 2 } }] })).toThrow())
  it('rejects invented native OCR confidence', () => expect(() => decodeParameterResult({ run, candidates: [{ ...candidate, content: { ...content, ocr_confidence: 99 } }] })).toThrow())
  it('preserves untrusted markup as data', () => expect(decodeFields({ ...fields, original_label: '<script>हिंदी</script>' }).original_label).toBe('<script>हिंदी</script>'))
  it('rejects clinical validation states', () => expect(() => decodeReviews([{ revision: 1, action: 'validated', fields, actor_id: id, created_at: run.created_at }])).toThrow())
  it('rejects false completed state', () => expect(() => decodeParameterRun({ ...run, finished_at: null })).toThrow())
  it('retains latest user revision first', () => expect(decodeReviews([1, 2].map(revision => ({ revision, action: 'corrected', fields, actor_id: id, created_at: run.created_at })))[0]?.revision).toBe(2))
})
