import { accountMutation, accountOwnedRead } from './auth'
import { reportChanged } from './report-events'

export interface RawFields { original_label: string; raw_value: string | null; original_unit: string | null; raw_reference: string | null }
export interface Fields extends RawFields { canonical_metric: string | null; numeric_value: string | null; comparator: string | null; value_kind: string; source_flag: string | null; calculated_range_status: 'unknown' }
export interface ParameterRun { id: string; report_id: string; source_run_id: string; attempt: number; status: 'processing' | 'completed' | 'failed'; extractor_version: string; rules_version: string; created_at: string; finished_at: string | null; deadline_at: string; error_category: string | null; candidate_count: number | null; warnings: string[] }
export interface Review { revision: number; action: 'confirmed' | 'corrected' | 'rejected'; fields: Fields; actor_id: string; created_at: string }
export interface Candidate { id: string; run_id: string; ordinal: number; content: { fields: Fields; page_number: number; source_text: string; source_start: number; source_end: number; source_method: string; certainty: 'needs_review'; warnings: string[]; ocr_confidence: number | null }; reviews: Review[] }
export interface ParameterResult { run: ParameterRun; candidates: Candidate[] }
export interface ReviewInput { idempotency_key: string; expected_revision: number; action: Review['action']; correction?: RawFields }
function object(v: unknown): v is Record<string, unknown> { return !!v && typeof v === 'object' && !Array.isArray(v) }
function string(v: unknown, max = 200): v is string { return typeof v === 'string' && v.length <= max }
function nullable(v: unknown, max = 200): v is string | null { return v === null || string(v, max) }
function integer(v: unknown, min: number, max: number): v is number { return typeof v === 'number' && Number.isInteger(v) && v >= min && v <= max }
function id(v: unknown): v is string { return typeof v === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v) }
function date(v: unknown): v is string { return typeof v === 'string' && Number.isFinite(Date.parse(v)) }
function strings(v: unknown, max: number): v is string[] { return Array.isArray(v) && v.length <= max && v.every(x => string(x, 100)) }
export function decodeFields(v: unknown): Fields {
  if (!object(v) || !string(v.original_label, 160) || !v.original_label.trim() || !nullable(v.raw_value, 100) || !nullable(v.original_unit, 60) || !nullable(v.raw_reference, 160) || !nullable(v.canonical_metric) || !nullable(v.numeric_value, 50) || (v.numeric_value !== null && !/^[+-]?\d+(?:\.\d+)?$/.test(v.numeric_value)) || !(v.comparator === null || ['<', '>', '<=', '>=', '=', '≤', '≥'].includes(String(v.comparator))) || !['numeric', 'qualitative', 'titre', 'interval', 'ordinal', 'unparsed', 'missing'].includes(String(v.value_kind)) || !(v.source_flag === null || ['H', 'L', 'High', 'Low', 'Abnormal'].includes(String(v.source_flag))) || v.calculated_range_status !== 'unknown') throw new Error('Invalid candidate fields')
  return { original_label: v.original_label, raw_value: v.raw_value, original_unit: v.original_unit, raw_reference: v.raw_reference, canonical_metric: v.canonical_metric, numeric_value: v.numeric_value, comparator: v.comparator as string | null, value_kind: String(v.value_kind), source_flag: v.source_flag as string | null, calculated_range_status: 'unknown' }
}
export function decodeParameterRun(v: unknown): ParameterRun {
  if (!object(v) || !id(v.id) || !id(v.report_id) || !id(v.source_run_id) || !integer(v.attempt, 1, 3) || !['processing', 'completed', 'failed'].includes(String(v.status)) || !string(v.extractor_version, 100) || !string(v.rules_version, 100) || !date(v.created_at) || !date(v.deadline_at) || !(v.finished_at === null || date(v.finished_at)) || !(v.error_category === null || ['interrupted', 'parser_failure', 'resource_limit'].includes(String(v.error_category))) || !(v.candidate_count === null || integer(v.candidate_count, 0, 200)) || !strings(v.warnings, 10)) throw new Error('Invalid parameter attempt')
  if ((v.status === 'failed') !== (v.error_category !== null) || (v.status === 'processing') !== (v.finished_at === null) || (v.status === 'completed' && v.candidate_count === null)) throw new Error('Inconsistent parameter attempt')
  return v as unknown as ParameterRun
}
export function decodeReviews(v: unknown): Review[] {
  if (!Array.isArray(v) || v.length > 20) throw new Error('Invalid reviews')
  const reviews = v.map((r: unknown): Review => {
    if (!object(r) || !integer(r.revision, 1, 20) || !['confirmed', 'corrected', 'rejected'].includes(String(r.action)) || !id(r.actor_id) || !date(r.created_at)) throw new Error('Invalid review')
    return { revision: r.revision, action: r.action as Review['action'], fields: decodeFields(r.fields), actor_id: r.actor_id, created_at: r.created_at }
  })
  if (new Set(reviews.map(r => r.revision)).size !== reviews.length) throw new Error('Duplicate reviews')
  return reviews.sort((a, b) => b.revision - a.revision)
}
export function decodeParameterResult(v: unknown): ParameterResult {
  if (!object(v) || !Array.isArray(v.candidates) || v.candidates.length > 200) throw new Error('Invalid parameters')
  const run = decodeParameterRun(v.run)
  const candidates = v.candidates.map((c: unknown): Candidate => {
    if (!object(c) || !id(c.id) || c.run_id !== run.id || !integer(c.ordinal, 1, 200) || !object(c.content)) throw new Error('Invalid candidate')
    const p = c.content
    if (!integer(p.page_number, 1, 20) || !string(p.source_text, 1024) || !integer(p.source_start, 0, 20000) || !integer(p.source_end, 1, 20000) || p.source_end - p.source_start !== Array.from(p.source_text).length || !['native_text', 'ocr'].includes(String(p.source_method)) || p.certainty !== 'needs_review' || !strings(p.warnings, 12) || !(p.ocr_confidence === null || (typeof p.ocr_confidence === 'number' && Number.isFinite(p.ocr_confidence) && p.ocr_confidence >= 0 && p.ocr_confidence <= 100)) || (p.source_method === 'native_text' && p.ocr_confidence !== null)) throw new Error('Invalid provenance')
    return { id: c.id, run_id: run.id, ordinal: c.ordinal, content: { fields: decodeFields(p.fields), page_number: p.page_number, source_text: p.source_text, source_start: p.source_start, source_end: p.source_end, source_method: String(p.source_method), certainty: 'needs_review', warnings: p.warnings, ocr_confidence: p.ocr_confidence }, reviews: decodeReviews(c.reviews) }
  })
  if (run.status !== 'completed' || run.candidate_count !== candidates.length || new Set(candidates.map(c => c.id)).size !== candidates.length || candidates.some((c, index) => c.ordinal !== index + 1)) throw new Error('Incomplete candidates')
  return { run, candidates }
}
function path(report: string) { if (!id(report)) throw new Error('Invalid report'); return `/reports/${report}` }
export async function parameterHistory(report: string, owner: string, signal?: AbortSignal) {
  return accountOwnedRead(`${path(report)}/parameter-processing`, v => {
    if (!object(v) || !Array.isArray(v.runs) || v.runs.length > 9) throw new Error('Invalid history')
    const runs = v.runs.map(decodeParameterRun)
    if (runs.some(r => r.report_id !== report) || new Set(runs.map(r => r.id)).size !== runs.length) throw new Error('Mismatched history')
    return runs
  }, owner, signal)
}
export async function extractParameters(report: string, source: string, key: string, owner: string, signal?: AbortSignal) {
  if (!id(source) || !id(key)) throw new Error('Invalid attempt')
  const run = await accountMutation(`${path(report)}/extract-parameters`, { source_run_id: source, idempotency_key: key }, decodeParameterRun, owner, 'POST', signal)
  if (run.report_id !== report || run.source_run_id !== source) throw new Error('Mismatched attempt')
  return run
}
export async function getParameters(report: string, run: string, owner: string, signal?: AbortSignal) {
  if (!id(run)) throw new Error('Invalid attempt')
  const result = await accountOwnedRead(`${path(report)}/parameters?run_id=${run}`, decodeParameterResult, owner, signal)
  if (result.run.report_id !== report || result.run.id !== run) throw new Error('Mismatched result')
  return result
}
export async function reviewParameter(report: string, candidate: string, body: ReviewInput, owner: string, signal?: AbortSignal) {
  if (!id(candidate)) throw new Error('Invalid candidate')
  reportChanged(report)
  try { return await accountMutation(`${path(report)}/parameters/${candidate}`, body, v => decodeReviews([v])[0]!, owner, 'PATCH', signal) }
  finally { reportChanged(report) }
}
export async function parameterReviews(report: string, candidate: string, owner: string, signal?: AbortSignal) {
  if (!id(candidate)) throw new Error('Invalid candidate')
  return accountOwnedRead(`${path(report)}/parameters/${candidate}/revisions`, decodeReviews, owner, signal)
}
