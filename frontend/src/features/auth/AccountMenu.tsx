import { useI18n } from '../../i18n/core'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../../components/Button'
import { errorMessage } from '../../services/api-client'
import { useAuth } from './auth-context'
import { NotificationLink } from '../system/Notifications'

export function AccountMenu() {
  const { t, copy } = useI18n()
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
    <header className="account-bar" aria-label={t("Your account")}>
      <div className="account-bar__identity"><span>{t("PERSONAL WORKSPACE")}</span><Link to="/settings" className="text-link" aria-label={t("Account settings for {p0}", { p0: state.session.user.email })}>{state.session.user.email}</Link></div>
      <Button variant="secondary" size="sm" disabled={busy} onClick={() => { void handleLogout() }}>{busy ? t("Signing out…") : t("Sign out")}</Button>
      {error && <p className="account-bar__error form-error" role="alert">{copy(error)}{" " + t("Sign-out has not been confirmed.")}</p>}
      <NotificationLink />
    </header>
  )
}
