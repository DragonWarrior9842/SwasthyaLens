import { accountMutation, accountOwnedRead } from './auth'
import { reportChanged } from './report-events'
import { decodeFields } from './parameters'
import type { Fields } from './parameters'

export interface Revision { revision: number; status: 'active' | 'superseded' | 'invalidated'; fields: Fields; catalog_version: 'observations-v1'; measurement_date: string | null; measured_at: string | null; candidate_id: string | null; review_revision: number | null; created_at: string; status_changed_at: string }
export interface Evidence { report_name: string; report_created_at: string; source_run_id: string; parameter_run_id: string; content: { page_number: number; source_text: string; source_start: number; source_end: number; source_method: string; fields: Fields } }
export interface Observation { id: string; source_type: 'report' | 'manual'; report_id: string | null; candidate_id: string | null; created_at: string; current: Revision; revisions: Revision[]; evidence: Evidence | null }
export interface ObservationPage { items: Observation[]; next_offset: number | null }
export interface Dashboard { uploaded_reports: number; reviewed_parameters: number; active_observations: number; observations: Observation[]; reports: { id: string; original_filename: string; created_at: string }[] }
export interface ManualInput { metric: 'weight' | 'heart_rate'; raw_value: string; unit: 'kg' | 'bpm'; measured_at: string; idempotency_key: string; expected_revision?: number }
export const metrics = [['hemoglobin', 'Hemoglobin'], ['tsh', 'TSH'], ['vitamin_d_unspecified', 'Vitamin D (unspecified)'], ['glucose_unspecified', 'Glucose (unspecified)'], ['crp', 'CRP'], ['weight', 'Weight'], ['heart_rate', 'Heart rate']] as const
function object(v: unknown): v is Record<string, unknown> { return !!v && typeof v === 'object' && !Array.isArray(v) }
function id(v: unknown): v is string { return typeof v === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v) }
function integer(v: unknown, min: number, max: number): v is number { return typeof v === 'number' && Number.isSafeInteger(v) && v >= min && v <= max }
function instant(v: unknown): v is string { return typeof v === 'string' && /T.*(?:Z|[+-]\d{2}:\d{2})$/.test(v) && Number.isFinite(Date.parse(v)) }
function day(v: unknown): v is string { return typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v) && Number.isFinite(Date.parse(v)) && new Date(v).toISOString().slice(0, 10) === v }
function revision(v: unknown): Revision {
  if (!object(v) || !integer(v.revision, 1, 100) || !['active', 'superseded', 'invalidated'].includes(String(v.status)) || v.catalog_version !== 'observations-v1' || !(v.measurement_date === null || day(v.measurement_date)) || !(v.measured_at === null || instant(v.measured_at)) || !(v.candidate_id === null || id(v.candidate_id)) || !(v.review_revision === null || integer(v.review_revision, 1, 20)) || !instant(v.created_at) || !instant(v.status_changed_at)) throw new Error('Invalid observation revision')
  return { ...v, fields: decodeFields(v.fields) } as unknown as Revision
}
export function decodeObservation(v: unknown): Observation {
  if (!object(v) || !id(v.id) || !['report', 'manual'].includes(String(v.source_type)) || !(v.report_id === null || id(v.report_id)) || !(v.candidate_id === null || id(v.candidate_id)) || !instant(v.created_at) || !Array.isArray(v.revisions) || v.revisions.length > 100) throw new Error('Invalid observation')
  const current = revision(v.current), revisions = v.revisions.map(revision)
  if (new Set(revisions.map(r => r.revision)).size !== revisions.length || (revisions[0] && JSON.stringify(revisions[0]) !== JSON.stringify(current))) throw new Error('Invalid observation history')
  for (const r of [current, ...revisions]) {
    if (v.source_type === 'report' ? (!id(v.report_id) || !id(v.candidate_id) || r.candidate_id !== v.candidate_id || r.review_revision === null || r.measured_at !== null) : (v.report_id !== null || v.candidate_id !== null || r.candidate_id !== null || r.review_revision !== null || r.measured_at === null || r.measurement_date !== null)) throw new Error('Invalid source relationship')
  }
  let evidence: Evidence | null = null
  if (v.evidence !== null) {
    const e = v.evidence
    if (v.source_type !== 'report' || !object(e) || typeof e.report_name !== 'string' || !e.report_name || e.report_name.length > 200 || !instant(e.report_created_at) || !id(e.source_run_id) || !id(e.parameter_run_id) || !object(e.content)) throw new Error('Invalid evidence')
    const c = e.content
    if (!integer(c.page_number, 1, 20) || typeof c.source_text !== 'string' || !c.source_text || c.source_text.length > 2048 || !integer(c.source_start, 0, 20000) || !integer(c.source_end, 1, 20000) || c.source_end - c.source_start !== Array.from(c.source_text).length || !['native_text', 'ocr'].includes(String(c.source_method))) throw new Error('Invalid source span')
    evidence = { ...e, content: { ...c, fields: decodeFields(c.fields) } } as unknown as Evidence
  }
  return { id: v.id, source_type: v.source_type as Observation['source_type'], report_id: v.report_id, candidate_id: v.candidate_id, created_at: v.created_at, current, revisions, evidence }
}
export function decodeObservationPage(v: unknown): ObservationPage {
  if (!object(v) || !Array.isArray(v.items) || v.items.length > 20 || !(v.next_offset === null || integer(v.next_offset, 20, 10000))) throw new Error('Invalid history page')
  const items = v.items.map(decodeObservation)
  if (new Set(items.map(r => r.id)).size !== items.length) throw new Error('Duplicate observation')
  return { items, next_offset: v.next_offset }
}
export function decodeDashboard(v: unknown): Dashboard {
  if (!object(v) || !integer(v.uploaded_reports, 0, Number.MAX_SAFE_INTEGER) || !integer(v.reviewed_parameters, 0, Number.MAX_SAFE_INTEGER) || !integer(v.active_observations, 0, Number.MAX_SAFE_INTEGER) || !Array.isArray(v.observations) || v.observations.length > 5 || !Array.isArray(v.reports) || v.reports.length > 3) throw new Error('Invalid overview')
  const observations = v.observations.map(decodeObservation)
  if (observations.some(r => r.current.status !== 'active') || observations.length > v.active_observations || v.reports.length > v.uploaded_reports) throw new Error('Inconsistent overview')
  const reports = v.reports.map((r: unknown) => { if (!object(r) || !id(r.id) || typeof r.original_filename !== 'string' || !instant(r.created_at)) throw new Error('Invalid recent report'); return { id: r.id, original_filename: r.original_filename, created_at: r.created_at } })
  return { uploaded_reports: v.uploaded_reports, reviewed_parameters: v.reviewed_parameters, active_observations: v.active_observations, observations, reports }
}
function path(identifier: string) { if (!id(identifier)) throw new Error('Invalid observation'); return `/observations/${identifier}` }
export const getDashboard = (owner: string, signal?: AbortSignal) => accountOwnedRead('/dashboard', decodeDashboard, owner, signal)
export const listObservations = (query: string, owner: string, signal?: AbortSignal) => accountOwnedRead(`/observations?${query}`, decodeObservationPage, owner, signal)
export async function getObservation(identifier: string, owner: string, signal?: AbortSignal) {
  const result = await accountOwnedRead(path(identifier), decodeObservation, owner, signal)
  if (result.id !== identifier || result.revisions.length === 0 || (result.source_type === 'report' && !result.evidence)) throw new Error('Mismatched observation')
  return result
}
export async function publishObservation(report: string, candidate: string, expected_revision: number, measurement_date: string | null, owner: string, signal?: AbortSignal) {
  if (!id(report) || !id(candidate)) throw new Error('Invalid source')
  const result = await accountMutation(`/reports/${report}/parameters/${candidate}/publish`, { expected_revision, measurement_date }, decodeObservation, owner, 'POST', signal)
  if (result.report_id !== report || result.candidate_id !== candidate || result.current.review_revision !== expected_revision) throw new Error('Mismatched publication')
  reportChanged(report)
  return result
}
export async function saveManual(body: ManualInput, owner: string, identifier?: string, signal?: AbortSignal) {
  const result = await accountMutation(identifier ? path(identifier) : '/observations/manual', body, decodeObservation, owner, identifier ? 'PATCH' : 'POST', signal)
  if (result.source_type !== 'manual' || (identifier && result.id !== identifier)) throw new Error('Mismatched manual record')
  return result
}
export const deleteObservation = (identifier: string, expected_revision: number, owner: string, signal?: AbortSignal) => accountMutation(path(identifier), { expected_revision }, v => { if (!object(v) || v.message !== 'Observation deleted.') throw new Error('Invalid deletion'); }, owner, 'DELETE', signal)
export function measurementLabel(r: Revision) { return r.measured_at ? `${new Date(r.measured_at).toISOString().replace('T', ' ').replace('.000Z', ' UTC')}` : r.measurement_date ? `${r.measurement_date} · day only, supplied by you` : 'Measurement date unknown' }
