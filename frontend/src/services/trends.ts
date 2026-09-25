import { accountOwnedRead } from './auth'
import { metrics } from './observations'

export type Metric = typeof metrics[number][0]
export interface Series { metric: Metric; unit: string | null; observation_count: number; supported_unit: boolean }
export interface Correlations { status: 'unsupported_catalog'; pairs: []; minimum_pairs: 14; method: 'pearson_same_day_medians'; rules_version: 'correlations-v1' }
export interface TrendCatalog { rules_version: 'trends-v1'; timezone: string; as_of: string; period_end: string; series: Series[]; correlations: Correlations }
export interface Point { observation_id: string; revision: number; source_type: 'report' | 'manual'; report_id: string | null; candidate_id: string | null; review_revision: number | null; day: string; measured_at: string | null; raw_value: string; value: string; unit: string }
export interface Period { start: string; end: string; sample_count: number; excluded_count: number; observed_days: number; coverage_percent: string | null; first_day: string | null; last_day: string | null; median: string | null; observed_range: string | null }
export interface Change { absolute: string; percent: string | null }
export interface Latest { latest: Point | null; previous: Point | null; change: Change | null; reason: 'no_dated_numeric_data' | 'fewer_than_two_days' | 'ambiguous_same_day' | 'available' }
export interface TrendResult {
  rules_version: 'trends-v1'; metric: Metric; unit: string; window: '7d' | '30d'; timezone: string; as_of: string; partial_end_day: boolean; history_start: string; mode: 'frequent' | 'occasional'; minimum_days: number | null;
  current: Period; previous: Period; points: Point[]; unknown_date_count: number; excluded_history_count: number; latest_comparison: Latest;
  status: 'increasing' | 'decreasing' | 'stable' | 'insufficient_data'; reason: 'available' | 'no_numeric_observations' | 'current_coverage' | 'previous_coverage' | 'occasional_metric'; change: Change | null; tolerance: string | null;
  pattern: 'consistent_increase' | 'consistent_decrease' | 'stable_sequence' | 'no_clear_pattern' | 'insufficient_data' | 'not_applicable';
}
function fail(): never { throw new Error('Invalid deterministic trend response') }
function obj(v: unknown): Record<string, unknown> { if (!v || typeof v !== 'object' || Array.isArray(v)) return fail(); return v as Record<string, unknown> }
function integer(v: unknown, max = Number.MAX_SAFE_INTEGER): v is number { return typeof v === 'number' && Number.isSafeInteger(v) && v >= 0 && v <= max }
function id(v: unknown): v is string { return typeof v === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v) }
function decimal(v: unknown): v is string { return typeof v === 'string' && /^-?[0-9]{1,45}(?:\.[0-9]{1,20})?$/.test(v) }
function day(v: unknown): v is string { return typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v) && Number.isFinite(Date.parse(v)) && new Date(v).toISOString().slice(0, 10) === v }
function instant(v: unknown): v is string { return typeof v === 'string' && /T.*(?:Z|[+-]\d{2}:\d{2})$/.test(v) && Number.isFinite(Date.parse(v)) }
function metric(v: unknown): v is Metric { return metrics.some(([key]) => key === v) }
function zone(v: unknown): v is string { if (typeof v !== 'string' || v.length > 64) return false; try { new Intl.DateTimeFormat('en', { timeZone: v }); return true } catch { return false } }
function unit(v: unknown): v is string { return typeof v === 'string' && v.length > 0 && v.length <= 60 }
function nullable<T>(v: unknown, check: (v: unknown) => v is T): v is T | null { return v === null || check(v) }
function decodeChange(v: unknown): Change | null { if (v === null) return null; const c = obj(v); if (!decimal(c.absolute) || !nullable(c.percent, decimal)) return fail(); return { absolute: c.absolute, percent: c.percent } }
function canonical(v: string) { const s = v.trim().replace('−', '-').replace(/^\+/, ''); if (!/^-?(?:\d{1,20}(?:\.\d{1,12})?|\.\d{1,12})$/.test(s)) return fail(); const n = s.replace(/^(-?)0+(?=\d)/, '$1').replace(/(\.\d*?)0+$/, '$1').replace(/\.$/, '').replace(/^(-?)\./, '$10.'); return /^-?0$/.test(n) ? '0' : n }
export function decodePoint(value: unknown): Point {
  const p = obj(value)
  if (!id(p.observation_id) || !integer(p.revision, 100) || p.revision < 1 || !day(p.day) || !nullable(p.measured_at, instant) || !decimal(p.value) || typeof p.raw_value !== 'string' || !unit(p.unit) || !nullable(p.report_id, id) || !nullable(p.candidate_id, id) || !(p.review_revision === null || (integer(p.review_revision, 20) && p.review_revision > 0))) return fail()
  if (p.source_type === 'manual' ? (p.report_id !== null || p.candidate_id !== null || p.review_revision !== null || p.measured_at === null) : (p.source_type !== 'report' || p.report_id === null || p.candidate_id === null || p.review_revision === null || p.measured_at !== null)) return fail()
  if (canonical(p.raw_value) !== canonical(p.value)) return fail()
  return p as unknown as Point
}
function decodePeriod(value: unknown, count: number): Period {
  const p = obj(value)
  if (!day(p.start) || !day(p.end) || (Date.parse(p.end) - Date.parse(p.start)) / 86400000 !== count - 1 || !integer(p.sample_count, 500) || !integer(p.excluded_count, 500) || !integer(p.observed_days, count) || p.observed_days > p.sample_count || !nullable(p.first_day, day) || !nullable(p.last_day, day) || !nullable(p.coverage_percent, decimal) || !nullable(p.median, decimal) || !nullable(p.observed_range, decimal)) return fail()
  if (p.sample_count === 0 ? (p.first_day !== null || p.last_day !== null || p.median !== null || p.observed_days !== 0) : (p.first_day === null || p.last_day === null || p.first_day < p.start || p.last_day > p.end || p.first_day > p.last_day)) return fail()
  return p as unknown as Period
}
export function decodeTrendCatalog(value: unknown): TrendCatalog {
  const c = obj(value), correlation = obj(c.correlations)
  if (c.rules_version !== 'trends-v1' || !zone(c.timezone) || !instant(c.as_of) || !day(c.period_end) || !Array.isArray(c.series) || c.series.length > 50 || correlation.status !== 'unsupported_catalog' || !Array.isArray(correlation.pairs) || correlation.pairs.length !== 0 || correlation.minimum_pairs !== 14 || correlation.method !== 'pearson_same_day_medians' || correlation.rules_version !== 'correlations-v1') return fail()
  const series = c.series.map(v => { const s = obj(v); if (!metric(s.metric) || !(s.unit === null || (typeof s.unit === 'string' && s.unit.length <= 60)) || !integer(s.observation_count) || s.observation_count < 1 || typeof s.supported_unit !== 'boolean' || (!s.unit && s.supported_unit)) return fail(); return s as unknown as Series })
  if (new Set(series.map(s => JSON.stringify([s.metric, s.unit]))).size !== series.length) return fail()
  return { ...c, series } as unknown as TrendCatalog
}
export function decodeTrend(value: unknown): TrendResult {
  const r = obj(value)
  if (r.rules_version !== 'trends-v1' || !metric(r.metric) || !unit(r.unit) || !['7d', '30d'].includes(String(r.window)) || !zone(r.timezone) || !instant(r.as_of) || typeof r.partial_end_day !== 'boolean' || !day(r.history_start) || !['frequent', 'occasional'].includes(String(r.mode)) || !Array.isArray(r.points) || r.points.length > 500 || !integer(r.unknown_date_count) || !integer(r.excluded_history_count, 500) || !['increasing', 'decreasing', 'stable', 'insufficient_data'].includes(String(r.status)) || !['available', 'no_numeric_observations', 'current_coverage', 'previous_coverage', 'occasional_metric'].includes(String(r.reason)) || !nullable(r.tolerance, decimal) || !['consistent_increase', 'consistent_decrease', 'stable_sequence', 'no_clear_pattern', 'insufficient_data', 'not_applicable'].includes(String(r.pattern))) return fail()
  const count = r.window === '7d' ? 7 : 30, current = decodePeriod(r.current, count), previous = decodePeriod(r.previous, count), points = r.points.map(decodePoint), change = decodeChange(r.change)
  if (Date.parse(current.start) - Date.parse(previous.end) !== 86400000 || r.history_start > previous.start || new Set(points.map(p => p.observation_id)).size !== points.length || points.some(p => p.unit !== r.unit || p.day < String(r.history_start) || p.day > current.end)) return fail()
  for (const period of [current, previous]) {
    const selected = points.filter(p => p.day >= period.start && p.day <= period.end)
    if (selected.length !== period.sample_count || new Set(selected.map(p => p.day)).size !== period.observed_days) return fail()
  }
  if (r.mode === 'occasional' ? (r.minimum_days !== null || current.median !== null || previous.median !== null || current.coverage_percent !== null || previous.coverage_percent !== null || r.status !== 'insufficient_data' || r.reason !== 'occasional_metric') : r.minimum_days !== Math.ceil(count / 2)) return fail()
  if (r.status === 'insufficient_data' ? (change !== null || r.tolerance !== null || r.reason === 'available') : (change === null || r.tolerance === null || r.reason !== 'available' || current.observed_days < Math.ceil(count / 2) || previous.observed_days < Math.ceil(count / 2))) return fail()
  const l = obj(r.latest_comparison), latest = l.latest === null ? null : decodePoint(l.latest), prior = l.previous === null ? null : decodePoint(l.previous), latestChange = decodeChange(l.change)
  if (!['no_dated_numeric_data', 'fewer_than_two_days', 'ambiguous_same_day', 'available'].includes(String(l.reason))) return fail()
  for (const p of [latest, prior]) if (p && !points.some(q => Object.keys(q).every(k => q[k as keyof Point] === p[k as keyof Point]))) return fail()
  if (l.reason === 'available' ? (!latest || !prior || !latestChange || latest.day <= prior.day) : (latestChange !== null || prior !== null)) return fail()
  return { ...r, current, previous, points, change, latest_comparison: { latest, previous: prior, change: latestChange, reason: l.reason } } as unknown as TrendResult
}
export const getTrendCatalog = (owner: string, signal?: AbortSignal) => accountOwnedRead('/trends/catalog', decodeTrendCatalog, owner, signal)
export async function getTrend(selectedMetric: Metric, selectedUnit: string, window: '7d' | '30d', end: string, owner: string, signal?: AbortSignal) {
  const query = new URLSearchParams({ unit: selectedUnit, window, ...(end ? { end } : {}) })
  const result = await accountOwnedRead(`/trends/${selectedMetric}?${query}`, decodeTrend, owner, signal)
  if (result.metric !== selectedMetric || result.unit !== selectedUnit || result.window !== window || (end && result.current.end !== end)) return fail()
  return result
}
