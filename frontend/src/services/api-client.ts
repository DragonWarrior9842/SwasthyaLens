import { resolveApiBaseUrl } from '../lib/config'

export type ApiErrorCode = 'configuration' | 'network' | 'timeout' | 'http' | 'invalid-response'

export class ApiError extends Error {
  readonly code: ApiErrorCode

  constructor(code: ApiErrorCode, message: string) {
    super(message)
    this.name = 'ApiError'
    this.code = code
  }
}

interface RequestOptions {
  signal?: AbortSignal
  baseUrl?: string
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
  }, 5_000)

  try {
    const response = await fetch(`${baseUrl}/${path.replace(/^\/+/, '')}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      credentials: 'omit',
      cache: 'no-store',
      signal: controller.signal,
    })

    if (!response.ok) {
      throw new ApiError('http', 'The local API returned an unsuccessful response.')
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
