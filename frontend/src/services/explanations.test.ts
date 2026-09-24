import { describe, expect, it } from 'vitest'
import { decodeExplanation } from './explanations'

const id = '11111111-1111-4111-8111-111111111111'
const fields = { original_label: 'Hemoglobin', raw_value: '13.20', original_unit: 'g/dL', raw_reference: '12–15', canonical_metric: 'hemoglobin', numeric_value: '13.20', comparator: null, value_kind: 'numeric', source_flag: null, calculated_range_status: 'unknown' }
const fact = { evidence_id: 'e1', label: 'Hemoglobin', value: '13.20', unit: 'g/dL', reference: '12–15', source_flag: null, canonical_metric: 'hemoglobin', comparator: null, value_kind: 'numeric', page_number: 1, calculated_range_status: 'unknown' }
const item = { fact, source: { observation_id: id, candidate_id: id, source_run_id: id, parameter_run_id: id, revision: 1, review_revision: 1, page_number: 1, source_start: 0, source_end: 20, fields }, explanation: 'Educational definition.', notes: ['Comparison unknown.'], educational_source_url: 'https://medlineplus.gov/lab-tests/hemoglobin-test/' }
const record = { id, report_id: id, status: 'ready', provider: 'mock-test', model: 'gpt-5.6-terra', prompt_version: 'report-education-v1', schema_version: 'closed-education-v1', catalog_version: 'education-en-v1', created_at: '2026-09-18T00:00:00Z', expires_at: '2026-10-18T00:00:00Z', finished_at: '2026-09-18T00:00:01Z', error_category: null, items: [item] }
const state = { report_id: id, eligible_count: 1, evaluation_enrolled: true, provider_available: true, provider: 'mock-test', record }
describe('grounded explanation boundary', () => {
  it('accepts only approved provider/model pairs and a known active provider', () => {
    expect(decodeExplanation({ ...state, provider: 'gemini', record: { ...record, provider: 'gemini', model: 'gemini-3.8-flash' } }).record?.provider).toBe('gemini')
    for (const change of [{ provider: 'gemini', model: 'gpt-5.6-terra' }, { provider: 'openai', model: 'gemini-3.8-flash' }, { provider: 'unknown' }]) {
      expect(() => decodeExplanation({ ...state, record: { ...record, ...change } })).toThrow()
    }
    expect(() => decodeExplanation({ ...state, provider: 'unknown' })).toThrow()
  })
  it('preserves exact strings and provenance', () => {
    const result = decodeExplanation(state)
    expect(result.record?.items[0]?.fact.value).toBe('13.20')
    expect(result.record?.items[0]?.source.review_revision).toBe(1)
  })
  it.each([{ value: '132' }, { value: '13.2' }, { unit: 'mg/L' }, { reference: null }, { evidence_id: 'e2' }, { page_number: 2 }, { calculated_range_status: 'normal' }])('rejects mismatched echoed fact %j', change => {
    expect(() => decodeExplanation({ ...state, record: { ...record, items: [{ ...item, fact: { ...fact, ...change } }] } })).toThrow()
  })
  it.each(['stale', 'failed', 'generating'])('rejects content in %s state', status => {
    expect(() => decodeExplanation({ ...state, record: { ...record, status } })).toThrow()
    expect(decodeExplanation({ ...state, record: { ...record, status, items: [] } }).record?.items).toEqual([])
  })
  it.each(['javascript:alert(1)', 'https://attacker.invalid/', 'https://medlineplus.gov.attacker.invalid/'])('rejects unsafe education link %s', educational_source_url => {
    expect(() => decodeExplanation({ ...state, record: { ...record, items: [{ ...item, educational_source_url }] } })).toThrow()
  })
  it('rejects duplicate evidence and unknown versions', () => {
    expect(() => decodeExplanation({ ...state, eligible_count: 2, record: { ...record, items: [item, item] } })).toThrow()
    expect(() => decodeExplanation({ ...state, record: { ...record, prompt_version: 'unknown' } })).toThrow()
  })
  it('accepts empty, unpublished state', () => {
    expect(decodeExplanation({ ...state, eligible_count: 0, evaluation_enrolled: false, record: null }).record).toBeNull()
  })
})
