import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { errorMessage } from '../../services/api-client'
import { restoreSession, signOut } from '../../services/auth'
import type { AuthState, Session } from '../../types/auth'
import { AuthContext } from './auth-context'
import { sessionCheckDelay } from './session-timing'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: 'checking' })
  const [pendingEmail, setPendingEmail] = useState('')
  const [notice, setNotice] = useState<string | null>(null)
  const revision = useRef(0)
  const channel = useRef<BroadcastChannel | null>(null)

  const checkSession = useCallback(async () => {
    const current = ++revision.current
    try {
      const session = await restoreSession()
      if (current === revision.current) setState(session ? { status: 'authenticated', session } : { status: 'anonymous' })
    } catch (error) {
      if (current === revision.current) setState({ status: 'unavailable', message: errorMessage(error) })
    }
  }, [])

  const acceptSession = useCallback((session: Session) => {
    revision.current++
    setState({ status: 'authenticated', session })
    setPendingEmail('')
    setNotice(null)
    // Cross-tab notifications carry no identity, credentials or profile data.
    channel.current?.postMessage('session-changed')
  }, [])

  const logout = useCallback(async () => {
    revision.current++
    const outcome = await signOut()
    setNotice(outcome === 'local-only' ? 'You are signed out on this browser, but the service could not confirm remote session revocation. Sign in and sign out again when the service is available.' : null)
    setState({ status: 'anonymous' })
    setPendingEmail('')
    channel.current?.postMessage('session-changed')
  }, [])

  useEffect(() => {
    let active = true
    const current = ++revision.current
    void restoreSession().then((session) => {
      if (active && current === revision.current) setState(session ? { status: 'authenticated', session } : { status: 'anonymous' })
    }).catch((error: unknown) => {
      if (active && current === revision.current) setState({ status: 'unavailable', message: errorMessage(error) })
    })
    const recheck = () => { if (document.visibilityState === 'visible') void checkSession() }
    window.addEventListener('focus', recheck)
    document.addEventListener('visibilitychange', recheck)
    if (typeof BroadcastChannel !== 'undefined') {
      const connection = new BroadcastChannel('swasthyalens-session')
      connection.onmessage = (event: MessageEvent<unknown>) => {
        if (event.data === 'session-changed') {
          // Discard the previous account's rendered content before the new read resolves.
          setState({ status: 'checking' })
          void checkSession()
        }
      }
      channel.current = connection
    }
    return () => {
      active = false
      window.removeEventListener('focus', recheck)
      document.removeEventListener('visibilitychange', recheck)
      channel.current?.close()
      channel.current = null
    }
  }, [checkSession])

  useEffect(() => {
    if (state.status !== 'authenticated') return
    const delay = sessionCheckDelay(state.session.expires_at)
    const timer = window.setTimeout(() => { void checkSession() }, delay)
    return () => window.clearTimeout(timer)
  }, [state, checkSession])

  return <AuthContext value={{ state, pendingEmail, notice, setPendingEmail, acceptSession, checkSession, logout }}>{children}</AuthContext>
}
