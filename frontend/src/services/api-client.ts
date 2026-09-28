import { resolveApiBaseUrl } from '../lib/config'

const publicErrors = {
  export_unavailable: 'The export could not be verified. Please try again.',
  export_timeout: 'The export took too long. Choose a smaller period or source.',
  export_capacity: 'Export limit reached: choose at most 200 observations from 20 reports and a smaller period.',
  export_invalid: 'Choose a valid export period of at most 366 days and a valid source.',
  export_csv_unsafe: 'Some source text could be interpreted as a spreadsheet formula. Choose JSON to preserve it safely.',
  notification_unavailable: 'Notifications are temporarily unavailable.',
  notification_not_found: 'This notification was removed or expired. Refresh notifications.',
  notification_invalid: 'Check the notification request and try again.',
  trend_unavailable: 'Trends are temporarily unavailable. Please try again.',
  trend_capacity: 'This analysis exceeds 500 observations or 50 metric/unit groups. Choose a shorter period or another end date; no partial statistics are shown.',
  trend_unit: 'This exact unit is not supported for this metric. The original remains in health history.',
  trend_invalid: 'Choose a valid period ending today or earlier.',
  explanation_not_found: 'This report or explanation is no longer available.',
  explanation_conflict: 'The source changed. Refresh before trying again.',
  explanation_evidence: 'Publish between one and twenty reviewed findings first.',
  explanation_evaluation_only: 'Only enrolled synthetic evaluation reports are enabled.',
  explanation_disabled: 'Live explanation evaluation is not enabled on this server.',
  explanation_unavailable: 'Report explanations are temporarily unavailable.',
  explanation_rate_limit: 'The explanation limit was reached. Wait before trying again.',
  explanation_budget: 'The Phase 7 evaluation budget has been reached.',
  explanation_invalid: 'The explanation could not be verified.',
  observation_not_found: 'This observation or its source is no longer available. Refresh health history.',
  observation_conflict: 'The observation or review changed. Refresh and review the latest revision before trying again.',
  observation_duplicate_source: 'This source row is already published. Use its original candidate review.',
  observation_limit: 'This account has reached its manual-entry limit.',
  parameter_limit: 'This text extraction has used its three parameter attempts.',
  processing_unavailable: 'Text extraction is not configured on this server.',
  processing_limit: 'This report has reached its three-attempt extraction limit.',
  extraction_not_found: 'No completed text extraction is available for this report.',
  unauthenticated: 'Your session has ended. Please sign in again.',
  invalid_credentials: 'The email or password is incorrect.',
  email_not_confirmed: 'Confirm your email before signing in.',
  invalid_code: 'That confirmation code is invalid or has expired.',
  session_expired: 'Your session has ended. Please sign in again.',
  service_unavailable: 'The account service is temporarily unavailable. Please try again shortly.',
  csrf_failed: 'The security check expired. Please submit the form again.',
  validation_error: 'Check the information entered and try again.',
  rate_limited: 'Too many attempts. Please wait before trying again.',
  logout_incomplete: 'You are signed out locally, but remote session revocation could not be confirmed.',
  account_changed: 'The signed-in account changed. Please review the current account before saving again.',
  report_not_found: 'This report is no longer available. Refresh your report history.',
  invalid_file: 'This file could not be accepted. Choose a valid PDF, JPEG or PNG report.',
  file_too_large: 'This file exceeds the upload limit. Choose a smaller report.',
  unsupported_file_type: 'Choose a PDF, JPEG or PNG report with a matching file extension.',
  filename_invalid: 'Rename the file using a short filename without paths or special characters.',
  report_conflict: 'This report has changed or an operation is still in progress. Refresh its status before trying again.',
  storage_unavailable: 'Private file storage is temporarily unavailable. Please try again shortly.',
  cleanup_pending: 'Deletion is still pending. The report will remain listed until cleanup is confirmed.',
} as const

export type ApiErrorCode = 'configuration' | 'network' | 'timeout' | 'http' | 'invalid-response' | keyof typeof publicErrors

export class ApiError extends Error {
  readonly code: ApiErrorCode
  readonly status: number | undefined

  constructor(code: ApiErrorCode, message: string, status?: number) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
  }
}

export interface RequestOptions {
  signal?: AbortSignal
  baseUrl?: string
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  body?: object
  csrfToken?: string
  credentials?: RequestCredentials
  timeoutMs?: number
}

export function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

export function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : 'Something went wrong. Please try again.'
}

/** All network access passes through this boundary and validates its response. */
export async function requestJson<T>(
  path: string,
  decode: (payload: unknown) => T,
  options: RequestOptions = {},
): Promise<T> {
  return request(path, async (response) => decode(await response.json()), options)
}

const reportFilePath = /^\/reports\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\/file$/i
const reportMediaTypes = ['application/pdf', 'image/jpeg', 'image/png']

/** Only the report byte-transfer route accepts a raw body. Auth writes stay JSON. */
export async function requestReportUpload<T>(path: string, file: Blob, decode: (payload: unknown) => T, options: Omit<RequestOptions, 'body' | 'method'>): Promise<T> {
  if (!reportFilePath.test(path) || !reportMediaTypes.includes(file.type) || options.credentials !== 'include' || !options.csrfToken) {
    throw new ApiError('configuration', 'The report upload request is not configured correctly.')
  }
  return request(path, async (response) => decode(await response.json()), { ...options, method: 'PUT' }, file)
}

