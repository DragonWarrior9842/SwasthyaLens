import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../auth/auth-context'
import { ApiError, errorMessage, isUnauthorized } from '../../services/api-client'

export function useHistoryAccount() {
  const { state, checkSession } = useAuth()
  const owner = state.status === 'authenticated' ? state.session.user.id : ''
  const authFailure = useCallback((error: unknown) => {
    if (isUnauthorized(error) || (error instanceof ApiError && error.code === 'account_changed')) void checkSession()
  }, [checkSession])
  return { owner, authFailure }
}
export function useOwnedHistory<T>(load: (signal: AbortSignal) => Promise<T>, authFailure: (error: unknown) => void) {
  const [state, setState] = useState<{ data: T | null; error: string | null; loadedFor: typeof load | null; version: number }>({ data: null, error: null, loadedFor: null, version: -1 })
  const [version, setVersion] = useState(0)
  const refresh = useCallback(() => setVersion(v => v + 1), [])
  useEffect(() => {
    const controller = new AbortController()
    void load(controller.signal).then(data => { if (!controller.signal.aborted) setState({ data, error: null, loadedFor: load, version }) }).catch((error: unknown) => {
      if (!controller.signal.aborted) { setState({ data: null, error: errorMessage(error), loadedFor: load, version }); authFailure(error) }
    })
    return () => controller.abort()
  }, [load, authFailure, version])
  useEffect(() => { window.addEventListener('focus', refresh); return () => window.removeEventListener('focus', refresh) }, [refresh])
  const loading = state.loadedFor !== load || state.version !== version
  return { data: loading ? null : state.data, error: loading ? null : state.error, loading, refresh }
}
