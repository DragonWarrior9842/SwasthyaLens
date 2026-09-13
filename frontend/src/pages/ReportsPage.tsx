import { Badge } from '../components/Badge'
import { Card } from '../components/Card'
import { EmptyState } from '../components/EmptyState'
import { PageHeader } from '../components/PageHeader'

export function ReportsPage() {
  return (
    <>
      <PageHeader eyebrow="REPORTS" title="Your reports, made clearer" description="A dedicated place for medical reports and understandable health information." />
      <Card>
        <div className="card-heading"><h2>Report history</h2><Badge>Coming later</Badge></div>
        <EmptyState icon="report" title="No reports uploaded yet." description="Report upload is not available in this version. When it is ready, your reports and their processing status will appear here.">
          <p>PDF and image support will be added in a later phase.</p>
        </EmptyState>
      </Card>
      <div className="page-note"><span className="page-note__line" /><p>Every report has a story. This space will help you keep yours together.</p></div>
    </>
  )
}
