import { Card } from '../components/Card'
import { ErrorState } from '../components/ErrorState'
import { LoadingState } from '../components/LoadingState'
import { PageHeader } from '../components/PageHeader'
import { useAuth } from '../features/auth/auth-context'
import { ReportHistory } from '../features/reports/ReportHistory'
import { ReportUpload } from '../features/reports/ReportUpload'
import { useReportHistory } from '../features/reports/useReportHistory'

export function ReportsPage() {
  const { state, checkSession } = useAuth()
  const ownerId = state.status === 'authenticated' ? state.session.user.id : ''
  const history = useReportHistory(ownerId, checkSession)
  return (
    <>
      <PageHeader eyebrow="REPORTS" title="Your reports, together" description="Upload and keep your medical reports in your private workspace. Download or delete them whenever you need." />
      {history.state.status === 'loading' && <Card className="report-feedback"><LoadingState title="Loading your reports…" description="Checking your private report history." /></Card>}
      {history.state.status === 'error' && <Card className="report-feedback"><ErrorState title="Unable to load reports" description={history.state.message} onRetry={history.refresh} /></Card>}
      {history.state.status === 'ready' && <div className="reports-workspace"><ReportUpload ownerId={ownerId} config={history.state.config} onChange={history.refresh} onAuthFailure={history.authFailure} /><ReportHistory ownerId={ownerId} page={history.state.page} notice={history.state.notice} refreshError={history.state.refreshError} refreshing={history.refreshing} loadingMore={history.loadingMore} moreError={history.moreError} onRefresh={history.refresh} onLoadMore={history.loadMore} onAuthFailure={history.authFailure} /></div>}
      <div className="page-note"><span className="page-note__line" /><p>Inspect source-preserving extracted text from report history. Medical interpretation and AI explanations are not included.</p></div>
    </>
  )
}
