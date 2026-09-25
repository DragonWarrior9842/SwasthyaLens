import { describe, expect, it } from 'vitest'
import fixture from './fixtures/trend.json'
import { decodePoint, decodeTrend, decodeTrendCatalog } from './trends'

describe('deterministic trend response boundary', () => {
  it('accepts a real backend-generated synthetic contract with exact decimals', () => {
    const actual = decodeTrend(fixture)
    expect(actual.current.median).toBe('72.750')
    expect(actual.change?.absolute).toBe('2.500')
    expect(actual.points).toHaveLength(14)
    expect(actual.status).toBe('increasing')
  })
  it.each([{ rules_version: 'unknown' }, { status: 'healthy' }, { window: '90d' }, { timezone: 'Invented' }, { mode: 'ai' }, { minimum_days: 2 }, { tolerance: null }, { reason: 'current_coverage' }, { unknown_date_count: -1 }, { pattern: 'diagnosis' }, { status: 'insufficient_data' }])('rejects malformed or unsupported metadata %j', changes => {
    expect(() => decodeTrend({ ...fixture, ...changes })).toThrow()
  })
  it.each([{ sample_count: 8 }, { observed_days: 6 }, { start: '2026-04-01' }, { end: '2026-02-30' }, { median: 72.75 }, { median: 'NaN' }, { first_day: null }])('rejects inconsistent period %j', changes => {
    expect(() => decodeTrend({ ...fixture, current: { ...fixture.current, ...changes } })).toThrow()
  })
  it.each([{ value: '999' }, { unit: 'lb' }, { day: '2027-01-01' }, { revision: 0 }, { measured_at: null }, { source_type: 'ocr' }, { report_id: fixture.points[0]!.observation_id }, { value: 'NaN' }, { raw_value: '<70.250' }])('rejects invalid point or grounding %j', changes => {
    expect(() => decodeTrend({ ...fixture, points: [{ ...fixture.points[0], ...changes }, ...fixture.points.slice(1)] })).toThrow()
  })
  it('retains exact scalar spelling and rejects comparators', () => {
    expect(decodePoint({ ...fixture.points[0], raw_value: ' +070.250 ', value: '70.250' }).raw_value).toBe(' +070.250 ')
    expect(() => decodePoint({ ...fixture.points[0], raw_value: '=70.250' })).toThrow()
    expect(decodePoint({ ...fixture.points[0], raw_value: '−0.25', value: '-0.25' }).value).toBe('-0.25')
  })
  it('rejects duplicate identities and fabricated latest evidence', () => {
    expect(() => decodeTrend({ ...fixture, points: [...fixture.points, fixture.points[0]] })).toThrow()
    expect(() => decodeTrend({ ...fixture, latest_comparison: { ...fixture.latest_comparison, latest: { ...fixture.latest_comparison.latest, revision: 2 } } })).toThrow()
  })
  it('does not enable unsupported correlations', () => {
    const catalog = { rules_version: 'trends-v1', timezone: 'UTC', as_of: fixture.as_of, period_end: fixture.current.end, series: [], correlations: { status: 'unsupported_catalog', pairs: [], minimum_pairs: 14, method: 'pearson_same_day_medians', rules_version: 'correlations-v1' } }
    expect(decodeTrendCatalog(catalog).series).toEqual([])
    expect(() => decodeTrendCatalog({ ...catalog, correlations: { ...catalog.correlations, pairs: ['weight,heart_rate'] } })).toThrow()
    expect(() => decodeTrendCatalog({ ...catalog, correlations: { ...catalog.correlations, minimum_pairs: 3 } })).toThrow()
  })
})
