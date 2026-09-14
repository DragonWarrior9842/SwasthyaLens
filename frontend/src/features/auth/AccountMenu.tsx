import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../../components/Button'
import { errorMessage } from '../../services/api-client'
import { useAuth } from './auth-context'

export function AccountMenu() {
  const { state, logout } = useAuth()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  if (state.status !== 'authenticated') return null

  async function handleLogout() {
    setBusy(true)
    setError(null)
    try { await logout() }
    catch (failure) { setError(errorMessage(failure)) }
    finally { setBusy(false) }
  }

  return (
    <header className="account-bar" aria-label="Your account">
      <div className="account-bar__identity"><span>PERSONAL WORKSPACE</span><Link to="/settings" className="text-link" aria-label={`Account settings for ${state.session.user.email}`}>{state.session.user.email}</Link></div>
      <Button variant="secondary" size="sm" disabled={busy} onClick={() => { void handleLogout() }}>{busy ? 'Signing out…' : 'Sign out'}</Button>
      {error && <p className="account-bar__error form-error" role="alert">{error} Sign-out has not been confirmed.</p>}
    </header>
  )
}
