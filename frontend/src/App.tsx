import { Route, Routes } from 'react-router-dom'
import { AppLayout } from './layouts/AppLayout'
import { AssistantPage } from './pages/AssistantPage'
import { DashboardPage } from './pages/DashboardPage'
import { HistoryPage } from './pages/HistoryPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { ReportsPage } from './pages/ReportsPage'
import { TrendsPage } from './pages/TrendsPage'
import { AuthProvider } from './features/auth/AuthProvider'
import { LocaleProvider } from './i18n/LocaleProvider'
import { SessionGate } from './features/auth/SessionGate'
import { AuthPage } from './pages/AuthPage'
import { SettingsPage } from './pages/SettingsPage'
import { ExportsPage } from './pages/ExportsPage'
import { NotificationsPage } from './features/system/Notifications'

export function App() {
  return (
    <AuthProvider>
      <LocaleProvider>
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
      </LocaleProvider>
    </AuthProvider>
  )
}
