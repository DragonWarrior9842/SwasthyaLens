import type { Session } from '../types/auth'
import { ApiError, isUnauthorized, requestJson, requestReportBlob, requestReportUpload } from './api-client'

const REFRESH_MARGIN_SECONDS = 60
let refreshPromise: Promise<Session | null> | null = null
let localQueue: Promise<unknown> = Promise.resolve()

export function decodeSession(payload: unknown): Session {
  if (!payload || typeof payload !== 'object' || !('user' in payload) || !('expires_at' in payload)) throw new Error('Invalid session')
  const { user, expires_at } = payload
  if (!user || typeof user !== 'object' || !('id' in user) || !('email' in user) || typeof user.id !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(user.id) || typeof user.email !== 'string' || !user.email || typeof expires_at !== 'number' || !Number.isSafeInteger(expires_at) || expires_at <= 0) throw new Error('Invalid session')
  return { user: { id: user.id, email: user.email }, expires_at }
}

function decodeCsrf(payload: unknown): string {
  if (!payload || typeof payload !== 'object' || !('csrf_token' in payload) || typeof payload.csrf_token !== 'string' || !payload.csrf_token) throw new Error('Invalid security response')
  return payload.csrf_token
}

function decodeMessage(payload: unknown): void {
  if (!payload || typeof payload !== 'object' || !('message' in payload) || typeof payload.message !== 'string') throw new Error('Invalid acknowledgement')
}

/** A shared lock prevents cookie rotation racing login/logout or another browser tab. */
export function withSessionLock<T>(operation: () => Promise<T>): Promise<T> {
  const run = () => {
    if (typeof window !== 'undefined' && (typeof navigator === 'undefined' || !navigator.locks)) {
      throw new ApiError('configuration', 'Secure session coordination is unavailable. Use an up-to-date browser over HTTPS, or the local development address.')
    }
    return typeof navigator !== 'undefined' && navigator.locks
      ? navigator.locks.request('swasthyalens-session', operation)
      : operation()
  }
  const result = localQueue.then(run, run)
  localQueue = result.catch(() => undefined)
  return result
}

async function writeWithCsrf<T>(path: string, body: object, decode: (payload: unknown) => T, method: 'POST' | 'PATCH' | 'DELETE' = 'POST', signal?: AbortSignal, timeoutMs = 15_000): Promise<T> {
  // Fetch inside the session lock: a token cannot be overtaken by another tab's cookie update.
  const cancellation = signal ? { signal } : {}
  const csrfToken = await requestJson('/auth/csrf', decodeCsrf, { credentials: 'include', timeoutMs: 15_000, ...cancellation })
  return requestJson(path, decode, { credentials: 'include', method, body, csrfToken, timeoutMs, ...cancellation })
}

export function accountRead<T>(path: string, decode: (payload: unknown) => T, signal?: AbortSignal): Promise<T> {
  return requestJson(path, decode, { credentials: 'include', timeoutMs: 15_000, ...(signal ? { signal } : {}) })
}

export function accountPatch<T>(path: string, body: object, decode: (payload: unknown) => T, expectedOwnerId: string): Promise<T> {
  return accountMutation(path, body, decode, expectedOwnerId, 'PATCH')
}

function withCurrentAccount<T>(expectedOwnerId: string, operation: () => Promise<T>, signal?: AbortSignal): Promise<T> {
  return withSessionLock(async () => {
    // Preserve the editor's intent if a different tab changed accounts while this write waited.
    // This ID is never sent as authorization; the server remains the authority for ownership.
    signal?.throwIfAborted()
    const current = await accountRead('/auth/me', decodeSession, signal)
    if (current.user.id !== expectedOwnerId) throw new ApiError('account_changed', 'The signed-in account changed. Please review the current account before saving again.')
    signal?.throwIfAborted()
    return operation()
  })
}

export function accountOwnedRead<T>(path: string, decode: (payload: unknown) => T, expectedOwnerId: string, signal?: AbortSignal): Promise<T> {
  return withCurrentAccount(expectedOwnerId, () => accountRead(path, decode, signal), signal)
}

export function accountMutation<T>(path: string, body: object, decode: (payload: unknown) => T, expectedOwnerId: string, method: 'POST' | 'PATCH' | 'DELETE', signal?: AbortSignal, timeoutMs = 15_000): Promise<T> {
  return withCurrentAccount(expectedOwnerId, () => writeWithCsrf(path, body, decode, method, signal, timeoutMs), signal)
}

export function accountUpload<T>(path: string, file: Blob, decode: (payload: unknown) => T, expectedOwnerId: string, signal?: AbortSignal): Promise<T> {
  return withCurrentAccount(expectedOwnerId, async () => {
    const cancellation = signal ? { signal } : {}
    const csrfToken = await requestJson('/auth/csrf', decodeCsrf, { credentials: 'include', timeoutMs: 15_000, ...cancellation })
    return requestReportUpload(path, file, decode, { credentials: 'include', csrfToken, timeoutMs: 90_000, ...cancellation })
  }, signal)
}

export function accountDownload(path: string, expectedType: string, expectedBytes: number, expectedOwnerId: string, signal?: AbortSignal): Promise<Blob> {
  return withCurrentAccount(expectedOwnerId, () => requestReportBlob(path, expectedType, expectedBytes, { credentials: 'include', timeoutMs: 60_000, ...(signal ? { signal } : {}) }), signal)
}

/** One refresh attempt, with another-tab recheck, and no replay of account mutations. */
export function restoreSession(): Promise<Session | null> {
  if (refreshPromise) return refreshPromise
  refreshPromise = withSessionLock(async () => {
    try {
      const current = await accountRead('/auth/me', decodeSession)
      if (current.expires_at > Date.now() / 1000 + REFRESH_MARGIN_SECONDS) return current
    } catch (error) {
      if (!isUnauthorized(error)) throw error
    }
    try {
      return await writeWithCsrf('/auth/refresh', {}, decodeSession)
    } catch (error) {
      if (isUnauthorized(error)) return null
      throw error
    }
  }).finally(() => { refreshPromise = null })
  return refreshPromise
}

export function signIn(email: string, password: string): Promise<Session> {
  return withSessionLock(() => writeWithCsrf('/auth/login', { email, password }, decodeSession))
}

export function signUp(email: string, password: string): Promise<void> {
  return withSessionLock(() => writeWithCsrf('/auth/signup', { email, password }, decodeMessage))
}

export function verifyEmail(email: string, token: string): Promise<Session> {
  return withSessionLock(() => writeWithCsrf('/auth/verify-email', { email, token }, decodeSession))
}

export function resendVerification(email: string): Promise<void> {
  return withSessionLock(() => writeWithCsrf('/auth/resend-verification', { email }, decodeMessage))
}

export function signOut(): Promise<'revoked' | 'local-only'> {
  return withSessionLock(async () => {
    const csrfToken = await requestJson('/auth/csrf', decodeCsrf, { credentials: 'include', timeoutMs: 15_000 })
    try {
      await requestJson('/auth/logout', decodeMessage, { credentials: 'include', method: 'POST', body: {}, csrfToken, timeoutMs: 15_000 })
      return 'revoked'
    } catch (error) {
      // Only the logout endpoint's 503 guarantees local cookies were cleared.
      if (error instanceof ApiError && error.status === 503 && error.code === 'logout_incomplete') return 'local-only'
      throw error
    }
  })
}
