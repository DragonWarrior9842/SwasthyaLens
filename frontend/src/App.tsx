import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import { LoadingState } from './components/LoadingState'
import { AppLayout } from './layouts/AppLayout'
import { AuthProvider } from './features/auth/AuthProvider'
import { LocaleProvider } from './i18n/LocaleProvider'
import { SessionGate } from './features/auth/SessionGate'
import { AuthPage } from './pages/AuthPage'
import { NotificationsPage } from './features/system/Notifications'

const AssistantPage = lazy(() => import('./pages/AssistantPage').then(m => ({ default: m.AssistantPage })))
const DashboardPage = lazy(() => import('./pages/DashboardPage').then(m => ({ default: m.DashboardPage })))
const HistoryPage = lazy(() => import('./pages/HistoryPage').then(m => ({ default: m.HistoryPage })))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage').then(m => ({ default: m.NotFoundPage })))
const ReportsPage = lazy(() => import('./pages/ReportsPage').then(m => ({ default: m.ReportsPage })))
const TrendsPage = lazy(() => import('./pages/TrendsPage').then(m => ({ default: m.TrendsPage })))
const SettingsPage = lazy(() => import('./pages/SettingsPage').then(m => ({ default: m.SettingsPage })))
const ExportsPage = lazy(() => import('./pages/ExportsPage').then(m => ({ default: m.ExportsPage })))

export function App() {
  return (
    <AuthProvider>
      <LocaleProvider>
      <Suspense fallback={<LoadingState />}>
      <Routes>
        <Route path="/auth/sign-in" element={<AuthPage mode="sign-in" />} />
        <Route path="/auth/sign-up" element={<AuthPage mode="sign-up" />} />
        <Route path="/auth/verify-email" element={<AuthPage mode="verify-email" />} />
        <Route element={<SessionGate />}>
          <Route element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="trends" element={<TrendsPage />} />
        <Route path="assistant" element={<AssistantPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="exports" element={<ExportsPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Route>
      </Routes>
      </Suspense>
      </LocaleProvider>
    </AuthProvider>
  )
}
