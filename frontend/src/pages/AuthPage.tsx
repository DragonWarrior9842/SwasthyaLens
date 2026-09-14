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
      <aside className="auth-story" aria-label="About SwasthyaLens">
        <Brand />
        <div className="auth-story__copy">
          <p className="eyebrow">A LITTLE MORE CLARITY</p>
          <h2>Your health.<br />Your understanding.</h2>
          <p>A thoughtful place to bring your health information together, one step at a time.</p>
        </div>
        <p className="auth-story__note">Health information and understanding.<br />Always yours to explore.</p>
      </aside>
      <main className="auth-main" id="main-content">
        <div className="auth-mobile-brand auth-brand"><Brand /></div>
        <section className="auth-card" aria-labelledby="auth-heading">
          <p className="eyebrow">SWASTHYALENS · YOUR ACCOUNT</p>
          <h1 ref={heading} tabIndex={-1} id="auth-heading">{headings[mode]}</h1>
          <p className="auth-description">
            {mode === 'sign-in' ? 'Sign in to your personal workspace.' : mode === 'sign-up' ? 'Create an account with your email and a strong password.' : 'Enter the six-digit code sent to your email to finish confirming your account.'}
          </p>
          {notice && <div className="form-notice" role="status">{notice}</div>}
          {state.status === 'checking' ? <LoadingState title="Checking your session…" /> : state.status === 'unavailable' ? (
            <ErrorState title="Account service unavailable" description={state.message} onRetry={() => { void checkSession() }} />
          ) : (
            <>
              <form className="account-form" onSubmit={(event) => { void submit(event) }} aria-busy={busy}>
                <div className="form-field">
                  <label htmlFor="auth-email">Email address</label>
                  <input id="auth-email" name="email" type="email" autoComplete="email" autoCapitalize="none" spellCheck={false} required maxLength={254} value={email} onChange={(event) => setEmail(event.target.value)} disabled={busy} />
                </div>
                {mode === 'verify-email' ? (
                  <div className="form-field">
                    <label htmlFor="auth-code">Confirmation code</label>
                    <input id="auth-code" name="code" type="text" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" minLength={6} maxLength={6} required value={token} onChange={(event) => setToken(event.target.value.replace(/\D/g, '').slice(0, 6))} disabled={busy} aria-describedby="code-help" />
                    <p id="code-help">Codes expire. Never share this code with anyone.</p>
                  </div>
                ) : (
                  <div className="form-field">
                    <label htmlFor="auth-password">Password</label>
                    <input id="auth-password" name="password" type="password" autoComplete={mode === 'sign-up' ? 'new-password' : 'current-password'} minLength={mode === 'sign-up' ? 12 : 1} maxLength={128} required value={password} onChange={(event) => setPassword(event.target.value)} disabled={busy} aria-describedby={mode === 'sign-up' ? 'password-help' : undefined} />
                    {mode === 'sign-up' && <p id="password-help">Use at least 12 characters. A unique passphrase works well.</p>}
                  </div>
                )}
                {error && <div className="form-error" role="alert">{error}</div>}
                {message && <div className="form-success" role="status">{message}</div>}
                {confirmationNeeded && <Link className="text-link" to="/auth/verify-email" state={routeState} onClick={() => setPendingEmail(email.trim())}>Enter your email confirmation code</Link>}
                <Button type="submit" disabled={busy} className="auth-submit">
                  {busy ? 'Please wait…' : mode === 'sign-in' ? 'Sign in' : mode === 'sign-up' ? 'Create account' : 'Confirm email'}
                </Button>
              </form>
              {mode === 'verify-email' && (
                <div className="verification-actions">
                  <Button variant="secondary" disabled={busy || resendAfter > 0 || !email.trim()} onClick={() => { void resend() }}>{resendAfter > 0 ? `Resend available in ${resendAfter}s` : 'Resend confirmation code'}</Button>
                  <p>Development email delivery is limited to eligible project addresses. If no code arrives, contact the project administrator.</p>
                </div>
              )}
              <div className="auth-switch">
                {mode === 'sign-in' ? <>New here? <Link className="text-link" to="/auth/sign-up" state={routeState}>Create an account</Link></> : <>Already have an account? <Link className="text-link" to="/auth/sign-in" state={routeState}>Sign in</Link></>}
              </div>
              {mode === 'sign-in' && <p className="auth-help">Need help signing in? Contact the project administrator.</p>}
            </>
          )}
        </section>
        <p className="auth-disclaimer">SwasthyaLens offers health information, not medical diagnoses.</p>
      </main>
    </div>
  )
}
