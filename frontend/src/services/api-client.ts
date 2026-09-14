import { resolveApiBaseUrl } from '../lib/config'

const publicErrors = {
  unauthenticated: 'Your session has ended. Please sign in again.',
  invalid_credentials: 'The email or password is incorrect.',
  email_not_confirmed: 'Confirm your email before signing in.',
  invalid_code: 'That confirmation code is invalid or has expired.',
  session_expired: 'Your session has ended. Please sign in again.',
  service_unavailable: 'The account service is temporarily unavailable. Please try again shortly.',
  csrf_failed: 'The security check expired. Please submit the form again.',
  validation_error: 'Check the information entered and try again.',
  rate_limited: 'Too many attempts. Please wait before trying again.',
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
  method?: 'GET' | 'POST' | 'PATCH'
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
        Accept: 'application/json',
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...(options.csrfToken ? { 'X-CSRF-Token': options.csrfToken } : {}),
      },
      ...(options.body ? { body: JSON.stringify(options.body) } : {}),
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
      const payload: unknown = await response.json()
      return decode(payload)
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
