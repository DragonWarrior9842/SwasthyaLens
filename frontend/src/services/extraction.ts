import { accountMutation, accountOwnedRead } from './auth'

export type RunStatus = 'queued' | 'processing' | 'completed' | 'failed'
export interface ProcessingRun {
  id: string; report_id: string; status: RunStatus; attempt: number
  created_at: string; started_at: string | null; finished_at: string | null; deadline_at: string
  error_category: string | null; processor: string | null; page_count: number | null
}
export interface ExtractedPage {
  page_number: number; text: string; method: 'native_text' | 'ocr'
  confidence: number | null; warnings: string[]
}
export interface ExtractionResult { run: ProcessingRun; pages: ExtractedPage[] }
const idPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const failures = ['corrupt_document', 'encrypted_document', 'unsupported_document', 'page_limit_exceeded', 'resource_limit_exceeded', 'extractor_failure', 'ocr_unavailable', 'ocr_failure', 'timeout', 'interrupted', 'source_unavailable']
function object(value: unknown): value is Record<string, unknown> { return !!value && typeof value === 'object' && !Array.isArray(value) }
function date(value: unknown): value is string { return typeof value === 'string' && Number.isFinite(Date.parse(value)) }
function integer(value: unknown, min: number, max: number): value is number { return typeof value === 'number' && Number.isInteger(value) && value >= min && value <= max }
function nullableDate(value: unknown): value is string | null { return value === null || date(value) }
export function decodeRun(value: unknown): ProcessingRun {
  if (!object(value) || typeof value.id !== 'string' || !idPattern.test(value.id) || typeof value.report_id !== 'string' || !idPattern.test(value.report_id) || !['queued', 'processing', 'completed', 'failed'].includes(String(value.status)) || !integer(value.attempt, 1, 3) || !date(value.created_at) || !date(value.deadline_at) || !nullableDate(value.started_at) || !nullableDate(value.finished_at) || !(value.error_category === null || failures.includes(String(value.error_category))) || !(value.processor === null || (typeof value.processor === 'string' && value.processor.length <= 500)) || !(value.page_count === null || integer(value.page_count, 1, 20))) throw new Error('Invalid processing run')
  if ((value.status === 'failed') !== (value.error_category !== null) || (['failed', 'completed'].includes(String(value.status))) !== (value.finished_at !== null) || (value.status === 'completed' && (value.page_count === null || value.processor === null))) throw new Error('Inconsistent processing run')
  return { id: value.id, report_id: value.report_id, status: value.status as RunStatus, attempt: value.attempt, created_at: value.created_at, started_at: value.started_at, finished_at: value.finished_at, deadline_at: value.deadline_at, error_category: value.error_category as string | null, processor: value.processor, page_count: value.page_count }
}
export function decodeHistory(value: unknown): ProcessingRun[] {
  if (!object(value) || !Array.isArray(value.runs) || value.runs.length > 3) throw new Error('Invalid processing history')
  const runs = value.runs.map(decodeRun)
  if (new Set(runs.map(run => run.id)).size !== runs.length || new Set(runs.map(run => run.report_id)).size > 1) throw new Error('Inconsistent processing history')
  return runs
}
export function decodeExtraction(value: unknown): ExtractionResult {
  if (!object(value) || !Array.isArray(value.pages)) throw new Error('Invalid extraction')
  const run = decodeRun(value.run)
  if (run.status !== 'completed' || value.pages.length !== run.page_count) throw new Error('Incomplete extraction')
  const pages = value.pages.map((page: unknown, index): ExtractedPage => {
    if (!object(page) || page.page_number !== index + 1 || typeof page.text !== 'string' || page.text.length > 20000 || !['native_text', 'ocr'].includes(String(page.method)) || !(page.confidence === null || (typeof page.confidence === 'number' && Number.isFinite(page.confidence) && page.confidence >= 0 && page.confidence <= 100)) || !Array.isArray(page.warnings) || !page.warnings.every(w => ['no_text', 'orientation_uncertain', 'layout_requires_review'].includes(String(w))) || (page.method === 'native_text' && page.confidence !== null)) throw new Error('Invalid extracted page')
    return { page_number: index + 1, text: page.text, method: page.method as 'native_text' | 'ocr', confidence: page.confidence, warnings: page.warnings as string[] }
  })
  return { run, pages }
}
function path(id: string) { if (!idPattern.test(id)) throw new Error('Invalid report ID'); return `/reports/${id}` }
export async function getProcessing(id: string, owner: string, signal?: AbortSignal) {
  const runs = await accountOwnedRead(`${path(id)}/processing`, decodeHistory, owner, signal)
  if (runs.some(run => run.report_id !== id)) throw new Error('Mismatched processing history')
  return runs
}
export async function processReport(id: string, key: string, owner: string, signal?: AbortSignal) {
  const run = await accountMutation(`${path(id)}/process`, { idempotency_key: key }, decodeRun, owner, 'POST', signal)
  if (run.report_id !== id) throw new Error('Mismatched processing run')
  return run
}
export async function getExtraction(id: string, runId: string, owner: string, signal?: AbortSignal) {
  if (!idPattern.test(runId)) throw new Error('Invalid run ID')
  const result = await accountOwnedRead(`${path(id)}/extraction?run_id=${runId}`, decodeExtraction, owner, signal)
  if (result.run.report_id !== id || result.run.id !== runId) throw new Error('Mismatched extraction')
  return result
}
