import type { Report, ReportConfig, ReportDeletion, ReportMediaType, ReportPage, ReportStatus } from '../types/reports'
import { accountDownload, accountMutation, accountOwnedRead, accountUpload } from './auth'

const mediaTypes = ['application/pdf', 'image/jpeg', 'image/png'] as const
const statuses: ReportStatus[] = ['pending_upload', 'uploading', 'uploaded', 'upload_failed', 'deleting']
const idPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

function record(value: unknown): value is Record<string, unknown> { return !!value && typeof value === 'object' && !Array.isArray(value) }
function mediaType(value: unknown): value is ReportMediaType { return typeof value === 'string' && mediaTypes.some((allowed) => allowed === value) }
function size(value: unknown): value is number { return typeof value === 'number' && Number.isSafeInteger(value) && value > 0 && value <= 5 * 1024 * 1024 }
function date(value: unknown): value is string { return typeof value === 'string' && Number.isFinite(Date.parse(value)) }

export function decodeReport(value: unknown): Report {
  if (!record(value) || typeof value.id !== 'string' || !idPattern.test(value.id) || typeof value.original_filename !== 'string' || filenameError(value.original_filename) || !mediaType(value.media_type) || !size(value.size_bytes) || typeof value.status !== 'string' || !statuses.includes(value.status as ReportStatus) || !date(value.created_at) || !date(value.updated_at) || !(value.error_category === null || typeof value.error_category === 'string')) throw new Error('Invalid report')
  return { id: value.id, original_filename: value.original_filename, media_type: value.media_type, size_bytes: value.size_bytes, status: value.status as ReportStatus, created_at: value.created_at, updated_at: value.updated_at, error_category: value.error_category }
}

export function decodeReportPage(value: unknown): ReportPage {
  if (!record(value) || !Array.isArray(value.reports) || value.reports.length > 100 || !(value.next_cursor === null || (typeof value.next_cursor === 'string' && value.next_cursor.length > 0 && value.next_cursor.length <= 2048))) throw new Error('Invalid report list')
  const reports = value.reports.map(decodeReport)
  if (new Set(reports.map((report) => report.id)).size !== reports.length) throw new Error('Duplicate reports')
  return { reports, next_cursor: value.next_cursor }
}

export function decodeReportConfig(value: unknown): ReportConfig {
  if (!record(value) || !size(value.max_upload_bytes) || !Array.isArray(value.allowed_media_types) || value.allowed_media_types.length === 0 || !value.allowed_media_types.every(mediaType) || new Set(value.allowed_media_types).size !== value.allowed_media_types.length) throw new Error('Invalid report configuration')
  return { max_upload_bytes: value.max_upload_bytes, allowed_media_types: value.allowed_media_types }
}

export function decodeDeletion(value: unknown): ReportDeletion {
  if (!record(value) || typeof value.report_id !== 'string' || !idPattern.test(value.report_id) || (value.status !== 'deleting' && value.status !== 'deleted')) throw new Error('Invalid deletion acknowledgement')
  return { report_id: value.report_id, status: value.status }
}

function decodeCleanup(value: unknown): { pending: number; cleaned: number } {
  if (!record(value) || typeof value.pending !== 'number' || typeof value.cleaned !== 'number' || !Number.isSafeInteger(value.pending) || !Number.isSafeInteger(value.cleaned) || value.pending < 0 || value.cleaned < 0) throw new Error('Invalid cleanup acknowledgement')
  return { pending: value.pending, cleaned: value.cleaned }
}

function reportPath(id: string): string {
  if (!idPattern.test(id)) throw new Error('Invalid report identifier')
  return `/reports/${id}`
}

export function getReportConfig(expectedOwnerId: string, signal?: AbortSignal) { return accountOwnedRead('/reports/config', decodeReportConfig, expectedOwnerId, signal) }
export function listReports(expectedOwnerId: string, cursor: string | null = null, signal?: AbortSignal) { return accountOwnedRead(`/reports${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ''}`, decodeReportPage, expectedOwnerId, signal) }
export function getReport(id: string, expectedOwnerId: string, signal?: AbortSignal) { return accountOwnedRead(reportPath(id), decodeReport, expectedOwnerId, signal) }
export function reserveReport(file: File, idempotencyKey: string, expectedOwnerId: string, signal?: AbortSignal) {
  return accountMutation('/reports', { original_filename: file.name, media_type: file.type, size_bytes: file.size, idempotency_key: idempotencyKey }, decodeReport, expectedOwnerId, 'POST', signal)
}
export function uploadReport(id: string, file: File, expectedOwnerId: string, signal?: AbortSignal) {
  return accountUpload(`${reportPath(id)}/file`, file, decodeReport, expectedOwnerId, signal)
}
export async function deleteReport(id: string, expectedOwnerId: string, signal?: AbortSignal) {
  const result = await accountMutation(reportPath(id), {}, decodeDeletion, expectedOwnerId, 'DELETE', signal)
  if (result.report_id !== id) throw new Error('Mismatched deletion acknowledgement')
  return result
}
export function cleanupReports(expectedOwnerId: string, signal?: AbortSignal) { return accountMutation('/reports/cleanup', {}, decodeCleanup, expectedOwnerId, 'POST', signal) }
export function downloadReport(report: Report, expectedOwnerId: string, signal?: AbortSignal) {
  return accountDownload(`${reportPath(report.id)}/file`, report.media_type, report.size_bytes, expectedOwnerId, signal)
}

export function filenameError(name: string): string | null {
  if (!name || name.trim() !== name || [...name].length > 120 || new TextEncoder().encode(name).length > 240 || /[\\/:<>"|?*\p{Cc}\p{Cf}]/u.test(name) || name.startsWith('.') || name.endsWith('.') || /^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(name)) return 'Use a short filename without paths, control characters or special filesystem characters.'
  return null
}

export function validateReportFile(file: File, config: ReportConfig): string | null {
  const invalidName = filenameError(file.name)
  if (invalidName) return invalidName
  if (file.size === 0) return 'This file is empty. Choose a report that contains data.'
  if (file.size > config.max_upload_bytes) return `This file exceeds the ${formatBytes(config.max_upload_bytes)} limit. Choose a smaller report.`
  const extension = file.name.split('.').at(-1)?.toLowerCase()
  const expectedType = extension === 'pdf' ? 'application/pdf' : extension === 'jpg' || extension === 'jpeg' ? 'image/jpeg' : extension === 'png' ? 'image/png' : null
  if (!expectedType || file.type !== expectedType || !config.allowed_media_types.includes(expectedType)) return 'Choose a PDF, JPEG or PNG with a matching filename and file type.'
  return null
}

export function formatBytes(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${new Intl.NumberFormat('en', { maximumFractionDigits: 1 }).format(bytes / (1024 * 1024))} MiB`
  return `${Math.max(1, Math.ceil(bytes / 1024))} KiB`
}

/** Force attachment download; never render user-controlled content in this application. */
export function saveReportAttachment(blob: Blob, filename: string): void {
  if (filenameError(filename)) throw new Error('Invalid attachment filename')
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.rel = 'noopener noreferrer'
  try {
    document.body.append(link)
    link.click()
  } finally {
    link.remove()
    // Allow the browser to begin its download before releasing the in-memory object.
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
}