/** Download only the expected private attachment, with a bounded response body. */
export async function requestReportBlob(path: string, expectedType: string, expectedBytes: number, options: Omit<RequestOptions, 'body' | 'method'>): Promise<Blob> {
  if (!reportFilePath.test(path) || !reportMediaTypes.includes(expectedType) || !Number.isSafeInteger(expectedBytes) || expectedBytes < 1 || expectedBytes > 5 * 1024 * 1024 || options.credentials !== 'include') {
    throw new ApiError('configuration', 'The report download request is not configured correctly.')
  }
  return request(path, async (response) => {
    const mediaType = response.headers.get('Content-Type')?.split(';')[0]?.trim().toLowerCase()
    if (mediaType !== expectedType || !/^attachment(?:;|$)/i.test(response.headers.get('Content-Disposition') ?? '') || !response.body) throw new Error('Unexpected attachment')
    const length = response.headers.get('Content-Length')
    if (length !== null && (!/^\d+$/.test(length) || Number(length) !== expectedBytes)) throw new Error('Unexpected attachment size')
    const reader = response.body.getReader()
    const parts: Uint8Array<ArrayBuffer>[] = []
    let received = 0
    try {
      while (true) {
        const part = await reader.read()
        if (part.done) break
        received += part.value.byteLength
        if (received > expectedBytes) throw new Error('Attachment exceeds expected size')
        parts.push(new Uint8Array(part.value))
      }
      if (received !== expectedBytes) throw new Error('Incomplete attachment')
      return new Blob(parts, { type: expectedType })
    } finally { await reader.cancel().catch(() => undefined); reader.releaseLock() }
  }, options, undefined, expectedType)
}

/** A separate strict boundary for explicit JSON-to-private-attachment exports. */
export async function requestExportBlob(format: 'csv' | 'json', options: RequestOptions): Promise<Blob> {
  const expected = format === 'csv' ? 'text/csv' : 'application/json'
  if (!['csv', 'json'].includes(format) || options.method !== 'POST' || !options.csrfToken || options.credentials !== 'include' || !options.body) throw new ApiError('configuration', 'The export request is not configured correctly.')
  return request('/exports', async response => {
    const length = response.headers.get('Content-Length')
    if (response.headers.get('Content-Type')?.split(';')[0] !== expected || response.headers.get('Content-Disposition') !== `attachment; filename="swasthyalens-health.${format}"` || !response.headers.get('Cache-Control')?.includes('no-store') || !response.body || !length || !/^\d+$/.test(length) || Number(length) < 1 || Number(length) > 2 * 1024 * 1024) throw new Error('Invalid export attachment')
    const reader = response.body.getReader(), parts: Uint8Array<ArrayBuffer>[] = []
    let size = 0
    try {
      while (true) {
        const part = await reader.read()
        if (part.done) break
        size += part.value.byteLength
        if (size > Number(length)) throw new Error('Oversized export')
        parts.push(new Uint8Array(part.value))
      }
      if (size !== Number(length)) throw new Error('Incomplete export')
      return new Blob(parts, { type: expected })
    } finally { await reader.cancel().catch(() => undefined); reader.releaseLock() }
  }, options, undefined, expected)
}

async function request<T>(path: string, decode: (response: Response) => Promise<T>, options: RequestOptions, rawBody?: Blob, accept = 'application/json'): Promise<T> {
  let baseUrl: string

  try {
    baseUrl = resolveApiBaseUrl(options.baseUrl ?? import.meta.env.VITE_API_BASE_URL)
    if (options.credentials === 'include' && baseUrl !== '/api') {
      if (typeof window === 'undefined' || new URL(baseUrl).origin !== window.location.origin) {
        throw new Error('Account requests require a same-origin API.')
      }
    }
  } catch {
    throw new ApiError('configuration', 'The local API address is not configured correctly.')
  }

  const controller = new AbortController()
  let timedOut = false
  const cancel = () => controller.abort()
  options.signal?.addEventListener('abort', cancel, { once: true })
  if (options.signal?.aborted) controller.abort()

  const timer = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, options.timeoutMs ?? 5_000)

  try {
    const response = await fetch(`${baseUrl}/${path.replace(/^\/+/, '')}`, {
      method: options.method ?? 'GET',
      headers: {
        Accept: accept,
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...(rawBody ? { 'Content-Type': rawBody.type } : {}),
        ...(options.csrfToken ? { 'X-CSRF-Token': options.csrfToken } : {}),
      },
      ...(options.body ? { body: JSON.stringify(options.body) } : {}),
      ...(rawBody ? { body: rawBody } : {}),
      credentials: options.credentials ?? 'omit',
      cache: 'no-store',
      redirect: 'error',
      signal: controller.signal,
    })

    if (!response.ok) {
      // Only render our own allowlisted messages, never provider bodies or validation inputs.
      if (options.credentials === 'include') {
        const payload: unknown = await response.json().catch(() => null)
        if (payload && typeof payload === 'object' && 'code' in payload && typeof payload.code === 'string' && Object.hasOwn(publicErrors, payload.code)) {
          const code = payload.code as keyof typeof publicErrors
          throw new ApiError(code, publicErrors[code], response.status)
        }
      }
      throw new ApiError('http', 'The local API returned an unsuccessful response.', response.status)
    }

    try {
      return await decode(response)
    } catch (error) {
      if (controller.signal.aborted) throw error
      throw new ApiError('invalid-response', 'The local API returned an unexpected response.')
    }
  } catch (error) {
    if (options.signal?.aborted) throw new DOMException('Request cancelled.', 'AbortError')
    if (timedOut) throw new ApiError('timeout', 'The local API did not respond in time.')
    if (error instanceof ApiError) throw error
    throw new ApiError('network', 'The local API could not be reached.')
  } finally {
    clearTimeout(timer)
    options.signal?.removeEventListener('abort', cancel)
  }
}
