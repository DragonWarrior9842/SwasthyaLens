import { accountMutation, accountOwnedRead } from './auth'
import { decodeFields } from './parameters'
import type { Fields } from './parameters'

interface Fact { evidence_id: string; label: string; value: string; unit: string | null; reference: string | null; source_flag: string | null; value_kind: string; comparator: string | null; canonical_metric: string | null; page_number: number; calculated_range_status: 'unknown' }
interface Source { observation_id: string; revision: number; candidate_id: string; review_revision: number; source_run_id: string; parameter_run_id: string; page_number: number; source_start: number; source_end: number; fields: Fields }
export interface ExplainedItem { fact: Fact; source: Source; explanation: string; notes: string[]; educational_source_url: string | null }
export interface ExplanationRecord { id: string; report_id: string; status: 'generating' | 'ready' | 'failed' | 'stale'; provider: 'openai' | 'mock-test' | 'gemini'; model: string; prompt_version: string; schema_version: string; catalog_version: string; created_at: string; expires_at: string; finished_at: string | null; error_category: string | null; items: ExplainedItem[] }
export interface ExplanationView { report_id: string; eligible_count: number; evaluation_enrolled: boolean; provider_available: boolean; provider: ExplanationRecord['provider']; record: ExplanationRecord | null }
function object(v: unknown): v is Record<string, unknown> { return !!v && typeof v === 'object' && !Array.isArray(v) }
function id(v: unknown): v is string { return typeof v === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v) }
function integer(v: unknown, min: number, max: number): v is number { return typeof v === 'number' && Number.isSafeInteger(v) && v >= min && v <= max }
function text(v: unknown, max: number): v is string { return typeof v === 'string' && v.length > 0 && v.length <= max }
function date(v: unknown): v is string { return typeof v === 'string' && /T.*(?:Z|[+-]\d{2}:\d{2})$/.test(v) && Number.isFinite(Date.parse(v)) }
const links = new Set(['hemoglobin-test', 'tsh-thyroid-stimulating-hormone-test', 'vitamin-d-test', 'blood-glucose-test', 'c-reactive-protein-crp-test'].map(x => `https://medlineplus.gov/lab-tests/${x}/`))
export function decodeExplanation(v: unknown): ExplanationView {
  if (!object(v) || !id(v.report_id) || !integer(v.eligible_count, 0, 21) || typeof v.evaluation_enrolled !== 'boolean' || typeof v.provider_available !== 'boolean' || !['openai', 'gemini', 'mock-test'].includes(String(v.provider))) throw new Error('Invalid explanation state')
  let record: ExplanationRecord | null = null
  if (v.record !== null) {
    const r = v.record
    if (!object(r) || !id(r.id) || r.report_id !== v.report_id || !['generating', 'ready', 'failed', 'stale'].includes(String(r.status)) || !['openai', 'gemini', 'mock-test'].includes(String(r.provider)) || r.model !== (r.provider === 'gemini' ? 'gemini-3.8-flash' : 'gpt-5.6-terra') || r.prompt_version !== 'report-education-v1' || r.schema_version !== 'closed-education-v1' || r.catalog_version !== 'education-en-v1' || !date(r.created_at) || !date(r.expires_at) || !(r.finished_at === null || date(r.finished_at)) || !(r.error_category === null || ['timeout', 'interrupted', 'invalid', 'authentication', 'rate_limit', 'network', 'provider_failure', 'source_changed'].includes(String(r.error_category))) || !Array.isArray(r.items) || r.items.length > 20) throw new Error('Invalid explanation record')
    if (r.status === 'ready' ? (r.items.length < 1 || r.items.length !== v.eligible_count || r.error_category !== null) : r.items.length !== 0) throw new Error('Unsafe explanation state')
    const observations = new Set<string>()
    const items = r.items.map((item: unknown, index: number): ExplainedItem => {
      if (!object(item) || !object(item.fact) || !object(item.source) || !text(item.explanation, 400) || !Array.isArray(item.notes) || item.notes.length < 1 || item.notes.length > 8 || !item.notes.every(n => text(n, 300)) || !(item.educational_source_url === null || links.has(String(item.educational_source_url)))) throw new Error('Invalid explanation item')
      const f = item.fact, s = item.source, fields = decodeFields(s.fields)
      if (!id(s.observation_id) || observations.has(s.observation_id) || !id(s.candidate_id) || !id(s.source_run_id) || !id(s.parameter_run_id) || !integer(s.revision, 1, 100) || !integer(s.review_revision, 1, 20) || !integer(s.page_number, 1, 20) || !integer(s.source_start, 0, 20000) || !integer(s.source_end, 1, 20000) || s.source_end <= s.source_start) throw new Error('Invalid explanation provenance')
      if (f.evidence_id !== `e${index + 1}` || !text(f.value, 100) || f.label !== fields.original_label || f.value !== fields.raw_value || f.unit !== fields.original_unit || f.reference !== fields.raw_reference || f.source_flag !== fields.source_flag || f.canonical_metric !== fields.canonical_metric || f.comparator !== fields.comparator || f.value_kind !== fields.value_kind || f.page_number !== s.page_number || f.calculated_range_status !== 'unknown') throw new Error('Mismatched explanation fact')
      observations.add(s.observation_id)
      return { ...item, source: { ...s, fields } } as unknown as ExplainedItem
    })
    record = { ...r, items } as unknown as ExplanationRecord
  }
  return { report_id: v.report_id, eligible_count: v.eligible_count, evaluation_enrolled: v.evaluation_enrolled, provider_available: v.provider_available, provider: v.provider as ExplanationRecord['provider'], record }
}
function path(report: string) { if (!id(report)) throw new Error('Invalid report'); return `/reports/${report}/explanations` }
function decoder(report: string) { return (v: unknown) => { const result = decodeExplanation(v); if (result.report_id !== report) throw new Error('Mismatched report'); return result } }
export const getExplanation = (report: string, owner: string, signal?: AbortSignal) => accountOwnedRead(path(report), decoder(report), owner, signal)
export const generateExplanation = (report: string, key: string, owner: string, signal?: AbortSignal) => {
  if (!id(key)) throw new Error('Invalid request key')
  return accountMutation(path(report), { idempotency_key: key, consent: true }, decoder(report), owner, 'POST', signal, 65_000)
}
