import { useI18n } from '../i18n/core'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Brand } from '../components/Brand'
import { Button } from '../components/Button'
import { ErrorState } from '../components/ErrorState'
import { LoadingState } from '../components/LoadingState'
import { useAuth } from '../features/auth/auth-context'
import { safeReturnTo } from '../features/auth/redirect'
import { ApiError, errorMessage } from '../services/api-client'
import { resendVerification, signIn, signUp, verifyEmail } from '../services/auth'

type AuthMode = 'sign-in' | 'sign-up' | 'verify-email'

const headings = {
  'sign-in': 'Welcome back',
  'sign-up': 'Your health story starts here',
  'verify-email': 'Check your email',
}

export function AuthPage({ mode }: { mode: AuthMode }) {
  // Remount form fields on a route change, discarding any password/code draft.
  return <AuthForm key={mode} mode={mode} />
}

function AuthForm({ mode }: { mode: AuthMode }) {
  const { t, copy } = useI18n()
  const { state, pendingEmail, notice, setPendingEmail, acceptSession, checkSession } = useAuth()
  const [email, setEmail] = useState(pendingEmail)
  const [password, setPassword] = useState('')
  const [token, setToken] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [confirmationNeeded, setConfirmationNeeded] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [resendAfter, setResendAfter] = useState(0)
  const heading = useRef<HTMLHeadingElement>(null)
  const location = useLocation()
  const navigate = useNavigate()
  const locationState: unknown = location.state
  const returnTo = safeReturnTo(locationState && typeof locationState === 'object' && 'returnTo' in locationState ? locationState.returnTo : undefined)
  const routeState = { returnTo }

  useEffect(() => { heading.current?.focus() }, [])
  useEffect(() => {
    if (resendAfter <= 0) return
    const timer = window.setTimeout(() => setResendAfter(resendAfter - 1), 1_000)
    return () => window.clearTimeout(timer)
  }, [resendAfter])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    setBusy(true)
    setError(null)
    setMessage(null)
    setConfirmationNeeded(false)
    const address = email.trim()
    // The request closure owns its short-lived value; no password remains in the field.
    const submittedPassword = password
    const submittedToken = token
    setPassword('')
    setToken('')
    try {
      if (mode === 'sign-up') {
        await signUp(address, submittedPassword)
        setPendingEmail(address)
        navigate('/auth/verify-email', { state: routeState })
      } else {
        const session = mode === 'verify-email' ? await verifyEmail(address, submittedToken) : await signIn(address, submittedPassword)
        acceptSession(session)
        navigate(returnTo, { replace: true })
      }
    } catch (failure) {
      setError(errorMessage(failure))
      setConfirmationNeeded(failure instanceof ApiError && failure.code === 'email_not_confirmed')
    } finally {
      setBusy(false)
    }
  }

  async function resend() {
    if (busy || resendAfter > 0 || !email.trim()) return
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      await resendVerification(email.trim())
      setMessage('If this email needs confirmation, a new code will be sent. Use the most recent code.')
      setResendAfter(60)
    } catch (failure) {
      setError(errorMessage(failure))
    } finally {
      setBusy(false)
    }
  }

  if (state.status === 'authenticated') return <Navigate to={returnTo} replace />

  return (
    <div className="auth-shell">
      <aside className="auth-story" aria-label={t("About SwasthyaLens")}>
        <Brand />
        <div className="auth-story__copy">
          <p className="eyebrow">{t("A LITTLE MORE CLARITY")}</p>
          <h2>{t("Your health.")}<br />{t("Your understanding.")}</h2>
          <p>{t("A thoughtful place to bring your health information together, one step at a time.")}</p>
        </div>
        <p className="auth-story__note">{t("Health information and understanding.")}<br />{t("Always yours to explore.")}</p>
      </aside>
      <main className="auth-main" id="main-content">
        <div className="auth-mobile-brand auth-brand"><Brand /></div>
        <section className="auth-card" aria-labelledby="auth-heading">
          <p className="eyebrow">{t("SWASTHYALENS · YOUR ACCOUNT")}</p>
          <h1 ref={heading} tabIndex={-1} id="auth-heading">{copy(headings[mode])}</h1>
          <p className="auth-description">
            {mode === 'sign-in' ? t("Sign in to your personal workspace.") : mode === 'sign-up' ? t("Create an account with your email and a strong password.") : t("Enter the six-digit code sent to your email to finish confirming your account.")}
          </p>
          {notice && <div className="form-notice" role="status">{copy(notice)}</div>}
          {state.status === 'checking' ? <LoadingState title={t("Checking your session…")} /> : state.status === 'unavailable' ? (
            <ErrorState title={t("Account service unavailable")} description={copy(state.message)} onRetry={() => { void checkSession() }} />
          ) : (
            <>
              <form className="account-form" onSubmit={(event) => { void submit(event) }} aria-busy={busy}>
                <div className="form-field">
                  <label htmlFor="auth-email">{t("Email address")}</label>
                  <input id="auth-email" name="email" type="email" autoComplete="email" autoCapitalize="none" spellCheck={false} required maxLength={254} value={email} onChange={(event) => setEmail(event.target.value)} disabled={busy} />
                </div>
                {mode === 'verify-email' ? (
                  <div className="form-field">
                    <label htmlFor="auth-code">{t("Confirmation code")}</label>
                    <input id="auth-code" name="code" type="text" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" minLength={6} maxLength={6} required value={token} onChange={(event) => setToken(event.target.value.replace(/\D/g, '').slice(0, 6))} disabled={busy} aria-describedby="code-help" />
                    <p id="code-help">{t("Codes expire. Never share this code with anyone.")}</p>
                  </div>
                ) : (
                  <div className="form-field">
                    <label htmlFor="auth-password">{t("Password")}</label>
                    <input id="auth-password" name="password" type="password" autoComplete={mode === 'sign-up' ? 'new-password' : 'current-password'} minLength={mode === 'sign-up' ? 12 : 1} maxLength={128} required value={password} onChange={(event) => setPassword(event.target.value)} disabled={busy} aria-describedby={mode === 'sign-up' ? 'password-help' : undefined} />
                    {mode === 'sign-up' && <p id="password-help">{t("Use at least 12 characters. A unique passphrase works well.")}</p>}
                  </div>
                )}
                {error && <div className="form-error" role="alert">{copy(error)}</div>}
                {message && <div className="form-success" role="status">{copy(message)}</div>}
                {confirmationNeeded && <Link className="text-link" to="/auth/verify-email" state={routeState} onClick={() => setPendingEmail(email.trim())}>{t("Enter your email confirmation code")}</Link>}
                <Button type="submit" disabled={busy} className="auth-submit">
                  {busy ? t("Please wait…") : mode === 'sign-in' ? t("Sign in") : mode === 'sign-up' ? t("Create account") : t("Confirm email")}
                </Button>
              </form>
              {mode === 'verify-email' && (
                <div className="verification-actions">
                  <Button variant="secondary" disabled={busy || resendAfter > 0 || !email.trim()} onClick={() => { void resend() }}>{resendAfter > 0 ? t("Resend available in {p0}s", { p0: resendAfter }) : t("Resend confirmation code")}</Button>
                  <p>{t("Development email delivery is limited to eligible project addresses. If no code arrives, contact the project administrator.")}</p>
                </div>
              )}
              <div className="auth-switch">
                {mode === 'sign-in' ? <>{"" + t("New here?") + " "}<Link className="text-link" to="/auth/sign-up" state={routeState}>{t("Create an account")}</Link></> : <>{"" + t("Already have an account?") + " "}<Link className="text-link" to="/auth/sign-in" state={routeState}>{t("Sign in")}</Link></>}
              </div>
              {mode === 'sign-in' && <p className="auth-help">{t("Need help signing in? Contact the project administrator.")}</p>}
            </>
          )}
        </section>
        <p className="auth-disclaimer">{t("SwasthyaLens offers health information, not medical diagnoses.")}</p>
      </main>
    </div>
  )
}
