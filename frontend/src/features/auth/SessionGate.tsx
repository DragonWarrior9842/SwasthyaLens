import { useI18n } from '../../i18n/core'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { Brand } from '../../components/Brand'
import { ErrorState } from '../../components/ErrorState'
import { LoadingState } from '../../components/LoadingState'
import { useAuth } from './auth-context'
import { safeReturnTo } from './redirect'

export function SessionGate() {
  const { t, copy } = useI18n()
  const { state, checkSession } = useAuth()
  const location = useLocation()
  if (state.status === 'anonymous') return <Navigate to="/auth/sign-in" state={{ returnTo: safeReturnTo(location.pathname) }} replace />
  if (state.status === 'authenticated') return <Outlet key={state.session.user.id} />
  return (
    <div className="session-screen">
      <div className="auth-brand"><Brand /></div>
      <main className="card session-card">
        {state.status === 'checking'
          ? <LoadingState title={t("Checking your session…")} description={t("Connecting to your private workspace.")} />
          : <ErrorState title={t("Unable to check your session")} description={copy(state.message)} onRetry={() => { void checkSession() }} />}
      </main>
    </div>
  )
}
