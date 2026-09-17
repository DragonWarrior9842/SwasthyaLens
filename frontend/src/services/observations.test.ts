import { describe, expect, it } from 'vitest'
import { decodeDashboard, decodeObservation, decodeObservationPage, measurementLabel } from './observations'

const id = '11111111-1111-4111-8111-111111111111'
const fields = { original_label: 'Hemoglobin', raw_value: '13.20', original_unit: 'g/dL', raw_reference: '12–15', canonical_metric: 'hemoglobin', numeric_value: '13.20', comparator: null, value_kind: 'numeric', source_flag: null, calculated_range_status: 'unknown' }
const revision = { revision: 1, status: 'active', fields, catalog_version: 'observations-v1', measurement_date: null, measured_at: null, candidate_id: id, review_revision: 1, created_at: '2026-09-17T00:00:00Z', status_changed_at: '2026-09-17T00:00:00Z' }
const observation = { id, source_type: 'report', report_id: id, candidate_id: id, created_at: revision.created_at, current: revision, revisions: [], evidence: null }
describe('observation boundary', () => {
  it('keeps decimal spelling and does not turn publication time into medical time', () => {
    const row = decodeObservation(observation)
    expect(row.current.fields.raw_value).toBe('13.20')
    expect(row.current.fields.numeric_value).toBe('13.20')
    expect(measurementLabel(row.current)).toBe('Measurement date unknown')
  })
  it('retains calendar day without timezone shifting', () => {
    const row = decodeObservation({ ...observation, current: { ...revision, measurement_date: '2020-01-01' } })
    expect(measurementLabel(row.current)).toBe('2020-01-01 · day only, supplied by you')
  })
  it('renders explicit manual instants in UTC across a day boundary', () => {
    const row = decodeObservation({ ...observation, source_type: 'manual', report_id: null, candidate_id: null, current: { ...revision, candidate_id: null, review_revision: null, measured_at: '2020-01-02T00:15:00+05:30' } })
    expect(measurementLabel(row.current)).toBe('2020-01-01 18:45:00 UTC')
  })
  it.each(['mg/dL', 'mmol/L', 'unknown', null])('does not convert unit %s', original_unit => {
    expect(decodeObservation({ ...observation, current: { ...revision, fields: { ...fields, original_unit } } }).current.fields.original_unit).toBe(original_unit)
  })
  it.each(['Negative', 'Positive', 'Trace', '1:80'])('preserves nonnumeric %s', raw_value => {
    const row = decodeObservation({ ...observation, current: { ...revision, fields: { ...fields, raw_value, numeric_value: null, value_kind: raw_value === '1:80' ? 'titre' : 'qualitative' } } })
    expect(row.current.fields.raw_value).toBe(raw_value)
    expect(row.current.fields.numeric_value).toBeNull()
  })
  it.each(['<', '>'])('preserves comparator %s', comparator => {
    const row = decodeObservation({ ...observation, current: { ...revision, fields: { ...fields, raw_value: `${comparator}5`, numeric_value: '5', comparator } } })
    expect(row.current.fields.comparator).toBe(comparator)
  })
  it.each([
    { report_id: null }, { candidate_id: null }, { source_type: 'ai' },
    { current: { ...revision, measured_at: revision.created_at } },
    { current: { ...revision, measurement_date: '2021-02-29' } },
    { current: { ...revision, measurement_date: revision.created_at } },
    { current: { ...revision, review_revision: null } },
    { current: { ...revision, status: 'clinically_validated' } },
    { current: { ...revision, fields: { ...fields, numeric_value: 13.2 } } },
    { revisions: [revision, revision] },
    { revisions: [{ ...revision, status: 'invalidated' }] },
  ])('rejects malformed observation %#', override => expect(() => decodeObservation({ ...observation, ...override })).toThrow())
  it('rejects duplicate page entries', () => expect(() => decodeObservationPage({ items: [observation, observation], next_offset: null })).toThrow())
  it('accepts an honest zero-data dashboard', () => expect(decodeDashboard({ uploaded_reports: 0, reviewed_parameters: 0, active_observations: 0, observations: [], reports: [] }).active_observations).toBe(0))
  it('rejects inactive observations on dashboard', () => expect(() => decodeDashboard({ uploaded_reports: 1, reviewed_parameters: 1, active_observations: 1, observations: [{ ...observation, current: { ...revision, status: 'invalidated' } }], reports: [] })).toThrow())
  it('rejects impossible dashboard counts', () => expect(() => decodeDashboard({ uploaded_reports: 1, reviewed_parameters: 1, active_observations: 0, observations: [observation], reports: [] })).toThrow())
})
